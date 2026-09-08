"""Yahoo Finance quotes + short history — stdlib HTTPS; no Korux imports."""

from __future__ import annotations

import json
import os
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
HTTP_TIMEOUT_S = 30
MAX_SYMBOLS = 40


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


def _want_history(args: dict[str, Any]) -> bool:
    raw = args.get("include_history")
    if raw is None:
        return True
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _pct(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None:
        return None
    if prev == 0:
        return None
    return round((curr - prev) / prev * 100.0, 4)


def _as_of_iso(epoch: Any) -> str | None:
    try:
        ts = int(epoch)
    except (TypeError, ValueError):
        return None
    if ts <= 0:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_content(quotes: list[dict[str, Any]]) -> str:
    lines: list[str] = ["Yahoo market quotes:"]
    for q in quotes:
        sym = q.get("symbol") or "?"
        price = q.get("regularMarketPrice")
        currency = q.get("currency") or ""
        name = q.get("shortName") or q.get("longName") or ""
        state = q.get("marketState") or ""
        as_of = q.get("as_of") or ""
        p1 = q.get("pct_1d")
        p5 = q.get("pct_5d")
        bit = f"- {sym}"
        if name:
            bit += f" ({name})"
        if price is not None:
            bit += f": {price}"
            if currency:
                bit += f" {currency}"
        if p1 is not None:
            bit += f" | %1D {p1:+.2f}%"
        if p5 is not None:
            bit += f" | %5D {p5:+.2f}%"
        if state:
            bit += f" | state={state}"
        if as_of:
            bit += f" | as_of={as_of}"
        if q.get("session_note"):
            bit += f" | note={q['session_note']}"
        lines.append(bit)
    return "\n".join(lines)


def _session_note(market_state: str | None) -> str | None:
    state = str(market_state or "").strip().upper()
    if state in {"CLOSED", "PREPRE", "POSTPOST"}:
        return "session_closed_or_inactive"
    if state in {"PRE", "POST"}:
        return "extended_hours_or_prepost"
    if state == "REGULAR":
        return None
    if state:
        return f"market_state_{state.lower()}"
    return "market_state_unknown"


def _mock_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    out = []
    as_of = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i, sym in enumerate(symbols):
        price = 100.0 + i
        prev = 99.0 + i
        close_5 = 98.0 + i
        out.append(
            {
                "symbol": sym,
                "shortName": f"Mock {sym}",
                "currency": "USD",
                "regularMarketPrice": price,
                "regularMarketPreviousClose": prev,
                "regularMarketChangePercent": _pct(price, prev),
                "regularMarketTime": None,
                "marketState": "CLOSED",
                "as_of": as_of,
                "pct_1d": _pct(price, prev),
                "pct_5d": _pct(price, close_5),
                "session_note": "session_closed_or_inactive",
                "history_source": "mock",
            }
        )
    return out


def _http_get_json(url: str) -> dict[str, Any]:
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
    if not isinstance(data, dict):
        return {}
    return data


def _fetch_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    params = urlencode({"symbols": ",".join(symbols)})
    data = _http_get_json(f"{QUOTE_URL}?{params}")
    result = (data.get("quoteResponse") or {}).get("result") or []
    if not isinstance(result, list):
        return []
    quotes: list[dict[str, Any]] = []
    for row in result:
        if not isinstance(row, dict):
            continue
        price = row.get("regularMarketPrice")
        prev = row.get("regularMarketPreviousClose")
        change_pct = row.get("regularMarketChangePercent")
        if change_pct is None:
            try:
                change_pct = _pct(
                    float(price) if price is not None else None,
                    float(prev) if prev is not None else None,
                )
            except (TypeError, ValueError):
                change_pct = None
        state = row.get("marketState")
        as_of = _as_of_iso(row.get("regularMarketTime"))
        quotes.append(
            {
                "symbol": row.get("symbol"),
                "shortName": row.get("shortName"),
                "longName": row.get("longName"),
                "currency": row.get("currency"),
                "regularMarketPrice": price,
                "regularMarketPreviousClose": prev,
                "regularMarketChangePercent": change_pct,
                "regularMarketTime": row.get("regularMarketTime"),
                "marketState": state,
                "as_of": as_of,
                "pct_1d": round(float(change_pct), 4)
                if isinstance(change_pct, (int, float))
                else change_pct,
                "pct_5d": None,
                "session_note": _session_note(str(state) if state is not None else None),
                "history_source": "quote",
            }
        )
    return quotes


def _fetch_pct_5d(symbol: str) -> float | None:
    """Compute ~5 trading-day % change from daily chart closes."""
    params = urlencode({"range": "1mo", "interval": "1d"})
    url = f"{CHART_URL}/{symbol}?{params}"
    try:
        data = _http_get_json(url)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    result = (data.get("chart") or {}).get("result")
    if not isinstance(result, list) or not result:
        return None
    first = result[0] if isinstance(result[0], dict) else {}
    indicators = (first.get("indicators") or {}).get("quote") or []
    if not indicators or not isinstance(indicators[0], dict):
        return None
    closes = indicators[0].get("close") or []
    if not isinstance(closes, list):
        return None
    vals = [float(c) for c in closes if isinstance(c, (int, float))]
    if len(vals) < 2:
        return None
    last = vals[-1]
    base_idx = max(0, len(vals) - 6)
    base = vals[base_idx]
    return _pct(last, base)


def _enrich_history(quotes: list[dict[str, Any]]) -> None:
    for q in quotes:
        sym = str(q.get("symbol") or "").strip()
        if not sym:
            continue
        pct5 = _fetch_pct_5d(sym)
        if pct5 is not None:
            q["pct_5d"] = pct5
            q["history_source"] = "quote+chart"


async def invoke(
    args: dict[str, Any],
    secret: dict[str, Any] | None = None,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = secret, ctx
    payload = args if isinstance(args, dict) else {}
    symbols = _normalize_symbols(payload)
    if not symbols:
        return _fail("VALIDATION", "symbols is required (non-empty list)")
    try:
        if _http_mock():
            quotes = _mock_quotes(symbols)
        else:
            quotes = _fetch_quotes(symbols)
            if quotes and _want_history(payload):
                _enrich_history(quotes)
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
        "fetched_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
