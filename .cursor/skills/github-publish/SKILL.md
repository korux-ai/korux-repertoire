---
name: github-publish
description: Tag the next semver release and push it to GitHub origin so Actions publishes the repertoire zip. Use when the user types publish next version, asks to tag the next version, or release to GitHub in this project.
---

# GitHub Publish (korux-ai/korux-repertoire)

When the user types `publish next version` in chat, compute the next immutable tag, validate packages, create an annotated tag, and push it to GitHub. Do not ask whether to tag or push.

GitHub Actions `.github/workflows/release.yml` builds `korux-repertoire-vX.Y.Z.zip` and attaches it (plus `SHA256SUMS`) on tag `v*`. Do **not** create the GitHub Release with `gh release create` unless the workflow failed and the user asked to recover.

## Remote

- Default branch: `main`
- `origin` → `https://github.com/korux-ai/korux-repertoire.git`
- Prefer existing git credentials / `gh auth`. Never hardcode tokens.

## Preconditions

Run in parallel first:

```bash
git status
git log -8 --oneline
git tag -l 'v*'
git ls-remote --tags origin
```

Stop if:

- The working tree is not clean (uncommitted changes). Tell the user to `commit` first.
- `HEAD` is not `main` tracking `origin/main` (unless the user named another branch to release).
- The chosen tag already exists locally or on `origin`. Never overwrite, delete, or force-push tags.

## Next version

Tags are `vX.Y.Z` only (example: `v0.3.0`). If the user named a version, use that if it is unused and valid.

Otherwise take the highest existing `v*` tag and bump:

- **MINOR** (`Y+1`, `Z=0`) when `packages/<id>/` was added since the last tag (skip `_template`).
- **PATCH** (`Z+1`) for fixes, docs, scripts, or existing-package changes only.
- **MAJOR** only if the user asked (catalog/contract break).

Do not use floating `latest`. Do not reuse `v0.3.0` for LinkedIn/Instagram if that tag already shipped other packages; bump forward.

## Workflow

1. Validate:

```bash
./scripts/validate_all.sh
```

Stop on failure; do not tag.

2. Annotated tag (HEREDOC message: why this release, 1–2 sentences, English):

```bash
git tag -a vX.Y.Z -m "$(cat <<'EOF'
<message>

EOF
)"
```

3. Push the tag only:

```bash
git push origin vX.Y.Z
```

4. Confirm Actions `Release` for that tag succeeded. Poll the GitHub API or `gh run list` / `gh release view vX.Y.Z` if available (no tokens in URLs). Report:

- tag and commit
- Release URL
- assets: `korux-repertoire-vX.Y.Z.zip`, `SHA256SUMS`
- package ids in the zip (`packages/*` minus `_template`)

## Rules

- Never `git config`, `--no-verify`, interactive (`-i`), force push, or hard reset.
- Never move or recreate a published tag.
- Do not commit `dist/`.
- Do not include secrets in the tag message.
- Local `./scripts/package_release.sh vX.Y.Z` is optional smoke (excludes `__pycache__`); CI zip is the official artifact.
