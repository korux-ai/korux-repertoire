# Yahoo market quotes

Public Yahoo Finance quote (+ daily chart) connector. **No Vault key.**

## Args

| Field | Required | Notes |
|-------|----------|-------|
| `symbols` | yes | Up to 40 Yahoo tickers |
| `include_history` | no | Default `true` — adds approx `pct_5d` from daily closes |

## Output (language-neutral)

Each `quotes[]` row may include: `regularMarketPrice`, `pct_1d`, `pct_5d`, `marketState`, `as_of`, `session_note`.

Compose / report prose language must follow the workflow NL or Staff language — do not treat this connector output as bilingual copy.

## Transport (1.2+)

Yahoo disabled redistribution via unofficial `/v7/finance/quote` (HTTP 401 feedback form).
This package **prefers** `/v8/finance/chart/{symbol}` (still unofficial) and may attempt crumb+cookie v7 only as fallback.

## Mock

```bash
KORUX_CAPABILITY_HTTP_MOCK=1
```

## Limits

- Unofficial endpoints; may break, rate-limit (429), or be blocked (401/403).
- `%5D` is approximate (last close vs ~5 prior daily closes).
- Holiday / closed sessions: trust `marketState` + `session_note`; do not invent a live print.
- For production reliability, plan a licensed market-data provider as a later connector.
