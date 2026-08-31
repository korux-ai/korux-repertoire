"""SMTP send — stdlib only; no Korux imports."""

from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from typing import Any

_TEST_SENT: list[dict[str, Any]] = []


def clear_test_sent() -> None:
    _TEST_SENT.clear()


def get_test_sent() -> list[dict[str, Any]]:
    return list(_TEST_SENT)


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _parse_smtp_secret(secret: dict[str, Any]) -> dict[str, Any] | dict[str, Any]:
    if not isinstance(secret, dict):
        return _fail("CREDENTIAL", "Vault secret must be a JSON object")
    host = str(secret.get("host") or "").strip()
    if not host:
        return _fail("CREDENTIAL", "Vault smtp JSON missing host")
    from_addr = str(secret.get("from") or secret.get("from_addr") or "").strip()
    if not from_addr:
        return _fail("CREDENTIAL", "Vault smtp JSON missing from")
    use_tls = secret.get("use_tls")
    if isinstance(use_tls, str):
        use_tls = use_tls.strip().lower() not in {"false", "0", "no"}
    elif use_tls is None:
        use_tls = int(secret.get("port") or 587) == 587
    return {
        "host": host,
        "port": int(secret.get("port") or 587),
        "username": str(secret.get("username") or secret.get("user") or ""),
        "password": str(secret.get("password") or ""),
        "from_addr": from_addr,
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

    if use_tls:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
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
