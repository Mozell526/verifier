# Issue #094: 3 扩 4、放到 NE、Judge 再写标签，排除也必须是绝对的

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 安放 / 绝对排除其它点名口
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户点名要讨论：只是 not_fulfilled 的补充、新增一个 judge 结果标签、fulfilled 从 3 态扩到 4 态、放到 NE、还是别的方式。093 专打原因说明项。本号打另外三个点名口。排除标准同章程：必须指出会改掉已锁的哪一项。

本号不叫它第二问。也不把「新增一个 judge 结果标签」当成这块东西的名字。

### 3 扩 4 会改掉什么

已锁单位：这件事 × 产品事实，不看这一次交付。
fulfilled 的 `status` 单位：这一次请求 × 这一次交付。
第四个词若写进 `JudgeFulfillmentAssessmentOutput.status` / `fulfillment_status`，嘴还是 fulfilled 的嘴，单位还是这一次交付。
已锁单位被改掉。

`fulfilled.md` 文首 + §1：词表沿用 `spec/info-volume.md`，不新增第四态。邻题不并进本协议三态。
一块东西不能既是办成了、又是没立住。四态仍逼 `status` 选一个词。已锁「两套单位」被焊回一套。

### 放到 NE 会改掉什么

已锁这块东西的说不清：还不能谈立住了没有。
fulfilled 的说不清（§2.3）：这一次办没办成，现在说不准。
两种说不清不是同一个出口。焊进同一个 `not_evaluable`，已锁出口被改掉。

`authority.md` §8.3：职责内能力缺失不能因为「功能未实现」自动降级为 not_evaluable。
「没立住」若塞进 NE，已经裁完的产品事实被改写成「这一次说不准」。已锁「产品事实不是这一次给没给到」被改掉。

040 碰撞针：查天气 = 这一次说不清 × 还不能谈立住（职责外）。两个说不清可以同时在，不能合成一个词。

### Judge 再写一个结果标签会改掉什么

「新增一个 judge 结果的标签」若是指：同一轮 Judge 再填一个 status。
已锁：产品事实来自已经裁完的能力/职责判断，不是这一次给没给到。
同一张嘴刚写完办成了，再写立没立住，会把「这一次给到了」对齐成「也立住了」。047 锁过这件事。
用户自己问过：Judge 都判定成 fulfilled 了，还会不会违逆自己？同一张嘴里，几乎一定不会。那是对齐，不是产品事实。
放进去，已锁「不看这一次交付」被改掉。

`product-function.md` §7.2：让 Judge 再填一个新标签 ✗。本号引用的是这条禁令的方向，不是把它的「这类事」偷换成已锁对象。

若「结果标签」只描述人看见时多一格字：那是安放描述，不是本号要排除的口，也不是这块东西的名字。095 再写。

### 可证伪

同时成立才算本 issue 站住：

1. 3 扩 4 / 放到 NE / Judge 再写标签，整句都不能当宿主；
2. 每一口的排除都指出改掉了已锁的哪一项；
3. 论证不得依赖「因为这是第二问」。

若某口并不改掉已锁内容，本号失败，方案必须就那口。
若只说「协议写过不准」而不指已锁内容，本号失败。

## Proposed Change

Consensus 只锁：这三个点名口都不能当宿主。排除是绝对的。

## Evidence

`fulfilled.md` §1：本协议只评办成了没有；不并进三态，也不新增第四态。
`fulfilled.md` §2.3：说不清答的是这一次办没办成，现在说不准。
`authority.md` §8.3：职责内能力缺失不强制改状态，不能自动降为 NE。
`impl/core/schema/judge.py`：`JudgeFulfillmentAssessmentOutput.status` 是模型可写的那一个词。
`impl/core/schema/table.py`：`fulfillment_status` 是主表那一个词。
`impl/frontend/summary.html`：`fulfillmentPill` 只认 fulfilled / not_fulfilled / not_evaluable。
047 Consensus：同一张嘴兼答，几乎一定对齐刚才的办成了没有。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 7c30ec2320df0b23
- pid: 2590

### Investigation

三个点名口按章程绝对标准各打一遍。不靠「第二问」，不靠「协议写过不准」单独成句。

已锁（只用内容）：

- 单位：这件事 × 产品事实，不看这一次交付
- 出口：立住了 / 没立住 / 说不清（说不清 = 还不能谈立住，须写清差在哪儿）
- 产品事实从哪来：已经裁完的能力/职责判断，不是这一次给没给到
- 040 第 4 条：办成了，不能自动排除没立住
- 040 针：查天气 = 这一次说不清 × 还不能谈立住（职责外）
- 047 Consensus：同一张嘴兼答，几乎一定对齐刚才的办成了没有

协议 / 出口原文：

- `fulfilled.md` §1 L28–L30：只评办成了没有；不并进，不新增第四态。
- `fulfilled.md` §2.3 L54–L56：说不清答的是这一次办没办成，现在说不准。
- `authority.md` §8.3 L499–L503：职责内能力缺失不强制改状态；不能因为功能未实现自动降 not_evaluable。
- `impl/core/schema/judge.py` L94–L97：`JudgeFulfillmentAssessmentOutput.status` 是模型可写的那一个词。
- `impl/core/schema/table.py` L36：`fulfillment_status` 是主表那一个词。
- `impl/frontend/summary.html` L377：`fulfillmentPill` 只认 fulfilled / not_fulfilled / not_evaluable。
- `impl/core/frontend_view.py` L77：矩阵行现在只有一个 `status`。

