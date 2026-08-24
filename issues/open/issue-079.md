# Issue #079: 这个标签挂在矩阵同一行、Status 旁边；不进判定 status，也不改主表芯片

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 现行出口落点
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

077 说方案是看见层的兄妹结果标签。本 issue 钉它挂在现行出口的哪一格。不打开。

### 现在有哪些格子

| 格子 | 现在答什么 | 能不能当第二问宿主 |
|---|---|---|
| `JudgeFulfillmentAssessmentOutput.status` | 第一问三词，模型可写 | 不能。那是第一问的嘴 |
| `FulfillmentAssessment.status` | 同上，结果对象 | 不能。存的是同一格 |
| `TraceTableRow.fulfillment_status` / 主表「状态」芯片 | 整案第一问 | 不能。060：不能变成第四种颜色 |
| `_fulfillment_panel.matrix[].status` | 这一条期望的第一问 | 不能。这列已经姓第一问 |
| `_fulfillment_panel.matrix[]` 同一行、status 旁边 | 现在没有这一格 | 规范格子（060） |
| `required_capabilities` 列 | 期望声明的能力名 | 不能。那不是产品立没立住 |
| authority statement 原文 | 裁口材料 | 不能。人现在不在这里读结果标签 |
| attribute / NE 原因 | 归因或第一问说不清的差在哪儿 | 不能 |

`_fulfillment_panel` 已经按 `expectation_id` 分行，对象和第一问是同一件。旁边加一格，不必另立类型表，也不必把对象切粗切细。

主表芯片是整案投影。以后最多做这些行的派生投影，不能代替行，也不能让人以为「状态」芯片改成了四个词。

### 谁写、存哪

058：Judge 写完第一问之后，读这一条期望上已经写下的能力/职责前缀（含同一次任务内 §7 允许去重的那一次，及其依据资料）。
没有裁口 → 第二问说不清（依据不充分）。不得用办成了反推立住了。

以后若存：物化同一份派生读，形态同类 `summary` / `_fulfillment_panel`。不进 `JudgeFulfillmentAssessmentOutput`，不进 prompt。`product-function.md` §8 的「派生列」说的是这件事，不是新判定。

### 四层（引用 060，不重开）

```text
协议    fulfilled.md 的兄妹文，不并进三个词
        对象仍是第一问那一件，不切成种类表
计算    判定写完第一问之后，读已经写下的前缀
存放    现在不进判定那张嘴；以后若存，只物化同一份读
看见    矩阵同一行、Status 旁边另开一格
        人看见的是一个新的结果标签
        这个标签不是第四个词，不是说不清，不是没办成的附注
        这个标签不是判定再写的
```

### 可证伪

若规范格子被改回主表芯片、Capabilities 列、authority 原文、或只在 NF 行出现，本 issue 失败。
若本 issue 批准现在改 `summary.html` / 加 schema 字段，本 issue 越权。

## Proposed Change

Consensus 只锁落点：矩阵同一行、Status 旁边。不实现。

---
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 344d097baef18f39
- pid: 23530

### Investigation
自己重读现行出口，不把 060 的结论当本号已证。

现在有的格子：
- `JudgeFulfillmentAssessmentOutput.status`（`judge.py` L94–97）：模型可写，第一问三词。
- `FulfillmentAssessment.status`（`judge.py` L27–30）：同一格的结果对象。
- `TraceTableRow.fulfillment_status`（`table.py` L36）+ `_fulfillment_status`（`table_view.py` L107–109）：整案第一问芯片。
- `_fulfillment_panel.matrix[].status`（`frontend_view.py` L71–81）：按 `expectation_id` 分行，值仍是 `assessment.status`。
- `renderFulfillmentMatrix`（`summary.html` L766–770）：列 = Expectation / Expected / Capabilities / Status / Blocking。没有第二问列。
- `required_capabilities`：期望声明的能力名，不是产品立没立住。
- `authority_tool_call_ids`：引用，不是第二问答案。
- `renderJudgeCard`（`summary.html` L778–782）：矩阵已经画在 Judge 评估卡里。

`JudgeResult.summary`（`judge.py` L73–76）已经证明：同一张 Judge 卡上可以有派生展示，而不等于模型又写了一个评估字段。

060 Consensus 原文：「规范格子 = 矩阵同一行、Status 旁边。不是案件表『状态』的第四种颜色，不是 Capabilities 列，不是 authority statement 原文，不是只在没办成行出现。」打开仍交 061。

本号新钉的不是另找一个格子。是：077 把剩余叫做「judge 结果标签」之后，这个名字默认会被听成 `assessment.status` 或主表芯片。079 要把这个名字绑回 060 已经锁死的那一格。

