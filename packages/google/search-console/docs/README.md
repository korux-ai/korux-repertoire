# google/search-console

First-party **read-only** connector for Google Search Console search analytics.

## Behavior

- `POST /webmasters/v3/sites/{siteUrl}/searchAnalytics/query`
- Auth: OAuth refresh or `access_token`
- Default window: `28daysAgo` → `3daysAgo` (GSC data lag); default dimension `query`
- Returns a table in `content` / `summary`

Out of scope: sitemap submit, URL inspection write, property admin.

Binding: [credential.md](credential.md).
