"""Focused tests that make no paid model calls."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from pydantic_ai.messages import RetryPromptPart, ToolCallPart, ToolReturnPart
from pydantic_ai.usage import RunUsage

from harness import (
    AuditTrail,
    DEFAULT_AUDIT_PATH,
    HarnessMemory,
    MAX_RUN_USD,
    MAX_TOTAL_TOKENS,
    run_sales_query,
    screen_query,
)
from sales_agent import (
    SALES_AGENT_SYSTEM_PROMPT,
    CompanyProfile,
    CustomerTarget,
    EmailDraft,
    _link_priority,
    extract_website,
    normalize_website,
    write_profile_file,
)


class QueryAndGuardrailTests(unittest.TestCase):
    def test_extracts_explicit_website_from_free_form_query(self) -> None:
        query = "Profile Acme at https://www.example.com/about, focusing on its customers."
        self.assertEqual(extract_website(query), "https://www.example.com/about")

    def test_extracts_bare_domain(self) -> None:
        self.assertEqual(extract_website("Research Example at example.com"), "https://example.com")

    def test_rejects_embedded_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "credentials"):
            normalize_website("https://user:password@example.com")

    def test_refuses_requests_to_send_email(self) -> None:
        refusal = screen_query("Go to https://example.com and send an email to the CEO")
        self.assertIsNotNone(refusal)

    def test_prioritizes_profile_pages(self) -> None:
        query = "Focus on industries and customer case studies"
        links = [
            "https://example.com/privacy",
            "https://example.com/customer-case-studies",
            "https://example.com/about",
        ]
        ordered = sorted(links, key=lambda value: _link_priority(value, query))
        self.assertEqual(ordered[0], "https://example.com/customer-case-studies")


class AgentContractTests(unittest.TestCase):
    def test_system_prompt_is_loaded_and_strict(self) -> None:
        self.assertIn("Never invent a fact. Ever.", SALES_AGENT_SYSTEM_PROMPT)
        self.assertIn("crawl_company_website", SALES_AGENT_SYSTEM_PROMPT)
        self.assertIn("assets/company_profile.json", SALES_AGENT_SYSTEM_PROMPT)
        self.assertIn("research_candidate_websites", SALES_AGENT_SYSTEM_PROMPT)
        self.assertIn("Never send them", SALES_AGENT_SYSTEM_PROMPT)

    def test_only_one_agent_is_defined(self) -> None:
        project = Path(__file__).resolve().parent
        assignment = re.compile(r"^\w+(?:\s*:[^=]+)?\s*=\s*Agent\(", re.MULTILINE)
        count = sum(
            len(assignment.findall(path.read_text(encoding="utf-8")))
            for path in project.glob("*.py")
        )
        self.assertEqual(count, 1)

    def test_dual_cost_controls_stay_below_one_dollar(self) -> None:
        self.assertLess(MAX_RUN_USD, Decimal("1.00"))
        self.assertLessEqual(MAX_TOTAL_TOKENS, 72_000)

    def test_outreach_contract_requires_contacts_and_unsent_status(self) -> None:
        self.assertTrue(CustomerTarget.model_fields["contact_emails"].is_required())
        self.assertEqual(
            EmailDraft.model_fields["status"].default,
            "draft_not_sent",
        )
        self.assertEqual(DEFAULT_AUDIT_PATH.parent.name, "output")

    def test_empty_profile_writes_valid_json(self) -> None:
        profile = CompanyProfile(
            company_name="Verified Test Company",
            company_website="https://example.com",
            profile_generated_at_utc="2026-09-24T00:00:00Z",
            requested_information="Test request",
            company_summary=None,
            products_and_services=[],
            industries_served=[],
            customer_types=[],
            problems_solved=[],
            value_propositions=[],
            differentiators=[],
            named_customers=[],
            geographic_reach=[],
            target_customer_signals=[],
            buyer_role_signals=[],
            requested_information_findings=[],
            pages_crawled=[],
            unresolved_items=["No live crawl was used in this unit test."],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = write_profile_file(profile, Path(directory) / "company_profile.json")
            loaded = CompanyProfile.model_validate_json(path.read_text(encoding="utf-8"))
        self.assertEqual(loaded.company_name, "Verified Test Company")


class AuditTrailTests(unittest.IsolatedAsyncioTestCase):
    def test_iterations_capture_tool_name_args_and_result_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit_log.json"
            audit = AuditTrail(
                path,
                "Build a profile",
                "https://example.com",
                None,
                "example.com",
                HarnessMemory(),
            )
            audit.write_iteration(
                1,
                SimpleNamespace(
                    model_response=SimpleNamespace(
                        parts=[
                            ToolCallPart(
                                tool_name="crawl_company_website",
                                args={"start_url": "https://example.com", "max_pages": 1},
                            )
                        ]
                    )
                ),
            )
            audit.write_iteration(
                2,
                SimpleNamespace(
                    request=SimpleNamespace(
                        parts=[
                            ToolReturnPart(
                                tool_name="crawl_company_website",
                                content={
                                    "ok": True,
                                    "pages": [{"url": "https://example.com"}],
                                    "errors": [],
                                },
                            )
                        ]
                    )
                ),
            )
            audit.write_stop("finished", "test complete", 2)
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            data["iterations"][0]["tool_calls"][0]["name"],
            "crawl_company_website",
        )
        self.assertEqual(
            data["iterations"][1]["tool_results"][0]["result_summary"]["page_count"],
            1,
        )
        self.assertIsNotNone(data["iterations"][0]["timestamp_utc"])
        self.assertIsNotNone(data["stop"])

    def test_iterations_capture_retries_budget_and_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit_log.json"
            audit = AuditTrail(path, "Build a profile", None, None, None, HarnessMemory())
            audit.write_iteration(
                1,
                SimpleNamespace(
                    request=SimpleNamespace(
                        parts=[
                            RetryPromptPart(
                                tool_name="inspect_crawled_page",
                                content="URL was not crawled.",
                            )
                        ]
                    )
                ),
                RunUsage(requests=2, tool_calls=1, input_tokens=1_000, output_tokens=100),
            )
            audit.write_stop("finished", "test complete", 1)
            data = json.loads(path.read_text(encoding="utf-8"))

        iteration = data["iterations"][0]
        self.assertEqual(iteration["retries"][0]["name"], "inspect_crawled_page")
        self.assertEqual(iteration["usage_so_far"]["requests"], 2)
        self.assertEqual(iteration["limits_remaining"]["model_requests"], 3)
        self.assertIn("memory_state_after", data["stop"])

    async def test_refusal_creates_a_zero_cost_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "refusal-audit.md"
            result = await run_sales_query(
                "Send an email using https://example.com",
                audit_path=audit_path,
            )
            audit = audit_path.read_text(encoding="utf-8")
        self.assertEqual(result.stop_reason, "guardrail_refuse")
        self.assertEqual(result.usage["total_tokens"], 0)
        self.assertIn('"stop": {', audit)
        self.assertIn('"iterations": []', audit)
        self.assertIn('"total_tokens": 0', audit)


if __name__ == "__main__":
    unittest.main()
