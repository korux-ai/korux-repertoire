"""HubSpot CRM contact upsert by email or update by contact_id. CRM v3, stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API_BASE = "https://api.hubapi.com"
HTTP_TIMEOUT_S = 40

KNOWN_PROP_KEYS = (
    "email",
    "firstname",
    "lastname",
    "phone",
    "company",
    "jobtitle",
    "website",
    "lifecyclestage",
)


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


def _build_properties(args: dict[str, Any]) -> dict[str, str]:
    props: dict[str, str] = {}
    for key in KNOWN_PROP_KEYS:
        val = str(args.get(key) or "").strip()
        if val:
            props[key] = val if key != "email" else val.lower()
    extra = args.get("properties")
    if isinstance(extra, str) and extra.strip():
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            raise ValueError("properties must be a JSON object") from None
    if isinstance(extra, dict):
        for k, v in extra.items():
            name = str(k or "").strip()
            if not name or name in props:
                continue
            text = str(v if v is not None else "").strip()
            if text:
                props[name] = text
    elif extra not in (None, ""):
        raise ValueError("properties must be an object")
    return props


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


def _create_contact(token: str, props: dict[str, str]) -> dict[str, Any]:
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


def _update_contact(token: str, contact_id: str, props: dict[str, str]) -> dict[str, Any]:
    status, resp = _request(
        "PATCH",
        f"{API_BASE}/crm/v3/objects/contacts/{quote(contact_id, safe='')}",
        headers=_headers(token),
        body=json.dumps({"properties": props}).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "hubspot update contact returned non-JSON")
    out_id = str(data.get("id") or contact_id).strip()
    return {"ok": True, "contact_id": out_id}


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    args = args or {}
    contact_id = str(args.get("contact_id") or "").strip()
    email = str(args.get("email") or "").strip().lower()
    if not contact_id and not email:
        return _fail("VALIDATION", "email or contact_id is required")

    try:
        props = _build_properties(args)
    except ValueError as exc:
        return _fail("VALIDATION", str(exc))

    if email and "email" not in props:
        props["email"] = email
    if contact_id and not props:
        return _fail("VALIDATION", "at least one property is required to update")
    if not contact_id and "email" not in props:
        return _fail("VALIDATION", "email is required when creating a contact")

    token = str((secret or {}).get("access_token") or (secret or {}).get("token") or "").strip()
    if not token:
        return _fail("CREDENTIAL", "hubspot Vault JSON requires access_token")

    summary_email = props.get("email") or email or contact_id
    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "contact_id": contact_id or "mock-contact",
            "action": "updated" if contact_id else "created",
            "email": props.get("email") or email or None,
            "content": summary_email,
            "summary": f"upsert {summary_email}",
        }

    try:
        action = "updated"
        if contact_id:
            # Update path: do not force email into PATCH unless provided
            patch_props = dict(props)
            if not email:
                patch_props.pop("email", None)
            updated = _update_contact(token, contact_id, patch_props)
            if updated.get("ok") is False:
                return updated
            contact_id = str(updated["contact_id"])
        else:
            found = _find_contact_by_email(token, props["email"])
            if found.get("ok") is False:
                return found
            existing = str(found.get("contact_id") or "").strip()
            if existing:
                patch_props = dict(props)
                # email already identifies the record; still allowed on PATCH
                updated = _update_contact(token, existing, patch_props)
                if updated.get("ok") is False:
                    return updated
                contact_id = str(updated["contact_id"])
                action = "updated"
            else:
                created = _create_contact(token, props)
                if created.get("ok") is False:
                    return created
                contact_id = str(created["contact_id"])
                action = "created"

        return {
            "ok": True,
            "stub": False,
            "contact_id": contact_id,
            "action": action,
            "email": props.get("email") or email or None,
            "content": summary_email,
            "summary": f"{action} contact {summary_email}",
        }
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
