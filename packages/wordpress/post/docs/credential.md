# wordpress/post — Vault credential

Bind tool name **`wordpress/post`** (alias `wp-post`).

Creates posts through the WordPress REST API using an **Application Password** (WordPress 5.6+). Prefer **draft** status; only set `status=publish` when intentionally going live.

## Prerequisites

1. WordPress site over **HTTPS** (http allowed only for `localhost`)
2. User with permission to create posts
3. Users → Profile → Application Passwords → create one for Korux

## Vault JSON

```json
{
  "site_url": "https://example.com",
  "username": "editor",
  "application_password": "xxxx xxxx xxxx xxxx xxxx xxxx"
}
```

Spaces in the application password are optional (runtime strips them).

## Agent binding

1. Vault → secret kind `wordpress`
2. Bind `tool_name`: **`wordpress/post`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`. Production posts to `{site_url}/wp-json/wp/v2/posts`.
