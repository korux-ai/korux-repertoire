# Contributing to korux-repertoire

This repository accepts **capability packages**: manifest, governor, docs, and (for connectors) executable `runtime/`. Korux consumes locked Release zips. Authoritative rules live in the [Korux capability-package spec](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/README.md); this file is the entry point.

## Placement rule

| Depends on Korux framework? | Belongs here? |
|----------------------------|---------------|
| **No** — only Vault JSON + third-party APIs | **Yes** |
| **Yes** — SOP/Agent/Governor/ACL/LLM kernel | **No** → Korux main repo `packages/korux/` |

## Hard rules (repertoire)

1. **Zero Korux dependency** — no `import korux…` or links to Korux libraries in package code.
2. **`kind: connector`** — **must** ship `runtime/invoke.py` with `runtime.kind=package` and `runtime.entry=runtime.invoke`.
3. **`kind: skill`** — **may** omit `runtime/` (catalog / Propose only); if present, same invoke contract applies.
4. **No `runtime.entry: korux.modules…`** — kernel paths belong in Korux core, not this repo.

## Local validation

```bash
./scripts/validate_all.sh
# or a single package:
python3 scripts/validate_capability_package.py packages/<namespace>/<name>
```

`packages/_template` is not in the catalog / Release and is not validated as a production package. When `runtime.entry` is `runtime.invoke`, `runtime/invoke.py` must exist and define `invoke`. CI also rejects any `korux` import under package trees.

Package locally (do not commit `dist/`):

```bash
./scripts/package_release.sh v0.5.0
```

## Write-external and Governor

PRs must pass the Korux review checklist (this repo does not keep a second copy):

- [PR review checklist](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#4-pr-评审清单)
- [Repository placement §2.5](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#25-仓库归属core-vs-repertoire)
- [Safety rails](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#5-安全红线)

Write-external packages require `writes_external=true`, a non-empty governor, and `default_gate=require_human` (written exceptions only). Secrets, tokens, and real PII must not enter this repository.

## New packages

1. Copy `packages/_template/` to `packages/<namespace>/<name>/`.
2. Confirm the capability does **not** need Korux framework (else contribute to Korux core).
3. Fill `manifest.json`: `id`, `version`, I/O flags, schema, auth, `params`, `default_gate`.
4. **Connector:** implement `runtime/invoke.py` (stdlib / third-party SDK only; `async def invoke(args, secret, context)`).
5. **Skill (optional runtime):** omit `runtime/` if the platform handles the step via kernel `step_kind`.
6. Write governor when `writes_external=true`; write `docs/credential.md` when `auth.required=true`.
7. After local validation, open a PR with an invoke example and CHANGELOG.

Full flow: [adding a capability](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#2-新增能力流程).

## License and DCO

This repository is Apache-2.0. Each commit must include a Developer Certificate of Origin sign-off (`git commit -s`). Do not commit secrets.

## Releases

Maintainers push an immutable tag `vX.Y.Z`. GitHub Actions validates, builds `korux-repertoire-vX.Y.Z.zip`, and attaches SHA256SUMS. Production must not depend on floating `latest`.
