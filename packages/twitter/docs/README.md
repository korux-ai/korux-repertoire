# twitter

First-party connector: post one X (Twitter) tweet. Copy is required; one JPEG/PNG is optional.

## Behavior

- No image: `POST /2/tweets`
- With image: `POST upload.twitter.com/1.1/media/upload.json`, then tweet with `media_ids`
- `writes_external`: human approval by default; empty body reject
- Images only via platform-injected `context.image` (from `image_file_id`); no public URL fetch, no base64

## invoke

`runtime.entry` = `runtime.invoke`

```text
async def invoke(args, secret, context) -> dict
```

- `args.content` required; `args.image_file_id` optional
- `secret`: `api_key` / `api_secret` / `access_token` / `access_token_secret`
- Flat success: `ok`, `stub`, `tweet_id`, `content` / `summary`
- `KORUX_CAPABILITY_HTTP_MOCK=1` skips the network and returns `stub: true`

Out of scope: multi-image, GIF/video, threads, replies, delete, timeline, read/reply comments.

Binding and signup: [credential.md](credential.md).
