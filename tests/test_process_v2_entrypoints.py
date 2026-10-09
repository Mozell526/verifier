"""V2 entry-point contracts. Synthetic evidence and scripted models only."""
from __future__ import annotations

import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from impl.core.tool_loop import History
from impl.projects.llm_probe.business_trace.design_rules import dossier_blocks
from impl.projects.llm_probe.business_trace.tools import EvidenceIndex
from impl.projects.llm_probe.business_trace.providers.llmtracing_transcript import build_transcript
from impl.projects.llm_probe.eval_axes.adapters import process_output
from impl.projects.llm_probe.process_loop import evaluation as agno
from impl.projects.llm_probe.process_loop import llmtracing
from impl.projects.llm_probe.process_loop.expectation_projection import criteria_for
from tests.support.expectations import E, PROJECTION, content_sha256
from tests.support.unit_reply import make_rule, set_outcome
from tests.test_llmtracing_tool_loop import (
    ScriptClient, all_ids, common, evaluation, make_trace, material, payload,
)

RULE = '整个响应必须是 JSON。'
CONDITION = '仅在用户确认后适用；取消时例外。'


def model_transcript():
    trace = make_trace()
    calls = trace.project_fields['business_trace']['records']['calls']
    for call in calls:
        call['pre']['messages'][0] = {'role': 'system', 'content': CONDITION + '\n' + RULE}
    return build_transcript(trace, trace.project_fields['business_trace'])


def dossier():
    def row(ref, kind, **fields):
        return {'id': ref, 'kind': kind, 'turn': 'turn1', 'scope': 'current',
                'fields': {k: {'status': 'available', 'value': v} for k, v in fields.items()}}
    return {'records': [row('call', 'model_calls', exact_request={'messages': [
                {'role': 'system', 'content': CONDITION}, {'role': 'system', 'content': RULE},
                {'role': 'user', 'content': 'Check device A.'}]}),
            row('answer', 'messages', content='not JSON')], 'contents': {}, 'gaps': [],
            'sources': [], 'coverage': []}


def agno_instance(obligation='output_contract'):
    """Submission boundary with real index/rule sources; nested loop is covered in test_process_loop."""
    instance = agno.Evaluation.__new__(agno.Evaluation)
    instance.dossier = dossier()
    instance.expectations, instance.projection, instance.submitted = E, PROJECTION, {}
    instance.index = EvidenceIndex(instance.dossier)
    instance.receipts = agno.EvaluationReceipts(instance.index, {'eval_model_capability'}, agno.result_refs)
    ob = next(o for o in common.PROCESS_SPECS['model_capability'].obligations if o.obligation_id == obligation)
    links = {'model_capability:call': {'link_id': 'model_capability:call', 'link_type': 'model_capability',
             'turn': 'turn1', 'input': [{'ref': 'call', 'field': 'exact_request'}],
             'output': [{'ref': 'answer', 'field': 'content'}], 'facts': {}}}
    pairs = [(ob.obligation_id, 'model_capability:call')]
    criteria = criteria_for(pairs, links, {ob.obligation_id: ob})
    units, codes = process_output.build_units(pairs, criteria, links)
    instance.cases = {'model_capability': agno.AxisCase('model_capability', {ob.obligation_id: ob}, links,
                      {}, pairs, {}, criteria, units, codes,
                      dossier_blocks(instance.dossier, list(links.values()), 'model_capability'))}
    return instance


def fixture(provider, obligation='output_contract'):
    if provider == 'agno':
        instance = agno_instance(obligation)
        case = instance.cases['model_capability']
        units, blocks = case.units, case.sources
        submit = instance._make_submit('model_capability')
        def read(ids=None):
            instance.index.collect(ids or ['call', 'answer'])
            instance.receipts.post_batch(History(calls=[]), [])
    else:
        spec = common.PROCESS_SPECS['model_capability']
        spec = replace(spec, obligations=tuple(o for o in spec.obligations if o.obligation_id == obligation))
        instance = llmtracing.TranscriptEvaluation(model_transcript(), {'model_capability': spec}, None, None,
                    expectations=E, projection=PROJECTION, trace_id='v2')
        units, blocks = instance.units['model_capability'], instance.sources['model_capability']
        submit = instance._submitter('model_capability')
        def read(ids=None):
            instance.evidence.read(ids or list(instance.evidence.records))
            instance.post_batch_hook.post_batch(History(calls=[]), [])
    return instance, units, blocks, submit, read


