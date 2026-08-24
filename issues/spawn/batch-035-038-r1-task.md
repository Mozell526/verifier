# Argue-peer task — batch 035–038 r1

Read first:
- ~/.codex/skills/council/roles/architect.md
- ~/.codex/skills/council/PROTOCOLS.md
- issues/charter-name-principle.md
- issues/trace/name-object-coverage.md
- issues/open/issue-035.md
- issues/open/issue-036.md
- issues/open/issue-037.md
- issues/open/issue-038.md
- issues/trace/principle-discovery.md
- issues/trace/check-name-principle.md
- issues/learning.md

Do **not** review or append to issue-001.md through issue-034.md. Those already have Consensus or belong to other charters. Do not reopen 012 / 019 / 020 / 021 / 025–028 verdicts; you may cite them.

This round's charter is `issues/charter-name-principle.md`, not `issues/charter.md` and not `issues/charter-name-generalization.md`.

## Your Role
You are architect acting as an argue peer. Follow the argue protocol in ~/.codex/skills/council/PROTOCOLS.md.

## Context
Charter: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/charter-name-principle.md
Principle: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/name-object-coverage.md
New simulation (rerun this yourself): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_1a_principle_program.py
New dump (a claim under review): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_1a_principle_program.json
Old coverage script (negative control, do not treat as the candidate): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_1a_coverage_program.py
Frozen traces: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/name_scenario_runs/
Mixed pack: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/name_scenario_mixed_pack.json
Set B (read-only): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/impl/projects/client_search/draft/cases/head_set_b.json
Oracle: spec/alg/fulfilled.md, spec/alg/material-positioning.md
XLSX (read-only, outside repo): /Users/xiaozijian/Downloads/verifier-client_search-cases-20260814-185013.xlsx
Judge host (read-only): impl/projects/client_search/draft/judge.py L897 and L1504–1508

User already rejected:
- `exit_role` as too rule-based
- selling `exit_live_identity` / whole-query equality as a generalizable architecture

User asked for principle / standard / boundary with no leftover ambiguity, plus an in-memory judge debug. Name is only one problem family.

## What to challenge
- 035 claims whole-query equality is a local proxy, not a principle. Is that attribution right, or is the whole-query gate already the right object?
- 036 claims object-cover (span + residual + field type) is an unambiguous total function. Does any clause still two-read? Is "never overlay NF" a hole? Is leftover-including-的 too conservative to be a principle, or is peeling 的 the next rule table?
- 037 claims frozen scores matching live_identity is expected, and only synthetics show extra reach. Is that honest, or is object_cover just a rename? Do not treat 41/47 as a KPI.
- 038 claims the host is still L1504–1508 vs 1A, so nothing may merge into judge.py. Is escalate-to-project the right verdict, or is there a smaller in-scope action?

Reproduce:
```bash
python3 issues/trace/simulate_1a_principle_program.py
```
Compare SHA-256 of the written JSON with the issue claim. Read `decide_object_cover` yourself. Check I129 / 红莲保单 / 共展 / HB009–014 / synthetics against the principle doc.

## Permission Mode
- "review": append response only, no file modifications beyond the issue files

## Hard constraints
- Do not modify src/**, impl/projects/client_search/**, xlsx, canvas, head_set_b.json, or the old coverage script.
- Do not decide charter §4 items (去年 / 称谓 / 昊轩).
- Field name must be **Verdict** (not Judgment).
- Write each Architect Response to a temp file first, then append. Do not use nested heredocs.

## Response format
Append to each issue file:

## Architect Response #1

**Verdict**: <vocabulary>

### Spawn Evidence
- spawn-id: <from your environment / instruction>

### Investigation
<what you re-read or recomputed, including your own script rerun>

### Reasoning
<agree / tighten / refute>

### Improvement Proposal
<only if useful; this run does not implement>
