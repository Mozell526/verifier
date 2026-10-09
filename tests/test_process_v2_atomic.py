"""Synthetic regressions from the independent review: atomics survive aggregation."""
import copy

import pytest

from impl.projects.llm_probe.eval_axes.adapters.process_common import _outcome
from impl.projects.llm_probe.eval_axes.adapters.process_protocol import issues_for
from impl.projects.llm_probe.judge import _slim_process_axis_for_main
from tests.support.unit_reply import set_outcome
from tests.test_process_v2_rules import case, item, submit, upstream_issue, block, rule, problem


def mixed_invalid():
    c = case(source='agno', refs=['obligation:rule'])
    upstream = upstream_issue()
    set_outcome(item(c)['rules'][0], 'input_invalid', upstream=[upstream['problem_id']])
    c['recorded_issues'] = [upstream]
    return c, upstream


def test_mixed_pass_cannot_hide_input_invalid_dependency():
    c, upstream = mixed_invalid()
    row, = submit(c)
    assert row['outcome'] == 'pass'
    assert row['upstream_issue_ids'] == [upstream['problem_id']]
    assert row['criterion_checks'][1]['upstream_issue_ids'] == [upstream['problem_id']]
    item(c)['rules'][0]['upstream'] = []
    with pytest.raises(ValueError, match='rules.\\[0\\].字段必须非空但产出为空：upstream'):
        submit(c)


def test_composition_and_main_view_keep_partly_untested_judgments():
    c, upstream = mixed_invalid()
    row, = submit(c)
    result = _outcome([row], c['obligations'], 'r', 's', {}, {}, axis_id=c['axis_id'])
    parts = result.output['assessment']['composition']
    assert parts['counts']['pass'] == 1
    assert parts['criterion_counts']['input_invalid'] == 1
    assert parts['input_invalid'][0]['upstream_issue_ids'] == [upstream['problem_id']]
    slim = _slim_process_axis_for_main({'output': result.output})['output']
    assert slim['results'][0]['checks'][0]['criterion_checks'][1]['outcome'] == 'input_invalid'
    assert slim['results'][0]['upstream_issue_ids'] == [upstream['problem_id']]


def test_local_failure_does_not_relabel_another_unresolved_problem():
    second = '金额必须是当前时点。'
    c = case(raw_blocks=[block(), block(second, path='/messages/1/content')])
    item(c)['rules'] = [rule('fail'), rule('insufficient_evidence',
        quotes=[dict(ref='request', quote=second)], missing=['缺少输入时点'])]
    c['payload']['problems'] = [problem(('U1/D1',)), problem(('U1/D2',), unresolved=True)]
    row, = submit(c)
    assert row['outcome'] == 'fail'
    issues = issues_for(c['axis_id'], [row])
    assert [p['attribution'] for p in issues] == ['local', 'unresolved']
    assert issues[1]['outcome'] == 'insufficient_evidence'
    assert len(issues[1]['attribution_axes']) == 2
    c['payload']['problems'][1]['axes'] = [c['axis_id']]
    with pytest.raises(ValueError, match='候选轴'):
        submit(c)


def test_coalesced_exercise_keeps_invalid_subcheck_in_composition():
    c, upstream = mixed_invalid()
    invalid, = submit(c)
    normal_case = case(source='agno', refs=['obligation:rule'])
    normal, = submit(normal_case)
    result = _outcome([normal, invalid], c['obligations'], 'r', 's', {}, {}, axis_id=c['axis_id'])
    row, = result.output['results']
    assert len(row['checks']) == 2
    assert row['upstream_issue_ids'] == [upstream['problem_id']]
    assert result.output['assessment']['composition']['criterion_counts']['input_invalid'] == 1


def test_one_problem_spanning_units_of_the_same_exercise_merges_instead_of_crashing():
    """Same problem id and body on two units that match one real exercise: only unit-local refs differ."""
    from impl.projects.llm_probe.process_loop.expectation_projection import coalesce

    def unit(inputs, outputs, expected):
        problem = dict(problem_id='planning_routing:p1', phenomenon='同一问题', observed='事实', attribution_axes=['planning_routing'],
                       impact='unknown', outcome='fail', expectation_ids=[], source_refs=[f'ref:{expected}'], expected=expected,
                       input_refs=inputs, output_refs=outputs)
        return dict(obligation_id='ob', link_id='L1', matched_link_id='actual', outcome='fail', expectation_ids=[], source_refs=[f'ref:{expected}'],
                    missing=[], expected=expected, observed='事实', evidence={'input': inputs, 'output': outputs},
                    upstream_issue_ids=[], problems=[problem])
    merged, = coalesce([unit(['a'], ['x'], '预期一'), unit(['b'], ['y'], '预期二')])
    problem, = merged['problems']
    assert problem['input_refs'] == ['a', 'b'] and problem['output_refs'] == ['x', 'y']
    assert problem['expected'] == '预期一\n预期二'
    changed = unit(['b'], ['y'], '预期二')
    changed['problems'][0]['phenomenon'] = '另一个现象'
    with pytest.raises(ValueError, match='正文冲突'):
        coalesce([unit(['a'], ['x'], '预期一'), changed])
