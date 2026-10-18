"""真实性：读知识案卷，逐条判定回答里的说法与取回的原文是否一致；不抽取、不检索。

待查项由本轴声明的来源（knowledge_loop.extract.extract_claims）交给知识查证轴，查证只取证；
这里只看每条的引用原文及其前后窗口，判 verified / refuted / unverifiable（spec/alg/knowledge-evidence.md §5）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping

from impl.core.structured_output import StructuredOutputSpec
from impl.projects.llm_probe.knowledge_loop.extract import extract_claims
from impl.projects.llm_probe.knowledge_loop.loop import FOUND
from ..llm import axis_llm, merge_usage
from ..types import AxisTimeout, AxisType, AxisSummary, Dependency, ExecutionLimits, Field, Input, RunOutcome, Verdict
from .knowledge_evidence import item_label


@dataclass
class ClaimVerdict:
    # reason 在前：先写比对，再落结论；实测 verdict 在前时出现过「理由写支持、结论填 refuted」。
    reason: str = ''
    verdict: str = ''
    basis: list[int] = field(default_factory=list)


_VERDICTS = ('verified', 'refuted', 'unverifiable')
_JUDGE_SYSTEM = '''判定回答里的一条说法与知识库原文是否一致。原文是查证阶段从知识源取回的，你不需要也不能再检索。

输入：
- claim：text 是事实本身，context 是它归属的对象与成立条件；判的是「context 之下的 text」。
- citations：编号列表，每项 quote 是摘出的原文，window 是 quote 在原文里的前后上下文（适用条件、例外常在旁边）。
- guidance：场景补充的判定口径，可能为空。

结论：
- verified：有原文支持——同一对象、同一条件下，原文的值或规定与说法一致。
- refuted：原文与说法矛盾——同一对象、同一条件下值不同；或说法把原文里有条件的规定说成了无条件（漏掉适用条件）。
- unverifiable：给定原文定不了——对象或条件对不上、原文只谈相关话题没给值、原文不足以判断。
知识库对同一事项有互相矛盾的说法时，不替知识库裁定：说法与其中一种一致即 verified，reason 写明另有不同说法及其原文。
数字写法可能不同：阿拉伯数字与中文数字、%与百分之、天与日、万与万元互为等价，等价写法视为一致。

输出 reason/verdict/basis：先在 reason 写原文怎么说、与说法是否一致，再按 reason 的结论填 verdict，两者不得矛盾。
basis 是作为依据的 citations 编号：verified 和 refuted 必须至少一个；unverifiable 时为 []。'''


def _judgement(payload: Any, count: int) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError('判定模型调用失败（无返回）')
    if payload.get('error'):
        detail = str(payload.get('raw_text') or '').strip()[:200]
        raise ValueError(f"判定模型调用失败（{payload['error']}）" + (f'：{detail}' if detail else ''))
    verdict, reason, basis = payload.get('verdict'), payload.get('reason'), payload.get('basis')
    if verdict not in _VERDICTS or not isinstance(reason, str) or not reason.strip() or not isinstance(basis, list):
        raise ValueError('判定结果缺少合法 verdict/reason/basis')
    if any(not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < count for i in basis):
        raise ValueError(f'basis 只能是 citations 的编号 0..{count - 1}')
    if verdict != 'unverifiable' and not basis:
        raise ValueError('verified/refuted 必须在 basis 里给出依据的引用编号')
    return {'verdict': verdict, 'reason': reason, 'basis': sorted(set(basis)) if verdict != 'unverifiable' else []}


def _judge(item, guidance, runtime, usage):
    citations = [{'id': i, 'quote': c['quote'], 'window': c['window']} for i, c in enumerate(item['citations'])]
    user = json.dumps({'claim': {'text': item['text'], 'context': item['context']}, 'citations': citations,
                       'guidance': guidance}, ensure_ascii=False)
    spec = StructuredOutputSpec.from_dataclass(ClaimVerdict, required_nonempty=['verdict', 'reason'])
    client = axis_llm(runtime.spec, role='truthfulness', tools=[])
    try:
        try:
            return _judgement(client.complete_json(_JUDGE_SYSTEM, user, trace_id=runtime.trace_id, stage='truthfulness_judge',
                                                   reasoning_effort='low', output_spec=spec), len(citations))
        except ValueError as exc:
            # 结构不合规只做一次带具体错误的修复，不是语义重试。
            return _judgement(client.complete_json(
                _JUDGE_SYSTEM, user + '\n\n## 上次输出不符合要求\n' + str(exc)[:600] + '\n请只修正这一点，重新输出。',
                trace_id=runtime.trace_id, stage='truthfulness_judge', reasoning_effort='low', output_spec=spec), len(citations))
    finally:
        merge_usage(usage, client.usage())


def _claim(item, judged):
    cited = [item['citations'][i] for i in judged['basis']]
    return {'claim_id': item['item_id'].split(':', 1)[1], 'text': item['text'], 'context': item['context'],
            'verdict': judged['verdict'], 'reason': judged['reason'],
            'citations': [{'source': c['source'], 'ref': c['call_id'], 'note': c['quote']} for c in cited]}


def _outcome(claims, extracted, sources, errors, usage):
    coverage = {'extracted': extracted, **{v: sum(c['verdict'] == v for c in claims) for v in _VERDICTS}}
    # key 放断言原文而不是 claim_id：表格和导出里读者要看的是"哪句话"，id 只对机器有意义。
    items = [{'key': item_label(c), 'value': c['verdict'], 'reason': c['reason'], 'claim_id': c['claim_id'], 'citations': c['citations']} for c in claims]
    groups = []
    for verdict in ('refuted', 'unverifiable', 'verified'):
        lines = [f"{c['claim_id']}（{c['reason']}）" for c in claims if c['verdict'] == verdict]
        if lines:
            groups.append('$' + verdict + '\n' + '\n'.join(lines))
    text = '\n\n'.join(groups) or ('真实性判定失败' if errors else '回答不含可核验的事实断言')
    output = {'claims': claims, 'sources': sources, 'coverage': coverage, 'errors': errors}
    return RunOutcome(output=output, summary=AxisSummary(text, items), failed=bool(errors),
                      failure_reason='；'.join(e['last_error'] for e in errors), usage=usage)


def run_truthfulness(inputs, axis, runtime):
    evidence = inputs['evidence']
    items = [item for item in evidence['items'] if item['origin'] == 'truthfulness']
    usage: dict[str, Any] = {'llm_calls': 0, 'tool_calls': 0}
    claims, errors = [], []
    for item in items:
        if item['status'] != FOUND:
            # 没找到相关原文：程序直接给，不调模型。
            claims.append(_claim(item, {'verdict': 'unverifiable', 'reason': '知识查证没找到相关原文：' + item['note'], 'basis': []}))
            continue
        try:
            runtime.ensure_time_left(f"断言 {item['item_id']}")
            claims.append(_claim(item, _judge(item, axis.description, runtime, usage)))
        except AxisTimeout as exc:
            usage['timed_out'] = True
            errors.append({'claim_id': item['item_id'], 'last_error': str(exc)})
            break
        except Exception as exc:
            errors.append({'claim_id': item['item_id'], 'last_error': str(exc)})
    return _outcome(claims, len(items), evidence['sources'], errors, usage)


AXIS_TYPE = AxisType(
    type_id='truthfulness', title='真实性', summary='从回答里提取事实断言交知识查证取证，逐条对照取回的原文判定',
    verdict_scope='item', verdict_enum=(Verdict('verified', '知识库中有原文支持该断言'), Verdict('refuted', '知识库原文与该断言矛盾'), Verdict('unverifiable', '知识库中找不到能支持或反驳的原文')),
    item_path='claims[].verdict', depend_on=(Dependency('knowledge_evidence'),), trigger_when=None,
    inputs=(Input('evidence', source='axis.knowledge_evidence.output', fields=('items', 'sources')),),
    output_fields=('claims', 'sources', 'coverage', 'errors'),
    # 知识源引用写在知识查证框；这里的描述只作判定口径补充。
    scenario_fields=(Field('description', required=False, expand='prompt_load'),),
    limits=ExecutionLimits(seconds=600), run=run_truthfulness, knowledge_items=extract_claims,
)
