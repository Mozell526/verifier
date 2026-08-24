# Issue #060: 四层必须拆开，看见点只可能在矩阵行上，不在「状态」芯片上

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Placement / 协议·计算·存放·看见
**Cases**: 无。本 issue 只对现行出口做落点。

## Verifier Discovery

用户上一句已经问过：到底放在哪里？用户怎么看到？现在前端只能看见 fulfilled。
048 Consensus 把「以后另开一列」停在看见面，没有批准。
本 issue 只钉四层，不代选现在看不看得见。

### 四层不是同一个动作

| 层 | 现行事实 | 第二问该落在哪 | 明确不是 |
|---|---|---|---|
| 协议 | `fulfilled.md` 答第一问；`product-function.md` 已是同级草稿 | 继续做第一问的兄妹文，不并进 fulfilled | 不是 authority 再发明第四种 statement 前缀 |
| 计算 | `authority_gate.py` 只拿裁口改第一问 | Judge 写完之后读已裁口 + 依据资料（058） | 不是 Judge LLM 新填；不是 `is_supported` |
| 存放 | `JudgeFulfillmentAssessmentOutput` 只有 status | 现在不进这张嘴。若以后要持久化，只能像 `summary` 一样事后派生 | 不是 schema 新枚举；不是 prompt 字段 |
| 看见 | 案件表「状态」= 整体第一问；矩阵 Status = 这一件第一问 | 以后若看见：同一行、Status 旁边，另开一格 | 不是「状态」的第四种颜色；不是只在 NF 行出现 |

`spec/alg/product-function.md` §8–9 已经按这个方向写过：先对照阅读，以后若看见再加派生列，不进 Judge，不进 prompt，不改 fulfilled。本轮把它从「方向」收成「四层落点」。

### 为什么看见点不能是案件表「状态」

`impl/frontend/summary.html` L107 的「状态」、L377 的三色 pill、L29–30 的 Fulfilled 计数，吃的都是整体第一问。

把第二问画进这一格，会同时做三件被禁的事：

1. 一个词回答两问（048 / product-function §7.1）
2. 对象被切粗成案件（059）
3. 用户会以为 fulfilled 多了一种状态（015 已死的第四态）

所以：现在只能看见 fulfilled，不是因为第二问属于没办成，是因为第二问还没有自己的格子。缺的是出口，不是定义。

### 为什么看见点只能是矩阵行上、Status 旁边

矩阵已经按第一问那一件分行：

```text
Expectation | Expected | Capabilities | Status | Blocking
```

- Status 是第一问细粒度出口
- Capabilities 是库存名，不能冒充第二问（040 / 059）
- 第二问若要被人看见，必须跟 Status 同粒、不同题：同一行的另一格

这格对办成了 / 没办成 / 说不清三侧都在。只在红行出现，046 已否。

不把 authority 的 statement 原文糊到界面上。用户要看见的是第二问三态，不是「职责内能力缺失：…」这句裁口。

### 存放为什么现在只能是投影

`summary_from_fulfillment` 和 `_fulfillment_panel` 都已经是读完 Judge 再投影。
第二问同一类：算的时候不改 `status`，也不进 `JudgeFulfillmentAssessmentOutput`。

现在就改 schema / 结果表，是章程 §4。本 issue 只锁：即使以后要存，也只能存派生结果，不能存成 Judge 产出。

### 可证伪

1. 若把第二问画进案件表「状态」还能保住「一个词不答两问」和「对象不切粗」，本 issue 不成立。
2. 若 Capabilities 列不看 Status 就能回答「产品把这件事立住了没有」，看见点应改挂那一列。
3. 若第二问必须先写进 `JudgeFulfillmentAssessmentOutput` 才能被矩阵读到，058 的「读」不成立，应打回 058。

### 不是什么

- 不是现在改 `summary.html`
- 不是批准派生列上线
- 不是给这格起对外中文名

### 请对手挑战

- 协议层继续放在 `product-function.md`，会不会让实现跟着旧「认种类」走？是不是应该明确：兄妹关系留下，§3 操作化不得当实现说明书？
- 矩阵现在要点进单案才看得到。用户说「前端只能看见 fulfilled」，会不会其实是在问主表，而不是问点进去之后的矩阵？挂在矩阵上是不是答错了看见面？
- 「现在只做投影、以后再存」会不会又是「先这样以后再换」？项目红线不接受临时方案。投影是不是已经是最终存放形态？

