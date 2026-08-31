"""Instagram professional Feed image post. Graph Content Publishing, stdlib HTTPS.

Images: prefer context.image.public_url (https). Otherwise upload an unpublished
photo to the linked Facebook Page, read a Graph image URL, then create + publish
the IG media container (Meta requires a fetchable image_url for Feed photos).
"""

from __future__ import annotations

import json
import os
import ssl
import time
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_CAPTION = 2200
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
HTTP_TIMEOUT_S = 60
CONTAINER_POLL_ATTEMPTS = 8
CONTAINER_POLL_SLEEP_S = 2.0


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {"1", "true", "TRUE", "yes"}


def _secret_fields(secret: dict[str, Any]) -> dict[str, Any]:
    ig_user_id = str(secret.get("ig_user_id") or secret.get("instagram_user_id") or "").strip()
    token = str(secret.get("page_access_token") or secret.get("access_token") or "").strip()
    page_id = str(secret.get("page_id") or "").strip()
    if not ig_user_id or not token or not page_id:
        return _fail(
            "CREDENTIAL",
            "instagram Vault JSON requires ig_user_id, page_access_token, and page_id",
        )
    return {"ig_user_id": ig_user_id, "page_access_token": token, "page_id": page_id}


def _sniff_image(data: bytes, filename: str, content_type: str) -> tuple[str, str] | dict[str, Any]:
    if len(data) > MAX_IMAGE_BYTES:
        return _fail("VALIDATION", "image exceeds 8MB limit")
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
        raise RuntimeError(f"instagram HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"instagram auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"instagram server error ({status})")
    return _fail("PROVIDER", f"instagram API {status}: {snippet}")


def _multipart(
    fields: dict[str, str], filename: str, data: bytes, content_type: str
) -> tuple[bytes, str]:
    boundary = f"----KoruxInstagram{uuid.uuid4().hex}"
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


def _resolve_image_url(creds: dict[str, str], image: dict[str, Any]) -> dict[str, Any]:
    public_url = str(image.get("public_url") or image.get("url") or "").strip()
    if public_url.startswith("https://"):
        return {"ok": True, "image_url": public_url}

    raw = image.get("bytes")
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        return _fail(
            "VALIDATION",
            "Instagram needs context.image.public_url (https) or context.image.bytes with page_id upload",
        )
    sniffed = _sniff_image(
        bytes(raw),
        str(image.get("filename") or ""),
        str(image.get("content_type") or ""),
    )
    if isinstance(sniffed, dict) and sniffed.get("ok") is False:
        return sniffed
    filename, content_type = sniffed  # type: ignore[misc]

    # Unpublished Page photo → Graph returns a CDN URL Meta can fetch for IG.
    url = f"{GRAPH_BASE}/{creds['page_id']}/photos"
    body, ctype = _multipart(
        {
            "published": "false",
            "temporary": "true",
            "access_token": creds["page_access_token"],
        },
        filename,
        bytes(raw),
        content_type,
    )
    status, resp = _request("POST", url, headers={"Content-Type": ctype}, body=body)
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        photo = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "facebook photos API returned non-JSON")
    photo_id = str(photo.get("id") or "").strip()
    if not photo_id:
        return _fail("PROVIDER", "facebook unpublished photo missing id")

    fields_url = (
        f"{GRAPH_BASE}/{photo_id}?fields=images&access_token={creds['page_access_token']}"
    )
    status, resp = _request("GET", fields_url, headers={}, body=None)
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        meta = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "facebook photo fields returned non-JSON")
    images = meta.get("images") if isinstance(meta, dict) else None
    if not isinstance(images, list) or not images:
        return _fail("PROVIDER", "facebook photo has no images[].source for Instagram")
    # Prefer largest width.
    best = max(
        (img for img in images if isinstance(img, dict) and img.get("source")),
        key=lambda img: int(img.get("width") or 0),
        default=None,
    )
    image_url = str((best or {}).get("source") or "").strip()
    if not image_url.startswith("https://"):
        return _fail("PROVIDER", "facebook photo source is not an https URL")
    return {"ok": True, "image_url": image_url}


