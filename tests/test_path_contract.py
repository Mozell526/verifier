from __future__ import annotations

import os
from pathlib import Path

import pytest

from impl.core.path_contract import (
    LogicalPathRef,
    PathContractError,
    PathResolver,
    PathRoots,
    PathScope,
    logical_ref_for_path,
    parse_prefixed_path,
)


def test_parse_prefixed_path_returns_declared_scope() -> None:
    path = parse_prefixed_path(
        "business://src/api/server.py",
        field_path="source.entrypoint",
        allowed_scopes={PathScope.BUSINESS_SOURCE},
    )

    assert path.scope is PathScope.BUSINESS_SOURCE
    assert path.location == "src/api/server.py"
    assert str(path) == "business://src/api/server.py"


def test_bare_path_is_rejected_without_legacy_scope_escape_hatch() -> None:
    with pytest.raises(PathContractError) as exc_info:
        parse_prefixed_path(
            "draft/attribute.py",
            field_path="verifier.roles.attribute.draft.module",
            allowed_scopes={PathScope.PROJECT_PACKAGE},
        )

    assert exc_info.value.code == "PATH_PREFIX_REQUIRED"


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("/tmp/server.py", "PATH_ABSOLUTE_CONFIG"),
        ("~/server.py", "PATH_ABSOLUTE_CONFIG"),
        ("C:\\repo\\server.py", "PATH_ABSOLUTE_CONFIG"),
        ("file://repo/server.py", "PATH_ABSOLUTE_CONFIG"),
        ("business://../server.py", "PATH_TRAVERSAL"),
        ("business://${ROOT}/server.py", "PATH_TRAVERSAL"),
        ("unknown://server.py", "PATH_PREFIX_UNKNOWN"),
    ],
)
def test_parse_rejects_nonportable_paths(value: str, code: str) -> None:
    with pytest.raises(PathContractError) as exc_info:
        parse_prefixed_path(
            value,
            field_path="field",
            allowed_scopes=set(PathScope),
        )

    assert exc_info.value.code == code


def test_parse_rejects_scope_not_allowed() -> None:
    with pytest.raises(PathContractError) as exc_info:
        parse_prefixed_path(
            "verifier://fixtures/case.json",
            field_path="field",
            allowed_scopes={PathScope.BUSINESS_SOURCE},
        )

    assert exc_info.value.code == "PATH_PREFIX_NOT_ALLOWED"


def test_resolver_uses_only_declared_root(tmp_path: Path) -> None:
    verifier = tmp_path / "verifier"
    business = tmp_path / "business"
    verifier.mkdir()
    business.mkdir()
    (verifier / "same.py").write_text("verifier", encoding="utf-8")
    (business / "same.py").write_text("business", encoding="utf-8")
    resolver = PathResolver(PathRoots(verifier_repo=verifier, business_source=business))

    resolved = resolver.resolve(
        "business://same.py",
        field_path="field",
        allowed_scopes={PathScope.BUSINESS_SOURCE},
        expected_type="file",
    )

    assert resolved.physical == (business / "same.py").resolve()


def test_resolver_can_address_the_declared_root(tmp_path: Path) -> None:
    business = tmp_path / "business"
    business.mkdir()
    resolver = PathResolver(PathRoots(business_source=business))

    resolved = resolver.resolve(
        "business://.",
        field_path="project.resources.source.repository",
        allowed_scopes={PathScope.BUSINESS_SOURCE},
        expected_type="directory",
    )

    assert resolved.physical == business.resolve()


def test_resolver_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    try:
        os.symlink(outside, root / "escape", target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not available")
    resolver = PathResolver(PathRoots(project_package=root))

    with pytest.raises(PathContractError) as exc_info:
        resolver.resolve(
            "project://escape/secret.txt",
            field_path="field",
            allowed_scopes={PathScope.PROJECT_PACKAGE},
        )

    assert exc_info.value.code == "PATH_SYMLINK_ESCAPE"


def test_resolver_validates_root_presence_target_type_and_existence(tmp_path: Path) -> None:
    resolver = PathResolver(PathRoots(project_package=tmp_path))
    directory = tmp_path / "directory"
    directory.mkdir()

    with pytest.raises(PathContractError, match="PATH_TYPE_MISMATCH"):
        resolver.resolve(
            "project://directory",
            field_path="field",
            allowed_scopes={PathScope.PROJECT_PACKAGE},
            expected_type="file",
        )
    with pytest.raises(PathContractError, match="PATH_NOT_FOUND"):
        resolver.resolve(
            "project://missing.py",
            field_path="field",
            allowed_scopes={PathScope.PROJECT_PACKAGE},
        )
    with pytest.raises(PathContractError, match="PATH_ROOT_UNBOUND"):
        PathResolver(PathRoots()).resolve(
            "artifact://state.json",
            field_path="field",
            allowed_scopes={PathScope.ARTIFACT_PACKAGE},
        )


def test_logical_path_ref_round_trip_and_resolve(tmp_path: Path) -> None:
    target = tmp_path / "src" / "api.py"
    target.parent.mkdir()
    target.write_text("pass\n", encoding="utf-8")
    reference = LogicalPathRef.from_mapping(
        {
            "location_scope": "business_source",
            "location": "src/api.py",
            "symbol": "create_app",
            "revision": "abc123",
            "sha256": "a" * 64,
        }
    )

    assert dict(reference.to_mapping()) == {
        "location_scope": "business_source",
        "location": "src/api.py",
        "symbol": "create_app",
        "revision": "abc123",
        "sha256": "a" * 64,
    }
    resolved = reference.resolve(
        PathResolver(PathRoots(business_source=tmp_path)),
        expected_type="file",
    )
    assert resolved.physical == target.resolve()


def test_reverse_mapping_requires_declared_scope_when_roots_overlap(tmp_path: Path) -> None:
    project = tmp_path / "impl" / "projects" / "demo"
    target = project / "draft" / "report.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")
    roots = PathRoots(verifier_repo=tmp_path, project_package=project)

    project_ref = logical_ref_for_path(
        target,
        scope=PathScope.PROJECT_PACKAGE,
        roots=roots,
        field_path="report",
    )
    verifier_ref = logical_ref_for_path(
        target,
        scope=PathScope.VERIFIER_REPO,
        roots=roots,
        field_path="report",
    )

    assert project_ref.location == "draft/report.json"
    assert verifier_ref.location == "impl/projects/demo/draft/report.json"


def test_all_five_roots_move_without_changing_logical_references(tmp_path: Path) -> None:
    scopes = {
        PathScope.VERIFIER_REPO: "verifier_repo",
        PathScope.BUSINESS_SOURCE: "business_source",
        PathScope.PROJECT_PACKAGE: "project_package",
        PathScope.KNOWLEDGE_ROUTE: "knowledge_route",
        PathScope.ARTIFACT_PACKAGE: "artifact_package",
    }
    references = {
        scope: LogicalPathRef(scope, "same.txt")
        for scope in scopes
    }

    for machine in ("machine-a", "machine-b"):
        machine_root = tmp_path / machine
        roots = {}
        for scope, field_name in scopes.items():
            root = machine_root / field_name
            root.mkdir(parents=True)
            (root / "same.txt").write_text(
                f"{machine}:{scope.value}", encoding="utf-8"
            )
            roots[field_name] = root
        resolver = PathResolver(PathRoots(**roots))

        for scope, reference in references.items():
            resolved = reference.resolve(resolver, expected_type="file").physical
            assert resolved == (roots[scopes[scope]] / "same.txt").resolve()
            assert resolved.read_text(encoding="utf-8") == f"{machine}:{scope.value}"
