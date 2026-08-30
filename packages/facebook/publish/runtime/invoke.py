"""Facebook Page text / single-image post. Graph v21.0, stdlib HTTPS only."""

from __future__ import annotations

import json
import os
import ssl
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
HTTP_TIMEOUT_S = 45


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {"1", "true", "TRUE", "yes"}


def _secret_fields(secret: dict[str, Any]) -> dict[str, Any]:
    page_id = str(secret.get("page_id") or "").strip()
    token = str(secret.get("page_access_token") or "").strip()
    if not page_id or not token:
        return _fail("CREDENTIAL", "facebook Vault JSON requires page_id and page_access_token")
    return {"page_id": page_id, "page_access_token": token}


def _sniff_image(data: bytes, filename: str, content_type: str) -> tuple[str, str] | dict[str, Any]:
    if len(data) > MAX_IMAGE_BYTES:
        return _fail("VALIDATION", "image exceeds 5MB limit")
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


def _request(method: str, url: str, *, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    req = Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            return int(resp.status), resp.read()
    except HTTPError as exc:
        return int(exc.code), exc.read() if exc.fp else b""
    except URLError as exc:
        raise RuntimeError(f"facebook HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:300]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"facebook auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"facebook server error ({status})")
    return _fail("PROVIDER", f"facebook API {status}: {snippet}")


def _multipart(
    fields: dict[str, str], filename: str, data: bytes, content_type: str
) -> tuple[bytes, str]:
    boundary = f"----KoruxFacebook{uuid.uuid4().hex}"
    crlf = b"\r\n"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}".encode(),
                crlf,
                f'Content-Disposition: form-data; name="{key}"'.encode(),
                crlf,
                crlf,
                str(value).encode("utf-8"),
                crlf,
            ]
        )
    chunks.extend(
        [
            f"--{boundary}".encode(),
            crlf,
            f'Content-Disposition: form-data; name="source"; filename="{filename}"'.encode(),
            crlf,
            f"Content-Type: {content_type}".encode(),
            crlf,
            crlf,
            data,
            crlf,
            f"--{boundary}--".encode(),
            crlf,
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _post_feed(page_id: str, token: str, message: str) -> dict[str, Any]:
    url = f"{GRAPH_BASE}/{page_id}/feed"
    body = urlencode({"message": message, "access_token": token}).encode("utf-8")
    status, resp = _request(
        "POST",
        url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
    )
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "facebook feed API returned non-JSON")
    post_id = str(data.get("id") or "").strip()
    if not post_id:
        return _fail("PROVIDER", "facebook feed API missing id")
    return {
        "ok": True,
        "stub": False,
        "post_id": post_id,
        "content": message,
        "summary": message,
    }


def _post_photo(page_id: str, token: str, message: str, image: dict[str, Any]) -> dict[str, Any]:
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
    filename, content_type = sniffed  # type: ignore[misc]
    url = f"{GRAPH_BASE}/{page_id}/photos"
    body, ctype = _multipart(
        {"caption": message, "access_token": token},
        filename,
        bytes(raw),
        content_type,
    )
    status, resp = _request("POST", url, headers={"Content-Type": ctype}, body=body)
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "facebook photos API returned non-JSON")
    post_id = str(data.get("post_id") or data.get("id") or "").strip()
    if not post_id:
        return _fail("PROVIDER", "facebook photos API missing id")
    return {
        "ok": True,
        "stub": False,
        "post_id": post_id,
        "content": message,
        "summary": message,
    }


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    text = str((args or {}).get("message") or "").strip()
    if not text:
        return _fail("VALIDATION", "message is required")
    if len(text) > 5000:
        return _fail("VALIDATION", "message exceeds 5000 characters")

    image_id = str((args or {}).get("image_file_id") or "").strip()
    image = (context or {}).get("image") if isinstance(context, dict) else None
    has_image = isinstance(image, dict) and bool(image.get("bytes"))
    if image_id and not has_image:
        return _fail("VALIDATION", "image_file_id set but context.image bytes missing")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "post_id": "mock-post",
            "content": text,
            "summary": text,
        }

    creds = _secret_fields(secret or {})
    if creds.get("ok") is False:
        return creds
    page_id = str(creds["page_id"])
    token = str(creds["page_access_token"])

    try:
        if has_image:
            return _post_photo(page_id, token, text, image)  # type: ignore[arg-type]
        return _post_feed(page_id, token, text)
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
