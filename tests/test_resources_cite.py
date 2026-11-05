import json

import pytest

from impl.core.resources import DIRECTORY, META_PREFIX, Address, ResourceTable, Role, TYPES, cite

BODY = {"name": "backend.policy.search", "kind": "tool_calls",
        "fields": {"input": {"status": "available", "value": {"query": "伏云平"}},
                   "output": {"status": "available", "value": {"polno": "P260922000005855", "holder": "伏云平",
                                                               "status": "交费有效"}}}}
ADDR = "trace://turn1/records/observations/15"
OUTPUT = ADDR + "/fields/output"
ROLES = {"tool_execution": {"input": ["input"], "output": ["output"]}}
IN, OUT = Role("field", "input", ("input",)), Role("field", "output", ("output",))


@pytest.fixture
def table():
    t = ResourceTable()
    t.mount(ADDR, "record_set", BODY, name="turn1/records/observations/15", title="backend.policy.search",
            meta={META_PREFIX + "roles": ROLES})
    return t


def run(table, quote, *, seen=None, scope=None, uri=ADDR, view="tool_execution"):
    return cite(table, uri, quote, seen={ADDR: [BODY]} if seen is None else seen, scope=scope, view=view)


def test_address_parse_and_parent():
    a = Address.parse(ADDR)
    assert (a.scheme, a.path, str(a)) == ("trace", "turn1/records/observations/15", ADDR)
    assert str(a.parent()) == "trace://turn1/records/observations"
    for bad in ["turn1/records/observations/15", ADDR + "#/fields/output"]:
        with pytest.raises(ValueError):
            Address.parse(bad)


def test_mount_builds_mcp_descriptor(table):
    d = table.get(ADDR).descriptor
    text = TYPES["record_set"].text(BODY)
    assert (str(d.uri), d.name, d.title, d.mimeType, d.size) == (
        ADDR, "turn1/records/observations/15", "backend.policy.search", "application/json", len(text.encode()))
    assert d.meta == {META_PREFIX + "roles": ROLES, META_PREFIX + "type": "record_set"}
    assert table.list() == [d]


def test_mount_rejections(table):
    for args in [(ADDR, "record_set", {}), ("trace://x", "nope", {}),
                 ("trace://turn1/records", "record_set", {}),                 # 已是目录
                 (OUTPUT, "record_set", {}),                                   # 上级已是直接资源
                 ("trace://a b", "record_set", {})]:                           # 不合 RFC 3986
        with pytest.raises(ValueError):
            table.mount(*args, name="x")


def test_templates_declared_by_type(table):
    [t] = table.templates()
    assert (t.uriTemplate, t.mimeType) == ("trace://{+record}/fields/{field}", "application/json")


def test_read_direct_template_and_directory_like_mcp(table):
    [whole] = table.read(ADDR).contents
    assert (str(whole.uri), whole.mimeType, whole.text) == (ADDR, "application/json", TYPES["record_set"].text(BODY))
    [field] = table.read(OUTPUT).contents
    assert str(field.uri) == OUTPUT and field.text == json.dumps(BODY["fields"]["output"], ensure_ascii=False, sort_keys=True)
    assert field.text in whole.text                                          # 字段的文本就是整条记录里那一段
    [folder] = table.read("trace://turn1/records").contents
    assert folder.mimeType == DIRECTORY
    assert json.loads(folder.text) == [{"uri": "trace://turn1/records/observations", "name": "observations",
                                        "mimeType": DIRECTORY}]
    for missing in ["trace://turn9", ADDR + "/fields/nope", ADDR + "/other"]:
        with pytest.raises(LookupError):
            table.read(missing)


def test_record_level_quote_in_both_ends_passes_and_reports_both_roles(table):
    r = run(table, "伏云平")
    assert r.ok and r.block == ADDR and r.roles == (IN, OUT)
    assert {x.node for x in r.regions} == {"/fields/input/value/query", "/fields/output/value/holder"}


def test_field_level_quote_lands_on_that_end_only(table):
    r = run(table, "伏云平", uri=OUTPUT)
    assert r.ok and r.roles == (OUT,) and [x.node for x in r.regions] == ["/fields/output/value/holder"]
    assert run(table, "伏云平", uri=ADDR + "/fields/input").roles == (IN,)


def test_region_maps_to_canonical_text(table):
    r = run(table, '"polno": "P260922000005855"', uri=OUTPUT)
    [x] = r.regions
    assert x.node == "/fields/output/value/polno" and not x.seen_only
    assert TYPES["record_set"].extract(table.get(ADDR), x.start, x.end) == '"polno": "P260922000005855"'


def test_record_attribute_is_citable(table):
    r = run(table, "backend.policy.search")
    assert r.ok and r.roles == (Role("attribute"),)


def test_role_without_view_merges_all_views(table):
    assert run(table, "交费有效", view=None).roles == (OUT,)
    assert run(table, "交费有效", view="context_memory").roles == (Role("field", "output", ()),)


def test_repeats_inside_one_resource_all_pass(table):
    seen = {**BODY, "fields": {**BODY["fields"], "output": {"status": "available", "value": {"a": "重复值", "b": "重复值"}}}}
    r = run(table, "重复值", uri=OUTPUT, seen={ADDR: [seen]})
    assert r.ok and len(r.regions) == 2 and r.roles == (OUT,)


def test_same_position_seen_twice_counts_once(table):
    assert len(run(table, "交费有效", seen={ADDR: [BODY, BODY]}).regions) == 1


def test_rejections_in_order(table):
    assert run(table, "x", uri="turn1/records/observations/15").reason == "no_address"   # 只收完整地址
    assert run(table, "x", uri="trace://turn1/records/observations/99").reason == "no_address"
    assert run(table, "x", uri=ADDR + "/fields/nope").reason == "no_address"
    assert run(table, "交费有效", seen={}).reason == "not_seen"
    assert run(table, "交费有效", scope=set()).reason == "out_of_scope"
    miss = run(table, "P260922000005855 已失效")
    assert miss.reason == "not_found" and "P260922000005855" in miss.hint
    other = run(table, "交费有效", uri=ADDR + "/fields/input")                       # 原文在别的字段
    assert other.reason == "not_found" and "/fields/output" in other.hint


def test_preview_seen_version_marks_seen_only(table):
    preview = {**BODY, "fields": {**BODY["fields"], "output": {"status": "available",
               "value": "〔预览，全文 80 字〕{\"holder\": \"伏云平\", \"polno\": \"P26092200000…"}}}
    r = run(table, "〔预览", seen={ADDR: [preview]})
    assert r.ok and r.regions[0].seen_only
    assert run(table, "交费有效", seen={ADDR: [preview]}).reason == "not_found"  # 没看到的部分不能引
