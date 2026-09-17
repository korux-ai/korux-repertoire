"""Supabase PostgREST rows — stdlib HTTPS; no Korux imports.

Failure shape (korux_failure_class_v1):
  {"ok": false, "error": {"class": "<closed>", "code": "...", "message": "..."}}
"""

from __future__ import annotations

import json
import os
import re
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

HTTP_TIMEOUT_S = 40
MAX_LIMIT = 200
DEFAULT_LIMIT = 50
_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_COL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_WRITE = frozenset({"insert", "update", "upsert"})
_ACTIONS = frozenset({"select", "insert", "update", "upsert"})

FAILURE_CLASSES = frozenset(
    {"auth", "empty", "unavailable", "validation", "denied", "provider"}
)
_CODE_TO_CLASS: dict[str, str] = {
    "CREDENTIAL": "auth",
    "AUTH": "auth",
    "UNAUTHORIZED": "auth",
    "VALIDATION": "validation",
    "ACCESS_DENIED": "denied",
    "DENIED": "denied",
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
    if cls not in FAILURE_CLASSES:
        cls = _CODE_TO_CLASS.get(str(code or "").strip().upper(), "provider")
    err: dict[str, Any] = {"class": cls, "code": code, "message": message}
    if retryable:
        err["retryable"] = True
    return {"ok": False, "error": err}


def _http_mock() -> bool:
    raw = os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip().lower()
    return raw in {"1", "true", "yes"}


def _parse_secret(secret: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(secret, dict):
        return _fail("CREDENTIAL", "Vault secret must be a JSON object")
    project_url = str(
        secret.get("project_url") or secret.get("base_url") or secret.get("url") or ""
    ).strip().rstrip("/")
    api_key = str(
        secret.get("api_key")
        or secret.get("service_role_key")
        or secret.get("secret_key")
        or secret.get("token")
        or ""
    ).strip()
    schema = str(secret.get("schema") or "public").strip() or "public"
    if not project_url:
        return _fail("CREDENTIAL", "Vault supabase/rows JSON missing project_url")
    if not api_key:
        return _fail("CREDENTIAL", "Vault supabase/rows JSON missing api_key")
    if not _TABLE_RE.match(schema):
        return _fail("CREDENTIAL", "Vault schema must be a simple identifier")
    return {"project_url": project_url, "api_key": api_key, "schema": schema}


def _normalize_filters(raw: Any) -> dict[str, str] | dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        return _fail("VALIDATION", "filters must be an object of column → value")
    out: dict[str, str] = {}
    for key, val in raw.items():
        col = str(key or "").strip()
        if not col or not _COL_RE.match(col):
            return _fail(
                "VALIDATION",
                f"invalid filter column name: {col!r}",
            )
        if val is None:
            continue
        if isinstance(val, (dict, list)):
            return _fail(
                "VALIDATION",
                "filter values must be scalars (string/number/bool)",
            )
        out[col] = str(val)
    return out


def _query_eq(filters: dict[str, str]) -> str:
    parts = []
    for col, val in filters.items():
        parts.append(f"{quote(col, safe='')}={quote('eq.' + val, safe='')}")
    return "&".join(parts)


def _request(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None = None,
) -> tuple[int, Any, str]:
    req = Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            raw = resp.read()
            status = int(resp.status)
    except HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        status = int(exc.code)
    except URLError as exc:
        return 0, None, f"Supabase request failed: {exc.reason}"
    text = raw.decode("utf-8", errors="replace") if raw else ""
    if not text.strip():
        return status, None, ""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return status, text, ""
    return status, data, ""


def _map_http_error(status: int, payload: Any) -> dict[str, Any]:
    detail = ""
    if isinstance(payload, dict):
        detail = str(payload.get("message") or payload.get("error") or payload.get("hint") or "")
    elif isinstance(payload, str):
        detail = payload[:300]
    suffix = f": {detail}" if detail else ""
    if status in {401, 403}:
        cls = "auth" if status == 401 else "denied"
        code = "UNAUTHORIZED" if status == 401 else "ACCESS_DENIED"
        return _fail(code, f"Supabase HTTP {status}{suffix}", failure_class=cls)
    if status == 404:
        return _fail("PROVIDER", f"Supabase HTTP 404{suffix}", failure_class="provider")
    if status == 409:
        return _fail("PROVIDER", f"Supabase conflict HTTP 409{suffix}", failure_class="provider")
    if status == 429:
        return _fail(
            "RATE_LIMITED",
            f"Supabase rate limited{suffix}",
            failure_class="unavailable",
            retryable=True,
        )
    if status >= 500:
        return _fail(
            "UNAVAILABLE",
            f"Supabase unavailable HTTP {status}{suffix}",
            failure_class="unavailable",
            retryable=True,
        )
    if status >= 400:
        return _fail(
            "VALIDATION" if status == 400 else "PROVIDER",
            f"Supabase HTTP {status}{suffix}",
            failure_class="validation" if status == 400 else "provider",
        )
    return _fail("PROVIDER", f"Unexpected Supabase HTTP {status}{suffix}")


def _format_content(action: str, table: str, rows: list[Any]) -> str:
    preview = json.dumps(rows[:5], ensure_ascii=False, default=str)
    if len(preview) > 4000:
        preview = preview[:4000] + "…"
    return f"action={action} table={table} row_count={len(rows)}\n{preview}"


def _mock_rows(action: str, table: str) -> list[dict[str, Any]]:
    if action == "select":
        return [{"id": 1, "table": table, "mock": True, "note": "mock select"}]
    return [{"id": 1, "table": table, "mock": True, "action": action}]


async def invoke(
    args: dict[str, Any],
    secret: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = context
    payload = args if isinstance(args, dict) else {}
    action = str(payload.get("action") or "").strip().lower()
    table = str(payload.get("table") or "").strip()

    if action not in _ACTIONS:
        return _fail(
            "VALIDATION",
            "action must be select, insert, update, or upsert",
            failure_class="validation",
        )
    if not table or not _TABLE_RE.match(table):
        return _fail(
            "VALIDATION",
            "table must be a non-empty simple identifier",
            failure_class="validation",
        )

    filters_or_err = _normalize_filters(payload.get("filters"))
    if isinstance(filters_or_err, dict) and filters_or_err.get("ok") is False:
        return filters_or_err
    filters: dict[str, str] = filters_or_err  # type: ignore[assignment]

    row = payload.get("row")
    if action in _WRITE:
        if not isinstance(row, dict) or not row:
            return _fail(
                "VALIDATION",
                f"{action} requires a non-empty row object",
                failure_class="validation",
            )
    if action == "update" and not filters:
        return _fail(
            "VALIDATION",
            "update requires filters to avoid full-table writes",
            failure_class="validation",
        )

    try:
        limit = int(payload.get("limit") if payload.get("limit") is not None else DEFAULT_LIMIT)
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))
    try:
        offset = int(payload.get("offset") or 0)
    except (TypeError, ValueError):
        offset = 0
    offset = max(0, min(offset, 10000))

    columns = str(payload.get("columns") or "*").strip() or "*"
    on_conflict = str(payload.get("on_conflict") or "").strip()
    if on_conflict and not _COL_RE.match(on_conflict):
        return _fail("VALIDATION", "on_conflict must be a simple column name")

    cfg = _parse_secret(secret)
    if cfg.get("ok") is False:
        return cfg

    if _http_mock():
        rows = _mock_rows(action, table)
        content = _format_content(action, table, rows)
        return {
            "ok": True,
            "stub": True,
            "empty": False,
            "action": action,
            "table": table,
            "rows": rows,
            "row_count": len(rows),
            "content": content,
            "summary": f"Mock {action} on {table} ({len(rows)} rows)",
            "provider": "supabase",
            "reader": "supabase/rows",
            "message": "Supabase rows mock completed",
        }

    base = f"{cfg['project_url']}/rest/v1/{quote(table, safe='')}"
    headers = {
        "apikey": cfg["api_key"],
        "Authorization": f"Bearer {cfg['api_key']}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Profile": cfg["schema"],
        "Content-Profile": cfg["schema"],
        "User-Agent": "KoruxCapability/1.0 (+https://github.com/korux-ai/korux-repertoire)",
    }

    if action == "select":
        qs = [f"select={quote(columns, safe=',.*()')}", f"limit={limit}", f"offset={offset}"]
        eq = _query_eq(filters)
        if eq:
            qs.append(eq)
        url = base + "?" + "&".join(qs)
        status, data, err = _request(method="GET", url=url, headers=headers)
        if err and data is None and status == 0:
            return _fail("UNAVAILABLE", err, failure_class="unavailable", retryable=True)
        if status >= 400:
            return _map_http_error(status, data)
        rows = data if isinstance(data, list) else ([] if data is None else [data])
        if not rows:
            return {
                "ok": True,
                "empty": True,
                "action": action,
                "table": table,
                "rows": [],
                "row_count": 0,
                "content": f"action=select table={table} row_count=0",
                "summary": f"No rows in {table}",
                "provider": "supabase",
                "reader": "supabase/rows",
                "message": "Supabase select returned no rows",
            }
        content = _format_content(action, table, rows)
        return {
            "ok": True,
            "empty": False,
            "action": action,
            "table": table,
            "rows": rows,
            "row_count": len(rows),
            "content": content,
            "summary": f"Selected {len(rows)} row(s) from {table}",
            "provider": "supabase",
            "reader": "supabase/rows",
            "message": "Supabase select completed",
        }

    # Writes
    body = json.dumps(row, ensure_ascii=False, default=str).encode("utf-8")
    headers = dict(headers)
    headers["Prefer"] = "return=representation"
    if action == "insert":
        status, data, err = _request(method="POST", url=base, headers=headers, body=body)
    elif action == "upsert":
        prefer = ["return=representation", "resolution=merge-duplicates"]
        headers["Prefer"] = ",".join(prefer)
        url = base
        if on_conflict:
            url = base + "?" + urlencode({"on_conflict": on_conflict})
        status, data, err = _request(method="POST", url=url, headers=headers, body=body)
    else:  # update
        eq = _query_eq(filters)
        url = base + ("?" + eq if eq else "")
        status, data, err = _request(method="PATCH", url=url, headers=headers, body=body)

    if err and data is None and status == 0:
        return _fail("UNAVAILABLE", err, failure_class="unavailable", retryable=True)
    if status >= 400:
        return _map_http_error(status, data)

    rows = data if isinstance(data, list) else ([] if data is None else [data])
    content = _format_content(action, table, rows)
    return {
        "ok": True,
        "empty": len(rows) == 0,
        "action": action,
        "table": table,
        "rows": rows,
        "row_count": len(rows),
        "content": content,
        "summary": f"{action} on {table} → {len(rows)} row(s)",
        "provider": "supabase",
        "reader": "supabase/rows",
        "message": f"Supabase {action} completed",
    }
