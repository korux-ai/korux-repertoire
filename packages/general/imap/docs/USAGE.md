# general/imap — usages (monitor poll vs Spec read)

Capability: `general/imap` (alias `inbound-email-monitor`).  
Vault kind: `imap`. One Config covers both usages below.

## Shared semantics

Both **poll** and **read** fetch **UNSEEN** messages only  
(optional `from_filter` / `subject_contains` / `seen_ids` dedupe).  
There is **no** “read already-seen latest mail” mode for workflows.

Actions:

| `action` | Meaning | `mark_read_on_process` |
|----------|---------|------------------------|
| `poll` (default) | Detect UNSEEN for monitor / trigger conditions; return `messages[]` | **Does not apply** (must not consume mail) |
| `read` | Spec mid-flow: ingest unread mail into the workflow | **Applies** after a successful fetch (Vault Config) |
| `mark_seen` | Explicitly mark UIDs seen (scheduler / advanced) | Honored (no-op when Config is false) |

## Usage A — Monitor trigger (scheduler)

**When:** Owner wants “new unread mail → start this flow”.

**Spec shape:** `type=trigger`, `kind=monitor`, `connector=general/imap` (or alias), pin `config_ref`.

**Runtime:** Korux scheduler calls **poll** (or equivalent `fetch_unseen`) on an interval.  
If conditions match, it starts a run with the message as seed, then may call **`mark_seen`** after the run starts successfully.  
Do **not** also add a mid-flow IMAP **read** for the same signal.

## Usage B — Spec step (mid-flow read)

**When:** NL says e.g. “start manually, then read the latest unread customer email” (and Staff has IMAP Config).

**Spec shape:** `type=step`, `connector=general/imap`, `action=read` (Korux defaults Spec steps to `read`), `gate=auto`, pin `config_ref`, then downstream `korux/llm-summarize` / decide.

**Runtime:** Korux Spec runner **must invoke** package **`read`**, absorb `content` into rolling step I/O, **fail-closed** if there is no unseen mail, and let the package apply `mark_read_on_process` when set.

**Propose Must:** Prefer Usage B when the flow already has a non-monitor trigger (e.g. manual) and NL asks to read the inbox mid-flow. Prefer Usage A when NL is “when email arrives / watch inbox”. Prefer **not** combining A + B for the same mailbox signal.

## Won't

- Split into two packages or two Vault kinds  
- Apply `mark_read_on_process` on **poll** (detection must not consume)  
- Poll already-read mail as “latest” for workflow steps  
- Invent `config_ref` in LLM Propose (Owner / auto-pin Ready Config)
