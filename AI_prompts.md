# AI Prompt Log

This file records the prompts used to complete each Homework 2 problem. Each problem will have its own section containing the problem number, title, initial prompt, and any follow-up prompts.

If a problem requires an additional prompt, the log will also include Brian's explanation of why the additional prompt was needed and what was missing from the prior result.

## Problem 1: Vibe coder prompts

### Prompt 1

> We are going to do a Yale SOM EMBA HW problem in our Foundations of AI for Managers class. For this project, use the Homework 2 folder that we've already created. Here we will build an agent to help a business find other business customers and draft outreach emails. YOU WILL NOT SEND THE EMAILS.

### Prompt 2

> Create a AI_prompts.md file. Keep this updated as we work. This is a log of what I've types to you. Break each problem down into a separate section of the file. I'll identify when each new problem starts. Each section will include the problem number and its title. Record the prompt that I give you. If I need to write additional prompts to you to accomplish a problem, ask me to comment on why I needed a second prompt - what was missing - and record it in the AI_prompts file as well. I will be graded on the code and the JSON outputs.

### Completion note

> That concludes "Problem 1: Vibe coder prompts"

## Problem 2: Seller brief

### Prompt 1

> "Problem 2:  Seller brief"  We are going to create an agent to find sales leads.  I want this agent, from a terminal command to request from the user the following 1) Company Name that we will be researching. 2) the company's website 3) Information that the user wants the agent to collect about the company that would then be useful to find APPROPRIATE sales targets for the user.  I will not be giving company names now.  I want create program that is capable of doing all these things so I can use it for other companies in the future, not just the one I'm interested in today.  Create the agent such that it does not need to reference this set of vibe-coding instructions again and can operate independently.

## Problem 3: Agent System Prompt

### Prompt 1

> " Problem 3: Agent System Prompt"  We will build only ONE PydanticAI agent for this entire assignment.  The agent system prompt file is "prompts/sales_agent.md" In "Problem 3" here we are defining how the agent builds the company profile when the human user asks for it.    The agent must defite what profile fields to collect and these will be taken from the seller brief and written into the prompt.    Agent then must crawl the company's website to fill these fields.  (again, the website to reference will be provided in terminal, not by reading the "brief" file.  DO NOT INVENT FACTS.  EVER.  Use only verified information from the website.  I want this agent to have a preppy personality  When presenting information to the user, I want it to be in a classic leather and brass style, and green glass like an old bank or  old money vibe.   when done, save the finished prfile to assets/company_profile.json.  In a later problem, we will be adding to this same prompt file when the agent later finds customers and drafts emails.

## Problem 4: Build agent & profile run

### Prompt 1

