"""Meta Marketing API ad account insights (read-only). Stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
HTTP_TIMEOUT_S = 40
DEFAULT_FIELDS = [
    "campaign_name",
    "impressions",
    "clicks",
    "spend",
    "cpc",
    "ctr",
    "reach",
    "actions",
    "cost_per_action_type",
]
DEFAULT_PRESET = "last_7d"
DEFAULT_LEVEL = "campaign"
DEFAULT_LIMIT = 25
ALLOWED_LEVELS = frozenset({"account", "campaign", "adset", "ad"})


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
        raise RuntimeError(f"meta ads HTTP error: {exc.reason}") from exc


def _act_id(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    if value.startswith("act_"):
        return value
    return f"act_{value}"


def _as_fields(value: Any) -> list[str]:
    if value is None:
        return list(DEFAULT_FIELDS)
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        return parts or list(DEFAULT_FIELDS)
    if isinstance(value, list):
        out = [str(x).strip() for x in value if str(x).strip()]
        return out[:20] or list(DEFAULT_FIELDS)
    return list(DEFAULT_FIELDS)


def _format_insights(data: dict[str, Any], fields: list[str]) -> tuple[str, int]:
    rows = data.get("data") if isinstance(data.get("data"), list) else []
    # Prefer a stable display set.
    display = [f for f in fields if f not in {"actions", "cost_per_action_type"}]
    display.extend(["purchase_cpa", "lead_cpa", "link_click"])
    lines = [" | ".join(display), " | ".join("---" for _ in display)]
    for row in rows:
        if not isinstance(row, dict):
            continue
        purchase_cpa = ""
        lead_cpa = ""
        link_click = ""
        for item in row.get("cost_per_action_type") or []:
            if not isinstance(item, dict):
                continue
            at = str(item.get("action_type") or "")
            if at in {"purchase", "omni_purchase"}:
                purchase_cpa = str(item.get("value") or "")
            if at in {"lead", "onsite_conversion.lead_grouped"}:
                lead_cpa = str(item.get("value") or "")
        for item in row.get("actions") or []:
            if not isinstance(item, dict):
                continue
            if str(item.get("action_type") or "") == "link_click":
                link_click = str(item.get("value") or "")
        vals: list[str] = []
        for f in display:
            if f == "purchase_cpa":
                vals.append(purchase_cpa)
            elif f == "lead_cpa":
                vals.append(lead_cpa)
            elif f == "link_click":
                vals.append(link_click)
            else:
                vals.append(str(row.get(f) or ""))
        lines.append(" | ".join(vals))
    if not rows:
        lines.append("(no rows)")
    return "\n".join(lines), len(rows)


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    args = args or {}
    secret = secret or {}

    token = str(secret.get("access_token") or secret.get("token") or "").strip()
    account = _act_id(str(args.get("ad_account_id") or secret.get("ad_account_id") or ""))
    if not token:
        return _fail("CREDENTIAL", "meta/ads-insights Vault requires access_token")
    if not account:
        return _fail("CREDENTIAL", "ad_account_id is required in Vault or args")

    date_preset = str(args.get("date_preset") or DEFAULT_PRESET).strip() or DEFAULT_PRESET
    level = str(args.get("level") or DEFAULT_LEVEL).strip().lower() or DEFAULT_LEVEL
    if level not in ALLOWED_LEVELS:
        return _fail("VALIDATION", f"level must be one of {sorted(ALLOWED_LEVELS)}")
    fields = _as_fields(args.get("fields"))
    try:
        limit = int(args.get("limit") or DEFAULT_LIMIT)
    except (TypeError, ValueError):
        return _fail("VALIDATION", "limit must be an integer")
    if limit < 1 or limit > 100:
        return _fail("VALIDATION", "limit must be between 1 and 100")

    if _http_mock():
        content = f"Meta ads mock insights for {account} preset={date_preset} level={level}"
        return {
            "ok": True,
            "stub": True,
            "content": content,
            "summary": content,
            "row_count": 0,
        }

    # Account-level insights without level=account uses aggregated account row;
    # for campaign/adset/ad pass level=…
    params: dict[str, str] = {
        "access_token": token,
        "fields": ",".join(fields),
        "date_preset": date_preset,
        "limit": str(limit),
    }
    if level != "account":
        params["level"] = level

    url = f"{GRAPH_BASE}/{account}/insights?{urlencode(params)}"
    try:
        status, resp = _request("GET", url, headers={}, body=None)
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))

    if status in {401, 403}:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        return _fail("CREDENTIAL", f"meta ads auth failed ({status}): {snippet}")
    if status >= 400:
        snippet = resp.decode("utf-8", errors="replace")[:400]
        return _fail("PROVIDER", f"meta ads API {status}: {snippet}")
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "meta ads insights returned non-JSON")
    if not isinstance(data, dict):
        return _fail("PROVIDER", "meta ads insights unexpected payload")

    content, row_count = _format_insights(data, fields)
    summary = f"Meta ads {account}: {row_count} rows ({date_preset}, level={level})"
    return {
        "ok": True,
        "stub": False,
        "content": content,
        "summary": summary,
        "row_count": row_count,
        "ad_account_id": account,
    }
