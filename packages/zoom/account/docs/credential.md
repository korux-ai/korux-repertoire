# zoom — Vault credential

Bind tool name **`zoom`**.

## Prerequisites

Zoom Marketplace Server-to-Server OAuth app, or a usable access token.

## Vault JSON

```json
{
  "account_id": "placeholder",
  "client_id": "placeholder",
  "client_secret": "placeholder"
}
```

Or `{"token": "eyJ…"}`.

## Agent binding

Vault kind `zoom` → `tool_name`: **`zoom`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` skips live HTTP (`stub: true`).
