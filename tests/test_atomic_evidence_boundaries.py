"""F1 regressions: atomic judgments cannot borrow a unit's weaker evidence gate.

Synthetic records and real validators/submitters only; no model or network calls.
"""
import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from impl.core.tool_loop import Call, History
from impl.projects.llm_probe.business_trace.design_rules import dossier_blocks
from impl.projects.llm_probe.business_trace.providers.llmtracing_transcript import build_transcript
from impl.projects.llm_probe.business_trace.tools import EvidenceIndex
from impl.projects.llm_probe.eval_axes.adapters import process_common as common, process_output
from impl.projects.llm_probe.process_loop import evaluation as agno
from impl.projects.llm_probe.process_loop.expectation_projection import (
    criteria_for, required_units, validate_dossier_expectations,
)
from impl.projects.llm_probe.process_loop.llmtracing import TranscriptEvaluation
from tests.support.expectations import content_sha256
from tests.support.unit_reply import make_check, set_outcome, unit_reply
from tests.test_need_source_boundaries import frozen, interleaved_trace
from tests.test_process_v2_entrypoints import agno_instance, fixture, rule_reply


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('No network allowed in atomic evidence tests')

    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)


def expectation_case(provider, delivered=False):
    """Keep E fixed; vary only which actual request the model received."""
    trace = interleaved_trace()
    expected, projection = frozen(trace)
    assert expected['sha256'] == content_sha256(expected['expectations'])
    assert projection['expectations_sha256'] == expected['sha256']
    if provider == 'transcript':
        spec = common.PROCESS_SPECS['model_capability']
        spec = replace(spec, obligations=tuple(o for o in spec.obligations
                                               if o.obligation_id == 'output_faithful'))
        ev = TranscriptEvaluation(build_transcript(trace, trace.project_fields['business_trace']),
            {'model_capability': spec, 'context_memory': common.PROCESS_SPECS['context_memory']},
            None, None, expectations=expected, projection=projection, trace_id='atomic-boundary')
        target = 't1.c1.response' if delivered else 't1.c2.response'
        record = target
        units, criteria = ev.units, ev.criteria
        submit, receipts = ev._submitter, ev.post_batch_hook

        def read():
            ev.evidence.read(list(ev.evidence.records))
            receipts.post_batch(History(calls=[]), [])

        context_target = 't1.c2:input'
    else:
        ev = agno_instance('output_faithful')
        ev.expectations, ev.projection = expected, projection
        request = expected['sources'][0]['value']
        ev.dossier['records'].append(dict(id='request', kind='requests', turn='turn1',
            scope='current', fields={'content': {'status': 'available', 'value': request}}))
        if delivered:
            ev.dossier['records'][0]['fields']['exact_request']['value']['messages'][-1]['content'] = request
        ev.index = EvidenceIndex(ev.dossier)
        ev.receipts = agno.EvaluationReceipts(ev.index,
            {'eval_model_capability', 'eval_context_memory'}, agno.result_refs)
        context_obligations = {o.obligation_id: o for o in common.PROCESS_SPECS['context_memory'].obligations
                               if o.obligation_id in {'input_assembled', 'delivered_intact'}}
        context_target = 'context_memory:call'
        context_links = {context_target: dict(link_id=context_target, link_type='context_memory',
            turn='turn1', input=[{'ref': 'request', 'field': 'content'}],
            output=[{'ref': 'call', 'field': 'exact_request'}], facts={},
            obligation_ids=['input_assembled'])}
        ev.cases['context_memory'] = agno.AxisCase('context_memory', context_obligations,
            context_links, {}, [], {}, {}, {}, {}, {})
        for axis, case in ev.cases.items():
            for link in required_units(axis, expected, projection):
                case.links[link['link_id']] = link
            case.pending = [(ob, ident) for ident, link in case.links.items() for ob in case.obligations
                            if ob in link.get('obligation_ids', case.obligations)]
            case.criteria = criteria_for(case.pending, case.links, case.obligations)
            case.units, case.short_criteria = process_output.build_units(case.pending, case.criteria, case.links)
            case.sources = dossier_blocks(ev.dossier, list(case.links.values()), axis)
        target = 'model_capability:call'
        record = 'call'
        units = {axis: case.units for axis, case in ev.cases.items()}
        criteria = {axis: case.short_criteria for axis, case in ev.cases.items()}
        submit, receipts = ev._make_submit, ev.receipts

        def read():
            ev.index.collect(['request', 'call', 'answer'])
            receipts.post_batch(History(calls=[]), [])

    return SimpleNamespace(ev=ev, units=units, criteria=criteria, submit=submit, record=record,
                           receipts=receipts, read=read, target=target, context_target=context_target)


