# Issue #091: 「judge 结果标签」只能描述安放，不能给这块东西改名

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 名字 / 安放 拆开
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户点名的四个口里，有一个是「新增一个 judge 结果的标签」。085–088 把这四个字写成方案名，主语却是「开第二问自己的格子」。

这块东西自己是什么：用户要的这件事，产品把它立成自己会做的事了没有。单位是产品事实。计算是读已经裁完的能力/职责前缀（058）。它不是判定对这一次交付再写一个词。

人现在看见的 judge 结果字，确实只有 fulfilled 那一格：

- `JudgeFulfillmentAssessmentOutput.status` 是模型可写评估字段里唯一的状态字
- 主表芯片是 `fulfillment_status`
- 矩阵行上 Status 旁边没有另一格

若这块东西的出口以后出现在人正在看的评估结果上，人会多看见一格字。那一格字，按看见层的叫法，可以叫做一个结果标签。

但那是安放，不是命名。

```text
这块东西是什么：这件事 × 产品事实 的出口
它出现在哪：若打开，人正在看的评估结果上会多一格字
那一格字叫什么：可以叫结果标签
谁写下的：不是同一张嘴再判一次
```

把「新增一个 judge 结果标签」写成这块东西的名字，会把安放说成身份。下一句就会滑成「所以让 Judge 再填」，或者滑成「所以它是 fulfilled 的兄妹问」。两句用户都不认。

`product-function.md` §7.2 / §8 杀的是「让 Judge 再填一个新标签」。主语是 Judge 填，不是人看见。`JudgeResult.summary` 已经证明：评估卡上可以有派生字，不必是模型新写的 `status`。

### 可证伪

同时成立才算本 issue 站住：

1. 「新增一个 judge 结果标签」不能当这块东西的名字；
2. 若只描述「人看见时会多一格字」，这一截可以留下；
3. 留下这一截，不得焊回「所以 Judge 再填」，也不得焊回「所以它叫第二问」。

若 Consensus 写成「方案名就是这块东西叫 judge 结果标签」，本 issue 失败。
若 Consensus 写成「所以看见层也不能叫标签，因此没有方案」，本 issue 失败。

## Proposed Change

Consensus 只锁：这块东西不改名为 judge 结果标签。那四个字最多描述安放。

## Evidence（本轮对照，不是新主张）

`product-function.md` §7.2 / §8 杀的主语是「让 Judge 再填一个新标签」，不是「人看见时会多一格字」。

`impl/core/schema/judge.py` `JudgeResult.summary` 注释原文：

> summary 是基于 fulfillment_assessments 派生的展示摘要
> 由 judge 阶段统一产出，下游 table_view/check/前端直接复用

评估卡上已经可以有派生字，不必是模型新写的 `status`。

047 / 058：这块东西的计算是读已经裁完的前缀，不是再开一张嘴。
把「新增一个 judge 结果标签」写成这块东西的名字，会把安放说成身份，下一句就会滑成「所以让 Judge 再填」或「所以它叫第二问」。两句用户本轮都不认。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 44e93555a7a3fdcb
- pid: 79817

### Investigation

自己拆了「judge 结果标签」的两层，并核对现行看见层：

- 用户点名的四个口里，有一个是「应该新增一个 judge 结果的标签」。这是安放选项，不是命名仪式
- 085-088 Consensus 把这四个字写成方案名，主语却是「开第二问自己的格子 / 它是 fulfilled 的兄妹标签」
- 这块东西自己是什么：040 / 用户贴出的那一块 = 这件事 × 产品事实的出口；计算是 058 读已经裁完的前缀
- `spec/alg/product-function.md` §7.2 L171、§8 L193-L198：杀掉的是「让 Judge 再填一个新标签」，主语是 Judge 填，不是人看见
- `impl/core/schema/judge.py` L94-L103：`JudgeFulfillmentAssessmentOutput` 模型可写评估字段里唯一的状态字是 `status`
- 同文件 L73-L76：`JudgeResult.summary` 已是基于 fulfillment_assessments 派生的展示摘要，证明评估卡上可以有派生字，不必是模型新写的 `status`
- `impl/core/schema/table.py` L36：主表只有 `fulfillment_status`
- `impl/core/frontend_view.py` L71-L81：矩阵行上 Status 旁边没有另一格
- `impl/frontend/summary.html` L377 `fulfillmentPill` 只认三词；L766-L770 `renderFulfillmentMatrix` 列是 Expectation / Expected / Capabilities / Status / Blocking；L778-L784 `renderJudgeCard` 看见的评估字就是 fulfilled

