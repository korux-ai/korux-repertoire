# hubspot/contact-upsert — Vault credential

Bind tool name **`hubspot/contact-upsert`**.

Creates or updates a CRM **contact**. Lookup uses `idProperty=email` when `contact_id` is absent.

## Prerequisites

1. HubSpot Private App: https://developers.hubspot.com/docs/api/private-apps
2. Scopes typically include:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`

## Vault JSON

```json
{
  "access_token": "pat-na1-xxxxxxxx"
}
```

## Agent binding

1. Vault → secret kind `hubspot`
2. Bind `tool_name`: **`hubspot/contact-upsert`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`. Production calls `api.hubapi.com` CRM v3.
