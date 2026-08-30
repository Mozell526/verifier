"""llm_probe 文本形态轴2：capability 预设的 boundary 文本作为 G。

StructuredCarrier 的平行形态——不做字段×操作符×值查表。
boundary 为空时所有期望归位为「说不清（缺能力边界资料）」。
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from impl.core.capability_carrier import (
    CARRY_NO,
    CARRY_UNDECIDABLE,
    CARRY_YES,
    GAP_AMBIGUITY,
    GAP_UNGOVERNED,
    RECOG_BOUNDARY_STATEMENT,
    CarrierError,
    CarrierVerdict,
    CapabilityCarrierBase,
    placement_request,
)

_DEFAULT_RETRIES = 3
_DEFAULT_RETRY_BACKOFF = (0.5, 1.5, 3.0)

CompleterFn = Callable[[str, str], Mapping[str, Any]]


@dataclass
class _TextVerdictOutput:
    carry: str = ""
    reason: str = ""
    self_recognition: str = ""
    citations: list[dict[str, str]] = field(default_factory=list)
    gap_kind: str = ""
    missing_material: str = ""


_CARRIER_SYSTEM = """\
你是承载性判定器。给你一条未达成的期望和一份能力边界描述。
只判断：这份能力边界描述能否证明该期望承载得了、还是承载不了、还是信息不够说不清。

