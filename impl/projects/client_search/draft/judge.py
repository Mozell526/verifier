from __future__ import annotations

from copy import deepcopy
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Set

from impl.core.authority_environment import build_authority_environment
from impl.core.authority_key_index import coverage_gap_trigger_hit
from impl.core.authority_tool import build_authority_resolve_tool
from impl.core.judge import _derive_overall_status
from impl.core.judge_protocol import ProjectJudge
from impl.core.project_loader import (
    load_field_provider,
    resolve_role_assets,
)
from impl.core.schema import (
    JudgeResult,
    ProjectSpec,
    RunTrace,
    load_authority_investigation_report,
    normalize_judge_result,
    to_dict,
    trace_extracted_output,
)
from impl.core.summary import summary_from_fulfillment
from impl.projects.client_search.judge import (
    judge_governance,
    protocol_tools,
    semantic_equivalence_rules,
)
from impl.projects.client_search.live import FIELD_PATTERNS, boundary_from_trace, capability_manifest, external_boundary_sources, value_mappings
from impl.projects.client_search.draft.enhanced_rules_key_index import (
    retrieve_enhanced_rules_for_fields,
)
from impl.projects.client_search.draft.field_tools import (
    build_field_key_index_registry,
    create_field_key_search_tool,
    create_minimal_field_definition_tool,
    load_explicit_field_support,
    search_field_key_index,
)
from impl.tools import ToolContext, ToolResult
from impl.tools import build_agno_tools

logger = logging.getLogger(__name__)

_FIELD_LIST_KEYS = frozenset(["conditions", "structured_output"])
_CJK_TEXT = re.compile(r"[\u3400-\u9fff]+")
_UNSUPPORTED_NOTICE = re.compile(
    r"(?P<constraint>[^，。；;\n]{1,32}?)(?:暂不支持|当前不支持|不支持)(?:搜索|查询)?"
)
_RANGE_CAPABLE_OPERATORS = frozenset({
    "GT", "GTE", "LT", "LTE", "RANGE", "BETWEEN", "NOT_RANGE", "WITHIN",
})
# 操作符形态冲突面由冻结权威调查报告（明确涉及操作符形态且未唯一决定的
# MaterialDecision/CoverageGap）推导（_operator_conflict_fields），不再硬编码字段名。
_JUDGE_TOOL_CALL_LIMIT = 8
_FIELD_NAVIGATION_CALL_LIMIT = 4
_FIELD_PATH_TOKEN = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(\.[A-Za-z][A-Za-z0-9_]*)+")


_AUTHORITY_REPORT_RELATIVE = "docs/authority-investigation-report.json"


def _load_authority_report(spec: ProjectSpec):
    """读取冻结权威调查报告（固定逻辑路径的 artifact，investigate-authority-judge.md §13）。"""
    selected = [
        item
        for item in resolve_role_assets(spec, "judge", use_candidate=True)
        if item["mapping"].kind == "investigation"
    ]
    if len(selected) != 1:
        raise RuntimeError(
            "Authority report requires exactly one judge investigation package, "
            f"got {len(selected)}"
        )
    path = Path(selected[0]["path"]) / _AUTHORITY_REPORT_RELATIVE
    if not path.is_file():
        raise FileNotFoundError(f"Authority investigation report not found: {path}")
    return load_authority_investigation_report(path)


def _operator_conflict_fields(spec: ProjectSpec) -> frozenset[str]:
    """从冻结权威调查报告推导操作符形态冲突面。

    报告的 MaterialDecision/CoverageGap 文本明确涉及操作符形态且标记为冲突面/
    未裁决时，该字段的可执行操作符无法由资料唯一确定：确定性 operator gate 不做
    强制翻转，留给 authority.resolve 现场裁决（unresolved → not_evaluable）。
    """
    report = _load_authority_report(spec)
    texts: list[str] = []
    for material in report.materials:
        for decision in material.decisions:
            texts.append(" ".join([
                decision.governs,
                decision.statement,
                decision.scenario,
                *decision.conditions,
            ]))
        texts.extend(material.limitations)
    for gap in report.coverage_gaps:
        texts.append(" ".join([
            gap.governs,
            gap.gap_reason,
            *gap.conditions,
            *gap.required_evidence,
        ]))
    fields: set[str] = set()
    for blob in texts:
        if not any(keyword in blob for keyword in ("操作符", "operator", "MATCH", "RANGE")):
            continue
        if not any(keyword in blob for keyword in ("冲突", "conflict", "未裁决", "unresolved")):
            continue
        for match in _FIELD_PATH_TOKEN.finditer(blob):
            token = match.group(0)
            if token.startswith("authority."):
                continue
            fields.add(token)
    return frozenset(fields)


def _request_text(intent_frame: Dict[str, Any]) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for item in intent_frame.get("request_candidates") or []:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value") or "").strip()
        if value and value not in seen:
            seen.add(value)
            values.append(value)
    return " ".join(values)


def _text_fragments(value: Any, *, minimum: int, maximum: int = 8) -> set[str]:
    text = value if isinstance(value, str) else json.dumps(
        value, ensure_ascii=False, sort_keys=True, default=str
    )
    fragments: set[str] = set()
    for run in _CJK_TEXT.findall(text.casefold()):
        upper = min(len(run), maximum)
        for size in range(minimum, upper + 1):
            fragments.update(
                run[index:index + size]
                for index in range(0, len(run) - size + 1)
            )
    fragments.update(
        token
        for token in re.findall(r"[a-z][a-z0-9_.-]{2,}", text.casefold())
    )
    return fragments


def _request_text_from_trace(trace: RunTrace) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for source in (trace.normalized_request, trace.input):
        if not isinstance(source, dict):
            continue
        for key in ("user_text", "query", "user_intent", "question"):
            value = source.get(key)
            if not value:
                continue
            value = str(value).strip()
            if value and value not in seen:
                seen.add(value)
                values.append(value)
    return " ".join(values)


def _request_enum_hits(
    trace: RunTrace,
    full_manifest: Dict[str, Any],
) -> Dict[str, list[str]]:
    """请求文本精确命中的清单枚举值（枚举值长度>=3 且为请求文本子串）。

    返回 field -> 命中的枚举值列表；用于把「具体产品全称/简称」等口语名映射到
    对应字段，并避免 compact manifest 展开超大枚举列表。
    """
    request_text = _request_text_from_trace(trace)
    hits: Dict[str, list[str]] = {}
    if not request_text or not isinstance(full_manifest, dict):
        return hits
    for field, entry in full_manifest.items():
        if not isinstance(entry, dict):
            continue
        matched = [
            str(enum)
            for enum in entry.get("enums") or []
            if len(str(enum)) >= 3 and str(enum) in request_text
        ]
        if matched:
            hits[field] = matched
    return hits


def _manifest_label_fragments(
    field: str,
    entry: Dict[str, Any],
    value_mapping: Optional[Dict[str, Any]] = None,
) -> set[str]:
    """字段的标签语料 fragment 集合：字段名 + 枚举 + 值映射别名（用户口语→标准值）。"""
    parts = [str(entry.get("field") or field)]
    parts += [str(enum) for enum in (entry.get("enums") or [])]
    if isinstance(value_mapping, dict):
        mapped = value_mapping.get(field)
        if isinstance(mapped, dict):
            parts += [str(key) for key in mapped] + [str(val) for val in mapped.values()]
    fragments: set[str] = set()
    for part in parts:
        fragments.update(_text_fragments(part, minimum=2, maximum=6))
    return fragments