def expectation_reply(case, expectation_outcome='pass', generic_outcome='insufficient_evidence', upstream=()):
    axis = 'model_capability'
    answer = unit_reply({'units': case.units[axis], 'dimension': axis}, 'insufficient_evidence')
    candidate, = [u for u in answer['units'] if 'candidates' in case.units[axis][u['unit']]]
    candidate['matched'] = case.target
    for check in candidate['checks']:
        expectation = case.criteria[axis][check['criterion']] == 'expectation:E1'
        outcome = expectation_outcome if expectation else generic_outcome
        code = check['criterion']
        check.clear()
        check.update(make_check(code, outcome, 'Synthetic atomic boundary judgment',
                                ['Separate generic obligation unresolved'] if outcome == 'insufficient_evidence' else [], upstream,
                                [case.record]))
        if outcome == 'fail':
            answer['problems'].append(dict(phenomenon='Requirement not fulfilled',
                breaks=[candidate['unit'] + '/' + check['criterion']], axes=[axis], impact='unknown'))
    return answer, candidate


def expected_result(case):
    result, = [r for r in case.ev.submitted['model_capability'] if r['expectation_ids'] == ['E1']]
    assert result['expectations_sha256'] == content_sha256(case.ev.expectations['expectations'])
    return result


@pytest.mark.parametrize('provider', ['agno', 'transcript'])
def test_mixed_pass_and_insufficient_requires_runtime_receipts(provider):
    ev, units, blocks, submit, read = fixture(provider, 'output_faithful')
    answer = rule_reply(units, blocks, 'insufficient_evidence')
    for unit in answer['units']:
        unit['rules'][0]['missing'] = ['Separate design applicability unresolved']
        for check in unit['checks']:
            set_outcome(check, 'pass', evidence=[unit['rules'][0]['quotes'][0]['ref']])
    original = copy.deepcopy(answer)
    read(sorted({b['ref'] for b in blocks}))  # cited rule texts read; runtime endpoints still unread
    rejected = submit(**answer)
    assert rejected['accepted'] is False, rejected
    assert '必要端点没有此前批次完整正文回执' in rejected['error']
    assert 'model_capability' not in ev.submitted

    # Reading without completing the batch still does not grant a receipt.
    if provider == 'agno':
        ev.index.collect(['call', 'answer'])
    else:
        ev.evidence.read(list(ev.evidence.records))
    rejected = submit(**answer)
    assert rejected['accepted'] is False, rejected
    assert '此前批次完整正文回执' in rejected['error']
    read()
    accepted = submit(**answer)
    assert accepted['accepted'] is True, accepted
    assert answer == original  # No dropping/relabeling the difficult atomic check.
    for row in ev.submitted['model_capability']:
        assert row['outcome'] == 'insufficient_evidence'
        assert [c['outcome'] for c in row['criterion_checks']] == ['pass', 'insufficient_evidence']
        assert row['evidence']['input'] and row['evidence']['output']


@pytest.mark.parametrize('provider', ['agno', 'transcript'])
@pytest.mark.parametrize('delivered', [False, True], ids=['missing-original', 'actual-original'])
def test_expectation_pass_with_generic_insufficient_requires_actual_input(provider, delivered):
    case = expectation_case(provider, delivered)
    answer, _ = expectation_reply(case)
    case.read()
    receipt = case.submit('model_capability')(**answer)
    assert receipt['accepted'] is delivered, receipt
    if not delivered:
        message = '出处未证实进入本次输入' if provider == 'transcript' else '期望原文未证实进入本次模型输入'
        assert message in receipt['error']
        assert 'model_capability' not in case.ev.submitted
    else:
        row = expected_result(case)
        assert row['outcome'] == 'insufficient_evidence'
        assert [c['outcome'] for c in row['criterion_checks']] == ['pass', 'insufficient_evidence']
        assert row['expectation_checks'][0]['outcome'] == 'pass'
        assert row['matched_link_id'] == case.target


