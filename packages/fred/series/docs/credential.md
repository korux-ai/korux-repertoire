# FRED API key

## Prerequisites

1. Create a free account at [https://fred.stlouisfed.org/](https://fred.stlouisfed.org/).
2. Request an API key: [https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html).

## Vault JSON

Secret kind / binding tool: `fred/series`

```json
{
  "api_key": "YOUR_FRED_API_KEY"
}
```

## Bind

1. Capabilities → create Config for `fred/series`.
2. Bind the Config to the staff tool `fred/series`.

## Common errors

| Symptom | Fix |
|---------|-----|
| CREDENTIAL missing api_key | Ensure Vault JSON has `api_key` |
| HTTP 400 / invalid series | Check `series_id` (e.g. `DGS10`) |
| HTTP 429 | Back off; FRED rate limits free keys |
