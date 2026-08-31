# meta/ads-mutate

First-party connector: Meta campaign/adset/ad **status** or capped **daily_budget**.

## Behavior

- `POST /{object_id}` with `status=ACTIVE|PAUSED` or `daily_budget`
- Runtime refuses DELETE/ARCHIVED and uncapped budgets
- Owner flags gate activate + budget changes
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: create campaigns, creatives, targeting, bid strategy changes, deletes.

Binding: [credential.md](credential.md).
