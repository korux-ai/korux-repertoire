# linkedin/publish — Vault credential

Bind tool name **`linkedin/publish`** on the agent that posts to a LinkedIn **Company Page**.

Personal profile posts are out of scope. Do not store personal `urn:li:person:…` as the author.

## Prerequisites

1. LinkedIn Developer app with access to the **Community Management** / Posts APIs: https://www.linkedin.com/developers/
2. OAuth 2.0 token with **`w_organization_social`** (and typically `r_organization_social`)
3. A Company Page where the authenticated member has a role that can post
4. Numeric **organization id** (Company Page id), not the vanity URL slug

## Vault JSON

```json
{
  "access_token": "AQX-placeholder",
  "organization_id": "12345678",
  "linkedin_version": "202503"
}
```

| Field | Notes |
|-------|--------|
| `access_token` | Member OAuth access token with organization posting scopes |
| `organization_id` | Numeric Page id (or `urn:li:organization:…`; runtime strips the prefix) |
| `linkedin_version` | Optional `LinkedIn-Version` header `YYYYMM` (default `202503`) |

Do not commit real tokens.

## Agent binding

1. Capabilities / Vault → create secret kind `linkedin`
2. Bind to the agent with `tool_name`: **`linkedin/publish`**

## Local / CI

Set `KORUX_CAPABILITY_HTTP_MOCK=1` to skip live HTTP (`stub: true`). Production leaves this unset — invoke calls LinkedIn `/rest/posts` (and `/rest/images` when posting an image).
