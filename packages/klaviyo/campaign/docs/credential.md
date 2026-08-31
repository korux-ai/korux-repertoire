# klaviyo/campaign — Vault credential

Bind tool name **`klaviyo/campaign`**.

Creates an email campaign via Klaviyo Campaigns + Templates APIs. Default invoke **does not send**.

## Prerequisites

1. Klaviyo Private API key with `campaigns:write` and `templates:write`
2. A list (or segment usable as included audience) id
3. Verified from email / label

## Vault JSON

```json
{
  "api_key": "pk_xxxxx",
  "list_id": "AbC123",
  "from_email": "hello@example.com",
  "from_label": "Acme",
  "revision": "2024-10-15"
}
```

## Agent binding

Vault kind `klaviyo` → `tool_name`: **`klaviyo/campaign`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`. Production calls `a.klaviyo.com`.
