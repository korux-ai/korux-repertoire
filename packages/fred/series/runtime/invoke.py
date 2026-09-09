"""FRED series observations — stdlib HTTPS; no Korux imports."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"
HTTP_TIMEOUT_S = 30
DEFAULT_LIMIT = 10
MAX_LIMIT = 100


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


def _parse_secret(secret: dict[str, Any] | None) -> dict[str, Any] | dict[str, Any]:
    if not isinstance(secret, dict):
        return _fail("CREDENTIAL", "Vault secret must be a JSON object with api_key")
    api_key = str(
        secret.get("api_key") or secret.get("fred_api_key") or secret.get("token") or ""
    ).strip()
    if not api_key:
        return _fail("CREDENTIAL", "Vault fred/series JSON missing api_key")
    return {"api_key": api_key}


def _format_content(series_id: str, observations: list[dict[str, Any]]) -> str:
    lines = [f"FRED series {series_id} (latest observations):"]
    for row in observations:
        date = row.get("date") or "?"
        value = row.get("value") or "?"
        lines.append(f"- {date}: {value}")
    return "\n".join(lines)


def _mock_obs(series_id: str, limit: int) -> list[dict[str, Any]]:
    return [
        {"date": f"2026-09-{7 - i:02d}", "value": str(4.0 + i * 0.01)}
        for i in range(min(limit, 5))
    ]


def _fetch_obs(series_id: str, api_key: str, limit: int) -> list[dict[str, Any]]:
    params = urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": str(limit),
        }
    )
    url = f"{FRED_OBS_URL}?{params}"
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
    rows = data.get("observations") or []
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        val = str(row.get("value") or "").strip()
        if val in {"", "."}:
            continue
        out.append({"date": row.get("date"), "value": val})
    return out


async def invoke(
    args: dict[str, Any],
    secret: dict[str, Any] | None = None,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = ctx
    series_id = str((args or {}).get("series_id") or "").strip()
    if not series_id:
        return _fail("VALIDATION", "series_id is required")
    try:
        limit = int((args or {}).get("limit") or DEFAULT_LIMIT)
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))

    if _http_mock():
        # Still require a secret shape in non-mock production; mock allows empty for unit tests.
        observations = _mock_obs(series_id, limit)
    else:
        parsed = _parse_secret(secret)
        if "error" in parsed:
            return parsed
        try:
            observations = _fetch_obs(series_id, parsed["api_key"], limit)
        except HTTPError as exc:
            return _fail("PROVIDER", f"FRED HTTP {exc.code}")
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return _fail("PROVIDER", f"FRED request failed: {exc}")

    if not observations:
        return {
            "ok": True,
            "empty": True,
            "content": "",
            "summary": f"FRED returned no observations for {series_id}",
            "series_id": series_id,
            "observations": [],
        }
    content = _format_content(series_id, observations)
    return {
        "ok": True,
        "content": content,
        "summary": f"FRED {series_id}: {observations[0].get('date')}={observations[0].get('value')}",
        "series_id": series_id,
        "observations": observations,
    }
