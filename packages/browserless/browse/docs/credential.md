# browserless/browse — Vault credential

Bind tool name `browserless/browse` on agents that need headless Chrome rendering.

## Prerequisites

1. Browserless Cloud account **or** a self-hosted Browserless/Chrome CDP HTTP gateway that exposes `POST /content`.
2. API token from the Browserless dashboard (cloud).

Docs: https://docs.browserless.io/rest-apis/content

## Vault JSON

Secret kind / binding tool: `browserless/browse`

```json
{
  "base_url": "https://production-sfo.browserless.io",
  "api_key": "YOUR_BROWSERLESS_TOKEN"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `base_url` | yes | Origin only (no `/content` path) |
| `api_key` | yes | Query `token=` (and Bearer header) |

Self-hosted example:

```json
{
  "base_url": "http://browserless.internal:3000",
  "api_key": "unused-if-open"
}
```

If your self-host does not require a token, still set a non-empty placeholder string so Vault validation passes, or fork the package.

## Invoke

- `POST {base_url}/content?token=…` (+ optional `stealth=true`)
- Body: `{ "url": "https://…" }`
- Response: raw HTML (truncated by `max_chars`)

## Local / CI

Set `KORUX_CAPABILITY_HTTP_MOCK=1` for deterministic mock HTML.

## Governor / Owner config (suggested)

| Config | Suggested use |
|--------|----------------|
| `blocked_url_hosts` | Mandatory SSRF guard (localhost, 169.254.169.254, intranet) |
| `max_content_length` | Cap HTML before LLM |
| `require_human_confirm` | Turn on when browser minutes are billed tightly (pair with platform gate / Track B) |
