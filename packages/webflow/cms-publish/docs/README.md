# webflow/cms-publish

First-party connector: create a Webflow CMS collection item (staged by default).

## Behavior

- `POST /v2/collections/{collection_id}/items` (default)
- `POST /v2/collections/{collection_id}/items/live` when `publish=true`
- `field_data` merges with required `name` + `slug`
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: asset upload, collection schema changes, site-wide publish, locales bulk.

Binding: [credential.md](credential.md).
