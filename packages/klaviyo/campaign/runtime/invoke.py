"""Klaviyo email campaigns. Stdlib HTTPS + Private API key.

create: campaign → HTML template → assign template (does not send).
send: campaign-send-jobs for an existing campaign_id.
create_and_send: create path then send.
"""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://a.klaviyo.com"
DEFAULT_REVISION = "2024-10-15"
HTTP_TIMEOUT_S = 60
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
        raise RuntimeError(f"klaviyo HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"klaviyo auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"klaviyo server error ({status})")
    return _fail("PROVIDER", f"klaviyo API {status}: {snippet}")


def _headers(api_key: str, revision: str) -> dict[str, str]:
    return {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "revision": revision,
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


def _secret_cfg(secret: dict[str, Any]) -> dict[str, Any]:
    api_key = str(secret.get("api_key") or secret.get("private_key") or "").strip()
    list_id = str(secret.get("list_id") or "").strip()
    from_email = str(secret.get("from_email") or "").strip()
    from_label = str(secret.get("from_label") or secret.get("from_name") or "").strip()
    revision = str(secret.get("revision") or DEFAULT_REVISION).strip() or DEFAULT_REVISION
    if not api_key or not list_id or not from_email or not from_label:
        return _fail(
            "CREDENTIAL",
            "klaviyo Vault needs api_key, list_id, from_email, from_label",
        )
    return {
        "api_key": api_key,
        "list_id": list_id,
        "from_email": from_email,
        "from_label": from_label,
        "revision": revision,
    }


def _create_campaign(cfg: dict[str, str], *, name: str, subject: str, list_id: str, preview_text: str) -> dict[str, Any]:
    content: dict[str, str] = {
        "subject": subject,
        "from_email": cfg["from_email"],
        "from_label": cfg["from_label"],
    }
    if preview_text:
        content["preview_text"] = preview_text
    payload = {
        "data": {
            "type": "campaign",
            "attributes": {
                "name": name,
                "audiences": {"included": [list_id], "excluded": []},
                "send_strategy": {"method": "immediate"},
                "campaign-messages": {
                    "data": [
                        {
                            "type": "campaign-message",
                            "attributes": {
                                "definition": {
                                    "channel": "email",
                                    "label": name,
                                    "content": content,
                                }
                            },
                        }
                    ]
                },
            },
        }
    }
    status, resp = _request(
        "POST",
        f"{API_BASE}/api/campaigns",
        headers=_headers(cfg["api_key"], cfg["revision"]),
        body=json.dumps(payload).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "klaviyo create campaign returned non-JSON")
    root = data.get("data") if isinstance(data, dict) else None
    if not isinstance(root, dict):
        return _fail("PROVIDER", "klaviyo create campaign missing data")
    campaign_id = str(root.get("id") or "").strip()
    message_id = ""
    included = data.get("included") if isinstance(data.get("included"), list) else []
    for item in included:
        if isinstance(item, dict) and item.get("type") == "campaign-message":
            message_id = str(item.get("id") or "").strip()
            break
    if not message_id:
        rel = ((root.get("relationships") or {}).get("campaign-messages") or {}).get("data")
        if isinstance(rel, list) and rel and isinstance(rel[0], dict):
            message_id = str(rel[0].get("id") or "").strip()
        elif isinstance(rel, dict):
            message_id = str(rel.get("id") or "").strip()
    if not campaign_id or not message_id:
        return _fail("PROVIDER", "klaviyo create campaign missing campaign/message id")
    return {"ok": True, "campaign_id": campaign_id, "message_id": message_id}


def _create_template(cfg: dict[str, str], *, name: str, html: str) -> dict[str, Any]:
    payload = {
        "data": {
            "type": "template",
            "attributes": {
                "name": name[:128] or "korux-template",
                "editor_type": "CODE",
                "html": html,
            },
        }
    }
    status, resp = _request(
        "POST",
        f"{API_BASE}/api/templates",
        headers=_headers(cfg["api_key"], cfg["revision"]),
        body=json.dumps(payload).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "klaviyo create template returned non-JSON")
    tid = str(((data.get("data") or {}) if isinstance(data, dict) else {}).get("id") or "").strip()
    if not tid:
        return _fail("PROVIDER", "klaviyo create template missing id")
    return {"ok": True, "template_id": tid}


def _assign_template(cfg: dict[str, str], *, message_id: str, template_id: str) -> dict[str, Any]:
    payload = {
        "data": {
            "type": "campaign-message",
            "id": message_id,
            "relationships": {
                "template": {"data": {"type": "template", "id": template_id}}
            },
        }
    }
    status, resp = _request(
        "POST",
        f"{API_BASE}/api/campaign-message-assign-template",
        headers=_headers(cfg["api_key"], cfg["revision"]),
        body=json.dumps(payload).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)
    return {"ok": True}


def _send_campaign(cfg: dict[str, str], campaign_id: str) -> dict[str, Any]:
    payload = {
        "data": {
            "type": "campaign-send-job",
            "id": campaign_id,
        }
    }
    status, resp = _request(
        "POST",
        f"{API_BASE}/api/campaign-send-jobs",
        headers=_headers(cfg["api_key"], cfg["revision"]),
        body=json.dumps(payload).encode("utf-8"),
    )
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
    name = str(args.get("name") or subject or "Korux campaign").strip()
    campaign_id = str(args.get("campaign_id") or "").strip()
    preview_text = str(args.get("preview_text") or "").strip()

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
        cid = campaign_id or "mock-klaviyo-campaign"
        return {
            "ok": True,
            "stub": True,
            "campaign_id": cid,
            "message_id": "mock-message",
            "status": "sending" if action in {"send", "create_and_send"} else "draft",
            "content": subject or cid,
            "summary": f"klaviyo {action} {cid}",
        }

    cfg = _secret_cfg(secret or {})
    if cfg.get("ok") is False:
        return cfg
    list_id = str(args.get("list_id") or cfg["list_id"]).strip()

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
                "summary": f"Sent Klaviyo campaign {campaign_id}",
            }

        created = _create_campaign(
            cfg, name=name, subject=subject, list_id=list_id, preview_text=preview_text
        )
        if created.get("ok") is False:
            return created
        campaign_id = str(created["campaign_id"])
        message_id = str(created["message_id"])
        tpl = _create_template(cfg, name=f"{name}-tpl", html=html)
        if tpl.get("ok") is False:
            return tpl
        assigned = _assign_template(
            cfg, message_id=message_id, template_id=str(tpl["template_id"])
        )
        if assigned.get("ok") is False:
            return assigned

        status_label = "draft"
        if action == "create_and_send":
            sent = _send_campaign(cfg, campaign_id)
            if sent.get("ok") is False:
                return sent
            status_label = "sending"

        return {
            "ok": True,
            "stub": False,
            "campaign_id": campaign_id,
            "message_id": message_id,
            "status": status_label,
            "content": subject,
            "summary": f"Klaviyo campaign {campaign_id} ({status_label})",
        }
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
