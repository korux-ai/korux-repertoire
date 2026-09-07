#!/usr/bin/env python3
"""Migrate repertoire packages onto dual-track capability governor contract.

- Ensure governor.json exists for every package
- Fill editable_governor_config for owner-keyed rules + first-party gaps
- Enrich mail / notion / tavily declarative rules for Owner config
- Add runtime/governor.py stubs only where Track B is requested (optional list)
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGES = REPO / "packages"

OWNER_KEYS = (
    "matches_any_owner",
    "url_host_in_owner",
    "length_gt_owner",
    "mentions_gt_owner",
    "empty_when_owner_true",
)

SCHEMA_PRESETS: dict[str, dict] = {
    "blocked_keywords": {
        "type": "array",
        "items": {"type": "string"},
        "label": "Blocked keywords",
        "description": "Reject when content matches any listed substring (case-insensitive).",
        "default": [],
    },
    "blocked_url_hosts": {
        "type": "array",
        "items": {"type": "string"},
        "label": "Blocked URL hosts",
        "description": "Reject when an http(s) URL host matches.",
        "default": [],
    },
    "max_chars": {
        "type": "integer",
        "minimum": 1,
        "label": "Max characters",
        "description": "Reject when text exceeds this length.",
    },
    "max_mentions": {
        "type": "integer",
        "minimum": 0,
        "label": "Max @ mentions",
    },
    "require_image": {
        "type": "boolean",
        "default": False,
        "label": "Require image",
    },
    "min_body_length": {
        "type": "integer",
        "minimum": 1,
        "label": "Minimum body length",
        "description": "Reject when trimmed body is shorter than this length.",
    },
    "require_title": {
        "type": "boolean",
        "default": False,
        "label": "Require title",
        "description": "Reject when title is empty.",
    },
    "max_results": {
        "type": "integer",
        "minimum": 1,
        "maximum": 20,
        "default": 5,
        "label": "Max results per search",
    },
    "max_content_length": {
        "type": "integer",
        "minimum": 1,
        "label": "Max content length",
    },
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def owner_keys_from_governor(gov: dict) -> set[str]:
    keys: set[str] = set()
    for rule in gov.get("rules") or []:
        when = rule.get("when") or {}
        for cond in when.values():
            if not isinstance(cond, dict):
                continue
            for ok in OWNER_KEYS:
                if ok in cond:
                    keys.add(str(cond[ok]))
    return keys


def enrich_mail(gov: dict, man: dict) -> None:
    rules = list(gov.get("rules") or [])
    ids = {r.get("id") for r in rules if isinstance(r, dict)}
    if "block_banned_words" not in ids:
        rules.insert(
            1,
            {
                "id": "block_banned_words",
                "when": {"args.body": {"matches_any_owner": "blocked_keywords"}},
                "action": "reject",
                "code": "GOVERNOR_POLICY",
                "message": "Email body matches an owner blocked keyword.",
            },
        )
    # also check subject — declarative only supports one arg; add second rule
    if "block_banned_words_subject" not in ids:
        rules.insert(
            2,
            {
                "id": "block_banned_words_subject",
                "when": {"args.subject": {"matches_any_owner": "blocked_keywords"}},
                "action": "reject",
                "code": "GOVERNOR_POLICY",
                "message": "Email subject matches an owner blocked keyword.",
            },
        )
    if "block_short_body" not in ids:
        rules.insert(
            3,
            {
                "id": "block_short_body",
                "when": {"args.body": {"length_lt_owner": "min_body_length"}},
                "action": "reject",
                "code": "VALIDATION",
                "message": "Email body shorter than owner min_body_length.",
            },
        )
    gov["rules"] = rules
    egc = dict(man.get("editable_governor_config") or {})
    egc.setdefault("blocked_keywords", SCHEMA_PRESETS["blocked_keywords"])
    egc.setdefault("min_body_length", SCHEMA_PRESETS["min_body_length"])
    man["editable_governor_config"] = egc


def enrich_notion(gov: dict, man: dict) -> None:
    rules = list(gov.get("rules") or [])
    ids = {r.get("id") for r in rules if isinstance(r, dict)}
    if "block_short_body" not in ids:
        rules.insert(
            1,
            {
                "id": "block_short_body",
                "when": {"args.body": {"length_lt_owner": "min_body_length"}},
                "action": "reject",
                "code": "VALIDATION",
                "message": "Notion body shorter than owner min_body_length.",
            },
        )
    if "block_empty_title" not in ids:
        rules.insert(
            2,
            {
                "id": "block_empty_title",
                "when": {"args.title": {"empty_when_owner_true": "require_title"}},
                "action": "reject",
                "code": "VALIDATION",
                "message": "Notion title is empty.",
            },
        )
    gov["rules"] = rules
    egc = dict(man.get("editable_governor_config") or {})
    egc.setdefault("min_body_length", SCHEMA_PRESETS["min_body_length"])
    egc.setdefault("require_title", SCHEMA_PRESETS["require_title"])
    man["editable_governor_config"] = egc


def enrich_tavily(gov: dict, man: dict) -> None:
    rules = list(gov.get("rules") or [])
    ids = {r.get("id") for r in rules if isinstance(r, dict)}
    if "block_denied_keywords" not in ids:
        rules.insert(
            0,
            {
                "id": "block_denied_keywords",
                "when": {"args.query": {"matches_any_owner": "blocked_keywords"}},
                "action": "reject",
                "code": "GOVERNOR_POLICY",
                "message": "Search query matches an owner blocked keyword.",
            },
        )
    gov["rules"] = rules
    egc = dict(man.get("editable_governor_config") or {})
    egc.setdefault("blocked_keywords", SCHEMA_PRESETS["blocked_keywords"])
    egc.setdefault("max_results", SCHEMA_PRESETS["max_results"])
    man["editable_governor_config"] = egc


def ensure_egc_for_keys(man: dict, keys: set[str]) -> None:
    egc = dict(man.get("editable_governor_config") or {})
    for key in keys:
        if key not in egc and key in SCHEMA_PRESETS:
            egc[key] = SCHEMA_PRESETS[key]
        elif key not in egc:
            egc[key] = {
                "type": "string",
                "label": key,
                "description": f"Owner governor config `{key}` referenced by governor.json rules.",
            }
    if egc:
        man["editable_governor_config"] = egc
    elif "editable_governor_config" not in man:
        # Explicit empty object so Governance UI knows the package opted into the contract.
        man["editable_governor_config"] = {}


TRACK_NOTE = {
    "implementation": "declarative",
    "notes": "Evaluated by Korux platform declarative engine; optional runtime/governor.py overrides.",
}


def migrate_one(root: Path) -> str:
    man_path = root / "manifest.json"
    gov_path = root / "governor.json"
    if not man_path.is_file():
        return "skip-no-manifest"
    man = _load(man_path)
    cid = str(man.get("id") or "")
    if not gov_path.is_file():
        gov = {
            "spec_version": "korux_governor_v1",
            "capability_id": cid,
            "capability_version": str(man.get("version") or "0.0.0"),
            "defaults": {"intercept_on_invoke": bool(man.get("writes_external")), "editable_fields": []},
            "rules": [],
        }
    else:
        gov = _load(gov_path)

    gov.setdefault("spec_version", "korux_governor_v1")
    gov.setdefault("capability_id", cid)
    gov.setdefault("capability_version", str(man.get("version") or "0.0.0"))
    gov.update({k: v for k, v in TRACK_NOTE.items() if k not in gov})

    if cid == "general/mail":
        enrich_mail(gov, man)
    elif cid == "notion/pages":
        enrich_notion(gov, man)
    elif cid == "tavily/web-search":
        enrich_tavily(gov, man)

    keys = owner_keys_from_governor(gov)
    # length_lt_owner is new — include in key scan
    for rule in gov.get("rules") or []:
        when = rule.get("when") or {}
        for cond in when.values():
            if isinstance(cond, dict) and cond.get("length_lt_owner"):
                keys.add(str(cond["length_lt_owner"]))
    ensure_egc_for_keys(man, keys)

    _dump(gov_path, gov)
    _dump(man_path, man)
    return cid


def main() -> None:
    done = []
    for man in sorted(PACKAGES.rglob("manifest.json")):
        if "_template" in str(man) or "example-connector" == man.parent.name:
            # still migrate template separately
            pass
        root = man.parent
        if root.name == "_template" or root.parent.name == "_template":
            continue
        cid = migrate_one(root)
        if cid and not cid.startswith("skip"):
            done.append(cid)
    print(f"migrated {len(done)} packages")
    for c in done:
        print(" ", c)


if __name__ == "__main__":
    main()
