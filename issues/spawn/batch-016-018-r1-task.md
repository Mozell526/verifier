Read each issue file below in full, inspect the cited specs, xlsx, set B, and simulation script yourself, and append one Architect Response to each file. Never overwrite prior content.

Issue files (respond to all three, separately):
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-016.md
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-017.md
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-018.md

Do **not** review or append to issue-013.md / 014.md / 015.md. Those belong to the archived charter `issues/charter-unsupported-label.md`. User parked switches 2 and 3.

## Your Role
You are architect acting as an argue peer. Follow the argue protocol in ~/.codex/skills/council/PROTOCOLS.md.

## Context
Charter: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/charter.md
Discovery: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate-1a-discovery.md
Simulation script (rerun this yourself): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_1a_name_program.py
Simulation dump: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_1a_name_program.json
Set B (read-only): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/impl/projects/client_search/draft/cases/head_set_b.json
Learning: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/learning.md
Decisions: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/decisions.md
Oracle: spec/alg/fulfilled.md, spec/alg/material-positioning.md
XLSX (read-only, outside repo): /Users/xiaozijian/Downloads/verifier-client_search-cases-20260814-185013.xlsx

Already confirmed: 006–012 Consensus = real-problem. Do not re-open their verdicts.

## What to challenge
User asked: simulate the 1A judgment change in memory and see if it actually works.
Oracle is 1A policy + dual-gate (set A defect family must not regress; set B head F must not drop). Canvas / 341 accuracy are not oracle.

- 016 claims 1A-wide lifts 共展/豆芽/见光/傻生 back to F and fails the set A gate.
- 017 claims 1A-surname+catalog can keep 王坤林 F ∧ 共展 NF, but still false-hits 保单号 / 居家潜客 / 家办客户.
- 018 claims set B 18/18 is a program exit, not an LLM judge eval, so it cannot certify the change.

You must independently rerun:

```bash
python3 issues/trace/simulate_1a_name_program.py
```

Do not copy verifier numbers. Re-read the script exits (`exit_wide` / `exit_surname`) and the set B branch. Confirm parked 10 rows are untouched.

Do not invent a shippable third overlay. Do not decide charter §4.3 (昊轩). Do not implement. Do not edit judge.py, xlsx, canvas, set B, or the simulation script.

## Permission Mode
review: append response only, no file modifications beyond the issue files.

For each issue pick exactly one verdict from the protocol vocabulary. Investigate before judging. The simulation dump is a claim under review, not already true.

Write each Architect Response to a temp file first, then append. Do not use nested heredocs (unmatched backticks broke a previous peer append).

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
