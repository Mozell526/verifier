"""Policy Search 独立 Mock 需求规划。

只读取业务配置中的能力定义，不读取 golden query。覆盖标签由调用方写入独立
coverage manifest，不进入 MockCase 或 Judge 链路。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class MockDemand:
    demand_id: str
    scenario: str
    user_intent: str
    query: str
    contexts: List[Dict[str, str]] = field(default_factory=list)
    coverage: Dict[str, Any] = field(default_factory=dict)


_FIELD_VALUES = {
    "polno": "PX73194826",
    "plan_full_name": "康宁终身",
    "applicant_name": "陈晓华",
    "insurant_name": "周海宁",
    "applicant_phoneno": "13856781234",
    "insurant_phoneno": "13924681357",
    "applicant_card_no": "310101198805126842",
    "insurant_card_no": "440106199203174517",
}
_NUMBER_VALUES = {
    "pol_yr": (3, 8),
    "applicant_age": (35, 55),
    "insurant_age": (18, 45),
    "sum_ins": (300000, 800000),
    "frist_period_prem": (5000, 20000),
    "year_pay_prem": (10000, 50000),
    "agg_paid_prem": (50000, 300000),
    "agg_receive_dividend": (1000, 10000),
    "aldnw_take_etamt": (5000, 50000),
    "distance_cooling_off_end_days": (3, 10),
    "total_modal_prem": (3000, 15000),
    "agg_pay_cnt": (1, 3),
}
_DATE_VALUES = {
    "insure_date": ("2026年3月1日", "2026年6月30日"),
    "undwrt_date": ("2026年4月1日", "2026年7月31日"),
    "pol_effective_date_term": ("2026年1月1日", "2026年8月31日"),
    "matu_date": ("2027年1月1日", "2028年12月31日"),
    "security_period_end_date": ("2026年9月1日", "2027年3月31日"),
    "pol_annual_day": ("2026年8月1日", "2026年8月31日"),
    "surrender_date": ("2026年2月1日", "2026年5月31日"),
    "pay_to_day": ("2026年8月10日", "2026年8月25日"),
}
_GENERIC_TEXT_VALUES = ("安康", "福享")
_SURFACE_WRAPPERS = (
    ("terse", "{base}"),
    ("command", "麻烦帮我筛一下，{base}"),
    ("question", "手上有没有{base}？"),
)


def _enabled_fields(config: Dict[str, Any]) -> list[Dict[str, Any]]:
    return [dict(item) for item in config.get("fields") or [] if item.get("enabled")]


def _enum_values(config: Dict[str, Any]) -> Dict[str, list[Dict[str, Any]]]:
    return {
        str(item.get("field_id") or ""): list(item.get("values") or [])
        for item in config.get("enums") or []
        if item.get("field_id")
    }


def _display(field: Dict[str, Any]) -> str:
    aliases = [str(item) for item in field.get("aliases") or [] if str(item).strip()]
    return aliases[-1] if aliases else str(field.get("display_name") or field.get("id") or "")


def _format_number(value: int, field_id: str, variant: int) -> str:
    if field_id in {"sum_ins", "frist_period_prem", "year_pay_prem", "agg_paid_prem", "agg_receive_dividend", "aldnw_take_etamt", "total_modal_prem"}:
        if value >= 10000 and value % 10000 == 0:
            return f"{value // 10000}{'万' if variant % 2 == 0 else '万元'}"
        return f"{value}元"
    return str(value)


def _atomic_demands(config: Dict[str, Any]) -> list[MockDemand]:
    enums = _enum_values(config)
    demands: list[MockDemand] = []
    for index, field in enumerate(_enabled_fields(config), start=1):
        field_id = str(field["id"])
        label = _display(field)
        data_type = str(field.get("data_type") or "")
        variants: list[tuple[str, str, str]] = []
        if data_type == "NUMBER":
            low, high = _NUMBER_VALUES.get(field_id, (2, 8))
            variants = [
                (f"筛选{label}不少于{_format_number(low, field_id, index)}的保单", f"{label}至少{_format_number(low, field_id, index)}", "GTE"),
                (f"筛选{label}在指定范围内的保单", f"{label}{_format_number(low, field_id, index)}到{_format_number(high, field_id, index + 1)}之间的", "BETWEEN"),
            ]
        elif data_type == "DATE":
            low, high = _DATE_VALUES.get(field_id, ("2026年5月1日", "2026年8月31日"))
            variants = [
                (f"筛选{label}在{low}之后的保单", f"{label}{low}以后", "GTE"),
                (f"筛选{label}处于给定日期区间的保单", f"{label}从{low}到{high}的保单", "BETWEEN"),
            ]
        elif data_type == "ENUM":
            values = enums.get(field_id) or []
            first = values[0] if values else {"value": "是", "aliases": []}
            second = values[1] if len(values) > 1 else first
            first_surface = str((first.get("aliases") or [first.get("value")])[-1] or first.get("value") or "是")
            second_surface = str((second.get("aliases") or [second.get("value")])[-1] or second.get("value") or first_surface)
            variants = [
                (f"筛选{label}为{first_surface}的保单", f"找{first_surface}的保单", "EQ"),
                (f"筛选{label}属于多个指定值的保单", f"{first_surface}或者{second_surface}的保单", "IN"),
            ]
        else:
            value = _FIELD_VALUES.get(field_id, _GENERIC_TEXT_VALUES[index % len(_GENERIC_TEXT_VALUES)])
            short = value[-4:] if field_id in {"polno", "applicant_phoneno", "insurant_phoneno", "applicant_card_no", "insurant_card_no"} else value[:2]
            variants = [
                (f"按{label}中的指定文本筛选保单", f"{label}里带{short}的", "CONTAINS"),
                (f"按{label}尾部片段筛选保单", f"{label}尾号{short}的保单", "SUFFIX" if "SUFFIX" in field.get("allowed_operators", []) else "CONTAINS"),
            ]
        for variant, (intent, query, operator) in enumerate(variants, start=1):
            demands.append(MockDemand(
                demand_id=f"field-{index:02d}-{variant}",
                scenario="atomic_condition",
                user_intent=intent,
                query=query,
                coverage={"kind": "field", "field_ids": [field_id], "operator_family": operator, "surface_style": "work_phrase"},
            ))
    return demands


def _replacement_values(scene: Dict[str, Any]) -> list[str]:
    values: list[str] = []
    for name, spec in (scene.get("variables") or {}).items():
        raw = str(name)
        resolver = str((spec or {}).get("resolver") or "")
        if "month" in raw:
            values.append("9")
        elif "quarter" in raw:
            values.append("三")
        elif "year" in raw and "date" not in raw:
            values.append("3")
        elif "day" in raw:
            values.append("15")
        elif "amount" in raw or "prem" in raw or "money" in resolver:
            values.append("5")
        elif "age" in raw:
            values.append("45")
        elif "count" in raw or "cnt" in raw:
            values.append("2")
        elif "suffix" in raw:
            values.append("4826")
        elif "phone" in raw:
            values.append("6813")
        elif "card" in raw:
            values.append("4517")
        elif "name" in raw:
            values.append("陈晓华")
        elif "category" in raw or resolver == "enum":
            values.append("分红")
        elif resolver in {"integer", "number"}:
            values.append("3")
        elif resolver == "date":
            values.append("2026年9月1日")
        elif resolver == "text":
            values.append("康宁")
    return values or ["3"]


def _render_scene_example(scene: Dict[str, Any]) -> str:
    examples = [str(item).strip() for item in scene.get("examples") or [] if str(item).strip()]
    base = examples[0] if examples else f"{scene.get('dimension', '')}{scene.get('sub_dimension', '')}相关保单"
    base = _concretize_template_choices(base)
    return _fill_placeholders(base, scene).replace("险险类", "险类")


def _fill_placeholders(value: str, scene: Dict[str, Any]) -> str:
    fallbacks = iter(_replacement_values(scene) * 4)

    def replace(match: re.Match[str]) -> str:
        before = value[max(0, match.start() - 10):match.start()]
        after = value[match.end():match.end() + 10]
        if re.match(r"(?:元|万|万元)", after):
            return "5"
        if re.match(r"(?:岁|周岁)", after):
            return "45"
        if re.match(r"(?:天|日)", after):
            return "15"
        if re.match(r"个月|月", after):
            return "9"
        if re.match(r"季度", after):
            return "三"
        if re.match(r"年", after):
            return "3"
        if re.match(r"次", after):
            return "2"
        if re.match(r"(?:客户|投保人|被保人|姓名)", after):
            return "陈晓华"
        if re.match(r"险类", after):
            return "分红"
        if re.match(r"险种", after):
            return "康宁"
        if "尾" in before or "后" in before:
            return "4826"
        if re.match(r"(?:保单号|合同号|号码)", after):
            return "PX7319"
        return next(fallbacks, "3")

    return re.sub(r"x+|X+", replace, value)


def _concretize_template_choices(value: str) -> str:
    """把业务配置中的斜杠模板选项收敛成一条真实用户表达。"""
    text = str(value)
    for template, concrete in (
        ("近xx天内/xx个月/xx季度/半年内/xx年", "近15天内"),
        ("xx天内/xx个月/xx季度/半年内/xx年", "15天内"),
        ("近xx个月/xx季度/半年内/xx年", "近3个月"),
        ("本周/xx月/xx季度", "本周"),
        ("xx月/xx季度/半年内/xx年", "近3个月"),
        ("xx元/万以上", "xx万元以上"),
        ("xx元/万", "xx万元"),
        ("xx万/万以上", "xx万以上"),
    ):
        text = text.replace(template, concrete)
    return text.replace("/", "或")


def _scene_scenario(scene: Dict[str, Any], fields: Dict[str, Dict[str, Any]]) -> str:
    related = [str(item) for item in scene.get("related_fields") or []]
    if any(str(fields.get(item, {}).get("data_type") or "") == "DATE" for item in related):
        return "time_boundary"
    if any(str(fields.get(item, {}).get("data_type") or "") == "ENUM" for item in related):
        return "enum_alias"
    text = "".join(str(item) for item in scene.get("examples") or [])
    if "我" in text or "代理人" in text:
        return "agent_identity"
    return "surface_generalization"


def _scene_demands(config: Dict[str, Any]) -> list[MockDemand]:
    fields = {str(item["id"]): item for item in _enabled_fields(config)}
    demands: list[MockDemand] = []
    scenes = [dict(item) for item in config.get("scene_templates") or [] if item.get("enabled")]
    for index, scene in enumerate(scenes, start=1):
        base = _render_scene_example(scene)
        scenario = _scene_scenario(scene, fields)
        for style, wrapper in _SURFACE_WRAPPERS:
            clean_base = base.rstrip("。？?")
            if style == "command":
                clean_base = re.sub(r"(?:有哪些|有多少)$", "", clean_base)
            if style == "question" and re.search(r"(?:有哪些|有多少|是否|能否)$", clean_base):
                query = clean_base + "？"
            else:
                query = wrapper.format(base=clean_base)
            demands.append(MockDemand(
                demand_id=f"scene-{index:03d}-{style}",
                scenario=scenario,
                user_intent=f"筛选符合“{base}”所表达条件的保单",
                query=query,
                coverage={
                    "kind": "business_scene",
                    "scene_ids": [str(scene.get("template_id") or f"scene-{index}")],
                    "field_ids": [str(item) for item in scene.get("related_fields") or []],
                    "surface_style": style,
                },
            ))
    return demands


def _unsupported_demands(config: Dict[str, Any]) -> list[MockDemand]:
    demands: list[MockDemand] = []
    for index, scene in enumerate(config.get("unsupported_scenes") or [], start=1):
        examples = [str(item).strip() for item in scene.get("examples") or [] if str(item).strip()]
        template = _concretize_template_choices(examples[0] if examples else "本期不支持条件的保单")
        base = re.sub(r"x+|X+", "3", template)
        for style, wrapper in _SURFACE_WRAPPERS:
            clean_base = base.rstrip("。？?")
            if style == "command":
                clean_base = re.sub(r"(?:有哪些|有多少)$", "", clean_base)
            if style == "question" and re.search(r"(?:有哪些|有多少|是否|能否)$", clean_base):
                query = clean_base + "？"
            else:
                query = wrapper.format(base=clean_base)
            demands.append(MockDemand(
                demand_id=f"unsupported-{index:02d}-{style}",
                scenario="unsupported",
                user_intent=f"尝试按“{base}”这一业务条件筛选保单",
                query=query,
                coverage={"kind": "unsupported_scene", "scene_ids": [str(scene.get("scene_id") or index)], "surface_style": style},
            ))
    return demands


def _compound_demands() -> list[MockDemand]:
    seeds = [
        ("陈晓华做投保人且保额至少30万", "陈晓华投保的，保额至少30万"),
        ("女性被保人或45岁以上投保人", "被保人是女性，或者投保人超过45岁的"),
        ("今年承保且分红险", "今年承保的分红险保单"),
        ("保单号尾号4826或尾号7319", "合同号尾号4826或7319"),
        ("累计已缴保费超过10万且仍有效", "已经交了十万以上并且还有效的单子"),
        ("九月到期或距离犹豫期结束不到3天", "九月到期的，或者犹豫期只剩不到三天的"),
        ("投保人35到50岁且被保人为男性", "投保人35至50岁，同时被保人是男的"),
        ("期缴保费不低于5000且允许加保", "每期至少五千、还能加保的保单"),
        ("今年生效并且投保人是陈晓华或周海宁", "今年生效，投保人陈晓华或者周海宁"),
        ("寿险来源且不是失效状态", "寿险公司的单子，状态别是失效"),
    ]
    wrappers = (
        ("plain", "{query}"),
        ("command", "帮我查查{query}"),
        ("question", "有没有{query}？"),
        ("no_punctuation", "把{query}都列出来"),
    )
    demands: list[MockDemand] = []
    for seed_index, (intent, query) in enumerate(seeds, start=1):
        for style, wrapper in wrappers:
            demands.append(MockDemand(
                demand_id=f"compound-{seed_index:02d}-{style}",
                scenario="compound_logic",
                user_intent=f"筛选{intent}的保单",
                query=wrapper.format(query=query),
                coverage={"kind": "logical_composition", "logic": "AND_OR", "surface_style": style},
            ))
    return demands


def _context_demands() -> list[MockDemand]:
    histories = [
        ("查陈晓华作为投保人的保单", "那今年生效的呢", "追加时间条件"),
        ("找保额超过30万的有效保单", "只看分红险", "追加险类条件"),
        ("查被保人45岁以上的", "改成投保人", "纠正角色"),
        ("筛选今年承保的保单", "再排除已经失效的", "追加状态条件"),
        ("找合同号尾号4826的", "7319的也要", "追加并列值"),
        ("查九月份到期的保单", "不对，是十月份", "纠正时间"),
        ("找年缴保费两万以上的", "放宽到一万", "纠正数值"),
        ("查女性被保人的保单", "年龄还要在30到45之间", "追加年龄区间"),
    ]
    suffixes = ("", "，麻烦了", "？")
    demands: list[MockDemand] = []
    for index, (previous, current, intent) in enumerate(histories, start=1):
        contexts = [
            {"role": "user", "content": previous, "sub_agent": ""},
            {"role": "assistant", "content": "已按上一轮条件完成查询。", "sub_agent": "POLICY_SEARCH"},
        ]
        for variant, suffix in enumerate(suffixes, start=1):
            demands.append(MockDemand(
                demand_id=f"context-{index:02d}-{variant}",
                scenario="context_disambiguation",
                user_intent=f"基于上一轮筛选结果{intent}",
                query=current.rstrip("？?") + suffix,
                contexts=contexts,
                coverage={"kind": "context", "context_operation": intent, "surface_style": f"context_{variant}"},
            ))
    return demands


def _clarification_demands() -> list[MockDemand]:
    queries = [
        "年缴保费的保单", "帮我按年龄找一下", "查最近生效的", "想看保单状态", "找姓陈的",
        "保额比较高的那些", "快到期的保单", "交费多的客户保单", "查一下尾号", "筛选今年的",
        "找不是这类的", "投保人或者被保人是陈先生的", "金额在三万到之间", "九月或生效的保单", "不要寿险和分红险的",
    ]
    return [
        MockDemand(
            demand_id=f"clarification-{index:02d}",
            scenario="clarification",
            user_intent="按信息不足或作用域不清的条件尝试筛选保单",
            query=query,
            coverage={"kind": "clarification", "surface_style": "incomplete_or_ambiguous"},
        )
        for index, query in enumerate(queries, start=1)
    ]


def build_mock_demands(config: Dict[str, Any]) -> list[MockDemand]:
    demands = [
        *_atomic_demands(config),
        *_scene_demands(config),
        *_unsupported_demands(config),
        *_compound_demands(),
        *_context_demands(),
        *_clarification_demands(),
    ]
    seen: set[str] = set()
    unique: list[MockDemand] = []
    for demand in demands:
        normalized = normalize_query(demand.query)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(demand)
    return unique


def normalize_query(value: str) -> str:
    return re.sub(r"[\s，。！？、；：,.!?;:]", "", str(value or "")).lower()


def coverage_summary(demands: Iterable[MockDemand], config: Dict[str, Any]) -> Dict[str, Any]:
    items = list(demands)
    field_ids = sorted({field for item in items for field in item.coverage.get("field_ids", [])})
    scene_ids = sorted({scene for item in items for scene in item.coverage.get("scene_ids", []) if str(scene).startswith("SCENE_")})
    unsupported_ids = sorted({scene for item in items for scene in item.coverage.get("scene_ids", []) if str(scene).startswith("UNSUPPORTED_")})
    return {
        "case_count": len(items),
        "enabled_field_count": len(_enabled_fields(config)),
        "covered_field_count": len(field_ids),
        "covered_field_ids": field_ids,
        "enabled_scene_count": len([item for item in config.get("scene_templates") or [] if item.get("enabled")]),
        "covered_scene_count": len(scene_ids),
        "covered_scene_ids": scene_ids,
        "unsupported_scene_count": len(config.get("unsupported_scenes") or []),
        "covered_unsupported_scene_count": len(unsupported_ids),
        "covered_unsupported_scene_ids": unsupported_ids,
        "scenario_counts": {
            scenario: sum(1 for item in items if item.scenario == scenario)
            for scenario in sorted({item.scenario for item in items})
        },
        "surface_style_counts": {
            style: sum(1 for item in items if item.coverage.get("surface_style") == style)
            for style in sorted({str(item.coverage.get("surface_style") or "") for item in items})
            if style
        },
    }
