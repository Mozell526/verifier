# Issue #064: fulfilled 不能从 3 态扩到 4 态

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 结果口 C / 三态扩四态
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户本轮点名：fulfilled 标签从 3 态扩展到 4 态。

这是最像「实现」的口：用户现在只能看见 fulfilled，加一个词，主表「状态」立刻看得见。本 issue 只钉：第四个词仍是第一问的嘴，加进去之后两问焊回一个标签。

### 第一问的嘴现在有几个词

`spec/alg/fulfilled.md` 开篇：

> 词表沿用 `spec/info-volume.md`，不新增第四态。

`spec/info-volume.md`：

> 值域完全相同，依然是 fulfilled / not_fulfilled / not_evaluable，不引入 partial 之类的新枚举。
> judge 只产出 fulfillment。
> 整体 fulfilled → 归因不追失败。
> 整体 not_fulfilled 或 not_evaluable → 归因才追。

`impl/core/schema/judge.py`：`JudgeFulfillmentAssessmentOutput.status` 仍是一条状态。

`impl/frontend/summary.html`：顶部计数、筛选、「状态」列、`fulfillmentPill()` 都只吃这三个词。新值一旦进 `status`，会同时进这四处。

所以第四态不是「旁边多一个字」。它是第一问那张嘴多吐一个词。

### 第四个词实际只能买到一格

口语上的第四态，不论叫「尽力了」「能力外」「现有功能之外」，消费者仍从 `status` 读它。它能单独说完的，只有九格里最熟的一格：没办成 × 没立住。

| 格子 | 加上第四个词之后 |
|---|---|
| 没办成 × 没立住 | 被新词吃掉。看起来解决了 |
| 没办成 × 立住了 | 仍是没办成。过严继续隐身 |
| 办成了 × 立住了 | 仍是办成了。第二问在成功案上继续隐身 |
| 办成了 × 没立住 | 没有落点。第四个词若不是 fulfilled，§8.3 正格被删；若仍是 fulfilled，第四个词没覆盖到它 |
| 说不清 × 任一 | 继续用说不清装长期缺口，013/015 已死 |

`spec/alg/product-function.md` §7.1：给 fulfilled 加第四态来表达本协议 ✗。
同文件 §6：「尽力了」只是「没办成 × 没这项功能」的读法，不是状态。
015 Consensus 路径 A、048 Consensus：第四态已死。

### 归因会被撕开

info-volume 的切口是三词：

```text
整体办成了     → 不追失败
整体没办成/说不清 → 追
```

第四个词不是办成了，就会少一个 F，该不追的被追，或者「没办成」的业务含义被改掉。
第四个词若被当成办成了，第二问又从成功案上消失。

没有一种加法能同时保住：

1. 第一问只看办成了没有；
2. 第二问在成功案和失败案上都能开口；
3. 归因仍按三态走。

### 看见层不能倒逼改词表

用户现在只能看见 fulfilled。这是 060 / 061 已经锁过的看见问题：规范格子还不在主表「状态」上。给「状态」加第四种颜色，是先改主表芯片，再假装第二问有了出口。048 写过：前端只看见 fulfilled，只能证明看见问题，不能证明词表该膨胀。

### 不是什么

- 不是批准另开一列。看见面仍交章程 §4。
- 不是把内部手柄「没立住」宣布成第四个 status。
- 不是重开 015 / 048 的对错，只把「3 扩 4」按本轮点名口再对一次现行出口。

### 可证伪

同时成立才算「3 态扩 4 态能当宿主」：

1. 新词进 `status` 之后，办成了 / 没办成 / 说不清 的含义不变；
2. 办成了 × 没立住 和 没办成 × 立住了 仍各自看得见；
3. 归因仍按原来的三态切口走。

现行出口三条都不能成立。所以 C 口不能当宿主。

## Proposed Change

Consensus 只锁：fulfilled 不能从 3 态扩到 4 态。第四个词仍是第一问的嘴。

不改 schema，不改前端，不宣布对外中文。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: c902435f16f979ab
- pid: 79074

### Investigation
自己重读：

- `spec/alg/fulfilled.md` 开篇 + §1：「词表沿用 `spec/info-volume.md`，不新增第四态。」邻协议不并进本协议三态。
- `spec/info-volume.md`：细粒度和整体值域都是 fulfilled / not_fulfilled / not_evaluable，「不引入 partial 之类的新枚举」；judge 只产 fulfillment；整体 F → 归因不追失败，整体 NF 或 NE 才追。
- `spec/alg/product-function.md` §6 / §7.1 / §8：九格对照；「给 fulfilled 加第四态」✗；「尽力了」只是「没办成 × 没这项功能」的读法，不是状态；一个枚举值会让一个标签回答两件事，并打乱归因。
- `impl/core/schema/judge.py` 94–104 / 30：评估结果只有一条 `status`。
- `impl/frontend/summary.html`：
  - 29–30 / 552–555：顶部计数只分 Fulfilled / Not Fulfilled，后者把 NE 算进去
  - 84–87：筛选只有三词
  - 107 + 377 + 426–431：主表「状态」=`fulfillmentPill(status)`，只有 ok/bad/warn 三色
  - 766–768：`renderFulfillmentMatrix` 每行只有一个 Status 单元格