### 未消元

- 现在看不看得见、改不改表：见 061

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: f7ab9fd0b34ddbc9
- pid: 59819

### Investigation

自己对了四层和现行看见面，不把「挂在矩阵上」听成「人现在就能在主表看见」：

- 章程 Done：四层必须拆开——写进协议 ≠ 让 Judge 填 ≠ 写进结果表 ≠ 画在「状态」芯片上。看见与否仍停在 §4。
- `spec/alg/fulfilled.md` §1：本协议只评办成了没有；产品功能见 `product-function.md`，不并进三态，也不新增第四态。
- `spec/alg/product-function.md` 开篇 / §7 / §8–9：同级草稿；现在只对照阅读；不加枚举、不加 Judge 新标签；以后若看见再加派生列，不进 prompt，不改 fulfilled。§3 仍留着「认种类 / 按种类汇总整案」。
- `impl/core/schema/judge.py`：`JudgeFulfillmentAssessmentOutput` 只有 `status`。`JudgeResult.summary` 已是读完 fulfillment 再派生的展示摘要。
- `impl/core/frontend_view.py` `_fulfillment_panel`：矩阵列是 Expectation / Expected / Capabilities / Status / Blocking。Status = 这一条 expectation 的第一问。
- `impl/core/table_view.py`：案件行 `status` / `fulfillment_status` = 整体第一问。
- `impl/frontend/summary.html` L29–30 Fulfilled 计数、L84「全部达成状态」、L107 案件表「状态」、L377 三色 pill、L428–431 `renderCaseStatus`：全是整体第一问。
- 同文件 L766–770 `renderFulfillmentMatrix`：要点进单案 accordion 才看得到五列；Capabilities 原样画出 `required_capabilities`。
- 048 Consensus：「以后另开一列」是看见面方向，不是本轮批准。看见与否、挂哪、叫什么，仍交章程 §4。
- 041 Consensus：要不要看见、叫什么中文、改不改 schema，是项目决定，不是用户作业。

### Reasoning

四层拆开是本轮真正要钉的东西。看见点不能进「状态」芯片，也对。原文有两处必须收紧，否则会答错面、或者把 §3 旧操作化当成实现说明书。

**1. 矩阵行上、Status 旁边，是唯一粒对的格子，不是人现在扫到的那张主表。**

把第二问画进案件表「状态」，会同时做三件被禁的事：一个词答两问（048 / product-function §1）、对象切粗成案件（059 / 040）、fulfilled 多一种颜色（015 已死的第四态）。可证伪 1 打不穿。Capabilities 不看 Status 也答不出产品把这件事立住了没有，看见点不能改挂那一列。可证伪 2 打不穿。矩阵读的是投影，不必先写进 `JudgeFulfillmentAssessmentOutput`。可证伪 3 打不穿。

但用户问的是「人怎么看见」。现行目光停在 L107 那一列，不在点进去之后的矩阵。060 若写成「所以人看见第二问就是看见矩阵」，答错面了。诚实说法：

```text
人现在看见的：案件表「状态」= 整体第一问。第二问没有格子。
以后若看见：规范格子 = 同一条期望行上、Status 旁边的另一格。
            办成了 / 没办成 / 说不清三侧都在；只在红行出现，046 已否。
            不把 authority statement 原文糊到界面上。
主表可以另做的，最多是这些行的派生投影，不能代替行，
也不能重新变成一枚「状态」芯片。那是 061 / §4，本 issue 不代选。
```

挂在矩阵上不是因为那是用户此刻的视线，是因为那是唯一已经按第一问那一件分行的出口。主表一行一个案子，放进去就切粗。

**2. 「现在投影、以后再存」不是「先这样以后再换」。**

项目红线不接受临时架构。这里的投影不是占位实现。058 已经把计算锁成读；`JudgeResult.summary` / `_fulfillment_panel` 已经是「Judge 写完再派生」。第二问同一类：算的时候不改 `status`，也不进 `JudgeFulfillmentAssessmentOutput`。以后若持久化，只能物化**同一份读**，不能变成第二份真源，更不能事后改成 Judge 产出。

所以最终存放形态就是派生结果。现在不落库，是章程 §4（改不改 schema），不是先做一套以后扔掉。本轮不改表。

