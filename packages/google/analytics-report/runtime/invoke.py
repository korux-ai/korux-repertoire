"""GA4 Data API runReport. Stdlib HTTPS + OAuth refresh (or access_token)."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TOKEN_URL = "https://oauth2.googleapis.com/token"
REPORT_URL = "https://analyticsdata.googleapis.com/v1beta/{property}:runReport"
SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
HTTP_TIMEOUT_S = 40
DEFAULT_METRICS = ["sessions", "activeUsers", "screenPageViews"]
DEFAULT_DIMENSIONS = ["date"]
DEFAULT_START = "7daysAgo"
DEFAULT_END = "yesterday"
DEFAULT_LIMIT = 25


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {"1", "true", "TRUE", "yes"}


def _request(method: str, url: str, *, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    req = Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            return int(resp.status), resp.read()
    except HTTPError as exc:
        return int(exc.code), exc.read() if exc.fp else b""
    except URLError as exc:
        raise RuntimeError(f"ga4 HTTP error: {exc.reason}") from exc


def _property_resource(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    if value.startswith("properties/"):
        return value
    return f"properties/{value}"


def _as_str_list(value: Any, *, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        return parts or list(default)
    if isinstance(value, list):
        out = [str(x).strip() for x in value if str(x).strip()]
        return out or list(default)
    return list(default)


def _access_token(secret: dict[str, Any]) -> dict[str, Any]:
    direct = str(secret.get("access_token") or secret.get("token") or "").strip()
    if direct:
        return {"ok": True, "token": direct}

    client_id = str(secret.get("client_id") or "").strip()
    client_secret = str(secret.get("client_secret") or "").strip()
    refresh_token = str(secret.get("refresh_token") or "").strip()
    if not (client_id and client_secret and refresh_token):
        return _fail(
            "CREDENTIAL",
            "google/analytics-report Vault needs access_token or client_id+client_secret+refresh_token",
        )
    body = urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    status, resp = _request(
        "POST",
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
    )
    if status >= 400:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        return _fail("CREDENTIAL", f"google OAuth refresh failed ({status}): {snippet}")
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "google OAuth returned non-JSON")
    token = str(data.get("access_token") or "").strip()
    if not token:
        return _fail("PROVIDER", "google OAuth missing access_token")
    return {"ok": True, "token": token}


def _format_report(data: dict[str, Any], *, metrics: list[str], dimensions: list[str]) -> tuple[str, int]:
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    lines: list[str] = []
    header = dimensions + metrics
    if header:
        lines.append(" | ".join(header))
        lines.append(" | ".join("---" for _ in header))
    for row in rows:
        if not isinstance(row, dict):
            continue
        dim_vals = [
            str(v.get("value") or "")
            for v in (row.get("dimensionValues") or [])
            if isinstance(v, dict)
        ]
        met_vals = [
            str(v.get("value") or "")
            for v in (row.get("metricValues") or [])
            if isinstance(v, dict)
        ]
        # Pad/truncate to requested widths.
        while len(dim_vals) < len(dimensions):
            dim_vals.append("")
        while len(met_vals) < len(metrics):
            met_vals.append("")
        lines.append(" | ".join(dim_vals[: len(dimensions)] + met_vals[: len(metrics)]))
    if not rows:
        lines.append("(no rows)")
    text = "\n".join(lines)
    return text, len(rows)


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    args = args or {}
    secret = secret or {}

    property_id = _property_resource(
        str(args.get("property_id") or secret.get("property_id") or "")
    )
    if not property_id:
        return _fail("CREDENTIAL", "property_id is required in Vault or args")

    start_date = str(args.get("start_date") or DEFAULT_START).strip() or DEFAULT_START
    end_date = str(args.get("end_date") or DEFAULT_END).strip() or DEFAULT_END
    metrics = _as_str_list(args.get("metrics"), default=DEFAULT_METRICS)[:10]
    dimensions = _as_str_list(args.get("dimensions"), default=DEFAULT_DIMENSIONS)[:9]
    try:
        limit = int(args.get("limit") or DEFAULT_LIMIT)
    except (TypeError, ValueError):
        return _fail("VALIDATION", "limit must be an integer")
    if limit < 1 or limit > 100:
        return _fail("VALIDATION", "limit must be between 1 and 100")

    if _http_mock():
        content = (
            f"GA4 mock report for {property_id} ({start_date} → {end_date})\n"
            f"metrics={','.join(metrics)} dimensions={','.join(dimensions)}"
        )
        return {
            "ok": True,
            "stub": True,
            "content": content,
            "summary": content,
            "row_count": 0,
        }

    try:
        tok = _access_token(secret)
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if tok.get("ok") is False:
        return tok

    payload = {
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "dimensions": [{"name": name} for name in dimensions],
        "metrics": [{"name": name} for name in metrics],
        "limit": str(limit),
    }
    url = REPORT_URL.format(property=property_id)
    try:
        status, resp = _request(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {tok['token']}",
                "Content-Type": "application/json",
            },
            body=json.dumps(payload).encode("utf-8"),
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))

    if status in {401, 403}:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        return _fail("CREDENTIAL", f"ga4 auth failed ({status}): {snippet}")
    if status >= 400:
        snippet = resp.decode("utf-8", errors="replace")[:400]
        return _fail("PROVIDER", f"ga4 API {status}: {snippet}")
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "ga4 runReport returned non-JSON")
    if not isinstance(data, dict):
        return _fail("PROVIDER", "ga4 runReport returned unexpected payload")

    content, row_count = _format_report(data, metrics=metrics, dimensions=dimensions)
    summary = f"GA4 {property_id}: {row_count} rows ({start_date} → {end_date})"
    return {
        "ok": True,
        "stub": False,
        "content": content,
        "summary": summary,
        "row_count": row_count,
        "property": property_id,
        "scope_hint": SCOPE,
    }
