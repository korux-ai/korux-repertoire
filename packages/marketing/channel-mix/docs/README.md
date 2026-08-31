# marketing/channel-mix

Catalog **skill** (no `runtime/`). Recommends channels and which **connectors** to Propose next; does not publish.

## When to use

- After `marketing/campaign-brief`, or when NL asks “which channels?”
- Need a short mix (typically 2–4) mapped to repertoire ids

## Connector map (examples)

| Channel idea | Connector id |
|--------------|--------------|
| LinkedIn Company Page | `linkedin/publish` |
| Instagram Feed | `instagram/publish` |
| X / Facebook Page | `twitter/publish`, `facebook/publish` |
| Email blast | `mailchimp/campaign` |
| Blog / SEO | `wordpress/post` |
| Measure | `google/analytics-report` |
| CRM handoff note | `hubspot/crm-note` |

Write-external connectors stay human-gated; this skill only recommends.

No Vault binding (`auth.required=false`).
