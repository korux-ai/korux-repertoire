# korux-repertoire

Official Korux capability catalog. This repository publishes **catalog snapshots** (manifests, governor rules, credential docs, and first-party in-package `runtime/`). Korux consumes **locked GitHub Release zips** only — never a floating `latest`.

SPDX-License-Identifier: Apache-2.0

Trust levels, PR review, and safety rails follow the Korux [contributor-guide](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/contributor-guide.md). Package fields: [package-manifest](https://github.com/korux-ai/korux/blob/main/docs/spec/capability-package/package-manifest.md).

## Layout

```text
korux-repertoire/
  packages/
    <namespace>/<name>/   # stable id = namespace/name (e.g. twitter/publish)
      manifest.json
      governor.json
      runtime/            # optional package-local invoke
      docs/
    _template/            # scaffolding only; not in release zip
  scripts/                # validate_all.sh · package_release.sh
  .github/workflows/
  CONTRIBUTING.md
  LICENSE
  README.md
```

Current packages:

| id | notes |
|----|--------|
| `general/mail` | SMTP send (`runtime.invoke`) |
| `general/imap` | IMAP inbound monitor |
| `tavily/web-search` | Tavily web research (`runtime.invoke`) |
| `twitter/publish` | X API post |
| `facebook/publish` | Graph API Page post |
| `linkedin/publish` | LinkedIn Company Page post |
| `instagram/publish` | Instagram professional Feed (image required) |
| `google/analytics-report` | GA4 Data API report (read-only) |
| `google/search-console` | Search Console search analytics (read-only) |
| `meta/ads-insights` | Meta Ads insights (read-only) |
| `meta/ads-mutate` | Meta Ads pause/activate + capped daily_budget (high risk) |
| `google/ads-mutate` | Google Ads pause/enable + capped budget (high risk) |
| `youtube/publish` | YouTube video upload (default unlisted) |
| `tiktok/publish` | TikTok video inbox/direct publish |
| `canva/design-export` | Canva export (+ optional Brand Template autofill) |
| `google/meet` | Google Meet identity (OAuth userinfo) |
| `microsoft/teams` | Microsoft Teams identity (Graph) |
| `mailchimp/campaign` | Mailchimp campaign create / optional send |
| `klaviyo/campaign` | Klaviyo email campaign create / optional send |
| `hubspot/crm-note` | HubSpot contact note (email upsert) |
| `hubspot/contact-upsert` | HubSpot contact create/update by email |
| `wordpress/post` | WordPress REST create post (draft default) |
| `webflow/cms-publish` | Webflow CMS item (staged default; optional live) |
| `marketing/campaign-brief` | Skill (no runtime): campaign brief for Propose |
| `marketing/channel-mix` | Skill (no runtime): channel mix → connectors |
| `marketing/brand-voice` | Skill (no runtime): brand voice checklist |
| `marketing/ab-copy` | Skill (no runtime): A/B copy variants |
| `marketing/content-calendar` | Skill (no runtime): content calendar |
| `marketing/performance-review` | Skill (no runtime): performance review |
| `marketing/local-store` | Skill (no runtime): local / multi-location plan |
| `marketing/hiring-campaign` | Skill (no runtime): hiring / employer-brand plan |
| `alpaca/place-order` | Alpaca paper trade |
| `notion/pages` | Notion page create |
| `zoom/account` | Zoom OAuth + users/me |

`kind: skill` may omit `runtime/` (catalog / Propose only). Connectors must ship `runtime.invoke`. Framework-bound skills stay in Korux (`packages/korux/*`).

## Consumption

1. Download `korux-repertoire-vX.Y.Z.zip` from [Releases](https://github.com/korux-ai/korux-repertoire/releases).
2. Validate, then unpack into the Korux workspace at `.data/capability/repertoire-vX.Y.Z/`.
3. Workflow / Run pin `repertoire_ref` (`builtin` or `vX.Y.Z`). Catalog = Korux **core** (`packages/korux/*`) ∪ selected release.

A package on disk is not enough to invoke: catalog **enabled**, staff Vault binding, and trust level still apply. In-package `runtime/` is loaded by Korux from `runtime.entry` (**first-party** only).

## Validate and release

```bash
./scripts/validate_all.sh
./scripts/scorecard_all.sh --html scorecard.html
./scripts/package_release.sh v0.5.1
```

Pushing tag `vX.Y.Z` uploads the zip to [Releases](https://github.com/korux-ai/korux-repertoire/releases) via Actions.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

This repository is licensed under the [Apache License 2.0](./LICENSE) (SPDX: `Apache-2.0`). The license does **not** grant rights to the Korux name, trademarks, or logos. Official `trust: first-party` releases and review stay with Korux maintainers. Merge into this repo does not imply production invoke.
