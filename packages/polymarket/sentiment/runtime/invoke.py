"""Polymarket public sentiment odds — stdlib HTTPS; no Korux imports.

Sentiment reference ONLY — never primary for Fed institutional probabilities.
Language-neutral structured fields.
"""

from __future__ import annotations

import json
import os
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEARCH_URL = "https://gamma-api.polymarket.com/public-search"
EVENTS_URL = "https://gamma-api.polymarket.com/events"
HTTP_TIMEOUT_S = 30
MAX_MARKETS = 15


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    raw = os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip().lower()
    return raw in {"1", "true", "yes"}


def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_get_json(url: str) -> Any:
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
    return json.loads(body)


def _parse_prices(raw: Any) -> list[float]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    out: list[float] = []
    for item in raw:
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            continue
    return out


def _parse_outcomes(raw: Any) -> list[str]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return [raw] if raw else []
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def _market_rows(markets: Any, *, limit: int) -> list[dict[str, Any]]:
    if not isinstance(markets, list):
        return []
    rows: list[dict[str, Any]] = []
    for m in markets:
        if not isinstance(m, dict):
            continue
        outcomes = _parse_outcomes(m.get("outcomes"))
        prices = _parse_prices(m.get("outcomePrices"))
        probs: list[dict[str, Any]] = []
        for i, name in enumerate(outcomes):
            price = prices[i] if i < len(prices) else None
            pct = round(price * 100.0, 2) if isinstance(price, float) else None
            probs.append({"outcome": name, "price": price, "pct": pct})
        rows.append(
            {
                "question": m.get("question") or m.get("slug"),
                "slug": m.get("slug"),
                "active": m.get("active"),
                "closed": m.get("closed"),
                "probabilities": probs,
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _format_content(query: str, events: list[dict[str, Any]]) -> str:
    lines = [
        "Polymarket sentiment (NOT institutional primary):",
        f"- query={query}",
        f"- role=sentiment_only",
        f"- as_of={_now()}",
    ]
    for ev in events:
        lines.append(f"- event={ev.get('title') or ev.get('slug')}")
        for m in ev.get("markets") or []:
            q = m.get("question") or "?"
            bits = []
            for p in m.get("probabilities") or []:
                if p.get("pct") is None:
                    continue
                bits.append(f"{p.get('outcome')}={p.get('pct')}%")
            lines.append(f"  - {q}: " + (", ".join(bits) if bits else "n/a"))
    return "\n".join(lines)


def _mock(query: str) -> dict[str, Any]:
    events = [
        {
            "title": f"Mock market for {query}",
            "slug": "mock-fed",
            "markets": [
                {
                    "question": "Mock: next FOMC hike 25bp?",
                    "slug": "mock-hike",
                    "active": True,
                    "closed": False,
                    "probabilities": [
                        {"outcome": "Yes", "price": 0.52, "pct": 52.0},
                        {"outcome": "No", "price": 0.48, "pct": 48.0},
                    ],
                }
            ],
        }
    ]
    return {
        "role": "sentiment_only",
        "confidence": "mock",
        "source": "mock",
        "as_of": _now(),
        "query": query,
        "events": events,
        "note": "HTTP mock — sentiment reference only",
    }


async def invoke(
    args: dict[str, Any],
    secret: dict[str, Any] | None = None,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = secret, ctx
    payload = args if isinstance(args, dict) else {}
    query = str(payload.get("query") or "").strip()
    slug = str(payload.get("event_slug") or "").strip()
    if not query and not slug:
        return _fail("VALIDATION", "query or event_slug is required")
    try:
        limit = int(payload.get("max_markets") or MAX_MARKETS)
    except (TypeError, ValueError):
        limit = MAX_MARKETS
    limit = max(1, min(limit, MAX_MARKETS))

    if _http_mock():
        bundle = _mock(query or slug)
        content = _format_content(query or slug, bundle["events"])
        return {
            "ok": True,
            "content": content,
            "summary": "Polymarket sentiment (mock)",
            **bundle,
        }

    events_out: list[dict[str, Any]] = []
    try:
        if slug:
            data = _http_get_json(f"{EVENTS_URL}?{urlencode({'slug': slug, 'limit': 1})}")
            rows = data if isinstance(data, list) else []
            for ev in rows[:3]:
                if not isinstance(ev, dict):
                    continue
                events_out.append(
                    {
                        "title": ev.get("title"),
                        "slug": ev.get("slug"),
                        "markets": _market_rows(ev.get("markets"), limit=limit),
                    }
                )
        else:
            data = _http_get_json(f"{SEARCH_URL}?{urlencode({'q': query})}")
            if not isinstance(data, dict):
                return _fail("PROVIDER", "Polymarket search returned unexpected payload")
            for ev in (data.get("events") or [])[:5]:
                if not isinstance(ev, dict):
                    continue
                # public-search events may omit nested markets — refetch by slug when needed
                markets = ev.get("markets")
                if not markets and ev.get("slug"):
                    detail = _http_get_json(
                        f"{EVENTS_URL}?{urlencode({'slug': ev.get('slug'), 'limit': 1})}"
                    )
                    if isinstance(detail, list) and detail and isinstance(detail[0], dict):
                        markets = detail[0].get("markets")
                events_out.append(
                    {
                        "title": ev.get("title"),
                        "slug": ev.get("slug"),
                        "markets": _market_rows(markets, limit=limit),
                    }
                )
    except HTTPError as exc:
        return _fail("PROVIDER", f"Polymarket HTTP {exc.code}")
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        return _fail("PROVIDER", f"Polymarket request failed: {exc}")

    if not events_out:
        return _fail("PROVIDER", "Polymarket returned no matching events")

    content = _format_content(query or slug, events_out)
    return {
        "ok": True,
        "content": content,
        "summary": f"Polymarket sentiment for {query or slug}",
        "role": "sentiment_only",
        "confidence": "prediction_market",
        "source": "polymarket:gamma",
        "as_of": _now(),
        "query": query or None,
        "event_slug": slug or None,
        "events": events_out,
        "note": "Sentiment reference ONLY — never primary for Fed institutional odds",
    }