def reply(units):
    return {'reason': '核对原文', 'scope_note': '单次调用边界', 'units': [
        {'unit': uid, 'checks': [{'criterion': c, 'outcome': 'insufficient_evidence', 'fact': '尚待核对',
                                 'missing': ['运行证据']} for c in unit['criteria']],
         'missing_criterion': [] if unit['criteria'] else ['缺适用判准']}
        for uid, unit in units.items()], 'problems': []}


def owned_ref(unit, sources, text):
    """Record id of the unit's own design source holding ``text`` (what a judge would cite)."""
    return next(b['ref'] for b in sources if unit['link_id'] in b['link_ids'] and text in b['text'])


def rule_reply(units, blocks, outcome='fail'):
    result = reply(units)
    for item in result['units']:
        quotes = [{'ref': owned_ref(units[item['unit']], blocks, text), 'quote': text} for text in (RULE, CONDITION)]
        item.update(missing_criterion=[], rules=[make_rule(outcome, quotes, applicability='该次调用实际收到的完整规则及例外',
                                                           fact='完整响应为自然语言，不是 JSON', evidence=[quotes[0]['ref']])])
        if outcome == 'fail':
            result['problems'].append({'phenomenon': '完整输出违约', 'breaks': [item['unit'] + '/D1'],
                                      'axes': ['model_capability'], 'impact': 'unknown'})
    return result


@pytest.mark.parametrize('provider', ['agno', 'transcript'])
def test_entries_use_identical_shared_schema_and_validator(provider):
    module = agno if provider == 'agno' else llmtracing
    assert module.OUTPUT is process_output.OUTPUT
    assert module.validate_submission is process_output.validate_submission
    assert 'units' in module.OUTPUT.json_schema()['properties']
    assert 'results' not in module.OUTPUT.json_schema()['properties']
    _, units, blocks, submit, read = fixture(provider)
    read()
    assert submit(**rule_reply(units, blocks))['accepted']


@pytest.mark.parametrize('provider', ['agno', 'transcript'])
def test_design_only_criterion_preserves_condition_in_problem(provider):
    instance, units, blocks, submit, read = fixture(provider)
    read()
    result = submit(**rule_reply(units, blocks))
    assert result['accepted'], result
    assert result['issues']
    assert all(RULE in p['expected'] and CONDITION in p['expected'] for p in result['issues'])
    assert all(not p['expectation_ids'] for p in result['issues'])
    assert all(c['quotes'] for row in instance.submitted['model_capability'] for c in row['criterion_checks'])


@pytest.mark.parametrize('provider', ['agno', 'transcript'])
@pytest.mark.parametrize('mutation', ['quote', 'runtime_ref', 'retired_blocks', 'invent_ref', 'unit', 'old_schema'])
def test_both_entries_reject_invalid_quote_coverage_identity_and_old_schema(provider, mutation):
    _, units, blocks, submit, read = fixture(provider)
    read()
    good = rule_reply(units, blocks)
    bad = copy.deepcopy(good)
    if mutation == 'quote':
        bad['units'][0]['rules'][0]['quotes'][0]['quote'] = '必须有字段（改写的假引文）'
    elif mutation == 'runtime_ref':  # delivered runtime output is evidence, not a design-rule source
        bad['units'][0]['rules'][0]['quotes'][0]['ref'] = 'answer' if provider == 'agno' else 't1.c1.response'
    elif mutation == 'retired_blocks':
        bad['units'][0]['blocks'] = []
    elif mutation == 'invent_ref':
        bad['units'][0]['rules'][0]['quotes'][0]['ref'] = 'B999999'
    elif mutation == 'unit':
        bad['units'][0]['unit'] = 'invented-event'
    else:
        bad = {'reason': 'old', 'scope_note': 'old', 'results': []}
    result = submit(**bad)
    assert not result['accepted'], result
    assert submit(**good)['accepted']


