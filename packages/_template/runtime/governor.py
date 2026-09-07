"""Optional Track B governor — pure stdlib, no ``import korux``.

Korux platform calls ``evaluate_governor`` when this file exists; otherwise it
evaluates sibling ``governor.json`` declaratively.

Return a plain dict:
  action: pass | reject | intercept
  rule_id, message, code, policy_id, editable_fields (optional)
"""

from __future__ import annotations

from typing import Any


def pack() -> dict[str, Any]:
    """Optional UI rule summaries (Governance page)."""
    return {
        "spec_version": "korux_governor_v1",
        "capability_id": "example-connector",
        "capability_version": "0.1.0",
        "defaults": {
            "intercept_on_invoke": True,
            "editable_fields": ["body"],
        },
        "rules": [
            {
                "id": "block_empty_body",
                "action": "reject",
                "message": "Body is empty; use upstream step output.",
            },
            {
                "id": "require_human_by_default",
                "action": "intercept",
                "gate": "require_human",
                "message": "Human confirmation required before external write.",
            },
        ],
    }


def evaluate_governor(
    *,
    ctx: dict[str, Any],
    args: dict[str, Any],
    context: dict[str, Any],
    owner_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = str(args.get("body") or "")
    editable = ["body"]
    version = str(ctx.get("capability_version") or "0.1.0")
    cid = str(ctx.get("capability_id") or "example-connector")

    if not body.strip():
        return {
            "action": "reject",
            "capability_id": cid,
            "capability_version": version,
            "rule_id": "block_empty_body",
            "message": "Body is empty; use upstream step output.",
            "code": "VALIDATION",
            "editable_fields": editable,
        }

    banned = [
        str(x).strip().lower()
        for x in ((owner_config or {}).get("blocked_keywords") or [])
        if str(x or "").strip()
    ]
    hay = body.lower()
    if any(w and w in hay for w in banned):
        return {
            "action": "reject",
            "capability_id": cid,
            "capability_version": version,
            "rule_id": "block_banned_words",
            "message": "Body matches an owner blocked keyword.",
            "code": "GOVERNOR_POLICY",
            "editable_fields": editable,
        }

    manifest = ctx.get("manifest") or {}
    if manifest.get("writes_external"):
        return {
            "action": "intercept",
            "capability_id": cid,
            "capability_version": version,
            "rule_id": "require_human_by_default",
            "message": "Human confirmation required before external write.",
            "code": "VALIDATION",
            "editable_fields": editable,
        }

    return {
        "action": "pass",
        "capability_id": cid,
        "capability_version": version,
        "editable_fields": editable,
    }
