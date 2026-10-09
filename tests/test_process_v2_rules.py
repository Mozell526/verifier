"""Synthetic v2 provenance/necessity contracts, never real business or model runs.

Exercise the shared submission validator, not mocks of production validation.
All fixtures are local to this file; no expectation-axis migration helpers.
"""
import copy
import json

import pytest
from tests.support.expectations import content_sha256
from tests.support.unit_reply import make_check, make_rule, set_outcome

from impl.projects.llm_probe.business_trace.design_rules import COLLECTION, dossier_blocks
from impl.projects.llm_probe.eval_axes.adapters.process_common import Obligation, _outcome
from impl.projects.llm_probe.eval_axes.adapters.process_output import OUTPUT, build_units, validate_submission
from impl.projects.llm_probe.eval_axes.adapters.process_protocol import issues_for
from impl.projects.llm_probe.process_loop.expectation_projection import criteria_for, required_units

RULE = '整个响应必须为 JSON，禁止代码围栏。'
CONDITION = '仅最终响应适用；用户说 "取消" 时例外。\n不要省略这项条件。'


def block(text=RULE, *, ref='request', path='/messages/0/content', scope='actual_input', owner='step'):
    return dict(id=f'synthetic:{ref}:{path}:{scope}', ref=ref, path=path, text=text,
                component='system', scope=scope, link_ids=[owner])


def rule(outcome='pass', *, quotes=None, missing=()):
    return make_rule(outcome, quotes if quotes is not None else [dict(ref='request', quote=RULE)],
                     applicability='synthetic rule, confirmed current version and applicable condition',
                     fact='synthetic complete response inspected', missing=missing, evidence=['response'])


def problem(breaks=('U1/D1',), *, axis='model_capability', unresolved=False):
    return dict(phenomenon='synthetic response violates the cited rule', breaks=list(breaks),
                axes=[axis, 'intent_understanding'] if unresolved else [axis], impact='unknown')


def case(*, axis='model_capability', source='trace', raw_blocks=None, refs=()):
    """Program material plus a legal shared-schema payload; each call is independent."""
    links = {'step': dict(link_id='step', link_type=axis, turn='t1',
                          input=[{'ref': 'request'}], output=[{'ref': 'response'}])}
    blocks = [block()] if raw_blocks is None else raw_blocks
    units, criteria = build_units([('rule', 'step')], {('rule', 'step'): list(refs)}, links)
    item = dict(unit='U1', checks=[make_check(c, 'pass', '', evidence=['response']) for c in units['U1']['criteria']],
                rules=[rule()] if blocks else [])
    return dict(payload=dict(reason='synthetic judgment', scope_note='synthetic visible endpoints', units=[item]),
                units=units, criteria=criteria, links=links, readable={'request', 'response', 'definition', 'cache'},
                axis_id=axis, obligations={'rule': Obligation('rule', axis, 'synthetic step', 'synthetic duty', source=source)},
                expectations={'expectations': [], 'sha256': content_sha256([])}, sources=blocks)


def submit(c):
    return validate_submission(**c)


def item(c):
    return c['payload']['units'][0]


def fail(c):
    set_outcome(item(c)['rules'][0], 'fail', fact='synthetic complete response inspected')
    c['payload']['problems'] = [problem(axis=c['axis_id'])]
    return c