@pytest.mark.parametrize('provider', ['agno', 'transcript'])
def test_rules_must_be_read_and_do_not_grant_runtime_endpoint_receipts(provider):
    _, units, blocks, submit, read = fixture(provider)
    result = submit(**rule_reply(units, blocks, 'pass'))
    # Rule texts are no longer pre-delivered: citing an unread record is rejected.
    assert not result['accepted'] and '不是已交付记录 id' in result['error']
    read(sorted({b['ref'] for b in blocks}))
    result = submit(**rule_reply(units, blocks, 'pass'))
    assert not result['accepted'] and '必要端点' in result['error']
    read()
    assert submit(**rule_reply(units, blocks, 'pass'))['accepted']


def test_removed_system_rule_is_not_in_later_model_sources_even_when_response_replayed():
    trace = make_trace()
    trace.project_fields['business_trace']['records']['calls'][1]['pre']['messages'][0] = {'role': 'system', 'content': 'New rules only.'}
    transcript = build_transcript(trace, trace.project_fields['business_trace'])
    instance = llmtracing.TranscriptEvaluation(transcript, {'model_capability': common.PROCESS_SPECS['model_capability']},
                    None, None, expectations=E, projection=PROJECTION, trace_id='removed')
    assert 't1.c1.response' in instance.evidence.records['t1.c2']['input_refs']
    units, sources = instance.units['model_capability'], instance.sources['model_capability']
    later = {uid: unit for uid, unit in units.items() if unit['link_id'] == 't1.c2.response'}
    assert len(later) == len(instance.obligations['model_capability'])
    removed = next(b for b in sources if 'Only report known device state.' in b['text'])
    assert 't1.c1.response' in removed['link_ids'] and 't1.c2.response' not in removed['link_ids']
    owned_by_later = [b for b in sources if 't1.c2.response' in b['link_ids']]
    assert owned_by_later and all('Only report known device state.' not in b['text'] for b in owned_by_later)
    assert any('New rules only.' in b['text'] for b in owned_by_later)

    # 旧调用规则即使全文读过也不能借给后一次；同一提交改用本次规则后才接受。
    instance.evidence.read(list(instance.evidence.records))
    instance.post_batch_hook.post_batch(History(calls=[]), [])
    assert removed['ref'] in instance.post_batch_hook.readable
    answer = payload('model_capability', instance=instance)
    uid = next(uid for uid, unit in later.items() if unit['obligation_id'] == 'output_contract')
    row = next(row for row in answer['units'] if row['unit'] == uid)
    row['missing_criterion'] = []
    row['rules'] = [make_rule('pass', [{'ref': removed['ref'], 'quote': 'Only report known device state.'}],
                              evidence=['t1.c2.response'])]
    submit = instance._submitter('model_capability')
    rejected = submit(**answer)
    assert not rejected['accepted'] and '未核实为本次适用版本' in rejected['error'], rejected
    current = next(b for b in owned_by_later if 'New rules only.' in b['text'])
    row['rules'][0].update(quotes=[{'ref': current['ref'], 'quote': 'New rules only.'}])
    accepted = submit(**answer)
    assert accepted['accepted'], accepted


def test_transcript_covers_every_response_and_multiple_observed_tools():
    trace = make_trace()
    calls = trace.project_fields['business_trace']['records']['calls']
    second_tool = {'id': 'tool-2', 'type': 'function', 'function': {'name': 'other', 'arguments': '{}'}}
    calls[0]['outcome']['response']['choices'][0]['message']['tool_calls'].append(second_tool)
    calls[1]['pre']['messages'].append({'role': 'tool', 'tool_call_id': 'tool-2', 'content': 'other data'})
    transcript = build_transcript(trace, trace.project_fields['business_trace'])
    instance = llmtracing.TranscriptEvaluation(transcript, common.PROCESS_SPECS, None, None,
                expectations=E, projection=PROJECTION, trace_id='multi')
    for axis in ('model_capability', 'intent_understanding', 'planning_routing'):
        assert len(instance.units[axis]) == 2 * len(instance.obligations[axis])
    for axis in ('tool_execution', 'knowledge_data'):
        assert len(instance.links[axis]) == 2
        assert len(instance.units[axis]) == 2 * len(instance.obligations[axis])
    assert all(not link['output'] for link in instance.links['tool_execution'].values())
    assert all(e['ref'] in instance.evidence.records for links in instance.links.values() for link in links.values()
               for side in ('input', 'output') for e in link[side])
    for axis in ('model_capability', 'planning_routing', 'knowledge_data'):
        incomplete = payload(axis, instance=instance)
        incomplete['units'].pop()
        result = instance._submitter(axis)(**incomplete)
        assert not result['accepted'] and '单位未判' in result['error']


