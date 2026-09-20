# general/mail — Vault credential

Bind tool name `general/mail` on the agent that runs outbound email steps.

## What goes in Vault JSON

One Vault secret (`secret_kind` = `smtp`) stores **this capability’s credential config only**:

- Included: fields declared under manifest `auth.fields` (e.g. `host`, `port`, `username`, `password`, `from`, `use_tls`, `use_ssl`) — sensitive and non-sensitive together in one JSON blob.
- **Not** included: Spec / step parameters such as `to`, `subject`, `body` (those stay on the workflow step or NL).

## SMTP secret (JSON)

### Local Mailpit / Mailhog (plain)

```json
{
  "host": "localhost",
  "port": 1025,
  "username": "",
  "password": "",
  "from": "korux@localhost",
  "use_tls": false,
  "use_ssl": false
}
```

### Gmail (STARTTLS on 587)

```json
{
  "host": "smtp.gmail.com",
  "port": 587,
  "username": "you@gmail.com",
  "password": "app-password",
  "from": "you@gmail.com",
  "use_tls": true,
  "use_ssl": false
}
```

### 163 (implicit SSL on 465)

```json
{
  "host": "smtp.163.com",
  "port": 465,
  "username": "you@163.com",
  "password": "authorization-code",
  "from": "you@163.com",
  "use_tls": false,
  "use_ssl": true
}
```

If `use_ssl` is omitted and `port` is `465`, runtime defaults to SSL.  
If `use_tls` is omitted and `port` is `587` (and SSL is off), runtime defaults to STARTTLS.

## Agent binding

1. Capabilities → Add `general/mail` (or Vault) → create secret kind `smtp`
2. Bind secret to agent with `tool_name`: **`general/mail`**

## Workflow NL hint

Recipient is **not** read from Vault — declare in NL, e.g. `发邮件到 legal@company.com`.
