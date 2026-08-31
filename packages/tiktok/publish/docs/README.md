# tiktok/publish

First-party connector: TikTok Content Posting (inbox draft default).

## Behavior

- Inbox: `POST /v2/post/publish/inbox/video/init/` then PUT file
- Direct: `POST /v2/post/publish/video/init/` with `post_info` (privacy starts `SELF_ONLY`)
- `PULL_FROM_URL` when `video_url` is set without local bytes
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: photo posts, music library, analytics, status polling UI.

Binding: [credential.md](credential.md).
