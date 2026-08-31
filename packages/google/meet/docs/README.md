# google/meet

First-party **identity** connector for Google Meet workflows (aligned with `zoom/account`).

## Behavior

- Resolve access token (direct or OAuth refresh)
- `GET https://www.googleapis.com/oauth2/v3/userinfo`
- Returns `user_id` (`sub`), `email`, optional `meeting_id` passthrough
- Real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: create/join Meet links, calendar events, recordings, transcript ingest.

Binding: [credential.md](credential.md).
