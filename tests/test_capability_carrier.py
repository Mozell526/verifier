from __future__ import annotations

from impl.core.capability_carrier import (
    CARRY_NO,
    CARRY_UNDECIDABLE,
    CARRY_YES,
    CarrierReading,
    PLACEMENT_CANNOT,
    PLACEMENT_UNCLEAR,
    PLACEMENT_WRONG,
    RECOG_UNMAPPED,
    RECOG_UNSUPPORTED,
    CapabilityCarrier,
    attach_row_placements,
    collect_report_errors,
    evaluate_reading,
    map_placement,
    parse_mapper_payload,
    place_not_fulfilled_payload,
    resolve_carrier,
    unmapped_verdict,
    validate_placements,
)


SNAPSHOT = {
    "fields": {
        "searchClientName": {
            "operators": ["MATCH", "EQ"],
            "enums": [],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
        },
        "policyDate": {
            "operators": ["EXISTS"],
            "enums": [],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
        },
        "deadField": {
            "operators": ["EQ"],
            "enums": ["A"],
            "is_supported": False,
            "governed": True,
            "source": "capability_manifest",
        },
        "customerUnredeemedPoints": {
            "operators": ["GTE"],
            "enums": [],
            "is_supported": False,
            "governed": True,
            "source": "capability_manifest",
        },
        "policies_insure_date": {
            "operators": ["RANGE"],
            "enums": [],
            "is_supported": False,
            "governed": True,
            "source": "capability_manifest",
        },
        "customerReview": {
            "operators": ["MATCH"],
            "enums": [],
            "is_supported": False,
            "governed": True,
            "source": "capability_manifest",
        },
        "licensePlateNo": {
            "operators": ["MATCH"],
            "enums": [],
            "is_supported": False,
            "governed": True,
            "source": "capability_manifest",
        },
        "polNoInfo.plancodeinfo.abbrname": {
            "operators": ["MATCH"],
            "enums": ["金凤"],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
        },
    }
}


def _nf(expectation_id: str, **expectation) -> dict:
    payload = {
        "expectation_id": expectation_id,
        "blocking": True,
        **expectation,
    }
    return {
        "overall_fulfillment": {"status": "not_fulfilled"},
        "business_expectations": [payload],
        "fulfillment_assessments": [
            {"expectation_id": expectation_id, "status": "not_fulfilled"}
        ],
    }


def _fixed_mapper(payload: dict):
    def mapper(_expectation, _snapshot):
        return payload
    return mapper


def _place(expectation_id: str, mapper_payload: dict, **expectation) -> dict:
    return place_not_fulfilled_payload(
        _nf(expectation_id, **expectation),
        SNAPSHOT,
        mapper=_fixed_mapper(mapper_payload),
    )


def test_unknown_reading_field_cannot_become_unclear() -> None:
    verdict = evaluate_reading(CarrierReading(field="licensePlate"), SNAPSHOT)
    assert verdict.carry == CARRY_UNDECIDABLE
    assert verdict.gap_kind == "工具失败"
    try:
        map_placement("not_fulfilled", verdict)
    except ValueError as exc:
        assert "归位失败" in str(exc)
    else:
        raise AssertionError("GAP_TOOL must not map to 说不清")


def test_unmapped_with_nearest_is_cannot() -> None:
    verdict = unmapped_verdict(
        [{
            "surface": "天气",
            "nearest": [{"field": "searchClientName", "why": "姓名不是天气"}],
        }],
        SNAPSHOT,
    )
    assert verdict.carry == CARRY_NO
    assert verdict.recognition == RECOG_UNMAPPED
    assert map_placement("not_fulfilled", verdict)["placement"] == PLACEMENT_CANNOT


def test_missing_operator_is_cannot() -> None:
    verdict = evaluate_reading(
        CarrierReading(field="policyDate", operator="BETWEEN"), SNAPSHOT
    )
    assert verdict.carry == CARRY_NO


def test_supported_false_is_cannot() -> None:
    verdict = evaluate_reading(CarrierReading(field="deadField", value="A"), SNAPSHOT)
    assert verdict.carry == CARRY_NO
    assert verdict.recognition == RECOG_UNSUPPORTED


def test_carried_reading_is_wrong_when_nf() -> None:
    verdict = evaluate_reading(
        CarrierReading(field="searchClientName", operator="MATCH"), SNAPSHOT
    )
    assert verdict.carry == CARRY_YES
    assert map_placement("not_fulfilled", verdict)["placement"] == PLACEMENT_WRONG
    assert map_placement("fulfilled", verdict) is None


def test_mixed_alternatives_are_ambiguity() -> None:
    verdict = resolve_carrier(
        [
            [CarrierReading(field="searchClientName")],
            [CarrierReading(field="deadField")],
        ],
        SNAPSHOT,
    )
    assert verdict.carry == CARRY_UNDECIDABLE
    assert verdict.gap_kind == "口径分歧"
    assert map_placement("not_fulfilled", verdict)["placement"] == PLACEMENT_UNCLEAR


def test_place_skips_non_nf_and_does_not_rewrite_axis1() -> None:
    spec = {"authority": {"enabled_scopes": ["capability_carrier"]}}
    row = {
        "case_key": "c1",
        "current": {"overall_fulfillment": {"status": "fulfilled"}},
        "draft": {
            "overall_fulfillment": {"status": "not_fulfilled"},
            "business_expectations": [
                {"expectation_id": "core", "blocking": True, "expected_outcome": "searchClientName"}
            ],
            "fulfillment_assessments": [
                {"expectation_id": "core", "status": "not_fulfilled"}
            ],
        },
    }
    carrier = CapabilityCarrier(
        SNAPSHOT,
        mapper=_fixed_mapper({
            "process_only": False,
            "alternatives": [{"readings": [{"field": "searchClientName", "operator": "MATCH"}]}],
            "unmapped": [],
        }),
    )
    attach_row_placements(spec, row, SNAPSHOT, carrier=carrier)
    assert row["draft"]["overall_fulfillment"]["status"] == "not_fulfilled"
    assert row["capability_carrier"]["current"]["applicable"] is False
    assert row["capability_carrier"]["draft"]["placements"][0]["placement"] == PLACEMENT_WRONG
    assert validate_placements(row, SNAPSHOT) == []