def _create_container(creds: dict[str, str], caption: str, image_url: str) -> dict[str, Any]:
    qs = urlencode(
        {
            "image_url": image_url,
            "caption": caption,
            "access_token": creds["page_access_token"],
        }
    )
    url = f"{GRAPH_BASE}/{creds['ig_user_id']}/media?{qs}"
    status, resp = _request("POST", url, headers={}, body=b"")
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "instagram media container returned non-JSON")
    creation_id = str(data.get("id") or "").strip()
    if not creation_id:
        return _fail("PROVIDER", "instagram media container missing id")
    return {"ok": True, "creation_id": creation_id}


def _wait_container_ready(creds: dict[str, str], creation_id: str) -> dict[str, Any]:
    for _ in range(CONTAINER_POLL_ATTEMPTS):
        url = (
            f"{GRAPH_BASE}/{creation_id}"
            f"?fields=status_code&access_token={creds['page_access_token']}"
        )
        status, resp = _request("GET", url, headers={}, body=None)
        if status >= 400:
            return _provider_fail(status, resp)
        try:
            data = json.loads(resp.decode("utf-8"))
        except json.JSONDecodeError:
            return _fail("PROVIDER", "instagram container status returned non-JSON")
        code = str(data.get("status_code") or "").upper()
        if code in {"FINISHED", "PUBLISHED"}:
            return {"ok": True}
        if code in {"ERROR", "EXPIRED"}:
            return _fail("PROVIDER", f"instagram container status={code}")
        time.sleep(CONTAINER_POLL_SLEEP_S)
    # Publish often still works if status was IN_PROGRESS briefly.
    return {"ok": True}


def _publish(creds: dict[str, str], creation_id: str) -> dict[str, Any]:
    qs = urlencode(
        {"creation_id": creation_id, "access_token": creds["page_access_token"]}
    )
    url = f"{GRAPH_BASE}/{creds['ig_user_id']}/media_publish?{qs}"
    status, resp = _request("POST", url, headers={}, body=b"")
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "instagram media_publish returned non-JSON")
    media_id = str(data.get("id") or "").strip()
    if not media_id:
        return _fail("PROVIDER", "instagram media_publish missing id")
    return {"ok": True, "media_id": media_id}


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    caption = str((args or {}).get("caption") or (args or {}).get("message") or "").strip()
    if not caption:
        return _fail("VALIDATION", "caption is required")
    if len(caption) > MAX_CAPTION:
        return _fail("VALIDATION", f"caption exceeds {MAX_CAPTION} characters")

    image_id = str((args or {}).get("image_file_id") or "").strip()
    if not image_id:
        return _fail("VALIDATION", "image_file_id is required for Instagram Feed posts")

    image = (context or {}).get("image") if isinstance(context, dict) else None
    has_image = isinstance(image, dict) and (
        bool(image.get("bytes")) or str(image.get("public_url") or image.get("url") or "").startswith("https://")
    )
    if not has_image:
        return _fail("VALIDATION", "image_file_id set but context.image bytes/public_url missing")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "media_id": "mock-ig-media",
            "content": caption,
            "summary": caption,
        }

    creds = _secret_fields(secret or {})
    if creds.get("ok") is False:
        return creds

    try:
        resolved = _resolve_image_url(creds, image)  # type: ignore[arg-type]
        if resolved.get("ok") is False:
            return resolved
        container = _create_container(creds, caption, str(resolved["image_url"]))
        if container.get("ok") is False:
            return container
        creation_id = str(container["creation_id"])
        ready = _wait_container_ready(creds, creation_id)
        if ready.get("ok") is False:
            return ready
        published = _publish(creds, creation_id)
        if published.get("ok") is False:
            return published
        return {
            "ok": True,
            "stub": False,
            "media_id": published["media_id"],
            "content": caption,
            "summary": caption,
        }
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
