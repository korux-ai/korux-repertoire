# youtube/publish — Vault credential

Bind tool name **`youtube/publish`**.

Uploads a video via YouTube Data API v3 **resumable** `videos.insert`. Default `privacy_status=unlisted`.

## Prerequisites

1. Google Cloud project with YouTube Data API v3 enabled
2. OAuth token with scope `https://www.googleapis.com/auth/youtube.upload`
3. Unverified apps may force uploads to **private** until Google verification

## Vault JSON

```json
{
  "access_token": "ya29.xxxxxxxx"
}
```

## Agent binding

1. Vault → secret kind `youtube`
2. Bind `tool_name`: **`youtube/publish`**
3. Korux must inject `context.video.bytes` from `video_file_id`

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`.
