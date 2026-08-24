from __future__ import annotations

import json
from typing import Any, Dict, Mapping

from impl.tools import ToolContext, ToolResult, VerifiableTool


class ClientSearchConditionCompareTool:
    tool_id = "client_search.condition_compare"
    tool_type = "comparison"

    def run(self, context: ToolContext) -> ToolResult:
        trace = context.trace
        if trace is None:
            return ToolResult(tool_id=self.tool_id, tool_type=self.tool_type, status="failed", error="trace missing")
        trace_input = trace.input if isinstance(trace.input, dict) else {}
        reference_ready = "reference" in set(trace.ready or [])
        reference = (
            trace.reference_contract
            if reference_ready
            and isinstance(trace.reference_contract, dict)
            and trace.reference_contract
            else trace_input.get("reference")
            if reference_ready and isinstance(trace_input.get("reference"), dict)
            else {}
        )
        reference_conditions = reference.get("expected_conditions") or []
        reference_is_oracle = bool(reference.get("is_current_oracle") or reference.get("oracle") == "current")
        if reference_is_oracle:
            expected_conditions = reference_conditions
            expected_source = "reference_oracle"
            query_logic = reference.get("expected_logic") or reference.get("logic") or "AND"
        elif reference_conditions:
            # A historical or non-oracle reference is evidence about another answer,
            # not a business standard for this case.  Keep it visible in ``expected``
            # for audit, but do not compare actual against it.
            expected_conditions = []
            expected_source = "reference_evidence"
            query_logic = reference.get("expected_logic") or reference.get("logic") or "AND"
        else:
            expected_conditions = []
            expected_source = "reference_evidence" if reference_conditions else "not_available"
            query_logic = reference.get("expected_logic") or reference.get("logic") or "AND"
        expected = {
            "query_logic": query_logic,
            "conditions": expected_conditions,
            "expected_source": expected_source,
            "reference_conditions": reference_conditions,
            "reference_is_oracle": reference_is_oracle,
        }
        extracted_output = trace.extracted_output or {}
        actual_conditions = (
            extracted_output.get("conditions")
            if isinstance(extracted_output.get("conditions"), list)
            else extracted_output.get("structured_output")
            if isinstance(extracted_output.get("structured_output"), list)
            else []
        )
        actual = {
            "query_logic": extracted_output.get("query_logic") or extracted_output.get("logic") or "AND",
            "conditions": actual_conditions,
        }
        equivalence_rules = (
            context.spec.verifier_extra_value("semantic_equivalence_rules", {})
            if context.spec
            else {}
        )
        # Include operator_compatibility from project.yaml via semantic_equivalence_rules
        wrong, missing, extra = self._compare(expected, actual, equivalence_rules) if expected_conditions else ([], [], [])
        boundary_limits = []
        if reference.get("allow_empty_conditions") and not expected["conditions"]:
            boundary_limits.append({"reason": reference.get("expected_reason") or "empty conditions allowed by project boundary"})
        status = "succeeded"
        evaluable = bool(expected_conditions)
        outputs = {
            "target_population": self._query_text(trace.input, trace.normalized_request, trace.extracted_output),
            "expected": expected,
            "actual": actual,
            "wrong": wrong,
            "missing": missing,
            "extra": extra,
            "extra_or_overbroad": extra,
            "boundary_limits": boundary_limits,
            "comparison_basis": "client_search wrong/missing/extra customer-search coverage",
            "expected_source": expected.get("expected_source"),
            "evaluable": evaluable,
            "expected_source_label": expected_source,
        }
        missing_evidence = [] if evaluable else [{"reason": "current intent/config expected conditions unavailable; reference expected_conditions kept as evidence only", "expected_source": expected_source}]
        evidence = [
            {"query": outputs["target_population"]},
            {"expected": expected},
            {"actual": actual},
            {"wrong": wrong, "missing": missing, "extra": extra, "boundary_limits": boundary_limits},
        ]
        return ToolResult(tool_id=self.tool_id, tool_type=self.tool_type, status=status, outputs=outputs, evidence=evidence, missing_evidence=missing_evidence, boundary_limits=boundary_limits)

    def _query_text(self, input_data: Mapping[str, Any], normalized_request: Mapping[str, Any], extracted_output: Mapping[str, Any]) -> str:
        nested = input_data.get("input") if isinstance(input_data.get("input"), dict) else {}
        return str(input_data.get("query") or nested.get("query") or normalized_request.get("user_text") or extracted_output.get("source_query") or "")

    def _compare(self, expected: Dict[str, Any], actual: Dict[str, Any], equivalence_rules: dict | None = None) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]], list[Dict[str, Any]]]:
        expected_conditions = [self._canonical_condition(item) for item in expected.get("conditions") or []]
        actual_conditions = [self._canonical_condition(item) for item in actual.get("conditions") or []]
        missing = []
        wrong = []
        extra = []
        matched_actual = set()
        for expected_index, expected_condition in enumerate(expected_conditions):
            exact_index = self._find_exact(expected_condition, actual_conditions, matched_actual)
            if exact_index is not None:
                matched_actual.add(exact_index)
                continue
            field_index = self._find_same_field(expected_condition, actual_conditions, matched_actual, equivalence_rules)
            if field_index is not None:
                matched_actual.add(field_index)
                actual_condition = actual_conditions[field_index]
                reason = self._wrong_reason(expected_condition, actual_condition, equivalence_rules)
                if reason:
                    wrong.append(
                        {
                            "type": "wrong_condition",
                            "expected_fragment": expected_condition,
                            "actual_fragment": actual_condition,
                            "reason": reason,
                        }
                    )
                continue
            missing.append({"type": "missing_condition", "expected_fragment": expected_condition, "reason": "用户目标客户集合需要该筛选条件，但 actual 未输出对应字段条件。"})
        for actual_index, actual_condition in enumerate(actual_conditions):
            if actual_index not in matched_actual:
                extra.append({"type": "extra_or_overbroad_condition", "actual_fragment": actual_condition, "reason": "actual 输出包含未被目标客户意图要求的条件，可能导致筛选范围过窄、过宽或偏离目标客户。"})
        expected_logic = expected.get("query_logic") or "AND"
        actual_logic = actual.get("query_logic") or "AND"
        if expected_conditions and actual_conditions and expected_logic != actual_logic:
            wrong.append({"type": "wrong_query_logic", "expected_fragment": expected_logic, "actual_fragment": actual_logic, "reason": "AND/OR 逻辑不一致会改变目标客户集合覆盖范围。"})
        return wrong, missing, extra
    def _find_exact(self, expected_condition: Dict[str, Any], actual_conditions: list[Dict[str, Any]], matched_actual: set[int]) -> int | None:
        for index, actual_condition in enumerate(actual_conditions):
            if index not in matched_actual and actual_condition == expected_condition:
                return index
        return None

    def _find_same_field(self, expected_condition: Dict[str, Any], actual_conditions: list[Dict[str, Any]], matched_actual: set[int], equivalence_rules: dict | None = None) -> int | None:
        for index, actual_condition in enumerate(actual_conditions):
            if index not in matched_actual and actual_condition.get("field") == expected_condition.get("field"):
                return index
        # Check equivalent_fields rules
        if equivalence_rules:
            eq_fields = equivalence_rules.get("equivalent_fields") or []
            for rule in eq_fields:
                if expected_condition.get("field") == rule.get("field"):
                    for index, actual_condition in enumerate(actual_conditions):
                        if index not in matched_actual and actual_condition.get("field") == rule.get("equivalent_field"):
                            return index
                elif expected_condition.get("field") == rule.get("equivalent_field"):
                    for index, actual_condition in enumerate(actual_conditions):
                        if index not in matched_actual and actual_condition.get("field") == rule.get("field"):
                            return index
        return None

    def _canonical_condition(self, condition: Any) -> Dict[str, Any]:
        if not isinstance(condition, dict):
            return {"value": condition}
        value = condition.get("value")
        return {
            "field": condition.get("field"),
            "operator": condition.get("operator"),
            "value": json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True)),
        }

    def _wrong_reason(self, expected_condition: Dict[str, Any], actual_condition: Dict[str, Any], equivalence_rules: dict | None = None) -> str:
        if expected_condition.get("operator") != actual_condition.get("operator"):
            # Check operator_compatibility before calling it wrong
            if equivalence_rules:
                compat_rules = equivalence_rules.get("operator_compatibility") or []
                for rule in compat_rules:
                    rule_field = rule.get("field", "")
                    if rule_field not in ("*", "", expected_condition.get("field", "")):
                        continue
                    if (expected_condition.get("operator") == rule.get("operator") and actual_condition.get("operator") == rule.get("equivalent_operator")) or                        (actual_condition.get("operator") == rule.get("operator") and expected_condition.get("operator") == rule.get("equivalent_operator")):
                        # Operators are compatible; verify single-value equivalence
                        if self._values_single_equivalent(expected_condition.get("value"), actual_condition.get("value")):
                            return ""  # Compatible operators with equivalent values
                        return "操作符兼容但值不等价：多值列表与单值不匹配。"
            return "字段相同但操作符错误，会改变目标客户集合。"
        if expected_condition.get("value") != actual_condition.get("value"):
            return "字段相同但值或枚举值错误，筛选出来的客户不是目标客户或覆盖范围不正确。"
        return "字段条件语义不一致。"

    @staticmethod
    def _values_single_equivalent(expected_value: Any, actual_value: Any) -> bool:
        """Check if values are equivalent under single-value MATCH/CONTAINS semantics.

        A single-element list ["X"] is equivalent to scalar "X".
        """
        # Normalize: unwrap single-element lists
        ev = expected_value[0] if isinstance(expected_value, list) and len(expected_value) == 1 else expected_value
        av = actual_value[0] if isinstance(actual_value, list) and len(actual_value) == 1 else actual_value
        return ev == av


