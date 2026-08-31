# general/mail — Vault credential

Bind tool name `general/mail` on the agent that runs outbound email steps.

## What goes in Vault JSON

One Vault secret (`secret_kind` = `smtp`) stores **this capability’s credential config only**:

- Included: fields declared under manifest `auth.fields` (e.g. `host`, `port`, `username`, `password`, `from`, `use_tls`) — sensitive and non-sensitive together in one JSON blob.
- **Not** included: Spec / step parameters such as `to`, `subject`, `body` (those stay on the workflow step or NL).

## SMTP secret (JSON)

```json
{
  "host": "localhost",
  "port": 1025,
  "username": "",
  "password": "",
  "from": "korux@localhost",
  "use_tls": false
}
```

Local dev: use Mailhog (`make up`) with `SMTP_HOST=localhost` and port `1025`.

## Agent binding

1. Capabilities → Add `general/mail` (or Vault) → create secret kind `smtp`
2. Bind secret to agent with `tool_name`: **`general/mail`**

## Workflow NL hint

Recipient is **not** read from Vault — declare in NL, e.g. `发邮件到 legal@company.com`.
