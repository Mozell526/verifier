# Argue task — issues 089, 090, 091, 092


## Isolation note
batch-089-092-r1 (spawn-id `44e93555a7a3fdcb`) died before writing. isolation_valid=false. Do not continue that spawn. This is a fresh r2. You must append `## Architect Response #1` to each of issue-089.md, issue-090.md, issue-091.md, issue-092.md.

Issues now have an Evidence appendix with verbatim protocol / exit quotes. Re-read the cited files yourself. Do not rubber-stamp the verifier.

You are the architect argue-peer. Isolated process. Do not role-play as verifier.

Read the role card prepended to this prompt. Follow council PROTOCOLS.md argue contract.

For EACH issue below, append exactly one `## Architect Response #1` to that issue file.
Each response MUST include:

### Spawn Evidence
- spawn-id: <the spawn-id from this spawn>
- pid: <your pid>

Then Investigation / Reasoning / Verdict / What I Changed.

Pick exactly one Verdict per issue: real-problem | reasonable-design | needs-more-info | not-actionable | escalate-to-project

Every response MUST include `### Spawn Evidence` with the spawn-id from this spawn.

## Context
Charter: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/charter-recognized-exit.md
Discovery: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/recognized-exit-discovery.md
Oracle: the user's pasted block in the charter; spec/alg/fulfilled.md 第一章; spec/alg/product-function.md §1 / §7–9; spec/alg/authority.md §8.3; spec/info-volume.md
Current exits to read yourself:
- impl/core/schema/judge.py
- impl/core/schema/table.py
- impl/core/table_view.py
- impl/core/frontend_view.py `_fulfillment_panel`
- impl/frontend/summary.html fulfillmentPill / renderFulfillmentMatrix / renderJudgeCard
Prior locks (Consensus content only, not nicknames): issues/open/issue-040.md, issue-047.md, issue-058.md, issue-060.md, issue-061.md

Do not touch issue-081.md (owned by charter-judge-agent-t4).
Do not treat issue-082.md / issue-083.md / issue-084.md as this run.
Do not adopt 085–088 scheme sentences as if they already settled this run. Their subject was 「第二问」; this run may attack that subject.

## What the user recognizes

The user said they recognize only this block, not 「第二问」:

```text
只看一件事：用户要的这件事，产品把它立成自己会做的事了没有
对象：仍是第一问那一件
      不得另立类型表
      不得为了更好答第二问，把对象切粗或切细
单位：这件事 × 产品事实
产品事实从哪来：已经裁完的能力/职责判断，及其依据资料
          不是这一次给没给到
          不是库存字段表
          不是「先分成姓名/年/天气」
不看：这一次交付；这一次承不承认 / 尽没尽力；预置类型表
不区分：没立住的技术原因
出口：立住了 / 没立住 / 说不清
```

「不得为了更好答第二问」in this block is a ban on cutting the object. It is not a name.

fulfilled still exists as the current visible judgment: 这一次办成了没有. It is the contrast object, not a reason to rename this block 「第二问」.

## What this run is

Re-analyze placement of THIS block. According to fulfilled's positioning: is it only a not_fulfilled supplement, a new judge-result label, fulfilled 3→4, put into NE, or another way? Give one scheme. Do not implement.

Must not:
- first rename this block 「第二问」 then deduce placement
- reopen the content of the block (object / unit / what it ignores / exit handles)
- implement fields, change frontend, adopt public Chinese
- approve opening this round
- whole-number escalate
- deliver only a kill-list with no scheme sentence

Attack the verifier if it smuggles 「第二问」 back as identity.
Attack the verifier if it turns 「judge 结果标签」 into the name of this block rather than a placement description.
Attack the verifier if dropping 「第二问」 secretly revives NF-only / 3→4 / NE / Judge-fills.

## Permission Mode
review: append response only. Do not modify spec/**, impl/**, xlsx, canvas, or frontend.
