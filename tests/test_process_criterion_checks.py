"""Synthetic atomic v2 checks; no retired assessment or commitment attachments.

The program supplies C identifiers. Design provenance tests live in
``test_process_v2_rules.py``; no fixtures from the expectation-axis migration.
"""
import copy

import pytest
from tests.support.expectations import content_sha256
from tests.support.unit_reply import make_check

from impl.core.structured_output import enforce_output
from impl.projects.llm_probe.eval_axes.adapters.process_common import Obligation
from impl.projects.llm_probe.eval_axes.adapters.process_output import OUTPUT, build_units, expand, validate_submission
from impl.projects.llm_probe.process_loop.expectation_projection import check_criteria, criteria_for

AXIS = 'planning_routing'
LINKS = {'step': dict(link_id='step', link_type=AXIS, turn='t1',
                      input=[{'ref': 'request'}], output=[{'ref': 'response'}])}
READABLE = {'request', 'response'}


def payload_for(refs, outcomes=None):
    """Build a current-schema submission and its immutable program material."""
    outcomes = outcomes or ['pass'] * len(refs)
    units, criteria = build_units([('rule', 'step')], {('rule', 'step'): refs}, LINKS)
    blocks = []  # no design-text sources in these atomic checks
    checks = [make_check(f'C{i}', outcome, f'synthetic fact {i}', ['synthetic missing evidence'], ['synthetic-upstream'], ['response'])
              for i, outcome in enumerate(outcomes, 1)]
    problems = [dict(phenomenon=f'synthetic failure {i}', breaks=[f'U1/C{i}'], axes=[AXIS], impact='unknown')
                for i, outcome in enumerate(outcomes, 1) if outcome == 'fail']
    payload = dict(reason='synthetic atomic checks', scope_note='synthetic request and response',
                   units=[dict(unit='U1', checks=checks)], problems=problems)
    return payload, units, criteria, blocks


def expanded(payload, units, criteria, blocks):
    return expand(payload, units, criteria, LINKS, READABLE, axis_id=AXIS, sources=blocks)


def submit(payload, units, criteria, blocks, *, source='agno', expectations=()):
    return validate_submission(payload, units, criteria, LINKS, READABLE, axis_id=AXIS, sources=blocks,
                               obligations={'rule': Obligation('rule', AXIS, 'synthetic step', 'synthetic duty', source=source)},
                               expectations={'expectations': list(expectations), 'sha256': content_sha256(list(expectations))})


def test_unit_schema_has_no_model_authored_aggregate_or_duplicate_ids():
    schema = OUTPUT.json_schema()
    props = schema['$defs']['UnitJudgment']['properties']
    assert not {'outcome', 'expectation_ids', 'expectation_checks', 'observed', 'criterion_refs'} & props.keys()
    assert {'checks', 'rules'} <= props.keys() and 'blocks' not in props
    defs = schema['$defs']
    # A pass states only its supporting records; every other outcome states its fact.
    assert set(defs['PassCheck']['required']) == {'criterion', 'outcome', 'evidence'}
    assert set(defs['PassCheck']['properties']) == {'criterion', 'outcome', 'evidence', 'missing'}
    assert set(defs['PassRule']['required']) == {'quotes', 'outcome', 'evidence'}
    assert set(defs['PassRule']['properties']) == {'quotes', 'outcome', 'evidence', 'missing'}
    assert set(defs['PlainCheck']['properties']) == {'criterion', 'fact', 'outcome', 'missing'}
    assert set(defs['GapCheck']['required']) == {'criterion', 'fact', 'outcome', 'missing'}
    assert set(defs['InvalidCheck']['required']) == {'criterion', 'fact', 'outcome', 'upstream'}
    assert set(defs['UnitJudgment']['required']) == {'unit', 'checks'}
    for rule in ('PlainRule', 'GapRule', 'InvalidRule'):
        assert {'quotes', 'applicability', 'outcome', 'fact'} <= set(defs[rule]['required'])


@pytest.mark.parametrize('outcomes,expected', [
    (['not_applicable'], 'not_applicable'), (['pass', 'fail'], 'fail'),
    (['fail', 'insufficient_evidence'], 'fail'),
    (['pass', 'insufficient_evidence'], 'insufficient_evidence'),
    (['contract_missing', 'input_invalid'], 'input_invalid'),
    (['contract_missing', 'pass'], 'pass'),
    (['input_invalid', 'not_applicable'], 'input_invalid'),
    (['contract_missing', 'not_applicable'], 'not_applicable'),
    (['contract_missing'], 'contract_missing'),
])
def test_aggregate_is_derived_without_overwriting_any_atomic_judgment(outcomes, expected):
    refs = ['expectation:e' + str(i) for i in range(len(outcomes))]
    args = payload_for(refs, outcomes)
    before = copy.deepcopy(args)
    row, = expanded(*args)
    assert row['outcome'] == expected
    assert [c['outcome'] for c in row['expectation_checks']] == outcomes
    assert [c['outcome'] for c in row['criterion_checks']] == outcomes
    assert row['expectation_ids'] == ['e' + str(i) for i in range(len(outcomes))]
    assert row['criterion_refs'] == refs
    # A pass carries no narrative; the program states it with its supporting record.
    assert row['observed'] == '\n'.join(dict.fromkeys('通过，依据：response' if o == 'pass' else f'synthetic fact {i}'
                                                       for i, o in enumerate(outcomes, 1)))
    assert args == before


