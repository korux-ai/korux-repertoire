# google/analytics-report

First-party **read-only** connector for Google Analytics 4 reports.

## Behavior

- Calls GA4 Data API `properties/{id}:runReport` over HTTPS
- Auth: OAuth refresh token trio, or a short-lived `access_token`
- Default window: `7daysAgo` → `yesterday`; default metrics `sessions`, `activeUsers`, `screenPageViews`; default dimension `date`
- Returns a markdown-ish table in `content` / `summary` for downstream summarize steps
- Does not write to GA4, Ads, or Search Console

## invoke

`runtime.entry` = `runtime.invoke`

- Optional args: `start_date`, `end_date`, `metrics`, `dimensions`, `limit`, `property_id`
- Vault: `property_id` + (`access_token` **or** `client_id`/`client_secret`/`refresh_token`)
- Success: `ok`, `stub: false`, `content`, `summary`, `row_count`

Binding: [credential.md](credential.md).