def _semantic_field_hits(
    request_text: str,
    full_manifest: Dict[str, Any],
    value_mapping: Optional[Dict[str, Any]] = None,
    *,
    max_fragment_df: int = 3,
) -> Set[str]:
    """请求文本与清单字段标签语料做 CJK fragment 匹配。

    只用跨字段低频 fragment（df<=max_fragment_df），避免「客户」「保险」等通用词误命中。
    用于 actual 使用了清单外字段名时，反查请求真正对应的清单字段（按枚举/值映射
    标签语义命中），避免紧凑清单被压成空而误判 not_evaluable。
    """
    request_fragments = _text_fragments(request_text, minimum=2, maximum=6)
    if not request_fragments:
        return set()
    field_fragments = {
        field: _manifest_label_fragments(field, entry, value_mapping)
        for field, entry in full_manifest.items()
        if isinstance(entry, dict)
    }
    document_frequency: dict[str, int] = {}
    for fragments in field_fragments.values():
        for fragment in fragments:
            document_frequency[fragment] = document_frequency.get(fragment, 0) + 1
    hits: Set[str] = set()
    for field, fragments in field_fragments.items():
        overlap = request_fragments & fragments
        rare = [fragment for fragment in overlap if document_frequency.get(fragment, 99) <= max_fragment_df]
        if any(fragment for fragment in rare if _CJK_TEXT.search(fragment)):
            hits.add(field)
    return hits


def _extract_fields_from_trace(
    trace: RunTrace,
    full_manifest: Optional[Dict[str, Any]] = None,
    value_mapping: Optional[Dict[str, Any]] = None,
) -> Set[str]:
    fields = set()
    output = trace_extracted_output(trace) if trace_extracted_output(trace) else {}
    if isinstance(output, dict):
        for key in _FIELD_LIST_KEYS:
            if key in output and isinstance(output[key], list):
                for entry in output[key]:
                    if isinstance(entry, dict) and "field" in entry:
                        fields.add(entry["field"])
    reference = trace.reference_contract or (trace.input.get("reference") if isinstance(trace.input, dict) else None)
    if isinstance(reference, dict):
        for value in reference.values():
            if isinstance(value, list):
                for entry in value:
                    if isinstance(entry, dict) and "field" in entry:
                        fields.add(entry["field"])
    # 请求文本命中能力清单的字段名或枚举值时，把该字段纳入紧凑清单，
    # 避免 actual 未输出该条件时 LLM 误以为能力清单没有该维度。
    if isinstance(full_manifest, dict):
        request_text = _request_text_from_trace(trace)
        if request_text:
            for field, entry in full_manifest.items():
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("field") or field)
                if name and name in request_text:
                    fields.add(field)
            fields.update(_request_enum_hits(trace, full_manifest))
            # 机制下沉：请求文本的字段语义命中总是并入 trace_fields（不再只
            # 在 actual 使用清单外字段时才反查）。让 LLM 在 compact manifest
            # 中看到请求真正对应的候选字段（枚举/值映射标签语义命中），自行
            # 裁决字段归属与孤词姓名例外的适用性，而不是因清单被压成空/漏
            # 字段而误判 fulfilled/not_evaluable。
            fields.update(
                _semantic_field_hits(request_text, full_manifest, value_mapping)
            )
    return fields


def _reference_has_condition_oracle(trace: RunTrace) -> bool:
    reference = trace.reference_contract or (
        trace.input.get("reference") if isinstance(trace.input, dict) else None
    )
    if not isinstance(reference, dict):
        return False
    return any(
        isinstance(reference.get(key), list) and bool(reference.get(key))
        for key in ("conditions", "structured_output", "expected_conditions")
    )


def _downstream_result_verified(trace: RunTrace) -> bool:
    boundary = trace.application_boundary or {}
    if isinstance(boundary, dict) and bool(boundary.get("result_set_verified")):
        return True
    output = trace_extracted_output(trace) or {}
    downstream = output.get("downstream_search") if isinstance(output, dict) else None
    return bool(
        isinstance(downstream, dict)
        and (
            downstream.get("result_set_verified") is True
            or str(downstream.get("status") or "").casefold()
            in {"succeeded", "verified", "completed"}
        )
    )


def _declares_closed_world(capability: Dict[str, Any]) -> bool:
    for key in ("closed_world", "authoritative", "is_complete", "complete"):
        if capability.get(key) is True:
            return True
    return False


def _enum_completeness_evidence(
    trace: RunTrace,
    compact_manifest: Dict[str, Any],
) -> list[Dict[str, Any]]:
    """Describe whether an actual enum expansion has evidence of being complete."""

    request = " ".join(
        str(value or "")
        for source in (trace.normalized_request, trace.input)
        if isinstance(source, dict)
        for value in [
            source.get("user_text")
            or source.get("query")
            or source.get("user_intent")
            or source.get("question")
        ]
        if value
    )
    boundary = trace.application_boundary or {}
    if not isinstance(boundary, dict):
        boundary = {}
    judge_scope = str(boundary.get("judge_scope") or "")
    parser_semantics_only = judge_scope == "parser_condition_semantics_only"
    output = trace_extracted_output(trace) or {}
    conditions = []
    if isinstance(output, dict):
        conditions = output.get("conditions") or output.get("structured_output") or []
    has_oracle = _reference_has_condition_oracle(trace)
    downstream_verified = _downstream_result_verified(trace)
    evidence: list[Dict[str, Any]] = []
    for index, condition in enumerate(conditions):
        if not isinstance(condition, dict):
            continue
        value = condition.get("value")
        if not isinstance(value, list) or len(value) < 2:
            continue
        field = str(condition.get("field") or "")
        capability = compact_manifest.get(field) or {}
        if not isinstance(capability, dict):
            capability = {}
        value_types = {str(item) for item in capability.get("value_types") or []}
        enum_refs = [str(item) for item in capability.get("enum_refs") or [] if str(item)]
        enum_values = {str(item) for item in capability.get("enums") or []}
        is_enum_field = bool(enum_refs or enum_values or "enum" in value_types or "list" in value_types)
        if not is_enum_field:
            continue
        string_values = [str(item) for item in value]
        values_mentioned = [item for item in string_values if item and item in request]
        explicit_enumeration = len(values_mentioned) == len(string_values)
        closed_world = _declares_closed_world(capability)
        static_sources = []
        if enum_refs:
            static_sources.append("field_enum_registry")
        if enum_values:
            static_sources.append("capability_manifest")
        category_expansion = not explicit_enumeration
        only_static_evidence = bool(
            static_sources
            and not closed_world
            and not has_oracle
            and not downstream_verified
        )
        all_in_static_registry = bool(
            enum_values and all(item in enum_values for item in string_values)
        )
        static_registry_is_closed_set = bool(
            parser_semantics_only and static_sources and all_in_static_registry
        )
        evidence.append({
            "condition_index": index,
            "field": field,
            "operator": str(condition.get("operator") or ""),
            "judge_scope": judge_scope,
            "actual_value_count": len(string_values),
            "actual_values_all_in_static_registry": all_in_static_registry,
            "user_explicitly_enumerated_all_actual_values": explicit_enumeration,
            "category_expansion_from_request": category_expansion,
            "static_source_types": static_sources,
            "enum_refs": enum_refs,
            "closed_world_evidence": closed_world,
            "case_oracle_available": has_oracle,
            "downstream_result_set_verified": downstream_verified,
            "static_registry_is_closed_set": static_registry_is_closed_set,
            "enum_authority_candidate": bool(
                category_expansion
                and only_static_evidence
                and not static_registry_is_closed_set
            ),
            "decision_rule": (
                "The static registry (field_enum_registry / capability_manifest enums) directly "
                "decides current_behavior only: which values the parser can currently deliver. "
                "Under parser_condition_semantics_only, when actual enumerates values all inside "
                "the registry and no conflicting material claims exist, completeness relative to "
                "the parser's deliverable set is directly decidable (current_behavior); it does "
                "NOT prove the downstream legal-value universe (external_fact), so enum-value-"
                "authority stays open for judgments depending on the external legal-value universe "
                "or when materials conflict about the same legal-value set: if it affects a "
                "blocking assessment, call authority.resolve and treat unresolved as not_evaluable. "
                "If the user explicitly listed the same values, completeness of the category "
                "expansion is not at issue."
            ),
        })
    return evidence


