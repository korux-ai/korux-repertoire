"""Google Meet identity verify via Google OAuth userinfo. Stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
HTTP_TIMEOUT_S = 20
PROVIDER = "google/meet"


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
        raise RuntimeError(f"google/meet HTTP error: {exc.reason}") from exc


def _access_token(secret: dict[str, Any]) -> dict[str, Any]:
    direct = str(secret.get("access_token") or secret.get("token") or "").strip()
    if direct:
        return {"ok": True, "token": direct}

    client_id = str(secret.get("client_id") or "").strip()
    client_secret = str(secret.get("client_secret") or "").strip()
    refresh_token = str(secret.get("refresh_token") or "").strip()
    if not (client_id and client_secret and refresh_token):
        return _fail(
            "CREDENTIAL",
            "google/meet Vault needs access_token or client_id+client_secret+refresh_token",
        )
    body = urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    status, resp = _request(
        "POST",
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
    )
    if status >= 400:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        return _fail("CREDENTIAL", f"google OAuth refresh failed ({status}): {snippet}")
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "google OAuth returned non-JSON")
    token = str(data.get("access_token") or "").strip()
    if not token:
        return _fail("PROVIDER", "google OAuth missing access_token")
    return {"ok": True, "token": token}


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    meeting_id = str((args or {}).get("meeting_id") or "").strip() or None
    summary = str((args or {}).get("summary") or (args or {}).get("body") or "")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "provider": PROVIDER,
            "user_id": "google-meet-mock-user",
            "email": "mock@example.com",
            "meeting_id": meeting_id,
            "summary": summary,
        }

    try:
        tok = _access_token(secret or {})
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if tok.get("ok") is False:
        return tok

    try:
        status, resp = _request(
            "GET",
            USERINFO_URL,
            headers={"Authorization": f"Bearer {tok['token']}"},
            body=None,
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))

    if status in {401, 403}:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        return _fail("CREDENTIAL", f"google userinfo failed ({status}): {snippet}")
    if status >= 400:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        return _fail("PROVIDER", f"google userinfo {status}: {snippet}")
    try:
        data = json.loads(resp.decode("utf-8")) if resp else {}
    except json.JSONDecodeError:
        data = {}

    user_id = str(data.get("sub") or data.get("id") or "").strip() or None
    email = str(data.get("email") or "").strip() or None
    if not user_id and not email:
        return _fail("PROVIDER", "google userinfo missing sub/email")

    return {
        "ok": True,
        "stub": False,
        "provider": PROVIDER,
        "user_id": user_id,
        "email": email,
        "meeting_id": meeting_id,
        "summary": summary,
        "summary_chars": len(summary),
    }
