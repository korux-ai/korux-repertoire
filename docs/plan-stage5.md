# Stage 5: invocable twitter / facebook capability packages

**Status:** Ready (this-repo checklist is implemented; live posting still depends on Korux companion work below)  
**Scope:** `packages/twitter` and `packages/facebook` only, including in-package `runtime/` that Korux can call.  
**Release:** Immutable tag `v0.2.0` (twitter / facebook on top of the `v0.1.0` pair). LinkedIn and Instagram posting are `v0.3.0`, not this stage’s done criteria.  
**Main-repo map:** Korux `docs/implementation/capability-repertoire/plan.md` stage 5 keeps cross-repo acceptance only; the implementation list is this document.

---

## Goals

1. The official catalog ships two write-external posting capabilities: `twitter` (X) and `facebook` (Page post). Each post is plain text, or copy plus **one optional JPEG/PNG**.
2. Each package includes manifest, governor, credential docs, CHANGELOG, and executable `runtime/` (real vendor HTTP APIs).
3. After Korux imports `v0.2.0`, a new workflow can invoke when enabled ∩ Vault bound ∩ human approval pass, with `stub: false`.

---

## Preconditions

- This repo’s `v0.1.0` had `send-email` and `web-research` only — no social packages.
- Korux seed already has `twitter` / `x`: catalog and governor exist; **invoke is a stub** (`stub: true` after Vault check; no X API).
- Korux has **no** `facebook` seed / connector / Vault template.
- Korux `connectors/proxy.py` branches on tool name and **cannot** yet load `runtime/` from an imported snapshot via `runtime.entry`. In-package runtime needs a generic loader in Korux (see “Korux companion work”). This repo does not implement Korux core.

---

## Capability boundary (this stage only)

| Package id | Action | Out of scope |
|------------|--------|----------------|
| `twitter` | One tweet: copy required (≤280 chars); optional one JPEG/PNG. No image: `POST /2/tweets`. With image: media upload, then `POST /2/tweets` with `media_ids` | Multi-image, GIF/video, threads, replies, delete, timeline, read/reply comments |
| `facebook` | One Page post: copy required; optional one JPEG/PNG. No image: Graph `v21.0` `POST /{page-id}/feed`. With image: `POST /{page-id}/photos` (`caption` = copy) | Albums, video, personal timeline, comments, ads, Instagram |

Images come only from Korux workspace files: optional `args.image_file_id`. The platform resolves the file before invoke and passes bytes via `context` (`filename` / `content_type`). The package **must not** fetch public URLs or accept base64. No `image_file_id` uses the text path. Non-JPEG/PNG or over vendor limits fail-closed.

`trust`: `first-party`. `writes_external: true`, `default_gate: require_human`. `aliases`: `twitter` keeps `x`, matching Korux seed. Comment read/reply is not this stage; later separate packages.

---

## Runtime strategy: in-package `runtime/` (strategy A)

`runtime.entry` is a path relative to the package root: `runtime.invoke`. `transport`: `in_process`. `idempotent: false`.

Do not set the entry to `korux.modules.connectors.proxy._twitter_invoke` (main-repo stub; it breaks “catalog is the implementation”).

### Call contract (for the Korux loader)

After Governor allow and Vault resolve, the platform calls:

```text
async def invoke(args: dict, secret: dict, context: dict) -> dict
```

The package may use stdlib synchronous HTTPS inside that coroutine. Success and failure return a **flat dict** (aligned with current `proxy` results, **not** the runtime-contract envelope). The platform wraps that dict as `{ok, result, side_effect, audit}`.

| Argument | Contents |
|----------|----------|
| `args` | Passed `input_schema`; twitter requires `content`; facebook requires `message`; optional `image_file_id` |
| `secret` | Vault JSON plaintext for this call only; the package must not log or audit plaintext secrets |
| `context` | `workspace_id` / `agent_id` / `execution_id` / `capability_version`; with an image, parsed `image` (`bytes` / `filename` / `content_type`) |

A flat success payload includes `ok: true`, `stub: false`, vendor ids (`tweet_id` / `post_id`), and `content` or `summary` for downstream. Failure raises or returns `ok: false` plus a stable code (validation / credential / vendor 4xx/5xx).

Constraints:

- Stdlib HTTPS only (`urllib` and similar). **No** pip deps in the package; the Release zip has no venv.
- No `korux.*` imports. Credential resolve, binding, and human gates stay on the platform.
- Optional: `KORUX_CAPABILITY_HTTP_MOCK=1` returns a local fake (`stub: true`, no network) for CI without keys. **Production leaves mock off.**

### twitter credentials (OAuth 1.0a User Context)

Posting needs user context, not App-only Bearer. Vault JSON fields:

- `api_key` / `api_secret` (Consumer)
- `access_token` / `access_token_secret`

`docs/credential.md` covers X Developer Portal signup, User Token permissions including tweet.write and media.write, and Vault bind `tool_name=twitter`.

### facebook credentials (Page)

- `page_id`
- `page_access_token` (long-lived Page token; docs describe exchanging a User token for a Page token; User tokens must not be used to post)

`binding_tool` / `invoke_tool`: `facebook`.

---

## Package layout (each capability)

```text
packages/twitter/
  manifest.json
  governor.json
  runtime/
    __init__.py          # export invoke
    invoke.py            # HTTP (text or upload-then-post)
    oauth1.py            # twitter signing (this package only)
  docs/
    README.md
    credential.md
  CHANGELOG.md
```

`facebook` is the same without `oauth1.py`. `packages/_template` may document the runtime signature; the example is not a releasable package.

