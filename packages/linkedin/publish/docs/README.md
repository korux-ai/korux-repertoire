# linkedin/publish

First-party connector: post once to a **LinkedIn Company Page**. Copy is required; one JPEG/PNG is optional.

## Behavior

- Text: LinkedIn Posts API `POST /rest/posts` with `author=urn:li:organization:{id}`
- With image: Images API `initializeUpload` → binary `PUT` → post with `content.media.id`
- `writes_external`: human approval by default; empty commentary reject
- Images only via platform-injected `context.image` bytes; no public URL fetch, no base64
- Requires `w_organization_social` OAuth; personal profile posting is out of scope

## invoke

`runtime.entry` = `runtime.invoke`

```text
async def invoke(args, secret, context) -> dict
```

- `args.commentary` required; `args.image_file_id` optional
- `secret`: `access_token`, `organization_id`, optional `linkedin_version`
- Flat success: `ok`, `stub: false`, `post_id`, `content` / `summary`
- `KORUX_CAPABILITY_HTTP_MOCK=1` skips the network and returns `stub: true`

Out of scope: personal profile, multi-image, video, documents, polls, comments, ads.

Binding and signup: [credential.md](credential.md).
