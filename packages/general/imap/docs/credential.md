# general/imap — Vault credential (IMAP)

Capability id: `general/imap` (aliases: `inbound-email-monitor`, …).  
Vault **secret_kind** stays `imap`.  
Bind tool: **`inbound-email-monitor`**.

## What goes in Vault JSON

One Vault secret stores **this capability’s IMAP config only**:

- Included: `auth.fields` (e.g. `host`, `port`, `username`, `password`, `folder`, `use_ssl`, `mark_read_on_process`) — credentials and non-secret options in one JSON blob.
- **Not** included: Spec step filters / NL (e.g. `from_filter`) when those live on the monitor step, not in `auth.fields`.

## IMAP secret (JSON)

```json
{
  "host": "imap.gmail.com",
  "port": 993,
  "username": "you@gmail.com",
  "password": "xxxx xxxx xxxx xxxx",
  "folder": "INBOX",
  "use_ssl": true,
  "mark_read_on_process": true
}
```

## Gmail

1. Gmail → Settings → Forwarding and POP/IMAP → enable IMAP.  
2. Google Account → Security → 2-Step Verification → App passwords.  
3. Capabilities Config: kind `imap`, host `imap.gmail.com`, port `993`.  
4. Bind secret to staff tool **`inbound-email-monitor`**.  
5. Spec trigger: `monitor` + `inbound-email-monitor` (or `general/imap`).

Local mock: `INBOUND_EMAIL_MOCK=true` (default); set `false` and restart worker for real IMAP.
