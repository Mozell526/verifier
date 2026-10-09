"""Prompt/schema/original-source agreement with scripted adversarial judgments."""
import copy
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from impl.core.structured_output import enforce_output, render_output_constraint
from impl.projects.llm_probe.process_contract import AXIS_DESCRIPTIONS, source_in_inputs
from impl.projects.llm_probe.eval_axes.adapters import process_common as common, expectations, process_output
from impl.projects.llm_probe.eval_axes.adapters.process_protocol import EVIDENCE_GUIDE, JUDGING_GUIDE
from impl.projects.llm_probe.eval_axes.types import ScenarioAxis
from impl.projects.llm_probe.process_loop import analysis, evaluation, llmtracing
from impl.projects.llm_probe.process_loop import expectation_projection as projection
from tests.test_expectations import fixture, design_case, design_reply
from tests.support.expectations import E, PROJECTION, content_sha256
from tests.support.unit_reply import unit_reply
from tests.test_llmtracing_tool_loop import ScriptClient, material as transcript_material


def test_prompts_schema_and_runtime_share_named_axes_and_unit_protocol():
    for spec in [process_output.OUTPUT, evaluation.OUTPUT, llmtracing.OUTPUT]:
        assert spec is process_output.OUTPUT
        schema = spec.json_schema()
        assert set(schema['$defs']['ProblemRecord']['properties']['axes']['items']['enum']) == set(AXIS_DESCRIPTIONS)
        unit = schema['$defs']['UnitJudgment']['properties']
        assert {'checks', 'rules', 'necessity', 'matched'} <= unit.keys() and not {'blocks', 'upstream'} & unit.keys()
        assert not {'expected', 'outcome', 'obligation_id', 'link_id', 'criterion_refs'} & unit.keys()
        assert unit['matched']['type'] == 'string' and unit['matched'].get('minLength', 0) == 0
        assert {'reason', 'scope_note', 'units', 'problems'} == set(schema['properties'])
    schema = projection.JOIN_SPEC.json_schema()
    assert set(schema['properties']) == {'data_needs'}
    assert set(schema['$defs']['DataNeed']['properties']['need']['enum']) == {'external', 'none', 'unknown'}
    assert {'block', 'quote'} <= schema['$defs']['ToolOption']['properties'].keys()
    for prompt in [process_output.UNIT_SYSTEM, analysis.SYSTEM, evaluation.SYSTEM, llmtracing.SYSTEM,
                   projection.JOIN_SYSTEM, expectations.SYSTEM]:
        assert not any(c in prompt for c in 'ικρσμχΛ')
    # Shared semantic rules must be present; entry-specific tool prose is not byte-coupled.
    for prompt in [process_output.UNIT_SYSTEM, evaluation.SYSTEM, llmtracing.SYSTEM]:
        assert EVIDENCE_GUIDE in prompt and JUDGING_GUIDE in prompt
        assert all(word in prompt for word in ('necessity', 'satisfied', 'required', 'unknown'))
        assert 'original_blocks' not in prompt and '逐块' not in prompt.replace('不逐块', '')
    assert 'dossier_collect' not in process_output.UNIT_SYSTEM
    assert 'dossier_collect' in evaluation.SYSTEM and 'evidence_read' in llmtracing.SYSTEM
    assert 'candidates' in process_output.UNIT_SYSTEM
    # Field shapes live in the schema the mechanism renders, not in hand-written prompt prose.
    rendered = render_output_constraint(process_output.OUTPUT)
    assert all(word in rendered for word in ('missing_criterion', 'breaks', 'anyOf', '只选一个分支'))


def test_project_obligation_config_uses_the_same_axis_ids_as_link_schema():
    from impl.core.capability_store import load_capability_map
    from impl.projects.llm_probe.business_trace.links import LINK_TYPES
    capability_map = load_capability_map('llm_probe')
    for capability in ('insurance-agno-e2e', 'insurance-llmtracing'):
        obligations = capability_map[capability]['process_obligations']
        assert len(obligations) == 1 and obligations[0]['link_type'] in LINK_TYPES
        assert obligations[0]['applies_to'] == ['planning_routing:repeat']
        assert common.project_obligations(capability_map[capability], 'planning_routing')[0].obligation_id == 'project:retry_after_non_retryable'


