from __future__ import annotations

import copy
import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

from .hashing import stable_sha256
from .structured_output import StructuredOutputSpec, render_output_constraint


_SCHEMA_MARKER = "你的输出必须是合法 JSON，且严格符合以下 JSON Schema："
_ALLOW_MARKERS = ("只允许", "只能产", "必须输出", "输出使用")
_FORBID_MARKERS = ("禁止输出", "不要输出", "不得输出")

# 手写输出形状/字段清单（第二真相源）的确定性识别模式。只匹配"结构约束句式"，
# 语义指令（证据必须引用、不得生成 ref_id、分析必须中文等）不含这些句式，不会误报。
_MANUAL_SHAPE_PATTERNS = (
    re.compile(r"输出 JSON，只(?:包含|含|输出|填)[:：]?\s*([^。\n]+)"),
    re.compile(r"最终只输出 JSON[:：]?\s*([^。\n]+)"),
    re.compile(r"最终只输出\s*([^。\n]+)"),
    re.compile(r"只输出 JSON[:：]?\s*([^。\n]+)"),
    re.compile(r"只能输出 JSON[:：]\s*([^。\n]+)"),
    re.compile(r"输出 JSON，字段[:：]\s*([^。\n]+)"),
    re.compile(r"只输出\s*([^。\n]+)"),
    re.compile(r"必填字段列表[:：]\s*([^。\n]+)"),
)
_SCHEMA_TYPE_TOKENS = frozenset({
    "str", "int", "float", "bool", "list", "dict", "json",
    "string", "number", "boolean", "array", "object", "null",
})
_FINDING_STATES = {
    "open": frozenset({"remediation_ready", "waived"}),
    "remediation_ready": frozenset({"verified", "open"}),
    "verified": frozenset({"closed", "open"}),
    "closed": frozenset(),
    "waived": frozenset({"open"}),
}


class ContextGovernanceBlocked(RuntimeError):
    """Raised before a Draft LLM call when deterministic context checks fail."""

    def __init__(self, report: Mapping[str, Any]):
        self.report = copy.deepcopy(dict(report))
        codes = [
            str(item.get("code") or "context_governance_blocked")
            for item in report.get("findings") or []
            if item.get("severity") == "blocking" and item.get("status") == "open"
        ]
        super().__init__(
            "context governance blocked Draft before LLM execution: "
            + ", ".join(codes)
        )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _tool_descriptor(tool: Any) -> dict[str, str]:
    entrypoint = getattr(tool, "entrypoint", None)
    logical_id = str(getattr(entrypoint, "logical_tool_id", "") or "")
    runtime_name = str(getattr(tool, "name", "") or "")
    if not runtime_name:
        runtime_name = str(getattr(tool, "__name__", "") or type(tool).__name__)
    return {
        "logical_id": logical_id or runtime_name,
        "runtime_name": runtime_name,
    }