`product-function.md` §7.2 我读了。本号只借它「不要让判定那张嘴再填一个新标签」这个方向。不把它的「这类事」偷换成已锁对象，也不把本块改名为那份协议。

### Reasoning

三口都不能当宿主。每一口都改掉已锁的至少一项。不是口味。

**3 扩 4。** 第四个词若写进 `JudgeFulfillmentAssessmentOutput.status` / `fulfillment_status` / overall，嘴还是 fulfilled 的嘴，单位还是这一次请求 × 这一次交付。已锁单位被改掉。四态仍逼这一格选一个词：办成了 × 没立住 写不下去，040 第 4 条被改掉。芯片只认三词，只证明出口还没有，不证明该挤进去。

**放到 NE。** 这块东西的说不清是「还不能谈立住」。fulfilled 的说不清是「这一次办没办成，现在说不准」。焊进同一个 `not_evaluable`，已锁出口被改掉。查天气这一针要求两个说不清同时在，不能合成一个词。再者，没立住对应 §8.3 的职责内能力缺失；塞进 NE，是把已经裁完的产品事实改写成「这一次说不准」。已锁「产品事实不是这一次给没给到」被改掉。

**Judge 再写一个结果标签。** 若是指同一轮 Judge 再填一个 status：产品事实不再来自已经裁完的前缀，而来自刚写完办成了没有的同一张嘴。047 已经写过，这张嘴几乎一定对齐刚才那一句。那是对齐，不是产品事实。已锁「不看这一次交付」和「产品事实从哪来」被改掉。

「结果标签」若只描述人看见时多一格字：那一格并不改对象、单位、不看什么、三态出口。按本轮绝对标准，**不得**排除那一格。那不是本号要杀的口，也不是这块东西的名字。095 写安放。verifier 把这两层拆开，是对的；拆开之后，本号才站得住。

论证没有依赖「因为这是第二问」。也没有把「judge 结果标签」做成这块东西的名字。丢掉「第二问」之后，这三口仍不能当宿主；没有偷把 NF 原因栏 / 3 扩 4 / NE / Judge 再填 救回来。

### Improvement Proposal

- **Target**: `issues/open/issue-094.md` 待写 Consensus。不改 `spec/**`、`impl/**`、前端。
- **Change**: Consensus 只锁：

```text
这三个点名口都不能当宿主。排除是绝对的。

死：fulfilled 3 扩 4
    （第四个词写进 JudgeFulfillmentAssessmentOutput.status / fulfillment_status / overall）
    改掉：已锁单位（这件事 × 产品事实 → 这一次请求 × 这一次交付）；
          040 第 4 条（一个词写不下 办成了 × 没立住）

死：放到 not_evaluable
    改掉：已锁出口（这块的说不清 ≠ 这一次办没办成现在说不准）；
          产品事实不是这一次给没给到
          （§8.3 职责内能力缺失不能自动降 NE）

死：同一轮 Judge 再写一个结果标签（再填一个 status）
    改掉：产品事实从哪来 = 已经裁完的能力/职责判断，不是这一次给没给到
          （047：同一张嘴兼答，几乎一定对齐刚才的办成了没有）

「人看见时多一格字」不是本号要排除的口，也不是这块东西的名字。
不得写成「因为这是第二问」。
不得只说「协议写过不准」。
```

- **Verification**:
  1. Consensus 若收回三口之一当宿主，且指不出改掉了已锁的哪一项，本号失败。
  2. Consensus 若把「看见时多一格字」也杀掉，本号失败——那口没有改锁，方案必须就那口。
  3. Consensus 若论证靠「因为这是第二问」，本号失败。

### What I Changed

- `issues/open/issue-094.md`: 只追加本段 Architect Response #1。未改项目源码、协议、数据、其它 issue 正文。

---
## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `7c30ec2320df0b23`

接受 architect。这三个点名口都不能当宿主。排除是绝对的。

死：fulfilled 3 扩 4
    （第四个词写进 JudgeFulfillmentAssessmentOutput.status / fulfillment_status / overall）
    改掉：已锁单位（这件事 × 产品事实 → 这一次请求 × 这一次交付）；
          040 第 4 条（一个词写不下 办成了 × 没立住）

死：放到 not_evaluable
    改掉：已锁出口（这块的说不清 ≠ 这一次办没办成现在说不准）；
          产品事实不是这一次给没给到
          （§8.3 职责内能力缺失不能自动降 NE）

死：同一轮 Judge 再写一个结果标签（再填一个 status）
    改掉：产品事实从哪来 = 已经裁完的能力/职责判断，不是这一次给没给到
          （047：同一张嘴兼答，几乎一定对齐刚才的办成了没有）

「人看见时多一格字」不是本号要排除的口，也不是这块东西的名字。
不得写成「因为这是第二问」。
不得只说「协议写过不准」。

闸：同 093。