def candidate_case(state='required'):
    axis, ob_id = 'planning_routing', 'work_coverage'
    e = dict(sources=[dict(id='t1.user', side='want', turn='t1', value='synthetic refresh request')],
             expectations=[dict(expectation_id='fresh', source_refs=['t1.user'], about='synthetic current status',
                                statement='report refreshed status', condition='user explicitly requested refresh')])
    e['sha256'] = content_sha256(e['expectations'])
    projection = {'expectations_sha256': e['sha256'], 'data_needs': [dict(expectation_id='fresh', need='external', reason='synthetic time-sensitive fact',
                                      methods=[], missing=['synthetic tool catalog absent'])]}
    required = required_units(axis, e, projection)
    need, = required
    runtime = dict(link_id='actual', link_type=axis, turn='turn1',
                   input=[{'ref': 'request'}], output=[{'ref': 'response'}])
    links = {need['link_id']: need, 'actual': runtime}
    obs = {ob_id: Obligation(ob_id, axis, 'synthetic arrangement', 'arrange necessary work', source='trace')}
    pairs = [(ob_id, need['link_id'])]
    units, criteria = build_units(pairs, criteria_for(pairs, links, obs), links)
    necessity = dict(state=state, fact='synthetic runtime evidence establishes necessity state', evidence=['cache'])
    if state == 'unknown':
        necessity['missing'] = ['synthetic cache freshness unknown']
    checks = [] if state == 'satisfied' else [dict(criterion='C1', outcome='insufficient_evidence',
                                                    fact='synthetic action not located', missing=['synthetic action record absent'])]
    payload = dict(reason='synthetic candidate action', scope_note='synthetic visible state',
                   units=[dict(unit='U1', checks=checks, necessity=necessity)])
    if state == 'required':
        payload['problems'] = [problem(('U1/C1',), axis=axis, unresolved=True)]
    return dict(payload=payload, units=units, criteria=criteria, links=links,
                readable={'request', 'response', 'cache'}, axis_id=axis, obligations=obs,
                expectations=e, required=required)


def upstream_issue():
    """A real validator-produced record for a synthetic earlier context failure."""
    c = fail(case(axis='context_memory'))
    issue, = issues_for('context_memory', submit(c))
    return issue


def test_design_rule_gets_program_identity_and_only_failed_rule_enters_problem():
    c = case(source='agno', refs=['obligation:rule'])
    item(c)['rules'] = [rule(), rule('fail')]
    # Same quote, different judgments: short rule numbers refer to list positions.
    c['payload']['problems'] = [problem(('U1/D2',))]
    before = copy.deepcopy(c)
    row, = submit(c)
    assert c == before
    assert row['outcome'] == 'fail'
    assert [v['outcome'] for v in row['criterion_checks']] == ['pass', 'pass', 'fail']
    assert row['criterion_refs'][0] == 'obligation:rule'
    ref = row['criterion_checks'][2]['criterion_ref']
    assert ref.startswith('design:') and len(ref.removeprefix('design:')) == 64
    assert row['expectation_ids'] == []
    assert row['problems'][0]['source_refs'] == [ref]
    assert row['problems'][0]['expected'] == f'request/messages/0/content：{RULE}'
    assert row['problems'][0]['observed'] == item(c)['rules'][1]['fact']
    assert submit(c)[0]['criterion_refs'] == row['criterion_refs']


def test_demand_general_obligation_and_design_rule_are_preserved_together():
    c = fail(case(source='agno', refs=['expectation:e', 'obligation:rule']))
    c['expectations']['expectations'] = [dict(expectation_id='e', about='synthetic answer', statement='answer status',
                                             condition='only after confirmation', source_refs=['t1.user'])]
    c['expectations']['sha256'] = content_sha256(c['expectations']['expectations'])
    set_outcome(item(c)['checks'][0], 'fail', fact='synthetic general check')
    c['payload']['problems'][0]['breaks'].insert(0, 'U1/C1')
    row, = submit(c)
    assert row['criterion_refs'][:2] == ['expectation:e', 'obligation:rule']
    assert row['criterion_checks'][2]['criterion_ref'].startswith('design:')
    assert row['expectation_ids'] == ['e']
    assert row['expected'] == ('expectation:e：synthetic answer：answer status（条件：only after confirmation）\n'
                               'obligation:rule：synthetic duty\n' + f'request/messages/0/content：{RULE}')
    assert row['problems'][0]['expected'] == ('expectation:e：synthetic answer：answer status（条件：only after confirmation）\n'
                                              + f'request/messages/0/content：{RULE}')


def test_multiple_original_locations_keep_rule_condition_exception_in_issue_and_summary():
    c = case(raw_blocks=[block(), block(CONDITION, path='/messages/1/content')])
    item(c)['rules'][0]['quotes'].append(dict(ref='request', quote=CONDITION))
    fail(c)
    row, = submit(c)
    expected = f'request/messages/0/content：{RULE}\nrequest/messages/1/content：{CONDITION}'
    assert row['expected'] == row['problems'][0]['expected'] == expected
    quotes = row['criterion_checks'][0]['quotes']
    assert [(q['path'], q['quote']) for q in quotes] == [('/messages/0/content', RULE), ('/messages/1/content', CONDITION)]
    output = _outcome([row], c['obligations'], 'synthetic reason', 'synthetic scope', {}, {}, axis_id=c['axis_id'])
    assert output.output['issues'][0]['expected'] == expected
    assert output.output['results'][0]['checks'][0]['criterion_checks'][0]['quotes'] == quotes
    assert expected in output.summary.items[0]['reason']


