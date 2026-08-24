import json
from pathlib import Path

from impl.core.schema.investigation_judge import (
    AUTHORITY_REPORT_SCHEMA_VERSION,
    load_authority_investigation_report,
    load_judge_contract,
    render_authority_report_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".agents/skills/draft/reference/investigation/judge/docs"


def test_judge_contract_uses_current_shape():
    raw = json.loads((BASE / "judge-investigation-contract.json").read_text())
    assert "authority_analyses" not in raw
    load_judge_contract(BASE / "judge-investigation-contract.json")


def test_authority_report_uses_materials_and_coverage_gaps():
    raw = json.loads((BASE / "authority-investigation-report.json").read_text())
    report = load_authority_investigation_report(BASE / "authority-investigation-report.json")
    assert report.schema_version == AUTHORITY_REPORT_SCHEMA_VERSION == 2
    assert report.materials
    assert report.coverage_gaps
    assert "findings" not in raw


def test_authority_report_markdown_is_deterministic_render():
    report = load_authority_investigation_report(BASE / "authority-investigation-report.json")
    expected = (BASE / "authority-investigation-report.md").read_text()
    assert render_authority_report_markdown(report) == expected


def test_draft_skill_requires_key_index_simulation_then_loop_before_solidify():
    skill = (ROOT / ".agents/skills/draft/SKILL.md").read_text()
    section = skill.split("### Collection Index 实验闭环", 1)[1].split("## Solidify", 1)[0]
    assert "frozen simulation probes" in section
    assert "deterministic Search→Load comparison" in section
    assert "最终选择以 Loop 的端到端效果为准" in section
    assert "只有模拟测试与 Loop 都证明合格" in section
    assert "expected trace" in section
    assert "完整 Collection 注入" in section
    assert "不得为通过结构门禁提前登记或 Solidify" in section
    assert "Investigation Readiness" in section
    assert "Simulation Readiness" in section
    assert "Selection Readiness" in section
    assert "--phase investigate" in section
    assert "--phase simulation" in section
    assert "--phase selection" in section
    assert "--require-selected" in section
    assert "完整 Index/Builder/projection" in section
    assert "holdout 必须失效" in section
    assert "不全局规定融合算法" in section


def test_draft_map_keeps_unproven_key_indexes_out_of_formal_assets():
    mapping = (ROOT / ".agents/skills/draft/MAP.md").read_text()
    section = mapping.split("## Key-Index 候选实验", 1)[1].split("## Active loop 与 restart", 1)[0]
    assert "证明前是 Draft 候选" in section
    assert "只有 `--phase selection`" in section
    assert "SearchHit 是导航结果" in section
    assert "channel consideration" in section
    assert "不强制实现不适用的 embedding 或 rerank" in section
    assert "holdout 不得" in section
    assert "--phase selection" in section