def _unsupported_boundary_evidence(trace: RunTrace) -> Dict[str, Any]:
    """Expose graceful handling of an unsupported constraint as boundary evidence."""

    output = trace_extracted_output(trace) or {}
    if not isinstance(output, dict):
        return {}
    visible_text = "\n".join(
        str(output.get(key) or "").strip()
        for key in ("intent_summary", "robot_text", "summary", "message")
        if str(output.get(key) or "").strip()
    )
    if not visible_text:
        return {}
    notices: list[str] = []
    constraints: list[str] = []
    for match in _UNSUPPORTED_NOTICE.finditer(visible_text):
        notice = match.group(0).strip()
        constraint = match.group("constraint").strip(" ：:，,。；;\n")
        constraint = re.sub(r"^(?:提示|说明|系统提示)", "", constraint).strip(" ：:")
        if notice and notice not in notices:
            notices.append(notice)
        if constraint and constraint not in constraints:
            constraints.append(constraint)
    if not notices:
        return {}
    request = " ".join(
        str(source.get(key) or "")
        for source in (trace.normalized_request, trace.input)
        if isinstance(source, dict)
        for key in ("user_text", "query", "user_intent", "question")
        if source.get(key)
    )
    request_terms = _text_fragments(request, minimum=2, maximum=6)
    constraint_terms = _text_fragments(constraints, minimum=2, maximum=6)
    overlap = sorted(request_terms & constraint_terms, key=lambda item: (-len(item), item))
    conditions = output.get("conditions") or output.get("structured_output") or []
    supported_condition_count = len(conditions) if isinstance(conditions, list) else 0
    acknowledged_request_constraint = bool(overlap)
    return {
        "unsupported_notices": notices,
        "unsupported_constraint_labels": constraints,
        "request_notice_overlap": overlap[:8],
        "acknowledges_requested_constraint": acknowledged_request_constraint,
        "supported_condition_count": supported_condition_count,
        "graceful_degradation_candidate": bool(
            acknowledged_request_constraint and supported_condition_count
        ),
        "all_conditions_unsupported": bool(
            acknowledged_request_constraint and supported_condition_count == 0
        ),
        "decision_rule": (
            "When actual clearly identifies a requested constraint as unsupported and still emits "
            "the remaining supported conditions, evaluate the retained conditions normally; the "
            "omitted unsupported constraint is a core-delivery item whose capability cannot be "
            "confirmed, so its delivery assessment is not_evaluable (no affirmative business "
            "conclusion), while the boundary-handling subgoal (transparent notice, no fabricated "
            "conditions) is fulfilled. "
            "When actual identifies the request's own term as unsupported AND emits no conditions "
            "(all_conditions_unsupported), derive the request's core-delivery expectation first: "
            "not_evaluable when the capability is unconfirmed (out-of-manifest), or not_fulfilled "
            "when the request condition hits an in-manifest expressible field but actual omits it; "
            "judge boundary-handling subgoals fulfilled. A transparent rejection alone must not "
            "turn the whole case fulfilled. When the unsupported label does not overlap the "
            "request text (the system re-labeled the request into a different capability "
            "category), the core delivery keeps the out-of-boundary not_evaluable handling."
        ),
    }


def _compact_capability_manifest(
    context: Dict[str, Any],
    trace_fields: Set[str],
    trace: Optional[RunTrace] = None,
) -> Dict[str, Any]:
    full_manifest = context.get("capability_manifest")
    if not isinstance(full_manifest, dict):
        return {}
    request_hits = _request_enum_hits(trace, full_manifest) if trace is not None else {}
    compact_fields = {field for field in trace_fields if field in full_manifest}
    compact: Dict[str, Any] = {}
    for field in compact_fields:
        entry = dict(full_manifest[field])
        enums = list(entry.get("enums") or [])
        show_all = entry.get("show_enum_in_prompt") is not False
        candidate_limit = entry.get("enum_candidate_limit_in_prompt")
        if not show_all or len(enums) > 50:
            limit = int(candidate_limit) if candidate_limit else 5
            hits = request_hits.get(field) or []
            if hits:
                kept = list(dict.fromkeys([*hits, *enums]))
            else:
                kept = list(enums)
            if len(kept) > limit:
                entry["enums"] = kept[:limit]
                entry["enum_values_truncated"] = True
            else:
                entry["enums"] = kept
            entry.setdefault("show_enum_in_prompt", False)
            entry["enum_candidate_limit_in_prompt"] = limit
            if hits:
                entry["request_enum_hits"] = hits
        compact[field] = entry
    return compact


def _compact_semantic_rules(context: Dict[str, Any], trace_fields: Set[str]) -> Dict[str, Any]:
    full_rules = context.get("semantic_equivalence_rules")
    if not isinstance(full_rules, dict):
        return {}
    if not trace_fields:
        return {}
    compact: Dict[str, Any] = {}
    if "equivalent_condition_forms" in full_rules:
        compact["equivalent_condition_forms"] = [r for r in full_rules["equivalent_condition_forms"] if isinstance(r, dict) and r.get("field") in trace_fields]
    if "operator_compatibility" in full_rules:
        compact["operator_compatibility"] = [r for r in full_rules["operator_compatibility"] if isinstance(r, dict) and r.get("field") in trace_fields]
    if "equivalent_fields" in full_rules:
        compact["equivalent_fields"] = [r for r in full_rules["equivalent_fields"] if isinstance(r, dict) and (r.get("field") in trace_fields or r.get("equivalent_field") in trace_fields)]
    return compact


def _compact_value_mappings(context: Dict[str, Any], trace_fields: Set[str]) -> Dict[str, Any]:
    full_mappings = context.get("value_mappings")
    if not isinstance(full_mappings, dict):
        return {}
    if not trace_fields:
        return {}
    return {field: full_mappings[field] for field in trace_fields if field in full_mappings}


def _build_field_tools(spec: ProjectSpec) -> list[Any]:
    """构建 client_search 字段认知 VerifiableTool（主 Judge 与 Authority 共享）。"""
    try:
        field_provider = load_field_provider(spec)
    except Exception as exc:
        logger.warning(f"[client_search.judge] Failed to load field provider for {spec.project_id}: {exc}")
        field_provider = None
    if field_provider is None:
        return []
    try:
        field_index_registry = build_field_key_index_registry(spec, field_provider)
    except Exception as exc:
        logger.warning(
            f"[client_search.judge] Failed to build field key index for {spec.project_id}: {exc}"
        )
        field_index_registry = None
    definition_tool = (
        create_minimal_field_definition_tool(field_provider, field_index_registry)
        if field_index_registry is not None
        else create_minimal_field_definition_tool(field_provider)
    )
    return [
        create_field_key_search_tool(spec, field_index_registry),
        definition_tool,
    ]



def _enrich_unsupported_boundary_evidence(
    spec: ProjectSpec, trace: RunTrace, evidence: Dict[str, Any]
) -> Dict[str, Any]:
    """Resolve unsupported notices to explicit field capability facts via Key-Index Search→Load."""
    if not evidence:
        return evidence
    labels = [
        str(item).strip()
        for item in evidence.get("unsupported_constraint_labels") or []
        if str(item).strip()
    ]
    request_text = " ".join(
        str(source.get(key) or "")
        for source in (trace.normalized_request, trace.input)
        if isinstance(source, dict)
        for key in ("user_text", "query", "user_intent", "question")
        if source.get(key)
    )
    query = " ".join([*labels, request_text]).strip()
    explicit_unsupported: list[dict[str, Any]] = []
    if query:
        # This is a deterministic gate, not a broad recall surface: only the top
        # Key-Index locator may control status. Lower-ranked fuzzy hits remain
        # navigation suggestions and must not silently widen the boundary.
        hits = search_field_key_index(spec, query, limit=1)
        if hits:
            hit = hits[0]
            field = str(hit.get("field") or "").strip()
            supported, explicit = load_explicit_field_support(spec, field)
            if explicit and not supported:
                explicit_unsupported.append({
                    "field": field,
                    "short_name": str(hit.get("short_name") or field),
                    "is_supported": False,
                    "is_supported_explicit": True,
                })
    enriched = dict(evidence)
    enriched["explicit_unsupported_fields"] = explicit_unsupported
    enriched["explicit_unsupported_capability"] = bool(explicit_unsupported)
    authority_enabled = bool(
        ((spec.verifier or {}).get("authority") or {}).get("enabled", True)
    )
    if authority_enabled:
        decision_rule = (
            " When Key-Index Search→Load resolves the requested constraint to a field with "
            "is_supported=false and is_supported_explicit=true, field presence does not mean "
            "deliverable capability and does not decide responsibility. The frozen investigation "
            "records this as a coverage gap: Authority must distinguish out-of-scope from an "
            "in-scope missing capability. Consume the Authority resolution before the dependent "
            "blocking assessment; transparent refusal remains a separate non-blocking subgoal."
        )
    else:
        decision_rule = (
            " When Key-Index Search→Load resolves the requested constraint to a field with "
            "is_supported=false and is_supported_explicit=true, it proves the current delivery "
            "limitation but does not decide responsibility. Authority is disabled: evaluate whether "
            "the Live output satisfies the user's requested result using current observable evidence. "
            "A missing blocking result is not_fulfilled; do not emit not_evaluable merely because a "
            "capability or responsibility boundary candidate exists. Transparent refusal remains a "
            "separate non-blocking subgoal."
        )
    enriched["decision_rule"] = str(enriched.get("decision_rule") or "") + decision_rule
    return enriched


