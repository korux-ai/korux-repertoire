# searxng/search — Vault credential

Bind tool name `searxng/search` on the agent that runs metasearch steps.

## Prerequisites

1. Run a **SearXNG** instance you control (or a trusted private instance).
2. Enable JSON output in `settings.yml`:

```yaml
search:
  formats:
    - html
    - json
```

Public instances often return HTTP 403 for `format=json` — prefer self-hosting.

## Vault JSON

Secret kind / binding tool: `searxng/search`

```json
{
  "base_url": "https://searx.example.com",
  "api_key": "optional-bearer-or-token"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `base_url` | yes | Instance origin (no trailing path required) |
| `api_key` | no | Sent as `Authorization: Bearer …` when set |

## Invoke

- Endpoint: `GET {base_url}/search?q=…&format=json&language=…`
- Runtime keeps at most 20 results (default 10).

## Local / CI

Set `KORUX_CAPABILITY_HTTP_MOCK=1` to skip live HTTP and return deterministic mock results.

## Governor / Owner config (suggested)

| Config | Suggested use |
|--------|----------------|
| `blocked_keywords` | Block sensitive research topics (e.g. competitor scrape bans, PII hunting) |
| `max_results` | Cap discovery volume / cost of downstream crawl steps |