@pytest.mark.parametrize('outcome', ['pass', 'fail'])
@pytest.mark.parametrize('scope', [COLLECTION, 'reference'])
@pytest.mark.parametrize('axis', ['model_capability', 'context_memory', 'tool_execution', 'planning_routing'])
def test_unverified_versions_cannot_establish_conformance_or_violation(axis, scope, outcome):
    c = case(axis=axis, raw_blocks=[block(scope=scope)])
    if outcome == 'fail':
        fail(c)
    with pytest.raises(ValueError, match='未核实为本次适用版本/实际输入'):
        submit(c)


@pytest.mark.parametrize('scope', [COLLECTION, 'reference'])
def test_unverified_version_stays_insufficient_evidence_with_its_gap(scope):
    c = case(raw_blocks=[block(scope=scope)])
    item(c)['rules'] = [rule('insufficient_evidence', missing=['synthetic run version is not verified'])]
    row, = submit(c)
    assert row['outcome'] == 'insufficient_evidence'
    assert row['missing'] == ['synthetic run version is not verified']
    assert row['criterion_checks'][0]['quotes'][0]['scope'] == scope
    assert row['problems'] == []


@pytest.mark.parametrize('axis', ['context_memory', 'tool_execution', 'planning_routing'])
def test_execution_scoped_rule_is_usable_by_its_execution_axis(axis):
    row, = submit(fail(case(axis=axis, raw_blocks=[block(scope='execution')])))
    assert row['outcome'] == 'fail'
    assert row['criterion_checks'][0]['quotes'][0]['scope'] == 'execution'


@pytest.mark.parametrize('outcome', ['pass', 'fail'])
def test_model_cannot_borrow_execution_rule_not_in_its_actual_input(outcome):
    c = case(raw_blocks=[block(scope='execution')])
    if outcome == 'fail':
        fail(c)
    with pytest.raises(ValueError, match='模型规则只能来自该次实际输入'):
        submit(c)


@pytest.mark.parametrize('outcome', ['pass', 'fail'])
def test_actual_input_scope_does_not_waive_receiving_call_ownership(outcome):
    c = case()
    # Source is still visible for review but belongs to a different call.
    c['sources'][0]['link_ids'] = ['different-call']
    if outcome == 'fail':
        fail(c)
    with pytest.raises(ValueError, match='未核实为本次适用版本/实际输入'):
        submit(c)


@pytest.mark.parametrize('bad_quote', ['entire response must be JSON', RULE.replace('禁止', '允许'),
                                       RULE.replace('，', ','), ' ', ''])
def test_quotes_are_verbatim_not_paraphrased_or_normalized(bad_quote):
    c = case()
    item(c)['rules'][0]['quotes'][0]['quote'] = bad_quote
    with pytest.raises(ValueError):
        submit(c)


@pytest.mark.parametrize('bad_ref', ['B1', 'not-delivered', 'synthetic:request', 'response'])
def test_quotes_must_cite_a_delivered_design_record_id(bad_ref):
    # 'response' is delivered but is runtime output, not a design-text source.
    c = case()
    item(c)['rules'][0]['quotes'][0]['ref'] = bad_ref
    with pytest.raises(ValueError, match='U1/D1 引用'):
        submit(c)


def test_quote_existing_in_another_record_cannot_be_claimed_at_a_different_record():
    c = case(raw_blocks=[block(), block(CONDITION, ref='definition', path='/fields/system_message/value', scope='execution')])
    item(c)['rules'][0]['quotes'][0]['ref'] = 'definition'
    with pytest.raises(ValueError, match='U1/D1 引用 definition'):
        submit(c)


