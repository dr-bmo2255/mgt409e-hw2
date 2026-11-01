"""Free-form terminal entry point for the single PydanticAI sales agent."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from harness import HarnessResult, run_sales_query
from sales_agent import CompanyProfile, CustomerOutreachResult, VerifiedFact

RESET = "\033[0m"
BRASS = "\033[38;2;201;162;39m"
GREEN_GLASS = "\033[38;2;79;169;124m"
CREAM = "\033[38;2;245;230;200m"
LEATHER = "\033[38;2;154;101;70m"
MUTED = "\033[38;2;185;173;147m"
ERROR = "\033[1;38;2;255;138;128m"


def _enable_terminal() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    if os.name == "nt":
        os.system("")


def _strip_ansi(value: str) -> str:
    for code in (RESET, BRASS, GREEN_GLASS, CREAM, LEATHER, MUTED, ERROR):
        value = value.replace(code, "")
    return value


def _panel(title: str, lines: list[str], border: str = GREEN_GLASS) -> None:
    width = 86
    title_text = f" {title} "
    left = max(1, (width - len(title_text)) // 2)
    right = width - len(title_text) - left
    print(f"{border}╔{'═' * left}{BRASS}{title_text}{border}{'═' * right}╗{RESET}")
    for line in lines:
        visible = len(_strip_ansi(line))
        print(f"{border}║{RESET} {line}{' ' * max(0, width - 2 - visible)} {border}║{RESET}")
    print(f"{border}╚{'═' * width}╝{RESET}")


def _fact_lines(facts: list[VerifiedFact]) -> list[str]:
    if not facts:
        return [f"{MUTED}Not verified on the official website.{RESET}"]
    return [f"{GREEN_GLASS}•{RESET} {fact.statement}" for fact in facts]


def _profile_lines(profile: CompanyProfile) -> list[str]:
    summary = (
        profile.company_summary.statement
        if profile.company_summary
        else "No concise summary was verified on the official website."
    )
    return [
        f"{CREAM}{summary}{RESET}",
        "",
        f"{BRASS}Products & services{RESET}",
        *_fact_lines(profile.products_and_services),
        "",
        f"{BRASS}Industries served{RESET}",
        *_fact_lines(profile.industries_served),
        "",
        f"{BRASS}Target-customer signals{RESET}",
        *_fact_lines(profile.target_customer_signals),
    ]


def _show_result(result: HarnessResult) -> None:
    if isinstance(result.output, CompanyProfile):
        _panel(
            f"{result.output.company_name} · Company Ledger",
            _profile_lines(result.output),
            LEATHER,
        )
    elif isinstance(result.output, CustomerOutreachResult):
        lines = [
            f"{CREAM}{result.message}{RESET}",
            "",
            *[
                (
                    f"{GREEN_GLASS}•{RESET} {target.company_name} "
                    f"— fit {target.fit_score}/100 — {target.contact_emails[0].email}"
                )
                for target in result.output.targets
            ],
            "",
            f"{MUTED}All outreach remains draft-only; nothing was sent.{RESET}",
        ]
        _panel(
            f"{result.output.seller_company_name} · Target Ledger",
            lines,
            LEATHER,
        )
    else:
        _panel("Research Desk Notice", [f"{ERROR}{result.message}{RESET}"], LEATHER)

    usage = result.usage
    cost = usage.get("cost_usd") or "unavailable; token cap enforced"
    print(f"\n{BRASS}Stop reason:{RESET} {result.stop_reason}")
    print(
        f"{BRASS}Usage:{RESET} {usage.get('total_tokens', 0)} tokens · "
        f"{usage.get('requests', 0)} model requests · ${cost}"
    )
    for label, path in result.artifacts.items():
        print(f"{BRASS}{label.replace('_', ' ').title()}:{RESET} {CREAM}{path}{RESET}")
    print(f"{BRASS}Audit:{RESET} {CREAM}{result.audit_path}{RESET}")
    print(f"{MUTED}No emails, forms, or messages were sent.{RESET}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a verified seller profile, or use one to find qualified customer "
            "targets and draft unsent outreach emails."
        )
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Plain-language instructions for the selected mode.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--url",
        "-url",
        help="The company's official website, e.g. https://www.example.com.",
    )
    mode.add_argument(
        "--profile",
        help="Seller profile JSON from Problem 4, e.g. assets/company_profile.json.",
    )
    return parser.parse_args()


def main() -> int:
    _enable_terminal()
    args = _parse_args()
    _panel(
        "The Brass Ledger",
        [
            f"{CREAM}Official-site company research for discerning B2B prospecting.{RESET}",
            f"{MUTED}One agent · bounded cost · verified facts · no emails sent{RESET}",
        ],
    )

    query = " ".join(args.query).strip()
    if not query:
        try:
            query = input(f"\n{BRASS}What company profile would you like?\n>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{MUTED}Cancelled. No model call was made.{RESET}")
            return 130

    print(f"\n{GREEN_GLASS}The research desk is examining the request…{RESET}")
    result = asyncio.run(
        run_sales_query(query, website=args.url, profile_path=args.profile)
    )
    print()
    _show_result(result)
    return 0 if result.stop_reason == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
