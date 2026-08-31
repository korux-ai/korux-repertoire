#!/usr/bin/env python3
"""Authoring quality scorecard for repertoire capability packages.

Hard findings reuse structural validation (same as validate_capability_package).
Soft findings are warnings: docs completeness, example JSON, setup guidance, etc.

Exit codes:
  0 — no hard failures (warnings allowed unless --fail-on-warn)
  1 — hard failures, or warnings when --fail-on-warn
  2 — usage / path error
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from package_validate import validate_package_dir  # noqa: E402

REPO_ROOT = ROOT.parent
PACKAGES_ROOT = REPO_ROOT / "packages"

MIN_LABEL_LEN = 3
MIN_DESCRIPTION_LEN = 24
MIN_PROPOSE_GUIDE_LEN = 40

# Headings / sections that indicate human setup / application guidance.
_SETUP_HEADING_RE = re.compile(
    r"(?im)^#{1,3}\s+.*(prerequisite|setup|agent binding|vault|credential|"
    r"gmail|how to|portal|oauth|developer|binding|申请|绑定|凭证).*$"
)
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_LATIN_RE = re.compile(r"[A-Za-z]{3,}")


@dataclass
class Finding:
    severity: str  # hard | warn | info
    code: str
    message: str


@dataclass
class PackageReport:
    package_id: str
    path: Path
    findings: list[Finding] = field(default_factory=list)

    @property
    def hard_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "hard")

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warn")

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "info")

    @property
    def grade(self) -> str:
        if self.hard_count:
            return "FAIL"
        if self.warn_count:
            return "WARN"
        return "PASS"


def iter_package_dirs(packages_root: Path) -> list[Path]:
    dirs: list[Path] = []
    if not packages_root.is_dir():
        return dirs
    for path in sorted(packages_root.rglob("manifest.json")):
        root = path.parent
        parts = root.relative_to(packages_root).parts
        if any(p.startswith("_") for p in parts):
            continue
        if len(parts) not in (1, 2):
            continue
        dirs.append(root)
    return dirs


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _short_text(value: Any) -> str:
    return str(value or "").strip()


def score_package(package_dir: Path) -> PackageReport:
    root = Path(package_dir)
    manifest_path = root / "manifest.json"
    manifest = _load_json(manifest_path) or {}
    package_id = _short_text(manifest.get("id")) or root.name
    report = PackageReport(package_id=package_id, path=root)

    for err in validate_package_dir(root):
        report.findings.append(Finding("hard", "structural", err))

    if not manifest:
        report.findings.append(
            Finding("hard", "manifest_parse", f"{manifest_path}: unreadable or invalid JSON")
        )
        return report

    _score_copy(report, manifest)
    _score_propose(report, manifest)
    _score_docs(report, root, manifest)
    _score_auth_examples(report, root, manifest)
    _score_ids(report, root, manifest)
    _score_skill_shape(report, root, manifest)
    _score_i18n(report, manifest)
    return report


def _score_copy(report: PackageReport, manifest: dict[str, Any]) -> None:
    label = _short_text(manifest.get("label"))
    if len(label) < MIN_LABEL_LEN:
        report.findings.append(
            Finding("warn", "label_short", f"label too short (<{MIN_LABEL_LEN} chars)")
        )
    elif not _LATIN_RE.search(label):
        report.findings.append(
            Finding(
                "warn",
                "label_english",
                "label has no Latin letters; public catalog docs expect English",
            )
        )

    description = _short_text(manifest.get("description"))
    if len(description) < MIN_DESCRIPTION_LEN:
        report.findings.append(
            Finding(
                "warn",
                "description_short",
                f"description too short (<{MIN_DESCRIPTION_LEN} chars)",
            )
        )
    elif not _LATIN_RE.search(description):
        report.findings.append(
            Finding(
                "warn",
                "description_english",
                "description has no Latin letters; public catalog docs expect English",
            )
        )


def _score_propose(report: PackageReport, manifest: dict[str, Any]) -> None:
    kind = _short_text(manifest.get("kind"))
    min_len = 120 if kind == "skill" else MIN_PROPOSE_GUIDE_LEN
    guide = manifest.get("propose_guide")
    if guide is None or not _short_text(guide):
        report.findings.append(
            Finding(
                "warn",
                "propose_guide_missing",
                "propose_guide is missing or empty"
                + (" (required for kind=skill)" if kind == "skill" else ""),
            )
        )
        return
    if len(_short_text(guide)) < min_len:
        report.findings.append(
            Finding(
                "warn",
                "propose_guide_short",
                f"propose_guide too short (<{min_len} chars)"
                + (" for catalog skill" if kind == "skill" else ""),
            )
        )


def _score_skill_shape(report: PackageReport, root: Path, manifest: dict[str, Any]) -> None:
    if _short_text(manifest.get("kind")) != "skill":
        return
    runtime = manifest.get("runtime")
    invoke_py = root / "runtime" / "invoke.py"
    if runtime is None and not invoke_py.is_file():
        report.findings.append(
            Finding(
                "info",
                "skill_catalog_only",
                "kind=skill with no runtime — Propose/catalog only; platform kernel executes",
            )
        )
    elif invoke_py.is_file():
        report.findings.append(
            Finding(
                "info",
                "skill_with_runtime",
                "skill ships runtime/invoke.py — ensure Korux loads package invoke for this id",
            )
        )
    if bool(manifest.get("writes_external")):
        report.findings.append(
            Finding(
                "warn",
                "skill_writes_external",
                "catalog skills should rarely writes_external; prefer a connector for external writes",
            )
        )


def _score_docs(report: PackageReport, root: Path, manifest: dict[str, Any]) -> None:
    docs = root / "docs"
    readme = docs / "README.md"
    if not readme.is_file():
        report.findings.append(
            Finding("warn", "docs_readme_missing", "docs/README.md is missing")
        )

    auth = manifest.get("auth") if isinstance(manifest.get("auth"), dict) else {}
    if auth.get("required"):
        cred = docs / "credential.md"
        if not cred.is_file():
            # Structural validate already hard-fails; keep scorecard quiet here.
            return
        try:
            text = cred.read_text(encoding="utf-8")
        except OSError as exc:
            report.findings.append(Finding("warn", "credential_unreadable", str(exc)))
            return
        if not _SETUP_HEADING_RE.search(text) and "bind" not in text.lower():
            report.findings.append(
                Finding(
                    "warn",
                    "credential_setup_missing",
                    "docs/credential.md lacks setup / binding guidance headings",
                )
            )
        if "```" not in text and "example_json" not in auth:
            report.findings.append(
                Finding(
                    "warn",
                    "credential_json_example_missing",
                    "docs/credential.md has no fenced JSON example",
                )
            )


def _parse_example_json(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    text = _short_text(raw)
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _example_from_credential_md(text: str) -> dict[str, Any] | None:
    match = _JSON_FENCE_RE.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _score_auth_examples(
    report: PackageReport, root: Path, manifest: dict[str, Any]
) -> None:
    auth = manifest.get("auth") if isinstance(manifest.get("auth"), dict) else {}
    if not auth.get("required"):
        return

    fields = auth.get("fields")
    field_names: list[str] = []
    required_names: list[str] = []
    if isinstance(fields, list):
        for row in fields:
            if not isinstance(row, dict):
                continue
            name = _short_text(row.get("name"))
            if not name:
                continue
            field_names.append(name)
            if row.get("required", True):
                required_names.append(name)

    example = _parse_example_json(auth.get("example_json"))
    cred_path = root / "docs" / "credential.md"
    cred_text = ""
    if cred_path.is_file():
        try:
            cred_text = cred_path.read_text(encoding="utf-8")
        except OSError:
            cred_text = ""

    if example is None and auth.get("example_json") is not None:
        report.findings.append(
            Finding("warn", "example_json_invalid", "auth.example_json is not a JSON object")
        )
    elif example is None:
        example = _example_from_credential_md(cred_text) if cred_text else None
        if example is None:
            report.findings.append(
                Finding(
                    "warn",
                    "example_json_missing",
                    "auth.example_json missing and no parseable JSON fence in credential.md",
                )
            )
        else:
            report.findings.append(
                Finding(
                    "warn",
                    "example_json_not_in_manifest",
                    "auth.example_json missing; JSON fence found in credential.md — copy into manifest",
                )
            )

    if example is not None and required_names:
        missing = [n for n in required_names if n not in example]
        if missing:
            report.findings.append(
                Finding(
                    "warn",
                    "example_json_fields",
                    "example JSON missing required auth.fields: " + ", ".join(missing),
                )
            )

    if cred_text and field_names:
        missing_docs = [n for n in field_names if n not in cred_text]
        if missing_docs:
            report.findings.append(
                Finding(
                    "warn",
                    "credential_fields_undocumented",
                    "auth.fields not mentioned in credential.md: " + ", ".join(missing_docs),
                )
            )


def _score_ids(report: PackageReport, root: Path, manifest: dict[str, Any]) -> None:
    cap_id = _short_text(manifest.get("id"))
    aliases = manifest.get("aliases") if isinstance(manifest.get("aliases"), list) else []
    alias_set = {str(a).strip() for a in aliases if str(a).strip()}
    known = {cap_id} | alias_set

    auth = manifest.get("auth") if isinstance(manifest.get("auth"), dict) else {}
    for key, val in (
        ("binding_tool", _short_text(manifest.get("binding_tool"))),
        ("invoke_tool", _short_text(manifest.get("invoke_tool"))),
        ("auth.binding_tool", _short_text(auth.get("binding_tool"))),
    ):
        if val and val not in known:
            report.findings.append(
                Finding(
                    "warn",
                    f"{key.replace('.', '_')}_mismatch",
                    f"{key}={val!r} is not manifest id or aliases",
                )
            )

    gov_path = root / "governor.json"
    if not gov_path.is_file():
        return
    pack = _load_json(gov_path)
    if not pack:
        return
    gov_id = _short_text(pack.get("capability_id"))
    if gov_id and gov_id not in known and gov_id != _short_text(manifest.get("binding_tool")):
        report.findings.append(
            Finding(
                "warn",
                "governor_id_mismatch",
                f"governor.capability_id={gov_id!r} does not match manifest id/aliases",
            )
        )
    gov_ver = _short_text(pack.get("capability_version"))
    man_ver = _short_text(manifest.get("version"))
    if gov_ver and man_ver and gov_ver != man_ver:
        report.findings.append(
            Finding(
                "warn",
                "governor_version_mismatch",
                f"governor.capability_version={gov_ver!r} != manifest.version={man_ver!r}",
            )
        )


def _score_i18n(report: PackageReport, manifest: dict[str, Any]) -> None:
    # Catalog contract does not yet define i18n fields; surface as info only.
    for key in ("label_i18n", "description_i18n", "i18n"):
        if key in manifest:
            val = manifest.get(key)
            if not val:
                report.findings.append(
                    Finding("warn", f"{key}_empty", f"{key} is present but empty")
                )
            return
    report.findings.append(
        Finding(
            "info",
            "i18n_not_in_contract",
            "no i18n fields on manifest (catalog contract is English-only for now)",
        )
    )


def _print_text_report(reports: list[PackageReport]) -> None:
    hard_total = warn_total = 0
    for report in reports:
        hard_total += report.hard_count
        warn_total += report.warn_count
        rel = report.path.relative_to(REPO_ROOT) if report.path.is_relative_to(REPO_ROOT) else report.path
        print(f"[{report.grade}] {report.package_id}  ({rel})")
        if not report.findings:
            print("  (no findings)")
            continue
        for finding in report.findings:
            print(f"  {finding.severity.upper():4} {finding.code}: {finding.message}")
        print()
    print(
        f"Summary: {len(reports)} packages, "
        f"{hard_total} hard, {warn_total} warn, "
        f"{sum(1 for r in reports if r.grade == 'PASS')} pass"
    )


def _render_html(reports: list[PackageReport]) -> str:
    rows: list[str] = []
    for report in reports:
        color = {"PASS": "#1b7f4e", "WARN": "#a15c00", "FAIL": "#a11"}.get(report.grade, "#333")
        items = "".join(
            f"<li><code>{html.escape(f.severity)}</code> "
            f"<strong>{html.escape(f.code)}</strong>: {html.escape(f.message)}</li>"
            for f in report.findings
            if f.severity != "info"
        )
        info_items = "".join(
            f"<li class='info'><code>info</code> "
            f"<strong>{html.escape(f.code)}</strong>: {html.escape(f.message)}</li>"
            for f in report.findings
            if f.severity == "info"
        )
        body = items + info_items
        if not body:
            body = "<li>(no findings)</li>"
        rows.append(
            f"<tr>"
            f"<td style='color:{color};font-weight:700'>{html.escape(report.grade)}</td>"
            f"<td><code>{html.escape(report.package_id)}</code></td>"
            f"<td>{report.hard_count}</td>"
            f"<td>{report.warn_count}</td>"
            f"<td><ul>{body}</ul></td>"
            f"</tr>"
        )
    hard_total = sum(r.hard_count for r in reports)
    warn_total = sum(r.warn_count for r in reports)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>korux-repertoire package scorecard</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; color: #1a1a1a; }}
    h1 {{ font-size: 1.4rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #ddd; padding: 0.6rem 0.5rem; vertical-align: top; text-align: left; }}
    th {{ font-size: 0.85rem; color: #555; }}
    ul {{ margin: 0; padding-left: 1.1rem; }}
    li.info {{ color: #666; }}
    code {{ font-size: 0.9em; }}
  </style>
</head>
<body>
  <h1>korux-repertoire package scorecard</h1>
  <p>{len(reports)} packages · {hard_total} hard · {warn_total} warn</p>
  <table>
    <thead>
      <tr><th>Grade</th><th>Package</th><th>Hard</th><th>Warn</th><th>Findings</th></tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
  </table>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Package dirs (default: all packages under packages/)",
    )
    parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Exit 1 when any soft warning is present",
    )
    parser.add_argument(
        "--html",
        type=Path,
        help="Write a static HTML report to this path",
    )
    parser.add_argument(
        "--quiet-info",
        action="store_true",
        help="Omit info-level findings from text output",
    )
    args = parser.parse_args(argv)

    if args.paths:
        package_dirs = [Path(p).resolve() for p in args.paths]
        for path in package_dirs:
            if not path.is_dir():
                print(f"not a directory: {path}", file=sys.stderr)
                return 2
    else:
        package_dirs = iter_package_dirs(PACKAGES_ROOT)
        if not package_dirs:
            print(f"no packages found under {PACKAGES_ROOT}", file=sys.stderr)
            return 2

    reports = [score_package(path) for path in package_dirs]

    if args.quiet_info:
        for report in reports:
            report.findings = [f for f in report.findings if f.severity != "info"]

    _print_text_report(reports)

    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(_render_html(reports), encoding="utf-8")
        print(f"Wrote HTML report: {args.html}")

    if any(r.hard_count for r in reports):
        return 1
    if args.fail_on_warn and any(r.warn_count for r in reports):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
