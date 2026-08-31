"""TikTok Content Posting API — inbox (default) or direct video post. Stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

API_BASE = "https://open.tiktokapis.com"
INBOX_INIT = f"{API_BASE}/v2/post/publish/inbox/video/init/"
DIRECT_INIT = f"{API_BASE}/v2/post/publish/video/init/"
HTTP_TIMEOUT_S = 120
DEFAULT_MAX_BYTES = 128 * 1024 * 1024
ALLOWED_MODES = frozenset({"inbox", "direct"})


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
        raise RuntimeError(f"tiktok HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"tiktok auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"tiktok server error ({status})")
    return _fail("PROVIDER", f"tiktok API {status}: {snippet}")


def _content_type(filename: str, declared: str) -> str:
    name = (filename or "").lower()
    ctype = (declared or "").lower()
    if ctype in {"video/mp4", "video/quicktime", "video/webm"}:
        return ctype
    if name.endswith(".mov"):
        return "video/quicktime"
    if name.endswith(".webm"):
        return "video/webm"
    return "video/mp4"


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    args = args or {}
    mode = str(args.get("mode") or "inbox").strip().lower() or "inbox"
    title = str(args.get("title") or "").strip()
    video_url = str(args.get("video_url") or "").strip()
    video_file_id = str(args.get("video_file_id") or "").strip()

    if mode not in ALLOWED_MODES:
        return _fail("VALIDATION", f"mode must be one of {sorted(ALLOWED_MODES)}")
    if mode == "direct" and not title:
        return _fail("VALIDATION", "title is required for mode=direct")
    if len(title) > 2200:
        return _fail("VALIDATION", "title exceeds 2200 characters")

    video = (context or {}).get("video") if isinstance(context, dict) else None
    has_bytes = (
        isinstance(video, dict)
        and isinstance(video.get("bytes"), (bytes, bytearray))
        and bool(video.get("bytes"))
    )
    if video_file_id and not has_bytes and not video_url:
        return _fail("VALIDATION", "video_file_id set but context.video.bytes missing")
    if not has_bytes and not video_url:
        return _fail("VALIDATION", "video_file_id (with bytes) or video_url is required")

    if video_url:
        parsed = urlparse(video_url)
        if parsed.scheme != "https" or not parsed.netloc:
            return _fail("VALIDATION", "video_url must be https")

    raw: bytes | None = None
    if has_bytes:
        raw = bytes(video["bytes"])  # type: ignore[index]
        max_bytes = DEFAULT_MAX_BYTES
        owner = (context or {}).get("governor") if isinstance(context, dict) else None
        if isinstance(owner, dict) and owner.get("max_video_bytes"):
            try:
                max_bytes = int(owner["max_video_bytes"])
            except (TypeError, ValueError):
                max_bytes = DEFAULT_MAX_BYTES
        if len(raw) > max_bytes:
            return _fail("VALIDATION", f"video exceeds {max_bytes} bytes")

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "publish_id": "mock-publish",
            "mode": mode,
            "content": title or f"tiktok-{mode}",
            "summary": title or f"tiktok-{mode}",
        }

    token = str((secret or {}).get("access_token") or (secret or {}).get("token") or "").strip()
    if not token:
        return _fail("CREDENTIAL", "tiktok Vault JSON requires access_token")

    if video_url and not has_bytes:
        source_info: dict[str, Any] = {"source": "PULL_FROM_URL", "video_url": video_url}
    else:
        assert raw is not None
        source_info = {
            "source": "FILE_UPLOAD",
            "video_size": len(raw),
            "chunk_size": len(raw),
            "total_chunk_count": 1,
        }

    payload: dict[str, Any] = {"source_info": source_info}
    init_url = INBOX_INIT
    if mode == "direct":
        init_url = DIRECT_INIT
        payload["post_info"] = {
            "title": title,
            "privacy_level": "SELF_ONLY",
            "disable_comment": _as_bool(args.get("disable_comment"), False),
            "disable_duet": _as_bool(args.get("disable_duet"), False),
            "disable_stitch": _as_bool(args.get("disable_stitch"), False),
        }

    try:
        code, resp = _request(
            "POST",
            init_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            body=json.dumps(payload).encode("utf-8"),
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if code >= 400:
        return _provider_fail(code, resp)
    try:
        envelope = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "tiktok init returned non-JSON")
    data = envelope.get("data") if isinstance(envelope, dict) else None
    if not isinstance(data, dict):
        err = envelope.get("error") if isinstance(envelope, dict) else None
        return _fail("PROVIDER", f"tiktok init unexpected payload: {err or envelope}")
    publish_id = str(data.get("publish_id") or "").strip()
    upload_url = str(data.get("upload_url") or "").strip()
    if not publish_id:
        return _fail("PROVIDER", "tiktok init missing publish_id")

    if source_info["source"] == "FILE_UPLOAD":
        if not upload_url:
            return _fail("PROVIDER", "tiktok init missing upload_url")
        assert raw is not None
        ctype = _content_type(
            str(video.get("filename") or "") if isinstance(video, dict) else "",
            str(video.get("content_type") or "") if isinstance(video, dict) else "",
        )
        try:
            put_code, put_resp = _request(
                "PUT",
                upload_url,
                headers={
                    "Content-Type": ctype,
                    "Content-Length": str(len(raw)),
                    "Content-Range": f"bytes 0-{len(raw) - 1}/{len(raw)}",
                },
                body=raw,
            )
        except RuntimeError as exc:
            return _fail("PROVIDER", str(exc))
        if put_code >= 400:
            return _provider_fail(put_code, put_resp)

    label = title or publish_id
    return {
        "ok": True,
        "stub": False,
        "publish_id": publish_id,
        "mode": mode,
        "content": label,
        "summary": f"tiktok {mode}: {label}",
    }
