# crawl4ai/fetch

Fetch **full-page markdown** from a Crawl4AI HTTP server after you already have a URL.

## When to propose

- After `searxng/search` or `tavily/web-search` when snippets are too short.
- Prefer this over `browserless/browse` for normal public articles.

## Typical pipeline

`searxng/search` → `crawl4ai/fetch` → summarize  
If empty/JS-heavy → `browserless/browse`
