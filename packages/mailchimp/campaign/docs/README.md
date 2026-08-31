# mailchimp/campaign

First-party connector for Mailchimp **regular** campaigns.

## Behavior

- `action=create` (default): `POST /3.0/campaigns` then `PUT /campaigns/{id}/content`
- `action=send`: `POST /campaigns/{id}/actions/send`
- `action=create_and_send`: create + content + send
- `writes_external` + `require_human`
- Stdlib HTTPS only; real API unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: A/B tests, RSS, automations, list member CRUD.

Binding: [credential.md](credential.md).