def test_rule_cannot_cite_a_source_owned_by_another_unit():
    c = case(raw_blocks=[block(owner='another-unit')])
    with pytest.raises(ValueError, match='未核实为本次适用版本'):
        submit(c)


def test_message_tool_and_format_blocks_resolve_escaped_nested_quote_paths():
    message = {'role': 'system', 'content': CONDITION + '\n' + RULE}
    tool = {'type': 'function', 'function': {'name': 'synthetic_lookup', 'description': '输入编号 "X"，\n只读查询。',
                                          'parameters': {'type': 'object', 'properties': {'id': {'type': 'string'}}}}}
    field = {'type': 'string', 'description': '字段 "a/b~c" 不得为空。\n仅最终响应。'}
    fmt = {'type': 'object', 'properties': {'a/b~c': field}, 'required': ['a/b~c']}
    request = {'messages': [message], 'tools': [tool], 'response_format': fmt}
    c = case()
    dossier = {'records': [dict(id='request', kind='model_calls', fields={
        'exact_request': dict(status='available', value=request)})]}
    raw = dossier_blocks(dossier, list(c['links'].values()), c['axis_id'])
    # Not recursive string leaves: one whole message, one tool, format + field.
    assert len(raw) == 4
    assert sorted(b['component'] for b in raw) == ['format', 'format', 'system', 'tools']
    c = case(raw_blocks=raw)
    prefix = '/fields/exact_request/value'
    quotes = [dict(ref='request', quote=message['content']),
              dict(ref='request', quote=tool['function']['description']),
              dict(ref='request', quote=field['description'])]
    item(c)['rules'] = [rule('fail', quotes=quotes)]
    c['payload']['problems'] = [problem()]
    row, = submit(c)
    resolved = row['criterion_checks'][0]['quotes']
    assert [q['quote'] for q in resolved] == [message['content'], tool['function']['description'], field['description']]
    # Program resolves each quote to the whole block holding it (message, tool, format field).
    assert [q['path'] for q in resolved] == [prefix + '/messages/0', prefix + '/tools/0',
                                           prefix + '/response_format/properties/a~1b~0c']
    assert all(q['quote'] in row['problems'][0]['expected'] for q in quotes)


@pytest.mark.parametrize('location,field,value', [
    ('rule', 'quotes', []), ('rule', 'quotes', None), ('rule', 'applicability', ' '),
    ('rule', 'fact', ' '), ('rule', 'outcome', 'sound'), ('rule', 'missing', 'version'),
    ('rule', 'criterion_ref', 'design:invented'), ('rule', 'id', 'D1'),
    ('quote', 'path', '/messages/0'), ('quote', 'block', 'B1'), ('quote', 'quote', 1), ('quote', 'ref', 7),
])
def test_rule_schema_and_semantic_required_fields_are_strict(location, field, value):
    c = case()
    target = {'rule': item(c)['rules'][0], 'quote': item(c)['rules'][0]['quotes'][0]}[location]
    target[field] = value
    with pytest.raises(ValueError):
        submit(c)


@pytest.mark.parametrize('outcome', ['insufficient_evidence', 'contract_missing'])
def test_each_rule_gap_needs_its_own_missing_not_another_rules_missing(outcome):
    c = case()
    item(c)['rules'] = [rule(outcome, missing=['synthetic first gap']), rule(outcome)]
    with pytest.raises(ValueError, match=r'rules\.\[1\]\.字段必须非空但产出为空：missing'):
        submit(c)


def test_omitted_rule_and_problem_defaults_are_instantiated_without_mutation():
    implicit = fail(case())
    item(implicit)['rules'][0].pop('missing', None)
    explicit = copy.deepcopy(implicit)
    item(explicit)['rules'][0]['missing'] = []
    explicit['payload']['problems'][0]['evidence'] = []
    before = copy.deepcopy(implicit)
    assert submit(implicit) == submit(explicit)
    assert implicit == before


@pytest.mark.parametrize('breaks', [[], ['U1/D404'], ['U2/D1'], ['U1/C1'], ['U1/design:invented']])
def test_problem_rule_references_must_point_at_a_real_failed_short_rule(breaks):
    c = fail(case())
    c['payload']['problems'][0]['breaks'] = breaks
    with pytest.raises(ValueError, match='breaks'):
        submit(c)


