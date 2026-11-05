import json

from impl.core.axis_loop.text import _normalize, dump
from impl.core.resources.text import QUOTES, closest, find_all, normalize_map, render, smallest

VALUE = {"name": "backend.policy.search", "fields": {"output": {"status": "available",
         "value": {"polno": "P260922000005855", "status": "交费有效", "list": [1, "二", None, True]}}},
         "z": "带\n换行与 \"引号\""}


def test_render_is_byte_identical_to_dump():
    text, _ = render(VALUE)
    assert text == dump(VALUE) == json.dumps(VALUE, ensure_ascii=False, sort_keys=True)


def test_regions_point_at_their_text():
    text, spans = render(VALUE)
    by = {(s.pointer, s.member): s for s in spans}
    value = by[("/fields/output/value/polno", False)]
    assert text[value.start:value.end] == '"P260922000005855"'
    member = by[("/fields/output/value/polno", True)]
    assert text[member.start:member.end] == '"polno": "P260922000005855"'
    assert text[by[("", False)].start:by[("", False)].end] == text
    assert text[by[("/fields/output/value/list/1", False)].start:by[("/fields/output/value/list/1", False)].end] == '"二"'


def test_normalize_map_matches_axis_loop_normalize():
    for sample in [dump(VALUE), 'a\\nb \\\\t c\\"d', "  x\ty\n", "\\\\\\r"]:
        norm, index = normalize_map(sample)
        assert norm == _normalize(sample).translate(QUOTES)
        assert all(sample[i] == ch for i, ch in zip(index, norm))


def test_find_all_tolerates_whitespace_and_escapes_and_reports_every_hit():
    text, spans = render(VALUE)
    [(start, end)] = find_all('"polno":"P260922000005855"', text)
    assert smallest(spans, start, end).pointer == "/fields/output/value/polno"
    assert len(find_all("status", text)) == 2
    assert find_all('带换行与"引号"', text)  # 原文里是转义的换行与引号
    assert find_all("", text) == []
    assert find_all("带换行与“引号”", text)  # 中文弯引号与直引号视为相同


def test_closest_finds_the_longest_shared_piece():
    text, _ = render(VALUE)
    start, end = closest("保单 P260922000005855 交费", text)
    assert "P260922000005855" in text[start:end]
