# Argue-peer task — batch 019–021 r1

Read first:
- ~/.codex/skills/council/roles/architect.md
- ~/.codex/skills/council/PROTOCOLS.md
- issues/charter.md
- issues/open/issue-019.md
- issues/open/issue-020.md
- issues/open/issue-021.md

Do **not** review or append to issue-013.md / 014.md / 015.md / 016.md / 017.md / 018.md. 016–018 already have Consensus. User parked 去年 / 格式外 / 称谓. User only authorized 1A / 4A.

## Your Role
You are architect acting as an argue peer. Follow the argue protocol in ~/.codex/skills/council/PROTOCOLS.md.

## Context
Charter: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/charter.md
Mixed pack: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/name_scenario_mixed_pack.json
Frozen traces: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/name_scenario_runs/
Simulation script (rerun this yourself): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_1a_mixed_program.py
Simulation dump: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_1a_mixed_program.json
Set B (read-only): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/impl/projects/client_search/draft/cases/head_set_b.json
Learning: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/learning.md
Decisions: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/decisions.md
Oracle: spec/alg/fulfilled.md, spec/alg/material-positioning.md
XLSX (read-only, outside repo): /Users/xiaozijian/Downloads/verifier-client_search-cases-20260814-185013.xlsx

Already confirmed: 006–012 and 016–018 Consensus = real-problem. Do not re-open their verdicts.

## What to challenge
User asked: run both normal and bad name-scenario cases through the current judge, then debug the judge in memory to see which handling balances long-tail overstrictness vs false lifts.

Oracle is 1A+4A policy + dual-gate (set A defect family must not regress AND set B / mixed-pack head F must not drop). Canvas / 341 accuracy are not oracle.

- 019 claims set B name+product six rows drop the person name at live parse, so no judge overlay may mark them fulfilled.
- 020 claims the current draft judge still flip-flops on the same `searchClientName MATCH` shape; set B true names are 7F/5NF; 匡西永 and 王坤林 flipped relative to the xlsx.
- 021 claims four in-memory exits: wide fails the fake-name gate; surname false-kills name+policy; role is 41/47 with all 6 misses = the live drops in 019; role must not be merged into judge.py.

You must independently rerun:

```bash
python3 issues/trace/simulate_1a_mixed_program.py
```

Do not copy verifier numbers. Re-read `exit_wide` / `exit_surname` / `exit_role`. Confirm parked queries and `undecided_given_name` (昊轩) abstain. Confirm name+product overlays do not invent a name condition from the query text.

Do **not** rerun the 48 LLM judges. Frozen traces in `issues/trace/name_scenario_runs/` are the evidence. Bash is only for the overlay script.

Do not invent a shippable fourth overlay. Do not decide charter §4.3 (昊轩). The fresh judge now says 昊轩 = fulfilled and the xlsx says not_fulfilled; that contradiction is data, not a policy decision. Do not implement. Do not edit judge.py, xlsx, canvas, set B, or the simulation script.

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
