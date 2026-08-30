# Zoom

Verifies Zoom credentials: Server-to-Server OAuth (`POST /oauth/token`) then `GET /v2/users/me`, or a bearer token.

Meeting-end inject remains on the Korux platform; this package does identity HTTP only.

Runtime entry: `runtime.invoke`.
