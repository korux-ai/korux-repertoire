# instagram/publish

First-party connector: one **Instagram Feed** image post on a professional account linked to a Facebook Page.

## Behavior

- Caption required; **image required** (fail-closed without `image_file_id` / `context.image`)
- Graph `v21.0`: create media container → (optional status poll) → `media_publish`
- Image URL: `context.image.public_url` **or** unpublished Facebook Page photo staging from bytes
- Separate Vault / `binding_tool` from `facebook/publish`
- `writes_external` + human approval by default

## invoke

`runtime.entry` = `runtime.invoke`

- `args.caption`, `args.image_file_id` required
- `secret`: `ig_user_id`, `page_access_token`, `page_id`
- Success: `ok`, `stub: false`, `media_id`, `content` / `summary`

Out of scope: personal IG, Stories, Reels, carousels, shopping tags, comments.

Binding: [credential.md](credential.md).
