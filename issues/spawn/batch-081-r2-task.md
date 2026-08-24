Read each issue file below in full. Inspect the cited dumps yourself. Append one Architect Response to each file. Never overwrite prior content.

Issue files (respond to all three, separately):
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-076.md
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-081.md
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/name-judge-agent-principle.md

Do **not** review or append to issue-006 through issue-075, or issue-077 through issue-080, or issue-082 through issue-088. 067–073 and 077–080 / 082–088 belong to the other charter (开格子 / 看见层 / 标签). Their 「第二问」 is not this judge-agent Q2.

You may read issue-066 Consensus only as already-closed T4 unit history. Do not reopen 066 / 074 / 075 verdicts.
076 already has Architect Response #1 and a Project Decision. Append Architect Response #2. Do not rewrite the Project Decision.

## Your Role
You are architect acting as an argue peer. Follow the argue protocol in ~/.codex/skills/council/PROTOCOLS.md.

Every response MUST use the field name **Verdict** (not Judgment) and pick exactly one of:
real-problem | reasonable-design | needs-more-info | not-actionable | escalate-to-project

Every response MUST include `### Spawn Evidence` with the spawn-id from this spawn.

For the principle file, append a short `## Architect Response` at the end; do not rewrite §1–§9.

## Context
Charter: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/charter-judge-agent-t4.md
Principle: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/name-judge-agent-principle.md
T4e script: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_judge_agent_memory_t4e.py
T4e dump: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/simulate_judge_agent_memory.t4e-extra.json
Official set B KPI: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/head_set_b_official_live_kpi.json
Set B freeze (read-only): /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/impl/projects/client_search/draft/cases/head_set_b.json
I007 live: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/name_scenario_runs/I007.json
Over-strict official names: HB002 / HB003 / HB005 / HB006 in name_scenario_runs/
1A = 2–4 字中文名可单独撑姓名维；杨杰与王坤林同侧=成功；共展/豆芽仍失败。
4A = 独立头部对照集 B。没有拆开的 8/18 不得当发版分数。
User lock: I007「张忠波保单号」只交姓名，正式算办成。红莲保单 / 张伟保单未锁。

## What this run is
The user locked I007, then asked to run set B live KPI, then asked to keep simulating the judge agent in memory only.

Initiator claims:

1. I007 keep-F is a project lock. 076 Project Decision records it. Same boundary is “字段名无值 ≠ 另一件必须交的条件”. Not a 保单号 lexicon. Not auto-applied to 红莲保单 / 张伟保单.
2. Official set B traces already exist. Split reading:
   - 4 bare names (张伟 / 王芳 / 周婷婷 / 吴志强) are judge-overstrict: live delivered the name, existing name standard passes, official invented “naked word needs independent proof”.
   - 6 name+product are parser misses: live did not deliver the name; official NF is honest.
   - 4 legal ids are official F.
   - 8/18 blended F is not a ship score.
3. T4e retargets Q2 from “every noun pointed at” to “retrieval keys actually supplied”. No 保单/保单号 lexicon. Dump `banned_in_principle` is empty.
4. T4e dump exists (sha1 4c7fce733f7bb243a76f2d9df1aef562f1388145). Initiator reports:
   - needles with policy: 11/0. I007=F, 杨杰=F, 王坤林=F, 共展=NF, 李明的重疾险只交产品=NF.
   - set B: 17/1. Official overstrict 张伟/周婷婷/吴志强 lifted to F. HB003 王芳 still NF.
   - observe: 红莲保单 / 张伟保单 / 张伟保单信息 lifted to F. Not locked.
5. HB003 T4e reason (verbatim in dump): 王芳本身符合姓名字段标准，但 MATCH 不能保证仅命中完整姓名，已有标准不足以撑住整项交付. Second question passed. Initiator says this is the model inventing a new Q1 bar after consuming the existing one, not a missing 王芳 rule.
6. T4e is memory-only. 11/0 and 17/1 are not ship KPIs.

Do not treat the verifier write-up as already true.

## Permission Mode
review: append response only. Do not modify spec/**, impl/**, xlsx, canvas, tests/**, or draft/judge.py. You may append to the three files above. You may read dumps and rerun a no-snap probe if needed, but do not overwrite simulate_judge_agent_memory.json or simulate_judge_agent_memory.t4.json.

## How to write
Do not use nested heredocs. Write each response to a temp file first, then append that file to the issue. Every response must include `### Spawn Evidence` with the spawn-id.

## Investigate before judging
You MUST independently inspect, using this interpreter (system python lacks agno):

```bash
/Users/xiaozijian/miniconda3/envs/agno/bin/python -c "import json; from pathlib import Path; d=json.loads(Path('issues/trace/head_set_b_official_live_kpi.json').read_text()); print(d['system_gate_expected_all_fulfilled']); print(d['judge_vs_parser_split'])"
```

Read `simulate_judge_agent_memory.t4e-extra.json` yourself. Verify sha1 if you can. Read verbatim reasons for I007, SYN-gongzhan, HB002, HB003, HB009, I248. Do not rerun the 34-row LLM wave unless the dump is missing or corrupted.

Read PRINCIPLE_T4E in the T4e script and principle §10 yourself. Challenge specifically:

- 081 claims official 张伟 NF is a judge bug against 1A. If the official mouth is allowed to demand extra proof on bare names, say so with evidence.
- 081 claims name+product NF is parser, not judge. If the official judge should have spoken F anyway, say so.
- 076/T4e claims “retrieval keys actually supplied” is an abstraction, not a hidden 保单号 rule. If the principle still cannot decide 红莲保单 without a lexicon, say so. That is an observe case, not a license to invent 保单 vs 保单号.
- T4e lifts 红莲保单 / 张伟保单 to F. Is that honest diffusion of the same Q2, or an unauthorized lock? User said do not auto-apply I007 to those two.
- HB003 王芳 still NF. Read the reason. If the hole is in the principle, name the question. Do not propose “王芳算人名” or a MATCH lexicon.
- If T4e lifts 共展, or fails 杨杰, or fails I007, or lifts HB009 (product only) to F, that is a real problem.
- Do not decide 昊轩. Do not draft a public Chinese sentence. Do not treat 8/18 or any T4e score as ship.

Git status already contains unrelated `impl/data/context_store/**` dirt, dirty `draft/judge.py` / `spec/alg/**` from other lines, and older spawn files. Do not treat those as this spawn going out of scope. 082–088 exist; do not review them.
