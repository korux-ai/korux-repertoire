"""SMTP send — stdlib only; no Korux imports."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

_TEST_SENT: list[dict[str, Any]] = []


def clear_test_sent() -> None:
    _TEST_SENT.clear()


def get_test_sent() -> list[dict[str, Any]]:
    return list(_TEST_SENT)


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _as_bool(raw: Any, *, default: bool | None = None) -> bool | None:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    text = str(raw).strip().lower()
    if text in {"", "none", "null"}:
        return default
    if text in {"false", "0", "no", "off"}:
        return False
    if text in {"true", "1", "yes", "on"}:
        return True
    return default


def _parse_smtp_secret(secret: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(secret, dict):
        return _fail("CREDENTIAL", "Vault secret must be a JSON object")
    host = str(secret.get("host") or "").strip()
    if not host:
        return _fail("CREDENTIAL", "Vault smtp JSON missing host")
    from_addr = str(secret.get("from") or secret.get("from_addr") or "").strip()
    if not from_addr:
        return _fail("CREDENTIAL", "Vault smtp JSON missing from")
    try:
        port = int(secret.get("port") or 587)
    except (TypeError, ValueError):
        return _fail("CREDENTIAL", "Vault smtp JSON port must be an integer")

    # Transport modes (mutually exclusive for send):
    # - ssl:      implicit TLS (SMTP_SSL), typical port 465 (e.g. 163)
    # - starttls: plain connect then STARTTLS, typical port 587 (e.g. Gmail)
    # - plain:    no encryption (local Mailpit / Mailhog)
    use_ssl = _as_bool(secret.get("use_ssl"), default=None)
    use_tls = _as_bool(secret.get("use_tls"), default=None)
    if use_ssl is None:
        use_ssl = port == 465
    if use_tls is None:
        # Legacy default: STARTTLS on 587 when SSL is not selected.
        use_tls = (not use_ssl) and port == 587
    if use_ssl and use_tls:
        # Prefer implicit SSL when both set (port 465 path).
        use_tls = False

    return {
        "host": host,
        "port": port,
        "username": str(secret.get("username") or secret.get("user") or ""),
        "password": str(secret.get("password") or ""),
        "from_addr": from_addr,
        "use_ssl": bool(use_ssl),
        "use_tls": bool(use_tls),
    }


def _send_smtp(
    *,
    to_email: str,
    subject: str,
    body: str,
    host: str,
    port: int,
    username: str,
    password: str,
    from_addr: str,
    use_ssl: bool,
    use_tls: bool,
) -> None:
    if host.strip().lower() == "test":
        _TEST_SENT.append(
            {
                "to": to_email,
                "subject": subject,
                "body": body,
                "from": from_addr,
            }
        )
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(body)

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, timeout=30, context=context) as smtp:
            if username:
                smtp.login(username, password)
            smtp.send_message(msg)
        return

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if username:
            smtp.login(username, password)
        smtp.send_message(msg)


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    to = str((args or {}).get("to") or "").strip()
    subject = str((args or {}).get("subject") or "")
    body = str((args or {}).get("body") or "")
    if not to:
        return _fail("VALIDATION", "to is required for general/mail")

    cfg = _parse_smtp_secret(secret or {})
    if cfg.get("ok") is False:
        return cfg

    try:
        _send_smtp(
            to_email=to,
            subject=subject,
            body=body,
            host=str(cfg["host"]),
            port=int(cfg["port"]),
            username=str(cfg["username"]),
            password=str(cfg["password"]),
            from_addr=str(cfg["from_addr"]),
            use_ssl=bool(cfg["use_ssl"]),
            use_tls=bool(cfg["use_tls"]),
        )
    except Exception as exc:
        return _fail("PROVIDER", f"SMTP send failed: {exc}")

    stub = str(cfg["host"]).strip().lower() == "test"
    return {
        "ok": True,
        "stub": stub,
        "to": to,
        "subject": subject,
        "body_chars": len(body),
        "boundary": "External",
        "message": "Email sent via SMTP after Vault inject + approval gate",
    }
