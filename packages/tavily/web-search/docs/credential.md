# tavily/web-search — Vault credential

Bind tool name `tavily/web-search` on the agent that runs search steps.

## Tavily API key (recommended)

JSON:

```json
{
  "api_key": "tvly-xxxxxxxx",
  "provider": "tavily"
}
```

## Optional fields

| Field | Description |
|-------|-------------|
| `base_url` | Override Tavily API base (default `https://api.tavily.com`) |
| `provider` | Must be `tavily` (only provider in v1.1.0) |

## Local / CI

Set `KORUX_CAPABILITY_HTTP_MOCK=1` or `WEB_RESEARCH_MOCK=true` to skip live HTTP and return deterministic mock snippets.