def test_each_failed_rule_requires_a_problem_even_when_another_failure_is_reported():
    c = fail(case())
    item(c)['rules'].append(rule('fail'))
    with pytest.raises(ValueError, match='U1/D2.*breaks'):
        submit(c)


@pytest.mark.parametrize('state', ['satisfied', 'required', 'unknown'])
def test_candidate_necessity_is_mandatory_even_when_checks_look_complete(state):
    c = candidate_case(state)
    del item(c)['necessity']
    with pytest.raises(ValueError, match='候选行动必须给 necessity'):
        submit(c)


def test_runtime_unit_must_not_invent_candidate_necessity():
    c = case()
    item(c)['necessity'] = dict(state='required', fact='synthetic', evidence=['request'])
    with pytest.raises(ValueError, match='仅候选行动必须给 necessity'):
        submit(c)


@pytest.mark.parametrize('state', ['satisfied', 'required'])
@pytest.mark.parametrize('evidence', [[], ['not-delivered'], ['planning_routing:p1']])
def test_satisfied_and_required_need_delivered_runtime_evidence(state, evidence):
    c = candidate_case(state)
    item(c)['necessity']['evidence'] = evidence
    with pytest.raises(ValueError, match='字段必须非空但产出为空：evidence|gap_ids 的编号'):
        submit(c)


@pytest.mark.parametrize('field,value', [('state', 'optional'), ('evidence', 'cache'), ('evidence', [1]),
                                         ('missing', 'unknown'), ('fact', ' '), ('invented', 'x')])
def test_necessity_types_enums_extra_fields_and_nonblank_fact_remain_strict(field, value):
    c = candidate_case()
    item(c)['necessity'][field] = value
    with pytest.raises(ValueError):
        submit(c)


@pytest.mark.parametrize('explanation', ['synthetic valid cache contains current data',
                                        'synthetic equivalent path already completed'])
def test_satisfied_candidate_is_recorded_without_problem_or_exercised_unit(explanation):
    c = candidate_case('satisfied')
    item(c)['necessity']['fact'] = explanation
    row, = submit(c)
    assert row['discharged'] is True and row['problems'] == []
    assert row['criterion_checks'] == []
    assert row['expectation_ids'] == ['fresh'] and row['source_refs'] == ['expectation:fresh']
    assert row['necessity']['evidence'] == ['cache'] and row['observed'] == explanation
    outcome = _outcome([row], c['obligations'], 'synthetic reason', 'synthetic scope', {}, {}, axis_id=c['axis_id'])
    assert outcome.output['results'] == outcome.output['issues'] == []
    assert outcome.output['coverage']['satisfied_actions'] == [row]
    assert all(n == 0 for n in outcome.output['assessment']['composition']['counts'].values())


@pytest.mark.parametrize('field,value', [('checks', [make_check('C1', 'pass', 'synthetic', evidence=['cache'])]),
                                         ('rules', [rule()]), ('missing_criterion', ['missing'])])
def test_satisfied_candidate_cannot_hide_a_judgment_or_rule(field, value):
    c = candidate_case('satisfied')
    item(c)[field] = value
    with pytest.raises(ValueError, match='判准须恰好|已满足不展开'):
        submit(c)


def test_unknown_necessity_keeps_the_unit_and_both_missing_reasons():
    c = candidate_case('unknown')
    row, = submit(c)
    assert not row['discharged']
    assert row['outcome'] == 'insufficient_evidence'
    assert row['missing'] == ['synthetic action record absent', 'synthetic cache freshness unknown']
    assert row['necessity']['state'] == 'unknown'
    assert row['source_refs'] == ['expectation:fresh']
    outcome = _outcome([row], c['obligations'], 'synthetic reason', 'synthetic scope', {}, {}, axis_id=c['axis_id'])
    assert outcome.output['assessment']['verdict'] == 'not_evaluable'
    assert outcome.output['assessment']['composition']['counts']['insufficient_evidence'] == 1


