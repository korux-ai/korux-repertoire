"""Meitu MTlab sync product cutout. api_key/api_secret query auth, stdlib HTTPS."""

from __future__ import annotations

import base64
import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

DEFAULT_BASE = "https://openapi.mtlab.meitu.com"
CUTOUT_PATH = "/v1/photo_scissors/sod"
HTTP_TIMEOUT_S = 90
DEFAULT_MAX_BYTES = 8 * 1024 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
ALLOWED_ACTIONS = frozenset({"cutout"})


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {"1", "true", "TRUE", "yes"}


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


def _request(method: str, url: str, *, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    req = Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT_S, context=ctx) as resp:
            return int(resp.status), resp.read()
    except HTTPError as exc:
        return int(exc.code), exc.read() if exc.fp else b""
    except URLError as exc:
        raise RuntimeError(f"meitu HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"meitu auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"meitu server error ({status})")
    return _fail("PROVIDER", f"meitu API {status}: {snippet}")


def _detect_type(data: bytes | None, filename: str, content_type: str, url: str) -> str:
    name = (filename or url or "").lower()
    ctype = (content_type or "").lower()
    if data and data.startswith(PNG_MAGIC):
        return "png"
    if data and data.startswith(JPEG_MAGIC):
        return "jpg"
    if "png" in ctype or name.endswith(".png"):
        return "png"
    return "jpg"


def _build_media(args: dict[str, Any], context: dict | None, max_bytes: int) -> dict[str, Any]:
    image_url = str(args.get("image_url") or "").strip()
    image = (context or {}).get("image") if isinstance(context, dict) else None
    public = ""
    if isinstance(image, dict):
        public = str(image.get("public_url") or image.get("url") or "").strip()

    if isinstance(image, dict) and isinstance(image.get("bytes"), (bytes, bytearray)) and image.get("bytes"):
        raw = bytes(image["bytes"])
        if len(raw) > max_bytes:
            return _fail("VALIDATION", f"image exceeds {max_bytes} bytes")
        media_type = _detect_type(
            raw,
            str(image.get("filename") or ""),
            str(image.get("content_type") or ""),
            "",
        )
        return {
            "ok": True,
            "media_info": {
                "media_data": base64.b64encode(raw).decode("ascii"),
                "media_profiles": {"media_data_type": media_type},
                "media_extra": {},
            },
        }

    url = image_url or public
    if url:
        parsed = urlparse(url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            return _fail("VALIDATION", "image_url must be http(s)")
        media_type = _detect_type(None, "", "", url)
        return {
            "ok": True,
            "media_info": {
                "media_data": url,
                "media_profiles": {"media_data_type": "url"},
                "media_extra": {},
            },
            "hint_type": media_type,
        }

    file_id = str(args.get("image_file_id") or "").strip()
    if file_id:
        return _fail("VALIDATION", "image_file_id set but context.image bytes/public_url missing")
    return _fail("VALIDATION", "image_file_id (with context.image) or image_url is required")


def _extract_urls(data: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("media_info_list", "media_data_list", "result"):
        items = data.get(key)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    for field in ("media_data", "media_url", "url", "image_url"):
                        val = str(item.get(field) or "").strip()
                        if val.startswith("http"):
                            urls.append(val)
                elif isinstance(item, str) and item.startswith("http"):
                    urls.append(item)
    for field in ("media_data", "url", "image_url"):
        val = str(data.get(field) or "").strip()
        if val.startswith("http"):
            urls.append(val)
    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    args = args or {}
    secret = secret or {}
    action = str(args.get("action") or "cutout").strip().lower() or "cutout"
    if action not in ALLOWED_ACTIONS:
        return _fail("VALIDATION", f"action must be one of {sorted(ALLOWED_ACTIONS)}")

    max_bytes = DEFAULT_MAX_BYTES
    gov = (context or {}).get("governor") if isinstance(context, dict) else None
    if isinstance(gov, dict) and gov.get("max_image_bytes") is not None:
        try:
            max_bytes = int(gov["max_image_bytes"])
        except (TypeError, ValueError):
            max_bytes = DEFAULT_MAX_BYTES

    media = _build_media(args, context, max_bytes)
    if media.get("ok") is False:
        return media

    try:
        model_type = int(args.get("model_type") if args.get("model_type") is not None else 0)
    except (TypeError, ValueError):
        return _fail("VALIDATION", "model_type must be an integer")
    return_mask = _as_bool(args.get("return_mask"), False)

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "image_urls": ["https://example.com/meitu-cutout.png"],
            "action": action,
            "content": "meitu-cutout",
            "summary": "meitu cutout stub",
        }

    api_key = str(secret.get("api_key") or secret.get("access_key") or "").strip()
    api_secret = str(secret.get("api_secret") or secret.get("secret_key") or "").strip()
    if not api_key or not api_secret:
        return _fail("CREDENTIAL", "meitu Vault requires api_key and api_secret")
    base = str(secret.get("base_url") or DEFAULT_BASE).strip().rstrip("/") or DEFAULT_BASE

    qs = urlencode({"api_key": api_key, "api_secret": api_secret})
    url = f"{base}{CUTOUT_PATH}?{qs}"
    body = {
        "parameter": {
            "nMask": return_mask,
            "model_type": model_type,
            "rsp_media_type": "png",
        },
        "media_info_list": [media["media_info"]],
        "extra": {},
    }
    try:
        code, resp = _request(
            "POST",
            url,
            headers={"Content-Type": "application/json"},
            body=json.dumps(body).encode("utf-8"),
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if code >= 400:
        return _provider_fail(code, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "meitu returned non-JSON")
    if not isinstance(data, dict):
        return _fail("PROVIDER", "meitu unexpected payload")

    # Some responses encode error in ErrorCode / error_code while HTTP 200
    err_code = data.get("ErrorCode", data.get("error_code", data.get("code")))
    if err_code not in (None, 0, "0", 200, "200"):
        msg = str(data.get("ErrorMsg") or data.get("message") or err_code)
        return _fail("PROVIDER", f"meitu error: {msg}")

    urls = _extract_urls(data)
    # Sync APIs sometimes return base64 in media_data — surface as data URI if no http url
    if not urls:
        for item in data.get("media_info_list") or []:
            if not isinstance(item, dict):
                continue
            raw_b64 = str(item.get("media_data") or "").strip()
            if raw_b64 and not raw_b64.startswith("http") and len(raw_b64) > 64:
                urls.append(f"data:image/png;base64,{raw_b64}")
                break
    if not urls:
        return _fail("PROVIDER", "meitu response missing image result")

    return {
        "ok": True,
        "stub": False,
        "image_urls": urls,
        "action": action,
        "content": urls[0],
        "summary": f"meitu {action}",
    }
