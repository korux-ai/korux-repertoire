"""Alibaba DashScope Wanxiang (万相) image edit. Stdlib HTTPS."""

from __future__ import annotations

import base64
import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_BASE = "https://dashscope.aliyuncs.com/api/v1"
DEFAULT_MODEL = "wan2.6-image"
HTTP_TIMEOUT_S = 120
MAX_PROMPT = 2000
MAX_IMAGE_BYTES = 10 * 1024 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


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
        raise RuntimeError(f"wanx HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"dashscope auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"dashscope server error ({status})")
    return _fail("PROVIDER", f"dashscope API {status}: {snippet}")


def _mime_from_bytes(data: bytes, filename: str, content_type: str) -> str:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if data.startswith(JPEG_MAGIC) or ctype in {"image/jpeg", "image/jpg"} or name.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if data.startswith(PNG_MAGIC) or ctype == "image/png" or name.endswith(".png"):
        return "image/png"
    if ctype.startswith("image/"):
        return ctype.split(";")[0].strip()
    return "image/jpeg"


def _resolve_image_ref(args: dict[str, Any], context: dict | None) -> dict[str, Any]:
    image_url = str(args.get("image_url") or "").strip()
    image = (context or {}).get("image") if isinstance(context, dict) else None
    public = ""
    if isinstance(image, dict):
        public = str(image.get("public_url") or image.get("url") or "").strip()
    if image_url:
        parsed = urlparse(image_url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            return _fail("VALIDATION", "image_url must be http(s)")
        return {"ok": True, "image": image_url}
    if public.startswith("https://") or public.startswith("http://"):
        return {"ok": True, "image": public}
    if isinstance(image, dict) and isinstance(image.get("bytes"), (bytes, bytearray)) and image.get("bytes"):
        raw = bytes(image["bytes"])
        if len(raw) > MAX_IMAGE_BYTES:
            return _fail("VALIDATION", f"image exceeds {MAX_IMAGE_BYTES} bytes")
        mime = _mime_from_bytes(
            raw,
            str(image.get("filename") or ""),
            str(image.get("content_type") or ""),
        )
        b64 = base64.b64encode(raw).decode("ascii")
        return {"ok": True, "image": f"data:{mime};base64,{b64}"}
    file_id = str(args.get("image_file_id") or "").strip()
    if file_id:
        return _fail("VALIDATION", "image_file_id set but context.image bytes/public_url missing")
    return _fail("VALIDATION", "image_file_id (with context.image) or image_url is required")


def _extract_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
    choices = output.get("choices") if isinstance(output.get("choices"), list) else []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("image"):
                    urls.append(str(part["image"]).strip())
                elif isinstance(part, dict) and part.get("image_url"):
                    urls.append(str(part["image_url"]).strip())
        elif isinstance(content, str) and content.startswith("http"):
            urls.append(content.strip())
    # Some responses put results under output.results
    results = output.get("results") if isinstance(output.get("results"), list) else []
    for item in results:
        if isinstance(item, dict) and item.get("url"):
            urls.append(str(item["url"]).strip())
    return [u for u in urls if u]


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    args = args or {}
    secret = secret or {}
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        return _fail("VALIDATION", "prompt is required")
    if len(prompt) > MAX_PROMPT:
        return _fail("VALIDATION", f"prompt exceeds {MAX_PROMPT} characters")

    size = str(args.get("size") or "1K").strip() or "1K"
    if size not in {"1K", "2K"}:
        return _fail("VALIDATION", "size must be 1K or 2K")
    try:
        n = int(args.get("n") if args.get("n") is not None else 1)
    except (TypeError, ValueError):
        return _fail("VALIDATION", "n must be an integer")
    if n < 1 or n > 4:
        return _fail("VALIDATION", "n must be between 1 and 4")

    resolved = _resolve_image_ref(args, context)
    if resolved.get("ok") is False:
        return resolved

    model = str(args.get("model") or secret.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    negative = str(args.get("negative_prompt") or "").strip()
    watermark = _as_bool(args.get("watermark"), False)

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "image_urls": ["https://example.com/wanx-edit.png"],
            "model": model,
            "content": prompt,
            "summary": f"wanx-edit stub ({model})",
        }

    api_key = str(secret.get("api_key") or secret.get("access_token") or secret.get("token") or "").strip()
    if not api_key:
        return _fail("CREDENTIAL", "alibaba/wanx-edit Vault requires api_key")
    base = str(secret.get("base_url") or DEFAULT_BASE).strip().rstrip("/") or DEFAULT_BASE

    content: list[dict[str, str]] = [
        {"image": str(resolved["image"])},
        {"text": prompt},
    ]
    parameters: dict[str, Any] = {
        "prompt_extend": True,
        "watermark": watermark,
        "n": n,
        "enable_interleave": False,
        "size": size,
    }
    if negative:
        parameters["negative_prompt"] = negative

    payload = {
        "model": model,
        "input": {"messages": [{"role": "user", "content": content}]},
        "parameters": parameters,
    }
    url = f"{base}/services/aigc/multimodal-generation/generation"
    try:
        code, resp = _request(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            body=json.dumps(payload).encode("utf-8"),
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if code >= 400:
        return _provider_fail(code, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "dashscope returned non-JSON")
    if not isinstance(data, dict):
        return _fail("PROVIDER", "dashscope unexpected payload")
    # DashScope sometimes returns code/message on HTTP 200
    if str(data.get("code") or "") and str(data.get("code")) not in {"", "Success", "null"}:
        # Success responses often omit code or use empty
        msg = str(data.get("message") or data.get("code"))
        if data.get("output") is None and data.get("code"):
            return _fail("PROVIDER", f"dashscope error: {msg}")

    urls = _extract_urls(data)
    if not urls:
        return _fail("PROVIDER", "dashscope response missing image urls")
    return {
        "ok": True,
        "stub": False,
        "image_urls": urls,
        "model": model,
        "content": urls[0],
        "summary": f"wanx-edit {model}: {prompt[:80]}",
    }