def test_snapshot_from_manifest_is_order_stable() -> None:
    from impl.core.capability_carrier import snapshot_from_capability_manifest, snapshot_id

    first = snapshot_from_capability_manifest({
        "clientAge": {"operators": ["LT", "GT"], "enums": ["B", "A"]},
        "searchClientName": {"operators": {"MATCH", "EQ"}},
    })
    second = snapshot_from_capability_manifest({
        "searchClientName": {"operators": ["EQ", "MATCH"]},
        "clientAge": {"operators": ["GT", "LT"], "enums": ["A", "B"]},
    })
    assert snapshot_id(first) == snapshot_id(second)
    assert first["fields"]["clientAge"]["enums"] == ["A", "B"]


def test_closed_space_missing_dimension_is_cannot() -> None:
    report = _place(
        "weather",
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "天气",
                "nearest": [{"field": "searchClientName", "why": "姓名不表达天气"}],
            }],
        },
        expected_outcome="天气",
    )
    assert report["placements"][0]["placement"] == PLACEMENT_CANNOT
    assert report["placements"][0]["recognition"] == RECOG_UNMAPPED
    assert "天气" in report["placements"][0]["reason"]


def test_extract_failure_is_placement_error() -> None:
    report = _place(
        "done",
        {"process_only": False, "alternatives": [], "unmapped": []},
        expected_outcome="按要求完成处理",
    )
    assert report["placements"] == []
    assert report["errors"][0]["stage"] == "mapper"
    assert report["errors"][0]["reason"] == "读法抽取重试耗尽"


def test_snapshot_unavailable_is_placement_error() -> None:
    report = place_not_fulfilled_payload(
        _nf("x", expected_outcome="按车牌号筛选"),
        {"fields": None},
        mapper=_fixed_mapper({"process_only": True, "alternatives": [], "unmapped": []}),
    )
    assert report["placements"] == []
    assert report["errors"][0]["stage"] == "snapshot"


def test_structured_value_and_match_mode_are_accepted() -> None:
    from impl.core.capability_carrier import _mapper_output_spec
    from impl.core.structured_output import validate_output

    snapshot = {
        "fields": {
            "clientAge": {
                "operators": ["RANGE", "GTE", "LTE"],
                "enums": [],
                "is_supported": True,
                "governed": True,
                "source": "capability_manifest",
            },
            "clientMobile": {
                "operators": ["MATCH"],
                "enums": [],
                "is_supported": True,
                "governed": True,
                "source": "capability_manifest",
            },
            "policies_insure_date": SNAPSHOT["fields"]["policies_insure_date"],
            "searchClientName": SNAPSHOT["fields"]["searchClientName"],
        }
    }
    payloads = [
        {
            "process_only": False,
            "alternatives": [{"readings": [
                {"field": "clientAge", "value": {"min": 18, "max": 18}, "operator": "RANGE"},
            ]}],
            "unmapped": [],
        },
        {
            "process_only": False,
            "alternatives": [{"readings": [
                {"field": "policies_insure_date", "value": ["2025-06-01", "2025-06-30"], "operator": "RANGE"},
            ]}],
            "unmapped": [],
        },
        {
            "process_only": False,
            "alternatives": [{"readings": [
                {"field": "searchClientName", "value": 3125, "operator": "MATCH"},
            ]}],
            "unmapped": [],
        },
        {
            "process_only": False,
            "alternatives": [{"readings": [
                {"field": "clientMobile", "value": "158", "operator": {"match_mode": "prefix"}},
            ]}],
            "unmapped": [],
        },
        {
            "process_only": False,
            "alternatives": [{"readings": [
                {"field": "clientMobile", "value": "5078", "operator": "MATCH", "match_mode": "suffix"},
            ]}],
            "unmapped": [],
        },
    ]
    spec = _mapper_output_spec()
    for payload in payloads:
        assert validate_output(payload, spec) == []

    age = parse_mapper_payload(payloads[0], snapshot)[0][0][0]
    assert age.value == "18~18"
    assert age.operator == "RANGE"
    assert evaluate_reading(age, snapshot).carry == CARRY_YES

    date = parse_mapper_payload(payloads[1], snapshot)[0][0][0]
    assert date.value == "2025-06-01~2025-06-30"
    assert evaluate_reading(date, snapshot).carry == CARRY_NO

    number = parse_mapper_payload(payloads[2], snapshot)[0][0][0]
    assert number.value == "3125"

    prefix = parse_mapper_payload(payloads[3], snapshot)[0][0][0]
    assert prefix.operator == "MATCH"
    assert prefix.match_mode == "prefix"
    assert evaluate_reading(prefix, snapshot).carry == CARRY_YES

    suffix = parse_mapper_payload(payloads[4], snapshot)[0][0][0]
    assert suffix.match_mode == "suffix"

    report = place_not_fulfilled_payload(
        _nf("mobile", expected_outcome="手机号前缀158"),
        snapshot,
        mapper=_fixed_mapper(payloads[3]),
    )
    assert report["placements"][0]["placement"] == PLACEMENT_WRONG
    assert not report.get("errors")

    null_value = {
        "process_only": False,
        "alternatives": [{"readings": [
            {"field": "searchClientName", "value": None, "operator": "MATCH"},
        ]}],
        "unmapped": [],
    }
    assert validate_output(null_value, spec) == []
    parsed_null = parse_mapper_payload(null_value, snapshot)
    assert parsed_null is not None
    assert parsed_null[0][0][0].value == ""


