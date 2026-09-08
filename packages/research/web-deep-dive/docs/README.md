# research/web-deep-dive

Catalog **skill** (no runtime): helps Propose draft a deep web-research pipeline.

## Tool choice cheat-sheet

| Need | Prefer |
|------|--------|
| Fast hosted snippets | `tavily/web-search` |
| More links / self-hosted privacy | `searxng/search` |
| Full article body | `crawl4ai/fetch` |
| SPA / empty crawl | `browserless/browse` |
| Stock quotes / FRED | `yahoo/market-quotes` / `fred/series` |

## Suggested Owner governors on connectors

- `searxng/search`: `blocked_keywords`, `max_results`
- `crawl4ai/fetch` & `browserless/browse`: `blocked_url_hosts`, `max_content_length`
