"""Zoom identity verify. Stdlib HTTPS only."""

from __future__ import annotations

import base64
import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_BASE = "https://api.zoom.us"
HTTP_TIMEOUT_S = 20


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
        raise RuntimeError(f"zoom HTTP error: {exc.reason}") from exc


def _access_token(secret: dict[str, Any], base: str) -> dict[str, Any]:
    token = str(secret.get("token") or secret.get("access_token") or "").strip()
    if token:
        return {"ok": True, "token": token}
    account_id = str(secret.get("account_id") or "").strip()
    client_id = str(secret.get("client_id") or "").strip()
    client_secret = str(secret.get("client_secret") or "").strip()
    if not (account_id and client_id and client_secret):
        return _fail("CREDENTIAL", "zoom Vault needs token or account_id+client_id+client_secret")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    url = f"{base}/oauth/token?" + urlencode(
        {"grant_type": "account_credentials", "account_id": account_id}
    )
    status, resp = _request(
        "POST",
        url,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body=b"",
    )
    if status >= 400:
        return _fail("CREDENTIAL", f"zoom OAuth failed ({status})")
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "zoom OAuth returned non-JSON")
    access = str((data or {}).get("access_token") or "").strip()
    if not access:
        return _fail("PROVIDER", "zoom OAuth missing access_token")
    return {"ok": True, "token": access}


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    meeting_id = str((args or {}).get("meeting_id") or "").strip() or None
    summary = str((args or {}).get("summary") or (args or {}).get("body") or "")
    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "user_id": "zoom-mock-user",
            "account_id": str((secret or {}).get("account_id") or "mock-account"),
            "meeting_id": meeting_id,
            "summary": summary,
        }

    base = str((secret or {}).get("base_url") or DEFAULT_BASE).rstrip("/")
    try:
        tok = _access_token(secret or {}, base)
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if tok.get("ok") is False:
        return tok
    token = str(tok["token"])
    try:
        status, resp = _request(
            "GET",
            f"{base}/v2/users/me",
            headers={"Authorization": f"Bearer {token}"},
            body=None,
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"zoom identity failed ({status})")
    if status >= 400:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        return _fail("PROVIDER", f"zoom API {status}: {snippet}")
    try:
        data = json.loads(resp.decode("utf-8")) if resp else {}
    except json.JSONDecodeError:
        data = {}
    return {
        "ok": True,
        "stub": False,
        "user_id": str((data or {}).get("id") or "") or None,
        "account_id": str((data or {}).get("account_id") or (secret or {}).get("account_id") or "") or None,
        "meeting_id": meeting_id,
        "summary": summary,
        "summary_chars": len(summary),
    }