> Problem 4: "Build agent & profile run"  In this problem, we will build ONE pydanticAI agent in sales_agent.py that loads prompts/sales_agent.md into its system prompt.  I want you to provide it the tools that it will need to look through a company's website and write a profiles file.  You can use the Playwright web crawler package to accomplish this.   From the input query text, The agent should figure out what the human wants.  Then build a profile of the company of interest.  I will provide harness pieces from out class lecture to keep the agent both safe and cost-efficient.  I do not want you to spend more than $1.00 in tokens on any given company.  Efficiency matterrs, so if you can do it for just a few cents, that it preferred.  Create a python virtual environment in the Homework 2 folder.  Here are some course rules to follow:  # Semester Project Rules
>
> These rules apply to agents working on apps and course projects in this workspace.
>
> ## AI model
>
> - Use `gpt-5.6-luna` as the default model for application work.
> - Keep the model configurable through `OPENAI_MODEL`; do not hard-code it in multiple files.
> - Use a smaller model only for simple, low-risk tasks when cost or latency matters.
>
> ## API keys and secrets
>
> - Never hard-code API keys, tokens, passwords, or other secrets in source code, notebooks, or documentation.
> - Load secrets from environment variables, normally through a local `.env` file during development.
> - Use `PORTKEY_API_KEY` from `.env` for all AI calls routed through Portkey.
> - Use `OPENAI_API_KEY` only when making direct OpenAI calls instead of routing through Portkey.
> - Add `.env` and other secret files to `.gitignore`; commit a `.env.example` containing variable names only.
> - Never print or expose secret values in logs, screenshots, error messages, or generated files.
> - If a secret is exposed, stop using it and rotate or revoke it immediately.
>
> ## App appearance
>
> - Use a polished, leather, brass, and green glass appearance for these apps by default.
> - Prefer  darker backrounds a readable lighter colored text, generous spacing, and clear visual hierarchy.
> - Keep the interface responsive and accessible: maintain sufficient contrast, use descriptive labels, and show clear loading and error states.
>
> ## Dependencies
>
> - For PydanticAI with OpenAI or Portkey, put `pydantic-ai-slim[openai]` in `requirements.txt`.
> - Do not use the full `pydantic-ai` package unless the project specifically needs its additional providers and integrations. The full package pulls many unnecessary extras and can make installs very large or stall.
> - Keep dependencies focused and document any deliberate exception.
>
> ## Dash run and stop rules
>
> - Run Dash with `use_reloader=False`, or run with debug mode off, so one edit does not spawn multiple servers.
> - Before starting an app again, check whether an orphan server is using its port. For the default port 8050 in PowerShell:
>
>   ```powershell
>   netstat -ano | findstr :8050
>   taskkill /PID <pid> /F
>   ```
>
> - Change `8050` when the app uses another port.
> - When stopping a Dash app, kill the whole application process tree, not only whatever process currently owns port 8050. Confirm that child Python processes have stopped before restarting.
>
> ## Dropbox and OneDrive
>
> - Pause Dropbox or OneDrive syncing, or exclude `.venv`, while creating a virtual environment and running `pip install`.
> - Live sync during environment creation or installation can lock files and corrupt or stall the virtual environment.
> - Keep virtual environments local to the project and never commit them.
>
> ## Project hygiene
>
> - Keep each app's source, requirements, configuration examples, and documentation together in its project folder.
> - Make small, focused changes and verify the app starts cleanly after dependency or run configuration changes.  **Harness checklist:**
>
> - **Tools** — the list above
> - **Memory** — chat history + current portfolio state
> - **Stopping Rules** — clear finish / max-step cutoff so it cannot loop forever
> - **Guardrails** — universe allow-list; no inventing prices; refuse unsafe asks
> - **Audit trail** — forensic log of thoughts, tool calls, observations.  In the  audit file write down what happanes every loop iteration.  after u build it. test it and give me some sort of proof that it works.

### Prompt 2

> a little more to this instruction.  Each time the agent is run, it will write agent-loop interations (date & time, thoughts, tool calls - name + args + result summary and when the run stops to "outputs/audit_log.json.  Once that is dones.  I want to run this agent on a real company website. and produce a detailed file in assets/company_profile.json.  SO again, the script will be taking a text query from the human and -url from terminal and pass both of these to the agent.  Use the company from seller brief where we recorded the fields that we care about in prompts/sales_agent.md.  A termianl prompt will look like the following [ python sales_agent.py "build a profiles of this company." -- url https://www.examplecompany_url.com.  The quoted text is my query in plain-language instructions.  When we get to point that we are ready to run that agent, let me know so I can then test it.

### Why a second prompt was needed

> C:  I forgot to read ahad and give all the instructions to the vibe coder and I pasted the harness parameters

The initial Problem 4 prompt therefore omitted the exact audit-log path and format, the separate
query-plus-URL terminal interface, and the plan to wait for Brian's real-company test URL.

### Prompt 3 — Live company test

> run this on the agent:  "build a profile of this company" --url https://www.singerequipment.com/

## Problem 5: Expand prompt & find customers

### Prompt 1

> Moving on.  Next problem.  Problem 5 “Expand prompt & find customers”
> Here we will be adding instructions to “prompts/sales_agent.md” file to find customer companies and draft the outreach emails (Do Not Send the Emails).
> When the human asks for customer targets and to create outreach emails, I want the agent to, in one loop, with tools we’ve designed, 1) read the company profile file 2) search the web for potential customer companies. 3) only keep the company if it would actually be a good customer for the seller business.  DO not keep companies that are random businesses, competitor businesses, or famous names that just happen to have a website.”  4) look through each candidate’s website for useful business context and contact email.  5) draft a targeted outreach email for each target.  (Again.  Never Send the email)
> Save the results to  “output/targets.json” (The company info and contact emails) and “output/emails.json” (the drafted emails).  Make sure the agent continues to update the audit tracker file “output/audit_log.json”
> Then I want the agent to run and find 3 target customers and generate those JSON files.  Use this command structure:  python sales_agent.py “find 3 good customer targets from this company and draft outreach emails.” – profile assets/company_profile.json.
> Quoted text is the query.
> --profile points to the company profile JSON from Problem 4.  You may use OpenAI websearch (via Portkey) and playwrite.  Keep all of those harness pieces intact to avoid runaway costs and made-up facts

