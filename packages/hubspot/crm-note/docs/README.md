# hubspot/crm-note

First-party connector: attach a note to a HubSpot contact.

## Behavior

- Resolve `contact_id`, or find/create contact by `email`
- `POST /crm/v3/objects/notes` with association type `202` (note → contact)
- Human gate by default; stdlib HTTPS; real API unless mocked

Out of scope: deals, tickets, bulk import, workflows, marketing email send.

Binding: [credential.md](credential.md).
