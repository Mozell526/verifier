# Argue-peer task — batch 025–028 r1

Read first:
- ~/.codex/skills/council/roles/architect.md
- ~/.codex/skills/council/PROTOCOLS.md
- issues/charter-name-generalization.md
- issues/open/issue-025.md
- issues/open/issue-026.md
- issues/open/issue-027.md
- issues/open/issue-028.md
- issues/trace/coverage-discovery.md
- issues/learning.md

Do **not** review or append to issue-016.md through issue-024.md. Those already have Consensus. Do not reopen 012 / 019 / 020 / 021 verdicts; you may cite them.

This round's charter is `issues/charter-name-generalization.md`, not `issues/charter.md`.

## Your Role
You are architect acting as an argue peer. Follow the argue protocol in ~/.codex/skills/council/PROTOCOLS.md.

## Context
Charter: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/charter-name-generalization.md
New simulation (rerun this yourself): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_1a_coverage_program.py
New dump (a claim under review): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_1a_coverage_program.json
Frozen traces: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/name_scenario_runs/
Mixed pack: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/name_scenario_mixed_pack.json
Set B (read-only): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/impl/projects/client_search/draft/cases/head_set_b.json
Oracle: spec/alg/fulfilled.md, spec/alg/material-positioning.md
XLSX (read-only, outside repo): /Users/xiaozijian/Downloads/verifier-client_search-cases-20260814-185013.xlsx
Judge host (read-only): impl/projects/client_search/draft/judge.py L897 and L1504–1508

User already rejected `exit_role` as too rule-based. Name is only one problem family. User asked for generalization plus an in-memory judge debug.

## What to challenge
- 025 claims `exit_role` is a name-type state machine; I248 `红莲保单` is the leak (value `红莲` ≠ query, still lifted).
- 026 claims `exit_live_identity` (whole-query live cover) matches role's 41/47 without 保单号 regex / pack-role routing, and set A flips only 王坤林.
- 027 claims 1A/4A cells pass, but inherit-NF on 共展 and HB009–014 must not be sold as “fake-name detector done” or “judge accuracy”.
- 028 claims the production source is still prompt L1504–1508 fighting 1A; do not merge any overlay into judge.py.

You must independently rerun:

```bash
python3 issues/trace/simulate_1a_coverage_program.py
```

Do not copy verifier numbers. Re-read `exit_live_identity` and `whole_query_cover`. Confirm the candidate does not read mixed-pack `role`. Confirm HB009–014 are inherit NF (no name invented from the query). Confirm 昊轩 inherit / abstain.

Do **not** rerun the 48 LLM judges. Frozen traces are the evidence. Bash is only for the overlay script.

Do not decide charter §4 (去年 / 格式外 / 昊轩). Do not implement. Do not edit judge.py, xlsx, canvas, set B, or the simulation script.

41/47 is not a KPI. Canvas / 341 accuracy are not oracle.

## Permission Mode
review: append response only, no file modifications beyond the issue files.

For each issue pick exactly one verdict from the protocol vocabulary. Investigate before judging. The simulation dump is a claim under review, not already true.

Write each Architect Response to a temp file first, then append. Do not use nested heredocs.

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
