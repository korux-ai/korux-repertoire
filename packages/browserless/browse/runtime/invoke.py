"""Browserless /content — stdlib HTTPS; no Korux imports."""

from __future__ import annotations

import ipaddress
import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

HTTP_TIMEOUT_S = 90
DEFAULT_MAX_CHARS = 80000
DEFAULT_BASE = "https://production-sfo.browserless.io"


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    raw = os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip().lower()
    return raw in {"1", "true", "yes"}


def _parse_secret(secret: dict[str, Any]) -> dict[str, Any] | dict[str, Any]:
    if not isinstance(secret, dict):
        return _fail("CREDENTIAL", "Vault secret must be a JSON object")
    base_url = str(secret.get("base_url") or secret.get("endpoint") or DEFAULT_BASE).strip().rstrip(
        "/"
    )
    api_key = str(secret.get("api_key") or secret.get("token") or "").strip()
    if not api_key:
        return _fail("CREDENTIAL", "Vault browserless/browse JSON missing api_key")
    return {"base_url": base_url, "api_key": api_key}


def _is_blocked_target(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except Exception:
        return "url is not a valid URL"
    if parsed.scheme not in {"http", "https"}:
        return "url scheme must be http or https"
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return "url host is missing"
    if host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
        return f"refusing to browse blocked host: {host}"
    try:
        ip = ipaddress.ip_address(host)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return f"refusing to browse non-public IP: {host}"
    except ValueError:
        pass
    return None


def _post_text(url: str, body: bytes, headers: dict[str, str]) -> tuple[int, str, str]:
    req = Request(url, data=body, method="POST", headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            raw = resp.read()
            status = int(resp.status)
    except HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        status = int(exc.code)
    except URLError as exc:
        return 0, "", f"Browserless request failed: {exc.reason}"
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        text = ""
    return status, text, ""


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    url = str((args or {}).get("url") or "").strip()
    if not url:
        return _fail("VALIDATION", "url is required")
    blocked = _is_blocked_target(url)
    if blocked:
        return _fail("GOVERNOR_POLICY", blocked)

    try:
        max_chars = int((args or {}).get("max_chars") or DEFAULT_MAX_CHARS)
    except (TypeError, ValueError):
        max_chars = DEFAULT_MAX_CHARS
    max_chars = max(500, min(max_chars, 200000))

    stealth_raw = (args or {}).get("stealth")
    stealth = False
    if isinstance(stealth_raw, bool):
        stealth = stealth_raw
    elif str(stealth_raw or "").strip().lower() in {"1", "true", "yes"}:
        stealth = True

    cfg = _parse_secret(secret or {})
    if cfg.get("ok") is False:
        return cfg

    if _http_mock():
        html = f"<html><body><h1>Mock Browserless</h1><p>{url}</p></body></html>"
        mock = True
    else:
        qs: dict[str, str] = {"token": cfg["api_key"]}
        if stealth:
            qs["stealth"] = "true"
        endpoint = urljoin(cfg["base_url"] + "/", "content") + "?" + urlencode(qs)
        payload = json.dumps({"url": url}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Accept": "text/html, application/json;q=0.9, */*;q=0.8",
            "Authorization": f"Bearer {cfg['api_key']}",
            "User-Agent": "KoruxCapability/1.0 (+https://github.com/korux-ai/korux-repertoire)",
        }
        status, html, err = _post_text(endpoint, payload, headers)
        if err:
            return _fail("PROVIDER", err)
        if status >= 400:
            return _fail("PROVIDER", f"Browserless rejected browse (HTTP {status})")
        if not (html or "").strip():
            return _fail("PROVIDER", "Browserless returned empty HTML")
        mock = False

    truncated = html[:max_chars]
    content = f"URL: {url}\nStealth: {stealth}\n\n{truncated}"
    return {
        "ok": True,
        "stub": mock,
        "url": url,
        "html": truncated,
        "content": content,
        "summary": f"Rendered HTML from {url} ({len(truncated)} chars)",
        "char_count": len(truncated),
        "stealth": stealth,
        "provider": "browserless",
        "boundary": "External",
        "reader": "browserless/browse",
        "message": "Page rendered via Browserless",
    }