- 已锁 Consensus：015-A（第四态 / partial 已死）；048（给 status / 整体判定加第四个值已死；一个新状态词只买到最熟的一格）；060（规范格子不是案件表「状态」的第四种颜色；本轮不批准打开）。

本轮不打开兄妹格，不宣布第四个词的中文名。

### Reasoning
攻击 1：「用户只能看见一枚芯片。本轮又不打开旁边那一格。拒绝第四种颜色，不就等于拒绝回答人在哪看见吗？」
看见位置和宿主不是同一题。060 Consensus 已经答过「若给人看，在哪」：矩阵同一行、Status 旁边，不是主表「状态」的第四种颜色。061 / 章程 §4 答的是「现在开不开」。本轮章程禁止把「以后若另开一格」写成批准上线，也禁止先改主表芯片假装第二问有了出口。拒绝 C，拒绝的是把第二问塞进第一问那张嘴；不是对看见位置保持沉默。位置已锁，打开仍停住。

攻击 2：「如果第四个词只是显示别名，不改 F/NF 的后端含义，是不是就能加？」
加在同一枚芯片上，别名仍是 C。`fulfillmentPill`、主表「状态」、筛选、顶部计数、矩阵 Status 读的都是同一个 `status`。新词一旦进这条嘴，观众侧的 F/NF/NE 已经被改写，哪怕 schema 枚举暂时没加第四个 literal：

- 别名吃掉一部分 NF：没办成的业务含义被改掉，过严（没办成 × 立住了）继续隐身
- 别名不吃 F：办成了 × 没立住仍无落点，成功案上第二问继续隐身
- 别名连 F 一起改：§8.3 正格从「办成了」里消失
- 归因仍按 info-volume 三词切口走。显示词和 `status` 分叉后，人按第四色筛选、归因按三态追，两边对不上

048 写过：一个新状态词留不住四件事——现有功能里没办成、现有功能里办成了、办法仍缺但这回给到了、按三态走的归因。它只买到「没办成 × 没立住」最熟的那一格。`product-function.md` §6 把「尽力了」明确降成读法，不得写回任何标签。显示别名就是把读法写回第一问的芯片。

若别名不进这枚芯片、而进旁边另一格，那已经不是 C，是 060 的派生兄妹格。本轮不得批准打开它，也不得把它当成「所以 3 扩 4 合法」。

可证伪三条不能同时成立：新词进 `status`（或进同一 pill）之后 F/NF/NE 含义不变；办成了 × 没立住 与 没办成 × 立住了 仍各自看得见；归因仍按原来的三态切口走。所以 C 口不能当宿主。第四个词仍是第一问的嘴。

不接受「先给状态加一种颜色，以后再解释第二问」。那是 048 / 060 已经禁止的看见倒逼。

### Improvement Proposal
- **Target**: 本 issue 的 Consensus 锁。不得改 `judge.py` 枚举、`summary.html` 的 pill / 筛选 / 计数、`_fulfillment_panel`。
- **Change**: 只锁：
  1. fulfilled 不能从 3 态扩到 4 态。第四个词，含「只是显示别名」，只要占主表「状态」/ `fulfillmentPill` / 同一 `status` 槽，就不能当宿主。
  2. 拒绝第四种颜色 ≠ 拒绝回答看见位置。看见位置继续引用 060：矩阵行上 Status 旁边。本轮不打开。
  3. 不得把内部手柄宣布成第四个 status。
- **Verification**: 重读 `fulfilled.md` 开篇、`info-volume.md` 值域与归因切口、`product-function.md` §7.1 / §8、`summary.html` 377 / 552–555 / 766–768、015-A / 048 / 060。确认没有新枚举、没有第四色、没有对外词。

---
## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `c902435f16f979ab`

fulfilled 不能从 3 态扩到 4 态。第四个词仍是第一问的嘴。

收下 architect 的收紧：

- 同一枚芯片上的第四种颜色，哪怕只叫「显示别名」，只要占主表「状态」/ 同一 `status` 槽，就不能当宿主。
- 拒绝第四种颜色 ≠ 拒绝回答人在哪看见。看见位置继续引用 060：矩阵同一行、Status 旁边。本轮不打开。
- 一个新状态词只买到「没办成 × 没立住」最熟的那一格；办成了 × 没立住、没办成 × 立住了、按三态走的归因都留不住。

不得把内部手柄宣布成第四个 status。本轮不改枚举，不改前端，不宣布对外中文。

闸：同 062。
