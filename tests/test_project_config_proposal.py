from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from impl.core.knowledge_route import load_project_knowledge_route
from impl.core.project_config import resolve_project_config
from scripts.scaffold_project import (
    accept_project_config_proposal,
    create_project_config_proposal,
    project_config_proposal_candidate,
    render_live_schema_stub,
    render_project_config,
    seal_project_config_proposal,
)


def test_scaffold_live_schema_does_not_duplicate_project_configuration():
    rendered = render_live_schema_stub("demo")

    for legacy_name in ("READY", "SCENARIO_ENUM", "INTENT_LABELS"):
        assert legacy_name not in rendered
    assert "REQUEST_JSON_SCHEMA" in rendered
    assert "EXTRACT_OUTPUT_JSON_SCHEMA" in rendered


def _write_route(root: Path, project_id: str = "demo") -> None:
    route_root = root / "projects" / project_id
    route_root.mkdir(parents=True)
    (route_root / "requirements.md").write_text(
        "业务目标：验证 proposal。\n范围：单轮问答。\n非目标：不调用服务。\n核心场景：已有输出。\n",
        encoding="utf-8",
    )
    (route_root / "project.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "project": {
                    "id": project_id,
                    "name": "Demo",
                    "description": "Demo project",
                },
                "documents": {
                    "requirements": {
                        "path": "route://requirements.md",
                        "type": "requirements",
                        "required": True,
                        "description": "business requirements",
                    }
                },
                "onboarding": {
                    "interaction": "single_turn",
                    "ready": ["output", "reference"],
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _proposal(root: Path):
    _write_route(root)
    route = load_project_knowledge_route(
        "demo",
        knowledge_root=root / "projects",
        verifier_root=root,
        environ={},
    )
    proposal_dir, status = create_project_config_proposal(
        route,
        render_project_config(route),
        root=root,
    )
    manifest = yaml.safe_load((proposal_dir / "proposal.yaml").read_text(encoding="utf-8"))
    return proposal_dir, status, manifest


def test_proposal_is_not_runtime_config_until_explicit_accept(tmp_path: Path) -> None:
    proposal_dir, status, manifest = _proposal(tmp_path)

    assert status == "proposal_created"
    assert manifest["validation"] == {"status": "passed", "errors": []}
    assert proposal_dir.is_relative_to(tmp_path / "report" / "config-proposals")
    with pytest.raises(FileNotFoundError):
        resolve_project_config(
            "demo",
            projects_dir=tmp_path / "impl" / "projects",
            verifier_root=tmp_path,
            environ={},
        )

    candidate_hash = manifest["candidate"]["sha256"]
    with pytest.raises(ValueError, match="hash changed after review"):
        accept_project_config_proposal(
            proposal_dir,
            expected_hash="0" * 64,
            root=tmp_path,
        )

    target = accept_project_config_proposal(
        proposal_dir,
        expected_hash=candidate_hash,
        root=tmp_path,
    )
    spec = resolve_project_config(
        "demo",
        projects_dir=tmp_path / "impl" / "projects",
        verifier_root=tmp_path,
        environ={},
    )

    assert target == tmp_path / "impl" / "projects" / "demo" / "project.yaml"
    assert spec.metadata["accepted_proposal_sha256"] == candidate_hash


def test_accept_rejects_candidate_or_route_changed_after_seal(tmp_path: Path) -> None:
    proposal_dir, _status, manifest = _proposal(tmp_path)
    candidate_path = proposal_dir / "project.yaml"
    candidate_path.write_text(
        candidate_path.read_text(encoding="utf-8") + "# changed after review\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hash changed after review"):
        accept_project_config_proposal(
            proposal_dir,
            expected_hash=manifest["candidate"]["sha256"],
            root=tmp_path,
        )

    seal_project_config_proposal(proposal_dir, root=tmp_path)
    resealed = yaml.safe_load((proposal_dir / "proposal.yaml").read_text(encoding="utf-8"))
    (tmp_path / "projects" / "demo" / "project.yaml").write_text(
        (tmp_path / "projects" / "demo" / "project.yaml").read_text(encoding="utf-8")
        + "# route changed\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="knowledge route changed"):
        accept_project_config_proposal(
            proposal_dir,
            expected_hash=resealed["candidate"]["sha256"],
            root=tmp_path,
        )


def test_initial_accept_never_overwrites_existing_formal_config(tmp_path: Path) -> None:
    proposal_dir, _status, manifest = _proposal(tmp_path)
    target = tmp_path / "impl" / "projects" / "demo" / "project.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("human: decision\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        accept_project_config_proposal(
            proposal_dir,
            expected_hash=manifest["candidate"]["sha256"],
            root=tmp_path,
        )
    assert target.read_text(encoding="utf-8") == "human: decision\n"


def test_existing_project_proposal_starts_from_human_owned_config(tmp_path: Path) -> None:
    _write_route(tmp_path)
    route = load_project_knowledge_route(
        "demo",
        knowledge_root=tmp_path / "projects",
        verifier_root=tmp_path,
        environ={},
    )
    target = tmp_path / "impl" / "projects" / "demo" / "project.yaml"
    target.parent.mkdir(parents=True)
    human_config = "schema_version: 1\n# human-owned decisions stay in the proposal\n"
    target.write_text(human_config, encoding="utf-8")

    candidate = project_config_proposal_candidate(route, target)

    assert candidate == human_config


def test_update_accept_requires_current_file_hash_and_sealed_current_state(tmp_path: Path) -> None:
    proposal_dir, _status, _manifest = _proposal(tmp_path)
    target = tmp_path / "impl" / "projects" / "demo" / "project.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("human: decision\n", encoding="utf-8")
    manifest = seal_project_config_proposal(proposal_dir, root=tmp_path)
    candidate_hash = manifest["candidate"]["sha256"]
    current_hash = hashlib.sha256(target.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="explicit update approval"):
        accept_project_config_proposal(
            proposal_dir,
            expected_hash=candidate_hash,
            root=tmp_path,
            update=True,
            expected_current_hash="0" * 64,
        )

    accepted = accept_project_config_proposal(
        proposal_dir,
        expected_hash=candidate_hash,
        root=tmp_path,
        update=True,
        expected_current_hash=current_hash,
    )
    assert "accepted_proposal_sha256" in accepted.read_text(encoding="utf-8")


def test_failed_proposal_validation_blocks_accept(tmp_path: Path) -> None:
    proposal_dir, _status, _manifest = _proposal(tmp_path)
    candidate_path = proposal_dir / "project.yaml"
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    candidate["runtime"]["ready"] = []
    candidate_path.write_text(
        yaml.safe_dump(candidate, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    manifest = seal_project_config_proposal(proposal_dir, root=tmp_path)

    assert manifest["validation"]["status"] == "failed"
    with pytest.raises(ValueError, match="validation has not passed"):
        accept_project_config_proposal(
            proposal_dir,
            expected_hash=manifest["candidate"]["sha256"],
            root=tmp_path,
        )