规则：
- 只看能力边界描述，不看这次交付了什么，不看 live 说了什么话
- carry 只能是 yes / no / undecidable
- carry=yes：能力边界描述明确表明该期望在覆盖范围内（承载得了）
- carry=no：能力边界描述明确表明该期望不在覆盖范围内（承载不了）——必须引用描述中的具体语句作为自认
- carry=undecidable：描述不足以判定（信息不够、描述模糊、或期望与描述口径不一致）
- self_recognition：carry=no 时必填，引用能力边界描述中表明「承载不了」的具体语句
- citations：每条引用给出 source（资料来源标识）、note（引用的具体语句或段落摘要）
- gap_kind：carry=undecidable 时必填，取值「口径分歧」或「空间未受治理」
- missing_material：carry=undecidable 时必填，说明缺什么资料才能判定
- 不要编造能力边界描述中没有的信息；描述没说的就是说不清
"""


def _verdict_output_spec():
    from impl.core.structured_output import StructuredOutputSpec
    return StructuredOutputSpec.from_dataclass(
        _TextVerdictOutput,
        required_nonempty=["carry", "reason"],
        description="轴2承载性判定：对单条期望输出 carry/reason/self_recognition/citations/gap_kind/missing_material",
    )


def _citations_from(data: Mapping[str, Any], fallback_note: str) -> tuple[dict[str, str], ...]:
    citations = tuple(
        {
            "source": str(item.get("source") or "capability_boundary"),
            "ref": str(item.get("ref") or "boundary"),
            "note": str(item.get("note") or ""),
        }
        for item in (data.get("citations") or [])
        if isinstance(item, Mapping)
    )
    if citations:
        return citations
    note = str(fallback_note or "").strip()
    if not note:
        return ()
    return ({
        "source": "capability_boundary",
        "ref": "boundary",
        "note": note,
    },)


def _parse_verdict(data: Mapping[str, Any] | None) -> CarrierVerdict | None:
    if not isinstance(data, Mapping):
        return None
    carry = str(data.get("carry") or "").strip()
    if carry not in (CARRY_YES, CARRY_NO, CARRY_UNDECIDABLE):
        return None
    reason = str(data.get("reason") or "").strip()
    if not reason:
        return None
    if carry == CARRY_NO:
        quote = str(data.get("self_recognition") or "").strip()
        if not quote:
            return None
        citations = _citations_from(data, quote)
        return CarrierVerdict(
            CARRY_NO, reason,
            citations=citations,
            recognition=RECOG_BOUNDARY_STATEMENT,
        )
    if carry == CARRY_UNDECIDABLE:
        gap = str(data.get("gap_kind") or "").strip()
        missing = str(data.get("missing_material") or "").strip()
        if gap not in (GAP_AMBIGUITY, GAP_UNGOVERNED) or not missing:
            return None
        return CarrierVerdict(
            CARRY_UNDECIDABLE, reason,
            gap_kind=gap, missing_material=missing,
            citations=_citations_from(data, reason),
        )
    citations = _citations_from(data, reason)
    if not citations:
        return None
    return CarrierVerdict(CARRY_YES, reason, citations=citations)


class TextCarrier(CapabilityCarrierBase):
    """文本形态：本 case 的 boundary 文本作为 G，LLM 判承载性。"""

    def __init__(
        self,
        boundary_loader: Callable[[], str] | None = None,
        *,
        spec: Any = None,
        completer: CompleterFn | None = None,
        retries: int = _DEFAULT_RETRIES,
        retry_backoff: Sequence[float] = _DEFAULT_RETRY_BACKOFF,
    ):
        self._boundary_loader = boundary_loader
        self._spec = spec
        self._completer = completer
        self._retries = max(1, retries)
        self._backoff_schedule = tuple(retry_backoff)
        self._cache: dict[str, CarrierVerdict | CarrierError] = {}

    def _current_boundary(self) -> str:
        if self._boundary_loader is not None:
            return str(self._boundary_loader() or "").strip()
        from impl.projects.llm_probe.capability import resolve_boundary

        request = placement_request()
        if not isinstance(request, Mapping):
            return ""
        return resolve_boundary(dict(request))

    def snapshot_revision(self) -> str:
        boundary = self._current_boundary()
        if not boundary:
            return ""
        return hashlib.sha256(boundary.encode("utf-8")).hexdigest()[:16]

    def citation_space(self) -> set[str] | None:
        return None

    def verdict_for(self, expectation: Mapping[str, Any]) -> CarrierVerdict | CarrierError:
        boundary = self._current_boundary()
        if not boundary:
            return CarrierVerdict(
                CARRY_UNDECIDABLE,
                "未填写能力边界描述",
                gap_kind=GAP_UNGOVERNED,
                missing_material=(
                    "能力边界描述（请在资料管理页的 capability 预设中填写 boundary 字段）"
                ),
            )
        text = self._expectation_text(expectation)
        cache_key = hashlib.sha256(
            (text + "|" + boundary).encode("utf-8")
        ).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]
        outcome = self._judge_with_retry(text, boundary)
        self._cache[cache_key] = outcome
        return outcome

    @staticmethod
    def _expectation_text(expectation: Mapping[str, Any]) -> str:
        parts = [
            str(expectation.get(key) or "")
            for key in ("expectation_id", "user_intent", "expected_outcome")
        ]
        criteria = expectation.get("acceptance_criteria")
        if isinstance(criteria, (list, tuple)):
            parts.extend(str(item) for item in criteria)
        elif criteria:
            parts.append(str(criteria))
        return " ".join(part for part in parts if part)

    def _judge_with_retry(self, expectation_text: str, boundary: str) -> CarrierVerdict | CarrierError:
        last_error = "LLM 输出无法解析为承载性判定"
        for attempt in range(self._retries):
            try:
                result = self._call_llm(expectation_text, boundary)
            except Exception as exc:
                last_error = str(exc)
                self._wait(attempt)
                continue
            verdict = _parse_verdict(result)
            if verdict is not None:
                return verdict
            last_error = "LLM 输出缺少必填字段或取值非法"
            self._wait(attempt)
        return CarrierError("text_carrier", "承载性判定重试耗尽", last_error)

    def _call_llm(self, expectation_text: str, boundary: str) -> Mapping[str, Any]:
        if self._completer is not None:
            data = self._completer(expectation_text, boundary)
            if not isinstance(data, Mapping):
                raise ValueError("completer must return a mapping")
            return data
        if self._spec is None:
            raise ValueError("TextCarrier 需要 spec 才能调 LLM")
        from impl.core.llm_client import project_llm_client

        client = project_llm_client(self._spec, role="capability_carrier_mapper", tools=[])
        user = (
            f"未达成的期望：\n{expectation_text}\n\n"
            f"能力边界描述：\n{boundary}"
        )
        return client.complete_json(
            _CARRIER_SYSTEM,
            user,
            reasoning_effort="low",
            output_spec=_verdict_output_spec(),
            stage="llm_probe_text_carrier",
        )

    def _wait(self, attempt: int) -> None:
        if attempt + 1 >= self._retries:
            return
        delay = self._backoff_schedule[min(attempt, len(self._backoff_schedule) - 1)]
        if delay > 0:
            time.sleep(delay)
