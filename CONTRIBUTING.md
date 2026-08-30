# Contributing to korux-repertoire

This repository accepts **capability packages**: manifest, governor, docs. First-party write-external packages also need executable `runtime/`. Korux consumes locked Release zips. Authoritative rules live in the Korux spec; this file is the entry point.

## Local validation

```bash
./scripts/validate_all.sh
# or a single package:
python3 scripts/validate_capability_package.py packages/<id>
```

`packages/_template` is not in the catalog / Release and is not validated as a production package. When `runtime.entry` is `runtime.invoke`, `runtime/invoke.py` must exist and define `invoke`. `korux.modules.*` entries do not require in-package `runtime/`.

Package locally (do not commit `dist/`):

```bash
./scripts/package_release.sh v0.2.0
```

## Write-external and Governor

PRs must pass the Korux review checklist (this repo does not keep a second copy):

- [PR review checklist](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#4-pr-评审清单)
  - [Manifest: `writes_external` / `default_gate`](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#41-manifest-与-schema)
  - [Governor non-empty; no relaxing hard floors](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#43-governor)
- [Safety rails](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#5-安全红线)
- [Governor rule syntax](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/governor-rules.md)

Write-external packages (post, email, Notion write, and similar) require `writes_external=true`, a non-empty governor, and `default_gate=require_human` (written exceptions only). Community packages must not default to `writes_external` + `auto` with no governor. Secrets, tokens, and real PII must not enter this repository.

## New packages

1. Copy `packages/_template/` to `packages/<kebab-id>/`.
2. Fill `manifest.json`: `id`, `version`, I/O flags, schema, auth, `params`, `default_gate`. First-party posting packages use `runtime.entry=runtime.invoke`.
3. Write governor when `writes_external=true`; write `docs/credential.md` when `auth.required=true`.
4. Implement `runtime/invoke.py` (stdlib HTTPS; do not import `korux.*`).
5. After local validation, open a PR with an invoke example and CHANGELOG.

Full flow: [adding a capability](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md#2-新增能力流程). Platform core API changes belong in a Korux main-repo RFC, separate from the package PR.

## License and DCO

This repository is Apache-2.0. Submitting a change is **inbound = outbound**: the contribution is licensed under the same terms, with no extra conditions unless a prior written agreement says otherwise.

Each commit must include a Developer Certificate of Origin sign-off, for example:

```text
Signed-off-by: Your Name <you@example.com>
```

Git: `git commit -s`. Do not commit secrets, tokens, or real PII. The license does not cover Korux trademarks.

## Releases

Maintainers push an immutable tag `vX.Y.Z`. GitHub Actions `release.yml` validates, builds `korux-repertoire-vX.Y.Z.zip`, and attaches it to the Release (plus `SHA256SUMS`). Production must not depend on floating `latest`.
