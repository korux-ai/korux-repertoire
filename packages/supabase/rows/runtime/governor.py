"""Track B governor for supabase/rows — allowlist tables; human gate on writes.

No ``import korux``. When present, Korux prefers this over governor.json.
"""

from __future__ import annotations

import re
from typing import Any

_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_WRITE = frozenset({"insert", "update", "upsert"})
_READ = frozenset({"select"})


def pack() -> dict[str, Any]:
    return {
        "spec_version": "korux_governor_v1",
        "capability_id": "supabase/rows",
        "capability_version": "1.0.0",
        "defaults": {
            "intercept_on_invoke": True,
            "editable_fields": [
                "action",
                "table",
                "filters",
                "row",
                "columns",
                "limit",
                "offset",
                "on_conflict",
            ],
        },
        "rules": [
            {
                "id": "reject_empty_table",
                "action": "reject",
                "message": {
                    "en": "table is empty",
                    "zh_CN": "table 为空",
                    "zh_HK": "table 為空",
                },
            },
            {
                "id": "reject_table_not_allowlisted",
                "action": "reject",
                "message": {
                    "en": "table not in Owner allowed_tables",
                    "zh_CN": "表名不在 Owner allowed_tables",
                    "zh_HK": "表名不在 Owner allowed_tables",
                },
            },
            {
                "id": "require_human_on_write",
                "action": "intercept",
                "gate": "require_human",
                "message": {
                    "en": "Human confirmation required before Supabase write",
                    "zh_CN": "Supabase 写入前须人工确认",
                    "zh_HK": "Supabase 寫入前須人工確認",
                },
            },
        ],
    }


def _msg(en: str, zh_cn: str, zh_hk: str) -> dict[str, str]:
    return {"en": en, "zh_CN": zh_cn, "zh_HK": zh_hk}


def evaluate_governor(
    *,
    ctx: dict[str, Any],
    args: dict[str, Any],
    context: dict[str, Any],
    owner_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = context
    version = str(ctx.get("capability_version") or "1.0.0")
    cid = str(ctx.get("capability_id") or "supabase/rows")
    editable = [
        "action",
        "table",
        "filters",
        "row",
        "columns",
        "limit",
        "offset",
        "on_conflict",
    ]
    owner = owner_config if isinstance(owner_config, dict) else {}

    action = str(args.get("action") or "").strip().lower()
    table = str(args.get("table") or "").strip()

    if not table:
        return {
            "action": "reject",
            "capability_id": cid,
            "capability_version": version,
            "rule_id": "reject_empty_table",
            "message": _msg(
                "table is empty; provide an Owner-allowlisted table name.",
                "table 为空；请提供 Owner 白名单中的表名。",
                "table 為空；請提供 Owner 白名單中的表名。",
            ),
            "code": "VALIDATION",
            "editable_fields": editable,
        }

    if not _TABLE_RE.match(table):
        return {
            "action": "reject",
            "capability_id": cid,
            "capability_version": version,
            "rule_id": "reject_invalid_table_name",
            "message": _msg(
                "table must be a simple identifier (letters, digits, underscore).",
                "table 必须是简单标识符（字母、数字、下划线）。",
                "table 必須是簡單標識符（字母、數字、底線）。",
            ),
            "code": "VALIDATION",
            "editable_fields": editable,
        }

    allowed = [
        str(x).strip()
        for x in (owner.get("allowed_tables") or [])
        if str(x or "").strip()
    ]
    if not allowed:
        return {
            "action": "reject",
            "capability_id": cid,
            "capability_version": version,
            "rule_id": "reject_empty_allowlist",
            "message": _msg(
                "Owner allowed_tables is empty; configure Governance before use.",
                "Owner allowed_tables 为空；请先在 Governance 配置表白名单。",
                "Owner allowed_tables 為空；請先在 Governance 配置表白名單。",
            ),
            "code": "GOVERNOR_POLICY",
            "editable_fields": editable,
        }

    allowed_l = {a.lower() for a in allowed}
    if table.lower() not in allowed_l:
        return {
            "action": "reject",
            "capability_id": cid,
            "capability_version": version,
            "rule_id": "reject_table_not_allowlisted",
            "message": _msg(
                f"table '{table}' is not in Owner allowed_tables.",
                f"表 '{table}' 不在 Owner allowed_tables 中。",
                f"表 '{table}' 不在 Owner allowed_tables 中。",
            ),
            "code": "GOVERNOR_POLICY",
            "editable_fields": editable,
        }

    if action not in _READ | _WRITE:
        return {
            "action": "reject",
            "capability_id": cid,
            "capability_version": version,
            "rule_id": "reject_invalid_action",
            "message": _msg(
                "action must be select, insert, update, or upsert.",
                "action 必须是 select、insert、update 或 upsert。",
                "action 必須是 select、insert、update 或 upsert。",
            ),
            "code": "VALIDATION",
            "editable_fields": editable,
        }

    require_read_human = bool(owner.get("require_human_on_read"))
    if action in _WRITE or (action in _READ and require_read_human):
        return {
            "action": "intercept",
            "capability_id": cid,
            "capability_version": version,
            "rule_id": "require_human_on_write"
            if action in _WRITE
            else "require_human_on_read",
            "gate": "require_human",
            "message": _msg(
                "Human confirmation required before Supabase row access.",
                "访问 Supabase 行数据前须人工确认。",
                "存取 Supabase 列資料前須人工確認。",
            ),
            "code": "VALIDATION",
            "editable_fields": editable,
        }

    return {
        "action": "pass",
        "capability_id": cid,
        "capability_version": version,
        "editable_fields": editable,
    }
