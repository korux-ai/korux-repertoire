"""Google Ads API REST — campaign status or capped budget. No REMOVED. Stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_VERSION = "v18"
API_BASE = f"https://googleads.googleapis.com/{API_VERSION}"
HTTP_TIMEOUT_S = 40
ALLOWED_ACTIONS = frozenset({"set_status", "set_budget"})
ALLOWED_STATUS = frozenset({"ENABLED", "PAUSED"})
DEFAULT_MAX_MICROS = 500_000_000


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {"1", "true", "TRUE", "yes"}


def _digits(raw: str) -> str:
    return "".join(ch for ch in str(raw or "") if ch.isdigit())


def _request(method: str, url: str, *, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    req = Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            return int(resp.status), resp.read()
    except HTTPError as exc:
        return int(exc.code), exc.read() if exc.fp else b""
    except URLError as exc:
        raise RuntimeError(f"google ads HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"google ads auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"google ads server error ({status})")
    return _fail("PROVIDER", f"google ads API {status}: {snippet}")


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


def _headers(secret: dict[str, Any]) -> dict[str, str] | dict[str, Any]:
    token = str(secret.get("access_token") or secret.get("token") or "").strip()
    developer = str(secret.get("developer_token") or "").strip()
    if not token:
        return _fail("CREDENTIAL", "google/ads-mutate Vault requires access_token")
    if not developer:
        return _fail("CREDENTIAL", "google/ads-mutate Vault requires developer_token")
    headers = {
        "Authorization": f"Bearer {token}",
        "developer-token": developer,
        "Content-Type": "application/json",
    }
    login = _digits(str(secret.get("login_customer_id") or ""))
    if login:
        headers["login-customer-id"] = login
    return headers


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    args = args or {}
    secret = secret or {}
    action = str(args.get("action") or "").strip().lower()
    campaign_id = _digits(str(args.get("campaign_id") or ""))
    status = str(args.get("status") or "").strip().upper()
    customer_id = _digits(str(args.get("customer_id") or secret.get("customer_id") or ""))

    if action not in ALLOWED_ACTIONS:
        return _fail("VALIDATION", f"action must be one of {sorted(ALLOWED_ACTIONS)}")
    if not campaign_id:
        return _fail("VALIDATION", "campaign_id is required")
    if not customer_id:
        return _fail("CREDENTIAL", "customer_id is required in Vault or args")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "campaign_id": campaign_id,
            "action": action,
            "status": status or None,
            "amount_micros": int(args["amount_micros"]) if args.get("amount_micros") is not None else None,
            "content": f"campaign:{campaign_id}:{action}",
            "summary": f"google ads {action} campaign {campaign_id}",
        }

    headers = _headers(secret)
    if headers.get("ok") is False:
        return headers  # type: ignore[return-value]

    try:
        if action == "set_status":
            if status not in ALLOWED_STATUS:
                return _fail("VALIDATION", "status must be ENABLED or PAUSED")
            if status == "ENABLED" and not _owner_flag(context, "allow_enable", False):
                return _fail(
                    "GOVERNOR_POLICY",
                    "status=ENABLED blocked unless Owner allow_enable=true",
                )
            url = f"{API_BASE}/customers/{customer_id}/campaigns:mutate"
            payload = {
                "operations": [
                    {
                        "update": {
                            "resourceName": f"customers/{customer_id}/campaigns/{campaign_id}",
                            "status": status,
                        },
                        "updateMask": "status",
                    }
                ]
            }
            code, resp = _request(
                "POST",
                url,
                headers=headers,  # type: ignore[arg-type]
                body=json.dumps(payload).encode("utf-8"),
            )
            if code >= 400:
                return _provider_fail(code, resp)
            return {
                "ok": True,
                "stub": False,
                "campaign_id": campaign_id,
                "action": action,
                "status": status,
                "content": f"campaign:{campaign_id}:{status}",
                "summary": f"google ads set_status {campaign_id}={status}",
            }

        if not _owner_flag(context, "allow_budget_change", False):
            return _fail(
                "GOVERNOR_POLICY",
                "set_budget blocked unless Owner allow_budget_change=true",
            )
        budget_id = _digits(str(args.get("budget_id") or ""))
        if not budget_id:
            return _fail("VALIDATION", "budget_id is required for set_budget")
        try:
            amount = int(args.get("amount_micros"))
        except (TypeError, ValueError):
            return _fail("VALIDATION", "amount_micros must be an integer")
        max_amount = _owner_int(context, "max_amount_micros", DEFAULT_MAX_MICROS)
        if amount < 10000:
            return _fail("VALIDATION", "amount_micros must be >= 10000")
        if amount > max_amount:
            return _fail("VALIDATION", f"amount_micros exceeds Owner max_amount_micros ({max_amount})")

        url = f"{API_BASE}/customers/{customer_id}/campaignBudgets:mutate"
        payload = {
            "operations": [
                {
                    "update": {
                        "resourceName": f"customers/{customer_id}/campaignBudgets/{budget_id}",
                        "amountMicros": str(amount),
                    },
                    "updateMask": "amountMicros",
                }
            ]
        }
        code, resp = _request(
            "POST",
            url,
            headers=headers,  # type: ignore[arg-type]
            body=json.dumps(payload).encode("utf-8"),
        )
        if code >= 400:
            return _provider_fail(code, resp)
        return {
            "ok": True,
            "stub": False,
            "campaign_id": campaign_id,
            "action": action,
            "amount_micros": amount,
            "content": f"budget:{budget_id}:{amount}",
            "summary": f"google ads set_budget {budget_id}={amount}",
        }
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
