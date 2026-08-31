"""IMAP poll / mark-seen — stdlib only; no Korux imports."""

from __future__ import annotations

import email
import imaplib
import re
from copy import deepcopy
from email.header import decode_header
from email.utils import parseaddr
from typing import Any

DEFAULT_MAX_UNSEEN_PER_POLL = 50
_TEST_INBOX: list[dict[str, Any]] = []
_TEST_NEXT_UID = 1
_TAG_RE = re.compile(r"<[^>]+>")
_IMAP_SAFE_RE = re.compile(r"^[a-zA-Z0-9._%+\-@]+$")


def clear_test_inbox() -> None:
    _TEST_INBOX.clear()
    global _TEST_NEXT_UID
    _TEST_NEXT_UID = 1


def inject_test_inbox_message(
    *,
    message_id: str,
    body: str,
    from_addr: str = "sender@example.com",
    subject: str = "",
) -> dict[str, Any]:
    global _TEST_NEXT_UID
    uid = str(_TEST_NEXT_UID)
    _TEST_NEXT_UID += 1
    msg = {
        "message_id": message_id,
        "body": body,
        "from": from_addr,
        "subject": subject or "",
        "imap_uid": uid,
        "imap_seen": False,
    }
    _TEST_INBOX.append(dict(msg))
    return dict(msg)


