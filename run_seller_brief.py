"""Backward-compatible command name for the Brass Ledger sales agent."""

from run_sales_agent import main


if __name__ == "__main__":
    raise SystemExit(main())
