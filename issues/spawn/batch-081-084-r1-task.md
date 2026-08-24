# Argue task — issues 081, 082, 083, 084

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
Charter: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/charter-q2-is-label.md
Discovery: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/q2-is-label-discovery.md
Oracle: spec/alg/fulfilled.md 第一章, spec/alg/product-function.md §1 / §7–9, spec/alg/authority.md §8.3, spec/info-volume.md
Current exits to read yourself:
- impl/core/schema/judge.py
- impl/core/schema/table.py
- impl/core/table_view.py
- impl/core/frontend_view.py `_fulfillment_panel`
- impl/frontend/summary.html fulfillmentPill / renderFulfillmentMatrix / renderJudgeCard
Prior locks (Consensus blocks only): issues/open/issue-040.md, issue-047.md, issue-058.md, issue-060.md, issue-061.md, issue-065.md, issue-066-q2-label-honesty.md, issue-069.md, issue-077.md, issue-078.md, issue-079.md, issue-080.md

Do not adopt Architect Response blocks from other charters on 066–080 as if they were this run.

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
The user asked again, after 077–080 already said "visible-layer sibling label, write-layer other way":

> 你要开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗？
> 按 fulfilled 的定位，它是否只是 not_fulfilled 的补充，应该新增一个 judge 结果的标签，还是 fulfilled 从 3 态扩到 4 态，甚至是把它放到 ne 里面，还是别的方式。给方案。不实现。

The only sentence this run may change: 077 named the scheme 「别的方式」. If opening the cell is adding a judge-result label, this run must name the scheme that label. Selecting 「别的方式」 again is failure.

Do not re-judge cases. Do not implement fields. Do not change the frontend. Do not adopt a final Chinese public sentence. Do not announce 立住了 / 没立住 as the public wording. Do not approve opening the sibling cell this round.

Must answer separately, never weld back into one sentence:

```text
人看见的：结果上是不是多了一格字
谁写下的：是不是同一张嘴再判一次
进哪张嘴：是不是改写办成了 / 没办成 / 说不清
```

This run MUST leave a scheme sentence whose name is 「新增一个 judge 结果标签」. Another "A/B/C/D all cannot host, therefore other way" is failure.

## Permission Mode
review: append response only. Do not modify spec/**, impl/**, xlsx, canvas, or frontend.

## How to write
Do not use nested heredocs. Write each response to a temp file first, then append that file to the issue. Every response must include `### Spawn Evidence` with the spawn-id.

## Investigate before judging
Quote the protocol sections and current exits yourself. Do not treat the verifier write-up as already true.

Challenge specifically. Do not rubber-stamp four `real-problem`s with the same paragraph.

- 081 claims: the scheme name is 「新增一个 judge 结果标签」; opening the cell is that thing; stop calling it 「别的方式」. Attack: is this just renaming the B that 065 killed? After 077 already said the visible-layer scheme is a sibling label, is 081 not-actionable restatement? If 「judge 结果标签」 in this product necessarily means `status`, 081 is false. If verifier smuggled "so Judge fills a new field" or a public Chinese name, reject that part.

- 082 claims: this label is a sibling of fulfilled, not 4th state, not NE, not NF-only. Attack: the user can only see one chip today. After naming the leftover "a judge result tag", isn't the honest place the chip they already look at? Would refusing A/C/D after admitting "it's a tag" be more casuistry? Is 「办成了 × 没立住」 actually required by fulfilled.md, or only by 040?

- 083 claims: the cell is matrix same row, next to Status; not assessment.status; not the table chip. Attack: is that grid something a user actually sees, or only an internal panel? If the user asked 「用户怎么看到这个东西」, is Status-adjacent in a matrix they must open still failing that? Is pointing at `_fulfillment_panel` smuggling an implementation?

- 084 claims: "judge result label" means a word the person sees on the judge result, not a new model-written status; leave one scheme sentence; do not whole-number escalate. Attack: if we name it a judge result label, have we already chosen B and contradicted product-function.md §7.2? Should the whole issue escalate because adding a visible label is a product decision? If the scheme sentence starts with a kill-list, fail it.

## Issues
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-081.md
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-082.md
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-083.md
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-084.md

## Already Confirmed Issues
077–080 locked a visible-layer sibling label and still called the write-layer 「别的方式」. This run may rename the scheme; it may not reopen A/C/D, same-mouth write, or opening.

## Learning Context
Do not rubber-stamp. 100% same verdict with the same paragraph is suspect. Isolation-failed if you omit spawn-id. Do not implement. Do not approve opening.
