# facebook — Vault credential

Bind tool name `facebook` on the agent that posts to a Facebook Page.

A **long-lived Page access token** is required. Do not use a User access token as the posting credential.

## Prerequisites

1. Facebook developer app: https://developers.facebook.com/
2. A Facebook Page the user manages
3. Graph permissions typically include `pages_manage_posts` and `pages_read_engagement` (plus `pages_show_list` to list Pages)

## Exchange User token → Page token

1. Obtain a User token with Page permissions (Facebook Login / Graph Explorer).
2. `GET /v21.0/me/accounts` with that User token.
3. Copy the target Page `id` and its `access_token`.
4. Optionally exchange for a long-lived Page token via Facebook token endpoint. Store **only** the Page token in Vault.

## Vault JSON

```json
{
  "page_id": "000000000000000",
  "page_access_token": "EAAG-placeholder"
}
```

Do not commit real tokens.

## Agent binding

1. Vault → create secret kind `facebook`
2. Bind to the agent with `tool_name`: **`facebook`**

## Local / CI

Set `KORUX_CAPABILITY_HTTP_MOCK=1` to skip live HTTP (`stub: true`). Production leaves this unset.
