# meta/ads-insights

First-party **read-only** Meta Ads insights connector.

## Behavior

- `GET /v21.0/act_{id}/insights`
- Defaults: `date_preset=last_7d`, `level=campaign`
- Formats spend/clicks plus purchase/lead CPA hints from `cost_per_action_type`

Out of scope: create/edit ads, budgets, creatives, Audiences.

Binding: [credential.md](credential.md).
