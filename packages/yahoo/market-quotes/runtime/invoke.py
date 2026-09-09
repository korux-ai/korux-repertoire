"""Yahoo Finance quotes + short history — stdlib HTTPS; no Korux imports.

Yahoo disabled unofficial multi-symbol ``/v7/finance/quote`` (HTTP 401 /
"User is unable to access this feature"). This package prefers ``/v8/finance/chart``
per symbol (still unofficial / rate-limited) and only tries v7 when a session
crumb is available.
"""

from __future__ import annotations

import json
import os
import ssl
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote as urlquote
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener

QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
CRUMB_URL = "https://query1.finance.yahoo.com/v1/test/getcrumb"
COOKIE_SEED_URL = "https://fc.yahoo.com"
HTTP_TIMEOUT_S = 30
MAX_SYMBOLS = 40
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


_CODE_TO_CLASS: dict[str, str] = {
    "CREDENTIAL": "auth",
    "AUTH": "auth",
    "VALIDATION": "validation",
    "EMPTY": "empty",
    "UNAVAILABLE": "unavailable",
    "TIMEOUT": "unavailable",
    "RATE_LIMITED": "unavailable",
    "PROVIDER": "provider",
}


def _fail(
    code: str,
    message: str,
    *,
    failure_class: str | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    cls = (failure_class or "").strip().lower()
    if cls not in {
        "auth",
        "empty",
        "unavailable",
        "validation",
        "denied",
        "provider",
    }:
        cls = _CODE_TO_CLASS.get(str(code or "").strip().upper(), "provider")
    err: dict[str, Any] = {"class": cls, "code": code, "message": message}
    if retryable:
        err["retryable"] = True
    return {"ok": False, "error": err}


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


class _YahooHttp:
    """Shared cookie jar + browser UA for Yahoo unofficial endpoints."""

    def __init__(self) -> None:
        self._cj = CookieJar()
        self._ctx = ssl.create_default_context()
        self._opener = build_opener(
            HTTPCookieProcessor(self._cj),
            HTTPSHandler(context=self._ctx),
        )
        self._crumb: str | None = None
        self._seeded = False

    def get_json(self, url: str) -> dict[str, Any]:
        body = self.get_text(url)
        data = json.loads(body)
        if not isinstance(data, dict):
            return {}
        return data

    def get_text(self, url: str) -> str:
        req = Request(
            url,
            headers={
                "User-Agent": BROWSER_UA,
                "Accept": "application/json,text/plain,*/*",
            },
            method="GET",
        )
        with self._opener.open(req, timeout=HTTP_TIMEOUT_S) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def ensure_session(self) -> None:
        if self._seeded:
            return
        try:
            # May 404; still often sets A1/A3 cookies.
            self.get_text(COOKIE_SEED_URL)
        except (HTTPError, URLError, TimeoutError, OSError):
            pass
        self._seeded = True

    def crumb(self) -> str | None:
        if self._crumb:
            return self._crumb
        self.ensure_session()
        try:
            raw = self.get_text(CRUMB_URL).strip()
        except (HTTPError, URLError, TimeoutError, OSError):
            return None
        if not raw or "<" in raw or "Too Many" in raw:
            return None
        self._crumb = raw
        return self._crumb


def _quote_row_from_v7(row: dict[str, Any]) -> dict[str, Any]:
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
    return {
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


def _pct_5d_from_closes(closes: list[Any]) -> float | None:
    if not isinstance(closes, list):
        return None
    vals = [float(c) for c in closes if isinstance(c, (int, float))]
    if len(vals) < 2:
        return None
    last = vals[-1]
    base_idx = max(0, len(vals) - 6)
    base = vals[base_idx]
    return _pct(last, base)


def _market_state_from_chart_meta(meta: dict[str, Any]) -> str | None:
    raw = meta.get("marketState")
    if raw:
        return str(raw)
    # Chart meta often omits marketState; infer coarsely from trading periods.
    now = meta.get("regularMarketTime") or meta.get("currentTradingPeriod")
    _ = now
    return None


def _quote_from_chart(http: _YahooHttp, symbol: str, *, want_history: bool) -> dict[str, Any] | None:
    range_ = "1mo" if want_history else "5d"
    path_sym = urlquote(symbol, safe="")
    params = urlencode({"range": range_, "interval": "1d"})
    url = f"{CHART_URL}/{path_sym}?{params}"
    data = http.get_json(url)
    result = (data.get("chart") or {}).get("result")
    if not isinstance(result, list) or not result:
        return None
    first = result[0] if isinstance(result[0], dict) else {}
    meta = first.get("meta") if isinstance(first.get("meta"), dict) else {}
    price = meta.get("regularMarketPrice")
    prev = meta.get("chartPreviousClose")
    if prev is None:
        prev = meta.get("previousClose")
    try:
        price_f = float(price) if price is not None else None
        prev_f = float(prev) if prev is not None else None
    except (TypeError, ValueError):
        price_f, prev_f = None, None
    change_pct = _pct(price_f, prev_f)
    state = _market_state_from_chart_meta(meta)
    as_of = _as_of_iso(meta.get("regularMarketTime"))
    pct5 = None
    if want_history:
        indicators = (first.get("indicators") or {}).get("quote") or []
        if indicators and isinstance(indicators[0], dict):
            pct5 = _pct_5d_from_closes(indicators[0].get("close") or [])
    return {
        "symbol": meta.get("symbol") or symbol,
        "shortName": meta.get("shortName") or meta.get("symbol") or symbol,
        "longName": meta.get("longName"),
        "currency": meta.get("currency"),
        "regularMarketPrice": price_f if price_f is not None else price,
        "regularMarketPreviousClose": prev_f if prev_f is not None else prev,
        "regularMarketChangePercent": change_pct,
        "regularMarketTime": meta.get("regularMarketTime"),
        "marketState": state,
        "as_of": as_of,
        "pct_1d": change_pct,
        "pct_5d": pct5,
        "session_note": _session_note(str(state) if state is not None else None),
        "history_source": "chart",
    }


def _fetch_quotes_v7(http: _YahooHttp, symbols: list[str]) -> list[dict[str, Any]]:
    crumb = http.crumb()
    params: dict[str, str] = {"symbols": ",".join(symbols)}
    if crumb:
        params["crumb"] = crumb
    data = http.get_json(f"{QUOTE_URL}?{urlencode(params)}")
    result = (data.get("quoteResponse") or {}).get("result") or []
    if not isinstance(result, list):
        return []
    quotes: list[dict[str, Any]] = []
    for row in result:
        if isinstance(row, dict):
            quotes.append(_quote_row_from_v7(row))
    return quotes


def _fetch_quotes_chart(
    http: _YahooHttp, symbols: list[str], *, want_history: bool
) -> list[dict[str, Any]]:
    quotes: list[dict[str, Any]] = []
    errors: list[str] = []
    for sym in symbols:
        try:
            row = _quote_from_chart(http, sym, want_history=want_history)
            if row:
                quotes.append(row)
            else:
                errors.append(f"{sym}: empty chart")
        except HTTPError as exc:
            errors.append(f"{sym}: HTTP {exc.code}")
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            errors.append(f"{sym}: {exc}")
    if not quotes and errors:
        raise RuntimeError("; ".join(errors[:5]))
    return quotes


def _fetch_quotes(symbols: list[str], *, want_history: bool) -> list[dict[str, Any]]:
    http = _YahooHttp()
    # Prefer chart: v7 quote is often hard-disabled (401 feature gate).
    try:
        quotes = _fetch_quotes_chart(http, symbols, want_history=want_history)
        if quotes:
            return quotes
    except RuntimeError:
        pass
    except HTTPError:
        pass

    try:
        quotes = _fetch_quotes_v7(http, symbols)
        if quotes and want_history:
            for q in quotes:
                sym = str(q.get("symbol") or "").strip()
                if not sym:
                    continue
                try:
                    enriched = _quote_from_chart(http, sym, want_history=True)
                except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
                    enriched = None
                if enriched and enriched.get("pct_5d") is not None:
                    q["pct_5d"] = enriched["pct_5d"]
                    q["history_source"] = "quote+chart"
        if quotes:
            return quotes
    except HTTPError as exc:
        if exc.code in {401, 403}:
            # Last attempt already preferred chart; surface clear provider message.
            raise
        raise

    return []


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
    want_history = _want_history(payload)
    try:
        if _http_mock():
            quotes = _mock_quotes(symbols)
        else:
            quotes = _fetch_quotes(symbols, want_history=want_history)
    except HTTPError as exc:
        # Soft-degrade so older Specs that still call Yahoo do not abort the whole run.
        if exc.code in {401, 403, 429}:
            as_of = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            msg = (
                f"Yahoo market quotes unavailable (HTTP {exc.code}). "
                "Do not invent prices; prefer web search / FRED for levels."
            )
            return {
                "ok": True,
                "content": msg,
                "summary": msg,
                "quotes": [],
                "symbols": symbols,
                "degraded": True,
                "degraded_reason": f"http_{exc.code}",
                "fetched_at": as_of,
            }
        return _fail("PROVIDER", f"Yahoo HTTP {exc.code}")
    except RuntimeError as exc:
        as_of = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        msg = (
            f"Yahoo market quotes unavailable ({exc}). "
            "Do not invent prices; prefer web search / FRED for levels."
        )
        return {
            "ok": True,
            "content": msg,
            "summary": msg,
            "quotes": [],
            "symbols": symbols,
            "degraded": True,
            "degraded_reason": "chart_fetch_failed",
            "fetched_at": as_of,
        }
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return _fail("PROVIDER", f"Yahoo request failed: {exc}")
    if not quotes:
        as_of = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "ok": True,
            "empty": True,
            "content": "",
            "summary": "Yahoo returned no quotes for the given symbols",
            "quotes": [],
            "symbols": symbols,
            "fetched_at": as_of,
        }
    content = _format_content(quotes)
    return {
        "ok": True,
        "content": content,
        "summary": content.split("\n", 1)[0],
        "quotes": quotes,
        "symbols": symbols,
        "fetched_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