@pytest.mark.parametrize('outcome', ['pass', 'fail', 'input_invalid', 'contract_missing', 'not_applicable'])
def test_unknown_necessity_cannot_turn_into_a_decisive_check(outcome):
    c = candidate_case('unknown')
    item(c)['checks'][0] = make_check('C1', outcome, 'synthetic', ['synthetic missing'], ['planning_routing:p1'], ['cache'])
    with pytest.raises(ValueError, match='必要性说不清必须落缺证'):
        submit(c)


def test_unknown_necessity_must_say_what_is_missing_even_with_a_check_gap():
    c = candidate_case('unknown')
    del item(c)['necessity']['missing']
    with pytest.raises(ValueError, match='necessity.必填字段缺失：missing'):
        submit(c)


def test_required_refresh_cannot_be_skipped_as_not_applicable():
    c = candidate_case()
    item(c)['checks'][0]['outcome'] = 'not_applicable'
    c['payload']['problems'] = []
    with pytest.raises(ValueError, match='必须做不能用 not_applicable'):
        submit(c)


@pytest.mark.parametrize('outcome', ['pass', 'fail'])
def test_required_unmatched_action_cannot_claim_a_performed_exercise(outcome):
    c = candidate_case()
    set_outcome(item(c)['checks'][0], outcome, evidence=['response'])
    if outcome == 'pass':
        c['payload']['problems'] = []
    else:
        c['payload']['problems'][0]['axes'] = [c['axis_id']]
    with pytest.raises(ValueError, match='未对接实际行使'):
        submit(c)


def test_unresolved_missing_action_requires_a_problem_and_does_not_assign_planning_fault():
    c = candidate_case()
    row, = submit(c)
    issue, = issues_for(c['axis_id'], [row])
    assert row['outcome'] == 'insufficient_evidence'
    assert row['matched_link_id'] == '' and row['upstream_issue_ids'] == []
    assert issue['attribution'] == 'unresolved'
    assert issue['attribution_axes'] == ['planning_routing', 'intent_understanding']
    assert 'user explicitly requested refresh' in issue['expected']
    assert issue['input_refs'] == ['cache']
    c['payload']['problems'] = []
    with pytest.raises(ValueError, match='必须做未发生未定位.*breaks'):
        submit(c)


@pytest.mark.parametrize('axes', [['planning_routing'], ['tool_execution', 'knowledge_data'],
                                  ['planning_routing', 'planning_routing']])
def test_unresolved_missing_action_needs_distinct_candidate_axes_including_current(axes):
    c = candidate_case()
    c['payload']['problems'][0]['axes'] = axes
    with pytest.raises(ValueError, match='至少两个|包含本轴|非法或重复'):
        submit(c)


@pytest.mark.parametrize('outcome', ['pass', 'fail'])
def test_required_action_may_match_positive_runtime_arrangement_evidence(outcome):
    c = candidate_case()
    item(c)['matched'] = 'actual'
    set_outcome(item(c)['checks'][0], outcome, evidence=['response'], fact='synthetic observed arrangement',
                **({} if outcome == 'pass' else {'missing': []}))
    c['payload']['problems'] = [problem(('U1/C1',), axis=c['axis_id'])] if outcome == 'fail' else []
    row, = submit(c)
    assert row['outcome'] == outcome and row['matched_link_id'] == 'actual'
    assert row['evidence'] == dict(input=['request', 'cache'], output=['response'])
    assert row['necessity']['state'] == 'required'


@pytest.mark.parametrize('recorded,reason', [('absent', '不是已记录的问题 id'), ('unresolved', '归因尚未定位')])
def test_input_invalid_requires_an_existing_localized_upstream_issue(recorded, reason):
    c = candidate_case()
    issue = upstream_issue()
    item(c)['checks'][0] = make_check('C1', 'input_invalid', 'synthetic action not located', upstream=[issue['problem_id']])
    c['payload']['problems'] = []
    c['recorded_issues'] = [] if recorded == 'absent' else [dict(issue, attribution='unresolved')]
    with pytest.raises(ValueError, match=reason):
        submit(c)


