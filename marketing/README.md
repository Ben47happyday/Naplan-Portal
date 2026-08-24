# Marketing email campaign runner

General-purpose, manually-triggered outreach tool. It never sends on its own —
you run it from the command line, and it defaults to a **dry run** (preview
only) unless you pass `--send`. Sending also requires typing `SEND` at an
interactive confirmation prompt.

Sends via **Microsoft Graph's `sendMail` API** using an app-only OAuth2
token (client credentials grant) — not SMTP. This is the modern, supported
way to send as a Microsoft 365 mailbox (like `support@zcube.com.au`) when
SMTP AUTH app passwords aren't available on the tenant, and it isn't
affected by Conditional Access "block legacy authentication" policies.

## Setup

### 1. Register an app in Microsoft Entra (one-time, needs a zcube.com.au M365 admin)

1. Go to [entra.microsoft.com](https://entra.microsoft.com) → **App registrations** → **New registration**.
2. Name it something identifiable, e.g. `naplan-marketing-mailer`. Leave the
   default "single tenant" account type. Register.
3. Note the **Application (client) ID** and **Directory (tenant) ID** shown
   on the app's Overview page — these go in `config.json` under `auth`.
4. Left menu → **Certificates & secrets** → **New client secret** → give it
   a description and an expiry (e.g. 12 months — you'll need to rotate it
   before it expires) → Add. **Copy the secret value immediately** — it's
   only shown once. This is what goes in `scret.txt` (step 2 below) —
   never in `config.json`.
5. Left menu → **API permissions** → **Add a permission** → **Microsoft
   Graph** → **Application permissions** (not Delegated) → search for
   `Mail.Send` → add it.
6. Still on API permissions, click **Grant admin consent for zcube.com.au**
   (requires admin rights) — without this the app can't send anything.
7. **Important — restrict which mailbox it can send as.** By default an app
   with the `Mail.Send` application permission can send as *any* mailbox in
   the tenant, which is far more blast radius than this script needs. Scope
   it down to just `support@zcube.com.au` using Exchange Online PowerShell:
   ```powershell
   Connect-ExchangeOnline
   New-ApplicationAccessPolicy -AppId "<client-id-from-step-3>" `
     -PolicyScopeGroupId "support@zcube.com.au" `
     -AccessRight RestrictAccess `
     -Description "Restrict naplan-marketing-mailer to support@zcube.com.au"
   ```
   Then verify it's actually enforced:
   ```powershell
   Test-ApplicationAccessPolicy -AppId "<client-id>" -Identity "support@zcube.com.au"   # should say Granted
   Test-ApplicationAccessPolicy -AppId "<client-id>" -Identity "someone.else@zcube.com.au"  # should say Denied
   ```

### 2. Configure this script

1. Copy `config.example.json` to `config.json` and fill in:
   - `auth.tenant_id` / `auth.client_id` from step 3 above
   - `sender.email` / `sender.name` / `sender.reply_to`
   - `business.name` / `business.address` (required for the compliance
     footer — Australia's Spam Act requires commercial emails to identify
     the sender and their address)
   - `campaign.csv_path`, `campaign.name_column`, `campaign.email_column` —
     point at any lead list, not just the NAPLAN one, as long as it has a
     name column and an email column
   - `campaign.learn_more_url` — the live NAPLAN portal URL the email's
     "Learn more" button links to
2. Put the client secret (from step 4 above) in a plain text file — default
   path is `scret.txt` next to the script (override with `--secret-file`).
   It's read fresh from disk on every run and never written anywhere else
   (not into `config.json`, not logged, not cached). Keep it out of git —
   it's already in `.gitignore`.
3. Edit `email_template.html` to change the message. It's an HTML email
   (table-based layout, inline styles, styled to match the NAPLAN Prep Hub
   portal — cream/orange theme, fox mascot) with a "Learn more" button.
   Available placeholders: `{agent_name}`, `{sender_name}`, `{reply_to}`,
   `{business_name}`, `{business_address}`, `{learn_more_url}`.

## Usage

```
# Preview everything that would be sent (no network calls, no emails sent)
python send_campaign.py --config config.json

# Preview just the first 3, written to a file for review
python send_campaign.py --config config.json --limit 3 --preview-out preview.txt

# Actually send (prompts for a typed "SEND" confirmation)
python send_campaign.py --config config.json --send

# Re-run later: already-sent addresses (from sent_log.csv) are skipped automatically
python send_campaign.py --config config.json --send

# Force resending to everyone, ignoring the sent log (suppression list still applies)
python send_campaign.py --config config.json --send --resend

# Add someone who asked not to be contacted again
python send_campaign.py --config config.json --add-unsubscribe someone@example.com
```

## Notes

- `sent_log.csv`, `unsubscribe_list.csv`, and `scret.txt` are created/updated
  next to this script and are excluded from git via `.gitignore` (along with
  `config.json`, since it can contain your sender identity).
- The CSV loader tolerates messy scraped-lead cells (e.g. `"foo@bar.com
  (general: baz@bar.com)"` or `"Not published - see https://..."`) and
  extracts the first valid email address, skipping rows with none.
- `campaign.delay_seconds` throttles sends to avoid tripping Microsoft's
  outbound rate limits / spam heuristics for the mailbox.
- The client secret expires (per whatever you picked in step 4 of the Entra
  setup) and will need rotating in Entra + updating `scret.txt` before then,
  or sends will start failing with a token error.
- If a send fails with `403 ErrorAccessDenied` or similar, the most likely
  causes are: admin consent wasn't granted for `Mail.Send` (step 6), or the
  Application Access Policy (step 7) is scoping the app to a different
  mailbox than `sender.email` in `config.json`.
