# hubspot/crm-note — Vault credential

Bind tool name **`hubspot/crm-note`**.

Creates a CRM **note** associated to a contact. If only `email` is provided, the runtime looks up the contact (`idProperty=email`) and creates one when missing.

## Prerequisites

1. HubSpot Private App: https://developers.hubspot.com/docs/api/private-apps
2. Scopes typically include:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.objects.notes.write` (or equivalent notes scopes for your app)

## Vault JSON

```json
{
  "access_token": "pat-na1-xxxxxxxx"
}
```

## Agent binding

1. Vault → secret kind `hubspot`
2. Bind `tool_name`: **`hubspot/crm-note`**

## Local / CI

`KORUX_CAPABILITY_HTTP_MOCK=1` → `stub: true`. Production calls `api.hubapi.com` CRM v3.
