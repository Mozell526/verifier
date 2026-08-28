"""资料系统 V1：槽位门禁、内容封口、binding 预算、material:// 引用。"""
from __future__ import annotations

import pytest

from impl.core import materials_store


SLOTS_YAML = """
slots:
  - slot_id: glossary
    title: 口径表
    description: judge 依据
    required: true
    roles: [judge]
  - slot_id: notes
    title: 补充说明
    required: false
    roles: [judge]
"""


@pytest.fixture
def demo_project(tmp_path, monkeypatch):
    root = tmp_path / "impl"
    (root / "projects" / "demo").mkdir(parents=True)
    (root / "data").mkdir(parents=True)
    (root / "projects" / "demo" / "materials.yaml").write_text(SLOTS_YAML, encoding="utf-8")
    monkeypatch.setattr(materials_store, "ROOT", root)
    return "demo"


def test_missing_required_slot_blocks(demo_project):
    with pytest.raises(ValueError, match="口径表"):
        materials_store.require_materials(demo_project)
    with pytest.raises(ValueError, match="必填资料槽位"):
        materials_store.binding_materials_for_role(demo_project, "judge")


def test_fill_slot_passes_gate_and_binds(demo_project):
    manifest = materials_store.save_material(
        demo_project, "glossary", content="字段A：含义A", title="口径表"
    )
    assert manifest["sha256"]
    materials_store.require_materials(demo_project)  # 不再抛错
    listing = materials_store.list_materials(demo_project)
    status = {slot["slot_id"]: slot["status"] for slot in listing["slots"]}
    assert status == {"glossary": "filled", "notes": "missing"}
    bound = materials_store.binding_materials_for_role(demo_project, "judge")
    assert len(bound) == 1
    assert bound[0]["content"] == "字段A：含义A"
    assert bound[0]["uri"] == "material://demo/glossary"


def test_binding_budget_enforced(demo_project):
    materials_store.save_material(demo_project, "glossary", content="x" * 20000)
    materials_store.save_material(demo_project, "notes", content="y" * 20000)
    with pytest.raises(ValueError, match="预算"):
        materials_store.binding_materials_for_role(demo_project, "judge")


def test_free_material_and_uri_resolution(demo_project):
    materials_store.save_material(demo_project, "doc-1", content="自由资料正文", title="文档一")
    listing = materials_store.list_materials(demo_project)
    assert [item["id"] for item in listing["free"]] == ["doc-1"]
    assert materials_store.resolve_material_uri("material://demo/doc-1") == "自由资料正文"
    materials_store.delete_material(demo_project, "doc-1")
    with pytest.raises(ValueError, match="不存在"):
        materials_store.resolve_material_uri("material://demo/doc-1")


def test_content_tamper_detected(demo_project):
    materials_store.save_material(demo_project, "glossary", content="原始内容")
    content_path = (
        materials_store.materials_root(demo_project) / "glossary" / materials_store.CONTENT_FILENAME
    )
    content_path.write_text("被绕过 API 手改的内容", encoding="utf-8")
    with pytest.raises(ValueError, match="哈希"):
        materials_store.read_content(demo_project, "glossary")
    with pytest.raises(ValueError, match="哈希"):
        materials_store.binding_materials_for_role(demo_project, "judge")


def test_path_traversal_rejected(demo_project):
    with pytest.raises(ValueError, match="非法"):
        materials_store.save_material("../evil", "x", content="c")
    with pytest.raises(ValueError, match="非法"):
        materials_store.delete_material(demo_project, "../evil")
    with pytest.raises(ValueError, match="格式"):
        materials_store.resolve_material_uri("material://demo/a/b")


def test_slot_declaration_validated(demo_project, monkeypatch):
    path = materials_store.ROOT / "projects" / "demo" / "materials.yaml"
    path.write_text("slots:\n  - slot_id: bad\n    fill: [teleport]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fill 不支持"):
        materials_store.load_slots(demo_project)


def test_capability_material_reference(demo_project):
    materials_store.save_material(demo_project, "cap-doc", content="能力口径全文……")
    from impl.projects.llm_probe.capability import resolve_capability

    text = resolve_capability({"capability": "material://demo/cap-doc"})
    assert text == "能力口径全文……"


def test_get_material_returns_body(demo_project):
    materials_store.save_material(demo_project, "glossary", content="字段A：含义A", title="口径表")
    loaded = materials_store.get_material(demo_project, "glossary")
    assert loaded["content"] == "字段A：含义A"
    assert loaded["id"] == "glossary"
    assert loaded["sha256"]
    with pytest.raises(ValueError, match="不存在"):
        materials_store.get_material(demo_project, "notes")


def test_batch_run_requires_materials(demo_project):
    from impl.core import pipeline

    with pytest.raises(ValueError, match="口径表"):
        pipeline.batch_run(demo_project, [{"id": "c1"}])
    empty = pipeline.batch_run("llm_probe", [])
    assert empty.total == 0


def test_material_content_resolver(demo_project):
    from impl.core.context.models import ContextUnitRecord
    from impl.core.context.resolvers import standard_content_resolver

    materials_store.save_material(demo_project, "glossary", content="resolver-body")
    record = ContextUnitRecord(
        id="u1",
        name="glossary",
        description="slot",
        content=None,
        content_ref="material://demo/glossary",
        project_id="demo",
        scope="project",
        roles=("judge",),
        unit_type="document",
        source_type="material",
    )
    text = standard_content_resolver().resolve("material://demo/glossary", record)
    assert text == "resolver-body"


