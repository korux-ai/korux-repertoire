"""Canva Connect API — export design; optional Brand Template autofill. Stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://api.canva.com/rest/v1"
HTTP_TIMEOUT_S = 45
POLL_ATTEMPTS = 20
POLL_SLEEP_S = 1.5
ALLOWED_ACTIONS = frozenset({"export", "autofill_and_export"})
ALLOWED_FORMATS = frozenset({"png", "jpg", "pdf"})


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
        raise RuntimeError(f"canva HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"canva auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"canva server error ({status})")
    return _fail("PROVIDER", f"canva API {status}: {snippet}")


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _parse_field_data(raw: Any) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        source = raw
    elif isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("field_data must be a JSON object") from exc
        if not isinstance(parsed, dict):
            raise ValueError("field_data must be a JSON object")
        source = parsed
    else:
        raise ValueError("field_data must be an object")
    out: dict[str, Any] = {}
    for key, value in source.items():
        name = str(key or "").strip()
        if not name:
            continue
        if isinstance(value, dict) and value.get("type"):
            out[name] = value
        else:
            out[name] = {"type": "text", "text": str(value if value is not None else "")}
    return out


def _export_format_body(fmt: str) -> dict[str, Any]:
    if fmt == "pdf":
        return {"type": "pdf", "export_quality": "regular"}
    if fmt == "jpg":
        return {"type": "jpg", "quality": 80}
    return {"type": "png", "export_quality": "regular"}


def _poll_job(
    token: str,
    *,
    path_prefix: str,
    job_id: str,
    result_key: str,
) -> dict[str, Any]:
    url = f"{API_BASE}/{path_prefix}/{job_id}"
    for _ in range(POLL_ATTEMPTS):
        status, resp = _request("GET", url, headers=_headers(token), body=None)
        if status >= 400:
            return _provider_fail(status, resp)
        try:
            data = json.loads(resp.decode("utf-8"))
        except json.JSONDecodeError:
            return _fail("PROVIDER", f"canva {path_prefix} poll returned non-JSON")
        job = data.get("job") if isinstance(data.get("job"), dict) else data
        if not isinstance(job, dict):
            return _fail("PROVIDER", f"canva {path_prefix} unexpected job payload")
        state = str(job.get("status") or "").lower()
        if state in {"success", "completed"}:
            return {"ok": True, "job": job}
        if state in {"failed", "error"}:
            err = job.get("error") or job.get("message") or state
            return _fail("PROVIDER", f"canva {path_prefix} job failed: {err}")
        time.sleep(POLL_SLEEP_S)
    return _fail("PROVIDER", f"canva {path_prefix} job timed out")


def _autofill(token: str, *, brand_template_id: str, title: str, field_data: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "brand_template_id": brand_template_id,
        "data": field_data,
    }
    if title:
        payload["title"] = title
    status, resp = _request(
        "POST",
        f"{API_BASE}/autofills",
        headers=_headers(token),
        body=json.dumps(payload).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "canva autofill create returned non-JSON")
    job = data.get("job") if isinstance(data.get("job"), dict) else data
    job_id = str((job or {}).get("id") or data.get("id") or "").strip()
    if not job_id:
        return _fail("PROVIDER", "canva autofill missing job id")
    polled = _poll_job(token, path_prefix="autofills", job_id=job_id, result_key="design")
    if polled.get("ok") is False:
        return polled
    design = (polled["job"] or {}).get("result") or (polled["job"] or {}).get("design") or {}
    if isinstance(design, dict) and isinstance(design.get("design"), dict):
        design = design["design"]
    design_id = str((design or {}).get("id") or "").strip()
    if not design_id:
        # Some responses nest design under result.design
        result = (polled["job"] or {}).get("result")
        if isinstance(result, dict):
            design_id = str((result.get("design") or {}).get("id") or "").strip()
    if not design_id:
        return _fail("PROVIDER", "canva autofill succeeded but missing design id")
    return {"ok": True, "design_id": design_id}


def _export(token: str, *, design_id: str, fmt: str) -> dict[str, Any]:
    payload = {
        "design_id": design_id,
        "format": _export_format_body(fmt),
    }
    status, resp = _request(
        "POST",
        f"{API_BASE}/exports",
        headers=_headers(token),
        body=json.dumps(payload).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "canva export create returned non-JSON")
    job = data.get("job") if isinstance(data.get("job"), dict) else data
    job_id = str((job or {}).get("id") or data.get("id") or "").strip()
    if not job_id:
        return _fail("PROVIDER", "canva export missing job id")
    polled = _poll_job(token, path_prefix="exports", job_id=job_id, result_key="urls")
    if polled.get("ok") is False:
        return polled
    job_body = polled["job"]
    urls = job_body.get("urls") or (job_body.get("result") or {}).get("urls") or []
    if not isinstance(urls, list):
        urls = []
    urls = [str(u).strip() for u in urls if str(u).strip()]
    if not urls:
        return _fail("PROVIDER", "canva export succeeded but missing urls")
    return {"ok": True, "urls": urls}


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    args = args or {}
    action = str(args.get("action") or "export").strip().lower() or "export"
    design_id = str(args.get("design_id") or "").strip()
    brand_template_id = str(args.get("brand_template_id") or "").strip()
    title = str(args.get("title") or "").strip()
    fmt = str(args.get("format") or "png").strip().lower() or "png"

    if action not in ALLOWED_ACTIONS:
        return _fail("VALIDATION", f"action must be one of {sorted(ALLOWED_ACTIONS)}")
    if fmt not in ALLOWED_FORMATS:
        return _fail("VALIDATION", f"format must be one of {sorted(ALLOWED_FORMATS)}")

    try:
        field_data = _parse_field_data(args.get("field_data") or args.get("data"))
    except ValueError as exc:
        return _fail("VALIDATION", str(exc))

    if action == "export" and not design_id:
        return _fail("VALIDATION", "design_id is required for action=export")
    if action == "autofill_and_export":
        if not brand_template_id:
            return _fail("VALIDATION", "brand_template_id is required for autofill_and_export")
        if not field_data:
            return _fail("VALIDATION", "field_data is required for autofill_and_export")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "design_id": design_id or "mock-design",
            "export_urls": ["https://example.com/canva-export.png"],
            "content": title or design_id or brand_template_id or "canva-export",
            "summary": f"canva {action} ({fmt})",
        }

    token = str((secret or {}).get("access_token") or (secret or {}).get("token") or "").strip()
    if not token:
        return _fail("CREDENTIAL", "canva Vault JSON requires access_token")

    try:
        if action == "autofill_and_export":
            filled = _autofill(
                token,
                brand_template_id=brand_template_id,
                title=title,
                field_data=field_data,
            )
            if filled.get("ok") is False:
                return filled
            design_id = str(filled["design_id"])

        exported = _export(token, design_id=design_id, fmt=fmt)
        if exported.get("ok") is False:
            return exported
        urls = exported["urls"]
        label = title or design_id
        return {
            "ok": True,
            "stub": False,
            "design_id": design_id,
            "export_urls": urls,
            "content": urls[0],
            "summary": f"canva export {fmt}: {label}",
        }
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
