# microsoft/teams

First-party **identity** connector for Microsoft Teams workflows (aligned with `zoom/account`).

## Behavior

- Bearer token → `GET /v1.0/me`
- App credentials → client_credentials token → `GET /v1.0/organization`
- Real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: create meetings, chat send, channel posts, Graph change notifications.

Binding: [credential.md](credential.md).
