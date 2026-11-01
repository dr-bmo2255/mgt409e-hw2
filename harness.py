"""Safety, memory, cost controls, stopping rules, and audit trail for the sales agent."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessage,
    NativeToolCallPart,
    NativeToolReturnPart,
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.usage import RunUsage, UsageLimits
from pydantic_graph import End

from sales_agent import (
    PROJECT_DIR,
    CompanyProfile,
    CustomerOutreachResult,
    SalesAgentOutput,
    SalesAgentDeps,
    build_model,
    deterministic_outreach_fields,
    deterministic_profile_fields,
    extract_website,
    normalize_website,
    resolve_profile_path,
    sales_agent,
    write_outreach_files,
    write_profile_file,
)

MAX_MODEL_REQUESTS = 5
MAX_TOOL_CALLS = 5
MAX_INPUT_TOKENS = 65_000
MAX_OUTPUT_TOKENS = 6_500
MAX_TOTAL_TOKENS = 72_000
MAX_RUN_USD = Decimal("0.90")
DEFAULT_AUDIT_PATH = PROJECT_DIR / "output" / "audit_log.json"
UNSAFE_PATTERNS = (
    r"ignore (all )?(previous|prior) (instructions|rules)",
    r"\bjailbreak\b",
    r"\b(hack|steal|phish|malware)\b",
    r"\b(send|submit|deliver)\b.{0,30}\b(email|message|form)\b",
    r"\b(scrape|collect|find)\b.{0,30}\b(personal|private)\b.{0,20}\b(email|phone|address)",
)


@dataclass
class HarnessMemory:
    """Conversation history plus current sales-profile state."""

    history: list[ModelMessage] = field(default_factory=list)
    current_profile: CompanyProfile | None = None

    def profile_state(self) -> str:
        if self.current_profile is None:
            return "No company profile has been created in this session."
        return (
            f"Current profile: {self.current_profile.company_name}; "
            f"website={self.current_profile.company_website}; "
            f"pages={len(self.current_profile.pages_crawled)}."
        )


@dataclass
class HarnessResult:
    query: str
    output: SalesAgentOutput | None
    message: str
    stop_reason: str
    audit_path: Path
    artifacts: dict[str, str]
    loop_iterations: int
    usage: dict[str, object]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def screen_query(query: str) -> str | None:
    """Refuse unsafe or out-of-scope requests before spending tokens."""

    if not query.strip():
        return "Please provide a company-profile request containing the official website."
    if len(query) > 4_000:
        return "The request is too long. Keep it under 4,000 characters."
    lowered = query.casefold()
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, lowered):
            return (
                "I cannot help with that request. This agent only builds evidence-based company "
                "profiles from an official public website and never sends communications or "
                "collects sensitive personal information."
            )
    return None


def usage_payload(usage: RunUsage | None) -> dict[str, object]:
    if usage is None:
        return {
            "requests": 0,
            "tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": None,
        }
    cost = usage.cost
    return {
        "requests": usage.requests,
        "tool_calls": usage.tool_calls,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "cost_usd": str(cost) if cost is not None else None,
    }


def _safe_observation(value: Any, max_characters: int = 5_000) -> Any:
    """Keep audit observations useful without duplicating entire crawled websites."""

    if isinstance(value, str):
        return value[:max_characters] + ("…[truncated]" if len(value) > max_characters else "")
    try:
        rendered = json.dumps(value, default=str)
    except TypeError:
        rendered = repr(value)
    if len(rendered) <= max_characters:
        return value
    return rendered[:max_characters] + "…[truncated]"


def _result_summary(value: Any) -> Any:
    """Summarize a tool result without copying full website content into the audit."""

    if isinstance(value, dict):
        pages = value.get("pages")
        if isinstance(pages, list):
            return {
                "ok": value.get("ok"),
                "page_count": len(pages),
                "page_urls": [
                    page.get("url")
                    for page in pages
                    if isinstance(page, dict) and page.get("url")
                ],
                "error_count": len(value.get("errors") or []),
                "limits": value.get("limits"),
            }
        candidates = value.get("candidates")
        if isinstance(candidates, list):
            return {
                "ok": value.get("ok"),
                "candidate_count": len(candidates),
                "candidates": [
                    {
                        "company_name": candidate.get("company_name"),
                        "website": candidate.get("website"),
                        "page_count": len(candidate.get("pages") or []),
                        "public_email_count": len(
                            candidate.get("public_contact_emails") or []
                        ),
                        "error_count": len(candidate.get("errors") or []),
                    }
                    for candidate in candidates
                    if isinstance(candidate, dict)
                ],
                "limits": value.get("limits"),
            }
        if "content" in value:
            return {
                "ok": value.get("ok"),
                "url": value.get("url"),
                "title": value.get("title"),
                "content_characters": len(str(value.get("content") or "")),
            }
    return _safe_observation(value, 1_000)


def describe_node(node: Any) -> dict[str, Any]:
    """Create a forensic but chain-of-thought-safe loop record."""

    record: dict[str, Any] = {
        "node": type(node).__name__,
        "thoughts": [],
        "tool_calls": [],
        "tool_results": [],
        "retries": [],
        "text_summary": [],
    }
    if isinstance(node, End):
        record["event"] = "finish"
        record["thoughts"].append(
            "The agent returned a validated final result, so the run can stop."
        )
        return record

    model_response = getattr(node, "model_response", None)
    if model_response is not None:
        record["event"] = "model_response"
        for part in getattr(model_response, "parts", []):
            if isinstance(part, ThinkingPart):
                record["thoughts"].append(
                    "Model reasoning occurred; private chain-of-thought is not retained."
                )
            elif isinstance(part, (ToolCallPart, NativeToolCallPart)):
                name = part.tool_name
                record["tool_calls"].append(
                    {"name": name, "args": getattr(part, "args", None)}
                )
                record["thoughts"].append(f"The agent selected the {name} tool.")
            elif isinstance(part, TextPart):
                record["text_summary"].append(_safe_observation(part.content, 1_000))
        if not record["thoughts"]:
            record["thoughts"].append(
                "The agent prepared structured profile content or responded to validation."
            )

    request = getattr(node, "request", None)
    if request is not None:
        for part in getattr(request, "parts", []):
            if isinstance(part, (ToolReturnPart, NativeToolReturnPart)):
                name = part.tool_name
                content = getattr(part, "content", None)
                record["tool_results"].append(
                    {"name": name, "result_summary": _result_summary(content)}
                )
                record["thoughts"].append(
                    f"The agent received the {name} result and can evaluate the evidence."
                )
            elif isinstance(part, RetryPromptPart):
                name = part.tool_name or "structured_output"
                record["retries"].append(
                    {"name": name, "error": _safe_observation(part.content, 1_000)}
                )
                record["thoughts"].append(
                    f"The {name} step failed or was rejected, so the model must retry."
                )
        if record["tool_results"] or record["retries"]:
            record["event"] = "tool_results"
        else:
            record["event"] = "model_request"
            record["thoughts"].append(
                "The harness sent the request and conversation memory to the model."
            )

    user_prompt = getattr(node, "user_prompt", None)
    if user_prompt:
        record["event"] = "user_prompt"
        record["user_prompt"] = _safe_observation(user_prompt, 4_000)
        record["thoughts"].append(
            "The agent received the human request and official-site allow-list."
        )
    return record


class AuditTrail:
    """JSON audit overwritten per run and flushed after every loop iteration."""

    def __init__(
        self,
        path: Path,
        query: str,
        website: str | None,
        profile_path: Path | None,
        hostname: str | None,
        memory: HarnessMemory,
    ) -> None:
        self.path = path
        self.memory = memory
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = {
            "run_started_utc": _now_iso(),
            "query": query,
            "website": website,
            "profile_path": str(profile_path) if profile_path else None,
            "allow_listed_host": hostname,
            "memory_state": memory.profile_state(),
            "limits": {
                "max_cost_usd": str(MAX_RUN_USD),
                "max_model_requests": MAX_MODEL_REQUESTS,
                "max_tool_calls": MAX_TOOL_CALLS,
                "max_input_tokens": MAX_INPUT_TOKENS,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "max_total_tokens": MAX_TOTAL_TOKENS,
            },
            "reasoning_policy": (
                "Records concise operational thoughts, tool calls, and result summaries; "
                "private chain-of-thought is not retained."
            ),
            "iterations": [],
            "stop": None,
            "usage": usage_payload(None),
        }
        self.flush()

    def write_iteration(self, index: int, node: Any, usage: RunUsage | None = None) -> None:
        """Record one loop iteration, including budget used and left before the cutoff."""

        used = usage_payload(usage)
        self.data["iterations"].append(
            {
                "iteration": index,
                "timestamp_utc": _now_iso(),
                **describe_node(node),
                "usage_so_far": used,
                "limits_remaining": {
                    "model_requests": MAX_MODEL_REQUESTS - used["requests"],
                    "tool_calls": MAX_TOOL_CALLS - used["tool_calls"],
                    "input_tokens": MAX_INPUT_TOKENS - used["input_tokens"],
                    "output_tokens": MAX_OUTPUT_TOKENS - used["output_tokens"],
                    "total_tokens": MAX_TOTAL_TOKENS - used["total_tokens"],
                },
            }
        )
        self.flush()

    def write_stop(
        self,
        reason: str,
        message: str,
        iterations: int,
        usage: RunUsage | None = None,
        artifacts: dict[str, str] | None = None,
    ) -> None:
        self.data["stop"] = {
            "timestamp_utc": _now_iso(),
            "reason": reason,
            "loop_iterations": iterations,
            "message": message,
            "artifacts": artifacts or {},
            "memory_state_after": self.memory.profile_state(),
            "memory_messages": len(self.memory.history),
        }
        self.data["usage"] = usage_payload(usage)
        self.flush()

    def flush(self) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.data, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)


def _target_count_from_query(query: str) -> int:
    match = re.search(r"\b([1-5])\b", query)
    return int(match.group(1)) if match else 3


async def run_sales_query(
    query: str,
    website: str | None = None,
    profile_path: str | Path | None = None,
    memory: HarnessMemory | None = None,
    audit_path: Path | None = None,
) -> HarnessResult:
    """Run profile or customer-outreach mode with bounded cost and a per-loop audit."""

    memory = memory or HarnessMemory()
    blocked = screen_query(query)
    hostname: str | None = None
    resolved_profile: Path | None = None

    if website and profile_path and blocked is None:
        blocked = "Choose either --url for profile mode or --profile for customer-target mode."
    try:
        if profile_path:
            resolved_profile = resolve_profile_path(profile_path)
            if not resolved_profile.is_file():
                raise ValueError(f"Profile file does not exist: {resolved_profile}")
        else:
            website = normalize_website(website) if website else (
                extract_website(query) if blocked is None else None
            )
            hostname = urlparse(website).hostname if website else None
    except ValueError as exc:
        if blocked is None:
            blocked = str(exc)

    audit = AuditTrail(
        audit_path or DEFAULT_AUDIT_PATH,
        query,
        website,
        resolved_profile,
        hostname,
        memory,
    )
    if blocked is not None or (
        resolved_profile is None and (website is None or hostname is None)
    ):
        message = blocked or "Provide --url for profile mode or --profile for target mode."
        audit.write_stop("guardrail_refuse", message, 0)
        return HarnessResult(
            query=query,
            output=None,
            message=message,
            stop_reason="guardrail_refuse",
            audit_path=audit.path,
            artifacts={},
            loop_iterations=0,
            usage=usage_payload(None),
        )

    target_count = _target_count_from_query(query)
    deps = SalesAgentDeps(
        input_query=query,
        website=website,
        allowed_hostname=hostname,
        profile_path=resolved_profile,
        requested_target_count=target_count,
        current_profile=memory.current_profile,
    )
    limits = UsageLimits(
        cost_limit=MAX_RUN_USD,
        request_limit=MAX_MODEL_REQUESTS,
        tool_calls_limit=MAX_TOOL_CALLS,
        input_tokens_limit=MAX_INPUT_TOKENS,
        output_tokens_limit=MAX_OUTPUT_TOKENS,
        total_tokens_limit=MAX_TOTAL_TOKENS,
    )
    run_usage: RunUsage | None = None
    iterations = 0

    if resolved_profile is not None:
        run_prompt = (
            f"Human request:\n{query}\n\n"
            f"Seller profile path allow-list: {resolved_profile}\n"
            f"Required target count: {target_count}\n\n"
            "Enter customer-target and outreach-draft mode. Read the profile with the tool, "
            "use one focused native web search for regional customer groups whose official "
            "contact-page snippets show public business emails, research those official "
            "websites with Playwright, "
            "keep only strong non-competitor fits with verified public business emails, and "
            "return the structured result. Never send email."
        )
    else:
        run_prompt = (
            f"Human request:\n{query}\n\n"
            f"Official website allow-list: {website}\n"
            f"Current session profile state: {memory.profile_state()}\n\n"
            "Enter company-profile mode, crawl only the allow-listed website, and build "
            "the verified profile."
        )

    try:
        async with sales_agent.iter(
            run_prompt,
            model=build_model(),
            deps=deps,
            message_history=memory.history or None,
            usage_limits=limits,
        ) as agent_run:
            async for node in agent_run:
                iterations += 1
                run_usage = agent_run.usage
                audit.write_iteration(iterations, node, run_usage)
            result = agent_run.result

        if result is None:
            message = "The run ended without a final structured result."
            audit.write_stop("no_final_output", message, iterations)
            return HarnessResult(
                query=query,
                output=None,
                message=message,
                stop_reason="no_final_output",
                audit_path=audit.path,
                artifacts={},
                loop_iterations=iterations,
                usage=usage_payload(None),
            )

        run_usage = result.usage
        memory.history = result.all_messages()
        artifacts: dict[str, str]
        if isinstance(result.output, CompanyProfile):
            output: SalesAgentOutput = deterministic_profile_fields(result.output, deps)
            profile_output_path = write_profile_file(output)
            memory.current_profile = output
            artifacts = {"company_profile": str(profile_output_path)}
            message = (
                f"Profile created for {output.company_name} from "
                f"{len(output.pages_crawled)} official website pages."
            )
        elif isinstance(result.output, CustomerOutreachResult):
            output = deterministic_outreach_fields(result.output, deps)
            targets_path, emails_path = write_outreach_files(output)
            artifacts = {
                "targets": str(targets_path),
                "emails": str(emails_path),
            }
            message = (
                f"Created {len(output.targets)} qualified customer targets and "
                f"{len(output.emails)} unsent email drafts for {output.seller_company_name}."
            )
        else:  # Defensive: output schema currently permits only the two models above.
            raise TypeError(f"Unsupported agent output: {type(result.output).__name__}")

        audit.write_stop(
            "finished",
            message,
            iterations,
            run_usage,
            artifacts=artifacts,
        )
        return HarnessResult(
            query=query,
            output=output,
            message=message,
            stop_reason="finished",
            audit_path=audit.path,
            artifacts=artifacts,
            loop_iterations=iterations,
            usage=usage_payload(run_usage),
        )
    except UsageLimitExceeded as exc:
        if "agent_run" in locals():
            run_usage = agent_run.usage
        message = (
            "Stopped by the bounded cost/usage cutoff. "
            f"Detail: {exc}"
        )
        audit.write_stop("max_step_or_cost_cutoff", message, iterations, run_usage)
        return HarnessResult(
            query=query,
            output=None,
            message=message,
            stop_reason="max_step_or_cost_cutoff",
            audit_path=audit.path,
            artifacts={},
            loop_iterations=iterations,
            usage=usage_payload(run_usage),
        )
    except Exception as exc:  # Errors are reported without environment values or secrets.
        message = f"Harness stopped after {type(exc).__name__}: {exc}"
        audit.write_stop("error", message, iterations, run_usage)
        return HarnessResult(
            query=query,
            output=None,
            message=message,
            stop_reason="error",
            audit_path=audit.path,
            artifacts={},
            loop_iterations=iterations,
            usage=usage_payload(run_usage),
        )
