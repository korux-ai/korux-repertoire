"""Crawl4AI /md fetch — stdlib HTTPS/HTTP; no Korux imports."""

from __future__ import annotations

import ipaddress
import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

HTTP_TIMEOUT_S = 90
DEFAULT_MAX_CHARS = 50000
ALLOWED_FILTERS = {"fit", "raw", "bm25", "llm"}


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    raw = os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip().lower()
    return raw in {"1", "true", "yes"}


def _parse_secret(secret: dict[str, Any]) -> dict[str, Any] | dict[str, Any]:
    if not isinstance(secret, dict):
        return _fail("CREDENTIAL", "Vault secret must be a JSON object")
    base_url = str(secret.get("base_url") or secret.get("endpoint") or "").strip().rstrip("/")
    if not base_url:
        return _fail("CREDENTIAL", "Vault crawl4ai/fetch JSON missing base_url")
    api_key = str(secret.get("api_key") or secret.get("token") or "").strip()
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
        return f"refusing to fetch blocked host: {host}"
    try:
        ip = ipaddress.ip_address(host)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return f"refusing to fetch non-public IP: {host}"
    except ValueError:
        pass
    return None


def _post_json(
    url: str, body: dict[str, Any], headers: dict[str, str]
) -> tuple[int, dict[str, Any] | None, str]:
    payload = json.dumps(body).encode("utf-8")
    req = Request(url, data=payload, method="POST", headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            raw = resp.read()
            status = int(resp.status)
    except HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        status = int(exc.code)
    except URLError as exc:
        return 0, None, f"Crawl4AI request failed: {exc.reason}"
    try:
        data = json.loads(raw.decode("utf-8", errors="replace") or "null")
    except json.JSONDecodeError:
        return status, None, "Crawl4AI returned invalid JSON"
    if not isinstance(data, dict):
        return status, None, "Crawl4AI response must be a JSON object"
    return status, data, ""


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    url = str((args or {}).get("url") or "").strip()
    if not url:
        return _fail("VALIDATION", "url is required")
    blocked = _is_blocked_target(url)
    if blocked:
        return _fail("GOVERNOR_POLICY", blocked)

    filt = str((args or {}).get("filter") or (args or {}).get("f") or "fit").strip().lower()
    if filt not in ALLOWED_FILTERS:
        return _fail("VALIDATION", f"filter must be one of {sorted(ALLOWED_FILTERS)}")
    focus = str((args or {}).get("focus_query") or (args or {}).get("q") or "").strip()
    try:
        max_chars = int((args or {}).get("max_chars") or DEFAULT_MAX_CHARS)
    except (TypeError, ValueError):
        max_chars = DEFAULT_MAX_CHARS
    max_chars = max(500, min(max_chars, 200000))

    cfg = _parse_secret(secret or {})
    if cfg.get("ok") is False:
        return cfg

    if _http_mock():
        markdown = (
            f"# Mock Crawl4AI\n\nFetched `{url}` with filter={filt}.\n\n"
            f"Focus: {focus or '(none)'}\n"
        )
        mock = True
    else:
        endpoint = urljoin(cfg["base_url"] + "/", "md")
        body: dict[str, Any] = {"url": url, "f": filt}
        if focus and filt in {"bm25", "llm"}:
            body["q"] = focus[:500]
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "KoruxCapability/1.0 (+https://github.com/korux-ai/korux-repertoire)",
        }
        if cfg.get("api_key"):
            headers["Authorization"] = f"Bearer {cfg['api_key']}"
        status, data, err = _post_json(endpoint, body, headers)
        if err and data is None:
            return _fail("PROVIDER", err)
        if status >= 400:
            return _fail("PROVIDER", f"Crawl4AI rejected fetch (HTTP {status})")
        assert data is not None
        if data.get("success") is False:
            return _fail("PROVIDER", str(data.get("error") or "Crawl4AI reported failure"))
        markdown = str(data.get("markdown") or "").strip()
        if not markdown:
            return _fail(
                "PROVIDER",
                "Crawl4AI returned empty markdown; try browserless/browse for JS-heavy pages",
            )
        mock = False

    truncated = markdown[:max_chars]
    content = f"URL: {url}\nFilter: {filt}\n\n{truncated}"
    return {
        "ok": True,
        "stub": mock,
        "url": url,
        "filter": filt,
        "markdown": truncated,
        "content": content,
        "summary": f"Fetched markdown from {url} ({len(truncated)} chars)",
        "char_count": len(truncated),
        "provider": "crawl4ai",
        "boundary": "External",
        "reader": "crawl4ai/fetch",
        "message": "Page markdown fetched via Crawl4AI",
    }
