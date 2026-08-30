# twitter — Vault credential

Bind tool name `twitter` on the agent that posts to X.

User-context OAuth 1.0a is required. App-only Bearer cannot post tweets.

## Prerequisites

1. X Developer Portal account: https://developer.x.com/
2. Project + App with **User authentication** and Read and Write
3. User token scopes / permissions include **tweet.write** and **media.write**

## Vault JSON

```json
{
  "api_key": "your-consumer-key",
  "api_secret": "your-consumer-secret",
  "access_token": "your-access-token",
  "access_token_secret": "your-access-token-secret"
}
```

Do not store a User token under another connector, and do not commit real keys.

## Agent binding

1. Vault → create secret kind `twitter`
2. Bind to the agent with `tool_name`: **`twitter`** (alias `x` resolves to the same capability)

## Local / CI

Set `KORUX_CAPABILITY_HTTP_MOCK=1` to skip live HTTP (`stub: true`). Production leaves this unset.
