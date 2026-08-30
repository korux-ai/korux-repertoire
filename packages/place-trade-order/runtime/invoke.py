"""Alpaca paper market order. Stdlib HTTPS only."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_PAPER_BASE = "https://paper-api.alpaca.markets"
HTTP_TIMEOUT_S = 30


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {
        "1",
        "true",
        "TRUE",
        "yes",
    }


def _ensure_paper_base_url(base_url: str) -> str | dict[str, Any]:
    normalized = base_url.rstrip("/").lower()
    if "paper-api" in normalized or normalized.startswith("http://localhost"):
        return base_url.rstrip("/")
    if normalized.startswith("http://test") or normalized.startswith("https://test"):
        return base_url.rstrip("/")
    return _fail("VALIDATION", "Only Alpaca paper trading endpoints are supported")


def _request(method: str, url: str, *, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    req = Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            return int(resp.status), resp.read()
    except HTTPError as exc:
        return int(exc.code), exc.read() if exc.fp else b""
    except URLError as exc:
        raise RuntimeError(f"alpaca HTTP error: {exc.reason}") from exc


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    symbol = str((args or {}).get("symbol") or "").strip().upper()
    side = str((args or {}).get("side") or "").strip().lower()
    quantity = (args or {}).get("quantity")
    if not symbol:
        return _fail("VALIDATION", "symbol is required")
    if side not in {"buy", "sell"}:
        return _fail("VALIDATION", "side must be buy or sell")
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        return _fail("VALIDATION", "quantity must be positive")
    if qty <= 0:
        return _fail("VALIDATION", "quantity must be positive")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "symbol": symbol,
            "side": side,
            "quantity": qty,
            "order_id": f"paper-mock-{symbol}-{side}-{qty}",
            "order_status": "accepted",
            "summary": f"{side} {qty} {symbol} (mock)",
        }

    api_key = str((secret or {}).get("api_key") or (secret or {}).get("key_id") or "").strip()
    api_secret = str((secret or {}).get("api_secret") or (secret or {}).get("secret") or "").strip()
    if not api_key or not api_secret:
        return _fail("CREDENTIAL", "broker Vault JSON requires api_key and api_secret")
    raw_base = str((secret or {}).get("base_url") or DEFAULT_PAPER_BASE).strip() or DEFAULT_PAPER_BASE
    base = _ensure_paper_base_url(raw_base)
    if isinstance(base, dict):
        return base

    payload = {
        "symbol": symbol,
        "qty": str(qty),
        "side": side,
        "type": "market",
        "time_in_force": "day",
    }
    url = f"{base}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Content-Type": "application/json",
    }
    try:
        status, resp = _request("POST", url, headers=headers, body=json.dumps(payload).encode("utf-8"))
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if status >= 400:
        snippet = resp.decode("utf-8", errors="replace")[:300]
        if status in {401, 403}:
            return _fail("CREDENTIAL", f"alpaca auth failed ({status})")
        return _fail("PROVIDER", f"alpaca API {status}: {snippet}")
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "alpaca returned non-JSON")
    order_id = str((data or {}).get("id") or "").strip()
    if not order_id:
        return _fail("PROVIDER", "alpaca response missing order id")
    status_txt = str(data.get("status") or "unknown")
    return {
        "ok": True,
        "stub": False,
        "symbol": symbol,
        "side": side,
        "quantity": qty,
        "order_id": order_id,
        "order_status": status_txt,
        "summary": f"{side} {qty} {symbol} order {order_id}",
    }