def test_enum_membership_checks_list_elements_not_joined_string() -> None:
    snapshot = {
        "fields": {
            "memberStatus": {
                "operators": ["CONTAINS", "MATCH"],
                "enums": ["潜客", "意向", "达标"],
                "is_supported": True,
                "governed": True,
                "source": "capability_manifest",
            },
        }
    }
    payload = {
        "process_only": False,
        "alternatives": [{"readings": [
            {"field": "memberStatus", "value": ["潜客", "意向"], "operator": "CONTAINS"},
        ]}],
        "unmapped": [],
    }
    reading = parse_mapper_payload(payload, snapshot)[0][0][0]
    assert reading.value == "潜客~意向"
    verdict = evaluate_reading(reading, snapshot)
    assert verdict.carry == CARRY_YES

    partial = parse_mapper_payload(
        {
            "process_only": False,
            "alternatives": [{"readings": [
                {"field": "memberStatus", "value": ["潜客", "新客"], "operator": "CONTAINS"},
            ]}],
            "unmapped": [],
        },
        snapshot,
    )[0][0][0]
    verdict = evaluate_reading(partial, snapshot)
    assert verdict.carry == CARRY_NO
    assert "新客" in verdict.reason and "潜客" not in verdict.reason


def test_parse_drops_fields_outside_catalog() -> None:
    parsed = parse_mapper_payload(
        {
            "process_only": False,
            "alternatives": [{"readings": [{"field": "notAField", "operator": "MATCH"}]}],
            "unmapped": [],
        },
        SNAPSHOT,
    )
    assert parsed is None


def test_unsupported_plate_from_mapper_is_cannot() -> None:
    report = _place(
        "按车牌号筛选目标客户",
        {
            "process_only": False,
            "alternatives": [{"readings": [{"field": "licensePlateNo"}]}],
            "unmapped": [],
        },
        expected_outcome="按车牌号贵C826N1筛选",
    )
    assert report["placements"][0]["placement"] == PLACEMENT_CANNOT
    assert report["placements"][0]["citations"][0]["ref"] == "licensePlateNo"


def test_conjunction_keeps_age_and_name_together() -> None:
    parsed = parse_mapper_payload(
        {
            "process_only": False,
            "alternatives": [{
                "readings": [
                    {"field": "searchClientName", "operator": "MATCH"},
                    {"field": "policyDate", "operator": "EXISTS"},
                ]
            }],
            "unmapped": [],
        },
        SNAPSHOT,
    )
    assert parsed is not None
    alternatives, unmapped = parsed
    assert unmapped == []
    assert {item.field for item in alternatives[0]} == {"searchClientName", "policyDate"}


def test_process_constraint_is_wrong_when_nf() -> None:
    report = _place(
        "extra",
        {"process_only": True, "alternatives": [], "unmapped": []},
        expected_outcome="不增加用户未表达的客户筛选条件",
    )
    assert report["placements"][0]["placement"] == PLACEMENT_WRONG


def test_round_cache_reuses_same_dimension() -> None:
    carrier = CapabilityCarrier(
        SNAPSHOT,
        mapper=_fixed_mapper({
            "process_only": False,
            "alternatives": [{"readings": [{"field": "searchClientName"}]}],
            "unmapped": [],
        }),
    )
    first = carrier.verdict_for({"expectation_id": "a", "expected_outcome": "searchClientName"})
    second = carrier.verdict_for({"expectation_id": "b", "expected_outcome": "searchClientName MATCH"})
    assert first is second
    assert len(carrier._cache) == 1


def test_replicate_majority_keeps_stable_answer() -> None:
    payloads = [
        {
            "process_only": False,
            "alternatives": [{"readings": [{"field": "searchClientName"}]}],
            "unmapped": [],
        },
        {
            "process_only": False,
            "alternatives": [{"readings": [{"field": "deadField"}]}],
            "unmapped": [],
        },
        {
            "process_only": False,
            "alternatives": [{"readings": [{"field": "searchClientName"}]}],
            "unmapped": [],
        },
    ]

    def mapper(_expectation, _snapshot):
        return payloads.pop(0)

    carrier = CapabilityCarrier(SNAPSHOT, mapper=mapper, replicate=True)
    verdict = carrier.verdict_for({"expectation_id": "x", "expected_outcome": "目标客户"})
    assert verdict.carry == CARRY_YES


def test_replicate_no_majority_is_ambiguity() -> None:
    payloads = [
        {
            "process_only": False,
            "alternatives": [{"readings": [{"field": "searchClientName"}]}],
            "unmapped": [],
        },
        {
            "process_only": False,
            "alternatives": [{"readings": [{"field": "deadField"}]}],
            "unmapped": [],
        },
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "天气",
                "nearest": [{"field": "searchClientName", "why": "姓名不是天气"}],
            }],
        },
    ]

    def mapper(_expectation, _snapshot):
        return payloads.pop(0)

    carrier = CapabilityCarrier(SNAPSHOT, mapper=mapper, replicate=True)
    verdict = carrier.verdict_for({"expectation_id": "x", "expected_outcome": "目标客户"})
    assert verdict.carry == CARRY_UNDECIDABLE
    assert verdict.gap_kind == "口径分歧"


