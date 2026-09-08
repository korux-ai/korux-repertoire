# browserless/browse

Render pages with **real headless Chrome** when lighter fetchers fail.

## When to propose

- After `crawl4ai/fetch` is empty or clearly broken on SPA sites.
- Not the default first fetch tool.

## Typical pipeline

`searxng/search` → `crawl4ai/fetch` → (fallback) `browserless/browse` → summarize
