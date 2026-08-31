"""LinkedIn Company Page text / single-image post. Posts API + Images API, stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REST_BASE = "https://api.linkedin.com/rest"
DEFAULT_LINKEDIN_VERSION = "202503"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_COMMENTARY = 3000
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
HTTP_TIMEOUT_S = 60


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {"1", "true", "TRUE", "yes"}


def _secret_fields(secret: dict[str, Any]) -> dict[str, Any]:
    token = str(secret.get("access_token") or secret.get("token") or "").strip()
    org = str(secret.get("organization_id") or secret.get("org_id") or "").strip()
    org = org.removeprefix("urn:li:organization:")
    version = str(secret.get("linkedin_version") or DEFAULT_LINKEDIN_VERSION).strip() or DEFAULT_LINKEDIN_VERSION
    if not token or not org:
        return _fail(
            "CREDENTIAL",
            "linkedin Vault JSON requires access_token and organization_id",
        )
    return {
        "access_token": token,
        "organization_id": org,
        "linkedin_version": version,
        "author_urn": f"urn:li:organization:{org}",
    }


def _headers(token: str, version: str, *, content_type: str | None = "application/json") -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": version,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _sniff_image(data: bytes, filename: str, content_type: str) -> tuple[str, str] | dict[str, Any]:
    if len(data) > MAX_IMAGE_BYTES:
        return _fail("VALIDATION", "image exceeds 8MB LinkedIn limit")
    name = (filename or "image").lower()
    ctype = (content_type or "").lower()
    if data.startswith(JPEG_MAGIC) or ctype in {"image/jpeg", "image/jpg"} or name.endswith((".jpg", ".jpeg")):
        if not data.startswith(JPEG_MAGIC):
            return _fail("VALIDATION", "image is not JPEG/PNG")
        return ("image.jpg", "image/jpeg")
    if data.startswith(PNG_MAGIC) or ctype == "image/png" or name.endswith(".png"):
        if not data.startswith(PNG_MAGIC):
            return _fail("VALIDATION", "image is not JPEG/PNG")
        return ("image.png", "image/png")
    return _fail("VALIDATION", "image must be JPEG or PNG")


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: bytes | None,
) -> tuple[int, bytes, dict[str, str]]:
    req = Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return int(resp.status), resp.read(), hdrs
    except HTTPError as exc:
        hdrs = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return int(exc.code), exc.read() if exc.fp else b"", hdrs
    except URLError as exc:
        raise RuntimeError(f"linkedin HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"linkedin auth failed ({status}): {snippet}")
    if status >= 500:
        return _fail("PROVIDER", f"linkedin server error ({status})")
    return _fail("PROVIDER", f"linkedin API {status}: {snippet}")


def _upload_image(creds: dict[str, str], image: dict[str, Any]) -> dict[str, Any]:
    raw = image.get("bytes")
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        return _fail("VALIDATION", "context.image.bytes is required when posting an image")
    sniffed = _sniff_image(
        bytes(raw),
        str(image.get("filename") or ""),
        str(image.get("content_type") or ""),
    )
    if isinstance(sniffed, dict) and sniffed.get("ok") is False:
        return sniffed
    _filename, content_type = sniffed  # type: ignore[misc]

    init_body = json.dumps(
        {"initializeUploadRequest": {"owner": creds["author_urn"]}}
    ).encode("utf-8")
    status, resp, _ = _request(
        "POST",
        f"{REST_BASE}/images?action=initializeUpload",
        headers=_headers(creds["access_token"], creds["linkedin_version"]),
        body=init_body,
    )
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "linkedin initializeUpload returned non-JSON")
    value = data.get("value") if isinstance(data, dict) else None
    if not isinstance(value, dict):
        return _fail("PROVIDER", "linkedin initializeUpload missing value")
    upload_url = str(value.get("uploadUrl") or "").strip()
    image_urn = str(value.get("image") or "").strip()
    if not upload_url or not image_urn:
        return _fail("PROVIDER", "linkedin initializeUpload missing uploadUrl/image")

    put_headers = {
        "Authorization": f"Bearer {creds['access_token']}",
        "Content-Type": content_type,
    }
    status, resp, _ = _request("PUT", upload_url, headers=put_headers, body=bytes(raw))
    if status >= 400:
        return _provider_fail(status, resp)
    return {"ok": True, "image_urn": image_urn}


def _create_post(
    creds: dict[str, str], commentary: str, image_urn: str | None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "author": creds["author_urn"],
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if image_urn:
        payload["content"] = {"media": {"id": image_urn}}

    status, resp, hdrs = _request(
        "POST",
        f"{REST_BASE}/posts",
        headers=_headers(creds["access_token"], creds["linkedin_version"]),
        body=json.dumps(payload).encode("utf-8"),
    )
    if status >= 400:
        return _provider_fail(status, resp)

    post_id = str(hdrs.get("x-restli-id") or "").strip()
    if not post_id and resp:
        try:
            data = json.loads(resp.decode("utf-8"))
            post_id = str((data or {}).get("id") or "").strip()
        except json.JSONDecodeError:
            post_id = ""
    if not post_id:
        return _fail("PROVIDER", "linkedin posts API missing x-restli-id")
    return {
        "ok": True,
        "stub": False,
        "post_id": post_id,
        "content": commentary,
        "summary": commentary,
    }


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    text = str((args or {}).get("commentary") or (args or {}).get("message") or "").strip()
    if not text:
        return _fail("VALIDATION", "commentary is required")
    if len(text) > MAX_COMMENTARY:
        return _fail("VALIDATION", f"commentary exceeds {MAX_COMMENTARY} characters")

    image_id = str((args or {}).get("image_file_id") or "").strip()
    image = (context or {}).get("image") if isinstance(context, dict) else None
    has_image = isinstance(image, dict) and bool(image.get("bytes"))
    if image_id and not has_image:
        return _fail("VALIDATION", "image_file_id set but context.image bytes missing")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "post_id": "urn:li:share:mock-post",
            "content": text,
            "summary": text,
        }

    creds = _secret_fields(secret or {})
    if creds.get("ok") is False:
        return creds

    try:
        image_urn: str | None = None
        if has_image:
            uploaded = _upload_image(creds, image)  # type: ignore[arg-type]
            if uploaded.get("ok") is False:
                return uploaded
            image_urn = str(uploaded["image_urn"])
        return _create_post(creds, text, image_urn)
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
