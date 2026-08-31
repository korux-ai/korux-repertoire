"""Meta Marketing API — pause/activate or capped daily_budget. No deletes. Stdlib HTTPS."""

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
ALLOWED_ACTIONS = frozenset({"set_status", "set_budget"})
ALLOWED_TYPES = frozenset({"campaign", "adset", "ad"})
ALLOWED_STATUS = frozenset({"ACTIVE", "PAUSED"})
DEFAULT_MAX_DAILY = 50000


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


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"meta ads auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"meta ads server error ({status})")
    return _fail("PROVIDER", f"meta ads API {status}: {snippet}")


def _owner_flag(context: dict | None, key: str, default: bool = False) -> bool:
    gov = (context or {}).get("governor") if isinstance(context, dict) else None
    if not isinstance(gov, dict) or key not in gov:
        return default
    val = gov.get(key)
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in {"1", "true", "yes", "on"}


def _owner_int(context: dict | None, key: str, default: int) -> int:
    gov = (context or {}).get("governor") if isinstance(context, dict) else None
    if not isinstance(gov, dict) or gov.get(key) is None:
        return default
    try:
        return int(gov[key])
    except (TypeError, ValueError):
        return default


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    args = args or {}
    action = str(args.get("action") or "").strip().lower()
    object_type = str(args.get("object_type") or "").strip().lower()
    object_id = str(args.get("object_id") or "").strip()
    status = str(args.get("status") or "").strip().upper()

    if action not in ALLOWED_ACTIONS:
        return _fail("VALIDATION", f"action must be one of {sorted(ALLOWED_ACTIONS)}")
    if object_type not in ALLOWED_TYPES:
        return _fail("VALIDATION", f"object_type must be one of {sorted(ALLOWED_TYPES)}")
    if not object_id or not object_id.isdigit():
        return _fail("VALIDATION", "object_id must be a numeric Meta id")

    fields: dict[str, str] = {}
    if action == "set_status":
        if status not in ALLOWED_STATUS:
            return _fail("VALIDATION", "status must be ACTIVE or PAUSED")
        if status == "ACTIVE" and not _owner_flag(context, "allow_activate", False):
            return _fail(
                "GOVERNOR_POLICY",
                "status=ACTIVE blocked unless Owner editable_governor_config.allow_activate=true",
            )
        fields["status"] = status
    else:
        if not _owner_flag(context, "allow_budget_change", False):
            return _fail(
                "GOVERNOR_POLICY",
                "set_budget blocked unless Owner allow_budget_change=true",
            )
        if object_type == "ad":
            return _fail("VALIDATION", "set_budget is not supported on ad objects")
        try:
            daily = int(args.get("daily_budget"))
        except (TypeError, ValueError):
            return _fail("VALIDATION", "daily_budget must be an integer (minor units)")
        max_daily = _owner_int(context, "max_daily_budget", DEFAULT_MAX_DAILY)
        if daily < 100:
            return _fail("VALIDATION", "daily_budget must be >= 100")
        if daily > max_daily:
            return _fail("VALIDATION", f"daily_budget exceeds Owner max_daily_budget ({max_daily})")
        fields["daily_budget"] = str(daily)

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "object_id": object_id,
            "action": action,
            "status": fields.get("status"),
            "daily_budget": int(fields["daily_budget"]) if "daily_budget" in fields else None,
            "content": f"{object_type}:{object_id}:{action}",
            "summary": f"meta ads {action} {object_type} {object_id}",
        }

    token = str((secret or {}).get("access_token") or (secret or {}).get("token") or "").strip()
    if not token:
        return _fail("CREDENTIAL", "meta/ads-mutate Vault requires access_token")

    fields["access_token"] = token
    body = urlencode(fields).encode("utf-8")
    url = f"{GRAPH_BASE}/{object_id}"
    try:
        code, resp = _request(
            "POST",
            url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=body,
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if code >= 400:
        return _provider_fail(code, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "meta ads mutate returned non-JSON")
    if data.get("success") is False:
        return _fail("PROVIDER", f"meta ads mutate rejected: {data}")
    return {
        "ok": True,
        "stub": False,
        "object_id": object_id,
        "action": action,
        "status": fields.get("status"),
        "daily_budget": int(fields["daily_budget"]) if "daily_budget" in fields else None,
        "content": f"{object_type}:{object_id}:{action}",
        "summary": f"meta ads {action} {object_type} {object_id}",
    }
