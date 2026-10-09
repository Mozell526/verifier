"""Scripted judgments, not claims that a model understood the evidence."""
from __future__ import annotations

import copy


GAP = {'insufficient_evidence', 'contract_missing'}


def make_check(criterion, outcome, fact, missing=(), upstream=(), evidence=()):
    """One criterion result in the static shape of its outcome (see process_output.CheckResult).

    A pass carries only its supporting record ids, never a narrative.
    """
    if outcome == 'pass':
        row = {'criterion': criterion, 'outcome': outcome, 'evidence': list(evidence)}
        if missing:  # scope limits of a pass, never a narrative
            row['missing'] = list(missing)
        return row
    row = {'criterion': criterion, 'outcome': outcome, 'fact': fact}
    if outcome == 'input_invalid':
        row['upstream'] = list(upstream)
    elif outcome in GAP or missing:  # the plain branch may carry notes; the gap branch must
        row['missing'] = list(missing)
    return row


def make_rule(outcome, quotes, *, applicability='脚本规则：已核对版本与适用条件', fact='脚本事实',
              missing=(), upstream=(), evidence=()):
    """One design-rule judgment in the static shape of its outcome (see process_output.RuleJudgment).

    A passing rule keeps its verbatim quotes (they are the criterion) and its supporting record ids only.
    """
    if outcome == 'pass':
        row = {'quotes': list(quotes), 'outcome': outcome, 'evidence': list(evidence)}
        if missing:
            row['missing'] = list(missing)
        return row
    row = {'quotes': list(quotes), 'applicability': applicability, 'outcome': outcome, 'fact': fact}
    if outcome == 'input_invalid':
        row['upstream'] = list(upstream)
    elif outcome in GAP or missing:
        row['missing'] = list(missing)
    return row


def endpoint_ids(link, fallback=()):
    """Record ids at an exercise's endpoints: what a scripted pass cites as its support."""
    ids = [e['ref'] for side in ('output', 'input') for e in (link or {}).get(side, [])]
    return list(dict.fromkeys(ids)) or list(fallback)


def set_outcome(row, outcome, *, evidence=None, fact='脚本事实', applicability='脚本规则：已核对版本与适用条件', **fields):
    """Reshape a scripted check or rule in place to the static shape of ``outcome``.

    Scripted tests often build one judgment and flip its outcome; the shapes differ per outcome,
    so the flip must drop the fields the new branch does not have and add the ones it needs.
    """
    row['outcome'] = outcome
    if outcome == 'pass':
        for key in ('fact', 'applicability', 'missing', 'upstream'):
            row.pop(key, None)
        row['evidence'] = list(evidence if evidence is not None else row.get('evidence', []))
    else:
        row.pop('evidence', None)
        row.setdefault('fact', fact)
        if 'quotes' in row:
            row.setdefault('applicability', applicability)
        if outcome != 'input_invalid':
            row.pop('upstream', None)
    row.update(fields)
    return row


def unit_reply(prompt, outcome='pass', fact='事实', *, missing=None, evidence=(), axes=None, only=None,
               reason='理由', scope_note='范围', matched=None, upstream=None, extra_units=(),
               necessity=None, rules=None, missing_criterion=None, pass_evidence=None):
    """Build an AxisJudgment for the program-owned units.

    ``necessity``, ``rules`` and ``missing_criterion`` are per-unit maps. Unconfigured action
    candidates have unknown necessity and insufficient-evidence checks, regardless
    of the ordinary-unit outcome. Configure necessity explicitly for positive or
    negative action scenarios. Raw overrides remain available for rejection tests.
    ``missing=None`` supplies a scripted gap; ``missing=[]`` deliberately does not.
    ``upstream`` names the recorded upstream problems of every ``input_invalid`` check.
    ``pass_evidence`` defaults to the first readable record of the prompt's reference catalog.
    """
    if pass_evidence is None:
        pass_evidence = (prompt.get('reference_catalog') or {}).get('readable_ids', [])[:1]
    units, problems = [], []
    for uid, spec in prompt['units'].items():
        if only and not only(spec):
            continue
        action = 'action_candidate' in spec
        configured = necessity is not None and uid in necessity
        need = copy.deepcopy(necessity[uid]) if configured else None
        if need and need['state'] != 'unknown' and not need.get('missing'):
            need.pop('missing', None)  # only the unknown branch has a ``missing`` field
        unit_outcome, unit_fact = outcome, fact
        unit_missing = list(missing) if missing is not None else (
            ['脚本未配置本项运行证据'] if outcome in {'insufficient_evidence', 'contract_missing'} else [])
        if action and not configured:
            need = {'state': 'unknown', 'fact': '脚本未配置当时是否仍须行动',
                    'evidence': [], 'missing': ['有效缓存、等价路径及刷新要求的证据']}
            unit_outcome, unit_fact = 'insufficient_evidence', need['fact']
            unit_missing = list(missing) if missing is not None else need['missing'][:]
        discharged = bool(need and need['state'] == 'satisfied')
        checks = [] if discharged else [
            make_check(c, unit_outcome, unit_fact, unit_missing, upstream or (), pass_evidence)
            for c in spec['criteria']]
        rule_checks = copy.deepcopy((rules or {}).get(uid, []))
        gaps = [] if checks or rule_checks or discharged else ['没有配置适用需求或设计规则判准']
        item = {'unit': uid, 'checks': checks, 'rules': rule_checks, 'missing_criterion': list((missing_criterion or {}).get(uid, gaps)),
                'matched': (matched or {}).get(uid, '')}
        if action or configured:
            item['necessity'] = need
        units.append(item)
        breaks = [f'{uid}/{c["criterion"]}' for c in checks if c['outcome'] == 'fail']
        breaks += [f'{uid}/D{n}' for n, rule in enumerate(rule_checks, 1) if rule['outcome'] == 'fail']
        if breaks:
            problems.append({'phenomenon': f'{uid} 的问题', 'breaks': breaks,
                             'axes': axes or [prompt['dimension']],
                             'impact': 'unknown', 'evidence': list(evidence)})
    units.extend(copy.deepcopy(extra_units))
    return {'reason': reason, 'scope_note': scope_note, 'units': units, 'problems': problems}