def need_material():
    expected = {**E, 'expectations': [{'expectation_id': 'E1', 'source_refs': ['user'],
        'about': 'device A', 'statement': 'Report current device state', 'condition': 'Refresh when requested', 'ambiguity_group': ''}],
        'sources': [{'id': 'user', 'side': 'want', 'turn': 't1', 'scope': 'request', 'component': 'user',
                     'value': 'Check device A.', 'trace_refs': ['t1.c1.m2']}]}
    expected['sha256'] = content_sha256(expected['expectations'])
    expected['material_sha256'] = content_sha256({'sources': expected['sources'], 'missing': expected['missing']})
    projection = {'data_needs': [{'expectation_id': 'E1', 'need': 'external', 'reason': 'Current external state',
                                 'methods': [], 'missing': ['tool declaration unavailable']}],
                  'expectations_sha256': expected['sha256']}
    return expected, projection


@pytest.mark.parametrize('state', ['satisfied', 'required', 'unknown'])
def test_candidate_necessity_preserved_and_unresolved_actions_not_lost(state):
    expected, projection = need_material()
    axis = 'planning_routing'
    instance = llmtracing.TranscriptEvaluation(material(), {axis: common.PROCESS_SPECS[axis]}, None, None,
                expectations=expected, projection=projection, trace_id=state)
    result = payload(axis, instance=instance)
    candidate = next(u for u in result['units'] if 'action_candidate' in instance.units[axis][u['unit']])
    candidate['necessity'] = {'state': state, 'fact': '有效缓存' if state == 'satisfied' else '时效和行动仍须核对',
                              'evidence': ['t1.c1.m2'], **({'missing': ['cache validity']} if state == 'unknown' else {})}
    if state == 'satisfied':
        candidate['checks'] = []
    if state == 'required':
        result['problems'] = [{'phenomenon': '必须行动未定位',
            'breaks': [candidate['unit'] + '/' + c['criterion'] for c in candidate['checks']],
            'axes': [axis, 'intent_understanding'], 'impact': 'unknown'}]
    client = ScriptClient([[('evidence_read', {'ids': all_ids()})], [('eval_' + axis, result)]])
    instance.meter.client = client
    output = instance.run()[axis]
    assert not output.failed, output.failure_reason
    if state == 'satisfied':
        assert not any(r['origin'] == 'expectation_deduction' for r in output.output['results'])
        assert not output.output['issues']
        assert output.output['coverage']['satisfied_actions'][0]['necessity']['state'] == state
    else:
        rows = [r for r in output.output['results'] if r['origin'] == 'expectation_deduction']
        assert rows and all(r['outcome'] == 'insufficient_evidence' for r in rows)
        if state == 'required':
            assert output.output['issues'][0]['attribution'] == 'unresolved'
            assert 'Refresh when requested' in output.output['issues'][0]['expected']


def test_required_candidate_cannot_skip_and_unknown_cannot_pass():
    expected, projection = need_material()
    instance = llmtracing.TranscriptEvaluation(material(), {'planning_routing': common.PROCESS_SPECS['planning_routing']},
                    None, None, expectations=expected, projection=projection, trace_id='required')
    instance.evidence.read(all_ids())
    instance.post_batch_hook.post_batch(History(calls=[]), [])
    for state, outcome in [('required', 'not_applicable'), ('unknown', 'pass')]:
        result = payload('planning_routing', instance=instance)
        candidate = next(u for u in result['units'] if 'action_candidate' in instance.units['planning_routing'][u['unit']])
        candidate['necessity'] = {'state': state, 'fact': '仍需核对', 'evidence': ['t1.c1.m2'],
                                  **({'missing': ['cache validity']} if state == 'unknown' else {})}
        for check in candidate['checks']:
            check['outcome'] = outcome
        assert not instance._submitter('planning_routing')(**result)['accepted']


