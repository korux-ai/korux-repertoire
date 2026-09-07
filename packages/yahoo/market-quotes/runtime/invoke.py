"""Yahoo Finance quotes — stdlib HTTPS; no Korux imports."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
HTTP_TIMEOUT_S = 30
MAX_SYMBOLS = 20


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    raw = os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip().lower()
    return raw in {"1", "true", "yes"}


def _normalize_symbols(args: dict[str, Any]) -> list[str]:
    raw = args.get("symbols")
    if raw is None and args.get("symbol"):
        raw = [args.get("symbol")]
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.replace(";", ",").split(",")]
        return [p for p in parts if p][:MAX_SYMBOLS]
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        s = str(item or "").strip()
        if s:
            out.append(s)
        if len(out) >= MAX_SYMBOLS:
            break
    return out


def _format_content(quotes: list[dict[str, Any]]) -> str:
    lines: list[str] = ["Yahoo market quotes:"]
    for q in quotes:
        sym = q.get("symbol") or "?"
        price = q.get("regularMarketPrice")
        prev = q.get("regularMarketPreviousClose")
        currency = q.get("currency") or ""
        name = q.get("shortName") or q.get("longName") or ""
        bit = f"- {sym}"
        if name:
            bit += f" ({name})"
        if price is not None:
            bit += f": {price}"
            if currency:
                bit += f" {currency}"
        if prev is not None:
            bit += f" (prev close {prev})"
        lines.append(bit)
    return "\n".join(lines)


def _mock_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    out = []
    for i, sym in enumerate(symbols):
        out.append(
            {
                "symbol": sym,
                "shortName": f"Mock {sym}",
                "currency": "USD",
                "regularMarketPrice": 100.0 + i,
                "regularMarketPreviousClose": 99.0 + i,
                "regularMarketTime": None,
            }
        )
    return out


def _fetch_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    params = urlencode({"symbols": ",".join(symbols)})
    url = f"{QUOTE_URL}?{params}"
    req = Request(
        url,
        headers={
            "User-Agent": "KoruxCapability/1.0 (+https://github.com/korux-ai)",
            "Accept": "application/json",
        },
        method="GET",
    )
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    data = json.loads(body)
    result = (data.get("quoteResponse") or {}).get("result") or []
    if not isinstance(result, list):
        return []
    quotes: list[dict[str, Any]] = []
    for row in result:
        if not isinstance(row, dict):
            continue
        quotes.append(
            {
                "symbol": row.get("symbol"),
                "shortName": row.get("shortName"),
                "longName": row.get("longName"),
                "currency": row.get("currency"),
                "regularMarketPrice": row.get("regularMarketPrice"),
                "regularMarketPreviousClose": row.get("regularMarketPreviousClose"),
                "regularMarketTime": row.get("regularMarketTime"),
                "marketState": row.get("marketState"),
            }
        )
    return quotes


async def invoke(
    args: dict[str, Any],
    secret: dict[str, Any] | None = None,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = secret, ctx
    symbols = _normalize_symbols(args if isinstance(args, dict) else {})
    if not symbols:
        return _fail("VALIDATION", "symbols is required (non-empty list)")
    try:
        if _http_mock():
            quotes = _mock_quotes(symbols)
        else:
            quotes = _fetch_quotes(symbols)
    except HTTPError as exc:
        return _fail("PROVIDER", f"Yahoo HTTP {exc.code}")
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return _fail("PROVIDER", f"Yahoo request failed: {exc}")
    if not quotes:
        return _fail("PROVIDER", "Yahoo returned no quotes for the given symbols")
    content = _format_content(quotes)
    return {
        "ok": True,
        "content": content,
        "summary": content.split("\n", 1)[0],
        "quotes": quotes,
        "symbols": symbols,
    }
