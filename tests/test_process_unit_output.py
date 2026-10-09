"""Synthetic v2 judgments: program-owned identities, evidence, defaults and coverage.

These cases are artificial protocol examples, not frozen business/model runs.
"""
import copy

import pytest
from tests.support.expectations import content_sha256

from impl.core.structured_output import enforce_output
from impl.projects.llm_probe.eval_axes.adapters.process_output import OUTPUT, build_units, expand

READABLE = {'R1', 'R2', 'extra'}
LINKS = {'L1': dict(link_id='L1', input=[{'ref': 'R1'}], output=[{'ref': 'R2'}, {'ref': 'missing-ref'}]),
         'L2': dict(link_id='L2', origin='expectation_deduction', input=[], output=[]),
         'L3': dict(link_id='L3', input=[], output=[])}
UNITS = {'U1': dict(obligation_id='ob_a', link_id='L1', criteria=['C1', 'C2']),
         'U2': dict(obligation_id='ob_b', link_id='L2', criteria=['C3'], candidates=['L1', 'L3'])}
CRITERIA = {'C1': 'expectation:e1', 'C2': 'obligation:ob_a', 'C3': 'expectation:e2'}
SPEC = OUTPUT


def check(c, outcome='pass', fact='事实', missing=(), upstream=(), evidence=('R1',)):
    from tests.support.unit_reply import make_check
    return make_check(c, outcome, fact, missing, upstream, evidence)


def reply(**over):
    base = dict(reason='r', scope_note='s', problems=[], units=[
        dict(unit='U1', checks=[check('C1'), check('C2')], rules=[],
             missing_criterion=[], necessity=None, matched=''),
        dict(unit='U2', checks=[check('C3', 'insufficient_evidence', missing=['缺'])], rules=[],
             missing_criterion=[], necessity=None, matched='')])
    return {**base, **over}


def run(payload, first=1):
    return expand(payload, UNITS, CRITERIA, LINKS, READABLE, axis_id='planning_routing', first_problem=first)


def test_program_restores_units_evidence_refs_and_aggregate():
    rows = run(reply())
    a = rows[0]
    assert (a['obligation_id'], a['link_id'], a['outcome']) == ('ob_a', 'L1', 'pass')
    assert a['source_refs'] == ['expectation:e1', 'obligation:ob_a'] and a['expectation_ids'] == ['e1']
    assert a['evidence'] == {'input': ['R1'], 'output': ['R2']}      # 未交付的端点不进证据
    assert rows[1]['outcome'] == 'insufficient_evidence' and rows[1]['origin'] == 'expectation_deduction'
    assert rows[1]['missing'] == ['缺']                                # 逐条判准的缺口汇总到单位


def test_matched_must_come_from_the_units_candidates():
    units = reply()['units']
    units[1]['matched'] = 'content#1'
    with pytest.raises(ValueError, match='不在它的 candidates 里'):
        run(reply(units=units))
    units[1]['matched'] = 'L1'
    assert run(reply(units=units))[1]['evidence'] == {'input': ['R1'], 'output': ['R2']}


def test_fail_is_not_hidden_by_passing_checks_and_needs_a_problem():
    units = reply()['units']
    units[0]['checks'][1] = check('C2', 'fail', '偏差')
    with pytest.raises(ValueError, match='U1/C2 判了 fail'):
        run(reply(units=units))
    problem = dict(phenomenon='现象', breaks=['U1/C2'], axes=['planning_routing'], impact='yes', evidence=['extra'])
    row = run(reply(units=units, problems=[problem]), first=3)[0]
    assert row['outcome'] == 'fail'
    p = row['problems'][0]
    assert p['problem_id'] == 'planning_routing:p3' and p['observed'] == '偏差'
    assert p['source_refs'] == ['obligation:ob_a'] and 'extra' in p['output_refs'] and 'extra' in row['evidence']['output']


def test_one_problem_spanning_units_has_one_identical_body():
    units = reply()['units']
    units[0]['checks'][0] = check('C1', 'fail', '同一事实')
    units[1]['checks'][0] = check('C3', 'fail', '另一事实')
    problem = dict(phenomenon='跨单位', breaks=['U1/C1', 'U2/C3'], axes=['planning_routing'], impact='no', evidence=['R1'])
    rows = run(reply(units=units, problems=[problem]))
    local = {'input_refs', 'output_refs', 'source_refs'}
    a, b = ({k: v for k, v in r['problems'][0].items() if k not in local} for r in rows)
    assert a == b and a['expectation_ids'] == ['e1', 'e2']
    # 各单位只带自己的端点（加模型指出的额外依据），不混入别的单位的证据。
    assert rows[0]['problems'][0]['input_refs'] == ['R1'] and rows[1]['problems'][0]['input_refs'] == []
    assert rows[1]['problems'][0]['output_refs'] == ['R1']
    from impl.projects.llm_probe.eval_axes.adapters.process_protocol import issues_for
    for r in rows:
        r['problems'][0]['expected'] = 'x'
    issue, = issues_for('planning_routing', rows)
    assert len(issue['units']) == 2 and issue['input_refs'] == ['R1']