def _fail(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _parse_mark_read_on_process(data: dict[str, Any]) -> bool:
    raw = data.get("mark_read_on_process")
    if raw is None:
        return True
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in {"false", "0", "no"}


def parse_imap_secret(secret: dict[str, Any]) -> dict[str, Any] | dict[str, Any]:
    if not isinstance(secret, dict):
        return _fail("CREDENTIAL", "Vault secret must be a JSON object")
    host = str(secret.get("host") or "").strip()
    if not host:
        return _fail("CREDENTIAL", "Vault imap JSON missing host")
    username = str(secret.get("username") or secret.get("user") or "").strip()
    password = str(secret.get("password") or "")
    if not username:
        return _fail("CREDENTIAL", "Vault imap JSON missing username")
    use_ssl = secret.get("use_ssl")
    if use_ssl is None:
        use_ssl = int(secret.get("port") or 993) == 993
    elif isinstance(use_ssl, str):
        use_ssl = use_ssl.strip().lower() not in {"false", "0", "no"}
    max_unseen_raw = secret.get("max_unseen")
    max_unseen = DEFAULT_MAX_UNSEEN_PER_POLL
    if max_unseen_raw is not None and str(max_unseen_raw).strip() != "":
        max_unseen = max(1, int(max_unseen_raw))
    return {
        "host": host,
        "port": int(secret.get("port") or (993 if use_ssl else 143)),
        "username": username,
        "password": password,
        "folder": str(secret.get("folder") or "INBOX"),
        "use_ssl": bool(use_ssl),
        "max_unseen": max_unseen,
        "mark_read_on_process": _parse_mark_read_on_process(secret),
    }


def normalize_sender_filter(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    if raw.startswith("*@"):
        domain = raw[2:].strip(".")
        return f"*@{domain}" if domain else ""
    if raw.startswith("@") and raw.count("@") == 1:
        domain = raw[1:].strip(".")
        return f"*@{domain}" if domain else ""
    if "@" not in raw and "." in raw:
        return f"*@{raw.strip('.')}"
    return raw


def sender_matches_filter(from_addr: str, want_filter: str) -> bool:
    want = normalize_sender_filter(want_filter)
    if not want:
        return True
    got = (from_addr or "").strip().lower()
    if not got:
        return False
    if want.startswith("*@"):
        domain = want[2:]
        return got.endswith(f"@{domain}") or got.split("@")[-1] == domain
    return got == want


def imap_from_search_term(want_filter: str | None) -> str | None:
    want = normalize_sender_filter(want_filter or "")
    if not want:
        return None
    term = want[2:].strip() if want.startswith("*@") else want
    if not term or not _IMAP_SAFE_RE.match(term):
        return None
    return term


def _cap_unseen_uids(raw_nums: list[bytes], *, max_unseen: int) -> list[bytes]:
    if max_unseen <= 0 or len(raw_nums) <= max_unseen:
        return list(raw_nums)
    return list(raw_nums[-max_unseen:])


def _decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for frag, charset in decode_header(value):
        if isinstance(frag, bytes):
            parts.append(frag.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(str(frag))
    return "".join(parts).strip()


def _strip_html(text: str) -> str:
    cleaned = _TAG_RE.sub(" ", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        plain: str | None = None
        html: str | None = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                continue
            ctype = (part.get_content_type() or "").lower()
            try:
                payload = part.get_payload(decode=True)
            except Exception:
                continue
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace").replace("\x00", "")
            if ctype == "text/plain" and plain is None:
                plain = text.strip()
            elif ctype == "text/html" and html is None:
                html = _strip_html(text)
        if plain:
            return plain[:20000]
        if html:
            return html[:20000]
        return ""
    try:
        payload = msg.get_payload(decode=True)
    except Exception:
        return ""
    if not payload:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    text = payload.decode(charset, errors="replace").replace("\x00", "")
    if (msg.get_content_type() or "").lower() == "text/html":
        return _strip_html(text)[:20000]
    return text.strip()[:20000]


def _message_from_imap_bytes(raw: bytes, *, fallback_id: str) -> dict[str, Any]:
    msg = email.message_from_bytes(raw)
    message_id = (_decode_mime_header(msg.get("Message-ID")) or fallback_id).strip()
    from_hdr = _decode_mime_header(msg.get("From"))
    from_addr = parseaddr(from_hdr)[1] or from_hdr
    subject = _decode_mime_header(msg.get("Subject"))
    body = _extract_body(msg)
    if subject and body:
        body = f"Subject: {subject}\n\n{body}"
    elif subject and not body:
        body = f"Subject: {subject}"
    return {
        "message_id": message_id,
        "from": from_addr,
        "subject": subject,
        "body": body or subject or "(empty message)",
    }


def _connect_imap(cfg: dict[str, Any]) -> imaplib.IMAP4:
    host = str(cfg.get("host") or "").strip().lower()
    port = int(cfg.get("port") or 993)
    use_ssl = bool(cfg.get("use_ssl", port == 993))
    username = str(cfg.get("username") or "")
    password = str(cfg.get("password") or "")
    if use_ssl:
        conn = imaplib.IMAP4_SSL(host, port, timeout=30)
    else:
        conn = imaplib.IMAP4(host, port, timeout=30)
    conn.login(username, password)
    return conn


def mark_messages_seen(cfg: dict[str, Any], uids: list[str] | set[str]) -> int:
    if not cfg.get("mark_read_on_process", True):
        return 0
    uid_list = [str(u).strip() for u in uids if str(u).strip()]
    if not uid_list:
        return 0
    host = str(cfg.get("host") or "").strip().lower()
    if host == "test":
        marked = 0
        want = set(uid_list)
        for msg in _TEST_INBOX:
            uid = str(msg.get("imap_uid") or "")
            if uid in want and not msg.get("imap_seen"):
                msg["imap_seen"] = True
                marked += 1
        return marked

    folder = str(cfg.get("folder") or "INBOX")
    conn: imaplib.IMAP4 | None = None
    marked = 0
    try:
        conn = _connect_imap(cfg)
        status, _ = conn.select(folder, readonly=False)
        if status != "OK":
            raise RuntimeError(f"IMAP select folder failed: {folder}")
        for uid in uid_list:
            status, _ = conn.uid("STORE", uid, "+FLAGS", "(\\Seen)")
            if status == "OK":
                marked += 1
        return marked
    finally:
        if conn is not None:
            try:
                conn.logout()
            except Exception:
                pass


def fetch_unseen_messages(
    cfg: dict[str, Any],
    *,
    seen_ids: set[str] | None = None,
    from_filter: str | None = None,
) -> list[dict[str, Any]]:
    seen = set(seen_ids or [])
    max_unseen = int(cfg.get("max_unseen") or DEFAULT_MAX_UNSEEN_PER_POLL)
    host = str(cfg.get("host") or "").strip().lower()
    imap_from = imap_from_search_term(from_filter)

    if host == "test":
        pending = [
            deepcopy(m)
            for m in _TEST_INBOX
            if not m.get("imap_seen")
            and str(m.get("message_id") or "")
            and str(m["message_id"]) not in seen
            and sender_matches_filter(str(m.get("from") or ""), from_filter or "")
        ]
        if len(pending) > max_unseen:
            pending = pending[-max_unseen:]
        return pending

    folder = str(cfg.get("folder") or "INBOX")
    conn: imaplib.IMAP4 | None = None
    try:
        conn = _connect_imap(cfg)
        status, _ = conn.select(folder, readonly=True)
        if status != "OK":
            raise RuntimeError(f"IMAP select folder failed: {folder}")
        if imap_from:
            status, data = conn.uid("SEARCH", None, "UNSEEN", "FROM", imap_from)
        else:
            status, data = conn.uid("SEARCH", None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return []
        nums = _cap_unseen_uids(data[0].split(), max_unseen=max_unseen)
        out: list[dict[str, Any]] = []
        for num in nums:
            uid_s = num.decode() if isinstance(num, bytes) else str(num)
            status, msg_data = conn.uid("FETCH", uid_s, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            part = msg_data[0]
            raw = part[1] if isinstance(part, tuple) and len(part) > 1 else None
            if not isinstance(raw, (bytes, bytearray)):
                continue
            parsed = _message_from_imap_bytes(bytes(raw), fallback_id=f"imap-uid:{uid_s}")
            parsed["imap_uid"] = uid_s
            mid = str(parsed.get("message_id") or "")
            if mid and mid in seen:
                continue
            if from_filter and not sender_matches_filter(
                str(parsed.get("from") or ""), from_filter
            ):
                continue
            out.append(parsed)
        return out
    finally:
        if conn is not None:
            try:
                conn.logout()
            except Exception:
                pass


async def invoke(args: dict, secret: dict, context: dict) -> dict:
    _ = context
    cfg = parse_imap_secret(secret or {})
    if cfg.get("ok") is False:
        return cfg

    action = str((args or {}).get("action") or "poll").strip().lower()
    if action == "mark_seen":
        uids = (args or {}).get("uids") or (args or {}).get("imap_uids") or []
        if not isinstance(uids, list):
            uids = [uids]
        try:
            marked = mark_messages_seen(cfg, [str(u) for u in uids])
        except Exception as exc:
            return _fail("PROVIDER", f"IMAP mark seen failed: {exc}")
        return {"ok": True, "marked": marked}

    from_filter = str((args or {}).get("from_filter") or "").strip() or None
    seen_raw = (args or {}).get("seen_ids") or []
    seen: set[str] = set()
    if isinstance(seen_raw, list):
        seen = {str(x).strip() for x in seen_raw if str(x).strip()}

    try:
        messages = fetch_unseen_messages(cfg, seen_ids=seen, from_filter=from_filter)
    except Exception as exc:
        return _fail("PROVIDER", f"IMAP poll failed: {exc}")

    subject_contains = str((args or {}).get("subject_contains") or "").strip().lower()
    if subject_contains:
        messages = [
            m
            for m in messages
            if subject_contains in str(m.get("subject") or "").lower()
            or subject_contains in str(m.get("body") or "").lower()
        ]

    return {
        "ok": True,
        "messages": messages,
        "count": len(messages),
        "content": messages[0].get("body") if messages else "",
        "summary": messages[0].get("body") if messages else "",
    }
