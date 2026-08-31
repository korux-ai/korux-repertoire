# canva/design-export — Vault credential

Bind tool name **`canva/design-export`**.

Exports a design via Canva Connect API. Optional Brand Template **autofill** (Enterprise) before export.

## Prerequisites

1. Canva Connect integration + OAuth (PKCE) access token
2. Scopes typically include `design:content:read` (export) and `design:content:write` + brand template scopes for autofill
3. Autofill requires Brand Templates / Enterprise access

## Vault JSON

```json
{
  "access_token": "xxxxxxxx"
}
```

## Agent binding

1. Vault → secret kind `canva`
2. Bind `tool_name`: **`canva/design-export`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`.
