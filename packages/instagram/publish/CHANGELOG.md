# Changelog

## 1.0.0

- First-party Instagram professional Feed post (caption + required JPEG/PNG)
- Package `runtime.invoke` via Graph Content Publishing (real HTTPS; mock only when `KORUX_CAPABILITY_HTTP_MOCK=1`)
- Image via `context.image.public_url` or unpublished Page photo staging from bytes
- Owner governor: blocked keywords / hosts / max chars; empty image reject
