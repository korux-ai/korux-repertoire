"""Webflow CMS create item (staged or live). Data API v2, stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://api.webflow.com/v2"
HTTP_TIMEOUT_S = 40
MAX_FIELD_CHARS = 200000


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
        raise RuntimeError(f"webflow HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"webflow auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"webflow server error ({status})")
    return _fail("PROVIDER", f"webflow API {status}: {snippet}")


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off", ""}:
        return False
    return default


def _parse_field_data(raw: Any) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("field_data must be a JSON object") from exc
        if not isinstance(parsed, dict):
            raise ValueError("field_data must be a JSON object")
        return parsed
    raise ValueError("field_data must be an object")


def _field_chars(field_data: dict[str, Any]) -> int:
    total = 0
    for value in field_data.values():
        if isinstance(value, str):
            total += len(value)
        else:
            total += len(json.dumps(value, ensure_ascii=False))
    return total


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    args = args or {}
    name = str(args.get("name") or "").strip()
    slug = str(args.get("slug") or "").strip()
    publish = _as_bool(args.get("publish"), False)

    if not name:
        return _fail("VALIDATION", "name is required")
    if not slug:
        return _fail("VALIDATION", "slug is required")

    try:
        extras = _parse_field_data(args.get("field_data") or args.get("fields"))
    except ValueError as exc:
        return _fail("VALIDATION", str(exc))

    field_data: dict[str, Any] = {"name": name, "slug": slug, **extras}
    # Ensure required keys win over extras
    field_data["name"] = name
    field_data["slug"] = slug
    if _field_chars(field_data) > MAX_FIELD_CHARS:
        return _fail("VALIDATION", f"field_data exceeds {MAX_FIELD_CHARS} characters")

    token = str((secret or {}).get("access_token") or (secret or {}).get("token") or "").strip()
    collection_id = str(
        (secret or {}).get("collection_id") or (secret or {}).get("collectionId") or ""
    ).strip()
    if not token:
        return _fail("CREDENTIAL", "webflow Vault JSON requires access_token")
    if not collection_id:
        return _fail("CREDENTIAL", "webflow Vault JSON requires collection_id")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "item_id": "mock-item",
            "slug": slug,
            "published": publish,
            "content": name,
            "summary": name,
        }

    path = "items/live" if publish else "items"
    url = f"{API_BASE}/collections/{collection_id}/{path}"
    payload = {"fieldData": field_data, "isArchived": False, "isDraft": not publish}
    try:
        code, resp = _request(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "accept": "application/json",
            },
            body=json.dumps(payload).encode("utf-8"),
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if code >= 400:
        return _provider_fail(code, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "webflow create item returned non-JSON")

    # Single-item create returns the item; bulk shape may wrap in items[]
    item = data
    if isinstance(data.get("items"), list) and data["items"]:
        item = data["items"][0]
    item_id = str(item.get("id") or "").strip()
    if not item_id:
        return _fail("PROVIDER", "webflow create item missing id")
    out_slug = str((item.get("fieldData") or {}).get("slug") or slug)
    return {
        "ok": True,
        "stub": False,
        "item_id": item_id,
        "slug": out_slug,
        "published": publish,
        "content": name,
        "summary": name,
    }