def test_all_rejections_are_reported_together():
    bad = reply(units=[dict(unit='U1', checks=[check('C1'), check('C9')], matched='x'),
                       dict(unit='U7', checks=[], matched='')],
                problems=[dict(phenomenon='p', breaks=['U1/C1'], axes=['planning_routing'], impact='no', evidence=['nope'])])
    with pytest.raises(ValueError) as caught:
        run(bad)
    text = str(caught.value)
    for fragment in ('未知或重复单位 U7', '单位未判', 'U1 的判准须恰好为', '不是应发生单位', 'breaks', 'readable_ids 或 gap_ids'):
        assert fragment in text, fragment


def test_breaks_may_only_cite_fail_or_insufficient_checks():
    problem = dict(phenomenon='p', breaks=['U1/C1'], axes=['planning_routing'], impact='no', evidence=[])
    with pytest.raises(ValueError, match='只能引用 fail 或 insufficient_evidence'):
        run(reply(problems=[problem]))


def test_schema_has_no_program_known_fields():
    schema = SPEC.json_schema()
    names = {k for d in schema['$defs'].values() for k in d['properties']}
    assert not names & {'obligation_id', 'link_ids', 'matched_link_id', 'source_refs', 'input_refs', 'output_refs',
                        'criterion_ref', 'expectation_ids', 'problem_id'}
    assert 'missing' in schema['$defs']['GapCheck']['properties'] and 'upstream' in schema['$defs']['InvalidCheck']['properties']
    assert not {'missing', 'upstream'} & schema['$defs']['UnitJudgment']['properties'].keys()
    enforce_output(reply(), SPEC, caller='t')


def test_schema_accepted_omissions_expand_like_explicit_defaults():
    payload = reply()
    del payload['problems']
    for unit in payload['units']:
        del unit['matched'], unit['rules'], unit['missing_criterion'], unit['necessity']
        for c in unit['checks']:
            if c['outcome'] == 'pass':  # the plain branch may omit ``missing``
                c.pop('missing', None)
    enforce_output(payload, SPEC, caller='t')
    assert run(payload) == run(reply())
    # Parsing must not mutate the captured model response.
    assert 'matched' not in payload['units'][0] and 'problems' not in payload


def test_problem_without_optional_evidence_keeps_failure_and_unit_evidence():
    payload = reply()
    payload['units'][0]['checks'][0] = check('C1', 'fail', '偏差')
    payload['problems'] = [dict(phenomenon='现象', breaks=['U1/C1'], axes=['planning_routing'], impact='yes')]
    enforce_output(payload, SPEC, caller='t')
    row = run(payload)[0]
    assert row['outcome'] == 'fail'
    assert row['problems'][0]['input_refs'] == ['R1']
    assert row['problems'][0]['output_refs'] == ['R2']


@pytest.mark.parametrize('invalid', ['missing_required', 'retired_blocks', 'null', 'wrong_type', 'extra', 'unit_level_missing'])
def test_optional_defaults_do_not_relax_output_contract(invalid):
    payload = reply()
    unit = payload['units'][0]
    if invalid == 'missing_required':
        del unit['checks']
    elif invalid == 'retired_blocks':
        unit['blocks'] = []
    elif invalid == 'null':
        unit['matched'] = None
    elif invalid == 'wrong_type':
        unit['checks'][0]['missing'] = '缺'
    elif invalid == 'unit_level_missing':
        unit['missing'] = ['缺']
    else:
        unit['invented'] = 'x'
    with pytest.raises(ValueError):
        enforce_output(payload, SPEC, caller='t')


def test_model_may_omit_optional_fields():
    payload = {'reason': 'r', 'scope_note': 's', 'units': [
        {'unit': 'U1', 'checks': [check('C1'), check('C2')]},
        {'unit': 'U2', 'checks': [dict(criterion='C3', outcome='insufficient_evidence', fact='f', missing=['未见行动记录'])]}]}
    enforce_output(payload, SPEC, caller='t')
    rows = run(payload)
    assert rows[0]['matched_link_id'] == '' and rows[0]['missing'] == [] and rows[0]['upstream_issue_ids'] == []
    assert rows[1]['missing'] == ['未见行动记录']