def test_yes_signature_ignores_equivalent_fields() -> None:
    payloads = [
        {
            "process_only": False,
            "alternatives": [{"readings": [{"field": "searchClientName", "operator": "MATCH"}]}],
            "unmapped": [],
        },
        {
            "process_only": False,
            "alternatives": [{"readings": [{"field": "searchClientName", "operator": "EQ"}]}],
            "unmapped": [],
        },
    ]

    def mapper(_expectation, _snapshot):
        return payloads.pop(0)

    carrier = CapabilityCarrier(SNAPSHOT, mapper=mapper, replicate=True)
    verdict = carrier.verdict_for({"expectation_id": "x", "expected_outcome": "按姓名筛选"})
    assert verdict.carry == CARRY_YES


def test_unmapped_does_not_override_carried_alternative() -> None:
    report = _place(
        "buy",
        {
            "process_only": False,
            "alternatives": [{"readings": [{"field": "searchClientName", "operator": "MATCH"}]}],
            "unmapped": [{
                "surface": "当前代理人处",
                "nearest": [{"field": "searchClientName", "why": "姓名不是购买状态"}],
            }],
        },
        expected_outcome="筛选在当前代理人处买过保险的客户",
    )
    assert report["placements"][0]["placement"] == PLACEMENT_WRONG


def test_mapper_retries_then_places() -> None:
    calls = {"n": 0}

    def mapper(_expectation, _snapshot):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("insufficient_quota")
        return {"process_only": True, "alternatives": [], "unmapped": []}

    carrier = CapabilityCarrier(
        SNAPSHOT,
        mapper=mapper,
        replicate=False,
        mapper_retries=3,
        retry_backoff=(0, 0, 0),
    )
    verdict = carrier.verdict_for({"expectation_id": "x", "expected_outcome": "不增加未表达限制"})
    assert verdict.carry == CARRY_YES
    assert calls["n"] == 3


def test_mapper_exhausted_is_placement_error_and_not_cached() -> None:
    calls = {"n": 0}

    def mapper(_expectation, _snapshot):
        calls["n"] += 1
        raise RuntimeError("all endpoints cooling")

    carrier = CapabilityCarrier(
        SNAPSHOT,
        mapper=mapper,
        replicate=False,
        mapper_retries=2,
        retry_backoff=(0, 0),
    )
    first = carrier.place(_nf("x", expected_outcome="按车牌号筛选"))
    second = carrier.place(_nf("x", expected_outcome="按车牌号筛选"))
    assert first["placements"] == []
    assert first["errors"][0]["stage"] == "mapper"
    assert second["errors"][0]["stage"] == "mapper"
    assert calls["n"] == 4
    assert collect_report_errors(first)


def test_client_search_snapshot_has_locked_fields() -> None:
    from impl.core.capability_carrier import load_capability_snapshot
    from impl.core.project_loader import load_project

    snapshot = load_capability_snapshot(load_project("client_search"))
    fields = snapshot.get("fields") or {}
    for name in (
        "licensePlateNo",
        "policies_insure_date",
        "searchClientName",
        "pCategorys",
        "customerReview",
    ):
        assert name in fields


def test_snapshot_uses_spec_capability_manifest() -> None:
    from types import SimpleNamespace

    from impl.core.capability_carrier import load_capability_snapshot

    spec = SimpleNamespace(
        project_id="other",
        capability_manifest=lambda: {
            "foo": {"operators": ["EQ"], "enums": [], "is_supported": True},
        },
        value_mappings=lambda: {},
    )
    snapshot = load_capability_snapshot(spec)
    assert "foo" in (snapshot.get("fields") or {})


def test_snapshot_without_project_loader_stays_empty() -> None:
    from types import SimpleNamespace

    from impl.core.capability_carrier import load_capability_snapshot

    missing_fn = load_capability_snapshot(SimpleNamespace(project_id="QA"))
    assert missing_fn.get("fields") is None
    assert missing_fn.get("load_error") == "capability_snapshot missing"

    missing_project = load_capability_snapshot(SimpleNamespace(project_id="no_such_project"))
    assert missing_project.get("fields") is None
    assert missing_project.get("load_error") == "capability_snapshot missing"


def test_gold_points_cannot_when_space_refuses() -> None:
    cases = [
        ("I127", "customerUnredeemedPoints", "交付未兑换积分不低于60万的客户搜索条件"),
        ("I091", "policies_insure_date", "承保日期2008年8月条件"),
        ("I088", "customerReview", "七月盘客客户集合搜索交付"),
        ("I092", "licensePlateNo", "车牌号客户搜索核心交付"),
    ]
    for case_id, field, expected in cases:
        report = _place(
            case_id,
            {
                "process_only": False,
                "alternatives": [{"readings": [{"field": field}]}],
                "unmapped": [],
            },
            expected_outcome=expected,
        )
        assert report["placements"][0]["placement"] == PLACEMENT_CANNOT, case_id
        assert report["placements"][0]["recognition"] == RECOG_UNSUPPORTED, case_id


def test_gold_maturity_amount_is_unmapped_cannot() -> None:
    report = _place(
        "I058",
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "满期金金额",
                "nearest": [{
                    "field": "customerUnredeemedPoints",
                    "why": "未兑换积分不是满期金",
                }],
            }],
        },
        expected_outcome="按满期金金额筛选十万至三十万元客户",
    )
    assert report["placements"][0]["placement"] == PLACEMENT_CANNOT
    assert report["placements"][0]["recognition"] == RECOG_UNMAPPED
    assert any(
        cite.get("note") == "未兑换积分不是满期金"
        for cite in report["placements"][0]["citations"]
    )


