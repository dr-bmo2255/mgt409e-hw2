# Generated assets

Running `python sales_agent.py "<profile query>" --url <official website>` writes the verified
seller profile to `assets/company_profile.json`. Problem 5 reads this file through `--profile`;
it does not replace the profile while researching customer targets.