@pytest.mark.parametrize('provider', ['agno', 'transcript'])
def test_input_invalid_expectation_accepts_real_prior_context_receipt(provider):
    case = expectation_case(provider)
    case.read()
    axis = 'context_memory'
    upstream = unit_reply({'units': case.units[axis], 'dimension': axis}, 'insufficient_evidence')
    unit, = [u for u in upstream['units'] if
             case.units[axis][u['unit']]['obligation_id'] == 'input_assembled' and
             case.units[axis][u['unit']]['link_id'] == case.context_target]
    for check in unit['checks']:
        check.update(outcome='fail', fact='Actual assembled input omitted the outer request', missing=[])
    upstream['problems'] = [dict(phenomenon='Original request not delivered',
        breaks=[unit['unit'] + '/' + c['criterion'] for c in unit['checks']], axes=[axis], impact='unknown')]
    receipt = case.submit(axis)(**upstream)
    assert receipt['accepted'] is True, receipt
    issue, = receipt['issues']
    assert issue['attribution'] == 'local' and issue['outcome'] == 'fail'
    assert issue['input_refs'] and issue['output_refs']
    assert issue['units'][0]['link_id'] == case.context_target

    answer, candidate = expectation_reply(case, 'input_invalid', 'pass', upstream=[issue['problem_id']])
    # Even a real accepted submission is invisible until the batch receipt exists.
    rejected = case.submit('model_capability')(**answer)
    assert rejected['accepted'] is False, rejected
    assert '不是已记录的问题 id' in rejected['error']
    assert 'model_capability' not in case.ev.submitted
    call = Call(id=0, tool='eval_context_memory', args=upstream, batch=1, result=receipt)
    case.receipts.post_batch(History(calls=[call]), [call])
    assert case.receipts.issues == receipt['issues']
    accepted = case.submit('model_capability')(**answer)
    assert accepted['accepted'] is True, accepted
    row = expected_result(case)
    assert row['outcome'] == 'pass'
    assert [c['outcome'] for c in row['criterion_checks']] == ['input_invalid', 'pass']
    assert row['expectation_checks'][0]['outcome'] == 'input_invalid'
    assert row['criterion_checks'][0]['upstream_issue_ids'] == [issue['problem_id']]
    assert row['upstream_issue_ids'] == [issue['problem_id']]
    assert row['matched_link_id'] == case.target


@pytest.mark.parametrize('outcome', ['pass', 'fail'])
def test_batch_dossier_validator_checks_each_decisive_expectation(outcome):
    case = expectation_case('agno')
    case.read()
    answer, _ = expectation_reply(case, outcome)
    axis = case.ev.cases['model_capability']
    # Batch consumers invoke this boundary directly, not through _make_submit.
    rows = process_output.validate_submission(answer, axis.units, axis.short_criteria,
        axis.links, case.receipts.backed, axis_id=axis.axis_id, obligations=axis.obligations,
        expectations=case.ev.expectations,
        required=required_units(axis.axis_id, case.ev.expectations, case.ev.projection), sources=axis.sources)
    row, = [r for r in rows if r['expectation_ids']]
    assert row['outcome'] == ('insufficient_evidence' if outcome == 'pass' else 'fail')
    assert [c['outcome'] for c in row['criterion_checks']] == [outcome, 'insufficient_evidence']
    with pytest.raises(ValueError, match='期望原文未证实进入本次模型输入'):
        validate_dossier_expectations(rows, axis.obligations, case.ev.expectations, axis.links, case.ev.dossier)

    # Same E and judgments now have actual source content, not just a matching ref.
    delivered = copy.deepcopy(case.ev.dossier)
    delivered['records'][0]['fields']['exact_request']['value']['messages'][-1]['content'] = case.ev.expectations['sources'][0]['value']
    validate_dossier_expectations(rows, axis.obligations, case.ev.expectations, axis.links, delivered)