未把「看见层可以叫标签」焊回「所以 Judge 再填」，也未焊回「所以它叫第二问」。

### Reasoning

本号必须把名字和安放切开。用户问的是「放在哪个位置」，四个口里有一个用了「judge 结果的标签」来描述一种安放。085-088 把描述升级成了这块东西的名字，下一句就滑成兄妹问 / 让 Judge 再填。两句用户都不认。

1. **这块东西不是「再判一次交付」。** 单位是产品事实。计算是读已经裁完的能力/职责前缀（058）。047 已经写过：同一张嘴兼答，几乎一定对齐刚才的办成了没有。那是对齐，不是产品事实。所以它不是判定对这一次交付再写一个词。

2. **人现在看见的 judge 结果字，确实只有 fulfilled 那一格。** 模型可写的状态字只有 `status`。主表芯片是 `fulfillment_status`。矩阵 Status 旁边没有另一格。这只证明这块东西的出口还没有自己的看见格，不证明它的名字叫「judge 结果标签」。

3. **若以后出现在人正在看的评估结果上，人会多看见一格字。** 按看见层的叫法，那一格字可以叫做一个结果标签。这是安放描述：出口落在评估结果上、并且单独占一格。`JudgeResult.summary` 已经证明派生字可以出现在评估卡上，而不进入 `JudgeFulfillmentAssessmentOutput.status`。

4. **把安放说成身份，会立刻滑到用户不认的两句。** 「方案名就是这块东西叫 judge 结果标签」→「所以让 Judge 再填」或「所以它是 fulfilled 的兄妹问」。`product-function.md` §7.2 / §8 杀的是前一句的填法。用户本轮杀的是后一句的外号。两句都不能从「看见时多一格字」推出来。

5. **反过来也不能杀看见层这个叫法。** 若写成「所以看见层也不能叫标签，因此没有方案」，本号失败。用户点名的那个口还可以留下一截：只描述安放，不给这块东西改名。

不整号 escalate：名字和安放能在本号拆开。对外中文、打开与否仍停。

### Improvement Proposal

**Problem**: 「新增一个 judge 结果标签」被写成这块东西的名字后，安放会滑成 Judge 再填，或滑成第二问。

**Proposed Change**: Consensus 只锁「那四个字最多描述安放」。不改 schema，不宣布对外中文。

**Design**:

    这块东西是什么：这件事 × 产品事实 的出口
    它出现在哪：若打开，人正在看的评估结果上会多一格字
    那一格字叫什么：可以叫结果标签
    谁写下的：不是同一张嘴再判一次

    「新增一个 judge 结果标签」不能当这块东西的名字。
    留下的只是看见层描述：人看见时会多一格字。

    不得焊回：
      所以 Judge 再填一个 status
      所以它叫第二问 / 兄妹问
      方案名就是这块东西叫 judge 结果标签
      看见层也不能叫标签，因此没有方案

**Implementation Steps**:
1. Consensus 采用上面切开。085-088 把方案名写成「新增一个 judge 结果标签」的那一句，本轮不再当身份。
2. 092 可以在安放句里说「那一格字可以叫做一个结果标签」，但必须立刻写「这不是这块东西的名字」。
3. 不改 `JudgeFulfillmentAssessmentOutput`，不加模型可写字段。

**Risks**: 有人把「可以叫结果标签」再听成 088 的方案名。必须靠 092 的主语和「不是名字」卡住。

**Verification**: 本号 Consensus 必须同时勾上：(1) 不能把这块东西改名为 judge 结果标签；(2) 看见层「多一格字」这一截可以留下；(3) 留下后不得焊回 Judge 再填 / 第二问。

**Why I Cannot Apply It**: 只读 peer；本号只拆名字和安放，不改看见层代码。

### What I Changed

- `issues/open/issue-091.md`: append-only Architect Response #1

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 8481552ab6d86f98
- pid: 85394

