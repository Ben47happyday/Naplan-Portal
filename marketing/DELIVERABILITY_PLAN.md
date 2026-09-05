# Marketing email deliverability plan

Purpose: keep campaign emails out of resellers' junk/spam folders. This is the
single source of truth for what "safe to send" means — `send_campaign.py`
runs an automated preflight check against the items marked **[auto-checked]**
before every real `--send`, and refuses to send if any of them fail.

## 1. Domain authentication (DNS)

| Item | Status | Detail |
|---|---|---|
| SPF | ✅ Done **[auto-checked]** | `v=spf1 include:spf.protection.outlook.com -all` on the sending domain |
| DKIM | ⬜ Pending **[auto-checked]** | `selector1._domainkey.<domain>` / `selector2._domainkey.<domain>` CNAMEs must resolve. Enable in Microsoft 365 Defender portal → Email & collaboration → Policies → Email authentication settings → DKIM, then publish the two CNAMEs it generates. |
| DMARC | ⬜ Pending **[auto-checked]** | `_dmarc.<domain>` TXT record must exist. Start with `v=DMARC1; p=none; rua=mailto:support@zcube.com.au; fo=1`, monitor for 1–2 weeks, then tighten to `p=quarantine` then `p=reject`. |

Without all three, mailbox providers have no way to verify the message wasn't
spoofed — this is the single biggest lever on junk placement, so the
preflight check hard-blocks sending until DKIM and DMARC are live (SPF is
already confirmed).

## 2. Sending volume / warm-up

| Item | Status | Detail |
|---|---|---|
| Per-run send limit | ✅ Enforced **[auto-checked]** | `campaign.max_send_per_run` in config (default 15). A brand-new sending domain blasting a full cold list at once is itself a spam signal — ramp up gradually rather than raising this in one step. |
| Suggested ramp | Manual | Day 1: 5–10 sends. Day 3: 15–20. Day 6: 30–40. Day 10+: remaining list — only if no bounce/complaint spike between steps. |
| Inter-message delay | ✅ Enforced | `campaign.delay_seconds` (default 5s) between sends within a run. |

## 3. Recipient restriction (separate from deliverability, but a related send-time gate)

| Item | Status | Detail |
|---|---|---|
| Send authorization | ✅ Enforced **[auto-checked]** | `ALLOWED_SEND_RECIPIENTS` hard-blocks `--send` to anyone outside the currently-authorized list. Lifted only on the user's explicit instruction. |

## 4. List hygiene

| Item | Status | Detail |
|---|---|---|
| Email verification | ⬜ Manual, recommended before first real batch | Run the lead list through a verification service (NeverBounce, ZeroBounce, Kickbox) to catch addresses that will hard-bounce — hard bounces are one of the most damaging signals to sender reputation. |
| Suppression list honored | ✅ Enforced | `unsubscribe_list.csv` checked before every send; add via `--add-unsubscribe`. |
| Informal opt-outs | Manual | Watch replies for "remove me" / "stop emailing" phrasing, not just the literal word "unsubscribe" — add those manually too. |
| Segment pausing | Manual | If one region/source batch shows notably worse engagement or more complaints after a send, pause that segment before continuing. |

## 5. Content / message construction

| Item | Status | Detail |
|---|---|---|
| Compliance footer (sender identity, address, unsubscribe) | ✅ Present **[auto-checked]** | Required under Australia's Spam Act 2003. Preflight checks `business.address`/`sender.name` aren't left as placeholder text. |
| Plain-text alternative | ⬜ Built, not yet active | `email_template.txt` exists and is rendered, but Graph's `sendMail` action can't attach it (HTML-only body) — needs the `Mail.ReadWrite` permission decision (see `README.md` notes) to switch to the raw-MIME send path. |
| `List-Unsubscribe` header | ⬜ Same blocker as above | Confirmed live that Graph's `sendMail` rejects non-`X-` custom headers; needs the same raw-MIME path. |
| Avoid spam-trigger content | Manual | No ALL CAPS subject lines, excessive exclamation marks, "free money"-style phrasing, or link-heavy bodies. Current template is copy-reviewed and short by design. |

## 6. Post-send monitoring

| Item | Status | Detail |
|---|---|---|
| Track opens/clicks | ✅ Available | Query `dbo.campaign_opens` / `dbo.campaign_clicks` after each batch. Zero opens across a batch is a signal to pause and investigate before sending more. |
| Track bounces/failures | ✅ Available | `dbo.campaign_sends.status = 'failed'` plus `sent_log.csv` — investigate any spike before continuing. |

## How the preflight check is used

Every real `--send` run prints a checklist report (✅/❌ per item) before
prompting for the `SEND` confirmation. Any ❌ aborts the run with a message
pointing back to the relevant section above. This file is what to update —
and what to re-read — whenever a check needs to change (e.g., once DKIM/DMARC
go live, or the warm-up ramp is far enough along to raise
`max_send_per_run`).
