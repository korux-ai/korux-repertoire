# FRED-style credential notes — fedwatch/probabilities

## Prerequisites

- Optional: a reachable JSON proxy that returns Fed meeting probabilities (many public mirrors are Cloudflare-gated).
- Optional Bearer token if your proxy requires auth.

## Vault JSON

Secret kind / binding tool: `fedwatch/probabilities`

```json
{
  "base_url": "https://your-reachable-proxy.example",
  "path": "/api/fed/latest",
  "api_key": "optional-bearer"
}
```

`auth.required=false` — invoke works without Vault when the default host is reachable, or via Yahoo `ZQ=F` secondary backup.

## Bind

1. Capabilities → Config for `fedwatch/probabilities` (optional).
2. Bind to Staff tool `fedwatch/probabilities`.

## Common errors

| Symptom | Fix |
|---------|-----|
| HTTP 403 from default host | Provide Vault `base_url` to a non-blocked proxy |
| PROVIDER both primary + backup failed | Fix network / mirror; disable inventing odds in compose |
| under_anchored ZQ=F only | Label as secondary; refresh primary later |
