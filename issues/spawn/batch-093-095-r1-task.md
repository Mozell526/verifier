# Argue task — issues 093, 094, 095

You are the architect argue-peer. Isolated process. Do not role-play as verifier.

Read the role card prepended to this prompt. Follow council PROTOCOLS.md argue contract.

For EACH issue below, append exactly one `## Architect Response #1` to that issue file.
Each response MUST include:

### Spawn Evidence
- spawn-id: <the spawn-id from this spawn>
- pid: <your pid>

Then Investigation / Reasoning / Verdict / What I Changed.
If verdict is real-problem, also include Improvement Proposal.

Pick exactly one Verdict per issue: real-problem | reasonable-design | needs-more-info | not-actionable | escalate-to-project

Every response MUST include `### Spawn Evidence` with the spawn-id from this spawn.

## Context
Charter: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/charter-nf-reason-absolute.md
Discovery: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/nf-reason-absolute-discovery.md
Oracle: the user's pasted block in the charter; spec/alg/fulfilled.md 第一章; spec/alg/authority.md §8.3; current reason slot (impl/core/summary.py summary_from_fulfillment, impl/core/frontend_view.py display_reason, impl/frontend/summary.html 评估卡「原因」); 040 / 047 Consensus content only.
Current exits to read yourself:
- impl/core/schema/judge.py
- impl/core/schema/table.py
- impl/core/summary.py
- impl/core/frontend_view.py `_fulfillment_panel` / `_judge_panel`
- impl/frontend/summary.html fulfillmentPill / renderFulfillmentMatrix / 评估卡原因
Prior locks (Consensus content only, not nicknames): issues/open/issue-040.md, issue-047.md, issue-060.md, issue-061.md

Do not touch issue-081.md.
Do not treat 089–092 as already settling this run. This run may attack them if 「原因说明项」punches through their exclusion.

## What the user recognizes

The user said they recognize only this block, not 「第二问」:

```text
只看一件事：用户要的这件事，产品把它立成自己会做的事了没有
对象：仍是 fulfilled 那一件
      不得另立类型表
      不得为了更好答这一块，把对象切粗或切细
单位：这件事 × 产品事实
产品事实从哪来：已经裁完的能力/职责判断，及其依据资料
          不是这一次给没给到
          不是库存字段表
          不是「先分成姓名/年/天气」
不看：这一次交付；这一次承不承认 / 尽没尽力；预置类型表
不区分：没立住的技术原因
出口：立住了 / 没立住 / 说不清
```

fulfilled still exists as the current visible judgment: 这一次办成了没有. It is the contrast object, not a reason to rename this block 「第二问」.

## What this run is

Re-analyze placement of THIS block. The user's remaining doubt: it still looks like a reason-explanation item for not_fulfilled. If the scheme does not place it there, the exclusion must be absolute.

Absolute in this run: putting the block in that mouth would change at least one already-locked item (object / unit / what it ignores / 3-way exit). Taste, cleanliness, or 「因为这是第二问」 is not enough. If a mouth does not change a lock, do not exclude it; change the scheme.

Also exclude or accept with the same bar: new judge-written result label, fulfilled 3→4, put into NE, or another way. Give one scheme. Do not implement.

Must not:
- first rename this block 「第二问」 then deduce placement
- reopen the content of the block
- implement fields, change frontend, adopt public Chinese
- approve opening this round
- whole-number escalate
- deliver only a kill-list with no scheme sentence
- treat 「只在没办成时才给人看」 as identity; that is viewing time and stays escalated

Attack the verifier if the exclusion of 「原因说明项」 is only taste.
Attack the verifier if it smuggles 「第二问」 back as identity.
Attack the verifier if 「judge 结果标签」 is turned into the name of this block.
Attack the verifier if dropping 「第二问」 secretly revives NF-reason / 3→4 / NE / Judge-fills.

## Issues
- issues/open/issue-093.md — 不是 NF 原因说明项；排除必须绝对
- issues/open/issue-094.md — 3扩4 / NE / Judge再写 也必须绝对排除
- issues/open/issue-095.md — 先写方案句

Append to those three files only. Do not edit spec / impl / frontend / older issue bodies.
