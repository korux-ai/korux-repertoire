# Example capability package

Contributor scaffolding. The public catalog uses equivalent `manifest.yaml` / `governor.yaml`; this tree uses JSON so `scripts/validate_capability_package.py` can validate with no extra deps.

Spec: Korux `docs/spec/capability-package/`. This directory is not in the Release catalog.

## Runtime signature (first-party in-package implementation)

When `runtime.entry` is package-relative it is fixed as:

```text
async def invoke(args: dict, secret: dict, context: dict) -> dict
```

- Stdlib HTTPS; do not import `korux.*`; no pip dependencies
- Return a flat dict (`ok` / `stub` / vendor id); the platform wraps the runtime-contract envelope
- `KORUX_CAPABILITY_HTTP_MOCK=1` for CI without keys; production leaves it unset