def test_gold_same_role_dimension_is_stable() -> None:
    carrier = CapabilityCarrier(
        SNAPSHOT,
        mapper=_fixed_mapper({
            "process_only": False,
            "alternatives": [{"readings": [{"field": "deadField"}]}],
            "unmapped": [],
        }),
    )
    first = carrier.place(_nf("I102", expected_outcome="交付被保人今年18岁的可执行筛选条件"))
    second = carrier.place(_nf("I317", expected_outcome="筛选六岁至十二岁的被保险人客户"))
    assert first["placements"][0]["placement"] == second["placements"][0]["placement"] == PLACEMENT_CANNOT


def test_gold_name_or_product_both_carry_is_wrong() -> None:
    report = _place(
        "I211",
        {
            "process_only": False,
            "alternatives": [
                {"readings": [{"field": "searchClientName", "value": "金凤"}]},
                {"readings": [{"field": "polNoInfo.plancodeinfo.abbrname", "value": "金凤"}]},
            ],
            "unmapped": [],
        },
        expected_outcome="按姓名检索客户金凤",
    )
    assert report["placements"][0]["placement"] == PLACEMENT_WRONG


def test_gold_process_and_carried_name_are_wrong() -> None:
    report = _place(
        "圈客",
        {"process_only": True, "alternatives": [], "unmapped": []},
        expected_outcome="圈客非人名不得映射为姓名条件",
    )
    assert report["placements"][0]["placement"] == PLACEMENT_WRONG


def test_validate_accepts_error_in_place_of_placement() -> None:
    row = {
        "draft": _nf("x", expected_outcome="盘客"),
        "capability_carrier": {
            "current": {"applicable": False, "placements": [], "errors": []},
            "draft": {
                "applicable": True,
                "placements": [],
                "errors": [{
                    "expectation_id": "x",
                    "stage": "mapper",
                    "reason": "读法抽取重试耗尽",
                    "last_error": "quota",
                }],
            },
        },
    }
    assert validate_placements(row, SNAPSHOT) == []


def test_validate_rejects_tool_failure_unclear() -> None:
    row = {
        "draft": _nf("x", expected_outcome="盘客"),
        "capability_carrier": {
            "current": {"applicable": False, "placements": [], "errors": []},
            "draft": {
                "applicable": True,
                "placements": [{
                    "expectation_id": "x",
                    "placement": PLACEMENT_UNCLEAR,
                    "gap_kind": "工具失败",
                    "missing_material": "稳定的期望读法",
                    "citations": [],
                }],
                "errors": [],
            },
        },
    }
    errors = validate_placements(row, SNAPSHOT)
    assert any("工具失败" in item for item in errors)


def test_collect_report_errors_walks_loop_rows() -> None:
    errors = collect_report_errors({
        "rows": [{
            "capability_carrier": {
                "current": {
                    "placements": [],
                    "errors": [{"expectation_id": "a", "stage": "mapper", "reason": "读法抽取重试耗尽"}],
                },
                "draft": {"placements": [], "errors": []},
            }
        }]
    })
    assert [item["expectation_id"] for item in errors] == ["a"]


def test_validate_rejects_cannot_without_recognition() -> None:
    row = {
        "draft": _nf("x", expected_outcome="盘客"),
        "capability_carrier": {
            "current": {"applicable": False, "placements": []},
            "draft": {
                "applicable": True,
                "placements": [{
                    "expectation_id": "x",
                    "placement": PLACEMENT_CANNOT,
                    "reason": "空间缺维度 交付老客户",
                    "citations": [{"source": "capability_manifest", "ref": "fields"}],
                }],
            },
        },
    }
    errors = validate_placements(row, SNAPSHOT)
    assert any("做不了 missing self-recognition" in item for item in errors)


def test_validate_rejects_same_dimension_drift() -> None:
    row = {
        "draft": {
            "overall_fulfillment": {"status": "not_fulfilled"},
            "business_expectations": [
                {"expectation_id": "a", "blocking": True},
                {"expectation_id": "b", "blocking": True},
            ],
            "fulfillment_assessments": [
                {"expectation_id": "a", "status": "not_fulfilled"},
                {"expectation_id": "b", "status": "not_fulfilled"},
            ],
        },
        "capability_carrier": {
            "current": {"applicable": False, "placements": []},
            "draft": {
                "applicable": True,
                "placements": [
                    {
                        "expectation_id": "a",
                        "placement": PLACEMENT_CANNOT,
                        "recognition": RECOG_UNSUPPORTED,
                        "citations": [{"ref": "customerReview"}],
                    },
                    {
                        "expectation_id": "b",
                        "placement": PLACEMENT_WRONG,
                        "citations": [{"ref": "customerReview"}],
                    },
                ],
            },
        },
    }
    errors = validate_placements(row, SNAPSHOT)
    assert any("same-dimension placement drifted" in item for item in errors)


def test_carrier_text_marks_sections() -> None:
    from impl.core.capability_carrier import carrier_text

    text = carrier_text({
        "applicable": True,
        "placements": [
            {"expectation_id": "投保月份", "placement": PLACEMENT_CANNOT, "reason": "空间缺维度 投保时间"},
            {"expectation_id": "新客户限定", "placement": PLACEMENT_WRONG, "reason": "完整表达存在"},
            {
                "expectation_id": "中银保信",
                "placement": PLACEMENT_UNCLEAR,
                "reason": "读不出维度",
                "missing_material": "M1 登记",
            },
        ],
    })
    assert text == (
        "$做不了\n投保月份（空间缺维度 投保时间）\n\n"
        "$做错了\n新客户限定（完整表达存在）\n\n"
        "$说不清\n中银保信（读不出维度；缺M1 登记）"
    )
    assert carrier_text({"applicable": False, "placements": []}) == ""