def _build_judge_tools(spec: ProjectSpec) -> list[Any]:
    field_tools = _build_field_tools(spec)
    navigation_state = {"calls": 0}

    def _budgeted_cached_execute(tool_id: str, execute):
        cache: dict[str, Any] = {}

        def execute_once(**kwargs):
            key = json.dumps(
                kwargs,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            if key in cache:
                return deepcopy(cache[key])
            if navigation_state["calls"] >= _FIELD_NAVIGATION_CALL_LIMIT:
                return ToolResult(
                    tool_id=tool_id,
                    tool_type="client_search_field_navigation",
                    status="inconclusive",
                    error=(
                        "Field navigation budget reached. Stop broadening field search; "
                        "use the evidence already loaded and preserve remaining calls for "
                        "authority.resolve when a governed claim or boundary depends on it."
                    ),
                    runtime_metadata={
                        "budget_kind": "field_navigation",
                        "limit": _FIELD_NAVIGATION_CALL_LIMIT,
                        "calls_used": navigation_state["calls"],
                    },
                )
            navigation_state["calls"] += 1
            cache[key] = deepcopy(execute(**kwargs))
            return deepcopy(cache[key])

        return execute_once

    for field_tool in field_tools:
        if field_tool.execute_fn is not None:
            field_tool.execute_fn = _budgeted_cached_execute(
                field_tool.tool_id, field_tool.execute_fn
            )
    return build_agno_tools(field_tools)


def condition_comparison(spec: ProjectSpec, trace: RunTrace) -> Dict[str, Any]:
    inputs = {"expected": {}}
    result = protocol_tools(spec).run(
        "client_search.condition_compare",
        ToolContext(project_id=spec.project_id, purpose="judge", spec=spec, trace=trace, inputs=inputs),
    )
    return {
        "tool_id": result.tool_id,
        "tool_type": result.tool_type,
        "status": result.status,
        "outputs": result.outputs,
        "evidence": result.evidence,
        "missing_evidence": result.missing_evidence,
        "boundary_limits": result.boundary_limits,
        "error": result.error,
    }


def apply_condition_comparison(trace: RunTrace, judge_result: JudgeResult, comparison: Dict[str, Any]) -> None:
    outputs = comparison.get("outputs") or {}
    if not outputs:
        return
    wrong = list(outputs.get("wrong") or [])
    missing = list(outputs.get("missing") or [])
    extra = list(outputs.get("extra") or [])
    if wrong or missing or extra:
        judge_result.wrong = wrong
        judge_result.missing = missing
        judge_result.extra = extra
    if outputs:
        judge_result.evidence = list(judge_result.evidence or []) + [{
            "source": "client_search.condition_compare",
            "wrong": wrong,
            "missing": missing,
            "extra": extra,
        }]
    if trace.extracted_output is not None:
        judge_result.actual = trace.extracted_output


def _scalar_condition_value(value: Any) -> Any:
    """条件值取标量：单元素列表归一为标量；多值/字典（如 RANGE）返回 None。"""
    if isinstance(value, (list, tuple)):
        return value[0] if len(value) == 1 else None
    if isinstance(value, dict):
        return None
    return value


def _operator_justified(
    field: str,
    operator: str,
    manifest_entry: Dict[str, Any],
    equiv_rules: list[Dict[str, Any]],
    value: Any = None,
) -> bool:
    """操作符是否可被下游执行。

    放行条件（确定性 gate，prompt 不得自行放行其他例外）：
    - operator 在字段支持集内；
    - 范围族操作符与支持集中的范围族互容；
    - 显式 semantic_equivalence_rules（equivalent_condition_forms /
      operator_compatibility / equivalent_fields）命中；
    - 单值 MATCH 且字段支持 CONTAINS：仅当条件值（标量或单元素列表）精确等于
      清单枚举值时，才视为后处理可归一为 CONTAINS（不再 blanket 放行）。
    """
    supported = set(manifest_entry.get("operators") or [])
    if operator in supported:
        return True
    value_types = set(manifest_entry.get("value_types") or [])
    if operator == "MATCH" and "CONTAINS" in supported and (
        "enum" in value_types or "list" in value_types or "extract" in value_types
    ):
        scalar = _scalar_condition_value(value)
        if scalar is not None:
            enum_values = {str(item) for item in (manifest_entry.get("enums") or [])}
            if str(scalar) in enum_values:
                return True
    if operator in _RANGE_CAPABLE_OPERATORS and supported & _RANGE_CAPABLE_OPERATORS:
        return True
    for rule in equiv_rules:
        if (
            isinstance(rule, dict)
            and rule.get("field") == field
            and str(rule.get("operator") or "") == operator
        ):
            return True
    return False


def _actual_operator_violations(spec: ProjectSpec, trace: RunTrace) -> list[Dict[str, Any]]:
    manifest = capability_manifest(spec)
    if not isinstance(manifest, dict):
        return []
    equiv_rules = semantic_equivalence_rules(spec)
    output = trace_extracted_output(trace) or {}
    if not isinstance(output, dict):
        return []
    violations: list[Dict[str, Any]] = []
    conditions = output.get("conditions") or output.get("structured_output") or []
    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        field = condition.get("field")
        operator = condition.get("operator")
        entry = manifest.get(field)
        if not field or not operator or not isinstance(entry, dict):
            continue
        if not _operator_justified(str(field), str(operator), entry, equiv_rules, value=condition.get("value")):
            violations.append({
                "field": str(field),
                "operator": str(operator),
                "supported_operators": list(entry.get("operators") or []),
            })
    return violations


def _assessment_uses_operator(
    assessment: FulfillmentAssessment, field: str, operator: str
) -> bool:
    def matches(value: Any) -> bool:
        if isinstance(value, dict):
            if (
                str(value.get("field") or "") == field
                and str(value.get("operator") or "") == operator
            ):
                return True
            return any(matches(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return any(matches(item) for item in value)
        if isinstance(value, str):
            return field in value and operator in value
        return False

    return matches(assessment.expected_evidence) or matches(assessment.actual_evidence)


def _apply_operator_capability_check(
    spec: ProjectSpec, trace: RunTrace, judge_result: JudgeResult
) -> None:
    """Authority 开启时消费 operator mismatch。

    能力清单只负责触发治理裁决，不能替 Authority 证明产品职责边界；缺少调用
    引用时 fail-closed 到 not_evaluable。Authority 关闭时，F/NF 完全由 Judge 的
    用户意图、Live 交付与语义等价链路决定，capability gate 不参与改写结果。
    """
    violations = _actual_operator_violations(spec, trace)
    if not violations:
        return
    authority_enabled = bool(
        ((spec.verifier or {}).get("authority") or {}).get("enabled", True)
    )
    if not authority_enabled:
        return
    conflict_fields = _operator_conflict_fields(spec) & {
        str(v.get("field") or "") for v in violations
    }
    if conflict_fields:
        judge_result.evidence = list(judge_result.evidence or []) + [{
            "source": "capability_manifest.operator_conflict_deferred",
            "fields": sorted(conflict_fields),
            "rule": (
                "operator form for these fields is an unresolved authority conflict surface; "
                "the deterministic gate does not decide fulfillment. Authority must resolve "
                "the capability question before a decisive status is accepted."
            ),
        }]
    violation_rule = (
        "condition operator conflicts with the manifest; this is a trigger for "
        "Authority capability/responsibility verification, not by itself proof of "
        "not_fulfilled. A resolved Authority conclusion and the live delivery evidence "
        "determine the assessment."
    )
    judge_result.evidence = list(judge_result.evidence or []) + [{
        "source": "capability_manifest.operator_violation",
        "violations": violations,
        "deferred_conflict_fields": sorted(conflict_fields),
        "rule": violation_rule,
    }]
    override_reasons: list[str] = []
    for violation in violations:
        field = violation["field"]
        for assessment in judge_result.fulfillment_assessments or []:
            if not _assessment_uses_operator(
                assessment, field, violation["operator"]
            ):
                continue
            status = str(getattr(assessment, "status", "") or "").strip().lower()
            if status != "fulfilled":
                continue
            call_ids = [
                str(call_id).strip()
                for call_id in (assessment.authority_tool_call_ids or [])
                if str(call_id).strip()
            ]
            if call_ids:
                # Authority gate 已在本项目 reconcile 前消费 audit：resolved
                # 由 Judge 继续评价，unresolved/tool failure 已被 gate 降为 NE。
                continue
            assessment.status = "not_evaluable"
            assessment.score = None
            marker = {
                "kind": "operator_authority_required_not_consulted",
                "field": field,
                "operator": violation["operator"],
                "needs_human_review": True,
                "reason": (
                    f"actual 对 {field} 使用 {violation['operator']}，与当前能力清单冲突；"
                    "Authority 已开启，必须真实调用 authority.resolve 核对决定性能力/职责标准，"
                    "当前 assessment 没有 Authority 引用，不能静默作出确定性结论"
                ),
            }
            assessment.downstream_impact = marker["reason"]
            override_reasons.append(marker["reason"])
            refs = list(getattr(assessment, "evidence_refs", None) or [])
            if not any(
                isinstance(item, dict)
                and item.get("kind") == marker["kind"]
                and item.get("field") == field
                for item in refs
            ):
                refs.append(marker)
            assessment.evidence_refs = refs
    if override_reasons:
        judge_result.reasoning_summary = "；".join(dict.fromkeys(override_reasons))


def build_judge_context(spec: ProjectSpec, trace: RunTrace) -> Dict[str, Any]:
    application_boundary = boundary_from_trace(trace)
    return {
        "semantic_equivalence_rules": semantic_equivalence_rules(spec),
        "field_patterns": FIELD_PATTERNS,
        "application_boundary": application_boundary,
        "judge_governance": judge_governance(),
        "condition_comparison": {},
        "protocol_tool_results": [],
        "client_search_judge_basis": "wrong/missing/extra customer-search condition coverage within current field/config boundary",
        "boundary_usage": "application adapter has already decided whether result-set verification is in scope; judge should evaluate only within application_boundary.judge_scope.",
        "external_boundary_sources": external_boundary_sources(spec),
        "capability_manifest": capability_manifest(spec, full=True),
        "value_mappings": value_mappings(spec),
    }


def build_intent_frame(
    spec: ProjectSpec,
    trace: RunTrace,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if context is None:
        context = build_judge_context(spec, trace)
    trace_fields = _extract_fields_from_trace(
        trace, context.get("capability_manifest"), context.get("value_mappings")
    )
    compact_manifest = _compact_capability_manifest(context, trace_fields, trace=trace)
    return {
        "project_id": spec.project_id,
        "request_candidates": [
            {"source": f"{source_name}.{key}", "value": value}
            for source_name in ("normalized_request", "input")
            for source_value in [getattr(trace, source_name, None) or {}]
            if isinstance(source_value, dict)
            for key in ("query", "user_intent", "question", "input", "user_text")
            for value in [source_value.get(key)]
            if value
        ],
        "boundary_hints": context.get("application_boundary") or {},
        "output_semantics": "produce complete, semantically correct, downstream-executable search conditions and query logic for the current user request",
        "business_task_type": "natural_language_to_downstream_client_search_conditions",
        "downstream_consumer": "downstream client search",
        "critical_intent_dimensions": ["target_population", "field_semantics", "operator", "value_or_unit", "boolean_logic", "unsupported_or_out_of_boundary_request"],
        "boundary_rules": context.get("application_boundary") or {},
        "semantic_equivalence_rules": context.get("semantic_equivalence_rules") or [],
        "field_patterns": context.get("field_patterns") or {},
        "condition_comparison": {},
        "capability_manifest": compact_manifest,
        "critical_intent_dimensions_detail": {
            "target_population": "目标客户群体描述，驱动 population-sensitive field/operator/value 组合",
            "field_semantics": "请求中提到的字段及其语义定义，优先匹配 capability_manifest 中的 field/description",
            "operator": "每个字段允许的操作符，必须匹配 capability_manifest 中对应字段的 operators 列表",
            "value_or_unit": "值的单位换算与格式规范，如万=10000、岁以上用GTE+1等",
            "boolean_logic": "条件间的 AND/OR/NOT 逻辑关系",
            "unsupported_or_out_of_boundary_request": (
                "分开评价核心结果与透明说明；Authority 关闭时按用户意图和实际交付判 F/NF，"
                "Authority 开启时由 resolution 决定职责内 NF、职责外 NE 或 unresolved NE"
            ),
        },
    }


def _material_conflict_reasons(
    trace: RunTrace,
    compact_manifest: Dict[str, Any],
    mapping_values: Dict[str, Any],
) -> list[str]:
    """Detect same-subject contradictions already present in loaded materials.

    This only opens Authority availability.  It does not choose a source, infer
    precedence or decide the verdict.  The detector is driven by the current
    request plus structured field/mapping material, not frozen case IDs.
    """
    request_text = _request_text_from_trace(trace)
    if not request_text:
        return []
    reasons: list[str] = []
    for field, mappings in (mapping_values or {}).items():
        if not isinstance(mappings, dict):
            continue
        entry = (compact_manifest or {}).get(field) or {}
        notes = str(entry.get("notes") or "") if isinstance(entry, dict) else ""
        if not notes:
            continue
        note_assignments = {
            alias.strip(): value.strip()
            for alias, value in re.findall(
                r"([^；;，,：:\s]{1,24})\s*[=＝]\s*([^；;，,。]{1,32})",
                notes,
            )
            if alias.strip() and value.strip()
        }
        for alias, mapped_value in mappings.items():
            alias_text = str(alias).strip()
            if not alias_text or alias_text not in request_text:
                continue
            note_value = note_assignments.get(alias_text)
            if note_value and str(mapped_value).strip() != note_value:
                reasons.append(f"conflicting_materials:value_mapping:{field}:{alias_text}")
    return list(dict.fromkeys(reasons))


def _authority_candidate_reasons(
    spec: ProjectSpec,
    trace: RunTrace,
    *,
    enum_completeness_evidence: list[Dict[str, Any]],
    unsupported_boundary_evidence: Dict[str, Any],
    compact_manifest: Optional[Dict[str, Any]] = None,
    mapping_values: Optional[Dict[str, Any]] = None,
) -> list[str]:
    """Return deterministic reasons that justify constructing Authority runtime.

    The gate controls availability only; it never decides the verdict and never
    promotes SearchHit/navigation summaries into Evidence.
    """
    reasons: list[str] = []
    violations = _actual_operator_violations(spec, trace)
    if violations:
        conflict_fields = _operator_conflict_fields(spec)
        for item in violations:
            field = str(item.get("field") or "")
            if field and field in conflict_fields:
                reasons.append(f"operator_standard_conflict:{field}")

    for item in enum_completeness_evidence:
        if isinstance(item, dict) and item.get("enum_authority_candidate") is True:
            field = str(item.get("field") or item.get("condition_field") or "unknown")
            reasons.append(f"enum_authority_space:{field}")

    if unsupported_boundary_evidence.get("all_conditions_unsupported") is True:
        # 全拒：请求自身约束被整体拒绝（acknowledges_requested_constraint 的特例）。
        reasons.append("capability_or_responsibility_boundary:all_conditions_unsupported")
    elif unsupported_boundary_evidence.get("acknowledges_requested_constraint") is True:
        # 系统明确拒绝/降级了请求自身携带的约束：该约束的能力/职责归属是
        # authority 边界判断点（全部拒绝或部分保留都算），不能凭词法启发式
        # 直接落 not_evaluable/not_fulfilled（fulfilled.md §2.3/§3、§10）。
        reasons.append(
            "capability_or_responsibility_boundary:unsupported_constraint_acknowledged"
        )
    if unsupported_boundary_evidence.get("explicit_unsupported_capability") is True:
        # Key-Index Search→Load 已把请求解析到 is_supported=false 字段：
        # 即使提示文本与请求无词法重叠（请求是具体值、提示是字段标签，如
        # 093 车牌），也是确定性的能力边界判断点，必须装配 authority。
        reasons.append(
            "capability_or_responsibility_boundary:explicit_unsupported_field"
        )

    gap_hit = coverage_gap_trigger_hit(
        _load_authority_report(spec), _request_text_from_trace(trace)
    )
    if gap_hit:
        # 请求文本在调查层 material-decisions 索引中的唯一最高命中是覆盖缺口：
        # 该事项当前没有唯一决定资料（investigate-authority-judge.md §11），
        # 是确定性能力/职责边界判断点，必须装配 authority 现场裁决，不靠启发式。
        reasons.append(f"capability_or_responsibility_boundary:coverage_gap:{gap_hit}")

    reasons.extend(
        _material_conflict_reasons(
            trace, compact_manifest or {}, mapping_values or {}
        )
    )

    output = trace_extracted_output(trace) or {}
    conditions = []
    if isinstance(output, dict):
        conditions = output.get("conditions") or output.get("structured_output") or []
    if (
        _request_text_from_trace(trace)
        and not conditions
        and unsupported_boundary_evidence.get("explicit_unsupported_capability") is not True
        and unsupported_boundary_evidence.get("all_conditions_unsupported") is not True
    ):
        reasons.append("missing_semantic_carrier:empty_actual_conditions")

    return list(dict.fromkeys(reasons))



def _authority_pre_obligations(
    spec: ProjectSpec,
    *,
    trace_fields: Set[str],
    compact_manifest: Dict[str, Any],
    mapping_values: Dict[str, Any],
    enhanced_rules: Dict[str, Any],
    unsupported_boundary_evidence: Dict[str, Any],
    authority_available: bool,
) -> list[Dict[str, Any]]:
    """从 MaterialDecisions 管辖映射开列本案的前置担保义务（仅引导）。

    这里不使用 key-index，也不把相关性当管辖。项目适配层只决定当前 trace
    的业务锚点（client_search 为字段/枚举空间）；每个 governed_by 必须回到
    调查报告中真实存在的 MaterialDecision。
    """
    report = _load_authority_report(spec)
    decisions: dict[str, list[tuple[int, Any]]] = {
        material.source_ref_id: list(enumerate(material.decisions, start=1))
        for material in report.materials
    }

    obligations: list[Dict[str, Any]] = []

    def add(
        *,
        subject: Dict[str, Any],
        source_ref_id: str,
        decision_positions: tuple[int, ...],
        obligation_kind: str,
    ) -> None:
        available = decisions.get(source_ref_id) or []
        selected = [item for item in available if item[0] in decision_positions]
        if not selected:
            return
        obligations.append({
            "subject": subject,
            "obligation_kind": obligation_kind,
            "governed_by": [
                {
                    "material_decision_ref": f"{source_ref_id}#decision-{position}",
                    "conclusion_kind": decision.conclusion_kind,
                    # Judge 只需知道管辖来源；完整理由由 authority.resolve 返回，避免重复注入。
                    "governs_summary": str(decision.governs or "")[:120],
                }
                for position, decision in selected
            ],
            "authority_availability": "available" if authority_available else "unavailable",
            "effect": "依赖该主题的规范性断言时，需资料对账或 claim 担保；否则不得支撑肯定性结论。",
        })

    for field in sorted(trace_fields):
        if field not in compact_manifest:
            continue
        entry = compact_manifest[field]
        subject = {"kind": "search_field", "field": field}
        add(
            subject=subject,
            source_ref_id="business-field-definitions",
            decision_positions=(1, 2),
            obligation_kind="field_carrier_and_translation",
        )
        if isinstance(entry, dict) and entry.get("enums"):
            add(
                subject={"kind": "field_enum_space", "field": field},
                source_ref_id=(
                    "business-planfullname-enums"
                    if field == "planfullname"
                    else "business-field-enums"
                ),
                decision_positions=(1,),
                obligation_kind="enum_space",
            )
        if field in mapping_values:
            add(
                subject={"kind": "value_mapping", "field": field},
                source_ref_id="business-value-mappings",
                decision_positions=(1, 2),
                obligation_kind="spoken_value_mapping",
            )

    enhanced_fields = {
        str(item.get("field") or "")
        for values in enhanced_rules.values()
        if isinstance(values, list)
        for item in values
        if isinstance(item, dict) and item.get("field")
    }
    for field in sorted(enhanced_fields & trace_fields):
        add(
            subject={"kind": "enhanced_rule", "field": field},
            source_ref_id="business-enhanced-rules",
            decision_positions=(1,),
            obligation_kind="complex_spoken_rule",
        )

    if (
        unsupported_boundary_evidence.get("explicit_unsupported_capability") is True
        or unsupported_boundary_evidence.get("all_conditions_unsupported") is True
    ):
        add(
            subject={"kind": "evaluation_boundary", "scope": "parser_vs_downstream"},
            source_ref_id="project-judge-boundary-source",
            decision_positions=(1, 2),
            obligation_kind="capability_or_responsibility_boundary",
        )

    # 以规范化 subject + obligation_kind 去重，保持稳定顺序。
    unique: dict[str, Dict[str, Any]] = {}
    for item in obligations:
        key = json.dumps(
            [item["subject"], item["obligation_kind"]],
            ensure_ascii=False,
            sort_keys=True,
        )
        unique.setdefault(key, item)
    return list(unique.values())

def _build_core_context(
    spec: ProjectSpec,
    trace: RunTrace,
    *,
    embedding_provider: Any = None,
) -> Dict[str, Any]:
    """构造 Draft Judge 单次判定的完整上下文（含 Authority Environment）。

    Authority 按 authority.md §4.2 以宿主无关 Ports 组合：Environment 是 Core
    私有组合对象，主 LLM 只能通过 authority.resolve 工具访问；snapshot 记录
    项目/Role/Draft 资产/资料 revision/工具指纹，并写入 Tool audit。
    """
    context = build_judge_context(spec, trace) or {}
    intent_frame = build_intent_frame(spec, trace, context)
    judge_assets = resolve_role_assets(spec, "judge", use_candidate=True)
    contract_metadata = next(
        (
            item.get("metadata") or {}
            for item in judge_assets
            if item["mapping"].asset_id == "judge_business_contract"
        ),
        {},
    )
    trace_fields = _extract_fields_from_trace(trace, context.get("capability_manifest"), context.get("value_mappings"))
    compact_manifest = _compact_capability_manifest(context, trace_fields, trace=trace)
    intent_frame["capability_manifest"] = compact_manifest
    semantic_rules = _compact_semantic_rules(context, trace_fields)
    mapping_values = _compact_value_mappings(context, trace_fields)
    enhanced = retrieve_enhanced_rules_for_fields(
        trace_fields,
        spec_id=spec.project_id,
    )
    critical_dimensions = (
        intent_frame.get("critical_intent_dimensions")
        or context.get("critical_intent_dimensions")
    )
    enum_completeness_evidence = _enum_completeness_evidence(trace, compact_manifest)
    unsupported_boundary_evidence = _enrich_unsupported_boundary_evidence(
        spec, trace, _unsupported_boundary_evidence(trace)
    )

    comparison = condition_comparison(spec, trace)
    authority_candidate_reasons = _authority_candidate_reasons(
        spec,
        trace,
        enum_completeness_evidence=enum_completeness_evidence,
        unsupported_boundary_evidence=unsupported_boundary_evidence,
        compact_manifest=compact_manifest,
        mapping_values=mapping_values,
    )
    authority_enabled = bool(
        ((spec.verifier or {}).get("authority") or {}).get("enabled", True)
    )
    authority_candidate_present = bool(authority_candidate_reasons) or embedding_provider is not None
    authority_required = authority_enabled and authority_candidate_present
    if embedding_provider is not None and not authority_candidate_reasons:
        authority_candidate_reasons = ["explicit_embedding_provider"]
    authority_pre_obligations = (
        _authority_pre_obligations(
            spec,
            trace_fields=trace_fields,
            compact_manifest=compact_manifest,
            mapping_values=mapping_values,
            enhanced_rules=enhanced,
            unsupported_boundary_evidence=unsupported_boundary_evidence,
            authority_available=True,
        )
        if authority_required
        else []
    )

    system_extras = [
        (
            "## Judge 决策顺序\n"
            "先派生用户真正要办成的 blocking 核心业务交付，再逐项比较 actual。"
            "安全拒绝、透明说明、不编造条件只能作为独立 non-blocking 验收项，不能替代核心交付；"
            "overall 必须由 blocking assessments 聚合。"
            "证据充分时只判 fulfilled/not_fulfilled；仅职责外、输入不可用或决定性证据确实不足时判 not_evaluable。"
            "HTTP 状态、历史 verdict 和归因信息不得替代 expected-vs-actual 判断。"
        ),
        (
            "## not_evaluable 成因契约（fulfilled.md §2.3/§10、authority.md §8.4）\n"
            "判 not_evaluable 时，必须在对应 assessment 的 actual_evidence 中显式写明成因标签，"
            "只允许五种：「结论类型：职责外」「结论类型：完全无关」「结论类型：依据不充分」"
            "「结论类型：输入坏」「结论类型：Authority 能力不可用」。"
            "Authority 开启时，职责外/职责内能力缺失/依据不充分必须真实调用 authority.resolve"
            "（在 authority_tool_call_ids 引用该次调用）；依据不充分同时给出缺料清单。"
            "Authority 关闭时不得自行声明这些治理结论，也不得仅因缺少 Authority 把用户效果判为 not_evaluable；"
            "应依据用户意图与当前实际交付判 fulfilled/not_fulfilled。"
            "完全无关/输入坏不需要 authority。缺标签或标签不可识别的 not_evaluable 会被标 "
            "needs_human_review（不静默放行）。"
        ),
        (
            "## client_search 直接证据\n"
            "只评价当前 parser_condition_semantics_only 边界内的客户搜索条件。\n"
            "### 意图拆解（先定目标再判交付）\n"
            "先写出用户最终要得到的客户集合与每个核心约束（字段、操作符、值/单位、AND/OR 逻辑），"
            "再据此派生 business_expectations；每个可独立判断的请求维度拆一条 expectation，"
            "核心交付的 expected_outcome 必须描述用户最终要得到的客户集合/筛选条件/可执行搜索结果。\n"
            "### 逐项核对\n"
            "每个 expectation 逐维度对照 actual：条件缺失、错误映射、无依据的额外收窄分别判 "
            "not_fulfilled；wrong/missing/extra 必须来自当前 actual，不能来自猜测、历史 verdict 或归因信息。"
            "### 证据分级\n"
            "证据必须分级使用，低级别证据不能单独支撑 fulfilled："
            "一级证据是 query 与 actual 本身（意图与交付的直接对照）；"
            "二级证据是权威业务口径（semantic_equivalence_rules 的等价条件形式/操作符兼容、"
            "value_mappings 的枚举全集与日期等价、enhanced_rules 中可被引用的确定性规则），"
            "只有实际引用到的二级证据才能支撑 fulfilled；"
            "三级证据是 matched_pattern、字段操作符合法性、Reference 一致——它们只解释条件如何被生成，"
            "不能单独证明用户意图已满足。字段定义只证明该字段声明的语义，名称相近或同属日期不能证明语义等价；"
            "枚举精确命中只证明值属于受控空间，不能证明该空间可被搜索消费；SearchHit 只用于导航，Load 后的"
            "内容也只能证明其明确声明的事项。意图约束与 actual 条件语义直接一致、不依赖映射/等价判断时，"
            "一级证据即可支撑 fulfilled。actual 使用未随附清单登记的字段名时，若 robot_text 或条件形态"
            "已明确该字段语义且与用户意图一致，不得仅因字段名不在清单中、或与清单键存在命名/别名差异而判 "
            "not_fulfilled；清单外字段按 actual 自身声明的语义核对，只有实际语义偏离意图或缺失核心约束才判 "
            "not_fulfilled。\n"
            "### 裸词规则\n"
            "请求只有裸词（无“姓名/客户/查/找/筛选”等指示词）且 actual 把该裸词当作姓名解析时，"
            "Reference 一致只说明生成路径匹配，不等于意图确认；除非存在姓名结构或语义证据"
            "（如专名、姓氏库命中、明确字段上下文），否则按未满足判 not_fulfilled。\n"
            "is_supported=false 或 actual 明确不支持某条件时，分别评价核心交付与透明边界说明，不能用说明替代核心结果。"
            "以下内容永远不能单独成为 blocking 核心交付：不错误映射、不编造条件、拒绝越界请求、告知当前限制、未识别到条件。"
            "若请求存在明确业务对象但 actual 没有可执行条件，仍要保留该对象的核心交付 expectation，"
            "Authority 关闭时按当前交付判 not_fulfilled；Authority 开启且最终判断依赖受治理标准时，"
            "先消费 Authority resolution 再判 fulfilled/not_fulfilled/not_evaluable。"
            "安全拒绝和透明说明必须另建 blocking=false 的 expectation。"
            "若 actual 只交付请求的一部分，必须按可独立判断的请求维度拆分 expectation：已交付维度照常评价；"
            "Authority 关闭时，被遗漏的 blocking 维度按实际未交付判 not_fulfilled；Authority 开启且命中"
            " coverage_gap 时只让依赖该边界的 assessment 消费 Authority，不得把已交付维度一起降级。"
        ),
        (
            "## client_search 最终输出拓扑与 fulfillment_assessments 字段约束（严格，以本节为唯一准则）\n"
            "最终只能输出一个符合 Judge LLM-owned schema 的 JSON object，禁止数组、Markdown、候选答案或对象外文字。"
            "顶层只允许 business_expectations、applicable_product_expectation_ids、fulfillment_assessments、"
            "expected、missing、wrong、extra、evidence、reasoning_summary。"
            "business_expectations 与 fulfillment_assessments 必须是独立顶层数组，并以 expectation_id 一一对齐。"
            "business_expectations[*].boundary 必须是 JSON object（没有内容就写 {}），绝不能写成数组。"
            "fulfillment_assessments[*] 只允许 expectation_id、status、score、expected_evidence、actual_evidence、"
            "downstream_impact、authority_tool_call_ids；expected_evidence/actual_evidence 必须是数组。"
            "禁止输出 overall_fulfillment、confidence、evidence_refs、authority_analysis_ids、actual；"
            "它们属于运行时代码派生/绑定字段，即使旧材料提到也不得由模型生成。"
            "只派生当前结论必需的验收项（通常 1-3 条，最多 4 条）；每条 evidence 最多 3 个短项，"
            "reasoning_summary 用不超过 180 个中文字符概括决定性依据，禁止复述输入资料。"
        ),
    ]
    if authority_required:
        system_extras.append(
            "## authority.resolve 使用规则（证据空间内现场裁决）\n"
            "本 case 存在确定性 Authority 候选信号："
            + json.dumps(authority_candidate_reasons, ensure_ascii=False)
            + "。只有这些标准冲突、枚举权威空间或能力/职责边界判断点可调用 authority.resolve。"
            "必须 Search→Load 后再消费 Evidence；SearchHit 不是 Evidence。"
            "若判决需要自己提出规范性断言，使用 claim 参数提交待担保断言："
            "工具参数必须是严格 JSON；decision_question 和 claim_statement 保持短且自包含，"
            "字符串内部不要复制带裸英文双引号的原话，必要时改用中文引号或正确 JSON 转义。"
            "supported 可消费；contradicted 不得支撑肯定性结论；ungoverned/gap_only 使依赖项 not_evaluable。"
            "能力/职责边界裁决按 resolved statement 前缀确定性消费（fulfilled.md §3/authority.md §8.3）："
            "「职责外：」→ 依赖项 not_evaluable（说不清，职责外）；"
            "「职责内能力缺失：」→ 依赖项不得 not_evaluable，期望未达成 → not_fulfilled（功能未实现=没办成）；"
            "「职责内正常：」→ 按 statement 与 basis 继续原有评价。"
            "coverage_gap:<id> 候选表示调查层已登记该事项无唯一决定资料（investigate-authority-judge.md §11）："
            "若导航命中该缺口且未找到 required_evidence 所要求类型的新决定性证据，必须 unresolved"
            "（依据不充分→not_evaluable + 缺料清单），不得用缺口依据本身宣布 resolved。"
            "不带 claim 的 resolved/unresolved 提问模式仍可用于先确定业务问题。"
            "工具失败不得伪装成 unresolved 或 gap_only。"
            f"字段 Key-Index Search→Load 导航合计最多 {_FIELD_NAVIGATION_CALL_LIMIT} 次；"
            "不要用同义词反复扩搜。若候选信号对应的 blocking 结论仍依赖受治理断言，"
            "必须停止字段导航并至少保留一次总工具预算给 authority.resolve。"
        )
    elif authority_candidate_present:
        system_extras.append(
            "## Authority 状态\n"
            "本 case 存在可能影响语义、等价、能力或职责判断的 Authority 候选信号，但 "
            "verifier.authority.enabled=false，因此不提供 authority.resolve。不得声称职责内外、"
            "正式语义或资料优先级已获权威确认；仍须依据用户意图与 Live 当前可见交付完成效果评价，"
            "核心结果未交付或 blocking 维度缺失时判 not_fulfilled，不得仅因 Authority 关闭或存在"
            "边界候选而判 not_evaluable。"
        )
    else:
        system_extras.append(
            "## Authority 状态\n"
            "本 case 无标准冲突、权威枚举空间或能力/职责边界候选信号，不提供 authority.resolve；"
            "请直接依据随附结构化资料完成判断，不得虚构 authority_tool_call_ids。"
        )

    authority_env = None
    authority_tool = None
    tools = list(_build_judge_tools(spec))
    environment_snapshot_sha256 = ""
    if authority_required:
        authority_env = build_authority_environment(
            spec,
            role="judge",
            use_candidate=True,
            embedding_provider=embedding_provider,
            trace_id=str(trace.trace_id or ""),
            case_id=str(getattr(trace, "case_id", "") or ""),
            gateway_tools=_build_field_tools(spec),
            # Draft candidate runtime records business-source drift and
            # continues; Solidify/Promotion keep the strict default.
            business_source_staleness_policy="warn",
        )
        authority_tool = build_authority_resolve_tool(authority_env)
        tools += build_agno_tools([authority_tool.as_verifiable_tool()])
        environment_snapshot_sha256 = authority_env.environment_snapshot_sha256

    dimension_expectation_ids = contract_metadata.get("dimension_expectation_ids") or {}
    authority_obligation_contract = (
        {
            "triggers": authority_candidate_reasons,
            "pre_obligations": authority_pre_obligations,
            "pre_obligation_role": "guidance_only; post-decision audit remains authoritative",
            "required_consumption": {
                "resolved": "consume statement for dependent assessment",
                "unresolved": "dependent assessment => not_evaluable",
                "tool_failure": "side cannot support an affirmative verdict",
                "not_called": "no affirmative verdict when a blocking conclusion depends on the trigger",
            },
            "expectation_topology": {
                "core_delivery": "blocking; expected_outcome must be the user's requested business result, not merely error avoidance",
                "safe_refusal_or_transparency": "non_blocking; create separately and never let it replace core delivery",
                "empty_actual_conditions": "retain the requested business result as blocking and set it not_evaluable unless a resolved Authority conclusion or frozen MaterialDecision proves the boundary",
            },
        }
        if authority_required
        else {
            "triggers": authority_candidate_reasons,
            "authority_available": False,
            "required_action": (
                "evaluate user intent against the observable Live delivery and prefer "
                "fulfilled/not_fulfilled; do not claim governed semantics or emit not_evaluable "
                "merely because Authority is disabled or a boundary candidate exists"
            ),
        }
    )
    user_prompt_extras = {
        "capability_manifest": compact_manifest,
        "semantic_equivalence_rules": semantic_rules,
        "value_mappings": mapping_values,
        "enhanced_rules": enhanced,
        "critical_intent_dimensions": critical_dimensions,
        "enum_completeness_evidence": enum_completeness_evidence,
        "unsupported_boundary_evidence": unsupported_boundary_evidence,
        "condition_comparison": comparison,
        "product_use_scenarios": contract_metadata.get("product_use_scenarios") or {},
        "authority_environment_snapshot_sha256": environment_snapshot_sha256,
        "authority_mode": (
            "on_demand"
            if authority_required
            else "disabled_with_candidates"
            if authority_candidate_present
            else "not_required"
        ),
    }
    if authority_required:
        # Authority 关闭/未命中时，候选理由与义务契约只描述“存在冲突候选”，
        # 会把模型拖向规则自证/过早 not_evaluable；此时只留 mode 标记，
        # 系统提示里的 Authority 状态块已给出“按意图判 F/NF”的守则。
        user_prompt_extras["authority_candidate_reasons"] = authority_candidate_reasons
        user_prompt_extras["authority_obligation_contract"] = authority_obligation_contract
    return {
        "user_intent": context.get("user_intent"),
        "intent_frame": intent_frame,
        "system_prompt_extras": system_extras,
        "authority_environment": authority_env,
        "authority_tool": authority_tool,
        "environment_snapshot_sha256": environment_snapshot_sha256,
        "product_expectation_ids": contract_metadata.get("product_expectation_ids") or [],
        "evaluation_dimension_ids": contract_metadata.get("dimensions") or [],
        "dimension_expectation_ids": dimension_expectation_ids,
        "tool_call_limit": _JUDGE_TOOL_CALL_LIMIT,
        "user_prompt_extras": to_dict(user_prompt_extras),
        "comparator_result": comparison,
        "protocol_tool_results": [comparison],
        "tools": tools,
        "context_governance": {
            "enabled": True,
            "mode": "draft",
            "role": "judge",
            "stage": "judge",
            "compiler_source": "impl/projects/client_search/draft/judge_execution.py#judge_trace",
            "user_source": "trace://judge-evidence-view",
            "runtime_owned_fields": [
                "overall_fulfillment",
                "actual",
                "fulfillment_assessments[*].confidence",
                "business_expectations[*].evidence_refs",
                "fulfillment_assessments[*].evidence_refs",
                "fulfillment_assessments[*].authority_analysis_ids",
            ],
            "excluded_clause_markers": ["`JudgeResult` 协议字段"],
            "required_tools": ["authority.resolve"] if authority_required else [],
            "max_prompt_chars": 160000,
            "segments": [
                {
                    "segment_id": f"client-search-draft-system-extra-{index + 1}",
                    "source": "project://draft/judge.py#system_prompt_extras",
                    "content": content,
                }
                for index, content in enumerate(system_extras)
            ],
        },
    }


class ClientSearchJudge(ProjectJudge):
    def __init__(self, spec: ProjectSpec):
        super().__init__(spec)

    def build_context(self, trace: RunTrace) -> dict:
        return _build_core_context(self.spec, trace)

    def judge_execution(self):
        from impl.projects.client_search.draft.judge_strategy import (
            DraftSinglePassJudgeExecution,
        )

        return DraftSinglePassJudgeExecution()

    def build_intent_frame(self, trace: RunTrace, context: Optional[dict] = None) -> dict:
        return build_intent_frame(self.spec, trace, context)

    def normalize_result(self, trace: RunTrace, result: JudgeResult) -> JudgeResult:
        return normalize_judge_result(result) or result

    def reconcile_result(self, trace: RunTrace, result: JudgeResult) -> JudgeResult:
        apply_condition_comparison(
            trace, result, condition_comparison(self.spec, trace)
        )
        _apply_operator_capability_check(self.spec, trace, result)
        result.overall_fulfillment = dict(result.overall_fulfillment or {})
        result.overall_fulfillment["status"] = _derive_overall_status(
            result.business_expectations, result.fulfillment_assessments
        )
        result.summary = summary_from_fulfillment(to_dict(result))
        return result