**3. 协议层继续留在 `product-function.md`，但 §3 不得当实现说明书。**

兄妹关系留下：fulfilled.md 答第一问，product-function.md 答另一问，不并进。这是 040 / 046–048 已经用过的文件位置。本轮不改协议正文。

§3「认种类 / 一件事里有几类分开看 / 按种类汇总整案」是 039 / 040 已退休的操作化。实现若跟着它走，会在 059 已经否掉的地方编案件级种类列。本 issue 必须写明：

```text
协议落点：继续做 fulfilled.md 的兄妹文
实现说明书：040 的「同一件、只换证据单位」+ 058 的读法
不是实现说明书：product-function.md §3 的认种类 / 整案按种类汇总
```

不在协议层再发明第四种 authority statement 前缀。

本轮不改 `summary.html`，不批准派生列上线，不给那一格起对外中文名。

## Improvement Proposal

**Problem**: 四层一直被收成同一个动作；若不拆开，第二问会被塞进「状态」芯片，或被 `product-function.md` §3 带去编种类列。

**Proposed Change**: 锁四层落点。不改协议正文，不改前端，不加字段。

**Design**:

```text
060 锁（位置图，不是上线）：

协议   product-function.md 继续做兄妹文，不并进 fulfilled.md
       §3 认种类 / 整案按种类汇总：不得当实现说明书
计算   058：Judge 写完之后读已裁口；不是 Judge 填，不是 is_supported
存放   现在不进 JudgeFulfillmentAssessmentOutput
       以后若存，只能物化同一份派生读（同类 summary / _fulfillment_panel）
       派生不是第二份真源
看见   规范格子 = 矩阵同一行、Status 旁边
       不是案件表「状态」的第四种颜色
       不是只在 NF 行出现
       不是 Capabilities 列
       不是 authority statement 原文
       主表现在仍只看见第一问；这不是定义残缺，是出口还没有

现在看不看得见、改不改表、对外叫什么：061 / 章程 §4
```

**Implementation Steps**:

1. Consensus 收下四层表，并写明矩阵是规范格子、不是当前主表视线。
2. 显式写：§3 不得当实现说明书；兄妹文件关系留下。
3. 把「以后再存」写成「物化同一份投影」，不得写成临时方案。
4. 不写列名、字段名、对外中文。不改 `summary.html`。

**Risks**: 把规范格子听成「本轮已经让人看见」；把投影听成以后要换真源；实现跟着 §3 去编种类列；在主表「状态」上偷加第四色。

**Verification**:

```text
# 1. summary.html L107 / L377 / L428：状态芯片仍只吃 fulfilled 三态
# 2. renderFulfillmentMatrix 仍是五列，没有本轮新列
# 3. JudgeFulfillmentAssessmentOutput 仍只有 status
# 4. product-function.md §3 原文不动；Consensus 必须写「不得当实现说明书」
# 5. Consensus 不得宣布对外中文，不得批准本轮改表
```

**Why I Cannot Apply It**: 只读 peer。改协议正文 / 前端 / schema 都在红线外。看见与否属章程 §4。

---
## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `f7ab9fd0b34ddbc9`

四层必须拆开。规范格子在矩阵行上、Status 旁边。那是唯一已经按第一问那一件分行的出口，不是用户此刻停在主表「状态」上的视线。

收下 architect 的收紧：

- 协议：`product-function.md` 继续做 `fulfilled.md` 的兄妹文，不并进。§3 认种类 / 整案按种类汇总，不得当实现说明书。
- 计算：058 的读。不是 Judge 填，不是 `is_supported`。
- 存放：现在不进 `JudgeFulfillmentAssessmentOutput`。以后若存，只能物化同一份派生读（同类 `summary` / `_fulfillment_panel`）。投影就是最终存放形态，不是以后要换的临时方案。
- 看见：规范格子 = 矩阵同一行、Status 旁边。不是案件表「状态」的第四种颜色，不是 Capabilities 列，不是 authority statement 原文，不是只在没办成行出现。主表最多以后做这些行的派生投影，不能代替行，也不能重新变成一枚「状态」芯片。

现在看不看得见、改不改表、对外叫什么：061 / 章程 §4。本轮不改 `summary.html`，不批准派生列上线，不宣布对外中文。

闸：同 058。
