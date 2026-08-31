"""Standalone capability package validation (aligned with Korux package_validate.py)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CAPABILITY_SPEC_VERSION = "korux_capability_v1"
GOVERNOR_SPEC_VERSION = "korux_governor_v1"

MANIFEST_REQUIRED_FIELDS: tuple[str, ...] = (
    "spec_version",
    "id",
    "version",
    "kind",
    "label",
    "description",
    "category",
    "reads_external",
    "writes_external",
    "boundary",
    "default_gate",
    "risk",
    "auth",
    "runtime",
    "status",
    "trust",
)

GOVERNOR_REQUIRED_FIELDS: tuple[str, ...] = (
    "spec_version",
    "capability_id",
    "capability_version",
    "defaults",
    "rules",
)

TRUST_LEVELS: frozenset[str] = frozenset({"first-party", "verified", "community"})

# Transitional: migrate to runtime.invoke in a follow-up release.
_LEGACY_KERNEL_ENTRY_IDS: frozenset[str] = frozenset({"tavily/web-search"})

PARAM_SOURCE_VALUES: frozenset[str] = frozenset(
    {
        "upstream",
        "trigger",
        "nl_fixed",
        "step_field",
        "vault",
        "default",
        "runtime_override",
    }
)

PARAM_REQUIRED_FIELDS: tuple[str, ...] = ("name", "required", "sources", "description")

_AUTH_FIELD_TYPES: frozenset[str] = frozenset({"text", "password", "number", "checkbox"})


def validate_params(
    params: Any, *, path: str = "params", manifest: dict[str, Any] | None = None
) -> list[str]:
    errors: list[str] = []
    if params is None:
        return []
    if not isinstance(params, list):
        return [f"{path}: must be an array"]

    schema_props: set[str] = set()
    if manifest:
        input_schema = manifest.get("input_schema")
        if isinstance(input_schema, dict):
            props = input_schema.get("properties")
            if isinstance(props, dict):
                schema_props = {str(k) for k in props}

    seen: set[str] = set()
    for i, row in enumerate(params):
        p = f"{path}[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{p}: must be an object")
            continue
        for field in PARAM_REQUIRED_FIELDS:
            if field not in row:
                errors.append(f"{p}: missing required field `{field}`")
        name = str(row.get("name") or "").strip()
        if not name:
            errors.append(f"{p}: name must be non-empty")
        elif name in seen:
            errors.append(f"{p}: duplicate param name {name!r}")
        else:
            seen.add(name)
        if schema_props and name and name not in schema_props:
            errors.append(f"{p}: name {name!r} not declared in input_schema.properties")
        sources = row.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{p}: sources must be a non-empty array")
        else:
            static_sources = {
                str(s)
                for s in sources
                if str(s) in PARAM_SOURCE_VALUES and str(s) != "runtime_override"
            }
            for src in sources:
                s = str(src)
                if s not in PARAM_SOURCE_VALUES:
                    errors.append(f"{p}: invalid source {s!r}")
            if row.get("required") is True and not static_sources:
                errors.append(
                    f"{p}: required=true needs at least one source besides runtime_override"
                )
        if "required" in row and not isinstance(row.get("required"), bool):
            errors.append(f"{p}: required must be boolean")
        desc = row.get("description")
        if desc is not None and not str(desc).strip():
            errors.append(f"{p}: description must be non-empty")
        if row.get("confirm_if_missing") is not None and not isinstance(
            row.get("confirm_if_missing"), bool
        ):
            errors.append(f"{p}: confirm_if_missing must be boolean")
        hint = row.get("propose_hint")
        if hint is not None and not str(hint).strip():
            errors.append(f"{p}: propose_hint must be non-empty when set")
        match = row.get("trigger_match")
        if match is not None:
            if not isinstance(match, dict):
                errors.append(f"{p}: trigger_match must be an object")
            else:
                kinds = match.get("kinds")
                if kinds is not None:
                    if not isinstance(kinds, list) or not kinds:
                        errors.append(f"{p}: trigger_match.kinds must be a non-empty array")
                connectors = match.get("connectors")
                if connectors is not None:
                    if not isinstance(connectors, list) or not connectors:
                        errors.append(
                            f"{p}: trigger_match.connectors must be a non-empty array"
                        )
                if "trigger" in {str(s) for s in (sources or [])} and not kinds and not connectors:
                    errors.append(
                        f"{p}: trigger_match requires kinds and/or connectors when source is trigger"
                    )
    return errors


def _validate_auth_fields(auth: dict[str, Any], *, path: str) -> list[str]:
    errors: list[str] = []
    fields = auth.get("fields")
    if fields is None:
        return errors
    if not isinstance(fields, list):
        return [f"{path}: fields must be an array"]
    for i, raw in enumerate(fields):
        p = f"{path}:fields[{i}]"
        if not isinstance(raw, dict):
            errors.append(f"{p}: must be an object")
            continue
        name = str(raw.get("name") or raw.get("key") or "").strip()
        if not name:
            errors.append(f"{p}: name is required")
        ftype = str(raw.get("type") or ("password" if raw.get("sensitive") else "text"))
        if ftype not in _AUTH_FIELD_TYPES:
            errors.append(f"{p}: invalid type {ftype!r}")
    sub_presets = auth.get("sub_presets")
    if sub_presets is not None:
        if not isinstance(sub_presets, list):
            errors.append(f"{path}: sub_presets must be an array")
        else:
            for i, raw in enumerate(sub_presets):
                if not isinstance(raw, dict):
                    errors.append(f"{path}:sub_presets[{i}] must be an object")
                elif not str(raw.get("id") or "").strip():
                    errors.append(f"{path}:sub_presets[{i}].id is required")
    return errors


def validate_manifest(manifest: dict[str, Any], *, path: str = "manifest") -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return [f"{path}: must be an object"]

    for field in MANIFEST_REQUIRED_FIELDS:
        if field not in manifest:
            errors.append(f"{path}: missing required field `{field}`")

    if manifest.get("spec_version") != CAPABILITY_SPEC_VERSION:
        errors.append(f"{path}: spec_version must be {CAPABILITY_SPEC_VERSION!r}")

    cid = str(manifest.get("id") or "")
    if cid and not re.fullmatch(r"[a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)?", cid):
        errors.append(
            f"{path}: id must be kebab-case or namespace/name (e.g. twitter/publish)"
        )

    version = str(manifest.get("version") or "")
    if version and not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"{path}: version must be semver x.y.z")

    writes = bool(manifest.get("writes_external"))
    gate = str(manifest.get("default_gate") or "")
    if writes and gate != "require_human":
        errors.append(f"{path}: writes_external=true requires default_gate=require_human")

    boundary = str(manifest.get("boundary") or "")
    reads = bool(manifest.get("reads_external"))
    expected_boundary = "External" if (reads or writes) else "Internal"
    if boundary and boundary != expected_boundary:
        errors.append(f"{path}: boundary must be {expected_boundary!r} for I/O flags")

    trust = str(manifest.get("trust") or "")
    if trust and trust not in TRUST_LEVELS:
        errors.append(f"{path}: invalid trust {trust!r}")

    if manifest.get("produces_content") is not None and not isinstance(
        manifest.get("produces_content"), bool
    ):
        errors.append(f"{path}: produces_content must be boolean")
    guide = manifest.get("propose_guide")
    if guide is not None and not str(guide).strip():
        errors.append(f"{path}: propose_guide must be non-empty when set")

    runtime = manifest.get("runtime")
    if runtime is not None and not isinstance(runtime, dict):
        errors.append(f"{path}: runtime must be an object")
    elif isinstance(runtime, dict) and not str(runtime.get("entry") or "").strip():
        errors.append(f"{path}: runtime.entry is required")

    auth = manifest.get("auth")
    if auth is not None and not isinstance(auth, dict):
        errors.append(f"{path}: auth must be an object")
    elif isinstance(auth, dict):
        errors.extend(_validate_auth_fields(auth, path=f"{path}:auth"))

    errors.extend(validate_params(manifest.get("params"), path=f"{path}:params", manifest=manifest))
    return errors


def validate_governor_pack(
    pack: dict[str, Any],
    *,
    manifest: dict[str, Any] | None = None,
    path: str = "governor",
) -> list[str]:
    errors: list[str] = []
    if not isinstance(pack, dict):
        return [f"{path}: must be an object"]

    for field in GOVERNOR_REQUIRED_FIELDS:
        if field not in pack:
            errors.append(f"{path}: missing required field `{field}`")

    if pack.get("spec_version") != GOVERNOR_SPEC_VERSION:
        errors.append(f"{path}: spec_version must be {GOVERNOR_SPEC_VERSION!r}")

    rules = pack.get("rules")
    if rules is not None and not isinstance(rules, list):
        errors.append(f"{path}: rules must be a list")
    elif isinstance(rules, list) and not rules and manifest and manifest.get("writes_external"):
        errors.append(f"{path}: writes_external capability requires non-empty rules")

    if manifest:
        cap_id = str(pack.get("capability_id") or "")
        invoke = str(manifest.get("invoke_tool") or manifest.get("id") or "")
        if cap_id and cap_id not in {str(manifest.get("id")), invoke}:
            if cap_id != str(manifest.get("binding_tool") or ""):
                errors.append(f"{path}: capability_id {cap_id!r} does not match manifest id")

    return errors


def _load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_package_dir(package_dir: Path) -> list[str]:
    errors: list[str] = []
    root = Path(package_dir)
    if not root.is_dir():
        return [f"{root}: not a directory"]

    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        errors.append(f"{root}: missing manifest.json")
        return errors

    try:
        manifest = _load_json_file(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{manifest_path}: {exc}"]

    errors.extend(validate_manifest(manifest, path=str(manifest_path)))

    governor_path = root / "governor.json"
    if bool(manifest.get("writes_external")):
        if not governor_path.is_file():
            errors.append(f"{root}: writes_external requires governor.json")
        else:
            try:
                pack = _load_json_file(governor_path)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{governor_path}: {exc}")
            else:
                errors.extend(
                    validate_governor_pack(pack, manifest=manifest, path=str(governor_path))
                )

    auth = manifest.get("auth") or {}
    if isinstance(auth, dict) and auth.get("required"):
        cred = root / "docs" / "credential.md"
        if not cred.is_file():
            errors.append(f"{root}: auth.required=true requires docs/credential.md")

    errors.extend(validate_params(manifest.get("params"), path="params", manifest=manifest))
    errors.extend(_validate_repertoire_manifest_runtime(root, manifest))
    errors.extend(_validate_package_runtime(root, manifest))
    errors.extend(_validate_no_korux_imports(root))
    return errors


def _validate_no_korux_imports(root: Path) -> list[str]:
    errors: list[str] = []
    for path in root.rglob("*.py"):
        if path.name.startswith("_") and path.name != "__init__.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            continue
        if re.search(r"(^|\n)\s*(import\s+korux|from\s+korux)", text):
            errors.append(f"{path}: must not import korux (repertoire packages are Korux-free)")
    return errors


def _validate_repertoire_manifest_runtime(root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        return errors
    entry = str(runtime.get("entry") or "").strip()
    kind = str(manifest.get("kind") or "").strip()
    cap_kind = str(runtime.get("kind") or "").strip()
    if not cap_kind:
        cap_kind = "kernel" if entry.startswith("korux.") else "package"
    if entry.startswith("korux.") and cap_kind == "package":
        errors.append(
            f"{root}: repertoire packages must not use runtime.entry {entry!r}; use runtime.invoke"
        )
    cap_id = str(manifest.get("id") or "").strip()
    if entry.startswith("korux.") and cap_id not in _LEGACY_KERNEL_ENTRY_IDS:
        errors.append(
            f"{root}: repertoire packages must not use runtime.entry {entry!r}; migrate to runtime.invoke"
        )
    if cap_id in _LEGACY_KERNEL_ENTRY_IDS and entry.startswith("korux."):
        return errors
    if kind == "connector":
        invoke_py = root / "runtime" / "invoke.py"
        if not invoke_py.is_file():
            errors.append(f"{root}: kind=connector requires runtime/invoke.py")
        elif entry and entry != "runtime.invoke" and not entry.startswith("runtime."):
            errors.append(f"{root}: connector runtime.entry must be runtime.invoke")
    return errors


def _is_package_relative_entry(entry: str) -> bool:
    e = str(entry or "").strip()
    if not e or e.startswith("korux."):
        return False
    return e == "runtime.invoke" or e.startswith("runtime.")


def _validate_package_runtime(root: Path, manifest: dict[str, Any]) -> list[str]:
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        return []
    entry = str(runtime.get("entry") or "").strip()
    if not _is_package_relative_entry(entry):
        return []
    invoke_py = root / "runtime" / "invoke.py"
    if not invoke_py.is_file():
        return [f"{root}: runtime.entry {entry!r} requires runtime/invoke.py"]
    try:
        text = invoke_py.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{invoke_py}: {exc}"]
    if not re.search(r"^(async\s+)?def\s+invoke\b", text, re.MULTILINE):
        return [f"{invoke_py}: must define invoke"]
    return []
