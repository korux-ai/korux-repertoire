"""WordPress REST API create post. Application Passwords + stdlib HTTPS."""

from __future__ import annotations

import base64
import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

HTTP_TIMEOUT_S = 40
MAX_CONTENT = 200000
ALLOWED_STATUS = frozenset({"draft", "publish", "pending", "private"})


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
        raise RuntimeError(f"wordpress HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"wordpress auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"wordpress server error ({status})")
    return _fail("PROVIDER", f"wordpress API {status}: {snippet}")


def _normalize_site_url(raw: str) -> dict[str, Any]:
    site = str(raw or "").strip().rstrip("/")
    if not site:
        return _fail("CREDENTIAL", "site_url is required")
    parsed = urlparse(site)
    if parsed.scheme not in {"https", "http"}:
        return _fail("VALIDATION", "site_url must be http(s)")
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1"}:
        return _fail("VALIDATION", "site_url must use https (http only allowed for localhost)")
    return {"ok": True, "site_url": site}


def _secret_cfg(secret: dict[str, Any]) -> dict[str, Any]:
    site = _normalize_site_url(str(secret.get("site_url") or secret.get("base_url") or ""))
    if site.get("ok") is False:
        return site
    username = str(secret.get("username") or secret.get("user") or "").strip()
    password = str(
        secret.get("application_password")
        or secret.get("app_password")
        or secret.get("password")
        or ""
    ).strip().replace(" ", "")
    if not username or not password:
        return _fail("CREDENTIAL", "wordpress Vault needs username and application_password")
    basic = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {
        "ok": True,
        "site_url": site["site_url"],
        "auth": f"Basic {basic}",
    }


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    args = args or {}
    title = str(args.get("title") or "").strip()
    content = str(args.get("content") or args.get("body") or "").strip()
    status = str(args.get("status") or "draft").strip().lower() or "draft"
    excerpt = str(args.get("excerpt") or "").strip()
    slug = str(args.get("slug") or "").strip()

    if not title:
        return _fail("VALIDATION", "title is required")
    if not content:
        return _fail("VALIDATION", "content is required")
    if len(content) > MAX_CONTENT:
        return _fail("VALIDATION", f"content exceeds {MAX_CONTENT} characters")
    if status not in ALLOWED_STATUS:
        return _fail("VALIDATION", f"status must be one of {sorted(ALLOWED_STATUS)}")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "post_id": "1",
            "link": "https://example.com/?p=1",
            "status": status,
            "content": title,
            "summary": title,
        }

    cfg = _secret_cfg(secret or {})
    if cfg.get("ok") is False:
        return cfg

    payload: dict[str, Any] = {
        "title": title,
        "content": content,
        "status": status,
    }
    if excerpt:
        payload["excerpt"] = excerpt
    if slug:
        payload["slug"] = slug

    url = f"{cfg['site_url']}/wp-json/wp/v2/posts"
    try:
        code, resp = _request(
            "POST",
            url,
            headers={
                "Authorization": cfg["auth"],
                "Content-Type": "application/json",
            },
            body=json.dumps(payload).encode("utf-8"),
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if code >= 400:
        return _provider_fail(code, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "wordpress create post returned non-JSON")
    post_id = str(data.get("id") or "").strip()
    if not post_id:
        return _fail("PROVIDER", "wordpress create post missing id")
    link = str(data.get("link") or "").strip()
    return {
        "ok": True,
        "stub": False,
        "post_id": post_id,
        "link": link or None,
        "status": str(data.get("status") or status),
        "content": title,
        "summary": title,
    }