def test_client_search_required_slot_is_filled():
    materials_store.require_materials("client_search")
    bound = materials_store.binding_materials_for_role("client_search", "judge")
    assert bound and bound[0]["id"] == "field_glossary"
    assert "clientAge" in bound[0]["content"]


def test_llm_probe_has_no_required_slots():
    assert materials_store.load_slots("llm_probe") == []
    materials_store.require_materials("llm_probe")


def test_edit_downgrades_investigation_provenance(demo_project):
    materials_store.save_material(
        demo_project, "glossary", content="调查原样内容",
        provenance={"source": "investigation", "detail": "rev abc123"},
    )
    # 同内容重存：provenance 原样保留
    kept = materials_store.save_material(demo_project, "glossary", content="调查原样内容")
    assert kept["provenance"] == {"source": "investigation", "detail": "rev abc123"}
    # 改内容：降级 derived + edited，出处保留
    edited = materials_store.save_material(demo_project, "glossary", content="人手改过的内容")
    assert edited["provenance"]["source"] == "derived"
    assert edited["provenance"]["edited"] is True
    assert edited["provenance"]["derived_from"] == "investigation"
    assert edited["provenance"]["detail"] == "rev abc123"
    # 纯上传资料改内容：不降级
    materials_store.save_material(demo_project, "notes", content="v1")
    plain = materials_store.save_material(demo_project, "notes", content="v2")
    assert plain["provenance"] == {"source": "user_upload"}


def test_stores_declaration(demo_project):
    path = materials_store.ROOT / "projects" / "demo" / "materials.yaml"
    assert materials_store.load_stores(demo_project) == []
    path.write_text("stores:\n  - capability_map\n", encoding="utf-8")
    assert materials_store.load_stores(demo_project) == ["capability_map"]
    assert materials_store.load_slots(demo_project) == []  # slots 变为可选
    path.write_text("stores:\n  - unknown_store\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stores 不支持"):
        materials_store.load_stores(demo_project)


def test_overview_sections_declaration_driven():
    from impl.core.materials_overview import project_overview

    cs = project_overview("client_search")
    cs_kinds = [section["kind"] for section in cs["sections"]]
    assert "investigation" in cs_kinds
    assert "system_assets" in cs_kinds
    assert "capability_map" not in cs_kinds  # client_search 未声明 stores
    investigation = next(s for s in cs["sections"] if s["kind"] == "investigation")
    assert not investigation["editable"]
    judge_pkg = next(i for i in investigation["items"] if i["asset_id"] == "judge_investigation")
    assert judge_pkg["production_exists"] is True
    assert judge_pkg["manifest"] and judge_pkg["manifest"].get("source_revision")

    lp = project_overview("llm_probe")
    lp_kinds = [section["kind"] for section in lp["sections"]]
    assert "capability_map" in lp_kinds  # llm_probe 声明了 stores
    slots_section = next(s for s in lp["sections"] if s["kind"] == "slots")
    assert slots_section["slots"] == []


def test_asset_view_readonly_projection():
    from impl.core.materials_overview import asset_view

    view = asset_view("client_search", "judge_investigation")
    assert view["asset_kind"] == "investigation"
    assert view["manifest"].get("source_revision")
    assert view["files"], "调查包应展示文件清单"
    assert "content" in view  # overview.md
    with pytest.raises(ValueError, match="没有资产"):
        asset_view("client_search", "no-such-asset")


def test_asset_view_expands_business_source_evidence():
    """调查对象清单必须把被调查的业务源码文件逐份列出，不能只给计数。"""
    from impl.core.materials_overview import asset_view

    view = asset_view("client_search", "judge_investigation")
    evidence = view["evidence_refs"]
    business = [ref for ref in evidence if ref["scope"] == "business_source"]
    assert len(business) >= 10
    paths = {ref["path"] for ref in business}
    assert any("field_definitions_args.yaml" in path for path in paths)
    assert all(ref["source_revision"] for ref in business)
    assert evidence[0]["scope"] == "business_source", "业务源码证据应排在最前"
    artifacts = view["artifact_refs"]
    assert any("experiments/" in (ref["path"] or "") for ref in artifacts), \
        "冻结的 key-index 实验产物是包的一部分，必须出现在清单里"


def test_asset_file_opens_package_and_rejects_traversal():
    from impl.core.materials_overview import asset_file

    opened = asset_file("client_search", "judge_investigation", "artifact_package", "overview.md")
    assert "Judge investigation" in opened["content"]
    doc = asset_file("client_search", "judge_investigation", "project_package", "judge_boundary_protocals.md")
    assert doc["content"].strip()
    with pytest.raises(ValueError, match="越界"):
        asset_file("client_search", "judge_investigation", "artifact_package", "../../evaluation.md")
    with pytest.raises(ValueError, match="scope"):
        asset_file("client_search", "judge_investigation", "elsewhere", "overview.md")
    with pytest.raises(ValueError, match="不可达"):
        asset_file("client_search", "judge_investigation", "artifact_package", "no-such-file.md")