def test_shared_validator_rejects_unknown_upstream_before_provider_boundary():
    instance = evaluation(None, ('intent_understanding',))
    result = payload('intent_understanding', 'input_invalid', instance=instance, upstream=['planning_routing:p999'])
    rejected = instance._submitter('intent_understanding')(**result)
    assert not rejected['accepted'] and '不是已记录的问题 id' in rejected['error']


def test_design_prefix_does_not_bypass_provider_receipts_without_shared_validation():
    instance = evaluation(None, ('model_capability',))
    ob = instance.obligations['model_capability']['output_contract']
    row = {'obligation_id': ob.obligation_id, 'link_id': 't1.c1.response', 'outcome': 'pass',
           'source_refs': ['design:invented'], 'evidence': {'input': ['t1.c1.system'], 'output': ['t1.c1.response']}}
    errors = instance.evidence.validate([row], {ob.obligation_id: ob}, set(instance.evidence.records), expectations=E)
    assert any('完整正文回执' in error for error in errors)


def test_transcript_projection_receives_only_pre_run_tool_declarations(monkeypatch):
    trace = make_trace()
    calls = trace.project_fields['business_trace']['records']['calls']
    calls[0]['pre']['tools'] = [{'name': 'lookup', 'description': 'query current state', 'parameters': {}}]
    calls[1]['pre']['tools'] = [{'name': 'runtime-tool-secret', 'parameters': {}}]
    transcript = build_transcript(trace, trace.project_fields['business_trace'])
    seen = []
    monkeypatch.setattr(llmtracing, 'axis_llm', lambda *a, **kw: SimpleNamespace(usage=lambda: {}))
    monkeypatch.setattr(llmtracing, 'prepare', lambda e, client, trace_id, *, tools: seen.append(tools) or PROJECTION)
    monkeypatch.setattr(llmtracing.TranscriptEvaluation, 'run', lambda self: {})
    llmtracing.run_evaluation(transcript, common.PROCESS_SPECS, None, None, expectations=E, trace_id='pre-run')
    assert seen and seen[0]
    assert all(b['component'] == 'tools' for b in seen[0])
    assert all('runtime-tool-secret' not in b['text'] and 'state unknown' not in b['text'] for b in seen[0])


@pytest.mark.parametrize('provider', ['agno', 'transcript'])
def test_unverified_collection_version_cannot_prove_violation(provider):
    _, units, blocks, submit, read = fixture(provider)
    read()
    for block in blocks:
        block['scope'] = 'observed_at_collection_not_verified_run_version'
    result = submit(**rule_reply(units, blocks))
    assert not result['accepted'] and '未核实' in result['error']


@pytest.mark.parametrize('delivered', [True, False])
def test_model_expectation_uses_underlying_source_not_verbatim_extracted_statement(delivered):
    expected, projection = need_material()
    assert expected['expectations'][0]['statement'] not in str(material())
    if not delivered:
        expected['sources'][0].update(value='An entirely different request', trace_refs=[])
    instance = llmtracing.TranscriptEvaluation(material(), {'model_capability': common.PROCESS_SPECS['model_capability']},
                None, None, expectations=expected, projection=projection, trace_id='source')
    result = payload('model_capability', instance=instance)
    row = next(r for r in result['units'] if 'candidates' in instance.units['model_capability'][r['unit']])
    row['matched'] = 't1.c1.response'
    for check in row['checks']:
        set_outcome(check, 'pass', evidence=['t1.c1.response'])
    instance.evidence.read(all_ids())
    instance.post_batch_hook.post_batch(History(calls=[]), [])
    accepted = instance._submitter('model_capability')(**result)
    assert accepted['accepted'] is delivered, accepted
    if not delivered:
        assert '出处未证实进入本次输入' in accepted['error']


