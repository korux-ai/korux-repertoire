# korux-repertoire

Official Korux capability catalog. This repository publishes **catalog snapshots** (manifests, governor rules, credential docs, and first-party in-package `runtime/`). Korux consumes **locked GitHub Release zips** only — never a floating `latest`.

SPDX-License-Identifier: Apache-2.0

Trust levels, PR review, and safety rails follow the Korux [contributor-guide](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md). Package fields: [package-manifest](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/package-manifest.md).

## Layout

```text
korux-repertoire/
  packages/              # capability packages; _template is scaffolding, not in the release catalog
    send-email/          # runtime.entry may still point at Korux modules
    web-research/
    twitter/             # runtime.invoke (X API)
    facebook/            # runtime.invoke (Graph API)
    place-trade-order/   # runtime.invoke (Alpaca paper)
    notion/              # runtime.invoke (Notion API)
    zoom/                # runtime.invoke (Zoom OAuth + users/me)
    _template/
  schemas/               # optional: manifest / governor JSON Schema
  scripts/               # validate_all.sh · package_release.sh
  .github/workflows/     # CI (PR/push) and tag Release
  CONTRIBUTING.md
  LICENSE
  README.md
```

`send-email` / `web-research` may keep `runtime.entry` as `korux.modules.*`. First-party packages with live vendor HTTP (`twitter`, `facebook`, `place-trade-order`, `notion`, `zoom`) ship executable `runtime/` in this repo. Google Meet / Microsoft Teams stay out until Korux has a non-mock live path.

## Consumption

1. Download `korux-repertoire-vX.Y.Z.zip` from [Releases](https://github.com/korux-ai/korux-repertoire/releases).
2. Validate, then unpack into the Korux workspace at `.data/capability/repertoire-vX.Y.Z/`.
3. Workflow / Run pin `repertoire_ref` (`builtin` or `vX.Y.Z`). With no imported remote catalog, Korux falls back to main-repo builtin `packages/`.

The public catalog is a superset; main-repo `packages/` is the offline first-party subset. Moving from `builtin` to a tag requires an explicit import and pin change — never a silent swap. Existing workflows keep their ref; new flows inherit the workspace default pin.

A package on disk is not enough to invoke: catalog **enabled**, staff Vault binding, and trust level still apply. In-package `runtime/` is loaded by Korux from `runtime.entry` (**first-party** only).

## Validate and release

```bash
./scripts/validate_all.sh
./scripts/package_release.sh v0.2.0
```

Pushing tag `vX.Y.Z` uploads the zip to [Releases](https://github.com/korux-ai/korux-repertoire/releases) via Actions.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

This repository is licensed under the [Apache License 2.0](./LICENSE) (SPDX: `Apache-2.0`). The license does **not** grant rights to the Korux name, trademarks, or logos. Official `trust: first-party` releases and review stay with Korux maintainers. Merge into this repo does not imply production invoke.
