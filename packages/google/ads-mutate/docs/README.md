# google/ads-mutate

First-party connector: Google Ads campaign **status** or capped **budget**.

## Behavior

- `POST .../campaigns:mutate` with `status=ENABLED|PAUSED`
- `POST .../campaignBudgets:mutate` with `amountMicros` (Owner-capped)
- Runtime refuses REMOVED / uncapped budgets
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: create campaigns, ads, keywords, bidding strategies, account hierarchy admin.

Binding: [credential.md](credential.md).
