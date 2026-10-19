"""出清单：核对说法类待查项 = 回答里逐字摘出的事实断言。

一次独立模型调用，只看回答和用户问题：不看知识库，就没有理由漏掉难查的。程序只挡"抽错"（改写、编造、夹带），
挡不住"抽漏"；漏抽率由验收样本量化（demand/knowledge_evidence.md §4）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Mapping

from impl.core.structured_output import StructuredOutputSpec
from impl.projects.llm_probe.eval_axes.llm import axis_llm, merge_usage


@dataclass
class ExtractedClaims:
    claims: list[dict[str, str]] = field(default_factory=list)


EXTRACT_SYSTEM = ('提取回答中可核验的事实断言。输出对象只有 claims 一个键，不要输出 schema 里的其他词（如 required）。'
                  'claims 每项只含 claim_id（唯一非空标识）、text、context 三个键；text 和 context 里的每一段都必须逐字摘自 output_text 的连续原文。'
                  '不改写，不推测；没有事实断言返回 claims=[]。用户问题仅作背景。'
                  '什么算一条断言：一个能拿去和条款原文比对的具体值——数字、期限、比例、金额、年龄，或明确的有/无某项责任。'
                  '一句话里有几个这样的值就拆几条，每条 text 只含自己那个值及其事项；'
                  '没有具体值的套话、建议、评价（如“视情况而定”“建议另行确认”“适合大多数人”）不是断言，不要抽。'
                  '回答自己给内容编的序号、排列顺序、指代（如“方式一”“保单一”“第二张”“上面这张”）不是关于对象的事实，不单独抽成断言。'
                  'text 加 context 合起来要能单独成立：离开这个回答单独读，意思和在回答里一样。'
                  'context 是核验这条 text 所需的最少上下文片段列表，只放两种：事实归属对象的标识（姓名、保单号、产品名或产品代码、办理事项的名称），'
                  '和成立条件（如“犹豫期内”“非0退保金时”）；不放任何被断言的数量和属性（张数、金额、状态、日期、“投保人：某某”这类，它们是断言本身）。'
                  '回答自己编的序号、指代不放进 context，换成它所指对象的标识在回答里的原文写法（如“第二张”指哪张保单就放那张的保单号）；'
                  '回答里找不到它所指对象的标识，这条就不抽。不需要上下文就填 []。'
                  '例如“甲产品投保年龄十八周岁，年交保费五千元”抽两条：text=“投保年龄十八周岁” context=[“甲产品”]；'
                  'text=“年交保费五千元” context=[“甲产品”]。'
                  '例如“乙产品在条件C下给付百分之八十”抽一条：text=“给付百分之八十” context=[“乙产品”,“条件C”]。')


_FORMAT = re.compile(r'[\s*`]+')


def _contains_value(segment: str, value: str) -> bool:
    """segment 里有没有 value 这个值：出现在一串字母数字中间的不算（保单号里的“0”不是金额“0”）。"""
    edge = re.compile(r'[A-Za-z0-9]')
    start = segment.find(value)
    while start >= 0:
        end = start + len(value)
        inside = (start > 0 and edge.match(segment[start - 1]) and edge.match(value[0])) or \
                 (end < len(segment) and edge.match(segment[end]) and edge.match(value[-1]))
        if not inside:
            return True
        start = segment.find(value, start + 1)
    return False


_QUOTES = str.maketrans({c: '"' for c in '“”„‟＂「」『』'} | {c: "'" for c in '‘’‚‛＇'})


def _plain(text):
    """逐字比对前去掉空白和 Markdown 强调符、统一引号：回答常带 **加粗**，格式符不是内容，模型摘句不带它们；
    直引号和弯引号模型常互换（回答写 "交费有效"，摘句成 “交费有效”），引号形状不是内容。改字仍判不是原文。"""
    return _FORMAT.sub('', text).translate(_QUOTES)


def parse_claims(payload: Any, output_text: str) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping) or payload.get('error') or not isinstance(payload.get('claims'), list):
        raise ValueError('断言提取失败：缺少 claims 列表')
    seen = set()
    result = []
    for claim in payload['claims']:
        if not isinstance(claim, Mapping):
            raise ValueError('断言必须是对象')
        key, text, context = claim.get('claim_id'), claim.get('text'), claim.get('context', [])
        if not isinstance(key, str) or not key.strip() or key in seen:
            raise ValueError('claim_id 必须唯一且非空')
        # 报错点名是哪条、哪一段：修复轮只拿到报错，不点名模型无从改起。
        if not isinstance(text, str) or not text.strip() or _plain(text) not in _plain(output_text):
            raise ValueError(f'断言 {key} 的 text {text!r} 不是 output_text 的逐字连续原文')
        if not isinstance(context, list):
            raise ValueError(f'断言 {key} 的 context 必须是字符串列表')
        bad = [c for c in context if not isinstance(c, str) or not c.strip() or _plain(c) not in _plain(output_text)]
        if bad:
            raise ValueError(f'断言 {key} 的 context 段 {bad[0]!r} 不是 output_text 的逐字连续原文')
        seen.add(key)
        result.append({'claim_id': key, 'text': text, 'context': [c.strip() for c in context]})
    # 防偷懒：context 只许带定位所需的上下文，带了别条断言的值就等于把整句塞回来，隔离失效。
    for claim in result:
        for other in result:
            if other is claim:
                continue
            leaked = [c for c in claim['context'] if _contains_value(c, other['text'])]
            if leaked:
                raise ValueError(f"断言 {claim['claim_id']} 的 context {leaked[0]!r} 含了断言 {other['claim_id']} 的值 {other['text']!r}，只放定位所需的上下文")
    return result


def extract_claims(trace: Any, runtime: Any, usage: dict[str, Any]) -> list[dict[str, Any]]:
    """真实性的待查项来源。失败抛 ValueError（轴记失败，不当作"没有断言"）。"""
    output_text = (trace.extracted_output or {}).get('output_text')
    if not isinstance(output_text, str):
        raise ValueError('output_text 缺失或不是文本')
    client = axis_llm(runtime.spec, role='truthfulness', tools=[])
    request = trace.normalized_request or {}
    user = json.dumps({'output_text': output_text, 'question': request.get('body') or {}}, ensure_ascii=False)
    spec = StructuredOutputSpec.from_dataclass(ExtractedClaims)
    try:
        # 提取是逐字摘抄，不需要深推理。
        try:
            claims = parse_claims(client.complete_json(EXTRACT_SYSTEM, user, trace_id=runtime.trace_id, stage='knowledge_extract',
                                                       reasoning_effort='low', output_spec=spec), output_text)
        except ValueError as exc:
            # 结构或逐字/隔离校验被阻断只做一次带具体错误的修复，不是语义重试。
            claims = parse_claims(client.complete_json(
                EXTRACT_SYSTEM, user + '\n\n## 上次输出不符合要求\n' + str(exc)[:600] + '\n请只修正这一点，重新输出只含 claims 键的 JSON。',
                trace_id=runtime.trace_id, stage='knowledge_extract', reasoning_effort='low', output_spec=spec), output_text)
    finally:
        merge_usage(usage, client.usage())
    return [{'item_id': c['claim_id'], 'kind': 'claim', 'text': c['text'], 'context': c['context']} for c in claims]