### Investigation

r2。不续写 spawn `44e93555a7a3fdcb`。自己拆了用户点名里「新增一个 judge 结果的标签」的两层。

- 用户问的是安放菜单：只补 NF / 新增一个 judge 结果的标签 / 3 扩 4 / 放进 NE / 别的方式。那四个字是菜单项，不是命名仪式。
- 085–088 把这四个字写成方案名，主语却是「开第二问自己的格子」。本轮可打这句主语和方案名，不重开内容。
- `spec/alg/product-function.md` §7.2 L171、§8 L193–L198：杀掉的主语是「让 Judge 再填一个新标签」，不是「人看见时会多一格字」。以后若看见，再加派生列；派生列不是 Judge 产出，不进 prompt，不改 fulfilled。
- `impl/core/schema/judge.py` L73–L76：`JudgeResult.summary` 已是基于 fulfillment_assessments 派生的展示摘要。L94–L103：模型可写评估字段里唯一的状态字仍是 `status`。
- `impl/core/frontend_view.py` L67–L82：矩阵一行一个 `expectation_id` + 一个 `status`，旁边没有另一格。
- `impl/frontend/summary.html` L766–L770：列是 Expectation / Expected / Capabilities / Status / Blocking。
- 047 / 058 Consensus 内容：同一张嘴兼答会对齐；计算是读已经裁完的前缀，不是再开一张嘴。

### Reasoning

必须把身份和安放切开。verifier 若把「judge 结果标签」写成这块东西的名字，下一句就会滑成「所以 Judge 再填」或「所以它叫第二问」。两句本轮都不认。

反过来也不能杀看见层这一截：人若看见，会多一格字。那一格字按看见层可以叫做一个结果标签。这只描述安放，不给这块东西改名。

还要挡住第三种滑法，dead r1 写得不够死：读者会把「可以叫结果标签」听成「选了用户菜单里的那一口」。用户那一口的主语是 Judge 填，§7.2 / §8 已经杀掉。本轮对那一口的回答是：没选它。选的是别的方式（092）。留下的只是看见层描述。

```text
这块东西是什么：这件事 × 产品事实 的出口
它出现在哪：若打开，人正在看的评估结果上会多一格字
那一格字叫什么：安放上可以说是一个结果标签
谁写下的：不是同一张嘴再判一次
菜单上选了哪一口：不是「新增一个 judge 结果的标签」
```

不整号 escalate。对外中文、打开与否仍停。

### Improvement Proposal

- **Target**: `issues/open/issue-091.md` 待写 Consensus。
- **Change**:

```text
这块东西不改名为 judge 结果标签。
「新增一个 judge 结果标签」最多描述安放：人看见时会多一格字。
这不是选了用户菜单里「新增一个 judge 结果的标签」那一口。
那一口的主语是 Judge 填，已经杀掉。

不得焊回：
  所以 Judge 再填一个 status
  所以它叫第二问 / 兄妹问
  方案名就是这块东西叫 judge 结果标签
  看见层也不能叫标签，因此没有方案
```

- **Verification**: Consensus 若把方案名写成这块东西叫 judge 结果标签，或写成看见层也不能叫标签所以没有方案，本号失败。

### What I Changed

- `issues/open/issue-091.md`: 只追加本段 r2 Architect Response #1。未改项目源码、协议、数据。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `8481552ab6d86f98`

接受 architect r2 的拆层。用户菜单里「新增一个 judge 结果的标签」不能当这块东西的名字，也不能当成「判定再写一个词」。

```text
这块东西是什么：这件事 × 产品事实 的出口
它出现在哪：若打开，人正在看的评估结果上会多一格字
那一格字叫什么：安放上可以叫结果标签
谁写下的：不是同一张嘴再判一次；读已经裁完的前缀（058）

「judge 结果标签」只描述安放。
它不是这块东西的名字。
它不是选了用户菜单那一口。
它不是让 Judge 再写 status。
字段层「judge 结果标签」继续等于 JudgeFulfillmentAssessmentOutput.status；那一层继续死。
085–088 以「第二问」为主语、把方案名写成「新增一个 judge 结果标签」的那一句，本轮不沿用。
```

不改 schema，不加字段，不宣布对外中文。

闸：同 089。

