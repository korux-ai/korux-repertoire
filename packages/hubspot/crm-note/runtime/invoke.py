"""HubSpot CRM note on a contact. CRM v3, stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API_BASE = "https://api.hubapi.com"
NOTE_TO_CONTACT_ASSOCIATION = 202
HTTP_TIMEOUT_S = 40
MAX_BODY = 10000


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
        raise RuntimeError(f"hubspot HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"hubspot auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"hubspot server error ({status})")
    return _fail("PROVIDER", f"hubspot API {status}: {snippet}")


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _find_contact_by_email(token: str, email: str) -> dict[str, Any]:
    url = f"{API_BASE}/crm/v3/objects/contacts/{quote(email, safe='')}?idProperty=email"
    status, resp = _request("GET", url, headers=_headers(token), body=None)
    if status == 404:
        return {"ok": True, "contact_id": None}
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "hubspot contact lookup returned non-JSON")
    contact_id = str(data.get("id") or "").strip()
    if not contact_id:
        return _fail("PROVIDER", "hubspot contact lookup missing id")
    return {"ok": True, "contact_id": contact_id}


def _create_contact(token: str, *, email: str, firstname: str, lastname: str) -> dict[str, Any]:
    props: dict[str, str] = {"email": email}
    if firstname:
        props["firstname"] = firstname
    if lastname:
        props["lastname"] = lastname
    status, resp = _request(
        "POST",
        f"{API_BASE}/crm/v3/objects/contacts",
        headers=_headers(token),
        body=json.dumps({"properties": props}).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "hubspot create contact returned non-JSON")
    contact_id = str(data.get("id") or "").strip()
    if not contact_id:
        return _fail("PROVIDER", "hubspot create contact missing id")
    return {"ok": True, "contact_id": contact_id}


def _create_note(token: str, *, body: str, contact_id: str) -> dict[str, Any]:
    payload = {
        "properties": {
            "hs_timestamp": str(int(time.time() * 1000)),
            "hs_note_body": body,
        },
        "associations": [
            {
                "to": {"id": contact_id},
                "types": [
                    {
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": NOTE_TO_CONTACT_ASSOCIATION,
                    }
                ],
            }
        ],
    }
    status, resp = _request(
        "POST",
        f"{API_BASE}/crm/v3/objects/notes",
        headers=_headers(token),
        body=json.dumps(payload).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "hubspot create note returned non-JSON")
    note_id = str(data.get("id") or "").strip()
    if not note_id:
        return _fail("PROVIDER", "hubspot create note missing id")
    return {"ok": True, "note_id": note_id}


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    args = args or {}
    body = str(args.get("body") or args.get("note") or args.get("content") or "").strip()
    if not body:
        return _fail("VALIDATION", "body is required")
    if len(body) > MAX_BODY:
        return _fail("VALIDATION", f"body exceeds {MAX_BODY} characters")

    contact_id = str(args.get("contact_id") or "").strip()
    email = str(args.get("email") or "").strip().lower()
    firstname = str(args.get("firstname") or "").strip()
    lastname = str(args.get("lastname") or "").strip()
    if not contact_id and not email:
        return _fail("VALIDATION", "contact_id or email is required")

    token = str((secret or {}).get("access_token") or (secret or {}).get("token") or "").strip()
    if not token:
        return _fail("CREDENTIAL", "hubspot Vault JSON requires access_token")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "note_id": "mock-note",
            "contact_id": contact_id or "mock-contact",
            "content": body,
            "summary": body[:200],
        }

    try:
        if not contact_id:
            found = _find_contact_by_email(token, email)
            if found.get("ok") is False:
                return found
            contact_id = str(found.get("contact_id") or "").strip()
            if not contact_id:
                created = _create_contact(
                    token, email=email, firstname=firstname, lastname=lastname
                )
                if created.get("ok") is False:
                    return created
                contact_id = str(created["contact_id"])

        note = _create_note(token, body=body, contact_id=contact_id)
        if note.get("ok") is False:
            return note
        return {
            "ok": True,
            "stub": False,
            "note_id": note["note_id"],
            "contact_id": contact_id,
            "content": body,
            "summary": body[:200],
        }
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
