# youtube/publish

First-party connector: upload a channel video (resumable Data API v3).

## Behavior

- Init `POST .../upload/youtube/v3/videos?uploadType=resumable`
- PUT binary to `Location`
- Default privacy **unlisted**; `public` is Owner-gated via `allow_public`
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: thumbnails, playlists, captions, live, comments, analytics.

Binding: [credential.md](credential.md).
