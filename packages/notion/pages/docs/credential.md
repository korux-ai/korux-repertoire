# notion — Vault credential

Bind tool name **`notion`**.

## Prerequisites

1. https://www.notion.so/my-integrations → New integration (Internal) → copy token
2. Share a parent page with that integration (··· → Connections)
3. Copy the 32-character page id from the parent page URL

## Vault JSON

```json
{
  "token": "ntn_placeholder",
  "parent_page_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "database_id": ""
}
```

## Agent binding

Vault kind `notion` → bind `tool_name`: **`notion`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` skips live HTTP (`stub: true`).
