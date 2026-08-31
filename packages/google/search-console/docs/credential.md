# google/search-console — Vault credential

Bind tool name **`google/search-console`** (aliases: `gsc`, `search-console`).

Read-only Search Analytics via Search Console API. Does **not** submit sitemaps or change property settings.

## Prerequisites

1. Google Cloud project with **Search Console API** enabled
2. OAuth client + refresh token with scope  
   `https://www.googleapis.com/auth/webmasters.readonly`
3. Search Console property the authorizing user can access
4. Exact **site_url** as shown in GSC (`https://example.com/` or `sc-domain:example.com`)

## Vault JSON

```json
{
  "site_url": "sc-domain:example.com",
  "client_id": "xxxxx.apps.googleusercontent.com",
  "client_secret": "GOCSPX-xxxxx",
  "refresh_token": "1//xxxxx"
}
```

Or short-lived `access_token` instead of the refresh trio.

## Agent binding

1. Vault → kind `google-search-console`
2. Bind `tool_name`: **`google/search-console`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`. Production calls `oauth2.googleapis.com/token` and `webmasters/v3/.../searchAnalytics/query`.