def test_each_gap_check_states_its_own_missing():
    # The schema (not a hand-written check) refuses a gap branch without its own ``missing``.
    units = reply()['units']
    units[0]['checks'] = [check('C1', 'insufficient_evidence', missing=['缺原始请求']), check('C2', 'contract_missing')]
    with pytest.raises(ValueError, match=r'units\.\[0\]\.checks\.\[1\]\.字段必须非空但产出为空：missing'):
        run(reply(units=units))
    units[0]['checks'][1].pop('missing')
    with pytest.raises(ValueError, match=r'checks\.\[1\]\.必填字段缺失：missing'):
        run(reply(units=units))


def test_input_invalid_names_its_own_upstream_in_the_schema():
    units = reply()['units']
    units[0]['checks'][0] = check('C1', 'input_invalid', '坏输入', upstream=['planning_routing:p1'])
    assert run(reply(units=units))[0]['upstream_issue_ids'] == ['planning_routing:p1']
    units[0]['checks'][0] = check('C1', 'input_invalid', '坏输入')
    with pytest.raises(ValueError, match=r'checks\.\[0\]\.字段必须非空但产出为空：upstream'):
        run(reply(units=units))
    units[0]['checks'][0] = {**check('C1', 'pass'), 'upstream': ['planning_routing:p1']}
    with pytest.raises(ValueError, match=r'checks\.\[0\]\.额外字段不允许：upstream'):
        run(reply(units=units))


def test_shared_submission_prompt_preserves_business_rules():
    from impl.projects.llm_probe.eval_axes.adapters.process_output import UNIT_SYSTEM
    from impl.projects.llm_probe.eval_axes.adapters.process_protocol import EVIDENCE_GUIDE, JUDGING_GUIDE
    assert EVIDENCE_GUIDE in UNIT_SYSTEM and JUDGING_GUIDE in UNIT_SYSTEM
    for rule in ('提示缺失不免除独立的不编造检查', '同一事件可在不同轴分别记录独立问题', '后文正确不抵消前文错误'):
        assert rule in UNIT_SYSTEM, rule


def test_off_map_link_without_turn_can_satisfy_a_should_happen_unit():
    from impl.projects.llm_probe.process_loop.expectation_projection import bind_results, criteria_for, required_units
    from impl.projects.llm_probe.eval_axes.adapters.process_common import Obligation
    from impl.projects.llm_probe.eval_axes.adapters.process_output import validate_submission

    axis = 'tool_execution'
    e = {'expectations': [dict(expectation_id='q', source_refs=['t1.user'], about='synthetic status',
                               statement='report refreshed status', condition='总是')],
         'sources': [dict(id='t1.user', side='want', turn='t1')]}
    e['sha256'] = content_sha256(e['expectations'])
    projection = {'expectations_sha256': e['sha256'], 'data_needs': [dict(expectation_id='q', need='external', reason='synthetic current data',
                                      methods=[], missing=['synthetic catalog absent'])]}
    required = required_units(axis, e, projection)
    need, = required
    obs = {name: Obligation(name, axis, 'synthetic execution', 'synthetic duty') for name in need['obligation_ids']}
    runtime = {'new:10': dict(link_id='new:10', link_type=axis, turn='',
                             input=[{'ref': 'R1'}], output=[{'ref': 'R2'}])}
    links = {need['link_id']: need, **runtime}
    pairs = [(name, need['link_id']) for name in obs]
    units, criteria = build_units(pairs, criteria_for(pairs, links, obs), links)
    payload = dict(reason='synthetic off-map execution', scope_note='synthetic visible endpoints', units=[
        dict(unit=uid, checks=[check(c) for c in unit['criteria']], matched='new:10',
             necessity=dict(state='required', fact='synthetic fresh data still needed', evidence=['R1']))
        for uid, unit in units.items()])
    rows = validate_submission(payload, units, criteria, links, READABLE, axis_id=axis, obligations=obs,
                               expectations=e, required=required)
    assert all(row['outcome'] == 'pass' and row['matched_link_id'] == 'new:10' for row in rows)
    assert all(row['evidence'] == dict(input=['R1'], output=['R2']) for row in rows)
    other_turn = {'new:10': {**runtime['new:10'], 'turn': 'turn2'}}
    with pytest.raises(ValueError, match='轮次'):
        bind_results(copy.deepcopy(rows), obs, e, required, runtime_links=other_turn)