RESCUE_SNAPSHOT = {
    "fields": {
        "searchClientName": {
            "operators": ["MATCH", "EQ"],
            "enums": [],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
            "description": "表示客户本人的人名",
            "aliases": ["姓名", "客户姓名"],
        },
        "polNoInfo.plancodeinfo.abbrname": {
            "operators": ["MATCH", "CONTAINS"],
            "enums": ["鑫盛", "鑫利", "平安福", "金凤", "财富"],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
            "description": "表示百万医疗业务词对应的一组固定产品简称",
            "aliases": ["少儿万能险"],
        },
        "polNoInfo.plancodeinfo.planfullname": {
            "operators": ["MATCH"],
            "enums": ["大连平安福宝计划(2022A)"],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
            "description": "保单投保险种全称",
            "aliases": [],
        },
        "customerReview": {
            "operators": ["MATCH"],
            "enums": [],
            "is_supported": False,
            "governed": True,
            "source": "capability_manifest",
            "description": "表示代理人的盘客业务动作或盘客月份，不表示客户添加日",
            "aliases": ["盘客", "盘客月份"],
        },
        "clientAge": {
            "operators": ["RANGE", "LTE", "GTE"],
            "enums": [],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
            "description": "表示客户本人年龄，不表示家庭成员年龄",
            "aliases": ["客户本人年龄", "年龄", "投保时间"],
        },
        "familyInfo.familyclientage": {
            "operators": ["RANGE", "LTE"],
            "enums": [],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
            "description": "表示家庭成员年龄，不表示客户本人年龄",
            "aliases": ["家庭成员年龄", "年龄"],
        },
        "customerUnredeemedPoints": {
            "operators": ["GTE"],
            "enums": [],
            "is_supported": False,
            "governed": True,
            "source": "capability_manifest",
            "description": "未兑换积分",
            "aliases": [],
        },
        "isBuyInsurance": {
            "operators": ["CONTAINS"],
            "enums": ["客户", "准客", "用户"],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
            "description": "客户类型；客户/准客=买过保险，用户=没有买过保险",
            "aliases": ["客户类型"],
        },
        "clientZodiac": {
            "operators": ["MATCH"],
            "enums": ["猴", "鼠", "牛"],
            "is_supported": False,
            "governed": True,
            "source": "capability_manifest",
            "description": "表示客户本人的十二生肖属相，不表示姓名",
            "aliases": ["十二生肖属相"],
        },
        "pajjMemberGradeInfo.pajjmemberstatus": {
            "operators": ["CONTAINS", "MATCH"],
            "enums": ["潜客", "意向", "达标"],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
            "description": "平安居家会员类型或状态",
            "aliases": [],
        },
        "annPremSegNum": {
            "operators": ["GT"],
            "enums": [],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
            "description": "表示年缴保费金额（大于），不表示总保费、产品总保额",
            "aliases": ["总保费", "年缴保费金额（大于）"],
            "negatives": ["总保费", "产品总保额"],
        },
        "pCategorys": {
            "operators": ["MATCH"],
            "enums": ["医疗保险", "定期寿险"],
            "is_supported": True,
            "governed": True,
            "source": "capability_manifest",
            "description": "客户持有一个明确的保险类别",
            "aliases": ["保险", "保险类别"],
        },
    }
}


def _rescue_place(expectation_id: str, mapper_payload: dict, **expectation) -> dict:
    return place_not_fulfilled_payload(
        _nf(expectation_id, **expectation),
        RESCUE_SNAPSHOT,
        mapper=_fixed_mapper(mapper_payload),
    )


def test_unmapped_enum_value_is_carried_not_missing_dimension() -> None:
    report = _rescue_place(
        "I566",
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "鑫盛、鑫利",
                "nearest": [{"field": "searchClientName", "why": "姓名不是产品"}],
            }],
        },
        expected_outcome="按或逻辑合并鑫盛与鑫利条件",
    )
    item = report["placements"][0]
    assert item["placement"] == PLACEMENT_WRONG
    assert any(cite.get("ref") == "polNoInfo.plancodeinfo.abbrname" for cite in item["citations"])


def test_missing_value_on_wrong_field_moves_to_enum_home() -> None:
    report = _rescue_place(
        "I049",
        {
            "process_only": False,
            "alternatives": [{"readings": [
                {"field": "polNoInfo.plancodeinfo.planfullname", "value": "平安福", "operator": "MATCH"},
            ]}],
            "unmapped": [],
        },
        expected_outcome="保留长期意外附加于平安福的关系",
    )
    item = report["placements"][0]
    assert item["placement"] == PLACEMENT_WRONG
    assert any(cite.get("ref") == "polNoInfo.plancodeinfo.abbrname" for cite in item["citations"])


def test_unmapped_alias_uses_unsupported_field_not_missing_dimension() -> None:
    report = _rescue_place(
        "I318",
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "盘客",
                "nearest": [{"field": "searchClientName", "why": "姓名不是盘客"}],
            }],
        },
        expected_outcome="交付盘客目标客户的可执行筛选",
    )
    item = report["placements"][0]
    assert item["placement"] == PLACEMENT_CANNOT
    assert item["recognition"] == RECOG_UNSUPPORTED
    assert item["citations"][0]["ref"] == "customerReview"


def test_unmapped_age_alias_is_carried() -> None:
    report = _rescue_place(
        "I057",
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "客户本人年龄小于17周岁",
                "nearest": [{"field": "searchClientName", "why": "姓名不是年龄"}],
            }],
        },
        expected_outcome="筛选客户本人年龄低于17周岁",
    )
    item = report["placements"][0]
    assert item["placement"] == PLACEMENT_WRONG
    assert any(cite.get("ref") == "clientAge" for cite in item["citations"])
    assert all(cite.get("ref") != "isBuyInsurance" for cite in item["citations"])


