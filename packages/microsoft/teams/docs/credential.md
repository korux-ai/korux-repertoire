# microsoft/teams — Vault credential

Bind tool name **`microsoft/teams`** (alias `microsoft-teams`).

Verifies Microsoft identity for Teams-related workflows via **Microsoft Graph**. Does **not** create Teams meetings.

## Prerequisites

**Option A — delegated / bearer token**

1. Access token with Graph permission to call `GET /v1.0/me` (e.g. `User.Read`)

**Option B — app-only (client credentials)**

1. Azure AD app registration
2. Application permission such as `Organization.Read.All` (admin consent)
3. Tenant id + client id + client secret

## Vault JSON

App-only:

```json
{
  "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "client_secret": "xxxxx"
}
```

Or bearer:

```json
{
  "access_token": "eyJ…"
}
```

`secret_kind` remains `microsoft-teams` for Vault compatibility.

## Agent binding

1. Vault → kind `microsoft-teams`
2. Bind `tool_name`: **`microsoft/teams`** (or alias `microsoft-teams`)

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`. Production calls `login.microsoftonline.com` (app-only) and `graph.microsoft.com`.
