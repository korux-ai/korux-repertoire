"""SearXNG metasearch — stdlib HTTPS only; no Korux imports."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

MAX_RESULTS_CAP = 20
HTTP_TIMEOUT_S = 45


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
        return _fail("CREDENTIAL", "Vault searxng/search JSON missing base_url")
    api_key = str(
        secret.get("api_key") or secret.get("token") or secret.get("authorization") or ""
    ).strip()
    return {"base_url": base_url, "api_key": api_key}


def _format_content(query: str, results: list[dict[str, Any]]) -> str:
    parts: list[str] = [f"Query: {query}", f"Results: {len(results)}"]
    for i, row in enumerate(results, 1):
        title = str(row.get("title") or f"Result {i}").strip()
        url = str(row.get("url") or "").strip()
        snippet = str(row.get("content") or row.get("snippet") or "").strip()
        engine = str(row.get("engine") or "").strip()
        block = f"{i}. {title}"
        if url:
            block += f"\n{url}"
        if engine:
            block += f"\nengine: {engine}"
        if snippet:
            block += f"\n{snippet[:1200]}"
        parts.append(block)
    return "\n\n".join(parts).strip()


def _mock_results(query: str, limit: int) -> list[dict[str, Any]]:
    q = (query or "").strip() or "mock"
    return [
        {
            "title": f"Mock SearXNG hit {i + 1} for {q[:40]}",
            "url": f"https://example.com/searxng/{i + 1}",
            "content": f"Snippet {i + 1}: metasearch excerpt about {q[:80]}.",
            "engine": "mock",
        }
        for i in range(limit)
    ]


def _get_json(url: str, headers: dict[str, str]) -> tuple[int, dict[str, Any] | None, str]:
    req = Request(url, headers=headers, method="GET")
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            raw = resp.read()
            status = int(resp.status)
    except HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        status = int(exc.code)
    except URLError as exc:
        return 0, None, f"SearXNG request failed: {exc.reason}"
    try:
        text = raw.decode("utf-8", errors="replace")
        data = json.loads(text or "null")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None, "SearXNG returned non-JSON (enable search.formats json in settings.yml)"
    if not isinstance(data, dict):
        return status, None, "SearXNG response must be a JSON object"
    return status, data, ""


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    query = str((args or {}).get("query") or (args or {}).get("q") or "").strip()
    if not query:
        return _fail("VALIDATION", "query is required")

    try:
        max_results = int((args or {}).get("max_results") or (args or {}).get("limit") or 10)
    except (TypeError, ValueError):
        max_results = 10
    limit = max(1, min(max_results, MAX_RESULTS_CAP))

    language = str((args or {}).get("language") or "all").strip() or "all"
    categories = str((args or {}).get("categories") or "").strip()

    cfg = _parse_secret(secret or {})
    if cfg.get("ok") is False:
        return cfg

    if _http_mock():
        results = _mock_results(query, limit)
        mock = True
    else:
        params: dict[str, Any] = {"q": query[:500], "format": "json", "language": language}
        if categories:
            params["categories"] = categories
        url = urljoin(cfg["base_url"] + "/", "search") + "?" + urlencode(params)
        headers = {
            "Accept": "application/json",
            "User-Agent": "KoruxCapability/1.0 (+https://github.com/korux-ai/korux-repertoire)",
        }
        if cfg.get("api_key"):
            headers["Authorization"] = f"Bearer {cfg['api_key']}"
        status, data, err = _get_json(url, headers)
        if err and data is None:
            return _fail("PROVIDER", err)
        if status >= 400:
            return _fail("PROVIDER", f"SearXNG rejected search (HTTP {status})")
        assert data is not None
        raw_results = data.get("results")
        if not isinstance(raw_results, list):
            raw_results = []
        results = []
        for row in raw_results:
            if not isinstance(row, dict):
                continue
            results.append(
                {
                    "title": str(row.get("title") or ""),
                    "url": str(row.get("url") or ""),
                    "content": str(row.get("content") or ""),
                    "engine": str(row.get("engine") or ""),
                    "score": row.get("score"),
                }
            )
            if len(results) >= limit:
                break
        mock = False

    content = _format_content(query, results)
    return {
        "ok": True,
        "stub": mock,
        "query": query,
        "language": language,
        "results": results,
        "result_count": len(results),
        "content": content,
        "summary": content.split("\n\n", 1)[0] if content else "",
        "provider": "searxng",
        "boundary": "External",
        "reader": "searxng/search",
        "message": "Metasearch completed via SearXNG",
    }
