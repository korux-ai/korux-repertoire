# meta/ads-mutate — Vault credential

Bind tool name **`meta/ads-mutate`**.

Spend-affecting writes: **ACTIVE/PAUSED** status, optional **daily_budget** (Owner-capped). **No DELETE/ARCHIVED**.

## Prerequisites

1. Meta Marketing API token with `ads_management`
2. Prefer reading ids via `meta/ads-insights` first

## Vault JSON

```json
{
  "access_token": "EAAG-placeholder"
}
```

## Owner gates (recommended)

- `allow_activate` default **false** (pause-only until enabled)
- `allow_budget_change` default **false**
- `max_daily_budget` default `50000` minor units

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`.