def test_direct_obligation_uses_explicit_existing_criterion_namespace():
    row, = submit(*payload_for(['obligation:rule'], ['fail']))
    assert row['outcome'] == 'fail' and row['expectation_ids'] == []
    assert row['source_refs'] == ['obligation:rule']
    assert row['observed'] == 'synthetic fact 1'
    assert row['expected'] == 'obligation:rule：synthetic duty'
    assert row['problems'][0]['expected'] == row['expected']


@pytest.mark.parametrize('codes', [[], [''], ['invented'], ['obligation:rule'],
                                   ['expectation:e'], ['C2'], ['C1', 'C1'], ['C1', 'C2']])
def test_ambiguous_unidentified_duplicate_and_missing_checks_are_rejected(codes):
    payload, units, criteria, blocks = payload_for(['obligation:rule'])
    payload['units'][0]['checks'] = [make_check(code, 'pass', 'synthetic fact', evidence=['response']) for code in codes]
    with pytest.raises(ValueError):
        expanded(payload, units, criteria, blocks)


def test_generic_obligation_and_demand_are_checked_side_by_side_with_condition():
    entry = dict(expectation_id='e', source_refs=['t1.user'], about='synthetic status',
                 statement='report current status', condition='only when refresh was requested')
    row, = submit(*payload_for(['obligation:rule', 'expectation:e'], ['pass', 'fail']), expectations=[entry])
    assert row['outcome'] == 'fail' and row['expectation_ids'] == ['e']
    assert row['criterion_refs'] == ['obligation:rule', 'expectation:e']
    assert row['problems'][0]['source_refs'] == ['expectation:e']
    assert row['problems'][0]['expected'] == (
        'expectation:e：synthetic status：report current status（条件：only when refresh was requested）')
    assert row['expected'] == 'obligation:rule：synthetic duty\n' + row['problems'][0]['expected']


@pytest.mark.parametrize('refs,error', [
    (['obligation:rule'], '缺'), (['obligation:rule', 'expectation:e', 'expectation:x'], '多'),
    (['obligation:rule', 'expectation:e', 'expectation:e'], '判准未恰好覆盖'),
])
def test_unit_must_check_exactly_its_program_supplied_criteria(refs, error):
    row, = expanded(*payload_for(['obligation:rule', 'expectation:e']))
    row['criterion_refs'] = refs
    table = {('rule', 'step'): ['expectation:e', 'obligation:rule']}
    with pytest.raises(ValueError, match=error):
        check_criteria([row], table)
    # Order is immaterial; quoted design checks are additional, not replacement C checks.
    check_criteria([dict(row, criterion_refs=['obligation:rule', 'design:synthetic', 'expectation:e'])], table)


@pytest.mark.parametrize('source', ['trace', 'case'])
@pytest.mark.parametrize('outcome', ['pass', 'fail'])
def test_obligation_template_cannot_replace_missing_specific_criterion(source, outcome):
    with pytest.raises(ValueError, match='适用需求或设计规则'):
        submit(*payload_for(['obligation:rule'], [outcome]), source=source)


@pytest.mark.parametrize('source', ['trace', 'case'])
def test_no_demand_or_rule_is_explicit_missing_criterion_not_a_synthetic_pass(source):
    payload, units, criteria, blocks = payload_for([])
    with pytest.raises(ValueError, match='missing_criterion'):
        submit(payload, units, criteria, blocks, source=source)
    payload['units'][0]['missing_criterion'] = ['synthetic applicable rule was not supplied']
    row, = submit(payload, units, criteria, blocks, source=source)
    assert row['outcome'] == 'contract_missing'
    assert row['criterion_checks'] == row['source_refs'] == row['problems'] == []
    assert row['missing'] == ['synthetic applicable rule was not supplied']


def test_criteria_for_uses_frozen_demands_and_general_obligations_not_trace_templates():
    obs = {source: Obligation(source, AXIS, 'synthetic', 'duty', source=source)
           for source in ('agno', 'trace', 'case')}
    pairs = [(source, 'step') for source in obs]
    assert criteria_for(pairs, LINKS, obs) == {
        ('agno', 'step'): ['obligation:agno'], ('trace', 'step'): [], ('case', 'step'): []}
    links = copy.deepcopy(LINKS)
    links['step']['expectation_ids'] = ['e']
    assert criteria_for(pairs, links, obs) == {
        ('agno', 'step'): ['expectation:e', 'obligation:agno'],
        ('trace', 'step'): ['expectation:e'], ('case', 'step'): ['expectation:e']}


@pytest.mark.parametrize('ref', ['expectation:unknown', 'expectation:', 'obligation:other', 'invented'])
def test_long_form_provenance_must_resolve_to_existing_demand_or_this_obligation(ref):
    with pytest.raises(ValueError):
        submit(*payload_for([ref]))


@pytest.mark.parametrize('location,field,value', [
    ('top', 'results', []), ('unit', 'outcome', 'fail'),
    ('unit', 'criterion_checks', []), ('unit', 'source_refs', ['obligation:rule']),
    ('check', 'criterion_ref', 'obligation:rule'), ('check', 'observed', 'old shape'),
])
def test_retired_fields_are_rejected_not_silently_downgraded(location, field, value):
    payload, *_ = payload_for(['obligation:rule'])
    target = {'top': payload, 'unit': payload['units'][0], 'check': payload['units'][0]['checks'][0]}[location]
    target[field] = value
    with pytest.raises(ValueError):
        enforce_output(payload, OUTPUT, caller='synthetic-test')
