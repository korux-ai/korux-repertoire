# webflow/cms-publish — Vault credential

Bind tool name **`webflow/cms-publish`**.

Creates a CMS collection item via Webflow Data API v2. Default is **staged** (`POST .../items`). Set invoke arg `publish=true` to create live (`POST .../items/live`).

## Prerequisites

1. Site token: https://developers.webflow.com/data/docs/get-started-site-api-access
2. Scope: `CMS:write` (and site access for the collection)
3. Collection ID from Designer → CMS → collection settings, or `GET /v2/sites/{site_id}/collections`

## Vault JSON

```json
{
  "access_token": "xxxxxxxx",
  "collection_id": "64abc..."
}
```

## Agent binding

1. Vault → secret kind `webflow`
2. Bind `tool_name`: **`webflow/cms-publish`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`. Production calls `api.webflow.com` v2.