def test_true_missing_enum_value_stays_missing() -> None:
    report = _rescue_place(
        "I022",
        {
            "process_only": False,
            "alternatives": [{"readings": [
                {"field": "polNoInfo.plancodeinfo.abbrname", "value": "少儿万能险", "operator": "MATCH"},
            ]}],
            "unmapped": [],
        },
        expected_outcome="精确筛选持有少儿万能险的客户",
    )
    item = report["placements"][0]
    assert item["placement"] == PLACEMENT_CANNOT
    assert item["recognition"] == "missing_value"


def test_polluted_or_ambiguous_alias_does_not_invent_a_reading() -> None:
    report = _rescue_place(
        "weather",
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "天气",
                "nearest": [{"field": "searchClientName", "why": "姓名不是天气"}],
            }],
        },
        expected_outcome="按天气筛选",
    )
    item = report["placements"][0]
    assert item["placement"] == PLACEMENT_CANNOT
    assert item["recognition"] == RECOG_UNMAPPED

    age_only = _rescue_place(
        "age-short",
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "年龄",
                "nearest": [{"field": "searchClientName", "why": "姓名不是年龄"}],
            }],
        },
        expected_outcome="年龄",
    )
    assert age_only["placements"][0]["recognition"] == RECOG_UNMAPPED

    insure_time = _rescue_place(
        "insure-time",
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "投保时间",
                "nearest": [{"field": "searchClientName", "why": "姓名不是投保时间"}],
            }],
        },
        expected_outcome="投保时间",
    )
    assert insure_time["placements"][0]["recognition"] == RECOG_UNMAPPED
    assert all(
        cite.get("ref") != "clientAge"
        for cite in insure_time["placements"][0]["citations"]
    )

    hijack = _rescue_place(
        "zodiac",
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "客户属相为猴",
                "nearest": [{"field": "searchClientName", "why": "姓名不是属相"}],
            }],
        },
        expected_outcome="按客户属相猴筛选",
    )
    assert hijack["placements"][0]["placement"] == PLACEMENT_CANNOT
    assert all(
        cite.get("ref") != "isBuyInsurance"
        for cite in hijack["placements"][0]["citations"]
    )

    for surface, forbidden in (
        ("高潜客户", "pajjMemberGradeInfo.pajjmemberstatus"),
        ("财富分群", "polNoInfo.plancodeinfo.abbrname"),
        ("总保费超过600000元", "annPremSegNum"),
        ("团体险对应的保险类别或投保险种", "pCategorys"),
    ):
        report = _rescue_place(
            surface,
            {
                "process_only": False,
                "alternatives": [],
                "unmapped": [{
                    "surface": surface,
                    "nearest": [{"field": "searchClientName", "why": "姓名不是该维"}],
                }],
            },
            expected_outcome=surface,
        )
        item = report["placements"][0]
        assert item["placement"] == PLACEMENT_CANNOT, (surface, item)
        if surface == "团体险对应的保险类别或投保险种":
            assert item["recognition"] in {RECOG_UNMAPPED, "missing_value"}, item
        else:
            assert item["recognition"] == RECOG_UNMAPPED, surface
            assert all(cite.get("ref") != forbidden for cite in item["citations"]), surface

    go = _rescue_place(
        "go-review",
        {
            "process_only": False,
            "alternatives": [],
            "unmapped": [{
                "surface": "去盘客",
                "nearest": [{"field": "searchClientName", "why": "姓名不是盘客"}],
            }],
        },
        expected_outcome="去盘客",
    )
    assert go["placements"][0]["recognition"] == RECOG_UNSUPPORTED
    assert go["placements"][0]["citations"][0]["ref"] == "customerReview"


def _place_on(snapshot: dict, mapper_payload: dict, expectation_id: str = "x") -> dict:
    return place_not_fulfilled_payload(
        _nf(expectation_id, expected_outcome=expectation_id),
        snapshot,
        mapper=_fixed_mapper(mapper_payload),
    )


def test_lexicon_unsupported_term_beats_unmapped() -> None:
    snapshot = {
        **RESCUE_SNAPSHOT,
        "lexicon": [{
            "term": "盘客",
            "aliases": ["去盘客"],
            "field": "customerReview",
            "status": "unsupported",
        }],
    }
    report = _place_on(snapshot, {
        "process_only": False,
        "alternatives": [],
        "unmapped": [{
            "surface": "5月盘客客户",
            "nearest": [{"field": "searchClientName", "why": "姓名不是盘客"}],
        }],
    })
    item = report["placements"][0]
    assert item["placement"] == PLACEMENT_CANNOT
    assert item["recognition"] == RECOG_UNSUPPORTED
    assert item["citations"][0]["ref"] == "customerReview"


def test_lexicon_missing_term_stays_cannot() -> None:
    snapshot = {
        **RESCUE_SNAPSHOT,
        "lexicon": [{
            "term": "圈客",
            "aliases": ["去圈客"],
            "field": "",
            "status": "missing",
            "note": "目录无圈客维度",
        }],
    }
    report = _place_on(snapshot, {
        "process_only": False,
        "alternatives": [],
        "unmapped": [{
            "surface": "去圈客",
            "nearest": [{"field": "searchClientName", "why": "姓名不是圈客"}],
        }],
    })
    item = report["placements"][0]
    assert item["placement"] == PLACEMENT_CANNOT
    assert item["recognition"] == RECOG_UNMAPPED
    assert "圈客" in item["reason"]


def test_lexicon_carried_term_is_wrong() -> None:
    snapshot = {
        **RESCUE_SNAPSHOT,
        "lexicon": [{
            "term": "客户本人年龄",
            "aliases": [],
            "field": "clientAge",
            "status": "carried",
        }],
    }
    report = _place_on(snapshot, {
        "process_only": False,
        "alternatives": [],
        "unmapped": [{
            "surface": "客户本人年龄小于17周岁",
            "nearest": [{"field": "searchClientName", "why": "x"}],
        }],
    })
    item = report["placements"][0]
    assert item["placement"] == PLACEMENT_WRONG
    assert any(cite.get("ref") == "clientAge" for cite in item["citations"])