def build_condition_compare_verifiable_tool() -> VerifiableTool:
    """Expose the current-case authority resolver to investigation Solidify."""

    def execute(
        *,
        expected_conditions: list[Dict[str, Any]],
        actual_conditions: list[Dict[str, Any]],
        expected_is_current_oracle: bool,
        expected_logic: str = "AND",
        actual_logic: str = "AND",
    ) -> ToolResult:
        expected = {
            "query_logic": expected_logic or "AND",
            "conditions": expected_conditions or [],
        }
        actual = {
            "query_logic": actual_logic or "AND",
            "conditions": actual_conditions or [],
        }
        comparison = ClientSearchConditionCompareTool()
        wrong, missing, extra = (
            comparison._compare(expected, actual, {})
            if expected_is_current_oracle and expected["conditions"]
            else ([], [], [])
        )
        evaluable = bool(expected_is_current_oracle and expected["conditions"])
        return ToolResult(
            tool_id=ClientSearchConditionCompareTool.tool_id,
            tool_type="comparison",
            status="succeeded",
            outputs={
                "expected": expected,
                "actual": actual,
                "wrong": wrong,
                "missing": missing,
                "extra": extra,
                "evaluable": evaluable,
            },
            missing_evidence=(
                []
                if evaluable
                else [{
                    "reason": (
                        "current oracle expected conditions are required to "
                        "resolve semantic mapping for the current case"
                    )
                }]
            ),
        )

    return VerifiableTool(
        tool_id=ClientSearchConditionCompareTool.tool_id,
        description=(
            "Compare current-case oracle conditions with actual conditions and "
            "emit a scope-local semantic-mapping resolution claim."
        ),
        applicable_scenario=(
            "Judge has a current-case oracle and needs deterministic evidence "
            "for the semantic mapping authority gate."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expected_conditions": {
                    "type": "array",
                    "description": "Current-case oracle conditions.",
                    "items": {"type": "object"},
                },
                "actual_conditions": {
                    "type": "array",
                    "description": "Conditions emitted by Live for the same case.",
                    "items": {"type": "object"},
                },
                "expected_is_current_oracle": {
                    "type": "boolean",
                    "description": "Whether expected_conditions are the current case oracle.",
                },
                "expected_logic": {
                    "type": "string",
                    "description": "Boolean logic in the current-case oracle.",
                },
                "actual_logic": {
                    "type": "string",
                    "description": "Boolean logic in the Live output.",
                },
            },
            "required": [
                "expected_conditions",
                "actual_conditions",
                "expected_is_current_oracle",
            ],
        },
        execute_fn=execute,
    )