def test_transcript_prompt_maps_source_id_to_readable_evidence_id():
    _, frozen, projected = fixture()
    frozen['sources'][0].update(id='t1.user', value='Check device A.', trace_refs=['t1.c1.m2', 'unavailable'])
    frozen['expectations'][0]['source_refs'] = ['t1.user']
    frozen['sha256'] = content_sha256(frozen['expectations'])
    projected['expectations_sha256'] = frozen['sha256']
    projected['data_needs'][0].update(need='none', reason='解释已给出的文字', missing=[])
    client = ScriptClient(['done'])
    evaluator = llmtracing.TranscriptEvaluation(transcript_material(), {'context_memory': common.PROCESS_SPECS['context_memory']},
        None, client, trace_id='contract-map', expectations=frozen, projection=projected)
    evaluator.run()
    prompt = json.loads(client.requests[0][-1]['content'])
    assert prompt['source_to_evidence']['t1.user'] == ['t1.c1.m2']
    assert 't1.user' not in {row['id'] for row in prompt['evidence']}
    assert evaluator.evidence.read_ids == set()  # Directory candidates are not receipts.


def project_case():
    ob = common.Obligation('project:retry_after_non_retryable', 'planning_routing', '重复调用',
                           '不可重试后拦住同参重发', source='project')
    links = {'planning_routing:repeat': dict(link_id='planning_routing:repeat', link_type='planning_routing',
        input=[dict(ref='rule', field='')], output=[dict(ref='repeat', field='')])}
    pairs = [(ob.obligation_id, 'planning_routing:repeat')]
    units, codes = process_output.build_units(pairs, projection.criteria_for(pairs, links, {ob.obligation_id: ob}), links)
    return dict(dimension='planning_routing', units=units, criteria=codes, sources=[]), links, {ob.obligation_id: ob}


def validate_reply(raw, prompt, links, obs, *, e=E, required=(), readable=('call', 'rule', 'repeat')):
    return process_output.validate_submission(raw, prompt['units'], prompt['criteria'], links, set(readable),
        axis_id=prompt['dimension'], obligations=obs, expectations=e, required=required, sources=prompt.get('sources', []))


def test_confirmed_project_obligation_is_its_own_criterion_not_an_invented_expectation():
    prompt, links, obs = project_case()
    raw = unit_reply(prompt, pass_evidence=['call'])
    row, = validate_reply(raw, prompt, links, obs)
    ob, = obs.values()
    assert row['expected'] == f'{ob.obligation_id}：{ob.duty}'
    assert row['criterion_refs'] == [ob.obligation_id] and row['expectation_ids'] == []
    raw['units'][0]['checks'] = []
    with pytest.raises(ValueError, match='判准须恰好'): validate_reply(raw, prompt, links, obs)


def test_confirmed_project_breach_can_generate_a_problem_without_inventing_e():
    prompt, links, obs = project_case()
    raw = unit_reply(prompt, 'fail', '工具明确不可重试后仍同参重发')
    row, = validate_reply(raw, prompt, links, obs)
    ob, = obs.values()
    assert row['problems'][0]['expected'] == f'{ob.obligation_id}：{ob.duty}'
    assert row['problems'][0]['expectation_ids'] == []
    assert row['problems'][0]['source_refs'] == [ob.obligation_id]
    raw['problems'][0]['breaks'] = ['U1/obligation:' + ob.obligation_id]
    with pytest.raises(ValueError, match='breaks'): validate_reply(raw, prompt, links, obs)


