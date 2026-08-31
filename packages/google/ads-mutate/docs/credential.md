# google/ads-mutate — Vault credential

Bind tool name **`google/ads-mutate`**.

Spend-affecting writes: campaign **ENABLED/PAUSED**, optional campaign budget **amount_micros** (Owner-capped). **No REMOVED**.

## Prerequisites

1. Google Ads API access + **developer token**
2. OAuth token with Google Ads scopes
3. Customer id (digits); optional manager `login_customer_id`

## Vault JSON

```json
{
  "access_token": "ya29.xxx",
  "developer_token": "xxxx",
  "customer_id": "1234567890",
  "login_customer_id": ""
}
```

## Owner gates (recommended)

- `allow_enable` default **false**
- `allow_budget_change` default **false**
- `max_amount_micros` default `500000000` (500 currency units)

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`.
