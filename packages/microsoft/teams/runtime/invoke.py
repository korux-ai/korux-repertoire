"""Microsoft Teams identity verify via Microsoft Graph. Stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
HTTP_TIMEOUT_S = 20
PROVIDER = "microsoft/teams"
DEFAULT_SCOPE = "https://graph.microsoft.com/.default"


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {
        "1",
        "true",
        "TRUE",
        "yes",
    }


def _request(method: str, url: str, *, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    req = Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            return int(resp.status), resp.read()
    except HTTPError as exc:
        return int(exc.code), exc.read() if exc.fp else b""
    except URLError as exc:
        raise RuntimeError(f"microsoft/teams HTTP error: {exc.reason}") from exc


def _access_token(secret: dict[str, Any]) -> dict[str, Any]:
    direct = str(secret.get("access_token") or secret.get("token") or "").strip()
    if direct:
        return {"ok": True, "token": direct, "mode": "bearer"}

    tenant_id = str(secret.get("tenant_id") or secret.get("tenant") or "").strip()
    client_id = str(secret.get("client_id") or "").strip()
    client_secret = str(secret.get("client_secret") or "").strip()
    if not (tenant_id and client_id and client_secret):
        return _fail(
            "CREDENTIAL",
            "microsoft/teams Vault needs access_token or tenant_id+client_id+client_secret",
        )
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    body = urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": DEFAULT_SCOPE,
        }
    ).encode("utf-8")
    status, resp = _request(
        "POST",
        url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
    )
    if status >= 400:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        return _fail("CREDENTIAL", f"microsoft OAuth failed ({status}): {snippet}")
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "microsoft OAuth returned non-JSON")
    token = str(data.get("access_token") or "").strip()
    if not token:
        return _fail("PROVIDER", "microsoft OAuth missing access_token")
    return {"ok": True, "token": token, "mode": "app", "tenant_id": tenant_id}


def _graph_get(token: str, path: str) -> tuple[int, bytes]:
    return _request(
        "GET",
        f"{GRAPH_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        body=None,
    )


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    meeting_id = str((args or {}).get("meeting_id") or "").strip() or None
    summary = str((args or {}).get("summary") or (args or {}).get("body") or "")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "provider": PROVIDER,
            "user_id": "teams-mock-user",
            "tenant_id": str((secret or {}).get("tenant_id") or "mock-tenant"),
            "meeting_id": meeting_id,
            "summary": summary,
        }

    try:
        tok = _access_token(secret or {})
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if tok.get("ok") is False:
        return tok

    token = str(tok["token"])
    mode = str(tok.get("mode") or "bearer")
    try:
        if mode == "app":
            status, resp = _graph_get(token, "/organization")
        else:
            status, resp = _graph_get(token, "/me")
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))

    if status in {401, 403}:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        return _fail("CREDENTIAL", f"microsoft graph failed ({status}): {snippet}")
    if status >= 400:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        return _fail("PROVIDER", f"microsoft graph {status}: {snippet}")

    try:
        data = json.loads(resp.decode("utf-8")) if resp else {}
    except json.JSONDecodeError:
        data = {}

    user_id = None
    tenant_id = str(tok.get("tenant_id") or (secret or {}).get("tenant_id") or "").strip() or None
    if mode == "app":
        values = data.get("value") if isinstance(data, dict) else None
        if isinstance(values, list) and values and isinstance(values[0], dict):
            tenant_id = str(values[0].get("id") or tenant_id or "").strip() or tenant_id
            user_id = f"app:{str((secret or {}).get('client_id') or 'client')}"
        if not tenant_id:
            return _fail("PROVIDER", "microsoft organization lookup missing tenant id")
    else:
        user_id = str(data.get("id") or "").strip() or None
        if not user_id:
            return _fail("PROVIDER", "microsoft /me missing id")

    return {
        "ok": True,
        "stub": False,
        "provider": PROVIDER,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "meeting_id": meeting_id,
        "summary": summary,
        "summary_chars": len(summary),
    }