def test_existing_upstream_problem_produces_untested_not_a_new_local_failure():
    c = candidate_case()
    issue = upstream_issue()
    item(c)['checks'][0] = make_check('C1', 'input_invalid', 'synthetic action not located', upstream=[issue['problem_id']])
    c['payload']['problems'] = []
    c['recorded_issues'] = [issue]
    row, = submit(c)
    assert row['outcome'] == 'input_invalid' and row['problems'] == []
    assert row['upstream_issue_ids'] == [issue['problem_id']]
    outcome = _outcome([row], c['obligations'], 'synthetic reason', 'synthetic scope', {}, {}, axis_id=c['axis_id'])
    assert outcome.output['assessment']['verdict'] == 'untested'
    assert outcome.output['assessment']['composition']['input_invalid'][0]['upstream_issue_ids'] == [issue['problem_id']]


def test_input_invalid_cannot_be_an_unreferenced_claim_or_attached_to_other_outcomes():
    # Both directions are enforced by the schema's branches, not by hand-written checks.
    c = candidate_case()
    item(c)['checks'][0] = make_check('C1', 'input_invalid', 'synthetic action not located')
    c['payload']['problems'] = []
    with pytest.raises(ValueError, match='checks.\\[0\\].字段必须非空但产出为空：upstream'):
        submit(c)
    c = candidate_case()
    issue = upstream_issue()
    item(c)['checks'][0]['upstream'] = [issue['problem_id']]
    c['recorded_issues'] = [issue]
    with pytest.raises(ValueError, match='checks.\\[0\\].额外字段不允许：upstream'):
        submit(c)


def test_context_rule_loss_compares_proven_delivery_source_with_actual_input():
    axis = 'context_memory'
    link = dict(link_id='step', link_type=axis, turn='turn1',
                input=[dict(ref='run', field='input')], output=[dict(ref='request', field='exact_request')])
    dossier = {'records': [
        dict(id='run', kind='runs', run_id='synthetic-run',
             fields={'input': dict(status='available', value={'system_message': RULE})}),
        dict(id='request', kind='model_calls', reconstructed_input={'run_id': 'synthetic-run'},
             fields={'exact_request': dict(status='available', value={'messages': [dict(role='user', content='synthetic question')]})}),
    ]}
    blocks = dossier_blocks(dossier, [link], axis)
    assert len(blocks) == 2
    c = case(axis=axis, raw_blocks=blocks)
    c['links'] = {'step': link}
    c['readable'].add('run')
    source = next(b for b in c['sources'] if b['ref'] == 'run')
    received = next(b for b in c['sources'] if b['ref'] == 'request')
    assert source['scope'] == 'execution'
    assert received['scope'] == 'actual_input'
    assert RULE not in received['text']
    item(c)['rules'] = [rule('fail', quotes=[dict(ref='run', quote=RULE)])]
    item(c)['rules'][0]['fact'] = 'synthetic proven source contains JSON rule; actual request omits it'
    c['payload']['problems'] = [problem(axis=axis)]
    row, = submit(c)
    issue, = issues_for(axis, [row])
    assert issue['attribution'] == 'local' and issue['attribution_axes'] == [axis]
    assert issue['input_refs'] == ['run'] and issue['output_refs'] == ['request']
    assert issue['expected'] == f'run/fields/input/value：{RULE}'


def test_known_upstream_issue_cannot_reference_the_same_unit_it_is_supposed_to_explain():
    c = case(axis='context_memory')
    issue = upstream_issue()  # Same axis/obligation/link as this synthetic unit.
    set_outcome(item(c)['rules'][0], 'input_invalid', upstream=[issue['problem_id']])
    c['recorded_issues'] = [issue]
    with pytest.raises(ValueError, match='自身|上游'):
        submit(c)


def test_bad_input_only_blocks_dependent_unit_not_independent_no_fabrication_check():
    c = case(source='agno', raw_blocks=[], refs=['obligation:rule'])
    issue = upstream_issue()
    item(c)['checks'][0] = make_check('C1', 'input_invalid', 'synthetic bad input', upstream=[issue['problem_id']])
    c['recorded_issues'] = [issue]
    c['obligations']['no_fabrication'] = Obligation('no_fabrication', c['axis_id'], 'synthetic response', 'do not fabricate')
    c['units']['U2'] = dict(obligation_id='no_fabrication', link_id='step', criteria=['C2'])
    c['criteria']['C2'] = 'obligation:no_fabrication'
    c['payload']['units'].append(dict(unit='U2', checks=[
        make_check('C2', 'pass', '', evidence=['response'])]))
    rows = submit(c)
    assert [r['outcome'] for r in rows] == ['input_invalid', 'pass']
    assert rows[0]['upstream_issue_ids'] == [issue['problem_id']]
    assert rows[1]['upstream_issue_ids'] == []
    outcome = _outcome(rows, c['obligations'], 'synthetic reason', 'synthetic scope', {}, {}, axis_id=c['axis_id'])
    assert outcome.output['assessment']['verdict'] == 'sound'
    counts = outcome.output['assessment']['composition']['counts']
    assert counts['input_invalid'] == counts['pass'] == 1