def _schema_field_names(schema: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    stack: list[Any] = [schema]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        if not isinstance(current, Mapping) or id(current) in seen:
            continue
        seen.add(id(current))
        properties = current.get("properties")
        if isinstance(properties, Mapping):
            result.update(str(key) for key in properties)
        for key in ("properties", "$defs"):
            value = current.get(key)
            if isinstance(value, Mapping):
                stack.extend(value.values())
        for key in ("items", "anyOf", "oneOf", "allOf"):
            value = current.get(key)
            if isinstance(value, Mapping):
                stack.append(value)
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                stack.extend(value)
    return result


def _schema_field_paths(schema: Mapping[str, Any]) -> set[str]:
    """Return only paths reachable from the root schema, resolving local refs."""

    result: set[str] = set()
    # Track definitions on the current recursion stack independently of their
    # rendered path.  A recursive $ref otherwise keeps producing ever-longer
    # prefixes (for example ``children[*].children[*]``) and never converges.
    active: set[int] = set()

    def resolve(node: Mapping[str, Any]) -> Mapping[str, Any]:
        reference = str(node.get("$ref") or "")
        if reference.startswith("#/$defs/"):
            target = (schema.get("$defs") or {}).get(reference.rsplit("/", 1)[-1])
            if isinstance(target, Mapping):
                return target
        return node

    def walk(node: Any, prefix: str) -> None:
        if not isinstance(node, Mapping):
            return
        node = resolve(node)
        key = id(node)
        if key in active:
            return
        active.add(key)
        alternatives = node.get("anyOf") or node.get("oneOf") or node.get("allOf")
        if isinstance(alternatives, Sequence) and not isinstance(alternatives, (str, bytes)):
            for item in alternatives:
                walk(item, prefix)
        properties = node.get("properties")
        if isinstance(properties, Mapping):
            for name, child in properties.items():
                path = f"{prefix}.{name}" if prefix else str(name)
                result.add(path)
                walk(child, path)
        items = node.get("items")
        if isinstance(items, Mapping):
            walk(items, f"{prefix}[*]" if prefix else "[*]")
        active.remove(key)

    walk(schema, "")
    return result


def _segment_snapshot(
    segment: Mapping[str, Any],
    *,
    index: int,
    default_role: str,
    default_stage: str,
) -> dict[str, Any]:
    content = str(segment.get("content") or "")
    allowed_roles = [str(item) for item in segment.get("allowed_roles") or [default_role]]
    allowed_stages = [str(item) for item in segment.get("allowed_stages") or [default_stage]]
    snapshot = {
        "segment_id": str(segment.get("segment_id") or f"segment-{index + 1}"),
        "source": str(segment.get("source") or ""),
        "role": str(segment.get("role") or default_role),
        "stage": str(segment.get("stage") or default_stage),
        "order": index,
        "char_count": len(content),
        "content_sha256": _sha256_text(content),
        "allowed_roles": allowed_roles,
        "allowed_stages": allowed_stages,
    }
    for key in ("protocol_version", "transform", "runtime_visibility"):
        if segment.get(key) not in (None, ""):
            snapshot[key] = segment.get(key)
    return snapshot


def build_context_governance_report(
    *,
    project_id: str,
    role: str,
    stage: str,
    mode: str,
    system: str,
    user: str,
    output_spec: StructuredOutputSpec,
    tools: Iterable[Any] = (),
    segments: Iterable[Mapping[str, Any]] = (),
    excluded_segments: Iterable[Mapping[str, Any]] = (),
    runtime_owned_fields: Iterable[str] = (),
    required_segments: Iterable[str] = (),
    required_tools: Iterable[str] = (),
    max_prompt_chars: int | None = None,
    reprompt: Mapping[str, Any] | None = None,
    trace_id: str = "",
    case_id: str = "",
    call_id: str = "",
    compiler_id: str = "context-compiler-v1",
    compiler_protocol_version: int = 1,
) -> dict[str, Any]:
    """Build a replayable prompt snapshot and run deterministic checks.

    Full prompt text remains in ContextStore.  This report stores identities,
    ordering, sizes, hashes and findings so it does not become a second prompt
    archive or a new runtime knowledge bundle.
    """

    normalized_mode = str(mode or "production").strip().lower()
    if normalized_mode not in {"production", "draft"}:
        raise ValueError("context governance mode must be production or draft")
    schema = output_spec.json_schema()
    constraint = render_output_constraint(output_spec)
    final_system = system + "\n\n" + constraint
    segment_items = [
        _segment_snapshot(item, index=index, default_role=role, default_stage=stage)
        for index, item in enumerate(segments)
    ]
    excluded_items = [
        {
            "segment_id": str(item.get("segment_id") or f"excluded-{index + 1}"),
            "source": str(item.get("source") or ""),
            "reason": str(item.get("reason") or "deterministic project compiler exclusion"),
            "char_count": len(str(item.get("content") or "")),
            "content_sha256": _sha256_text(str(item.get("content") or "")),
        }
        for index, item in enumerate(excluded_segments)
    ]
    tool_plan = [_tool_descriptor(tool) for tool in tools]
    snapshot = {
        "schema_version": 1,
        "project_id": str(project_id),
        "role": str(role),
        "stage": str(stage),
        "mode": normalized_mode,
        "lineage": {
            "trace_id": str(trace_id or ""),
            "case_id": str(case_id or ""),
            "call_id": str(call_id or ""),
        },
        "compiler_id": str(compiler_id or "context-compiler-v1"),
        "compiler_protocol_version": int(compiler_protocol_version),
        "output_contract": {
            "identity": f"{output_spec.model.__module__}.{output_spec.model.__qualname__}",
            "sha256": stable_sha256(schema),
            "field_names": sorted(_schema_field_names(schema)),
            "parser_identity": "impl.core.schema_validator.SchemaValidator",
            "parser_schema_sha256": stable_sha256(schema),
        },
        "messages": [
            {
                "role": "system",
                "char_count": len(final_system),
                "content_sha256": _sha256_text(final_system),
            },
            {
                "role": "user",
                "char_count": len(user),
                "content_sha256": _sha256_text(user),
            },
        ],
        "compiled_prompt_sha256": stable_sha256([
            {"role": "system", "content": final_system},
            {"role": "user", "content": user},
        ]),
        "prompt_char_count": len(final_system) + len(user),
        "segments": segment_items,
        "excluded_segments": excluded_items,
        "tool_plan": tool_plan,
        "reprompt": dict(reprompt or {"occurred": False, "added_char_count": 0}),
    }
    findings = scan_compiled_context(
        snapshot=snapshot,
        system=final_system,
        schema=schema,
        runtime_owned_fields=runtime_owned_fields,
        required_segments=required_segments,
        required_tools=required_tools,
        max_prompt_chars=max_prompt_chars,
    )
    return {
        "schema_version": 1,
        "snapshot": snapshot,
        "findings": findings,
        "gate": {
            "mode": normalized_mode,
            "blocking": any(
                item["severity"] == "blocking" and item["status"] == "open"
                for item in findings
            ),
        },
    }


def _finding(
    *,
    code: str,
    severity: str,
    problem: str,
    evidence: Sequence[Mapping[str, Any]],
    impact: str,
    owner: str,
    remediation: str,
    blocked_stage: str,
) -> dict[str, Any]:
    evidence_items = [dict(item) for item in evidence]
    identity = stable_sha256([code, evidence_items, blocked_stage])[:16]
    return {
        "finding_id": f"context:{code}:{identity}",
        "code": code,
        "severity": severity,
        "problem": problem,
        "evidence": evidence_items,
        "impact": impact,
        "owner": {"primary": owner, "contributing": []},
        "remediation": remediation,
        "blocked_stage": blocked_stage,
        "status": "open",
        "verification_evidence": [],
    }


def scan_compiled_context(
    *,
    snapshot: Mapping[str, Any],
    system: str,
    schema: Mapping[str, Any],
    runtime_owned_fields: Iterable[str] = (),
    required_segments: Iterable[str] = (),
    required_tools: Iterable[str] = (),
    max_prompt_chars: int | None = None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    schema_paths = _schema_field_paths(schema)
    # Unqualified top-level ownership instructions remain scoped to top-level
    # fields; configured runtime-owned paths preserve nested ownership such as
    # ``fulfillment_assessments[*].confidence``.
    properties = schema.get("properties")
    top_level_fields = {
        str(key) for key in properties
    } if isinstance(properties, Mapping) else set()
    runtime_paths = {str(item).strip() for item in runtime_owned_fields if str(item).strip()}
    runtime_terminals = {
        path: path.rsplit(".", 1)[-1].replace("[*]", "")
        for path in runtime_paths
    }
    ownership_overlap = sorted(runtime_paths & schema_paths)
    if ownership_overlap:
        findings.append(_finding(
            code="output_ownership_schema_conflict",
            severity="blocking",
            problem="Runtime-owned fields are present in the LLM-owned output schema.",
            evidence=[{"field_paths": ownership_overlap}],
            impact="The same output path has two owners before prompt compilation.",
            owner="core_compiler",
            remediation="Remove the path from one ownership contract and regenerate the schema identity.",
            blocked_stage=str(snapshot.get("stage") or "draft_loop"),
        ))

    marker_count = system.count(_SCHEMA_MARKER)
    if marker_count != 1:
        findings.append(_finding(
            code="output_contract_count",
            severity="blocking",
            problem="The compiled prompt must contain exactly one rendered output contract.",
            evidence=[{"schema_marker_count": marker_count}],
            impact="The model cannot know which output schema is authoritative.",
            owner="core_compiler",
            remediation="Render the registered StructuredOutputSpec exactly once.",
            blocked_stage=str(snapshot.get("stage") or "draft_loop"),
        ))

    schema_field_names = _schema_field_names(schema)
    if not schema_field_names:
        findings.append(_finding(
            code="output_contract_empty",
            severity="blocking",
            problem="The registered output contract declares no output fields.",
            evidence=[{"field_names": []}],
            impact="The model has no defined output shape; an empty contract cannot be validated.",
            owner="project_compiler",
            remediation="Register a StructuredOutputSpec that declares at least one output field.",
            blocked_stage=str(snapshot.get("stage") or "draft_loop"),
        ))

    # 手写二次 schema 注入（§12 阶段 2 "schema 重复注入"）：统一渲染的 marker
    # 后跟换行，不会命中 `JSON Schema[:：]\s*\{`，因此该模式只匹配手写注入。
    inline_schema_injections = len(re.findall(r"JSON Schema[:：]\s*\{", system))
    if inline_schema_injections:
        findings.append(_finding(
            code="schema_duplicate_injection",
            severity="blocking",
            problem="A second JSON Schema is hand-injected into the compiled prompt.",
            evidence=[{"inline_schema_injections": inline_schema_injections}],
            impact="The model sees two rendered output schemas and cannot know which is authoritative.",
            owner="project_compiler",
            remediation="Remove the hand-written schema injection; the registered StructuredOutputSpec renders the single contract.",
            blocked_stage=str(snapshot.get("stage") or "draft_loop"),
        ))

    # 手写输出字段清单与注册 schema 重复（第二真相源，字段变化时可能漂移）。
    for line_no, line in enumerate(system.splitlines(), start=1):
        for pattern in _MANUAL_SHAPE_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            tokens = {
                token
                for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", match.group(1))
                if token not in _SCHEMA_TYPE_TOKENS
            }
            if not tokens:
                continue
            known = sorted(tokens & schema_field_names)
            if not known:
                continue
            findings.append(_finding(
                code="manual_field_list_duplicate",
                severity="high",
                problem="A hand-written output field list duplicates the registered output schema.",
                evidence=[{
                    "line": line_no,
                    "fields": known,
                    "extra_tokens": sorted(tokens - schema_field_names),
                    "text": line[:300],
                }],
                impact="The schema becomes a second truth source that can drift when fields change.",
                owner="project_compiler",
                remediation="Remove the hand-written field list; keep only semantic instructions.",
                blocked_stage=str(snapshot.get("stage") or "draft_loop"),
            ))
            break

    allowed_mentions: set[str] = set()
    forbidden_mentions: set[str] = set()
    for line_no, line in enumerate(system.splitlines(), start=1):
        allowed_marker = next((marker for marker in _ALLOW_MARKERS if marker in line), "")
        forbidden_marker = next((marker for marker in _FORBID_MARKERS if marker in line), "")
        allowed = bool(allowed_marker)
        forbidden = bool(forbidden_marker)
        if not allowed and not forbidden:
            continue
        def instruction_clause(marker: str, _line: str = line) -> str:
            if not marker:
                return ""
            instruction = _line[_line.index(marker):]
            # Ownership lists end at the first clause boundary.  Later
            # explanatory clauses may legitimately mention other fields.
            return re.split(r"[；;。]", instruction, maxsplit=1)[0]

        def mentions(value: str, text: str) -> bool:
            return bool(re.search(
                rf"(?<![A-Za-z0-9_]){re.escape(value)}(?![A-Za-z0-9_])",
                text,
            ))

        if allowed:
            instruction = instruction_clause(allowed_marker)
            mentioned_top = {field for field in top_level_fields if mentions(field, instruction)}
            mentioned_runtime = {
                path for path, terminal in runtime_terminals.items()
                if mentions(terminal, instruction)
            }
            allowed_mentions.update(mentioned_top | mentioned_runtime)
            invalid = sorted(mentioned_runtime)
            if invalid:
                findings.append(_finding(
                    code="runtime_field_claimed_by_llm",
                    severity="blocking",
                    problem="Prompt assigns runtime-owned fields to the LLM output contract.",
                    evidence=[{"line": line_no, "fields": invalid, "text": line[:500]}],
                    impact="LLM and Runtime can both claim ownership of the same output field.",
                    owner="project_compiler",
                    remediation="Remove the fields from LLM instructions or register them in the single output schema if ownership is intentional.",
                    blocked_stage=str(snapshot.get("stage") or "draft_loop"),
                ))
        if forbidden:
            instruction = instruction_clause(forbidden_marker)
            mentioned_schema = {
                path
                for path in schema_paths
                if mentions(path.rsplit(".", 1)[-1].replace("[*]", ""), instruction)
                and (
                    "." not in path
                    or mentions(path.split(".", 1)[0].replace("[*]", ""), instruction)
                )
            }
            mentioned_runtime = {
                path for path, terminal in runtime_terminals.items()
                if mentions(terminal, instruction)
            }
            forbidden_mentions.update(mentioned_schema | mentioned_runtime)
            invalid = sorted(mentioned_schema)
            if invalid:
                findings.append(_finding(
                    code="schema_field_forbidden_by_prompt",
                    severity="blocking",
                    problem="Prompt forbids fields that the registered output schema permits.",
                    evidence=[{"line": line_no, "fields": invalid, "text": line[:500]}],
                    impact="The output contract is internally contradictory.",
                    owner="project_compiler",
                    remediation="Align the prompt with the registered StructuredOutputSpec.",
                    blocked_stage=str(snapshot.get("stage") or "draft_loop"),
                ))
    contradictory = sorted(allowed_mentions & forbidden_mentions)
    if contradictory:
        findings.append(_finding(
            code="field_instruction_conflict",
            severity="blocking",
            problem="The same output field is both allowed and forbidden in the compiled prompt.",
            evidence=[{"fields": contradictory}],
            impact="The model receives mutually exclusive field ownership instructions.",
            owner="project_compiler",
            remediation="Keep one ownership rule derived from the registered output schema.",
            blocked_stage=str(snapshot.get("stage") or "draft_loop"),
        ))

    role = str(snapshot.get("role") or "")
    stage = str(snapshot.get("stage") or "")
    compiler_protocol_version = int(snapshot.get("compiler_protocol_version") or 0)
    for segment in snapshot.get("segments") or []:
        missing = [key for key in ("segment_id", "source", "content_sha256") if not segment.get(key)]
        if missing:
            findings.append(_finding(
                code="segment_not_traceable",
                severity="blocking",
                problem="A compiled context segment cannot be traced to a stable source.",
                evidence=[{"segment_id": segment.get("segment_id"), "missing": missing}],
                impact="The prompt cannot be reconstructed or audited reliably.",
                owner="project_compiler",
                remediation="Register segment ID, source and content hash before compilation.",
                blocked_stage=stage,
            ))
        if role not in set(segment.get("allowed_roles") or []):
            findings.append(_finding(
                code="role_context_leak",
                severity="blocking",
                problem="A context segment is not authorized for the current role.",
                evidence=[{"segment_id": segment.get("segment_id"), "role": role, "allowed_roles": segment.get("allowed_roles")}],
                impact="Private context from another role can bias the Judge.",
                owner="project_compiler",
                remediation="Exclude the segment or correct its role policy at Solidify.",
                blocked_stage=stage,
            ))
        if stage not in set(segment.get("allowed_stages") or []):
            findings.append(_finding(
                code="stage_context_leak",
                severity="blocking",
                problem="A context segment is not authorized for the current stage.",
                evidence=[{"segment_id": segment.get("segment_id"), "stage": stage, "allowed_stages": segment.get("allowed_stages")}],
                impact="Investigation or reference-only material can leak into runtime evaluation.",
                owner="solidify",
                remediation="Slice or reclassify the material before runtime compilation.",
                blocked_stage=stage,
            ))
        segment_protocol = segment.get("protocol_version")
        protocol_mismatch = False
        if segment_protocol not in (None, ""):
            try:
                protocol_mismatch = int(segment_protocol) != compiler_protocol_version
            except (TypeError, ValueError):
                protocol_mismatch = True
        if protocol_mismatch:
            findings.append(_finding(
                code="protocol_version_mismatch",
                severity="blocking",
                problem="A context segment declares an incompatible compiler protocol version.",
                evidence=[{
                    "segment_id": segment.get("segment_id"),
                    "segment_protocol_version": segment_protocol,
                    "compiler_protocol_version": compiler_protocol_version,
                }],
                impact="Draft and Production contracts can be silently mixed in one model call.",
                owner="project_compiler",
                remediation="Re-solidify the segment against the active compiler protocol before use.",
                blocked_stage=stage,
            ))
        transform = str(segment.get("transform") or "").strip()
        if transform and transform not in {
            "original", "original_slice", "deterministic_projection"
        }:
            findings.append(_finding(
                code="runtime_fact_rewrite",
                severity="blocking",
                problem="Runtime context contains a fact transform outside the deterministic compiler allowlist.",
                evidence=[{"segment_id": segment.get("segment_id"), "transform": transform}],
                impact="Model-written or unknown rewrites can be misrepresented as original business facts.",
                owner="project_compiler",
                remediation="Move semantic rewriting to Harness/Solidify or use an audited deterministic projection.",
                blocked_stage=stage,
            ))
        visibility = str(segment.get("runtime_visibility") or "runtime").strip()
        if visibility != "runtime":
            findings.append(_finding(
                code="restricted_material_in_runtime",
                severity="blocking",
                problem="A non-runtime material class is present in the compiled Runtime context.",
                evidence=[{
                    "segment_id": segment.get("segment_id"),
                    "runtime_visibility": visibility,
                }],
                impact="Investigation-only or Reference-only material can leak into the tested role.",
                owner="solidify",
                remediation="Exclude the material or register a runtime-authorized segment projection.",
                blocked_stage=stage,
            ))

    hashes: dict[str, list[str]] = {}
    for segment in snapshot.get("segments") or []:
        hashes.setdefault(str(segment.get("content_sha256") or ""), []).append(str(segment.get("segment_id") or ""))
    duplicate_groups = [ids for digest, ids in hashes.items() if digest and len(ids) > 1]
    if duplicate_groups:
        findings.append(_finding(
            code="duplicate_context_segment",
            severity="high",
            problem="Identical context content is injected through more than one segment.",
            evidence=[{"segment_ids": ids} for ids in duplicate_groups],
            impact="Repeated material lowers effective information density and can amplify one source.",
            owner="project_compiler",
            remediation="Deduplicate by content identity while preserving the strongest source metadata.",
            blocked_stage=stage,
        ))

    available_segments = {
        str(item.get("segment_id") or "")
        for item in snapshot.get("segments") or []
    }
    missing_segments = sorted(
        {str(item) for item in required_segments if str(item)} - available_segments
    )
    if missing_segments:
        findings.append(_finding(
            code="required_segment_unavailable",
            severity="blocking",
            problem="A required context segment is absent from the compiled prompt.",
            evidence=[{
                "missing_segments": missing_segments,
                "available_segments": sorted(available_segments),
            }],
            impact="The role cannot satisfy a solidified information obligation.",
            owner="project_compiler",
            remediation="Select the registered segment or remove the stale obligation before Draft execution.",
            blocked_stage=stage,
        ))

    available_tools = {
        str(item.get("logical_id") or item.get("runtime_name") or "")
        for item in snapshot.get("tool_plan") or []
    }
    missing_tools = sorted({str(item) for item in required_tools} - available_tools)
    if missing_tools:
        findings.append(_finding(
            code="required_tool_unavailable",
            severity="blocking",
            problem="A required information path is missing from the actual tool plan.",
            evidence=[{"missing_tools": missing_tools, "available_tools": sorted(available_tools)}],
            impact="The role cannot satisfy a solidified information obligation.",
            owner="tool_index",
            remediation="Expose the registered tool or remove the invalid obligation before Draft execution.",
            blocked_stage=stage,
        ))

    prompt_chars = int(snapshot.get("prompt_char_count") or 0)
    if max_prompt_chars is not None and prompt_chars > int(max_prompt_chars):
        findings.append(_finding(
            code="context_budget_exceeded",
            severity="high",
            problem="Compiled context exceeds the configured character budget.",
            evidence=[{"prompt_char_count": prompt_chars, "max_prompt_chars": int(max_prompt_chars)}],
            impact="Decision-relevant material can be drowned out or truncated.",
            owner="project_compiler",
            remediation="Move conditional material to Search→Load or remove duplicate/obsolete segments.",
            blocked_stage=stage,
        ))

    reprompt = snapshot.get("reprompt") or {}
    added = int(reprompt.get("added_char_count") or 0)
    base = int(reprompt.get("base_user_char_count") or 0)
    if reprompt.get("occurred") and base > 0 and added > max(2000, base):
        findings.append(_finding(
            code="reprompt_context_amplification",
            severity="high",
            problem="Structured reprompt adds more text than the original user payload.",
            evidence=[{"base_user_char_count": base, "added_char_count": added}],
            impact="A correction attempt can amplify invalid output and distract from the original evidence.",
            owner="core_compiler",
            remediation="Include only error paths and affected previous values in the reprompt.",
            blocked_stage=stage,
        ))
    return findings


def enforce_context_governance(report: Mapping[str, Any]) -> None:
    gate = report.get("gate") or {}
    if gate.get("mode") == "draft" and gate.get("blocking") is True:
        raise ContextGovernanceBlocked(report)


def configure_context_governance(
    client: Any,
    *,
    config: Mapping[str, Any] | None,
    project_id: str,
    system: str,
    user: str,
    output_spec: StructuredOutputSpec,
    tools: Iterable[Any] = (),
    reprompt: bool = False,
) -> dict[str, Any]:
    """Compile, attach and enforce an opt-in governance report for one call."""

    if not config or config.get("enabled") is not True:
        setattr(client, "_context_governance_report", {})
        return {}
    base_user_chars = int(config.get("base_user_char_count") or len(user))
    report = build_context_governance_report(
        project_id=project_id,
        role=str(config.get("role") or "judge"),
        stage=str(config.get("stage") or "judge"),
        mode=str(config.get("mode") or "production"),
        system=system,
        user=user,
        output_spec=output_spec,
        tools=tools,
        segments=list(config.get("segments") or []) + [
            {
                "segment_id": "compiled-system",
                "source": str(config.get("compiler_source") or "context-compiler"),
                "content": system,
                "role": str(config.get("role") or "judge"),
                "stage": str(config.get("stage") or "judge"),
            },
            {
                "segment_id": "case-user-payload",
                "source": str(config.get("user_source") or "trace://judge-evidence"),
                "content": user,
                "role": str(config.get("role") or "judge"),
                "stage": str(config.get("stage") or "judge"),
            },
        ],
        excluded_segments=config.get("excluded_segments") or (),
        runtime_owned_fields=config.get("runtime_owned_fields") or (),
        required_segments=config.get("required_segments") or (),
        required_tools=config.get("required_tools") or (),
        max_prompt_chars=config.get("max_prompt_chars"),
        reprompt={
            "occurred": bool(reprompt),
            "base_user_char_count": base_user_chars,
            "added_char_count": max(0, len(user) - base_user_chars) if reprompt else 0,
        },
        trace_id=str(config.get("trace_id") or ""),
        case_id=str(config.get("case_id") or ""),
        call_id=str(config.get("call_id") or ""),
        compiler_id=str(config.get("compiler_id") or "context-compiler-v1"),
        compiler_protocol_version=int(config.get("compiler_protocol_version") or 1),
    )
    setattr(client, "_context_governance_report", report)
    setattr(client, "_context_governance_config", dict(config))
    setattr(client, "_context_governance_tools", list(tools))
    enforce_context_governance(report)
    return report


def governance_report_matches_call(
    report: Mapping[str, Any] | None,
    *,
    system: str,
    user: str,
    output_spec: StructuredOutputSpec,
) -> bool:
    """Return whether a previously compiled report describes this exact call."""
    snapshot = (report or {}).get("snapshot") if isinstance(report, Mapping) else None
    if not isinstance(snapshot, Mapping):
        return False
    messages = snapshot.get("messages")
    if not isinstance(messages, Sequence) or len(messages) != 2:
        return False
    final_system = system + "\n\n" + render_output_constraint(output_spec)
    identity = f"{output_spec.model.__module__}.{output_spec.model.__qualname__}"
    contract = snapshot.get("output_contract") or {}
    return bool(
        contract.get("identity") == identity
        and contract.get("sha256") == stable_sha256(output_spec.json_schema())
        and messages[0].get("content_sha256") == _sha256_text(final_system)
        and messages[1].get("content_sha256") == _sha256_text(user)
    )


def ensure_call_context_governance(
    client: Any,
    *,
    project_id: str,
    role: str,
    stage: str,
    trace_id: str,
    system: str,
    user: str,
    output_spec: StructuredOutputSpec,
    tools: Iterable[Any] = (),
) -> dict[str, Any]:
    """Guarantee every LLM call has an exact snapshot without weakening Draft gates."""
    existing = dict(getattr(client, "_context_governance_report", {}) or {})
    if governance_report_matches_call(
        existing,
        system=system,
        user=user,
        output_spec=output_spec,
    ):
        return existing
    return configure_context_governance(
        client,
        config={
            "enabled": True,
            "mode": "production",
            "role": str(role or "llm"),
            "stage": str(stage or "complete_json"),
            "trace_id": str(trace_id or ""),
            "compiler_source": "impl/core/llm_client.py#complete_json-auto-governance",
            "user_source": "trace://llm-call-payload",
        },
        project_id=str(project_id or "default"),
        system=system,
        user=user,
        output_spec=output_spec,
        tools=tools,
    )


def role_governance_config(
    spec: Any,
    *,
    role: str,
    stage: str,
    trace_id: str = "",
    case_id: str = "",
    call_id: str = "",
    compiler_source: str = "",
    user_source: str = "",
    max_prompt_chars: int | None = None,
) -> dict[str, Any]:
    """Build the default governed-call config for non-Judge role entrypoints."""
    base_role = str(role).split("-", 1)[0]
    role_draft = getattr(spec, "role_draft", None)
    draft = role_draft(base_role) if callable(role_draft) else {}
    return {
        "enabled": True,
        "mode": "draft" if (draft or {}).get("enabled") is True else "production",
        "role": str(role),
        "stage": str(stage),
        "trace_id": str(trace_id or ""),
        "case_id": str(case_id or ""),
        "call_id": str(call_id or ""),
        "compiler_source": str(compiler_source or f"core://{role}/{stage}"),
        "user_source": str(user_source or f"trace://{role}/{stage}"),
        "max_prompt_chars": max_prompt_chars,
    }


def slice_context_clauses(
    content: str,
    *,
    source: str,
    excluded_markers: Iterable[str],
) -> tuple[str, list[dict[str, str]]]:
    """Apply an opt-in deterministic source projection without rewriting facts."""

    markers = [str(item) for item in excluded_markers if str(item)]
    if not content or not markers:
        return content, []
    kept_lines: list[str] = []
    excluded: list[dict[str, str]] = []
    for line_no, line in enumerate(content.splitlines(keepends=True), start=1):
        clauses = re.split(r"(?<=[；;。])", line)
        kept_clauses: list[str] = []
        for clause_index, clause in enumerate(clauses, start=1):
            matched = next((marker for marker in markers if marker in clause), "")
            if not matched:
                kept_clauses.append(clause)
                continue
            excluded.append({
                "segment_id": f"excluded-line-{line_no}-clause-{clause_index}",
                "source": source,
                "content": clause,
                "reason": (
                    "Runtime result contract is excluded from the LLM-owned "
                    f"context contract; marker={matched}"
                ),
            })
        kept_lines.append("".join(kept_clauses))
    return "".join(kept_lines), excluded


def compact_reprompt_previous_values(
    data: Mapping[str, Any],
    inconsistencies: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Keep only prior top-level values needed to repair reported paths."""

    roots: set[str] = set()
    for item in inconsistencies:
        where = str(item.get("where") or "").strip()
        if where:
            roots.add(where.split(".", 1)[0].split("[", 1)[0])
        marker = " ".join(
            str(item.get(key) or "")
            for key in ("kind", "detail")
        ).lower()
        if "expectation" in marker or "fulfillment" in marker:
            roots.update({"business_expectations", "fulfillment_assessments"})
        if "expected" in marker:
            roots.add("expected")
        if "applicab" in marker:
            roots.add("applicable_product_expectation_ids")
    return {key: data[key] for key in sorted(roots) if key in data}


def transition_context_finding(
    finding: Mapping[str, Any],
    *,
    to_status: str,
    verification_evidence: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Apply the Finding lifecycle without treating a code change as proof."""

    current = str(finding.get("status") or "open")
    target = str(to_status or "").strip()
    if current not in _FINDING_STATES or target not in _FINDING_STATES[current]:
        raise ValueError(f"invalid context finding transition: {current} -> {target}")
    evidence = [dict(item) for item in verification_evidence]
    if target in {"verified", "closed"} and not evidence:
        raise ValueError(f"transition to {target} requires verification evidence")
    updated = copy.deepcopy(dict(finding))
    updated["status"] = target
    if evidence:
        updated.setdefault("verification_evidence", []).extend(evidence)
    return updated


def report_from_context_messages(
    *,
    project_id: str,
    caller: str,
    messages: Sequence[Mapping[str, Any]],
    mode: str = "production",
) -> dict[str, Any]:
    """Create a limited audit view for historical ContextRecords.

    Historical records lack segment/source metadata, so this function does not
    invent provenance.  It explicitly records that limitation and still exposes
    the actual message hashes, sizes and output-contract marker count.
    """

    normalized = [
        {"role": str(item.get("role") or ""), "content": str(item.get("content") or "")}
        for item in messages
    ]
    system = "\n".join(item["content"] for item in normalized if item["role"] == "system")
    snapshot = {
        "schema_version": 1,
        "project_id": project_id,
        "role": caller,
        "stage": caller,
        "mode": mode,
        "compiler_id": "historical-context-record",
        "output_contract": {
            "identity": "unknown",
            "sha256": "",
            "field_names": [],
        },
        "messages": [
            {
                "role": item["role"],
                "char_count": len(item["content"]),
                "content_sha256": _sha256_text(item["content"]),
            }
            for item in normalized
        ],
        "compiled_prompt_sha256": stable_sha256(normalized),
        "prompt_char_count": sum(len(item["content"]) for item in normalized),
        "segments": [],
        "tool_plan": [],
        "reprompt": {"occurred": False, "added_char_count": 0},
    }
    findings = []
    marker_count = system.count(_SCHEMA_MARKER)
    if marker_count != 1:
        findings.append(_finding(
            code="output_contract_count",
            severity="blocking",
            problem="Historical context does not show exactly one rendered output contract.",
            evidence=[{"schema_marker_count": marker_count}],
            impact="The effective output contract cannot be established from the record.",
            owner="core_compiler",
            remediation="Re-run through the governed compiler to produce a complete snapshot.",
            blocked_stage=caller,
        ))
    findings.append(_finding(
        code="historical_provenance_unavailable",
        severity="diagnostic",
        problem="Historical ContextRecord predates segment-level governance metadata.",
        evidence=[{"message_count": len(normalized)}],
        impact="Message text is visible but individual source segments cannot be traced deterministically.",
        owner="project_compiler",
        remediation="Use a new governed run for segment-level before/after evidence.",
        blocked_stage=caller,
    ))
    return {
        "schema_version": 1,
        "snapshot": snapshot,
        "findings": findings,
        "gate": {"mode": mode, "blocking": any(item["severity"] == "blocking" for item in findings)},
    }
