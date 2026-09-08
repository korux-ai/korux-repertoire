# searxng/search

Privacy-oriented **metasearch** connector. Returns ranked titles, URLs, and short snippets from a SearXNG instance.

## When to propose

- Need **more candidate links** than `tavily/web-search` snippets.
- Owner already runs SearXNG with JSON enabled.
- Multilingual research: set `language` to `zh-CN` / `zh-HK` / `en`.

## Typical pipeline

`searxng/search` → select URLs → `crawl4ai/fetch` → (optional) `browserless/browse` → summarize

See also skill `research/web-deep-dive`.
