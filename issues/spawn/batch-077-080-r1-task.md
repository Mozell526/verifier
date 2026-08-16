# Argue task — issues 077, 078, 079, 080

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
Charter: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/charter-q2-scheme.md
Discovery: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/q2-scheme-discovery.md
Oracle: spec/alg/fulfilled.md 第一章, spec/alg/product-function.md §1 / §6–10, spec/alg/authority.md §8.3, spec/info-volume.md
Current exits to read yourself:
- impl/core/schema/judge.py
- impl/core/schema/table.py
- impl/core/table_view.py `_fulfillment_status`
- impl/core/frontend_view.py `_fulfillment_panel`
- impl/frontend/summary.html fulfillmentPill / fulfillmentStatus / renderFulfillmentMatrix if present
Prior locks (Consensus blocks only): issues/open/issue-047.md, issue-058.md, issue-060.md, issue-061.md, issue-062.md, issue-063.md, issue-064.md, issue-065.md, issue-066-q2-label-honesty.md, issue-069.md

Do not adopt Architect Response blocks from other charters on 066–076. Those files may contain parallel-charter writes.

Locked two-question structure (do not rewrite):

```text
第一问（已经有）
  只看一件事：这一次，用户要的事办成了没有
  单位：这一次请求 × 这一次交付
  不看：产品把这件事立住了没有
  不区分：没给到的原因
  出口：办成了 / 没办成 / 说不清

第二问（出口还没有）
  只看一件事：用户要的这件事，产品把它立成自己会做的事了没有
  对象：仍是第一问那一件
        不得另立类型表
        不得为了更好答第二问，把对象切粗或切细
  单位：这件事 × 产品事实
  产品事实从哪来：已经裁完的能力/职责判断，及其依据资料
  不看：这一次交付；这一次承不承认 / 尽没尽力；预置类型表
  出口：立住了 / 没立住 / 说不清
```

内部手柄不宣布采用为对外题面。

## What this run is
The user asked for a scheme, not another kill-list:

> 你要开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗？
> 按 fulfilled 的定位，它是否只是 not_fulfilled 的补充，应该新增一个 judge 结果的标签，还是 fulfilled 从 3 态扩到 4 态，还是放到 NE，还是别的方式。给方案。不实现。

Do not re-judge cases. Do not implement fields. Do not change the frontend. Do not adopt a final Chinese public sentence. Do not announce 立住了 / 没立住 as the public wording. Do not approve opening the sibling cell this round.

Must answer separately, never weld back into one sentence:

```text
人看见的：结果上是不是多了一格字
谁写下的：是不是同一张嘴再判一次
进哪张嘴：是不是改写办成了 / 没办成 / 说不清
```

This run MUST leave a scheme sentence. Another "A/B/C/D all cannot host, therefore no scheme" is failure.

## Permission Mode
review: append response only. Do not modify spec/**, impl/**, xlsx, canvas, or frontend.

## How to write
Do not use nested heredocs. Write each response to a temp file first, then append that file to the issue. Every response must include `### Spawn Evidence` with the spawn-id.

## Investigate before judging
Quote the protocol sections and current exits yourself. Do not treat the verifier write-up as already true.

Challenge specifically. Do not rubber-stamp four `real-problem`s with the same paragraph.

- 077 claims: the scheme is a sibling result label on the judge result the person sees; the user's sentence is true at that layer. Attack: is this just circling the B that 065 killed, under a nicer name? Is 「judge 结果标签」 in this product necessarily the `status` field, so 077 is false? After 066-q2 already said "opening a cell is a seen label", is 077 not-actionable restatement? If verifier smuggled "so B is approved" or a public Chinese name, reject that part.

- 078 claims: admitting 077 does not revive NF-only / 3-to-4 / NE. Attack: the user can only see one chip today. After calling the leftover "a judge result tag", isn't the honest place the chip they already look at? Would a sibling they must click into fail 「用户怎么看到」? Is refusing A/C/D after admitting "it's a tag" more casuistry?

- 079 claims: the cell is matrix same row, next to Status; not assessment.status; not the table chip. Attack: `_fulfillment_panel` is already the judge card — does a derived sibling still feel like Judge output, collapsing 077 back into judge-written B? Is the table chip the only place the user asked about? Did 060 already lock this, making 079 not-actionable?

- 080 claims: one scheme sentence; opening still charter §4. Attack: did verifier actually choose among A/B/C/D/other, or write another kill-list? Should 080 be escalate-to-project because choosing to add a visible tag is a product decision? If the scheme sentence implements a field, a frontend column, or "Judge should fill it", reject that part.

If verifier smuggled a frontend column, a new schema field, or a public Chinese name into the conclusion, reject that part. Scheme-locking may be done without implementing.

Issues to judge, in order:
1. /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-077.md
2. /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-078.md
3. /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-079.md
4. /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-080.md
