---
name: github-commit
description: Generate a Git commit message from the diff, create a commit, and push to GitHub origin. Use when the user types commit, asks to git commit, commit and push, or commit to GitHub in this project.
---

# GitHub Commit (korux-ai/korux-repertoire)

When the user types `commit` in chat, generate a commit message from the diff, create a git commit, and push it to GitHub. Do not ask whether to push.

## Remote

- Default branch: `main`
- `origin` → `https://github.com/korux-ai/korux-repertoire.git`
- Prefer existing git credentials / `gh auth`. Never hardcode tokens in this skill or in commands.

## Workflow

Run in parallel first:

```bash
git status
git diff && git diff --cached
git log -8 --oneline
```

Then:

1. Draft a concise commit message (1–2 sentences, why not what). Match existing log language.
2. Stage the relevant changed/untracked files. Do not stage secrets the user did not intend to commit (`.env`, credentials, tokens, private keys).
3. Commit with HEREDOC only:

```bash
git commit -m "$(cat <<'EOF'
<message>

EOF
)"
```

4. Push to GitHub:

```bash
git push origin HEAD
```

If push auth fails, use GitHub CLI (do not embed tokens in the URL):

```bash
gh auth status
git push origin HEAD
```

5. Run `git status` and report commit hash, message, and remote result.

## Rules

- Never `git config`, `--no-verify`, `--no-gpg-sign`, interactive (`-i`), force push, or hard reset.
- Never amend unless the user asked, this conversation created HEAD, and it is not pushed.
- If a hook rejects the commit, fix and create a **new** commit (do not amend).
- If there is nothing to commit, stop and say so.
- Empty commit is not allowed.
- Never commit files that contain secrets; warn the user instead.
