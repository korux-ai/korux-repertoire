# crawl4ai/fetch — Vault credential

Bind tool name `crawl4ai/fetch` on agents that fetch full page markdown.

## Prerequisites

1. Run the official Crawl4AI Docker/HTTP server (default port `11235`).
2. Confirm `POST /md` is reachable from the Korux host.

Example:

```bash
curl -X POST "http://127.0.0.1:11235/md" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","f":"fit"}'
```

## Vault JSON

Secret kind / binding tool: `crawl4ai/fetch`

```json
{
  "base_url": "http://127.0.0.1:11235",
  "api_key": "optional-bearer-token"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `base_url` | yes | Crawl4AI server origin |
| `api_key` | no | Sent as `Authorization: Bearer …` when set |

## Invoke

- Endpoint: `POST {base_url}/md`
- Body: `{ "url", "f": filter, "q": focus_query }`
- Filters: `fit` (default), `raw`, `bm25`, `llm`

## Local / CI

Set `KORUX_CAPABILITY_HTTP_MOCK=1` for deterministic mock markdown.

## Governor / Owner config (suggested)

| Config | Suggested use |
|--------|----------------|
| `blocked_url_hosts` | Block localhost, link-local, metadata endpoints, intranet CNAMEs |
| `max_content_length` | Cap tokens sent to downstream LLM summarize |
