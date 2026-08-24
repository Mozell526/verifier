#!/usr/bin/env python3
"""One-time migration for active Draft loop state and referenced reports.

Only reports referenced by loop.json are active. Unreferenced historical reports
are intentionally left byte-for-byte unchanged until they re-enter promotion or
validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from impl.core.path_contract import LogicalPathRef, PathResolver, PathRoots, PathScope, logical_ref_for_path
from impl.core.portable_artifact import (
    PortableArtifactWriter,
    write_active_artifact,
    write_portable_export,
)
from impl.core.project_config import resolve_project_config
from impl.core.schema.draft_state import DRAFT_LOOP_STATE_VERSION, DRAFT_RUN_REPORT_VERSION


REPO_ROOT = Path(__file__).resolve().parents[1]


def migrate_active_draft_artifacts(*, write: bool) -> list[Path]:
    changed: list[Path] = []
    for state_path in sorted(
        (REPO_ROOT / "impl" / "projects").glob("*/draft/.state/*/loop.json")
    ):
        project_root = state_path.parents[3].resolve()
        roots = PathRoots(verifier_repo=REPO_ROOT, project_package=project_root)
        raw = _read_object(state_path)
        migrated = dict(raw)
        migrated["schema_version"] = DRAFT_LOOP_STATE_VERSION
        migrated_iterations: list[dict[str, Any]] = []
        for index, item in enumerate(raw.get("iterations") or []):
            if not isinstance(item, Mapping):
                raise TypeError(f"{state_path}: iterations[{index}] must be an object")
            iteration = dict(item)
            existing_report_ref, report_path = _project_reference(
                item.get("run_report"),
                state_path=state_path,
                roots=roots,
                field_path=f"iterations[{index}].run_report",
            )
            original_report = _read_object(report_path)
            report = _migrate_report(original_report, roots, report_path)
            if report != original_report:
                changed.append(report_path)
                if write:
                    write_portable_export(report_path, report)
            report_ref = (
                existing_report_ref
                if report == original_report and existing_report_ref.sha256
                else logical_ref_for_path(
                    report_path,
                    scope=PathScope.PROJECT_PACKAGE,
                    roots=roots,
                    field_path=f"iterations[{index}].run_report",
                    sha256=_file_sha256(report_path),
                )
            )
            iteration["run_report"] = dict(report_ref.to_mapping())
            iteration["evidence"] = [
                _evidence_pointer(
                    value,
                    state_path=state_path,
                    project_root=project_root,
                    roots=roots,
                    field_path=f"iterations[{index}].evidence[{pointer_index}]",
                )
                for pointer_index, value in enumerate(item.get("evidence") or [])
            ]
            migrated_iterations.append(iteration)
        migrated["iterations"] = migrated_iterations
        if migrated != raw:
            changed.append(state_path)
            if write:
                write_active_artifact(
                    "draft_loop",
                    state_path,
                    migrated,
                    repository_root=REPO_ROOT,
                )
    return changed


def migrate_iteration_case_paths(*, write: bool) -> list[Path]:
    changed: list[Path] = []
    for cases_path in sorted(
        (REPO_ROOT / "impl" / "projects").glob(
            "*/draft/.state/*/iteration-cases.json"
        )
    ):
        project_root = cases_path.parents[3]
        project_id = project_root.name
        spec = resolve_project_config(
            project_id,
            projects_dir=REPO_ROOT / "impl" / "projects",
            dotenv_path=REPO_ROOT / ".env",
            verifier_root=REPO_ROOT,
        )
        if spec.path_roots is None:
            raise RuntimeError(f"{project_id} has no registered PathRoots")
        original = json.loads(cases_path.read_text(encoding="utf-8"))
        migrated = _migrate_captured_runtime_paths(original, spec.path_roots)
        if migrated == original:
            continue
        changed.append(cases_path)
        state_path = cases_path.parent / "loop.json"
        state = _read_object(state_path)
        state["cases_sha256"] = _stable_hash(migrated)
        changed.append(state_path)
        if write:
            write_active_artifact(
                "draft_iteration_cases",
                cases_path,
                migrated,
                repository_root=REPO_ROOT,
            )
            write_active_artifact(
                "draft_loop",
                state_path,
                state,
                repository_root=REPO_ROOT,
            )
    return changed


def _migrate_captured_runtime_paths(value: Any, roots: PathRoots) -> Any:
    if isinstance(value, Mapping):
        if "location_scope" in value:
            LogicalPathRef.from_mapping(value)
            return dict(value)
        migrated: dict[str, Any] = {}
        for key, item in value.items():
            if key in {
                "external_repo",
                "workspace_path",
                "uploads_path",
                "outputs_path",
            } and isinstance(item, str):
                path = Path(item)
                if path.is_absolute():
                    migrated[key] = dict(logical_ref_for_path(
                        path,
                        scope=PathScope.BUSINESS_SOURCE,
                        roots=roots,
                        field_path=f"draft_iteration_cases.{key}",
                    ).to_mapping())
                    continue
            migrated[str(key)] = _migrate_captured_runtime_paths(item, roots)
        return migrated
    if isinstance(value, list):
        return [_migrate_captured_runtime_paths(item, roots) for item in value]
    return value


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _project_reference(
    value: Any,
    *,
    state_path: Path,
    roots: PathRoots,
    field_path: str,
) -> tuple[LogicalPathRef, Path]:
    if isinstance(value, Mapping):
        reference = LogicalPathRef.from_mapping(value, field_path=field_path)
        if reference.location_scope is not PathScope.PROJECT_PACKAGE:
            raise ValueError(f"{state_path}: {field_path} must use project_package scope")
        path = reference.resolve(
            PathResolver(roots),
            field_path=field_path,
            expected_type="file",
        ).physical
        return reference, path
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{state_path}: {field_path} must contain a report path")
    path = Path(value)
    if not path.is_absolute():
        path = state_path.parent / path
    path = path.resolve()
    reference = logical_ref_for_path(
        path,
        scope=PathScope.PROJECT_PACKAGE,
        roots=roots,
        field_path=field_path,
    )
    return reference, path


def _evidence_pointer(
    value: Any,
    *,
    state_path: Path,
    project_root: Path,
    roots: PathRoots,
    field_path: str,
) -> dict[str, Any]:
    if isinstance(value, Mapping):
        raw_artifact = value.get("artifact")
        if not isinstance(raw_artifact, Mapping):
            raise TypeError(f"{state_path}: {field_path}.artifact must be a LogicalPathRef")
        reference = LogicalPathRef.from_mapping(
            raw_artifact, field_path=f"{field_path}.artifact"
        )
        path = reference.resolve(
            PathResolver(roots), field_path=f"{field_path}.artifact", expected_type="file"
        ).physical
        persisted = reference if reference.sha256 else LogicalPathRef(
            reference.location_scope,
            reference.location,
            symbol=reference.symbol,
            revision=reference.revision,
            sha256=_file_sha256(path),
        )
        result = {"artifact": dict(persisted.to_mapping())}
        pointer = value.get("pointer")
        if pointer:
            result["pointer"] = pointer
        return result
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{state_path}: {field_path} must contain an evidence pointer")
    raw_path, separator, fragment = value.partition("#")
    path = Path(raw_path)
    if not path.is_absolute():
        path = state_path.parent / path
    path = path.resolve()
    if path.is_relative_to(project_root):
        scope = PathScope.PROJECT_PACKAGE
    elif path.is_relative_to(REPO_ROOT):
        scope = PathScope.VERIFIER_REPO
    else:
        raise ValueError(f"{state_path}: {field_path} is outside registered roots")
    reference = logical_ref_for_path(
        path,
        scope=scope,
        roots=roots,
        field_path=field_path,
        sha256=_file_sha256(path),
    )
    result: dict[str, Any] = {"artifact": dict(reference.to_mapping())}
    if separator:
        result["pointer"] = f"#{fragment}"
    return result


def _migrate_report(
    report: Mapping[str, Any],
    roots: PathRoots,
    report_path: Path,
) -> dict[str, Any]:
    migrated = dict(report)
    migrated["schema_version"] = DRAFT_RUN_REPORT_VERSION
    for side in ("current", "draft"):
        raw_side = migrated.get(side)
        if not isinstance(raw_side, Mapping):
            continue
        side_value = dict(raw_side)
        assets: list[Any] = []
        for index, raw_asset in enumerate(raw_side.get("assets") or []):
            if not isinstance(raw_asset, Mapping):
                raise TypeError(f"{report_path}: {side}.assets[{index}] must be an object")
            asset = dict(raw_asset)
            old_path = asset.pop("path", None)
            if old_path is not None:
                path = Path(str(old_path)).resolve()
                asset["location"] = dict(logical_ref_for_path(
                    path,
                    scope=PathScope.PROJECT_PACKAGE,
                    roots=roots,
                    field_path=f"{side}.assets[{index}].path",
                ).to_mapping())
            elif isinstance(asset.get("location"), Mapping):
                LogicalPathRef.from_mapping(
                    asset["location"], field_path=f"{side}.assets[{index}].location"
                )
            else:
                raise ValueError(f"{report_path}: {side}.assets[{index}] has no location")
            assets.append(asset)
        side_value["assets"] = assets
        migrated[side] = side_value
    PortableArtifactWriter().validate(migrated)
    return migrated


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected a JSON object")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="apply the migration")
    parser.add_argument(
        "--iteration-cases-only",
        action="store_true",
        help="migrate captured runtime paths and the owning loop hash only",
    )
    args = parser.parse_args()
    changed = migrate_iteration_case_paths(write=args.write)
    if not args.iteration_cases_only:
        changed = [*migrate_active_draft_artifacts(write=args.write), *changed]
    mode = "migrated" if args.write else "would migrate"
    for path in changed:
        print(f"{mode}: {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