### Reasoning
三记攻击。079 最容易变成 060 复读，所以只判增量。

1. `_fulfillment_panel` 已经是 Judge 卡。派生兄妹仍会看起来像 Judge 产出，077 是不是塌回判定再写的 B？
看起来像出现在 Judge 评估结果上：会。这正是 077 说「看见层叫 judge 结果标签成立」的原因，不是缺陷。
由 `status` 那张嘴写出来：不会。卡上已经有反例——`JudgeResult.summary` 是派生展示摘要，活在同一张卡上，不是 `JudgeFulfillmentAssessmentOutput` 的字段。`product-function.md` §8 允许的「派生列」说的就是这种东西：不是 Judge 产出，不进 prompt，不改 fulfilled。058 的读，以后若物化，形态同类 `summary` / `_fulfillment_panel`。
焊法才塌回 B：把「出现在 Judge 卡上」听成「Judge 再填一个 status」。章程要拆开的就是这两句。方案可以要求：以后若打开，这一格必须能从呈现上读成派生/对照，而不是第二枚 Status。本轮不实现前端，不把这句布置成改 `summary.html`。

2. 用户问的是不是只是主表芯片？
最熟、现在亮着的那一格，确实是主表「状态」。用户点名「judge 结果的标签」时，很多人眼睛停在这里。但这枚芯片是整案第一问投影，不是按第一问那一件分行的出口。把它当宿主，不是答「用户怎么看到」，是把第二问收成第四种颜色。060 已经禁。用户本轮问的是四个口怎么安放，不是「必须写在第一眼那枚芯片上」。第一眼看不看得见，061 已经 escalate。079 把标签钉在矩阵行上，是为了对象仍是第一问那一件，不必另立类型表，也不必切粗切细。

3. 060 已经锁了这个格子，079 是不是 not-actionable？
060 锁的是格子。本轮 077 新给了一个名字。这个名字在本产品里，默认指 `JudgeFulfillmentAssessmentOutput.status` 或主表芯片。若不在本轮把名字和格子绑死，077 会在下一句被听成「所以还是改 status」。079 的增量是绑名，不是发明新格，也不是重开 060 的四层。可证伪仍然有效：若规范格子被改回芯片 / Capabilities / authority 原文 / 只在 NF 行出现，本号失败；若本号批准现在改 `summary.html` 或加 schema 字段，本号越权。

**Judgment / Verdict**：real-problem。落点仍是 060 那一格：矩阵同一行、Status 旁边。不是 `assessment.status`，不是主表芯片。不是实现指令。

## Improvement Proposal

- **Target**: 本号 Consensus。引用 060，不重开 060。
- **Change**:

```text
077 说的兄妹结果标签，若打开，挂在 fulfillment_panel 矩阵同一行、Status 旁边。
不是 JudgeFulfillmentAssessmentOutput.status。
不是 FulfillmentAssessment.status。
不是主表 fulfillment_status 芯片。
不是 matrix[].status 改写成四个词。
不是 Capabilities 列，不是 authority 原文，不是只在 NF 行出现。
计算仍是 058 的读。现在不进判定那张嘴；以后若存，只物化同一份派生读。
本轮不改 summary.html，不加 schema 字段，不批准派生列上线。
点名 _fulfillment_panel 是现行出口指针，不是「请先加一列」。
```

- **Verification**:
  1. 对照 `frontend_view.py` L71–81 与 `summary.html` L766–770：现在那一格确实不存在，且旁边的 Status 仍姓第一问。
  2. 对照 060 Consensus：本号不得改规范格子，不得把主表芯片升格成宿主。
  3. Consensus 不得出现列名实现、字段名实现、「Judge 应填写」。

### What I Changed
无。review 模式，只追加本回应。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `344d097baef18f39`

077 说的兄妹结果标签，若打开，挂在 fulfillment_panel 矩阵同一行、Status 旁边。这是绑名，不是另找格子，也不重开 060。

收下 architect 的落点：

- 不是 `JudgeFulfillmentAssessmentOutput.status`
- 不是 `FulfillmentAssessment.status`
- 不是主表 `fulfillment_status` 芯片
- 不是把 `matrix[].status` 改写成四个词
- 不是 Capabilities 列，不是 authority 原文，不是只在 NF 行出现
- 出现在 Judge 评估卡上，不使 Judge 变成写的人。卡上已有派生 `summary` 作反例
- 计算仍是 058 的读。现在不进判定那张嘴；以后若存，只物化同一份派生读

点名 `_fulfillment_panel` 是现行出口指针，不是「请先加一列」。本轮不改 `summary.html`，不加 schema 字段，不批准派生列上线。

闸：同 077。
