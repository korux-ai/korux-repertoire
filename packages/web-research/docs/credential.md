# web-research — Vault credential

Bind tool name `web-research` on the agent that runs search steps.

## Tavily API key (recommended)

JSON:

```json
{
  "api_key": "tvly-xxxxxxxx",
  "provider": "tavily"
}
```

Or paste the bare API key as the secret value.

## Optional fields

| Field | Description |
|-------|-------------|
| `base_url` | Override Tavily API base (default `https://api.tavily.com`) |
| `provider` | Must be `tavily` (only provider in v1.0.0) |

## Local / CI

Set `WEB_RESEARCH_MOCK=true` (default) to skip live HTTP and return deterministic mock snippets.
