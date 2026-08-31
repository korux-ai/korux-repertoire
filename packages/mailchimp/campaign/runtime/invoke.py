"""Mailchimp Marketing API campaigns. Stdlib HTTPS only.

Default action=create builds a saved regular campaign + content (does not send).
action=send sends an existing campaign_id.
action=create_and_send creates, sets content, then sends immediately.
"""

from __future__ import annotations

import base64
import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HTTP_TIMEOUT_S = 45
MAX_HTML = 200000


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {"1", "true", "TRUE", "yes"}


def _request(method: str, url: str, *, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    req = Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            return int(resp.status), resp.read()
    except HTTPError as exc:
        return int(exc.code), exc.read() if exc.fp else b""
    except URLError as exc:
        raise RuntimeError(f"mailchimp HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"mailchimp auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"mailchimp server error ({status})")
    return _fail("PROVIDER", f"mailchimp API {status}: {snippet}")


def _server_prefix(api_key: str, explicit: str) -> str:
    if explicit.strip():
        return explicit.strip()
    if "-" in api_key:
        return api_key.rsplit("-", 1)[-1].strip()
    return ""


def _secret_cfg(secret: dict[str, Any]) -> dict[str, Any]:
    api_key = str(secret.get("api_key") or secret.get("token") or "").strip()
    list_id = str(secret.get("list_id") or "").strip()
    from_name = str(secret.get("from_name") or "").strip()
    reply_to = str(secret.get("reply_to") or secret.get("from_email") or "").strip()
    prefix = _server_prefix(api_key, str(secret.get("server_prefix") or ""))
    if not api_key or not list_id or not from_name or not reply_to or not prefix:
        return _fail(
            "CREDENTIAL",
            "mailchimp Vault needs api_key (with -dc suffix or server_prefix), list_id, from_name, reply_to",
        )
    basic = base64.b64encode(f"anystring:{api_key}".encode("utf-8")).decode("ascii")
    return {
        "api_key": api_key,
        "list_id": list_id,
        "from_name": from_name,
        "reply_to": reply_to,
        "base": f"https://{prefix}.api.mailchimp.com/3.0",
        "auth": f"Basic {basic}",
    }


def _headers(cfg: dict[str, str]) -> dict[str, str]:
    return {
        "Authorization": cfg["auth"],
        "Content-Type": "application/json",
    }


def _create_campaign(cfg: dict[str, str], *, subject: str, title: str, list_id: str, from_name: str, reply_to: str) -> dict[str, Any]:
    payload = {
        "type": "regular",
        "recipients": {"list_id": list_id},
        "settings": {
            "subject_line": subject,
            "title": title or subject,
            "from_name": from_name,
            "reply_to": reply_to,
        },
    }
    status, resp = _request(
        "POST",
        f"{cfg['base']}/campaigns",
        headers=_headers(cfg),
        body=json.dumps(payload).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "mailchimp create campaign returned non-JSON")
    campaign_id = str(data.get("id") or "").strip()
    if not campaign_id:
        return _fail("PROVIDER", "mailchimp create campaign missing id")
    return {"ok": True, "campaign_id": campaign_id, "status": str(data.get("status") or "save")}


def _set_content(cfg: dict[str, str], campaign_id: str, *, html: str, text: str) -> dict[str, Any]:
    body: dict[str, str] = {"html": html}
    if text.strip():
        body["plain_text"] = text
    status, resp = _request(
        "PUT",
        f"{cfg['base']}/campaigns/{campaign_id}/content",
        headers=_headers(cfg),
        body=json.dumps(body).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)
    return {"ok": True}


def _send_campaign(cfg: dict[str, str], campaign_id: str) -> dict[str, Any]:
    status, resp = _request(
        "POST",
        f"{cfg['base']}/campaigns/{campaign_id}/actions/send",
        headers=_headers(cfg),
        body=b"",
    )
    # Mailchimp often returns 204 No Content on send.
    if status >= 400:
        return _provider_fail(status, resp)
    return {"ok": True, "status": "sending"}


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    args = args or {}
    action = str(args.get("action") or "create").strip().lower()
    if action not in {"create", "send", "create_and_send"}:
        return _fail("VALIDATION", "action must be create, send, or create_and_send")

    subject = str(args.get("subject") or "").strip()
    html = str(args.get("html") or args.get("body") or "").strip()
    text = str(args.get("text") or "").strip()
    title = str(args.get("title") or "").strip()
    campaign_id = str(args.get("campaign_id") or "").strip()

    if action in {"create", "create_and_send"}:
        if not subject:
            return _fail("VALIDATION", "subject is required")
        if not html:
            return _fail("VALIDATION", "html is required")
        if len(html) > MAX_HTML:
            return _fail("VALIDATION", f"html exceeds {MAX_HTML} characters")
    if action == "send" and not campaign_id:
        return _fail("VALIDATION", "campaign_id is required when action=send")

    if _http_mock():
        cid = campaign_id or "mock-campaign"
        return {
            "ok": True,
            "stub": True,
            "campaign_id": cid,
            "status": "sending" if action in {"send", "create_and_send"} else "save",
            "content": subject or cid,
            "summary": f"mailchimp {action} {cid}",
        }

    cfg = _secret_cfg(secret or {})
    if cfg.get("ok") is False:
        return cfg

    list_id = str(args.get("list_id") or cfg["list_id"]).strip()
    from_name = str(args.get("from_name") or cfg["from_name"]).strip()
    reply_to = str(args.get("reply_to") or cfg["reply_to"]).strip()

    try:
        if action == "send":
            sent = _send_campaign(cfg, campaign_id)
            if sent.get("ok") is False:
                return sent
            return {
                "ok": True,
                "stub": False,
                "campaign_id": campaign_id,
                "status": "sending",
                "content": subject or campaign_id,
                "summary": f"Sent Mailchimp campaign {campaign_id}",
            }

        created = _create_campaign(
            cfg,
            subject=subject,
            title=title,
            list_id=list_id,
            from_name=from_name,
            reply_to=reply_to,
        )
        if created.get("ok") is False:
            return created
        campaign_id = str(created["campaign_id"])
        content = _set_content(cfg, campaign_id, html=html, text=text)
        if content.get("ok") is False:
            return content

        status_label = str(created.get("status") or "save")
        if action == "create_and_send":
            sent = _send_campaign(cfg, campaign_id)
            if sent.get("ok") is False:
                return sent
            status_label = "sending"

        return {
            "ok": True,
            "stub": False,
            "campaign_id": campaign_id,
            "status": status_label,
            "content": subject,
            "summary": f"Mailchimp campaign {campaign_id} ({status_label})",
        }
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
