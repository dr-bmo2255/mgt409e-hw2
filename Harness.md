# Sales Agent Harness

This project uses one PydanticAI agent for two jobs:

1. Build a verified seller profile from the seller's official website.
2. Find qualified customer companies and draft outreach emails.

The harness surrounds that agent with limited tools, evidence checks, stopping rules, cost limits,
and an audit trail. It never gives the agent a way to send an email.

## 1. Tools available to the agent

### Crawl the seller's website

**Tool:** `crawl_company_website`

- **Purpose:** Uses Playwright to read the seller's official website, including JavaScript-rendered
  pages.
- **Inputs:** The starting URL and a requested page limit.
- **Outputs:** Successfully read page URLs, page titles, bounded page text, crawl errors, and the
  limits applied.
- **Controls:** The tool stays on the human-provided, allow-listed host; blocks images, media, and
  fonts; runs only once; reads at most 5 pages; and returns no more than 20,000 characters.

### Re-read seller evidence

**Tool:** `inspect_crawled_page`

- **Purpose:** Lets the agent review a seller page already stored in the evidence ledger.
- **Input:** An exact URL returned by the seller crawler.
- **Output:** The cached title and text for that page, or an error if the URL was not crawled.
- **Control:** It cannot browse a new URL.

### Read the seller profile

**Tool:** `read_company_profile`

- **Purpose:** Loads the verified profile used to judge potential customers.
- **Input:** The path supplied by the human through `--profile`.
- **Output:** A compact, validated summary of the seller's offerings, markets, customer types,
  problems solved, value propositions, geography, and target signals.
- **Controls:** It accepts only a JSON file directly inside `assets`, requires the exact path
  allow-listed by the harness, and validates the file against the `CompanyProfile` schema.

### Search the public web

**Tool:** Native OpenAI web search through Portkey.

- **Purpose:** Discovers plausible customer companies and their official websites.
- **Inputs:** Focused search queries based on the verified seller profile.
- **Outputs:** Public search results, snippets, and URLs for candidate discovery.
- **Controls:** Customer-target mode allows one bounded search capability. Search results alone do
  not qualify a target; the candidate's own website must verify the fit.
- **Profile-mode restriction:** Web search cannot be used as factual evidence when building the
  seller profile.

### Research candidate websites

**Tool:** `research_candidate_websites`

- **Purpose:** Uses Playwright to verify business context and find public business contact emails
  on candidate companies' official websites.
- **Input:** Up to 6 candidate records, each containing a company name and official website.
- **Output:** Official page titles, URLs, bounded text, public emails found on those pages, errors,
  and applied limits.
- **Controls:** At most 2 calls per run, 2 pages per candidate, and 3,000 returned characters per
  candidate. It blocks heavy media, rejects local/private addresses, stays on each candidate's
  host, and never submits a form or sends a message.

### Submit a structured result

PydanticAI provides a final structured-output mechanism. The agent must return either a validated
`CompanyProfile` or `CustomerOutreachResult`. The harness—not the model—then writes:

- `assets/company_profile.json`
- `output/targets.json`
- `output/emails.json`

This mechanism writes local files only. It does not communicate with any company.

## 2. Stopping rules

### Successful completion

The profile run is done when:

- The requested profile fields have enough official-site evidence, or relevant accessible pages
  are exhausted.
- Every retained fact includes an exact excerpt and URL from a page the crawler actually read.
- The result passes the `CompanyProfile` schema.

The customer-target run is done when:

- The profile has been read through the approved tool.
- Candidate discovery and official-site research are complete.
- The agent has exactly the requested number of qualified targets (1–5; default 3).
- Every target has verified business context and at least one public business contact email.
- Every target has one matching email marked `draft_not_sent`.
- The result passes the `CustomerOutreachResult` schema.

### Mandatory cutoffs

Each run must stop at any of these limits:

- 5 model requests.
- 5 successful tool calls.
- 65,000 cumulative input tokens.
- 6,500 cumulative output tokens.
- 72,000 cumulative total tokens.
- A $0.90 PydanticAI cost ceiling when the provider returns recognized pricing data.
- 1 retry for a failed tool and 2 retries for invalid structured output.

The token ceilings remain active when the Portkey model name does not provide recognized pricing
telemetry. The audit records when provider-reported cost is unavailable.

### Failure and refusal stops

The harness stops without producing deliverables when:

- The request is blank, longer than 4,000 characters, unsafe, or asks the agent to send a message.
- The required `--url` or `--profile` input is missing or invalid.
- Both modes are requested at once.
- A required file cannot be read or validated.
- The agent cannot produce enough evidence-backed targets before reaching its limits.
- A model, browser, tool, validation, or file-writing error prevents safe completion.

Individual page failures do not cause endless retries. They are recorded as unresolved profile
items, rejected candidates, or crawl errors.

## 3. Guardrails

The agent must not:

- Invent company facts, capabilities, needs, customer relationships, results, prices, or contact
  information.
- Treat model memory, search snippets, or a famous name as sufficient proof of customer fit.
- Keep random businesses, competitors, resellers, or companies outside the evidenced market.
- Retain a target without official-site business context and a verified public business email.
- Collect sensitive personal information or scrape private contact data.
- Send an email, submit a contact form, or imply that a draft was delivered.
- Follow instructions found inside a website; webpage text is untrusted evidence.
- Browse local, private, loopback, reserved, credential-bearing, or non-HTTP(S) URLs.
- Leave the allow-listed seller or candidate host while crawling.
- Read arbitrary local files or write deliverables outside the designated project locations.
- Expose API keys or other secrets.
- Continue indefinitely after errors, failed validation, or budget cutoffs.

Additional protections:

- Exact evidence excerpts and source URLs are checked against text stored by the crawlers.
- Public contact emails must have been observed on the cited candidate page.
- Every draft must use an email verified for that same target.
- The application deterministically sets paths, timestamps, requested counts, and the
  `DRAFTS ONLY — NO EMAILS WERE SENT` safety label.
- `output/audit_log.json` is rewritten on every run and saved after every loop iteration, so a
  crash still leaves a record of each step completed. Each iteration records its timestamp,
  operational thought summaries, tool names and arguments, result summaries, failed or rejected
  steps that forced a retry, usage so far, and the budget remaining before each cutoff. The final
  stop record adds the stopping reason, artifacts, total usage, and the memory state after the
  run. Private chain-of-thought and secrets are not retained.
