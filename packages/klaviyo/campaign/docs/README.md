# klaviyo/campaign

First-party connector for Klaviyo **email** campaigns.

## Behavior

- `create`: `POST /api/campaigns` → `POST /api/templates` → assign template
- `send`: `POST /api/campaign-send-jobs`
- `create_and_send`: create path then send
- Human gate; real HTTPS unless mocked

Out of scope: flows/automations, SMS, catalog feeds.

Binding: [credential.md](credential.md).
