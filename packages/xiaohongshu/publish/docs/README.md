# xiaohongshu/publish

First-party connector: Xiaohongshu image note via **configured OpenAPI** (not creator-web scraping).

## Behavior

- Optional multipart image upload, then note post
- Inputs: `title`, `caption`, `image_file_id` / `image_url`, optional `topics`
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: cookie/X-S signed creator web API, video notes, live commerce.

Binding: [credential.md](credential.md).
