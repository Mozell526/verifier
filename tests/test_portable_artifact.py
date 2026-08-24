from __future__ import annotations

import json
from pathlib import Path

import pytest

from impl.core.path_contract import LogicalPathRef, PathContractError, PathResolver, PathRoots, PathScope
from impl.core.portable_artifact import (
    PortableArtifactWriter,
    resolve_logical_refs_in_payload,
    write_portable_export,
)


def test_portable_writer_serializes_logical_refs_atomically(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    writer = PortableArtifactWriter()

    writer.write_json(
        target,
        {
            "source": LogicalPathRef(
                PathScope.BUSINESS_SOURCE,
                "src/api.py",
                symbol="create_app",
                revision="abc123",
                sha256="a" * 64,
            )
        },
    )

    assert json.loads(target.read_text(encoding="utf-8"))["source"] == {
        "location_scope": "business_source",
        "location": "src/api.py",
        "symbol": "create_app",
        "revision": "abc123",
        "sha256": "a" * 64,
    }
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    "payload",
    [
        {"source_root": "/Users/demo/repo"},
        {"module_path": "tools/check.py"},
        {"run_report": "iterations/001-run.json"},
        {"source": Path("src/api.py")},
        {"location": "src/api.py"},
    ],
)
def test_portable_writer_rejects_physical_or_bare_paths(tmp_path: Path, payload: object) -> None:
    with pytest.raises(PathContractError, match="PATH_SCHEMA_BYPASS"):
        PortableArtifactWriter().write_json(tmp_path / "state.json", payload)


def test_portable_writer_rejects_malformed_logical_ref(tmp_path: Path) -> None:
    with pytest.raises(PathContractError):
        PortableArtifactWriter().write_json(
            tmp_path / "state.json",
            {"source": {"location_scope": "business_source", "location": "../secret"}},
        )


def test_runtime_payload_hydrates_logical_refs_without_requiring_target(tmp_path: Path) -> None:
    business = tmp_path / "business"
    business.mkdir()
    resolver = PathResolver(PathRoots(business_source=business))

    hydrated = resolve_logical_refs_in_payload(
        {
            "response": {
                "workspace_path": LogicalPathRef(
                    PathScope.BUSINESS_SOURCE,
                    "runtime/thread/workspace",
                ).to_mapping()
            }
        },
        resolver,
    )

    assert hydrated["response"]["workspace_path"] == str(
        business / "runtime" / "thread" / "workspace"
    )


def test_historical_export_cannot_write_registered_active_target(tmp_path: Path) -> None:
    target = (
        tmp_path
        / "impl"
        / "projects"
        / "demo"
        / "draft"
        / "investigation"
        / "attribute"
        / "manifest.json"
    )
    target.parent.mkdir(parents=True)

    with pytest.raises(PathContractError, match="PATH_WRITER_BYPASS"):
        write_portable_export(target, {"schema_version": 2})


def test_historical_export_allows_classified_iteration_report(tmp_path: Path) -> None:
    target = (
        tmp_path
        / "impl"
        / "projects"
        / "demo"
        / "draft"
        / ".state"
        / "attribute"
        / "iterations"
        / "001-run.json"
    )
    target.parent.mkdir(parents=True)

    written = write_portable_export(target, {"schema_version": 2, "run_status": "failed"})

    assert written == target
