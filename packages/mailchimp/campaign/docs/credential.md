# mailchimp/campaign — Vault credential

Bind tool name **`mailchimp/campaign`**.

Creates a **regular** audience campaign via the Mailchimp Marketing API. Default invoke **does not send**; it creates the campaign and sets HTML content. Sending requires `action=send` or `action=create_and_send` (still human-gated).

## Prerequisites

1. Mailchimp account with Marketing API access: https://mailchimp.com/developer/
2. API key from Account → Extras → API keys (format `…-us21`; datacenter suffix required)
3. Audience **list id** (Audience → Settings → Audience name and defaults)

## Vault JSON

```json
{
  "api_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-us21",
  "list_id": "a1b2c3d4e5",
  "from_name": "Acme Marketing",
  "reply_to": "hello@example.com"
}
```

Optional `server_prefix` if your key has no `-dc` suffix.

## Agent binding

1. Vault → secret kind `mailchimp`
2. Bind `tool_name`: **`mailchimp/campaign`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` returns `stub: true`. Production leaves unset — real calls to `{dc}.api.mailchimp.com/3.0`.
