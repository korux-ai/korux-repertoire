# canva/design-export

First-party connector: Canva Connect export (+ optional Brand Template autofill).

## Behavior

- `POST /v1/exports` then poll job for download URLs (24h)
- Optional `POST /v1/autofills` then export the new design
- Formats: png (default), jpg, pdf
- Human gate; real HTTPS unless `KORUX_CAPABILITY_HTTP_MOCK=1`

Out of scope: OAuth dance inside runtime, asset upload library, folder moves, editor return navigation.

Binding: [credential.md](credential.md).
