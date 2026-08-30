"""X (Twitter) text / single-image post. Stdlib HTTPS only."""

from __future__ import annotations

import json
import os
import ssl
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .oauth1 import oauth_authorization

TWEETS_URL = "https://api.twitter.com/2/tweets"
MEDIA_URL = "https://upload.twitter.com/1.1/media/upload.json"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
HTTP_TIMEOUT_S = 45


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {"1", "true", "TRUE", "yes"}


def _secret_fields(secret: dict[str, Any]) -> dict[str, str] | dict[str, Any]:
    api_key = str(secret.get("api_key") or "").strip()
    api_secret = str(secret.get("api_secret") or "").strip()
    access_token = str(secret.get("access_token") or "").strip()
    access_token_secret = str(secret.get("access_token_secret") or "").strip()
    if not (api_key and api_secret and access_token and access_token_secret):
        return _fail("CREDENTIAL", "twitter Vault JSON requires api_key, api_secret, access_token, access_token_secret")
    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "access_token": access_token,
        "access_token_secret": access_token_secret,
    }


def _auth_header(method: str, url: str, creds: dict[str, str]) -> str:
    return oauth_authorization(
        method,
        url,
        api_key=creds["api_key"],
        api_secret=creds["api_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )


def _sniff_image(data: bytes, filename: str, content_type: str) -> tuple[str, str] | dict[str, Any]:
    if len(data) > MAX_IMAGE_BYTES:
        return _fail("VALIDATION", "image exceeds 5MB Twitter limit")
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
        raise RuntimeError(f"twitter HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:300]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"twitter auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"twitter server error ({status})")
    return _fail("PROVIDER", f"twitter API {status}: {snippet}")


def _multipart(field: str, filename: str, data: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = f"----KoruxTwitter{uuid.uuid4().hex}"
    crlf = b"\r\n"
    chunks = [
        f"--{boundary}".encode(),
        crlf,
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"'.encode(),
        crlf,
        f"Content-Type: {content_type}".encode(),
        crlf,
        crlf,
        data,
        crlf,
        f"--{boundary}--".encode(),
        crlf,
    ]
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _upload_media(creds: dict[str, str], image: dict[str, Any]) -> dict[str, Any]:
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
    body, ctype = _multipart("media", filename, bytes(raw), content_type)
    headers = {
        "Authorization": _auth_header("POST", MEDIA_URL, creds),
        "Content-Type": ctype,
    }
    status, resp = _request("POST", MEDIA_URL, headers=headers, body=body)
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        payload = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "twitter media upload returned non-JSON")
    media_id = str(payload.get("media_id_string") or payload.get("media_id") or "").strip()
    if not media_id:
        return _fail("PROVIDER", "twitter media upload missing media_id")
    return {"ok": True, "media_id": media_id}


def _post_tweet(creds: dict[str, str], text: str, media_id: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": text}
    if media_id:
        payload["media"] = {"media_ids": [media_id]}
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": _auth_header("POST", TWEETS_URL, creds),
        "Content-Type": "application/json",
    }
    status, resp = _request("POST", TWEETS_URL, headers=headers, body=body)
    if status >= 400:
        return _provider_fail(status, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "twitter tweets API returned non-JSON")
    tweet_id = str((data.get("data") or {}).get("id") or "").strip()
    if not tweet_id:
        return _fail("PROVIDER", "twitter tweets API missing id")
    return {
        "ok": True,
        "stub": False,
        "tweet_id": tweet_id,
        "content": text,
        "summary": text,
    }


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    text = str((args or {}).get("content") or "").strip()
    if not text:
        return _fail("VALIDATION", "content is required")
    if len(text) > 280:
        return _fail("VALIDATION", "content exceeds 280 characters")

    image_id = str((args or {}).get("image_file_id") or "").strip()
    image = (context or {}).get("image") if isinstance(context, dict) else None
    has_image = isinstance(image, dict) and bool(image.get("bytes"))
    if image_id and not has_image:
        return _fail("VALIDATION", "image_file_id set but context.image bytes missing")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "tweet_id": "mock-tweet",
            "content": text,
            "summary": text,
        }

    creds = _secret_fields(secret or {})
    if creds.get("ok") is False:
        return creds

    media_id = None
    if has_image:
        uploaded = _upload_media(creds, image)  # type: ignore[arg-type]
        if uploaded.get("ok") is not True:
            return uploaded
        media_id = str(uploaded.get("media_id") or "")

    try:
        return _post_tweet(creds, text, media_id)  # type: ignore[arg-type]
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