def test_same_batch_upstream_issue_is_not_yet_an_accepted_receipt():
    axes = ('intent_understanding', 'context_memory')
    instance = evaluation(None, axes)
    upstream = payload('intent_understanding', 'fail', instance=instance)
    downstream = payload('context_memory', 'input_invalid', instance=instance, upstream=['intent_understanding:p1'])
    client = ScriptClient([[('evidence_read', {'ids': all_ids()})],
                          [('eval_intent_understanding', upstream), ('eval_context_memory', downstream)],
                          [('eval_context_memory', downstream)]])
    instance.meter.client = client
    outcomes = instance.run()
    assert all(not result.failed for result in outcomes.values()), [o.failure_reason for o in outcomes.values()]
    calls = outcomes['context_memory'].output['view']['loop_calls']
    assert calls[2]['result']['accepted'] is False
    assert '不是已记录的问题 id' in calls[2]['result']['error']
    assert calls[3]['result']['accepted'] is True


def test_repeated_context_prefix_does_not_count_same_transfer_twice():
    trace = make_trace()
    calls = trace.project_fields['business_trace']['records']['calls']
    third = copy.deepcopy(calls[1])
    third['call_id'] = 'c'
    calls.append(third)
    transcript = build_transcript(trace, trace.project_fields['business_trace'])
    instance = llmtracing.TranscriptEvaluation(transcript, {'context_memory': common.PROCESS_SPECS['context_memory']},
                None, None, expectations=E, projection=PROJECTION, trace_id='prefix')
    arrivals = [link for link in instance.links['context_memory'].values() if link['obligation_ids'] == ['arrives_intact']]
    assert len(arrivals) == 2  # one response replay and one missing tool-origin boundary
    assert len({tuple(e['ref'] for e in link['output']) for link in arrivals}) == 2


def test_invented_runtime_match_is_rejected():
    expected, projection = need_material()
    instance = llmtracing.TranscriptEvaluation(material(), {'intent_understanding': common.PROCESS_SPECS['intent_understanding']},
                None, None, expectations=expected, projection=projection, trace_id='invented')
    result = payload('intent_understanding', instance=instance)
    row = next(r for r in result['units'] if 'candidates' in instance.units['intent_understanding'][r['unit']])
    row['matched'] = 'transcript'
    rejected = instance._submitter('intent_understanding')(**result)
    assert not rejected['accepted'] and 'candidates' in rejected['error']


@pytest.mark.parametrize('provider', ['agno', 'transcript'])
@pytest.mark.parametrize('enabled', [True, False], ids=['enabled-axis', 'no-axes'])
@pytest.mark.parametrize('mutation', ['stale_e', 'stale_projection', 'missing_e_hash',
                                      'missing_projection_hash', 'missing_need', 'duplicate_need', 'unknown_need'])
def test_constructors_reject_invalid_e_identity_before_preparing_or_calling_tools(monkeypatch, provider, enabled, mutation):
    expected, projected = need_material()
    if mutation == 'stale_e':
        expected['expectations'][0]['statement'] = 'Changed requirement'
    elif mutation == 'stale_projection':
        expected['expectations'][0]['condition'] = 'Changed condition, same E ID'
        expected['sha256'] = content_sha256(expected['expectations'])
    elif mutation == 'missing_e_hash':
        expected.pop('sha256')
    elif mutation == 'missing_projection_hash':
        projected.pop('expectations_sha256')
    elif mutation == 'missing_need':
        projected['data_needs'].clear()
    elif mutation == 'duplicate_need':
        projected['data_needs'].append(copy.deepcopy(projected['data_needs'][0]))
    else:
        projected['data_needs'][0]['expectation_id'] = 'unregistered'
    client = ScriptClient([])
    def unexpected(*a, **kw):
        pytest.fail('invalid identity must fail before analysis/evidence/ToolLoop preparation')
    monkeypatch.setattr(agno, 'Analysis', unexpected)
    monkeypatch.setattr(llmtracing, 'TranscriptEvidence', unexpected)
    axes = ('intent_understanding',) if enabled else ()
    with pytest.raises(ValueError, match='sha256|恰好覆盖'):
        if provider == 'agno':
            agno.Evaluation(dossier(), client, expectations=expected, projection=projected,
                            trace_id='invalid-identity', enabled=axes)
        else:
            llmtracing.TranscriptEvaluation(material(), {a: common.PROCESS_SPECS[a] for a in axes}, None, client,
                                           expectations=expected, projection=projected, trace_id='invalid-identity')
    assert client.requests == []
