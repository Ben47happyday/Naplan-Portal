---
name: campaign-report
description: Generate a campaign send report (delivery, opens, clicks, with automated-scanner-vs-human signal analysis) for a specific marketing campaign, reading directly from the production Supabase database, and publish it as an Artifact. Use when asked to report on, review, check results of, or see how a marketing campaign performed.
---

# Campaign report

Produces the same report format as the first "Batch 1" campaign report: a
polished HTML page (NAPLAN Prep Hub / Zcube visual language) showing
delivery counts, raw open/click events, and — critically — whether those
events look like genuine human engagement or automated mail-security
scanning, then publishes it as an Artifact.

## Steps

1. **Get the campaign to report on.** If the user already named a
   `campaign_id` or an exact/partial campaign name in their request, use
   that. Otherwise ask which campaign — offer to list recent ones first if
   they don't know the ID:
   ```
   python .claude/skills/campaign-report/generate_report.py --list
   ```
2. **Generate the report.** Run:
   ```
   python .claude/skills/campaign-report/generate_report.py --campaign-id <ID> --out <tmp-file>.html
   ```
   (or `--campaign-name "<exact or partial name>"` instead of `--campaign-id`
   if that's what the user gave you). The script connects to the production
   Supabase database via `database/config.py` (needs `DATABASE_URL` set —
   same as `marketing/send_campaign.py`), pulls the campaign, every send,
   every receiver, and every open/click event, classifies each event as
   `engaged` / `proxy_open` (e.g. Gmail's image proxy) / `bot` (spam-scanner
   user-agent, private-range IP paired with a non-browser UA, or a click
   timestamped before that same send's open) / or `no_events`, and writes a
   ready-to-publish HTML file to the path given.
3. **Publish it** with the Artifact tool (`file_path` = the `--out` path from
   step 2, a title like "Batch N Send Report" or the campaign's own name,
   favicon 📊). Do not hand-edit the generated HTML's data — if a number
   looks wrong, fix the query/classification logic in
   `generate_report.py`, not the output file.
4. **Summarize the key finding in chat** the same way the first report did:
   lead with whether any engagement is real or automated, not just raw
   counts — that's the part a bare stats table hides.

## Notes

- The script is read-only — it never writes to the database, only queries it.
- Campaign names in this project sometimes contain non-ASCII em dashes
  (`—`) that display as `�` in some terminals; that's a display artifact of
  the console codepage, not a data problem — don't try to fix it.
- If `--list` or the report shows no campaigns, `DATABASE_URL` probably
  isn't set in this environment's `.env` — see `marketing/README.md` /
  `database/config.py` for how it's configured.
- For context on what "good" looks like for a batch (bounce thresholds,
  warm-up pacing, when to send the next batch), see
  `marketing/DELIVERABILITY_PLAN.md` — the report's "next steps" section
  already reflects that plan, but re-read it if the user asks something the
  report doesn't cover.