@pytest.mark.parametrize('field,value', [('path', '/different/location'), ('scope', 'execution')])
def test_same_quote_at_different_provenance_is_not_the_same_criterion(field, value):
    c = case(axis='planning_routing')
    original, = submit(c)
    c['sources'][0][field] = value
    changed, = submit(c)
    assert changed['criterion_refs'] != original['criterion_refs']
    assert changed['criterion_checks'][0]['quotes'][0][field] == value
    assert changed['criterion_checks'][0]['quotes'][0]['quote'] == RULE


@pytest.mark.parametrize('field,value', [('phenomenon', ' '), ('axes', []), ('axes', ['made_up_axis']),
                                         ('impact', 'maybe'), ('evidence', ['not-delivered']),
                                         ('problem_id', 'invented'), ('expected', 'rewritten rule')])
def test_problem_schema_references_and_program_owned_fields_stay_strict(field, value):
    c = fail(case())
    c['payload']['problems'][0][field] = value
    with pytest.raises(ValueError):
        submit(c)


def test_rule_lookup_prefers_the_units_own_copy_over_a_shorter_twin_from_another_call():
    # Same record, same sentence twice: a shorter block owned by another call must not
    # shadow this unit's own copy (would be a false rejection), nor be accepted in its place.
    own = block(RULE + '\n其余说明。', path='/messages/0/content')
    twin = block(RULE, path='/messages/9/content', owner='another-call')
    row, = submit(fail(case(raw_blocks=[twin, own])))
    assert row['criterion_checks'][0]['quotes'][0]['path'] == '/messages/0/content'
    with pytest.raises(ValueError, match='未核实为本次适用版本'):
        submit(fail(case(raw_blocks=[twin])))


def test_misplaced_citation_is_told_where_the_rule_text_really_is():
    c = case(raw_blocks=[block(), block('其他', ref='copy', path='/state')])
    item(c)['rules'][0]['quotes'][0]['ref'] = 'copy'
    c['readable'].add('copy')
    with pytest.raises(ValueError, match="改引那条记录|不是本单位|没有设计原文|U1/D1 引用 copy"):
        submit(c)
    c = case(raw_blocks=[block(), block('其他', ref='copy', path='/state', owner='x')])
    c['sources'].append(block(RULE, ref='copy', path='/x', scope='reference', owner='x'))
    c['readable'].add('copy')
    item(c)['rules'][0]['quotes'][0]['ref'] = 'other-record'
    c['readable'].add('other-record')
    with pytest.raises(ValueError, match=r"设计原文在 \['(copy|request)'.*请改引"):
        submit(c)


def test_collection_copy_citation_resolves_to_the_runs_confirmed_copy_of_the_same_sentence():
    definition = block(ref='definition', path='/fields/description/value', scope=COLLECTION)
    execution = block(ref='run-tool', path='/fields/tool_description/value', scope='execution')
    c = case(axis='tool_execution', raw_blocks=[definition, execution])
    c['readable'].add('definition')
    item(c)['rules'][0]['quotes'][0]['ref'] = 'definition'
    row, = submit(fail(c))
    quote = row['criterion_checks'][0]['quotes'][0]
    assert quote['ref'] == 'run-tool' and quote['scope'] == 'execution'
    # Without a confirmed twin the collection-time copy still cannot establish a violation.
    only = case(axis='tool_execution', raw_blocks=[definition])
    only['readable'].add('definition')
    item(only)['rules'][0]['quotes'][0]['ref'] = 'definition'
    with pytest.raises(ValueError, match='未核实为本次适用版本'):
        submit(fail(only))
