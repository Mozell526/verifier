"""V2 requirement isolation and six-axis counterexamples; no model-quality claim."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from impl.core.structured_output import enforce_output, render_output_constraint
from impl.projects.llm_probe.business_trace.expectation_material import project_requirements
from impl.projects.llm_probe.business_trace.design_rules import project_design, dossier_blocks
from impl.projects.llm_probe.business_trace.providers.llmtracing_transcript import build_transcript
from impl.projects.llm_probe.business_trace.providers.llmtracing_evidence import TranscriptEvidence
from impl.projects.llm_probe.eval_axes.adapters import expectations as axis, process_common as common, process_output
from impl.projects.llm_probe.eval_axes.types import ScenarioAxis
from impl.projects.llm_probe.process_loop import expectation_projection as projection, evaluation
from impl.projects.llm_probe.process_loop.llmtracing import TranscriptEvaluation, OUTPUT
from tests.support.expectations import E, PROJECTION, content_sha256
from tests.support.unit_reply import make_check, make_rule, unit_reply
from tests.test_llmtracing_tool_loop import make_trace, ScriptClient, payload


def fixture(*, condition='总是'):
    material = {'sources': [dict(id='user', side='want', turn='t1', component='user',
        value='查询保单现金价值', scope='request', trace_refs=['t1.c1.m2'])], 'missing': []}
    material['sha256'] = content_sha256(material)
    entries = [dict(expectation_id='Q', source_refs=['user'], about='保单现金价值',
                    statement='告知金额', condition=condition, ambiguity_group='')]
    e = dict(expectations=entries, sources=material['sources'], missing=[], verdict='complete',
             material_sha256=material['sha256'], sha256=content_sha256(entries))
    projected = dict(expectations_sha256=e['sha256'], data_needs=[dict(expectation_id='Q', need='external', methods=[],
        reason='现金价值是外部保单事实，不是因为存在工具才需要数据', missing=['工具说明未提供'])])
    return material, e, projected


def result(ob='work_coverage', link='planning_routing:expected:Q', outcome='insufficient_evidence', ids=('Q',), matched=''):
    """Internal expanded row, not the model submission schema."""
    refs = ['expectation:' + ident for ident in ids] or [ob if ob.startswith('project:') else 'obligation:' + ob]
    missing = ['原始产出'] if outcome in {'insufficient_evidence', 'contract_missing'} else []
    return dict(obligation_id=ob, link_id=link, outcome=outcome, expectation_ids=list(ids), matched_link_id=matched,
        expectation_checks=[dict(expectation_id=x, outcome=outcome, observed='核对原文') for x in ids],
        criterion_refs=refs, criterion_checks=[dict(criterion_ref=ref, outcome=outcome,
            observed='核对原文', missing=missing[:]) for ref in refs],
        observed='没有可见的查询', source_refs=refs[:], evidence={'input': ['t1.c1.m2'], 'output': []},
        missing=missing, problems=[], upstream_issue_ids=[], judged_by='llm', flags=[])


def design_case():
    """Rule and separate condition are actual-input blocks, never E entries."""
    texts = ['仅最终响应适用；用户取消时例外。', '整个响应必须是 JSON，不得附加说明或代码围栏。']
    data = {'records': [dict(id='call', kind='model_calls', turn='turn1', scope='current', fields={
        'exact_request': {'status': 'available', 'value': {'messages': [
            {'role': 'system', 'content': text} for text in texts]}},
        'output': {'status': 'available', 'value': '说明\n```json\n{"answer":"ok"}\n```'}})], 'contents': {}}
    links = {'model_capability:call': dict(link_id='model_capability:call', link_type='model_capability', turn='turn1',
        input=[{'ref': 'call', 'field': 'exact_request'}], output=[{'ref': 'call', 'field': 'output'}])}
    ob = next(o for o in common.PROCESS_SPECS['model_capability'].obligations if o.obligation_id == 'output_contract')
    pairs = [(ob.obligation_id, 'model_capability:call')]
    units, criteria = process_output.build_units(pairs, projection.criteria_for(pairs, links, {ob.obligation_id: ob}), links)
    # ``sources`` is the program-side provenance index; it is never part of the model prompt.
    return (dict(dimension='model_capability', units=units, criteria=criteria,
                 sources=dossier_blocks(data, list(links.values()), 'model_capability')), links, {ob.obligation_id: ob}, texts)


def design_reply(prompt, outcome='fail'):
    uid, _ = next(iter(prompt['units'].items()))
    return unit_reply(prompt, rules={uid: [dict(
        quotes=[dict(ref=b['ref'], quote=json.loads(b['text'])['content']) for b in prompt['sources']],
        applicability='当次实际系统输入，最终响应适用，用户未取消', outcome=outcome,
        fact='整段响应含说明及代码围栏', missing=['运行版本未核实'] if outcome == 'insufficient_evidence' else [])]})


def test_projection_excludes_outputs_runtime_system_tools_and_caller_ability():
    trace = make_trace()
    records = trace.project_fields['business_trace']['records']
    first = records['calls'][0]['pre']
    first['messages'][0]['content'] = '[本轮 Direct 已执行] 状态=EMPTY; PRIVATE_RUNTIME'
    first['tools'] = [{'type': 'function', 'function': {'name': 'lookup', 'parameters': {'type': 'object'}}}]
    first['optional_params'] = {'response_format': {'type': 'json_object'}, 'runtime_value': 'PRIVATE_PARAM'}
    records['definitions'] = [{'data': {'system_message': '声明的静态规则',
        'instruction_templates': [{'template': '状态={status}; 不重复查询', 'instance': 'PRIVATE_INSTANCE'}]}}]
    y = project_requirements(trace, {'criterion': '按原文作答', 'capability': 'PRIVATE_CAPABILITY'})
    text = json.dumps(y, ensure_ascii=False)
    assert not any(v in text for v in ('PRIVATE_RUNTIME', 'PRIVATE_PARAM', 'PRIVATE_INSTANCE', 'PRIVATE_CAPABILITY',
                                       'state unknown', '状态={status}', '声明的静态规则', 'lookup', 'json_object'))
    assert {s['side'] for s in y['sources']} == {'want'}
    assert y['missing'] == [dict(turn='case', component='capability', reason='capability 未拆分')]
    changed = copy.deepcopy(trace)
    changed.raw_response = {'answer': 'changed'}
    changed.project_fields['business_trace']['records']['calls'][1]['outcome'] = {'event': 'failure', 'error': 'changed'}
    assert y == project_requirements(changed, {'criterion': '按原文作答', 'capability': 'different'})


def test_history_resolves_reference_but_current_assistant_is_not_input_to_e():
    trace = make_trace()
    first = trace.project_fields['business_trace']['records']['calls'][0]['pre']
    original_messages = [{'role': 'user', 'content': 'P001状态'},
        {'role': 'assistant', 'content': '有效'}, {'role': 'user', 'content': '它的缴费方式呢'}]
    trace.normalized_request['body'] = {'messages': copy.deepcopy(original_messages)}
    first['messages'] = [first['messages'][0], *original_messages]
    y = project_requirements(trace)
    assert [s['value'] for s in y['sources'] if s['side'] == 'want'] == ['它的缴费方式呢']
    assert len([s for s in y['sources'] if s['side'] == 'history']) == 2
    assert y['missing'] == [] and 'state unknown' not in json.dumps(y)


def test_agno_original_run_input_and_definition_provenance():
    trace = SimpleNamespace(turn_records=[], normalized_request={}, project_fields={'business_trace': {
        'provider': 'agno', 'status': 'succeeded', 'association': {'run_id': 'current'}, 'records': {
        'run': {'run_id': 'current', 'run_input': '查P002现金价值', 'content': 'SECRET_RESULT'},
        'definitions': [{'data': {'system_message': '只按工具结果回答'}}]}}})
    y = project_requirements(trace)
    assert [s['value'] for s in y['sources']] == ['查P002现金价值'] and y['missing'] == []
    assert 'SECRET_RESULT' not in json.dumps(y)
    blocks = project_design(trace)['blocks']
    assert any('只按工具结果回答' in b['text'] and b['scope'] == 'observed_at_collection_not_verified_run_version' for b in blocks)


@pytest.mark.parametrize('component,original', [
    ('system_message', '历史仅用于理解指代和未完成意图；历史答案不是本轮事实依据，时效性/个人数据须重新调用工具核实'),
    ('instruction_templates', '[Direct 已执行] 状态={status}；不要重复请求相同保单相同字段；可使用其他能力补充，否则把未完成项写入 gaps'),
])
def test_retired_design_gold_cases_are_original_sources_not_demands(component, original):
    trace = make_trace()
    value = original if component == 'system_message' else [{'template': original, 'instance': 'PRIVATE_INSTANTIATED_RESULT'}]
    trace.project_fields['business_trace']['records']['definitions'] = [{'data': {component: value}}]
    y = project_requirements(trace)
    assert original not in json.dumps(y, ensure_ascii=False)
    assert not y['missing']
    blocks = project_design(trace)['blocks']
    block, = [b for b in blocks if b['text'] == original]
    assert block['scope'] == 'observed_at_collection_not_verified_run_version'
    assert block['component'] == 'system' and block['path']
    assert 'PRIVATE_INSTANTIATED_RESULT' not in json.dumps(blocks, ensure_ascii=False)


@pytest.mark.parametrize('change', ['duplicate', 'runtime_ref', 'history_only', 'background_only', 'design_material',
                                   'single_ambiguity', 'empty', 'consumer_field'])
def test_invalid_expectation_sets_rejected(change):
    material, e, _ = fixture()
    p = {'expectations': copy.deepcopy(e['expectations'])}
    if change == 'duplicate': p['expectations'].append(copy.deepcopy(p['expectations'][0]))
    if change == 'runtime_ref': p['expectations'][0]['source_refs'] = ['t1.c2.response']
    if change == 'history_only': material['sources'][0].update(side='history', component='history')
    if change == 'background_only': material['sources'][0].update(side='background', component='description')
    if change == 'design_material': material['sources'][0]['component'] = 'system'
    if change == 'single_ambiguity': p['expectations'][0]['ambiguity_group'] = 'g'
    if change == 'empty': p['expectations'][0]['about'] = ' '
    if change == 'consumer_field': p['expectations'][0]['blocking'] = True
    with pytest.raises(ValueError): axis.validate(p, material)


def test_material_verdict_and_bounded_reprompt_do_not_depend_on_consumers(monkeypatch):
    material, e, _ = fixture()
    material['missing'] = [dict(component='capability', reason='capability 未拆分', turn='case')]
    sent = []
    class Client:
        def complete_json(self, system, prompt, **kwargs):
            sent.append(prompt)
            return {'expectations': e['expectations']} if len(sent) % 2 == 0 else {'expectations': []}
        def usage(self): return {'llm_calls': len(sent)}
    monkeypatch.setattr(axis, 'axis_llm', lambda *a, **kw: Client())
    runtime = SimpleNamespace(spec=None, trace_id='test', ensure_time_left=lambda *_: None, enabled_axes=['model_capability'])
    one = axis.run({'requirements': material}, ScenarioAxis('expectations', True, ''), runtime)
    runtime.enabled_axes = ['model_capability', 'fulfilled']
    two = axis.run({'requirements': material}, ScenarioAxis('expectations', True, ''), runtime)
    assert one.output == two.output and one.output['verdict'] == 'partial'
    assert len(sent) == 4 and sent[0] == sent[2]


def test_data_need_candidates_independent_of_runtime_and_tool_availability():
    _, e, projected = fixture()
    frozen = copy.deepcopy(e)
    raw = {'data_needs': projected['data_needs']}
    projection.validate_join(raw, e)
    for name in common.PROCESS_SPECS:
        units = projection.required_units(name, e, projected)
        assert units and units[0]['expectation_ids'] == ['Q'] and not units[0]['output']
        assert units[0]['action_candidate'] == (name in {'planning_routing', 'tool_execution', 'knowledge_data'})
    assert e == frozen
    projected['data_needs'][0].update(need='unknown', missing=['需求时效不明'])
    unit, = projection.required_units('knowledge_data', e, projected)
    assert unit['action_candidate'] and unit['data_need']['missing'] == ['需求时效不明']
    projection.validate_join(raw, e)
    projected['data_needs'][0]['missing'] = []
    with pytest.raises(ValueError, match='缺口'): projection.validate_join(raw, e)
    projected['data_needs'][0].update(need='none', reason='仅需解释用户给出的文本')
    assert not projection.required_units('knowledge_data', e, projected)
    assert projection.required_units('intent_understanding', e, projected)


def test_candidate_methods_quote_original_tool_description_not_requirement_ids():
    _, e, projected = fixture()
    tools = [dict(id='tool-block', component='tools', text='lookup 按保单号查询现金价值。')]
    projected['data_needs'][0].update(methods=[dict(block='tool-block', quote=tools[0]['text'])], missing=[])
    raw = {'data_needs': projected['data_needs']}
    projection.validate_join(raw, e, tools)
    projected['data_needs'][0]['methods'][0]['quote'] = '查询所有资料（改写）'
    with pytest.raises(ValueError, match='逐字'): projection.validate_join(raw, e, tools)
    projected['data_needs'][0]['methods'][0].update(block='Q', quote=tools[0]['text'])
    with pytest.raises(ValueError, match='原文位置'): projection.validate_join(raw, e, tools)


def test_candidate_method_pointer_preserves_quotes_newlines_and_source_location():
    _, e, projected = fixture()
    description = '仅查询保单的 "cash_value"。\n不得把历史金额当作当前金额。'
    tools = [dict(id='tool-block', component='tools', text=json.dumps(
        {'function': {'name': 'lookup', 'description': description}}, ensure_ascii=False))]
    projected['data_needs'][0].update(methods=[dict(block='tool-block', path='/function/description', quote=description)], missing=[])
    raw = {'data_needs': projected['data_needs']}
    projection.validate_join(raw, e, tools)
    for wrong_path in ('/function/name', '/missing', ''):
        projected['data_needs'][0]['methods'][0]['path'] = wrong_path
        with pytest.raises(ValueError, match='逐字'): projection.validate_join(raw, e, tools)


def test_missing_required_coverage_and_false_na_are_errors():
    _, e, projected = fixture()
    units = projection.required_units('planning_routing', e, projected)
    obs = {o.obligation_id: o for o in common.PROCESS_SPECS['planning_routing'].obligations}
    with pytest.raises(ValueError, match='未覆盖'): projection.bind_results([], obs, e, units)
    with pytest.raises(ValueError, match='不能用未发生'): projection.bind_results([result(outcome='not_applicable')], obs, e, units)
    row = result(outcome='pass')
    with pytest.raises(ValueError, match='未对接'): projection.bind_results([row], obs, e, units)
    row['matched_link_id'] = 't2.c1.response'
    with pytest.raises(ValueError, match='轮次'):
        projection.bind_results([row], obs, e, units, runtime_links={'t2.c1.response': {'turn': 't2'}})


def test_expected_is_derived_with_conditions_and_each_requirement_checked():
    _, e, projected = fixture(condition='投保人确认后')
    row = result(outcome='fail', matched='t1.c2.response')
    row['problems'] = [dict(source_refs=['expectation:Q'])]
    obs = {o.obligation_id: o for o in common.PROCESS_SPECS['planning_routing'].obligations}
    projection.bind_results([row], obs, e, projection.required_units('planning_routing', e, projected))
    assert '告知金额' in row['expected'] and '投保人确认后' in row['expected']
    assert row['source_refs'] == ['expectation:Q'] and row['problems'][0]['expected'] == row['expected']
    e['expectations'].append({**e['expectations'][0], 'expectation_id': 'Q2'})
    e['sha256'] = content_sha256(e['expectations'])
    row['expectation_ids'].append('Q2')
    with pytest.raises(ValueError, match='独立核对'): projection.bind_results([row], obs, e)
    with pytest.raises(ValueError, match='缺'):
        projection.check_criteria([row], {(row['obligation_id'], row['link_id']): ['expectation:Q', 'expectation:Q2']})
    raw = payload('model_capability')
    raw['units'][0]['expected'] = '只要片段字段齐全'
    with pytest.raises(ValueError): enforce_output(raw, OUTPUT, caller='test')


def test_one_actual_exercise_with_multiple_expectations_is_counted_once():
    rows = []
    for q in ['Q', 'Q2']:
        row = result(link='planning_routing:expected:' + q, ids=(q,), matched='planning_routing:path:turn1')
        row['expected'] = q
        rows.append(row)
    out = projection.coalesce(rows)
    assert len(out) == 1 and len(out[0]['checks']) == 2 and out[0]['expectation_ids'] == ['Q', 'Q2']
    assert [r['criterion_refs'] for r in out[0]['checks']] == [['expectation:Q'], ['expectation:Q2']]


def test_inherited_params_are_actual_input_and_whole_json_is_checked():
    trace = make_trace()
    for call in trace.project_fields['business_trace']['records']['calls']:
        call['pre']['optional_params'] = {'response_format': {'type': 'json_object'}}
    trace.project_fields['business_trace']['records']['calls'][1]['outcome']['response']['choices'][0]['message']['content'] = '说明\n```json\n{"answer":"ok"}\n```'
    tr = build_transcript(trace, trace.project_fields['business_trace'])
    idx = TranscriptEvidence(tr)
    assert idx.records['t1.c2.params']['canonical_ref'] == 't1.c1.params'
    assert 't1.c1.params' in idx.call_inputs('t1.c2')['input_refs']
    assert idx.records['t1.c2.response']['whole_content_json'] is False
    run = TranscriptEvaluation(tr, {'model_capability': common.PROCESS_SPECS['model_capability']}, None, None,
                              expectations=E, projection=PROJECTION, trace_id='json')
    uid = next(uid for uid, u in run.units['model_capability'].items()
               if u['link_id'] == 't1.c2.response' and u['obligation_id'] == 'output_contract')
    units, sources = {uid: run.units['model_capability'][uid]}, run.sources['model_capability']
    b = next(b for b in sources if b['component'] == 'format' and 'json_object' in b['text']
             and units[uid]['link_id'] in b['link_ids'])
    raw = unit_reply(dict(dimension='model_capability', units=units), rules={uid: [make_rule(
        'pass', [dict(ref=b['ref'], quote=b['text'])], evidence=['t1.c2.response'])]})
    rows = process_output.expand(raw, units, run.criteria['model_capability'], run.links['model_capability'],
                                 set(idx.records), axis_id='model_capability', sources=sources)
    refs = frozenset(c['criterion_ref'] for row in rows for c in row['criterion_checks'])
    errors = idx.validate(rows, run.obligations['model_capability'], set(idx.records), expectations=E, design_refs=refs)
    assert any('完整 content' in err for err in errors)
    _, e, _ = fixture()
    row = result('output_faithful', 't1.c2.response', 'pass')
    row['evidence'] = {'input': ['t1.c1.m2'], 'output': ['t1.c2.response']}
    e['sources'][0]['trace_refs'] = ['t2.c1.m2']
    assert any('未证实进入' in err for err in idx.validate([row], run.obligations['model_capability'], set(idx.records), expectations=e))


def test_required_missing_query_cross_axis_full_loop():
    _, e, projected = fixture()
    trace = make_trace()
    calls = trace.project_fields['business_trace']['records']['calls']
    calls[:] = calls[:1]
    calls[0]['pre']['messages'][1]['content'] = e['sources'][0]['value']
    trace.normalized_request['body']['message'] = e['sources'][0]['value']
    calls[0]['outcome']['response']['choices'][0]['message'] = {'role': 'assistant', 'content': '没有安排查询，直接结束'}
    tr = build_transcript(trace, trace.project_fields['business_trace'])
    axes = ('planning_routing', 'knowledge_data')
    run = TranscriptEvaluation(tr, {a: common.PROCESS_SPECS[a] for a in axes}, None, None,
                              expectations=e, projection=projected, trace_id='missing-query')
    submissions = []
    for name in axes:
        p = payload(name, instance=run)
        for item in p['units']:
            spec = run.units[name][item['unit']]
            if 'action_candidate' not in spec:
                if name == 'knowledge_data' and item['checks']:
                    item['checks'] = [make_check(c['criterion'], 'input_invalid', '规划未发起查询', upstream=['planning_routing:p1'])
                                      for c in item['checks']]
                continue
            item['necessity'] = dict(state='required', fact='本轮要求现金价值且没有已有数据或等价路径',
                                     evidence=['t1.c1.m2', 't1.c1.response'])
            item['checks'] = [make_check(c['criterion'], 'fail' if name == 'planning_routing' else 'input_invalid',
                                         '已收到要求却直接结束' if name == 'planning_routing' else '规划未发起查询',
                                         upstream=['planning_routing:p1']) for c in item['checks']]
            if name == 'planning_routing':
                item['matched'] = 't1.c1.response'
                p['problems'].append(dict(phenomenon='未安排必要查询', breaks=[item['unit'] + '/' + c['criterion'] for c in item['checks']],
                                         axes=[name], impact='unknown', evidence=[]))
        submissions.append([(f'eval_{name}', p)])
    client = ScriptClient([[('evidence_read', {'ids': list(run.evidence.records)})], *submissions])
    run.meter.client = client
    out = run.run()
    assert all(not v.failed for v in out.values()), [(k, v.failure_reason, v.usage) for k, v in out.items()]
    assert out['planning_routing'].output['assessment']['verdict'] == 'problematic'
    assert out['knowledge_data'].output['assessment']['verdict'] == 'untested'
    issue, = out['planning_routing'].output['issues']
    assert issue['attribution'] == 'local' and issue['expectation_ids'] == ['Q']
    assert all(r['upstream_issue_ids'] == [issue['problem_id']] for r in out['knowledge_data'].output['results'] if r['outcome'] == 'input_invalid')
    assert len(client.requests) == 3  # Dependent axis follows the accepted issue receipt.


def test_frozen_b_projection_separates_design_format_from_user_demands():
    from impl.core.schema import normalize_run_trace
    root = Path(__file__).resolve().parents[1]
    trace = normalize_run_trace(json.loads((root / 'report/llmtracing-calibration-draft/frozen-inputs/B.trace.json').read_text()))
    y = project_requirements(trace)
    # This historical frozen trace has no independently recorded outer request.
    # Do not promote its gateway user message to an original merely to populate E.
    assert y['sources'] == []
    assert y['missing'] == [dict(turn='t1', component='user', reason='用户原文未独立记录')]
    assert not any(s['component'] in {'system', 'tools', 'format'} for s in y['sources'])
    assert all(not ref.endswith('.response') for s in y['sources'] for ref in s['trace_refs'])
    assert not any(m['component'] in {'system', 'tools', 'format'} for m in y['missing'])
    assert any(b['component'] == 'format' and 'json_schema' in b['text'] for b in project_design(trace)['blocks'])


def test_units_list_every_required_pair_and_each_model_call_once():
    _, e, projected = fixture()
    trace = make_trace()
    tr = build_transcript(trace, trace.project_fields['business_trace'])
    run = TranscriptEvaluation(tr, {'model_capability': common.PROCESS_SPECS['model_capability']}, None, None,
                              expectations=e, projection=projected, trace_id='pending')
    pairs = [(u['obligation_id'], u['link_id']) for u in run.units['model_capability'].values()]
    assert len(pairs) == len(set(pairs))
    assert {link for ob, link in pairs if ob == 'output_faithful'} == {'model_capability:expected:Q', 't1.c1.response', 't1.c2.response'}
    assert 'obligation_id' not in OUTPUT.json_schema()['$defs']['UnitJudgment']['properties']


def test_missing_final_rejects_claimed_impact():
    trace = make_trace()
    trace.raw_response, trace.extracted_output = None, {}
    idx = TranscriptEvidence(build_transcript(trace, trace.project_fields['business_trace']))
    row = result('output_faithful', 't1.c2.response')
    row['problems'] = [dict(source_refs=[], input_refs=[], output_refs=[], impact='yes')]
    ob = {'output_faithful': common.PROCESS_SPECS['model_capability'].obligations[0]}
    _, e, _ = fixture()
    assert any('impact 必须 unknown' in s for s in idx.validate([row], ob, set(idx.records), expectations=e))


def test_requirement_must_be_actual_model_input_not_external_configuration():
    _, e, _ = fixture()
    row = result('output_faithful', 'model_capability:call', 'pass')
    row['evidence']['input'] = ['call']
    ob = {'output_faithful': common.PROCESS_SPECS['model_capability'].obligations[0]}
    links = {'model_capability:call': dict(input=[{'ref': 'call', 'field': 'exact_request'}])}
    data = {'records': [{'id': 'call', 'fields': {'exact_request': {'value': {'messages': [{'role': 'user', 'content': 'another request'}]}}}}]}
    with pytest.raises(ValueError, match='期望原文未证实'): projection.validate_dossier_expectations([row], ob, e, links, data)
    data['records'][0]['fields']['exact_request']['value']['messages'][0]['content'] = e['sources'][0]['value']
    projection.validate_dossier_expectations([row], ob, e, links, data)


def test_shared_projection_cache_survives_runtime_deadline_copy():
    from dataclasses import replace
    from impl.projects.llm_probe.eval_axes.types import AxisRuntime
    runtime = AxisRuntime(None, 'run', 'trace', 'scenario', 'case')
    one = replace(runtime, deadline=1)
    one.expectation_projection.update(PROJECTION)
    assert replace(runtime, deadline=2).expectation_projection == PROJECTION


def test_expectations_are_analysis_and_not_clustering_dimensions():
    from impl.core.table_view import eval_axes_summary
    from impl.core.axes_clustering import build_material
    from impl.projects.llm_probe.eval_axes.registry import AXIS_TYPES
    _, e, _ = fixture()
    rows = eval_axes_summary({'results': [{'type_id': 'expectations', 'status': 'succeeded', 'verdict': 'complete', 'output': e}]})
    assert rows[0]['role'] == 'analysis'
    data = build_material([{'pool_index': 0, 'request_key': 'case', 'axes': rows}], [AXIS_TYPES['expectations'].describe()])
    assert not data['axes'] and not data['refs']


def test_agno_history_is_context_only_and_current_output_excluded():
    trace = SimpleNamespace(turn_records=[], normalized_request={}, project_fields={'business_trace': {
        'provider': 'agno', 'status': 'succeeded', 'association': {'run_id': 'current'}, 'records': {
        'run': {'run_id': 'current', 'run_input': '它的缴费方式呢', 'content': 'CURRENT_SECRET'},
        'history_runs': [{'run_id': 'past', 'run_input': 'P001状态', 'content': '已生效', 'ordering': 'trace_timestamps'},
                        {'run_id': 'current', 'run_input': '它的缴费方式呢', 'content': 'CURRENT_SECRET',
                         'ordering': 'trace_timestamps'}]}}})
    y = project_requirements(trace)
    assert len([s for s in y['sources'] if s['side'] == 'history']) == 2
    assert 'CURRENT_SECRET' not in json.dumps(y)


@pytest.mark.parametrize('tools', [None, []])
def test_tool_absence_does_not_make_demand_material_partial(tools):
    trace = make_trace()
    trace.project_fields['business_trace']['records']['calls'][0]['pre']['tools'] = tools
    assert project_requirements(trace)['missing'] == []


@pytest.mark.parametrize('item', json.loads((Path(__file__).parent / 'fixtures/expectations_gold.json').read_text())['cases'], ids=lambda item: item['id'])
def test_spec_gold_fixtures_obey_provider_contract(item):
    axis.validate(item['expected'], item['material'])
    assert all(s['side'] in {'want', 'history', 'background'} for s in item['material']['sources'])
    wants = {s['id'] for s in item['material']['sources'] if s['side'] == 'want'}
    assert all(wants.intersection(e['source_refs']) for e in item['expected']['expectations'])


def test_expectation_failure_blocks_six_axes_without_starting_consumer(monkeypatch):
    from impl.projects.llm_probe.eval_axes import build_report
    from impl.projects.llm_probe.process_loop import llmtracing
    monkeypatch.setattr(axis, 'run', lambda *a: (_ for _ in ()).throw(ValueError('invalid expectations')))
    monkeypatch.setattr(llmtracing, 'axis_llm', lambda *a, **kw: pytest.fail('consumer must not start'))
    rows = {r['type_id']: r for r in build_report(SimpleNamespace(project_id='llm_probe'), make_trace())['results']}
    assert rows['expectations']['status'] == 'failed' and rows['trace_analysis']['status'] == 'succeeded'
    assert all(rows[a]['status'] == 'blocked' and rows[a]['output'] is None for a in common.PROCESS_SPECS)


def test_dossier_order_provides_planning_issues_before_dependent_data(monkeypatch):
    from impl.projects.llm_probe import capability
    from impl.projects.llm_probe.eval_axes import build_report, runner
    seen = []
    monkeypatch.setattr(capability, 'capability_business_trace', lambda _: {'provider': 'agno'})
    monkeypatch.setattr(runner, 'run_axes', lambda spec, trace, axes, **kw: seen.extend(a.type_id for a in axes) or [])
    trace = make_trace('agno')
    trace.normalized_request = {'capability_ref': 'insurance-agno-e2e'}
    build_report(SimpleNamespace(project_id='llm_probe'), trace)
    assert seen.index('expectations') < seen.index('planning_routing') < seen.index('tool_execution') < seen.index('knowledge_data')
    assert seen.index('context_memory') < seen.index('model_capability')


def test_dossier_model_cannot_borrow_other_call_even_without_e_refs():
    row = result('output_faithful', 'model_capability:call', 'pass', ids=())
    row['evidence']['input'] = ['other-call']
    ob = {'output_faithful': common.PROCESS_SPECS['model_capability'].obligations[0]}
    with pytest.raises(ValueError, match='不属于该次实际输入'):
        projection.validate_dossier_expectations([row], ob, E,
            {'model_capability:call': {'input': [{'ref': 'call', 'field': 'exact_request'}]}}, {'records': []})


def test_transcript_units_use_real_boundaries_never_placeholder_events():
    trace = make_trace()
    tr = build_transcript(trace, trace.project_fields['business_trace'])
    run = TranscriptEvaluation(tr, {'context_memory': common.PROCESS_SPECS['context_memory']}, None, None,
                              expectations=E, projection=PROJECTION, trace_id='pending')
    assert run.units['context_memory'] and all(u['link_id'] != 'transcript' for u in run.units['context_memory'].values())
    assert any(u['link_id'] == 't1.c1:input' for u in run.units['context_memory'].values())
    assert all(end['ref'] in run.evidence.records for link in run.links['context_memory'].values()
               for side in ('input', 'output') for end in link[side])


def test_all_accepted_results_finish_before_requesting_deadline_expired_prose():
    trace = make_trace()
    tr = build_transcript(trace, trace.project_fields['business_trace'])
    axes = tuple(common.PROCESS_SPECS)
    client = ScriptClient([[('evidence_read', {'ids': ['t1.request']})], [(f'eval_{a}', payload(a)) for a in axes]])
    run = TranscriptEvaluation(tr, {a: common.PROCESS_SPECS[a] for a in axes}, None, client,
                              expectations=E, projection=PROJECTION, trace_id='completed')
    original = run.post_batch_hook.post_batch
    def expire_after_submission(history, calls):
        notes = original(history, calls)
        if set(run.submitted) == set(axes): run.meter.deadline = 0
        return notes
    run.post_batch_hook.post_batch = expire_after_submission
    assert all(not value.failed for value in run.run().values())
    assert len(client.requests) == 2 and run.completion_hook.checks[-1]['decision'] == 'done'


@pytest.mark.parametrize('spec', [process_output.OUTPUT, evaluation.OUTPUT, OUTPUT], ids=['dossier', 'agno', 'transcript'])
def test_model_schema_optional_match_and_retired_block_reviews_agree(spec):
    assert spec is process_output.OUTPUT
    value = payload('context_memory')
    props = spec.json_schema()['$defs']['UnitJudgment']
    assert 'matched' not in props['required']
    assert process_output.UnitJudgment.__dataclass_fields__['matched'].default == ''
    assert 'blocks' not in props['properties']
    enforce_output(value, spec, caller='test')
    value['units'][0]['matched'] = ''
    enforce_output(value, spec, caller='test')
    value['units'][0].pop('matched')
    enforce_output(value, spec, caller='test')
    value['units'][0]['blocks'] = []
    with pytest.raises(ValueError, match='blocks'): enforce_output(value, spec, caller='test')
    rendered = render_output_constraint(spec)
    assert 'BlockReview' not in rendered and 'necessity' in rendered


def test_expectations_native_schema_accepts_no_ambiguity_group():
    material, e, _ = fixture()
    raw = {'expectations': e['expectations']}
    item_schema = axis.OUTPUT.json_schema()['$defs']['Expectation']
    assert 'ambiguity_group' in item_schema['required']
    assert all(len(e['ambiguity_group']) >= item_schema['properties']['ambiguity_group'].get('minLength', 0) for e in raw['expectations'])
    axis.validate(raw, material)
    raw['expectations'][0].pop('ambiguity_group')
    with pytest.raises(ValueError, match='ambiguity_group'): axis.validate(raw, material)


@pytest.mark.parametrize('axis_id', tuple(common.PROCESS_SPECS))
@pytest.mark.parametrize('mutation,match', [
    ('stale_content', 'E.*sha256'), ('missing_e_hash', 'E.*sha256'),
    ('stale_projection', 'expectations_sha256'), ('missing_projection_hash', 'expectations_sha256'),
    ('missing_need', '恰好覆盖'), ('missing_data_needs', '恰好覆盖'),
    ('duplicate_need', '恰好覆盖'), ('extra_need', '恰好覆盖'), ('unknown_need', '恰好覆盖'),
    ('duplicate_e_id', 'expectation_id.*唯一'),
])
def test_required_units_rejects_inconsistent_identity_before_expansion(axis_id, mutation, match):
    _, e, projected = fixture()
    if mutation == 'stale_content':
        e['expectations'][0]['condition'] = '用户确认后'
    elif mutation == 'missing_e_hash':
        e.pop('sha256')
    elif mutation == 'stale_projection':
        e['expectations'][0]['statement'] = '告知当前金额而非历史金额'
        e['sha256'] = content_sha256(e['expectations'])  # Same IDs, different E.
    elif mutation == 'missing_projection_hash':
        projected.pop('expectations_sha256')
    elif mutation == 'missing_need':
        projected['data_needs'].clear()
    elif mutation == 'missing_data_needs':
        projected.pop('data_needs')
    elif mutation in {'duplicate_need', 'extra_need'}:
        extra = copy.deepcopy(projected['data_needs'][0])
        if mutation == 'extra_need':
            extra['expectation_id'] = 'unregistered'
        projected['data_needs'].append(extra)
    elif mutation == 'unknown_need':
        projected['data_needs'][0]['expectation_id'] = 'unregistered'
    else:
        e['expectations'].append(copy.deepcopy(e['expectations'][0]))
        e['sha256'] = projected['expectations_sha256'] = content_sha256(e['expectations'])
    with pytest.raises(ValueError, match=match):
        projection.required_units(axis_id, e, projected)


def test_empty_e_has_actual_identity_and_no_validation_bypass():
    assert E['sha256'] == content_sha256([])
    assert projection.validate_projection(E, PROJECTION) == E['sha256']
    assert projection.required_units('intent_understanding', E, PROJECTION) == []
    for e, projected in [({**E, 'sha256': ''}, PROJECTION), (E, {'data_needs': []}),
                         (E, {**PROJECTION, 'expectations_sha256': content_sha256({})})]:
        with pytest.raises(ValueError, match='sha256'):
            projection.required_units('intent_understanding', e, projected)


def test_identity_uses_same_canonical_e_encoding_as_producer():
    _, e, projected = fixture()
    e['expectations'][0] = dict(reversed(list(e['expectations'][0].items())))
    assert projection.validate_projection(e, projected) == e['sha256']
    assert len(projection.required_units('intent_understanding', e, projected)[0]['obligation_ids']) == 5


def preparation_fixture():
    """Real dossier field wrappers and long provenance IDs, not hand-written B IDs."""
    description = '仅查询保单的 "cash_value"。\n不得把历史金额当作当前金额。'
    source = dict(id='turn1/records/definitions/lookup', kind='definitions', turn='turn1',
                  definition_type='tool', name='lookup', fields={
                      'name': {'status': 'available', 'value': 'lookup'},
                      'description': {'status': 'available', 'value': description}})
    link = dict(link_id='prepare', link_type='planning_routing', turn='turn1',
                input=[dict(ref=source['id'], field='definition')], output=[])
    tools = dossier_blocks({'records': [source], 'contents': {}}, [link], 'planning_routing')
    _, e, projected = fixture()
    raw = {'data_needs': copy.deepcopy(projected['data_needs'])}
    raw['data_needs'][0].update(methods=[dict(block='B1', path='/description/value', quote=description)], missing=[])
    return source, tools, e, raw


def test_preparer_short_ids_bind_quote_path_to_actual_original_provenance():
    from impl.projects.llm_probe.business_trace.dossier import resolve_node_path
    source, tools, e, raw = preparation_fixture()
    frozen_tools, frozen_reply = copy.deepcopy(tools), copy.deepcopy(raw)
    requests = []
    class Client:
        def complete_json(self, system, prompt, **kwargs):
            requests.append(json.loads(prompt))
            assert kwargs['output_spec'] is projection.JOIN_SPEC
            return raw
    prepared = projection.prepare(e, Client(), 'short-ids', tools=tools)
    sent, = requests
    assert [b['id'] for b in sent['tools']] == ['B1']
    assert 'link_ids' not in sent['tools'][0]
    assert tools[0]['id'].startswith('design:') and len(tools[0]['id']) > 64
    method, = prepared['data_needs'][0]['methods']
    assert method == dict(block=tools[0]['id'], ref=source['id'], path='/fields/description/value',
                          quote=source['fields']['description']['value'])
    assert resolve_node_path(source, method['path']) == method['quote']
    assert prepared['expectations_sha256'] == content_sha256(e['expectations'])
    assert prepared['design_sha256'] == content_sha256(tools)
    # The bound internal representation has ref/absolute path, not ToolOption's wire schema.
    assert projection.validate_projection(e, prepared) == e['sha256']
    unit, = projection.required_units('planning_routing', e, prepared)
    assert unit['data_need']['methods'] == [method]
    assert tools == frozen_tools and raw == frozen_reply


@pytest.mark.parametrize('mutation,match', [
    ('long_id', '原文位置.*B'), ('unknown_block', '原文位置.*B'),
    ('absolute_path', '原文位置'), ('wrong_path', '原文位置'),
    ('rewritten_quote', '逐字'), ('missing_need', '恰好覆盖'),
])
@pytest.mark.parametrize('repair', [False, True])
def test_preparer_rejects_bad_provenance_with_one_bounded_correction(mutation, match, repair):
    _, tools, e, good = preparation_fixture()
    bad = copy.deepcopy(good)
    method = bad['data_needs'][0]['methods'][0]
    if mutation == 'long_id':
        method['block'] = tools[0]['id']
    elif mutation == 'unknown_block':
        method['block'] = 'B999'
    elif mutation == 'absolute_path':
        method['path'] = '/fields/description/value'
    elif mutation == 'wrong_path':
        method['path'] = '/name/value'
    elif mutation == 'rewritten_quote':
        method['quote'] = '查询所有资料（不是原文）'
    else:
        bad['data_needs'] = []
    requests = []
    class Client:
        def complete_json(self, system, prompt, **kwargs):
            requests.append(prompt)
            return good if repair and len(requests) == 2 else bad
    if repair:
        prepared = projection.prepare(e, Client(), 'repair', tools=tools)
        assert projection.validate_projection(e, prepared) == e['sha256']
        assert prepared['data_needs'][0]['methods'][0]['ref'] == tools[0]['ref']
    else:
        with pytest.raises(ValueError, match=match):
            projection.prepare(e, Client(), 'reject', tools=tools)
    assert len(requests) == 2
    assert requests[1].startswith(requests[0] + '\n修正无效投影：')


def test_preparer_rejects_stale_e_before_any_model_call():
    _, tools, e, _ = preparation_fixture()
    e['expectations'][0]['statement'] = '内容变更但未重新定格'
    client = SimpleNamespace(complete_json=lambda *a, **kw: pytest.fail('stale E must not reach a model'))
    with pytest.raises(ValueError, match='E.*sha256'):
        projection.prepare(e, client, 'stale', tools=tools)
