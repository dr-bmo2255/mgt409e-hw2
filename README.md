# Homework 2 — B2B Sales Research Agent

The project uses one reusable PydanticAI agent defined in `sales_agent.py`. It interprets a
free-form terminal request, crawls the supplied official company website, and produces a verified
company profile for later lead finding. The agent does not send emails, submit forms, or contact
anyone.

## Setup

Pause OneDrive or Dropbox syncing (or exclude `.venv`) before creating the environment.

```powershell
cd "C:\Users\bmore\MGT409\Homework 2"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PLAYWRIGHT_BROWSERS_PATH="0"
python -m playwright install chromium
```

Store the Portkey key in `C:\Users\bmore\MGT409\.env` or copy `.env.example` to this folder as
`.env` and add the key there. Never commit `.env`.

## Run

Build the seller profile:

```powershell
python sales_agent.py "Build a profile of this company, focusing on products, industries, and customer evidence." --url https://www.example.com
```

The quoted argument is the human's free-form query. `--url` is the separate official website
allow-list. (`-url` is also accepted; the standard `--url` spelling has no space.)

The profile is saved as `assets/company_profile.json`. It contains profile facts,
requested findings, exact evidence excerpts, official-site source URLs, crawled pages, and
unresolved items.

Find qualified targets and create unsent outreach drafts:

```powershell
python sales_agent.py "find 3 good customer targets from this company and draft outreach emails." --profile assets/company_profile.json
```

This mode writes `output/targets.json` and `output/emails.json`. It reads the selected profile,
uses bounded native web search to discover candidates, and uses Playwright to verify fit, business
context, and public contact emails on candidate websites. The persistent instructions for both
modes live in `prompts/sales_agent.md`.

The model defaults to `gpt-5.6-luna` and can be changed with `OPENAI_MODEL`.

Every run overwrites `output/audit_log.json`. The JSON records the run date and time, each
agent-loop iteration, concise operational thoughts, tool-call names and arguments, result
summaries, stopping reason, token usage, and provider-reported cost when available. It does not
retain private chain-of-thought.

`run_seller_brief.py` remains as a backward-compatible command and launches the same agent.

## Design safeguards

- Model output is validated against Pydantic models before JSON is written.
- The seller website reader accepts only the user-provided public host.
- Website text is treated as untrusted evidence, not instructions.
- The Playwright crawler blocks heavy media, prioritizes profile-relevant pages, and is capped at
  five pages and 20,000 characters. Playwright is the one deliberate browser dependency because
  many company websites render essential text with JavaScript.
- Research runs are limited to five model requests, five tool calls, 72,000 cumulative tokens, and a
  PydanticAI cost limit of $0.90. The token cap remains active if provider pricing is unavailable.
- Every evidence excerpt and source URL is validated against pages the tool actually crawled.
- Company-profile mode cannot use third-party facts. Target mode uses at most two native searches
  for discovery, then requires candidate-site evidence before retaining a company.
- Missing facts are left empty or recorded as unresolved rather than invented.
- No tool can send an email or other communication; `output/emails.json` contains drafts only.