@pytest.mark.parametrize('kind', ['missing', 'duplicate', 'unknown'])
def test_unit_coverage_is_exact_even_without_problems(kind):
    payload = reply()
    if kind == 'missing':
        payload['units'].pop()
    elif kind == 'duplicate':
        payload['units'].append(copy.deepcopy(payload['units'][0]))
    else:
        payload['units'][0]['unit'] = 'U404'
    with pytest.raises(ValueError, match='单位未判|未知或重复单位'):
        run(payload)


def test_submission_order_cannot_change_program_unit_order_or_inputs():
    payload = reply()
    payload['units'].reverse()
    before = copy.deepcopy((payload, UNITS, CRITERIA, LINKS))
    assert run(payload) == run(reply())
    assert (payload, UNITS, CRITERIA, LINKS) == before


@pytest.mark.parametrize('field,value', [
    ('checks', None), ('checks', {}), ('blocks', []), ('blocks', {}),
    ('rules', None), ('rules', 'D1'), ('missing_criterion', 'missing'),
    ('necessity', False), ('matched', 1),
    ('outcome', 'pass'), ('criterion_refs', ['expectation:e1']),
])
def test_unit_field_types_and_program_owned_fields_remain_strict(field, value):
    payload = reply()
    payload['units'][0][field] = value
    with pytest.raises(ValueError):
        run(payload)


@pytest.mark.parametrize('field,value', [
    ('criterion', 1), ('outcome', 'sound'), ('outcome', True), ('fact', None),
    ('fact', 42), ('missing', [False]), ('missing', None),
    ('criterion_ref', 'expectation:e1'), ('observed', 'model must use fact'),
])
def test_atomic_check_types_and_extra_fields_remain_strict(field, value):
    payload = reply()
    payload['units'][0]['checks'][0][field] = value
    with pytest.raises(ValueError):
        run(payload)


@pytest.mark.parametrize('field,value', [('reason', ''), ('reason', None), ('scope_note', ''),
                                          ('scope_note', []), ('units', {}), ('problems', None)])
def test_top_level_output_remains_strict(field, value):
    payload = reply(**{field: value})
    with pytest.raises(ValueError):
        run(payload)


def test_build_units_assigns_reusable_short_ids_without_mutation():
    links = {
        'run1': dict(link_id='run1', turn='turn1'),
        'run2': dict(link_id='run2', turn='t2'),
        'off_map': dict(link_id='off_map', turn=''),
        'need': dict(link_id='need', turn='t1', origin='expectation_deduction',
                     action_candidate=True, data_need={'expectation_id': 'e1', 'need': 'external',
                                                       'reason': 'synthetic fresh data', 'methods': [], 'missing': ['no tool catalog']}),
        'other_need': dict(link_id='other_need', turn='t1', origin='expectation_deduction'),
    }
    pairs = [('a', 'run1'), ('b', 'need'), ('c', 'run2')]
    criteria = {pairs[0]: ['expectation:e1', 'obligation:a'],
                pairs[1]: ['expectation:e1'], pairs[2]: ['obligation:c']}
    before = copy.deepcopy((pairs, criteria, links))
    units, codes = build_units(pairs, criteria, links)
    assert list(units) == ['U1', 'U2', 'U3']
    assert codes == {'C1': 'expectation:e1', 'C2': 'obligation:a', 'C3': 'obligation:c'}
    assert units['U1'] == dict(obligation_id='a', link_id='run1', criteria=['C1', 'C2'])
    assert units['U2']['candidates'] == ['run1', 'off_map']
    assert units['U2']['action_candidate'] == links['need']['data_need']
    assert (pairs, criteria, links) == before
    assert build_units(pairs, criteria, links) == (units, codes)
    links['need']['turn'] = 'case'
    case_units, _ = build_units(pairs, criteria, links)
    assert case_units['U2']['candidates'] == ['run1', 'run2', 'off_map']


def test_single_candidate_is_matched_by_the_program_only_for_non_action_units():
    one = {**UNITS, 'U2': {**UNITS['U2'], 'candidates': ['L1']}}
    rows = expand(reply(), one, CRITERIA, LINKS, READABLE, axis_id='planning_routing')
    assert rows[1]['matched_link_id'] == 'L1'
    # Two candidates stay the judge's choice; an action candidate may legitimately match none.
    assert expand(reply(), UNITS, CRITERIA, LINKS, READABLE, axis_id='planning_routing')[1]['matched_link_id'] == ''
    action = {**LINKS, 'L2': {**LINKS['L2'], 'action_candidate': True}}
    payload = reply()
    payload['units'][1]['necessity'] = dict(state='unknown', fact='f', evidence=[], missing=['缓存'])
    assert expand(payload, one, CRITERIA, action, READABLE, axis_id='planning_routing')[1]['matched_link_id'] == ''
