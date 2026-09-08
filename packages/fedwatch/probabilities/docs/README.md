# Fed policy probabilities (`fedwatch/probabilities`)

Language-neutral connector for FOMC meeting odds.

## Sources

1. **Primary** — JSON from `base_url` + `path` (default `https://rateprobability.com/api/fed/latest`). Public hosts may return Cloudflare 403; bind a reachable mirror in Vault.
2. **Secondary (optional)** — Yahoo `ZQ=F` settle heuristic when `allow_futures_backup=true`. Marked `confidence=under_anchored` and **must not** be treated as CME FedWatch meeting probabilities.

## Vault (optional)

Secret kind: `fedwatch/probabilities`

```json
{
  "base_url": "https://your-reachable-proxy.example",
  "path": "/api/fed/latest",
  "api_key": "optional-bearer"
}
```

## Mock

```bash
KORUX_CAPABILITY_HTTP_MOCK=1
```

## Compose guidance

- Prefer `role=primary` rows for rate odds.
- If `refresh_required=true` or `confidence=under_anchored`, say so in the brief; do not invent fresh institutional odds.
- Prose language follows workflow / Staff language — this package does not emit bilingual copy.
