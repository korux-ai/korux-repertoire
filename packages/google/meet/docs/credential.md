# google/meet — Vault credential

Bind tool name **`google/meet`** (alias `google-meet`).

Verifies Google identity for Meet-related workflows via **OAuth 2.0 userinfo** (same pattern as Zoom identity check). Does **not** create Google Meet conferences.

## Prerequisites

1. Google Cloud OAuth client (Desktop or Web)
2. Refresh token with at least `openid` / `email` / `profile` (userinfo) scopes  
   Optional Meet/Calendar scopes can be added later for richer meeting ops
3. Or a short-lived `access_token` with the same scopes

## Vault JSON (recommended)

```json
{
  "client_id": "xxxxx.apps.googleusercontent.com",
  "client_secret": "GOCSPX-xxxxx",
  "refresh_token": "1//xxxxx"
}
```

Or:

```json
{
  "access_token": "ya29.xxxxx"
}
```

`secret_kind` remains `google-meet` for Vault compatibility with older bindings.

## Agent binding

1. Vault → kind `google-meet`
2. Bind `tool_name`: **`google/meet`** (or alias `google-meet`)

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`. Production calls `oauth2.googleapis.com/token` (when refreshing) and `googleapis.com/oauth2/v3/userinfo`.
