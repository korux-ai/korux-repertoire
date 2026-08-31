# google/analytics-report — Vault credential

Bind tool name **`google/analytics-report`** (aliases: `ga4-report`, `google-analytics`).

Read-only GA4 Data API (`analytics.readonly`). This package does **not** modify property settings or ads.

## Prerequisites

1. Google Cloud project with **Google Analytics Data API** enabled
2. OAuth 2.0 client (Desktop or Web) used to obtain a **refresh token** with scope  
   `https://www.googleapis.com/auth/analytics.readonly`
3. GA4 property where the authorizing Google user has at least **Viewer**
4. Numeric **property id** (Admin → Property settings), not the Measurement ID `G-XXXX`

## Vault JSON (recommended: refresh token)

```json
{
  "property_id": "123456789",
  "client_id": "xxxxx.apps.googleusercontent.com",
  "client_secret": "GOCSPX-xxxxx",
  "refresh_token": "1//xxxxx"
}
```

Optional short-lived override (skips refresh):

```json
{
  "property_id": "123456789",
  "access_token": "ya29.xxxxx"
}
```

| Field | Notes |
|-------|--------|
| `property_id` | Digits or `properties/{id}` |
| `client_id` / `client_secret` / `refresh_token` | Used to mint access tokens at invoke time |
| `access_token` | Optional; if set, used directly |

Do not commit real tokens.

## Agent binding

1. Vault → create secret kind `google-analytics`
2. Bind with `tool_name`: **`google/analytics-report`**

## Local / CI

Set `KORUX_CAPABILITY_HTTP_MOCK=1` for offline tests (`stub: true`). Production leaves this unset — invoke calls `oauth2.googleapis.com/token` (when refreshing) and `analyticsdata.googleapis.com` `runReport`.
