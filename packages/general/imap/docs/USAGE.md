# general/imap — usages (monitor vs Spec step)

Capability: `general/imap` (alias `inbound-email-monitor`).  
Vault kind: `imap`. One Config covers both usages below.

## Shared semantics

Both usages call the same runtime action **`poll`** = fetch **UNSEEN** messages only  
(optional `from_filter` / `subject_contains` / `seen_ids` dedupe).  
There is **no** “read already-seen latest mail” mode for workflows.

Actions:

| `action` | Meaning |
|----------|---------|
| `poll` (default) | Fetch unseen messages; return `messages[]`, `content`/`summary` = first body |
| `mark_seen` | Mark UIDs seen after processing |

## Usage A — Monitor trigger (scheduler)

**When:** Owner wants “new unread mail → start this flow”.

**Spec shape:** `type=trigger`, `kind=monitor`, `connector=general/imap` (or alias), pin `config_ref`.

**Runtime:** Korux scheduler / inbound monitor polls on an interval and starts a run with the message as seed. Do **not** also add a mid-flow IMAP step for the same poll.

## Usage B — Spec step (mid-flow read)

**When:** NL says e.g. “start manually, then read the latest unread customer email” (and Staff has IMAP Config).

**Spec shape:** `type=step`, `connector=general/imap`, `gate=auto` (typical), pin `config_ref`, then downstream `korux/llm-summarize` / decide.

**Runtime:** Korux Spec runner **must invoke** package `poll` on this step, absorb `content` into rolling step I/O, and **fail-closed** if there is no unseen mail (do not pretend success).

**Propose Must:** Prefer Usage B when the flow already has a non-monitor trigger (e.g. manual) and NL asks to read the inbox mid-flow. Prefer Usage A when NL is “when email arrives / watch inbox”.

## Won't

- Split into two packages or two Vault kinds  
- Poll already-read mail as “latest” for workflow steps  
- Invent `config_ref` in LLM Propose (Owner / auto-pin Ready Config)