Governor hard floor (Owner **cannot** disable): empty body reject; `writes_external` → intercept + `require_human`. `editable_fields` are `content` / `message` and optional `image_file_id`. Approval cards must show copy; with an image, show the filename (and a platform preview if one exists).

Daily post caps and quiet hours are **not** this capability governor (Workflow `per_window`). Required hashtags, legal disclaimers, and PII/LLM review are out of this stage.

### Owner config (`editable_governor_config`)

Both packages declare the fields below. Empty list / unset means no extra tightening. Evaluation uses `$owner.*`; a hit **rejects** (no vendor call). Config may only tighten, never relax the hard floor.

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `blocked_keywords` | string[] | `[]` | Reject if copy (`content` / `message`) contains a substring (case-insensitive) |
| `blocked_url_hosts` | string[] | `[]` | Parse `http(s)` URLs from copy; reject if host (lowercased) is in the list |
| `max_chars` | integer | twitter `280`; facebook `5000` | Reject if copy is longer; default must not exceed the platform cap (X 280) |

Optional (in manifest this stage; default does not tighten):

| Field | Type | Default | Rule |
|-------|------|---------|------|
| `max_mentions` | integer | unlimited (omit or `null`) | Reject if `@` count in copy exceeds the cap |
| `require_image` | boolean | `false` | If `true` and no valid `image_file_id` / `context.image`, reject |

Korux passes binding `owner_config` into the capability governor before invoke (same path as `web-research` blocked keywords).

---

## This-repo checklist

- [x] Create `packages/twitter` and `packages/facebook` from `_template`
- [x] Fill manifests (I/O, schema, auth, params, `editable_governor_config`, `runtime.entry=runtime.invoke`, trust)
- [x] Governor (hard floor + `$owner` keywords / hosts / length; optional mentions / require image) + `docs/credential.md` + README + CHANGELOG
- [x] Implement `runtime/` (text post, single-image upload+post, optional HTTP mock)
- [x] `validate_all.sh` green. Require `runtime/invoke.py` exporting `invoke` only when `runtime.entry` is package-relative (this stage: `runtime.invoke`). `send-email` / `web-research` `korux.modules.*` entries do not need in-package `runtime/`
- [x] README / CONTRIBUTING: releases include first-party `runtime/`; drop “manifest+governor only”
- [x] After merge, tag `v0.2.0`; zip contains four packages: `send-email`, `web-research`, `twitter`, `facebook` (no `_template`)

---

## Korux companion work (not this repo)

Without the items below, import shows catalog entries but invoke 404s or still hits the twitter stub.

1. **Generic load:** Only when `trust=first-party` (or later written `verified`) and `runtime.entry` is an in-package module, `importlib`-load `invoke` from `packages/<id>/` for the current `repertoire_ref`. Paths limited to `CAPABILITY_CACHE_DIR` or builtin `packages/`. Community packages must not execute in-package code. `facebook` must not require a permanent `proxy.py` branch (the twitter stub uses the same loader).
2. **Connector table:** After disk overlay, `get_connector("facebook")` works (derive External + requires_secret from catalog; do not rely only on `BUILTINS`).
3. **Vault:** `facebook` template and `twitter` fields match package `auth.fields` (add a twitter-specific template if the main repo still lacks one).
4. **File inject:** When `image_file_id` is set, read the workspace file, validate JPEG/PNG, put bytes in `context.image`; missing or wrong type fail-closed with no vendor call.
5. **Governor binding:** Overlay twitter / facebook expose `editable_governor_config`; merge `owner_config` before invoke (same path as web-research keywords).
6. **Acceptance:** Import `v0.2.0` → workspace default pin → enable + bind → human approval then a real post (text and single-image at least once, or mock off against a test account). Old specs stay on `v0.1.0` / `builtin` and do not see facebook.

---

## Non-goals

- LinkedIn, Instagram (see “Follow-on `v0.3.0`”; not this stage’s zip / acceptance)
- Multi-image, GIF/video, fetch-by-URL, in-invoke base64 images
- Read comments, reply to comments, threads, delete (later separate capabilities, not this posting package)
- Daily post caps, quiet hours, required hashtags, PII/LLM review inside the capability package
- Copying twitter/facebook into main-repo git `packages/` (builtin need not sync; facebook is unavailable offline without import)
- Dynamically loading arbitrary community code (this stage: official first-party zip only)
- Floating `latest`

---

## Follow-on `v0.3.0` (not this stage)

Start after the `v0.2.0` posting path (in-package runtime, human gate, optional single image, `file_id` inject) is accepted. Same posting MVP: copy + optional one JPEG/PNG; `trust: first-party`; write-external human gate. Separate package ids; do not share `invoke_tool` with `facebook`.

| Package id | Action | Out of scope |
|------------|--------|----------------|
| `linkedin` | **Company Page only**: one post (copy required; optional one JPEG/PNG) | Personal profile posts, multi-image, video, comments, ads |
| `instagram` | **Only** an Instagram professional account linked to a Facebook Page, Feed post (copy + optional one JPEG/PNG; no image fail-closed — this capability requires an image) | Personal IG, Stories, Reels, shopping tags, comments |

Instagram and Facebook share Meta Graph; Vault stays split: `instagram` must not share `binding_tool` with `facebook`. Korux uses the stage-5 generic loader; no new `proxy.py` hardcoding for these two.

---

## Done when

- Repertoire Release `v0.2.0` zip includes both social packages and CI validation passes.
- After Korux imports that tag, new workflows can select `twitter` / `facebook`.
- With correct credentials and human approval, invoke hits the vendor API (or the documented mock switch); non-mock responses have `stub: false`. Text and single-image paths both work.
- Write-external still goes through governor human review; secrets stay out of git.
