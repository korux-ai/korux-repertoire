"""YouTube Data API v3 resumable video upload. Stdlib HTTPS."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UPLOAD_INIT = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
HTTP_TIMEOUT_S = 120
DEFAULT_MAX_BYTES = 128 * 1024 * 1024
ALLOWED_PRIVACY = frozenset({"private", "unlisted", "public"})
MP4_HINTS = (b"ftyp",)


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _http_mock() -> bool:
    return os.environ.get("KORUX_CAPABILITY_HTTP_MOCK", "").strip() in {"1", "true", "TRUE", "yes"}


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
        raise RuntimeError(f"youtube HTTP error: {exc.reason}") from exc


def _provider_fail(status: int, raw: bytes) -> dict[str, Any]:
    snippet = raw.decode("utf-8", errors="replace")[:400]
    if status in {401, 403}:
        return _fail("CREDENTIAL", f"youtube auth failed ({status})")
    if status >= 500:
        return _fail("PROVIDER", f"youtube server error ({status})")
    return _fail("PROVIDER", f"youtube API {status}: {snippet}")


def _sniff_video(data: bytes, filename: str, content_type: str) -> tuple[str, str] | dict[str, Any]:
    name = (filename or "video.mp4").lower()
    ctype = (content_type or "").lower()
    if ctype.startswith("video/") or name.endswith((".mp4", ".mov", ".webm", ".mpeg", ".mpg")):
        if name.endswith(".mov") or ctype == "video/quicktime":
            return ("video.mov", "video/quicktime")
        if name.endswith(".webm") or ctype == "video/webm":
            return ("video.webm", "video/webm")
        return ("video.mp4", "video/mp4")
    # Heuristic: ISO BMFF / MP4 often has 'ftyp' near start
    if b"ftyp" in data[:64]:
        return ("video.mp4", "video/mp4")
    return _fail("VALIDATION", "video must be mp4/mov/webm (or video/* content_type)")


def _tags(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()][:30]
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()][:30]
    return []


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    args = args or {}
    title = str(args.get("title") or "").strip()
    description = str(args.get("description") or "").strip()
    privacy = str(args.get("privacy_status") or "unlisted").strip().lower() or "unlisted"
    category_id = str(args.get("category_id") or "22").strip() or "22"
    tags = _tags(args.get("tags"))
    video_file_id = str(args.get("video_file_id") or "").strip()

    if not title:
        return _fail("VALIDATION", "title is required")
    if len(title) > 100:
        return _fail("VALIDATION", "title exceeds 100 characters")
    if len(description) > 5000:
        return _fail("VALIDATION", "description exceeds 5000 characters")
    if privacy not in ALLOWED_PRIVACY:
        return _fail("VALIDATION", f"privacy_status must be one of {sorted(ALLOWED_PRIVACY)}")
    if not video_file_id:
        return _fail("VALIDATION", "video_file_id is required")

    video = (context or {}).get("video") if isinstance(context, dict) else None
    has_video = isinstance(video, dict) and isinstance(video.get("bytes"), (bytes, bytearray)) and video.get("bytes")
    if not has_video:
        return _fail("VALIDATION", "video_file_id set but context.video.bytes missing")

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

    sniffed = _sniff_video(
        raw,
        str(video.get("filename") or ""),  # type: ignore[union-attr]
        str(video.get("content_type") or ""),  # type: ignore[union-attr]
    )
    if isinstance(sniffed, dict) and sniffed.get("ok") is False:
        return sniffed
    _filename, content_type = sniffed  # type: ignore[misc]

    if _http_mock():
        return {
            "ok": True,
            "stub": True,
            "video_id": "mock-video",
            "privacy_status": privacy,
            "content": title,
            "summary": title,
        }

    token = str((secret or {}).get("access_token") or (secret or {}).get("token") or "").strip()
    if not token:
        return _fail("CREDENTIAL", "youtube Vault JSON requires access_token")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": category_id,
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    if tags:
        body["snippet"]["tags"] = tags

    try:
        code, resp, hdrs = _request(
            "POST",
            UPLOAD_INIT,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Length": str(len(raw)),
                "X-Upload-Content-Type": content_type,
            },
            body=json.dumps(body).encode("utf-8"),
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if code >= 400:
        return _provider_fail(code, resp)
    upload_url = str(hdrs.get("location") or "").strip()
    if not upload_url:
        return _fail("PROVIDER", "youtube resumable init missing Location")

    try:
        code, resp, _ = _request(
            "PUT",
            upload_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": content_type,
                "Content-Length": str(len(raw)),
            },
            body=raw,
        )
    except RuntimeError as exc:
        return _fail("PROVIDER", str(exc))
    if code >= 400:
        return _provider_fail(code, resp)
    try:
        data = json.loads(resp.decode("utf-8"))
    except json.JSONDecodeError:
        return _fail("PROVIDER", "youtube upload returned non-JSON")
    video_id = str(data.get("id") or "").strip()
    if not video_id:
        return _fail("PROVIDER", "youtube upload missing video id")
    out_privacy = str((data.get("status") or {}).get("privacyStatus") or privacy)
    return {
        "ok": True,
        "stub": False,
        "video_id": video_id,
        "privacy_status": out_privacy,
        "content": title,
        "summary": title,
    }
