# korux-repertoire

Open-source **capability catalog** for governed AI agents — each package ships governance rules *with* the connector, not bolted on later.

## What is this?

Think: n8n / Zapier-style nodes, but every package includes:

| File | Role |
|------|------|
| `manifest.json` | What it does, risk level, I/O boundary (`writes_external`, gates) |
| `governor.json` | Runtime rules — human approval, validation, block |
| `runtime/` + `docs/` | Executable connector + credential / setup guide |

**Start here (no Korux install needed):**

- [general/mail/governor.json](packages/general/mail/governor.json) — human must approve before send email
- [linkedin/publish/governor.json](packages/linkedin/publish/governor.json) — Company Page post gate
- [meta/ads-mutate/governor.json](packages/meta/ads-mutate/governor.json) — high-risk ads pause / budget caps

Website: [korux.ai](https://korux.ai) · Building in public on LinkedIn / X: [@korux_ai](https://x.com/korux_ai)

---

Official Korux catalog snapshots (manifests, governor rules, credential docs, and first-party in-package `runtime/`). Korux consumes **locked GitHub Release zips** only — never a floating `latest`.

SPDX-License-Identifier: Apache-2.0

Package authoring rules: [CONTRIBUTING.md](./CONTRIBUTING.md). Full Korux runtime / capability-package specs live in the main Korux repo (not all docs may be public yet); this catalog is readable on its own.

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
| `alibaba/wanx-edit` | Alibaba Wanxiang prompt image edit (DashScope) |
| `meitu/product-image` | Meitu product cutout (MTlab sync) |
| `design/template-compose` | Product card compose (photo+logo+headline → social_post) |
| `xiaohongshu/publish` | Xiaohongshu image note (Owner-configured OpenAPI) |
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
| `marketing/product-promo` | Skill (no runtime): one-product promo → compose/XHS |
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

## GitHub Topics (repo settings)

Set these under **About → Topics** so people can find the catalog:

`ai-agents` · `agentic-ai` · `governance` · `human-in-the-loop` · `workflow-automation` · `llm` · `capability-catalog` · `n8n` · `zapier`

**Suggested About description (one line):**

```
Governed AI agent capability catalog — manifest + governor rules + runtime connectors
```

**Website:** `https://korux.ai`

## License

This repository is licensed under the [Apache License 2.0](./LICENSE) (SPDX: `Apache-2.0`). The license does **not** grant rights to the Korux name, trademarks, or logos. Official `trust: first-party` releases and review stay with Korux maintainers. Merge into this repo does not imply production invoke.
