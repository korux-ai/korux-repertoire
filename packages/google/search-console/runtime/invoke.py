"""Google Search Console searchAnalytics.query. Stdlib HTTPS + OAuth refresh."""

from __future__ import annotations

import json
import os
import re
import ssl
from datetime import date, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

TOKEN_URL = "https://oauth2.googleapis.com/token"
QUERY_URL = "https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
HTTP_TIMEOUT_S = 40
DEFAULT_START = "28daysAgo"
DEFAULT_END = "3daysAgo"
DEFAULT_DIMENSIONS = ["query"]
DEFAULT_LIMIT = 25
ALLOWED_DIMENSIONS = frozenset(
    {"query", "page", "country", "device", "searchAppearance", "date"}
)
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
        raise RuntimeError(f"gsc HTTP error: {exc.reason}") from exc


def _resolve_date(raw: str, *, fallback: str) -> str:
    value = str(raw or fallback).strip() or fallback
    if _ISO_DATE.fullmatch(value):
        return value
    lower = value.lower()
    if lower == "today":
        return date.today().isoformat()
    if lower == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    m = re.fullmatch(r"(\d+)daysago", lower)
    if m:
        return (date.today() - timedelta(days=int(m.group(1)))).isoformat()
    return value


def _as_dimensions(value: Any) -> list[str]:
    if value is None:
        dims = list(DEFAULT_DIMENSIONS)
    elif isinstance(value, str):
        dims = [p.strip() for p in value.split(",") if p.strip()] or list(DEFAULT_DIMENSIONS)
    elif isinstance(value, list):
        dims = [str(x).strip() for x in value if str(x).strip()] or list(DEFAULT_DIMENSIONS)
    else:
        dims = list(DEFAULT_DIMENSIONS)
    out: list[str] = []
    for d in dims[:4]:
        if d not in ALLOWED_DIMENSIONS:
            continue
        out.append(d)
    return out or list(DEFAULT_DIMENSIONS)


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
            "google/search-console Vault needs access_token or client_id+client_secret+refresh_token",
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


def _format_rows(data: dict[str, Any], dimensions: list[str]) -> tuple[str, int]:
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    header = dimensions + ["clicks", "impressions", "ctr", "position"]
    lines = [" | ".join(header), " | ".join("---" for _ in header)]
    for row in rows:
        if not isinstance(row, dict):
            continue
        keys = row.get("keys") if isinstance(row.get("keys"), list) else []
        key_vals = [str(k) for k in keys[: len(dimensions)]]
        while len(key_vals) < len(dimensions):
            key_vals.append("")
        clicks = row.get("clicks", "")
        impressions = row.get("impressions", "")
        ctr = row.get("ctr", "")
        position = row.get("position", "")
        if isinstance(ctr, float):
            ctr = f"{ctr:.4f}"
        if isinstance(position, float):
            position = f"{position:.2f}"
        lines.append(
            " | ".join(key_vals + [str(clicks), str(impressions), str(ctr), str(position)])
        )
    if not rows:
        lines.append("(no rows)")
    return "\n".join(lines), len(rows)


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    args = args or {}
    secret = secret or {}

    site_url = str(args.get("site_url") or secret.get("site_url") or "").strip()
    if not site_url:
        return _fail("CREDENTIAL", "site_url is required in Vault or args")

    start_date = _resolve_date(str(args.get("start_date") or ""), fallback=DEFAULT_START)
    end_date = _resolve_date(str(args.get("end_date") or ""), fallback=DEFAULT_END)
    if not _ISO_DATE.fullmatch(start_date) or not _ISO_DATE.fullmatch(end_date):
        return _fail("VALIDATION", "start_date/end_date must be YYYY-MM-DD or NdaysAgo/yesterday/today")
    if start_date > end_date:
        return _fail("VALIDATION", "start_date must be <= end_date")

    dimensions = _as_dimensions(args.get("dimensions"))
    try:
        row_limit = int(args.get("row_limit") or args.get("limit") or DEFAULT_LIMIT)
    except (TypeError, ValueError):
        return _fail("VALIDATION", "row_limit must be an integer")
    if row_limit < 1 or row_limit > 1000:
        return _fail("VALIDATION", "row_limit must be between 1 and 1000")

    search_type = str(args.get("search_type") or "web").strip().lower() or "web"
    if search_type not in {"web", "image", "video", "news"}:
        return _fail("VALIDATION", "search_type must be web, image, video, or news")

    if _http_mock():
        content = (
            f"GSC mock for {site_url} ({start_date} → {end_date})\n"
            f"dimensions={','.join(dimensions)} search_type={search_type}"
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

    payload: dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit,
        "startRow": 0,
        "searchType": search_type,
    }
    url = QUERY_URL.format(site=quote(site_url, safe=""))
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
        return _fail("CREDENTIAL", f"gsc auth failed ({status}): {snippet}")
    if status >= 400:
        snippet = resp.decode("utf-8", errors="replace")[:400]
        return _fail("PROVIDER", f"gsc API {status}: {snippet}")
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "gsc query returned non-JSON")
    if not isinstance(data, dict):
        return _fail("PROVIDER", "gsc query returned unexpected payload")

    content, row_count = _format_rows(data, dimensions)
    summary = f"GSC {site_url}: {row_count} rows ({start_date} → {end_date})"
    return {
        "ok": True,
        "stub": False,
        "content": content,
        "summary": summary,
        "row_count": row_count,
        "site_url": site_url,
        "scope_hint": SCOPE,
    }
