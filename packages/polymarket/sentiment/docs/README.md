# Polymarket sentiment (`polymarket/sentiment`)

Read-only public odds from Polymarket Gamma API.

## Role

**`sentiment_only`** — never primary for institutional FedWatch. Use `fedwatch/probabilities` for primary rate odds.

## Args

| Field | Notes |
|-------|-------|
| `query` | Public search text |
| `event_slug` | Exact event slug (preferred when known) |
| `max_markets` | Cap markets per event (default 8, max 15) |

Provide **query or event_slug**.

## Mock

```bash
KORUX_CAPABILITY_HTTP_MOCK=1
```

## Language

Structured fields only. Report prose language follows workflow / Staff language.
