# Example capability package

Contributor scaffolding. The public catalog uses equivalent `manifest.yaml` / `governor.yaml`; this tree uses JSON so `scripts/validate_capability_package.py` can validate with no extra deps.

Spec: Korux `docs/spec/capability-package/`. This directory is not in the Release catalog.

## Runtime signature (first-party in-package implementation)

When `runtime.entry` is package-relative it is fixed as:

```text
async def invoke(args: dict, secret: dict, context: dict) -> dict
```

- Stdlib HTTPS; do not import `korux.*`; no pip dependencies
- Return `{ "ok": true, … }` or `{ "ok": false, "error": { "class", "code", "message" } }`
- Use `_fail(code, message, failure_class=…)` from the template; never return code/message alone
- Empty rows: `{ "ok": true, "empty": true, "content": "" }`
- Soft degrade: `{ "ok": true, "degraded": true, … }` (does not trigger Spec failure_policy)
- `KORUX_CAPABILITY_HTTP_MOCK=1` for CI without keys; production leaves it unset

### HTTP / auth → class (hint)

| Situation | `error.class` |
|-----------|---------------|
| Missing / bad Vault credential | `auth` |
| 401 / 403 from provider when credential present | often `unavailable` (Cloudflare / rate) — not always `auth` |
| Empty business payload | prefer `empty: true` success, else class `empty` |
| Timeout / 5xx / connection | `unavailable` |
| Bad args | `validation` |
| Other provider fault | `provider` |
