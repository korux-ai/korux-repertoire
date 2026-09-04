"""Xiaohongshu (RED) image note publish via Owner-configured OpenAPI. Stdlib HTTPS.

Does NOT call creator web scrape endpoints. Paths are Vault-configurable because
official note-publish availability depends on enterprise/partner approval.
"""

from __future__ import annotations

import json
import os
import ssl
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_BASE = "https://open.xiaohongshu.com"
DEFAULT_UPLOAD = "/api/sns/v1/note/image/upload"
DEFAULT_POST = "/api/sns/v1/note/post"
HTTP_TIMEOUT_S = 60
MAX_TITLE = 40
MAX_CAPTION = 1000
MAX_IMAGE_BYTES = 12 * 1024 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


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
        raise RuntimeError(f"xiaohongshu HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"xiaohongshu auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"xiaohongshu server error ({status})")
    return _fail("PROVIDER", f"xiaohongshu API {status}: {snippet}")


def _topics(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        return [t.strip().lstrip("#") for t in raw.replace("，", ",").split(",") if t.strip()][:10]
    if isinstance(raw, list):
        return [str(t).strip().lstrip("#") for t in raw if str(t).strip()][:10]
    return []


def _sniff(data: bytes, filename: str, content_type: str) -> tuple[str, str] | dict[str, Any]:
    if len(data) > MAX_IMAGE_BYTES:
        return _fail("VALIDATION", f"image exceeds {MAX_IMAGE_BYTES} bytes")
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if data.startswith(JPEG_MAGIC) or "jpeg" in ctype or name.endswith((".jpg", ".jpeg")):
        return ("image.jpg", "image/jpeg")
    if data.startswith(PNG_MAGIC) or "png" in ctype or name.endswith(".png"):
        return ("image.png", "image/png")
    return _fail("VALIDATION", "image must be JPEG or PNG")


def _multipart(fields: dict[str, str], filename: str, data: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = f"----KoruxXhs{uuid.uuid4().hex}"
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
                value.encode("utf-8"),
                crlf,
            ]
        )
    chunks.extend(
        [
            f"--{boundary}".encode(),
            crlf,
            f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode(),
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


def _extract_image_id(payload: dict[str, Any]) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    for key in ("image_id", "file_id", "media_id", "id"):
        val = str((data or {}).get(key) or "").strip()
        if val:
            return val
    images = (data or {}).get("images") if isinstance(data, dict) else None
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict):
            for key in ("image_id", "file_id", "id"):
                val = str(first.get(key) or "").strip()
                if val:
                    return val
        if isinstance(first, str) and first.strip():
            return first.strip()
    return ""


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    args = args or {}
    secret = secret or {}
    title = str(args.get("title") or "").strip()
    caption = str(args.get("caption") or args.get("desc") or args.get("content") or "").strip()
    image_file_id = str(args.get("image_file_id") or "").strip()
    image_url = str(args.get("image_url") or "").strip()
    topics = _topics(args.get("topics"))

    if not caption:
        return _fail("VALIDATION", "caption is required")
    if len(caption) > MAX_CAPTION:
        return _fail("VALIDATION", f"caption exceeds {MAX_CAPTION} characters")
    if len(title) > MAX_TITLE:
        return _fail("VALIDATION", f"title exceeds {MAX_TITLE} characters")

    image = (context or {}).get("image") if isinstance(context, dict) else None
    has_bytes = isinstance(image, dict) and isinstance(image.get("bytes"), (bytes, bytearray)) and bool(image.get("bytes"))
    public = ""
    if isinstance(image, dict):
        public = str(image.get("public_url") or image.get("url") or "").strip()
    if image_url:
        public = image_url
    if public:
        parsed = urlparse(public)
        if parsed.scheme != "https" or not parsed.netloc:
            return _fail("VALIDATION", "image_url must be https")
    if image_file_id and not has_bytes and not public:
        return _fail("VALIDATION", "image_file_id set but context.image bytes/public_url missing")
    if not has_bytes and not public:
        return _fail("VALIDATION", "image_file_id (with context.image) or image_url is required")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "note_id": "mock-xhs-note",
            "content": caption,
            "summary": title or caption[:80],
        }

    token = str(secret.get("access_token") or secret.get("token") or "").strip()
    if not token:
        return _fail("CREDENTIAL", "xiaohongshu Vault requires access_token")
    base = str(secret.get("api_base") or DEFAULT_BASE).strip().rstrip("/") or DEFAULT_BASE
    upload_path = str(secret.get("upload_path") or DEFAULT_UPLOAD).strip() or DEFAULT_UPLOAD
    post_path = str(secret.get("post_path") or DEFAULT_POST).strip() or DEFAULT_POST
    if not upload_path.startswith("/"):
        upload_path = "/" + upload_path
    if not post_path.startswith("/"):
        post_path = "/" + post_path

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    image_ids: list[str] = []
    try:
        if has_bytes:
            raw = bytes(image["bytes"])  # type: ignore[index]
            sniffed = _sniff(
                raw,
                str(image.get("filename") or ""),  # type: ignore[union-attr]
                str(image.get("content_type") or ""),  # type: ignore[union-attr]
            )
            if isinstance(sniffed, dict) and sniffed.get("ok") is False:
                return sniffed
            filename, content_type = sniffed  # type: ignore[misc]
            body, ctype = _multipart({}, filename, raw, content_type)
            code, resp = _request(
                "POST",
                f"{base}{upload_path}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": ctype},
                body=body,
            )
            if code >= 400:
                return _provider_fail(code, resp)
            try:
                uploaded = json.loads(resp.decode("utf-8"))
            except json.JSONDecodeError:
                return _fail("PROVIDER", "xiaohongshu upload returned non-JSON")
            if not isinstance(uploaded, dict):
                return _fail("PROVIDER", "xiaohongshu upload unexpected payload")
            image_id = _extract_image_id(uploaded)
            if not image_id:
                return _fail("PROVIDER", "xiaohongshu upload missing image id")
            image_ids.append(image_id)
        else:
            # Some partner gateways accept image_urls instead of pre-upload
            pass

        payload: dict[str, Any] = {
            "title": title or caption[:MAX_TITLE],
            "content": caption,
            "desc": caption,
        }
        if image_ids:
            payload["image_ids"] = image_ids
        if public and not image_ids:
            payload["image_urls"] = [public]
        if topics:
            payload["topics"] = topics

        code, resp = _request(
            "POST",
            f"{base}{post_path}",
            headers=auth_headers,
            body=json.dumps(payload).encode("utf-8"),
        )
        if code >= 400:
            return _provider_fail(code, resp)
        try:
            data = json.loads(resp.decode("utf-8"))
        except json.JSONDecodeError:
            return _fail("PROVIDER", "xiaohongshu post returned non-JSON")
        if not isinstance(data, dict):
            return _fail("PROVIDER", "xiaohongshu post unexpected payload")
        # Common success shapes
        if data.get("success") is False or (
            data.get("code") not in (None, 0, "0", 200, "200") and data.get("data") is None and data.get("note_id") is None
        ):
            # only treat as error when explicit failure markers present
            if data.get("success") is False or (isinstance(data.get("code"), int) and data["code"] != 0):
                return _fail("PROVIDER", f"xiaohongshu post rejected: {data.get('message') or data.get('code')}")

        note_data = data.get("data") if isinstance(data.get("data"), dict) else data
        note_id = str((note_data or {}).get("note_id") or (note_data or {}).get("id") or "").strip()
        if not note_id:
            note_id = "unknown"
        return {
            "ok": True,
            "stub": False,
            "note_id": note_id,
            "content": caption,
            "summary": title or caption[:80],
        }
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
