# xiaohongshu/publish — Vault credential

Bind tool name **`xiaohongshu/publish`**.

Publishes an **image note** through an Owner-configured Xiaohongshu / RED **OpenAPI gateway**.  
This package does **not** automate `creator.xiaohongshu.com` web sessions.

## Prerequisites

1. Xiaohongshu open-platform / professional-account (or approved partner) access with **note publish** permission — availability is restricted; confirm against current official docs.
2. OAuth `access_token` for the publishing account
3. Confirm upload + post paths with your approved API pack (defaults are common placeholders and may need Vault overrides)

## Vault JSON

```json
{
  "access_token": "xxxxxxxx",
  "api_base": "https://open.xiaohongshu.com",
  "upload_path": "/api/sns/v1/note/image/upload",
  "post_path": "/api/sns/v1/note/post"
}
```

Override `api_base` / paths when your enterprise gateway differs.

## Agent binding

1. Vault → secret kind `xiaohongshu`
2. Bind `tool_name`: **`xiaohongshu/publish`**
3. Prefer upstream `design/template-compose` `social_post` fields (`title`, `caption`, image)

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`.