def test_transcript_briefing_keeps_rules_as_readable_evidence_without_creating_e():
    client = ScriptClient(['done'])
    evaluator = llmtracing.TranscriptEvaluation(transcript_material(), {'model_capability': common.PROCESS_SPECS['model_capability']},
        None, client, trace_id='coverage-briefing', expectations=E, projection=PROJECTION)
    evaluator.run()
    prompt = json.loads(client.requests[0][-1]['content'])
    briefing, = prompt['axes']
    assert prompt['expectations'] == [] and prompt['expectation_sources'] == []
    # Rule texts are read like any other evidence; the briefing does not inline them.
    assert 'original_blocks' not in briefing and 'Only report known device state.' not in json.dumps(briefing)
    assert any('Only report known device state.' in b['text'] for b in evaluator.sources['model_capability'])
    for spec in briefing['units'].values():
        assert 'blocks' not in spec
        assert all(briefing['criteria'][c].startswith('obligation:') for c in spec['criteria'])
    # A rule-dependent obligation has no manufactured generic/expectation criterion.
    assert all(not u['criteria'] for u in briefing['units'].values() if u['obligation'] == 'output_contract')


def test_greek_axis_is_rejected_by_declared_schema():
    raw = unit_reply({'dimension': 'knowledge_data', 'units': {'U1': {'criteria': ['C1']}}}, 'fail')
    raw['problems'][0]['axes'] = ['χ']
    with pytest.raises(ValueError): enforce_output(raw, process_output.OUTPUT, caller='test')
    raw['problems'][0]['axes'] = ['knowledge_data']
    enforce_output(raw, process_output.OUTPUT, caller='test')


def test_instruction_container_requires_all_original_rules_in_this_call():
    source = {'component': 'system', 'value': {'instructions': ['禁止编造', '完整输出 JSON']}}
    actual = {'messages': [{'role': 'system', 'content': '规则：禁止编造。完整输出 JSON。'}]}
    assert source_in_inputs(source, [actual])
    assert not source_in_inputs(source, [{'messages': [{'role': 'system', 'content': '禁止编造'}]}])
    assert not source_in_inputs(source, [{'messages': [{'role': 'user', 'content': '禁止编造。完整输出 JSON。'}]}])
    assert not source_in_inputs(source, [{'kind': 'message', 'role': 'user', 'origin': 'model_request', 'text': '禁止编造。完整输出 JSON。'}])
    assert source_in_inputs(source, [{'kind': 'system', 'origin': 'model_request', 'text': '禁止编造。完整输出 JSON。'}])
    assert not source_in_inputs(source, [])
    assert not source_in_inputs({**source, 'value': {'instructions': []}}, [actual])
    assert not source_in_inputs({**source, 'value': {'instructions': ['禁止编造'], 'unknown_wrapper': 'x'}}, [actual])


def test_model_source_match_never_borrows_other_call_or_rewrites_source():
    prompt, links, obs, texts = design_case()
    frozen = copy.deepcopy(prompt)
    raw = design_reply(prompt)
    rows = validate_reply(raw, prompt, links, obs)
    assert all(text in rows[0]['expected'] for text in texts)
    assert prompt == frozen
    wrong = copy.deepcopy(prompt)
    for b in wrong['sources']: b['link_ids'] = ['model_capability:other-call']
    with pytest.raises(ValueError, match='本次适用版本/实际输入'): validate_reply(raw, wrong, links, obs)
    assert prompt == frozen


@pytest.mark.parametrize('scope', ['observed_at_collection_not_verified_run_version', 'reference'])
def test_unverified_design_version_cannot_support_pass_or_fail(scope):
    prompt, links, obs, _ = design_case()
    for block in prompt['sources']: block['scope'] = scope
    with pytest.raises(ValueError, match='本次适用版本'): validate_reply(design_reply(prompt), prompt, links, obs)
    row, = validate_reply(design_reply(prompt, 'insufficient_evidence'), prompt, links, obs)
    assert row['outcome'] == 'insufficient_evidence' and row['missing'] == ['运行版本未核实']
    assert not row['problems']


