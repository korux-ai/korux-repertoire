"""Fed policy probability snapshot — stdlib HTTPS; no Korux imports.

Primary: Owner-configured or default institutional proxy JSON.
Optional secondary: Yahoo 30-Day Fed Funds futures (ZQ=F) settle heuristic.
Always language-neutral structured fields; compose chooses prose language.
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

DEFAULT_BASE = "https://rateprobability.com"
DEFAULT_PATH = "/api/fed/latest"
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
HTTP_TIMEOUT_S = 30


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    raw = os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip().lower()
    return raw in {"1", "true", "yes"}


def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truthy(raw: Any, default: bool = False) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _http_get_json(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    hdrs = {
        "User-Agent": "KoruxCapability/1.0 (+https://github.com/korux-ai)",
        "Accept": "application/json",
    }
    if headers:
        hdrs.update(headers)
    req = Request(url, headers=hdrs, method="GET")
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


def _normalize_meetings(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        item = {
            "label": row.get("label") or row.get("name") or row.get("meeting") or row.get("date"),
            "date": row.get("date") or row.get("meeting_date"),
            "hike_pct": row.get("hike_pct")
            or row.get("hike_probability")
            or row.get("increase_pct"),
            "cut_pct": row.get("cut_pct") or row.get("cut_probability") or row.get("ease_pct"),
            "hold_pct": row.get("hold_pct")
            or row.get("no_change_pct")
            or row.get("unchanged_pct"),
        }
        # Pass through nested summary fields if present.
        for key in ("summary", "probabilities", "outcomes"):
            if key in row:
                item[key] = row[key]
        out.append(item)
    return out


def _parse_primary_payload(data: dict[str, Any], *, source: str) -> dict[str, Any]:
    primary = data.get("primary") if isinstance(data.get("primary"), dict) else data
    meetings = _normalize_meetings(
        primary.get("meetings") or data.get("meetings") or primary.get("fomc")
    )
    summary = primary.get("summary") if isinstance(primary.get("summary"), dict) else {}
    as_of = (
        primary.get("as_of")
        or primary.get("asOf")
        or data.get("as_of")
        or summary.get("as_of")
        or _now()
    )
    return {
        "role": "primary",
        "confidence": "institutional_proxy",
        "source": source,
        "as_of": as_of,
        "meetings": meetings,
        "summary": summary or {
            k: primary.get(k)
            for k in (
                "sep_hike_pct",
                "oct_hike_pct",
                "year_end_hike_pct",
                "next_hike_pct",
                "next_hold_pct",
            )
            if primary.get(k) is not None
        },
        "raw_keys": sorted(list(data.keys()))[:40],
    }


def _format_content(bundle: dict[str, Any]) -> str:
    lines = [
        "Fed policy probabilities:",
        f"- role={bundle.get('role')} confidence={bundle.get('confidence')}",
        f"- source={bundle.get('source')}",
        f"- as_of={bundle.get('as_of')}",
    ]
    if bundle.get("refresh_required"):
        lines.append("- refresh_required=true")
    summary = bundle.get("summary") or {}
    if isinstance(summary, dict) and summary:
        for k, v in summary.items():
            lines.append(f"- summary.{k}={v}")
    for m in bundle.get("meetings") or []:
        if not isinstance(m, dict):
            continue
        lines.append(
            "- meeting={label} date={date} hike={hike} hold={hold} cut={cut}".format(
                label=m.get("label") or "?",
                date=m.get("date") or "?",
                hike=m.get("hike_pct"),
                hold=m.get("hold_pct"),
                cut=m.get("cut_pct"),
            )
        )
    note = bundle.get("note")
    if note:
        lines.append(f"- note={note}")
    return "\n".join(lines)


def _mock_bundle() -> dict[str, Any]:
    return {
        "role": "primary",
        "confidence": "mock",
        "source": "mock",
        "as_of": _now(),
        "refresh_required": False,
        "meetings": [
            {
                "label": "next_fomc",
                "date": "2026-09-16",
                "hike_pct": 60.0,
                "hold_pct": 40.0,
                "cut_pct": 0.0,
            }
        ],
        "summary": {"next_hike_pct": 60.0, "next_hold_pct": 40.0},
        "note": "HTTP mock — not for production decisions",
    }


def _yahoo_zq_backup() -> dict[str, Any]:
    """Secondary under-anchored hint from front Fed Funds futures quote."""
    params = urlencode({"symbols": "ZQ=F"})
    data = _http_get_json(f"{YAHOO_QUOTE_URL}?{params}")
    rows = (data.get("quoteResponse") or {}).get("result") or []
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise ValueError("ZQ=F quote missing")
    row = rows[0]
    price = row.get("regularMarketPrice") or row.get("regularMarketPreviousClose")
    # CME 30-day FF futures quote ≈ 100 - implied rate (%). Not a meeting probability.
    implied_rate = None
    try:
        if price is not None:
            implied_rate = round(100.0 - float(price), 4)
    except (TypeError, ValueError):
        implied_rate = None
    as_of = None
    try:
        ts = int(row.get("regularMarketTime") or 0)
        if ts > 0:
            as_of = datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
    except (TypeError, ValueError):
        as_of = None
    return {
        "role": "secondary",
        "confidence": "under_anchored",
        "source": "yahoo:ZQ=F",
        "as_of": as_of or _now(),
        "refresh_required": True,
        "meetings": [],
        "summary": {
            "zq_price": price,
            "implied_ff_rate_pct": implied_rate,
        },
        "note": (
            "Futures settle backup only — not CME FedWatch meeting odds. "
            "Do not treat as primary hike probability."
        ),
    }


async def invoke(
    args: dict[str, Any],
    secret: dict[str, Any] | None = None,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = ctx
    payload = args if isinstance(args, dict) else {}
    secret = secret if isinstance(secret, dict) else {}
    allow_backup = _truthy(payload.get("allow_futures_backup"), default=True)

    if _http_mock():
        bundle = _mock_bundle()
        content = _format_content(bundle)
        return {
            "ok": True,
            "content": content,
            "summary": "Fed probabilities (mock)",
            **bundle,
        }

    base = str(
        secret.get("base_url") or payload.get("base_url") or DEFAULT_BASE
    ).strip().rstrip("/")
    path = str(secret.get("path") or payload.get("path") or DEFAULT_PATH).strip()
    if not path.startswith("/"):
        path = "/" + path
    url = f"{base}{path}"

    headers: dict[str, str] = {}
    token = str(secret.get("api_key") or secret.get("token") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    primary_error: str | None = None
    try:
        data = _http_get_json(url, headers=headers or None)
        bundle = _parse_primary_payload(data, source=url)
        bundle["refresh_required"] = False
        content = _format_content(bundle)
        return {
            "ok": True,
            "content": content,
            "summary": f"Fed probabilities as_of={bundle.get('as_of')}",
            **bundle,
        }
    except HTTPError as exc:
        primary_error = f"primary HTTP {exc.code} from {url}"
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        primary_error = f"primary failed: {exc}"

    if allow_backup:
        try:
            bundle = _yahoo_zq_backup()
            bundle["primary_error"] = primary_error
            content = _format_content(bundle)
            return {
                "ok": True,
                "content": content,
                "summary": "Fed probabilities secondary (ZQ=F under-anchored)",
                **bundle,
            }
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
            return _fail(
                "PROVIDER",
                f"{primary_error}; futures backup also failed: {exc}. "
                "Configure Vault fedwatch/probabilities base_url to a reachable proxy.",
            )

    return _fail(
        "PROVIDER",
        f"{primary_error}. Set Vault base_url to a reachable FedWatch proxy, "
        "or set allow_futures_backup=true.",
    )
