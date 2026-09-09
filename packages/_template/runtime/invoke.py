"""Template connector invoke — stdlib only; no ``import korux``.

Failure shape (v2.2.37 / korux_failure_class_v1):
  {"ok": false, "error": {"class": "<closed>", "code": "...", "message": "..."}}

Closed ``class`` values: auth | empty | unavailable | validation | denied | provider
"""

from __future__ import annotations

from typing import Any

# Closed failure classes — must stay aligned with Korux failure-policy.md
FAILURE_CLASSES = frozenset(
    {"auth", "empty", "unavailable", "validation", "denied", "provider"}
)

_CODE_TO_CLASS: dict[str, str] = {
    "CREDENTIAL": "auth",
    "AUTH": "auth",
    "SECRET_MISSING": "auth",
    "UNAUTHORIZED": "auth",
    "VALIDATION": "validation",
    "ACCESS_DENIED": "denied",
    "DENIED": "denied",
    "EMPTY": "empty",
    "UNAVAILABLE": "unavailable",
    "TIMEOUT": "unavailable",
    "RATE_LIMITED": "unavailable",
    "CONNECTION": "unavailable",
    "PROVIDER": "provider",
}


def _fail(
    code: str,
    message: str,
    *,
    failure_class: str | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    """Build a contract-shaped failure. Always includes ``error.class``."""
    cls = (failure_class or "").strip().lower()
    if cls not in FAILURE_CLASSES:
        cls = _CODE_TO_CLASS.get(str(code or "").strip().upper(), "provider")
    err: dict[str, Any] = {
        "class": cls,
        "code": code,
        "message": message,
    }
    if retryable:
        err["retryable"] = True
    return {"ok": False, "error": err}


async def invoke(
    args: dict[str, Any],
    secret: dict[str, Any] | None = None,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Example invoke — replace with real provider calls."""
    _ = secret, ctx
    payload = args if isinstance(args, dict) else {}
    body = str(payload.get("body") or "").strip()
    if not body:
        return _fail(
            "VALIDATION",
            "body is required",
            failure_class="validation",
        )
    # Example empty success (no business rows) — Runner may treat via treat_empty_as.
    if payload.get("force_empty"):
        return {
            "ok": True,
            "empty": True,
            "content": "",
            "summary": "No results",
        }
    # Example soft degrade — still ok; does NOT trigger Spec failure_policy.
    if payload.get("force_degraded"):
        return {
            "ok": True,
            "degraded": True,
            "content": "Partial stub result",
            "summary": "degraded",
        }
    # Example hard unavailable (e.g. HTTP 503 / timeout).
    if payload.get("force_unavailable"):
        return _fail(
            "UNAVAILABLE",
            "Upstream provider unavailable",
            failure_class="unavailable",
            retryable=True,
        )
    return {
        "ok": True,
        "content": body,
        "summary": body[:120],
        "stub": True,
    }