def test_rule_and_separate_condition_survive_unit_problem_and_summary():
    prompt, links, obs, texts = design_case()
    rows = validate_reply(design_reply(prompt), prompt, links, obs)
    row, = rows
    check, = row['criterion_checks']
    assert row['expectation_ids'] == [] and check['criterion_ref'].startswith('design:')
    assert {q['quote'] for q in check['quotes']} == set(texts)
    assert len({q['path'] for q in check['quotes']}) == 2
    assert row['problems'][0]['expected'] == row['expected']
    out = common._outcome(rows, obs, '完整输出违约', '实际输入规则', {}, {}, axis_id='model_capability')
    assert out.output['assessment']['verdict'] == 'problematic'
    assert all(text in out.output['issues'][0]['expected'] for text in texts)
    assert all(text in out.summary.as_dict()['items'][0]['reason'] for text in texts)


@pytest.mark.parametrize('mutation', ['quote', 'unknown_ref', 'undelivered_ref', 'retired_block_field'])
def test_rule_citations_are_verbatim_and_point_at_delivered_design_records(mutation):
    prompt, links, obs, _ = design_case()
    raw = design_reply(prompt)
    item = raw['units'][0]
    if mutation == 'quote': item['rules'][0]['quotes'][0]['quote'] = '只要片段字段齐全（改写）'
    if mutation == 'unknown_ref': item['rules'][0]['quotes'][0]['ref'] = 'B1'
    if mutation == 'undelivered_ref': item['rules'][0]['quotes'][0]['ref'] = 'rule'
    if mutation == 'retired_block_field': item['blocks'] = []
    with pytest.raises(ValueError): validate_reply(raw, prompt, links, obs)


def test_rule_citation_error_is_repairable_with_unchanged_material(monkeypatch):
    texts = ['仅最终响应适用；用户取消时例外。', '整个响应必须是 JSON，不得附加说明或代码围栏。']
    request = {'messages': [{'role': 'system', 'content': text} for text in texts]}
    call = dict(id='call', kind='model_calls', turn='turn1', scope='current', exact_request={'status': 'available'},
        fields={'exact_request': {'status': 'available', 'value': request},
                'output': {'status': 'available', 'value': '说明\n```json\n{"answer":"ok"}\n```'}})
    data = dict(records=[call], model_calls=[call], contents={}, sources=[], gaps=[], coverage=[])
    prompts = []
    class Client:
        def complete_json(self, system, user, **kwargs):
            p, _ = json.JSONDecoder().raw_decode(user)
            prompts.append((p, user, system + render_output_constraint(kwargs['output_spec'])))
            assert not p['expectations'] and not p['criteria']
            # Rule texts arrive once, inside the delivered record, not as a separate block list.
            assert 'original_blocks' not in p and all(text in user for text in texts)
            assert 'call' in p['reference_catalog']['readable_ids']
            assert 'call/exact_request' not in p['reference_catalog']['readable_ids']
            reply = unit_reply(p, rules={'U1': [dict(quotes=[dict(ref='call', quote=text) for text in texts],
                applicability='当次实际系统输入，最终响应适用，用户未取消', outcome='fail', fact='整段响应含说明及代码围栏')]})
            if len(prompts) == 1: reply['units'][0]['rules'][0]['quotes'][0]['quote'] += '（改写）'
            return reply
        def usage(self): return {'llm_calls': len(prompts)}
    monkeypatch.setattr(common, 'axis_llm', lambda *a, **kw: Client())
    runtime = SimpleNamespace(spec=SimpleNamespace(project_id='llm_probe'), scenario_id='none',
        trace_id='contract-test', ensure_time_left=lambda *_: None, expectation_projection=copy.deepcopy(PROJECTION))
    spec = common.PROCESS_SPECS['model_capability']
    spec = replace(spec, obligations=tuple(o for o in spec.obligations if o.obligation_id == 'output_contract'))
    out = common.run_process_axis('model_capability', {'expectations': E, 'trace_analysis': {
        'dossier': data, 'structure': {}, 'coverage': [], 'selections': {'model_capability': {'refs': ['call']}}}},
        ScenarioAxis('model_capability', True, ''), runtime, spec)
    assert not out.failed, out.failure_reason
    assert len(prompts) == 2 and prompts[0][0] == prompts[1][0]
    assert 'U1/D1 引用 call' in prompts[1][1]
    assert out.output['assessment']['verdict'] == 'problematic'
    assert out.output['results'][0]['expectation_ids'] == []
    assert all(text in out.output['issues'][0]['expected'] for text in texts)


