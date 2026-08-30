# send-email — Vault credential

Bind tool name `send-email` on the agent that runs outbound email steps.

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

1. Vault → create secret `smtp` (or workspace convention name)
2. Bind secret to agent with `tool_name`: **`send-email`**

## Workflow NL hint

Recipient is **not** read from Vault — declare in NL, e.g. `发邮件到 legal@company.com`.
