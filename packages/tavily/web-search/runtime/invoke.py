"""Tavily web search — stdlib HTTPS only; no Korux imports."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_TAVILY_BASE = "https://api.tavily.com"
DEFAULT_PROVIDER = "tavily"
MAX_RESULTS_CAP = 10
HTTP_TIMEOUT_S = 45


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    raw = os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip().lower()
    if raw in {"1", "true", "yes"}:
        return True
    wr = os.environ.get("WEB_RESEARCH_MOCK", "").strip().lower()
    return wr in {"1", "true", "yes"}


def _parse_secret(secret: dict[str, Any]) -> dict[str, Any] | dict[str, Any]:
    if not isinstance(secret, dict):
        return _fail("CREDENTIAL", "Vault secret must be a JSON object")
    api_key = str(
        secret.get("api_key") or secret.get("token") or secret.get("tavily_api_key") or ""
    ).strip()
    if not api_key:
        return _fail("CREDENTIAL", "Vault tavily/web-search JSON missing api_key")
    provider = str(secret.get("provider") or DEFAULT_PROVIDER).strip().lower()
    base_url = str(secret.get("base_url") or DEFAULT_TAVILY_BASE).rstrip("/")
    return {"api_key": api_key, "provider": provider, "base_url": base_url}


def _format_research_output(data: dict[str, Any]) -> str:
    parts: list[str] = []
    query = str(data.get("query") or "").strip()
    if query:
        parts.append(f"Query: {query}")
    answer = str(data.get("answer") or "").strip()
    if answer:
        parts.append(f"Answer:\n{answer}")
    for i, row in enumerate(data.get("results") or [], 1):
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or f"Result {i}").strip()
        url = str(row.get("url") or "").strip()
        snippet = str(row.get("content") or row.get("snippet") or "").strip()
        block = f"{i}. {title}"
        if url:
            block += f"\n{url}"
        if snippet:
            block += f"\n{snippet[:1200]}"
        parts.append(block)
    return "\n\n".join(parts).strip()


def _mock_payload(query: str, max_results: int) -> dict[str, Any]:
    q = (query or "").strip() or "mock"
    n = max(1, min(max_results, MAX_RESULTS_CAP))
    results = [
        {
            "title": f"Mock result {i + 1} for {q[:40]}",
            "url": f"https://example.com/mock/{i + 1}",
            "content": f"Snippet {i + 1}: synthetic web excerpt about {q[:80]}.",
            "score": round(1.0 - i * 0.1, 2),
        }
        for i in range(n)
    ]
    return {
        "query": q,
        "answer": f"Mock synthesis for: {q[:120]}",
        "results": results,
        "provider": DEFAULT_PROVIDER,
        "mock": True,
    }


def _post_json(url: str, body: dict[str, Any]) -> tuple[int, dict[str, Any] | None, str]:
    payload = json.dumps(body).encode("utf-8")
    req = Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            raw = resp.read()
            status = int(resp.status)
    except HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        status = int(exc.code)
    except URLError as exc:
        return 0, None, f"Web research API request failed: {exc.reason}"
    try:
        data = json.loads(raw.decode("utf-8") or "null")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, None, "Web research API returned invalid JSON"
    if not isinstance(data, dict):
        return status, None, "Web research API response must be an object"
    return status, data, ""


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    query = str((args or {}).get("query") or (args or {}).get("q") or "").strip()
    if not query:
        return _fail("VALIDATION", "query is required")

    try:
        max_results = int((args or {}).get("max_results") or (args or {}).get("limit") or 5)
    except (TypeError, ValueError):
        max_results = 5
    limit = max(1, min(max_results, MAX_RESULTS_CAP))

    cfg = _parse_secret(secret or {})
    if cfg.get("ok") is False:
        return cfg

    provider = str(cfg["provider"])
    if _http_mock():
        data = _mock_payload(query, limit)
    else:
        if provider != DEFAULT_PROVIDER:
            return _fail("VALIDATION", f"Unsupported tavily/web-search provider: {provider}")
        status, data, err = _post_json(
            f"{cfg['base_url']}/search",
            {
                "api_key": cfg["api_key"],
                "query": query[:500],
                "max_results": limit,
                "include_answer": True,
                "search_depth": "basic",
            },
        )
        if err and data is None:
            return _fail("PROVIDER", err)
        if status >= 400:
            return _fail(
                "PROVIDER",
                f"Web research API rejected search (HTTP {status})",
            )
        assert data is not None
        results = data.get("results")
        if not isinstance(results, list):
            results = []
        data = {
            "query": query,
            "answer": str(data.get("answer") or "").strip() or None,
            "results": [
                {
                    "title": str(r.get("title") or ""),
                    "url": str(r.get("url") or ""),
                    "content": str(r.get("content") or ""),
                    "score": r.get("score"),
                }
                for r in results
                if isinstance(r, dict)
            ],
            "provider": provider,
        }

    content = _format_research_output(data)
    return {
        "ok": True,
        "stub": bool(data.get("mock")),
        "query": data.get("query") or query,
        "answer": data.get("answer"),
        "results": data.get("results") or [],
        "result_count": len(data.get("results") or []),
        "content": content,
        "summary": content,
        "provider": data.get("provider") or provider,
        "boundary": "External",
        "reader": "tavily/web-search",
        "message": "Web research completed via Tavily",
    }