## Problem 6: Agent harness summary

### Prompt 1

> Problem 6 “Agent harness summary”
> Create “Harness.md” at the project root.  This is a short summary of how we kept the agent under control.   I want this to report the following: 1) tools – every tool that the agent can use, what it does, and the inputs / outputs.  2) Stopping rules – when the agent is done and when it must stop and why  (e.g. max steps, enough tarets, failures, etc. )  3)guardrails – what the agent must not do (e.g invent facts, send emails, runaway costs, unsafe actions, etc.)  Keep this harness files readable.  A non-coder executive manager should be able to read this without reading the sales_agent.py file.  (This step is important because this file will be compared to my code when the assignment is graded!)

## Problem 7: Rank targets and emails

### Prompt 1

> Problem 7 “Rank targets and emails”
> I want to write a reflection about each of the customer targets and the outreach emails.  Open each of the target customers for me and then ask me about them.  I need to rank them from best to worst and give an explanation why.  I then also need to explain what makes these emails effective or ineffective, commenting perhaps on the tone, personalization, asks, etc.)  This is not something that you, the AI, can answer for me.  This is asking about my personal judgement.  Once I’ve provided the thoughts, record them and then we will move to problem 8.

### Prompt 2 — Brian's target ranking

> Here is my ranking.  #1 Restura.  This company build high end dining facilities for senior living complexes.  I don't think I would have found this company.  AI has target this one well - the facilities are large that they will build.  They use higher end building materials.  This kind of company will absolutely be building more facilites in the future and this could be great ongoing buisnesss.  #2 is Titan Hospitality.  It is a 11 restaurant and catering hall management group in MD that appears to be pretty high and and large venue.  This a company that will probably be adding to their portfolio and would be high profile in the public and potentially lead to future business from some of their competitors as well.  #3 Glendale Dining Services.  Also an appropriate company.  As a large dining services company its another one that will result in repeat business.  They have a broader profolio, including senior living, residential facilities, and schools.  Although it may be a good customer, by the look of their website, they appear to be on a tighter budget.  Nursing home dining services aren't very sexy.

### Prompt 3 — Brian's outreach email reflection

> As for email reflections:  Restura - was very good at capturing the higher end culinary and technology highlights that go into their planning.  The body of the email seems very targeted to them.  Glendale - AI took a different approach focusing both on Singer Equipments kitchen construction capabilites and Singer's smallware (glasses, plates) and supply chain for restaurant supplies.  Titan - This email was the most vague.  It seems the most AI-like "your restaurant portfolio of... caught my attention."  This may be in part that the text available on the website did less of the informing of the consumer than did the photos of their high end restaurants.  Titan would have to be re-written to be more specific to them.   The other 2 companies could be sent as the stand.

## Problem 8: Sales dashboard webpage

### Prompt 1

> Problem 8 “Sales dashboard webpage”
> Now I want you make asmall webpage called “dashboard.html” showing my company’s profile, the target customers it selected, their profiles, contact info for each target, and the draft emails that were created for each.  This will be for easy presentation to a human manager for them to quickly skim.   Lets use that nice leather, brass, and green bank glass stylings that I like.  Make a nice layout.   Make it look like a desktop with each of the profiles on the desk like a piece of paper for each.  Put them in rank order.  Make the design really nice and realistic.  This is where we show off what AI can do.  For this step, you can use whatever AI model will produce the nicest graphics.  It does not have to be an OpenAI model.   Put the profile, targets, and meail in the HTML itself.  Copy the content into the HTML.  I do not the HTML to read the JSON file when the webpage is opened.  I want the dashboard.html page to open with all of the content with NO extra steps, so the grading Tas and prof can open this with a double-click and nothing more.  Ok go!  I know you are going to do a great job with this step.

## Problem 9: Submit zip

### Prompt 1

> Problem 9 “Submit zip”
> Place everything that we worked on in this problem set in a folder called “hw2”, zip it as “hw2.zip” So I can upload to Canvas.  DO NOT put the .env file in the zip.  Include instead “.env.example” with Portkey_API_Key / model settings shows as placeholders only.  Reference the file structure that I uploaded to you.
