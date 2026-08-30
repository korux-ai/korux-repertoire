"""Notion pages API. Stdlib HTTPS only."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

NOTION_VERSION = "2022-06-28"
DEFAULT_BASE = "https://api.notion.com"
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


def _request(method: str, url: str, *, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    req = Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            return int(resp.status), resp.read()
    except HTTPError as exc:
        return int(exc.code), exc.read() if exc.fp else b""
    except URLError as exc:
        raise RuntimeError(f"notion HTTP error: {exc.reason}") from exc


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:300]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"notion auth failed ({status})")
    return _fail("PROVIDER", f"notion API {status}: {snippet}")


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    action = str((args or {}).get("action") or "create_page").strip().lower()
    title = str((args or {}).get("title") or (args or {}).get("name") or "").strip() or "Untitled"
    body = str((args or {}).get("body") or (args or {}).get("content") or (args or {}).get("summary") or "")
    if not body.strip() and action != "update_page":
        return _fail("VALIDATION", "body is required")

    token = str((secret or {}).get("token") or (secret or {}).get("api_token") or "").strip()
    if not token:
        return _fail("CREDENTIAL", "notion Vault JSON requires token")
    parent = str(
        (args or {}).get("parent_page_id")
        or (secret or {}).get("parent_page_id")
        or (secret or {}).get("parent")
        or ""
    ).strip()
    database_id = str((args or {}).get("database_id") or (secret or {}).get("database_id") or "").strip()
    page_id = str((args or {}).get("page_id") or "").strip()
    base = str((secret or {}).get("base_url") or DEFAULT_BASE).rstrip("/")

    if _http_mock():
        pid = page_id or "notion-mock-page"
        return {
            "ok": True,
            "stub": True,
            "action": action,
            "page_id": pid,
            "page_url": f"https://www.notion.so/mock-{pid}",
            "title": title,
            "content": body,
            "summary": body,
        }

    try:
        if action == "create_database_item":
            if not database_id:
                return _fail("VALIDATION", "database_id is required for create_database_item")
            payload: dict[str, Any] = {
                "parent": {"database_id": database_id},
                "properties": {
                    "Name": {"title": [{"type": "text", "text": {"content": title[:2000]}}]}
                },
            }
            if body:
                payload["children"] = [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": body[:1900]}}]
                        },
                    }
                ]
            status, resp = _request(
                "POST",
                f"{base}/v1/pages",
                headers=_headers(token),
                body=json.dumps(payload).encode("utf-8"),
            )
        elif action == "update_page":
            if not page_id:
                return _fail("VALIDATION", "page_id is required for update_page")
            props: dict[str, Any] = {}
            if title and title != "Untitled":
                props["title"] = {"title": [{"type": "text", "text": {"content": title[:2000]}}]}
            payload = {"properties": props} if props else {}
            status, resp = _request(
                "PATCH",
                f"{base}/v1/pages/{page_id}",
                headers=_headers(token),
                body=json.dumps(payload).encode("utf-8"),
            )
            if status < 400 and body.strip():
                _request(
                    "PATCH",
                    f"{base}/v1/blocks/{page_id}/children",
                    headers=_headers(token),
                    body=json.dumps(
                        {
                            "children": [
                                {
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [
                                            {"type": "text", "text": {"content": body[:1900]}}
                                        ]
                                    },
                                }
                            ]
                        }
                    ).encode("utf-8"),
                )
        else:
            if not parent:
                return _fail("VALIDATION", "parent_page_id is required (Vault or args)")
            payload = {
                "parent": {"page_id": parent},
                "properties": {
                    "title": {"title": [{"type": "text", "text": {"content": title[:2000]}}]}
                },
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": body[:1900]}}]
                        },
                    }
                ]
                if body
                else [],
            }
            status, resp = _request(
                "POST",
                f"{base}/v1/pages",
                headers=_headers(token),
                body=json.dumps(payload).encode("utf-8"),
            )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))

    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8")) if resp else {}
    except json.JSONDecodeError:
        return _fail("PROVIDER", "notion returned non-JSON")
    pid = str((data or {}).get("id") or page_id or "").strip()
    if not pid:
        return _fail("PROVIDER", "notion response missing page id")
    url = str((data or {}).get("url") or "")
    return {
        "ok": True,
        "stub": False,
        "action": action,
        "page_id": pid,
        "page_url": url or None,
        "title": title,
        "content": body,
        "summary": body,
    }
