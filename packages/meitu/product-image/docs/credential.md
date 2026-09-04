# meitu/product-image — Vault credential

Bind tool name **`meitu/product-image`**.

Uses Meitu AI Open Platform **MTlab sync** cutout (`/v1/photo_scissors/sod`) with `api_key` + `api_secret` query auth.

## Prerequisites

1. Register / apply at https://ai.meitu.com/
2. Purchase or trial **智能抠图** (or equivalent) and obtain `api_key` / `api_secret`
3. Official docs hub: https://ai.meitu.com/doc/

## Vault JSON

```json
{
  "api_key": "YOUR_APPKEY",
  "api_secret": "YOUR_SECRET",
  "base_url": "https://openapi.mtlab.meitu.com"
}
```

`base_url` optional. Newer OpenAPI gateway (`open.mtlab.meitu.com` + HMAC) is out of scope for v1 — use MTlab sync keys.

## Agent binding

1. Vault → secret kind `meitu`
2. Bind `tool_name`: **`meitu/product-image`**
3. Prefer `image_file_id` + `context.image.bytes` (or https URL)

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`.
