# place-trade-order — Vault credential

Bind tool name **`place-trade-order`**. Use **paper** keys only.

## Prerequisites

1. Alpaca account with Paper Trading enabled: https://app.alpaca.markets/
2. Paper API Key ID and Secret (not Live)

## Vault JSON

```json
{
  "api_key": "PK-placeholder",
  "api_secret": "placeholder",
  "base_url": "https://paper-api.alpaca.markets"
}
```

`base_url` is optional. Hosts without `paper-api` (except localhost/test) are refused.

## Agent binding

1. Vault → secret kind `broker`
2. Bind `tool_name`: **`place-trade-order`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` returns a fake `order_id` (`stub: true`). Production leaves this unset.