def test_client_search_snapshot_includes_lexicon() -> None:
    from impl.core.capability_carrier import catalog_prompt, load_capability_snapshot
    from impl.core.project_loader import load_project

    snapshot = load_capability_snapshot(load_project("client_search"))
    terms = {item["term"] for item in snapshot.get("lexicon") or []}
    assert {"盘客", "圈客", "属相", "满期金"} <= terms
    prompt = catalog_prompt(snapshot)
    assert "盘客" in prompt and "圈客" in prompt


def test_axis2_assets_are_in_current_fingerprint() -> None:
    import sys
    from pathlib import Path

    from impl.core.project_loader import load_project

    spec = load_project("client_search")
    lexicon = spec.project_package_path() / "capability_lexicon.yaml"
    mapper = spec.verifier_root_path() / "impl" / "core" / "capability_carrier.py"
    assert lexicon.is_file()
    assert mapper.is_file()
    scripts = spec.verifier_root_path() / ".agents" / "skills" / "draft" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from fingerprints import current_fingerprint

    first = current_fingerprint(spec)
    original = lexicon.read_bytes()
    try:
        lexicon.write_bytes(original + b"\n# fingerprint-probe\n")
        second = current_fingerprint(spec)
    finally:
        lexicon.write_bytes(original)
    assert first != second


def test_client_search_axis2_frozen_nf() -> None:
    from impl.core.capability_carrier import load_capability_snapshot
    from impl.core.project_loader import load_project

    snapshot = load_capability_snapshot(load_project("client_search"))
    cases = [
        ("I088", {"process_only": False, "alternatives": [{"readings": [{"field": "customerReview"}]}], "unmapped": []}, PLACEMENT_CANNOT, RECOG_UNSUPPORTED, "customerReview"),
        ("I318", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "盘客", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_CANNOT, RECOG_UNSUPPORTED, "customerReview"),
        ("I069", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "去盘客", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_CANNOT, RECOG_UNSUPPORTED, "customerReview"),
        ("I114", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "5月盘客客户", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_CANNOT, RECOG_UNSUPPORTED, "customerReview"),
        ("I128", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "圈客", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_CANNOT, RECOG_UNMAPPED, None),
        ("I058", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "满期金金额范围为100000至300000元", "nearest": [{"field": "customerUnredeemedPoints", "why": "积分不是满期金"}]}]}, PLACEMENT_CANNOT, RECOG_UNMAPPED, None),
        ("I031", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "客户属相为猴", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_CANNOT, RECOG_UNSUPPORTED, "clientZodiac"),
        ("I060", {"process_only": False, "alternatives": [{"readings": [{"field": "licensePlateNo"}]}], "unmapped": []}, PLACEMENT_CANNOT, RECOG_UNSUPPORTED, "licensePlateNo"),
        ("I127", {"process_only": False, "alternatives": [{"readings": [{"field": "customerUnredeemedPoints"}]}], "unmapped": []}, PLACEMENT_CANNOT, RECOG_UNSUPPORTED, "customerUnredeemedPoints"),
        ("I056", {"process_only": False, "alternatives": [{"readings": [{"field": "is_life_insured"}]}], "unmapped": []}, PLACEMENT_CANNOT, RECOG_UNSUPPORTED, "is_life_insured"),
        ("I085", {"process_only": False, "alternatives": [{"readings": [{"field": "policies_insure_date"}]}], "unmapped": []}, PLACEMENT_CANNOT, RECOG_UNSUPPORTED, "policies_insure_date"),
        ("I022", {"process_only": False, "alternatives": [{"readings": [{"field": "polNoInfo.plancodeinfo.abbrname", "value": "少儿万能险", "operator": "MATCH"}]}], "unmapped": []}, PLACEMENT_CANNOT, "missing_value", "polNoInfo.plancodeinfo.abbrname"),
        ("I049", {"process_only": False, "alternatives": [{"readings": [{"field": "polNoInfo.plancodeinfo.planfullname", "value": "平安福", "operator": "MATCH"}]}], "unmapped": []}, PLACEMENT_WRONG, "", "polNoInfo.plancodeinfo.abbrname"),
        ("I566", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "鑫盛、鑫利", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_WRONG, "", "polNoInfo.plancodeinfo.abbrname"),
        ("I057", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "客户本人年龄小于17周岁", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_WRONG, "", "clientAge"),
        ("I338", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "保单总数量等于0", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_CANNOT, RECOG_UNSUPPORTED, "polNum"),
        ("I208", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "续收", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_CANNOT, RECOG_UNMAPPED, None),
        ("I326", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "团体险", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_CANNOT, RECOG_UNMAPPED, None),
        ("I584", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "财富分群", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_CANNOT, RECOG_UNMAPPED, None),
        ("I122", {"process_only": False, "alternatives": [], "unmapped": [{"surface": "高潜客户", "nearest": [{"field": "searchClientName", "why": "x"}]}]}, PLACEMENT_CANNOT, RECOG_UNMAPPED, None),
    ]
    for case_id, payload, placement, recognition, ref in cases:
        report = _place_on(snapshot, payload, case_id)
        assert not report.get("errors"), case_id
        item = report["placements"][0]
        assert item["placement"] == placement, (case_id, item)
        if recognition:
            assert item.get("recognition") == recognition, (case_id, item)
        if ref:
            assert any(cite.get("ref") == ref for cite in item.get("citations") or []), (case_id, item)