def test_unit_reply_defaults_do_not_invent_rule_applicability_or_action_necessity():
    prompt = dict(dimension='planning_routing', units={
        'U1': dict(criteria=['C1'], action_candidate={'need': 'external'}),
        'U2': dict(criteria=[])})
    before = copy.deepcopy(prompt)
    raw = unit_reply(prompt, 'fail')
    action, empty = raw['units']
    assert action['necessity']['state'] == 'unknown' and action['necessity']['missing']
    assert action['checks'][0]['outcome'] == 'insufficient_evidence' and action['checks'][0]['missing']
    assert empty['checks'] == [] and empty['missing_criterion']
    assert all('blocks' not in u for u in raw['units'])
    assert not raw['problems'] and prompt == before
    raw['units'][0]['necessity']['fact'] = 'changed'
    assert unit_reply(prompt)['units'][0]['necessity']['fact'] != 'changed'


@pytest.mark.parametrize('state,outcome', [('satisfied', 'pass'), ('required', 'pass'), ('required', 'fail'), ('unknown', 'insufficient_evidence')])
def test_unit_reply_configurable_necessity_preserves_positive_and_negative_scenarios(state, outcome):
    _, e, projected = fixture()
    required = projection.required_units('planning_routing', e, projected)
    links = {u['link_id']: u for u in required}
    links['t1.actual'] = dict(link_id='t1.actual', link_type='planning_routing', turn='t1',
                             input=[dict(ref='call', field='request')], output=[dict(ref='call', field='response')])
    obs = {o.obligation_id: o for o in common.PROCESS_SPECS['planning_routing'].obligations}
    pairs = [(ob, u['link_id']) for u in required for ob in u['obligation_ids']]
    units, criteria = process_output.build_units(pairs, projection.criteria_for(pairs, links, obs), links)
    prompt = dict(dimension='planning_routing', units=units, criteria=criteria)
    need = dict(state=state, fact='有效缓存已满足' if state == 'satisfied' else '刷新要求及现有数据核对',
                evidence=['call'], missing=['缓存有效性未记录'] if state == 'unknown' else [])
    raw = unit_reply(prompt, outcome, necessity={'U1': need}, matched={'U1': 't1.actual'} if state == 'required' else None,
                     pass_evidence=['call'])
    row, = validate_reply(raw, prompt, links, obs, e=e, required=required)
    assert row['necessity'] == need
    if state == 'satisfied':
        assert row['discharged'] and not row['criterion_checks'] and not row['problems']
        out = common._outcome([row], obs, '已有证据满足', '缓存', {}, {}, axis_id='planning_routing')
        assert out.output['results'] == [] and out.output['issues'] == []
        assert out.output['coverage']['satisfied_actions'][0]['necessity'] == need
    else:
        assert row['outcome'] == outcome and row['criterion_checks']
        assert bool(row['problems']) == (outcome == 'fail')


def test_unit_reply_explicit_invalid_missing_and_necessity_remain_rejectable():
    prompt = dict(dimension='planning_routing', units={'U1': dict(criteria=['C1'],
                  obligation_id='work_coverage', link_id='step')})
    raw = unit_reply(prompt, 'insufficient_evidence', missing=[])
    assert raw['units'][0]['checks'][0]['missing'] == []
    with pytest.raises(ValueError, match='missing'):
        process_output.expand(raw, prompt['units'], {'C1': 'obligation:work_coverage'},
                              {'step': {}}, set(), axis_id='planning_routing')
    raw = unit_reply(prompt, necessity={'U1': dict(state='unknown', fact='没有候选行动却填必要性', evidence=[], missing=['缺口'])},
                     pass_evidence=['step'])
    assert raw['units'][0]['necessity'] is not None
    # The helper does not silently repair explicit adversarial payloads.
    with pytest.raises(ValueError, match='仅候选行动'):
        process_output.expand(raw, prompt['units'], {'C1': 'obligation:work_coverage'},
            {'step': {}}, set(), axis_id='planning_routing')
