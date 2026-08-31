# instagram/publish — Vault credential

Bind tool name **`instagram/publish`**. Do **not** reuse the `facebook/publish` Vault binding — keep secrets and `binding_tool` separate even though both use Meta Graph.

Only **Instagram professional accounts** linked to a Facebook Page are supported (Feed image posts).

## Prerequisites

1. Meta developer app: https://developers.facebook.com/
2. Facebook Page linked to an Instagram professional account
3. Long-lived **Page access token** with permissions such as:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement` / `pages_manage_posts` (needed when uploading bytes via an unpublished Page photo)
4. Instagram user id (`ig_user_id`) from `GET /{page-id}?fields=instagram_business_account`

## Vault JSON

```json
{
  "ig_user_id": "17841400000000000",
  "page_access_token": "EAAG-placeholder",
  "page_id": "000000000000000"
}
```

| Field | Notes |
|-------|--------|
| `ig_user_id` | Instagram professional account id |
| `page_access_token` | Page token with IG content publish scopes |
| `page_id` | Linked Facebook Page id (used to stage image bytes when no public URL) |

## Image injection

Meta Feed publishing needs a fetchable `image_url`. Runtime behavior:

1. If Korux injects `context.image.public_url` (`https://…`), that URL is used.
2. Else if `context.image.bytes` is present, the package uploads an **unpublished** photo to `page_id`, reads Graph `images[].source`, then creates + publishes the IG container.

Do not pass arbitrary public URLs in args (no URL fetch from step input).

## Agent binding

1. Vault → create secret kind `instagram`
2. Bind with `tool_name`: **`instagram/publish`**

## Local / CI

Set `KORUX_CAPABILITY_HTTP_MOCK=1` for offline tests (`stub: true`). Production leaves this unset.
