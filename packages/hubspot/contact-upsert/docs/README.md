# hubspot/contact-upsert

First-party connector: create or update a HubSpot contact (email upsert or `contact_id` patch).

## Behavior

- Lookup `GET /crm/v3/objects/contacts/{email}?idProperty=email`
- Create `POST /crm/v3/objects/contacts` or update `PATCH .../contacts/{id}`
- Optional extra `properties` object for custom HubSpot fields
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: notes (use `hubspot/crm-note`), companies/deals, bulk CSV import, GDPR delete.

Binding: [credential.md](credential.md).
