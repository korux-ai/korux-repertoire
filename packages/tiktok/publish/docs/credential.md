# tiktok/publish — Vault credential

Bind tool name **`tiktok/publish`**.

Uses TikTok Content Posting API. Default **inbox** upload (`video.upload`) so the creator finishes in-app. Optional **direct** post (`video.publish`) when Owner allows.

## Prerequisites

1. TikTok developer app with Content Posting API access
2. OAuth token with `video.upload` (inbox) and/or `video.publish` (direct)
3. For `video_url` / `PULL_FROM_URL`: verify URL prefix with TikTok

## Vault JSON

```json
{
  "access_token": "act.xxxxxxxx"
}
```

## Agent binding

1. Vault → secret kind `tiktok`
2. Bind `tool_name`: **`tiktok/publish`**
3. For FILE_UPLOAD, Korux injects `context.video.bytes` from `video_file_id`

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`.
