# Yahoo market quotes

Public Yahoo Finance quote (+ optional daily chart) connector. **No Vault key.**

## Args

| Field | Required | Notes |
|-------|----------|-------|
| `symbols` | yes | Up to 40 Yahoo tickers |
| `include_history` | no | Default `true` — adds approx `pct_5d` via v8 chart |

## Output (language-neutral)

Each `quotes[]` row may include: `regularMarketPrice`, `pct_1d`, `pct_5d`, `marketState`, `as_of`, `session_note`.

Compose / report prose language must follow the workflow NL or Staff language — do not treat this connector output as bilingual copy.

## Mock

```bash
KORUX_CAPABILITY_HTTP_MOCK=1
```

## Limits

- Unofficial endpoints; may break or rate-limit.
- `%5D` is approximate (last close vs ~5 prior daily closes).
- Holiday / closed sessions: trust `marketState` + `session_note`; do not invent a live print.
