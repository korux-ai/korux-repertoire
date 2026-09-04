# meitu/product-image

First-party connector: Meitu **智能抠图** for product photos (mainland SMB workflow).

## Behavior

- `POST /v1/photo_scissors/sod?api_key=&api_secret=`
- Input: workspace image bytes (base64) or https URL
- Output: result URL(s) or data URI
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: HMAC OpenAPI gateway, virtual try-on, video, beauty-only portraits (use Meitu beauty APIs separately later).

Binding: [credential.md](credential.md).
