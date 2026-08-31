# meta/ads-insights — Vault credential

Bind tool name **`meta/ads-insights`** (aliases: `meta-ads`, `facebook-ads-insights`).

**Read-only** Marketing API insights. Does **not** create ads, change bids, or pause campaigns.

## Prerequisites

1. Meta app with Marketing API access: https://developers.facebook.com/
2. System user or user token with `ads_read` (and access to the ad account)
3. Ad account id (`act_123…` or numeric)

## Vault JSON

```json
{
  "access_token": "EAAG-placeholder",
  "ad_account_id": "act_1234567890"
}
```

## Agent binding

Vault kind `meta-ads` → `tool_name`: **`meta/ads-insights`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`. Production calls `graph.facebook.com/.../insights`.
