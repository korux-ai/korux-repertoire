# wordpress/post

First-party connector: create a WordPress post via REST + Application Password.

## Behavior

- `POST /wp-json/wp/v2/posts`
- Default `status=draft`; `publish` / `pending` / `private` allowed
- HTTPS required except localhost
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: media upload, pages, custom post types, plugins, multisite admin.

Binding: [credential.md](credential.md).
