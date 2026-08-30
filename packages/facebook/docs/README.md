# facebook

First-party connector: post once to a **Facebook Page**. Copy is required; one JPEG/PNG is optional.

## Behavior

- No image: Graph `v21.0` `POST /{page-id}/feed`
- With image: `POST /{page-id}/photos` (`caption` = copy)
- `writes_external`: human approval by default; empty body reject
- Images only via platform-injected `context.image`; no public URL fetch, no base64
- Credential must be a **long-lived Page token**; do not post with a User token

## invoke

`runtime.entry` = `runtime.invoke`

```text
async def invoke(args, secret, context) -> dict
```

- `args.message` required; `args.image_file_id` optional
- `secret`: `page_id` / `page_access_token`
- Flat success: `ok`, `stub`, `post_id`, `content` / `summary`
- `KORUX_CAPABILITY_HTTP_MOCK=1` skips the network and returns `stub: true`

Out of scope: personal timeline, albums, video, comments, ads, Instagram.

Binding and signup: [credential.md](credential.md).
