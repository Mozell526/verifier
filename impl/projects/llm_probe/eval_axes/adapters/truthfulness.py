"""真实性：隔离提取与逐断言核验，程序汇总，不向核验阶段泄露整份回答。"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping

from impl.core.structured_output import StructuredOutputSpec
from impl.projects.llm_probe.material_tools import verify_quote as verify_material_quote
from impl.projects.llm_probe.text_carrier import _TOOL_CALL_LIMIT
from ..llm import axis_llm, merge_usage
from ..sources import expand_sources, build_tools
from ..sources.es_tools import EsTools
from ..types import AxisType, AxisSummary, ExecutionLimits, Field, Input, RunOutcome, Verdict


@dataclass
class ExtractedClaims:
    claims: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ClaimVerdict:
    verdict: str = ''
    reason: str = ''
    citations: list[dict[str, str]] = field(default_factory=list)


_VERDICTS = ('verified', 'refuted', 'unverifiable')
_EXTRACT_SYSTEM = '提取回答中可核验的事实断言。claims 每项只含 claim_id（唯一非空标识）和 text（逐字摘自 output_text 的连续原文）。不改写，不推测；没有事实断言返回 claims=[]。用户问题仅作背景。'
_VERIFY_SYSTEM = f'''核验这一条断言：资料中能否找到支持或反驳它的原文？
只使用给定知识源与工具，不依赖记忆。verified=原文支持；refuted=原文矛盾；unverifiable=找不到支持或反驳原文。
输出 verdict/reason/citations，reason 必须非空。verified 和 refuted 必须引用；unverifiable 时 citations 必须是 []，
不要为了佐证"没找到"去 read 无关条款——检索过哪些词、为何不相关写进 reason 即可。
引用每项只含三个键 source/ref/note（键名固定，不要写成 locator）：source 是给定的 material:// 或 es:// URI；
ref 填工具返回的 locator 值（形如 文档ID#字段）；note 是该位置逐字原文。
流程：outline 一次了解字段/骨架 → 用断言里的产品名和条款主体词 search（最多换 3 种措辞）→ 命中再 read 精读。
工具预算共 {_TOOL_CALL_LIMIT} 次，超出即本次作废。3 次检索都没有与该断言主体（同一产品、同一条款事项）相关的条款时，
立即返回 unverifiable，reason 写明检索了哪些词、知识库里没有对应条款；不要继续换词穷举。
检索片段不代替原文；工具报错（不是零命中）不能冒充 unverifiable。'''


def _claims(payload, output_text):
    if not isinstance(payload, Mapping) or payload.get('error') or not isinstance(payload.get('claims'), list):
        raise ValueError('断言提取失败：缺少 claims 列表')
    seen = set()
    result = []
    for claim in payload['claims']:
        if not isinstance(claim, Mapping):
            raise ValueError('断言必须是对象')
        key, text = claim.get('claim_id'), claim.get('text')
        if not isinstance(key, str) or not key.strip() or key in seen:
            raise ValueError('claim_id 必须唯一且非空')
        if not isinstance(text, str) or not text.strip() or text not in output_text:
            raise ValueError('断言 text 必须逐字来自 output_text')
        seen.add(key)
        result.append({'claim_id': key, 'text': text})
    return result


def _verify_result(payload, catalog, description, receipts):
    if not isinstance(payload, Mapping):
        raise ValueError('断言核验模型调用失败（无返回）')
    if payload.get('error'):
        # 带上错误码和原因：重试反馈给模型看（预算超了要早停），汇总给人看（不是一句黑盒失败）。
        detail = str(payload.get('raw_text') or '').strip()[:200]
        raise ValueError(f"断言核验模型调用失败（{payload['error']}）" + (f'：{detail}' if detail else ''))
    verdict, reason = payload.get('verdict'), payload.get('reason')
    citations = payload.get('citations')
    if verdict not in _VERDICTS or not isinstance(reason, str) or not reason.strip() or not isinstance(citations, list):
        raise ValueError('核验结果缺少合法 verdict/reason/citations')
    if verdict != 'unverifiable' and not citations:
        raise ValueError('verified/refuted 必须带引用')
    if any(receipt.get('error') for receipt in receipts):
        raise ValueError('知识源工具调用失败')
    if verdict == 'unverifiable':
        # "没找到"的证据在 reason 里；顺手附上的无关条款不是证据，不回读、不落盘。
        return {'verdict': verdict, 'reason': reason, 'citations': []}
    es_catalog = [c for c in catalog if c.get('source') == 'es']
    cleaned = []
    for citation in citations:
        if not isinstance(citation, Mapping) or any(not isinstance(citation.get(k), str) or not citation[k].strip() for k in ('source', 'ref', 'note')):
            raise ValueError('引用必须带 source/ref/note')
        source, ref, note = (citation[k] for k in ('source', 'ref', 'note'))
        if source.startswith('es://'):
            ok = bool(es_catalog) and EsTools(es_catalog, receipts).verify_quote(source[5:], ref, note)
        elif source.startswith('material://') and '{' + source + '}' in description:
            parts = source[len('material://'):].split('/')
            ok = len(parts) == 2 and verify_material_quote(parts[0], parts[1], ref, note)
        else:
            ok = False
        if not ok:
            raise ValueError(f'引用回读核验失败: {source}#{ref}')
        cleaned.append({'source': source, 'ref': ref, 'note': note})
    return {'verdict': verdict, 'reason': reason, 'citations': cleaned}


def _outcome(claims, extracted, catalog, errors, usage):
    coverage = {'extracted': extracted, **{v: sum(c['verdict'] == v for c in claims) for v in _VERDICTS}}
    items = [{'key': c['claim_id'], 'value': c['verdict'], 'reason': c['reason']} for c in claims]
    groups = []
    for verdict in ('refuted', 'unverifiable', 'verified'):
        lines = [f"{c['claim_id']}（{c['reason']}）" for c in claims if c['verdict'] == verdict]
        if lines:
            groups.append('$' + verdict + '\n' + '\n'.join(lines))
    text = '\n\n'.join(groups) or ('真实性核验失败' if errors else '回答不含可核验的事实断言')
    sources = [{'uri': c['uri'], 'snapshot_id': c.get('snapshot_id') or c.get('sha256', '')} for c in catalog]
    output = {'claims': claims, 'sources': sources, 'coverage': coverage, 'errors': errors}
    return RunOutcome(output=output, summary=AxisSummary(text, items), failed=bool(errors),
                      failure_reason='；'.join(e['last_error'] for e in errors), usage=usage)


def run_truthfulness(inputs, axis, runtime):
    trace = inputs['trace']
    output_text = (trace.extracted_output or {}).get('output_text')
    usage: dict[str, Any] = {'llm_calls': 0, 'tool_calls': 0}
    errors, completed, catalog = [], [], []
    extracted = []
    try:
        if not isinstance(output_text, str):
            raise ValueError('output_text 缺失或不是文本')
        # 第一阶段只带回答和问题背景；无工具、无框描述、无知识源。
        client = axis_llm(runtime.spec, role='truthfulness', tools=[])
        request = trace.normalized_request or {}
        try:
            payload = client.complete_json(
                _EXTRACT_SYSTEM, json.dumps({'output_text': output_text, 'question': request.get('body') or {}}, ensure_ascii=False),
                trace_id=runtime.trace_id, stage='truthfulness_extract',
                output_spec=StructuredOutputSpec.from_dataclass(ExtractedClaims),
            )
        finally:
            merge_usage(usage, client.usage())
        extracted = _claims(payload, output_text)
        if not extracted:
            return _outcome([], 0, [], [], usage)
        description, catalog = expand_sources(axis.description, material_catalog=True)
        # 每个断言/每次重试用独立客户端；反馈只含本断言的核验错误。
        for claim in extracted:
            feedback = ''
            last_error = ''
            for attempt in range(3):
                receipts = []
                client = None
                try:
                    tools = build_tools(catalog, receipts)
                    client = axis_llm(runtime.spec, role='truthfulness', tools=tools, tool_call_limit=_TOOL_CALL_LIMIT if tools else None)
                    payload = client.complete_json(
                        _VERIFY_SYSTEM, json.dumps({'claim': claim, 'description': description, 'catalog': catalog, 'feedback': feedback}, ensure_ascii=False),
                        trace_id=runtime.trace_id, stage='truthfulness_verify',
                        output_spec=StructuredOutputSpec.from_dataclass(ClaimVerdict, required_nonempty=['verdict', 'reason']),
                    )
                    verdict = _verify_result(payload, catalog, axis.description, receipts)
                    completed.append({**claim, **verdict})
                    break
                except Exception as exc:
                    last_error = str(exc)
                    feedback = '上次核验失败，请修正：' + last_error
                finally:
                    usage['tool_calls'] += len(receipts)
                    if client is not None:
                        merge_usage(usage, client.usage())
            else:
                errors.append({'claim_id': claim['claim_id'], 'last_error': last_error, 'attempts': 3})
    except Exception as exc:
        errors.append({'claim_id': '', 'last_error': str(exc)})
    return _outcome(completed, len(extracted), catalog, errors, usage)


AXIS_TYPE = AxisType(
    type_id='truthfulness', title='真实性', summary='从回答里提取事实断言，逐条对照知识库核验',
    verdict_scope='item', verdict_enum=(Verdict('verified', '知识库中有原文支持该断言'), Verdict('refuted', '知识库原文与该断言矛盾'), Verdict('unverifiable', '知识库中找不到能支持或反驳的原文')),
    item_path='claims[].verdict', depend_on=(), trigger_when=None, inputs=(Input('trace', 'sample.trace'),),
    output_fields=('claims', 'sources', 'coverage', 'errors'), scenario_fields=(Field('description', expand='catalog'),),
    limits=ExecutionLimits(tool_calls=_TOOL_CALL_LIMIT), run=run_truthfulness,
    implementation_files=('impl/projects/llm_probe/eval_axes/adapters/truthfulness.py', 'impl/projects/llm_probe/eval_axes/sources/__init__.py', 'impl/projects/llm_probe/eval_axes/sources/es_client.py', 'impl/projects/llm_probe/eval_axes/sources/es_tools.py'),
)
