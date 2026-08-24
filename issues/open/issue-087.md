# Issue #087: 挂在同一条期望行、Status 旁边；不进 status，不改主表芯片

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 安放 / 挂在哪一格
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

085 锁方案名。086 锁不是哪三个口。本号锁挂在哪一格。

060 Consensus 已经点名：规范格子在矩阵行上、Status 旁边。那是唯一已经按第一问那一件分行的出口。

现行原文：

- `impl/core/frontend_view.py` L71–81：`_fulfillment_panel.matrix[]` 每行只有一个 `status`
- `impl/frontend/summary.html` `renderFulfillmentMatrix`：列是 Expectation / Expected / Capabilities / Status / Blocking
- `impl/core/schema/judge.py` L94–103：模型可写评估字段只有 `status`
- `impl/core/schema/table.py` L36：主表只有 `fulfillment_status`
- `impl/core/table_view.py`：芯片值仍是第一问三个词

以后若打开，第二问那一格挂在矩阵同一行、Status 旁边。现在那一格不存在。

不挂进：

- `assessment.status` / `JudgeFulfillmentAssessmentOutput.status`：那是第一问的嘴
- 主表 `fulfillment_status` 芯片：那是第一问的总览，人现在停在这里，不能因此把第二问塞进去
- 主表新芯片：那是打开 / 主表要不要做派生投影，仍交 061，本号不布置

`JudgeResult.summary` 已经证明：同一张评估卡上可以有派生展示，不必让模型再写一个字段。

存放仍是 060：现在不进 `JudgeFulfillmentAssessmentOutput`。以后若存，只物化同一份派生读。计算仍是 058：读已经裁完的能力/职责前缀。

### 可证伪

同时成立才算本 issue 站住：

1. 能指出现行出口上以后若打开、挂在哪一格：矩阵同一行、Status 旁边；
2. 那一格现在不存在，不是因为它属于三个词里的某一个；
3. 不把这一格写进 status，也不把主表芯片改成四态。

若另找一格（主表芯片、NE reason、只在 NF 行画标记），本 issue 失败。
若点名这一格就被听成「本轮加列 / Judge 来填」，本 issue 失败。

## Proposed Change

Consensus 只锁：挂在 fulfillment_panel 矩阵同一行、Status 旁边。不进 status，不改主表芯片。本轮不加列。

---
## Architect Response #1

**Judgment**: real-problem
**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 5d262889dc7c1b05
- pid: 51034

### Investigation

自己对着现行出口数格子，不把 060 / 079 的指针当成已经实现的列。

现行原文：

- `impl/core/frontend_view.py` L61–86 `_fulfillment_panel`：按 `business_expectations` 逐条铺 `matrix[]`。每行字段是 `expectation_id` / `downstream_consumer` / `expected_outcome` / `required_capabilities` / `status` / `score` / `blocking` / `downstream_impact`。`status` 来自 `assessment.status`，缺省 `not_evaluable`。没有第二问那一格。
- `impl/frontend/summary.html` L766–770 `renderFulfillmentMatrix`：列是 Expectation / Expected / Capabilities / Status / Blocking。包在 `<details class="accordion" open>`，标题「业务预期达成矩阵」，由 `renderJudgeCard`（L778–782）画进单链路 Judge 评估卡。默认展开，不是 hidden 调试块。
- 同文件 L377 `fulfillmentPill`、L393–400 `renderCaseJudge`：用例池第一眼看的是 `fulfillment_status` 三词，不是矩阵。
- `impl/core/schema/judge.py` L94–103：模型可写评估字段只有 `status`。L73–76：`JudgeResult.summary` 已是派生展示。
- `impl/core/schema/table.py` L36、`impl/core/table_view.py` L107–109：主表芯片仍是第一问三个词。

协议：`product-function.md` §8「以后若要看见，再加派生列；派生列不是 Judge 产出」。`fulfilled.md` 不并进三态。

已锁：060 规范格子 = 矩阵同一行、Status 旁边，不是用户此刻停在主表「状态」上的视线；079 把 077 的兄妹标签绑在这一格；061 打开 escalate。本号不重开位置，只把 085 的方案名绑回这一格。

### Evidence Verification

核过。矩阵行上 Status 旁边现在确实没有第二格。这一格缺席，不是因为它属于三个词里的某一个，是 `_fulfillment_panel.matrix[]` 根本没产这个键，前端也没画这一列。
矩阵不是「只有内部 panel 才有的东西」。单链路 Judge 卡默认展开就画这张表。它也不是人第一眼停住的地方：用例池看的是芯片。060 已经把这两层视线拆开。本号不得把规范格子挪回芯片来迁就第一眼。

### Reasoning

三记攻击。本号只锁挂点，不批准加列。

1. 这张网格是用户真看见的，还是只有内部 panel？
两边都不是极端。`_fulfillment_panel` 是给前端的数据包。人看见的是 `renderFulfillmentMatrix` 画出来的那张「业务预期达成矩阵」。它在 Judge 评估卡上，默认 `open`。看单链路结果的人看得到。只扫用例池的人看不到——他们看到的是 `fulfillmentPill`。060 写过：规范格子是唯一已经按第一问那一件分行的出口，不是用户此刻停在主表「状态」上的视线。本号继续认这一格，不把它降成「内部才有、因此作废」。

2. 用户若问「用户怎么看到这个东西」，矩阵里 Status 旁边、还得点进评估卡，是不是仍然没答？
若问的是第一眼，是没答完。那一截不是本号能锁的。061 / 章程 §4 已经 escalate：现在看不看得见、主表要不要做派生投影，是项目决定。本轮不得布置主表新芯片，也不得把「挂在哪」偷换成「先改用例池让人看见」。用户本轮问的是方案名和安放，不是批准打开。规范格子答的是：以后若打开，第二问跟哪一件、跟哪一格 Status 并排。第一眼另算。

3. 点名 `_fulfillment_panel` 是不是在偷运实现？
不是，只要当现行出口指针，不当作业单。060 / 079 已经用过同一个指针。章程要的是「能指出现行出口上，以后若打开，挂在哪一格」。不点名就指不准。点名不等于「本轮给 `matrix[]` 加键、给 `summary.html` 加 `<th>`」。087 正文已经写了本轮不加列、不进 `JudgeFulfillmentAssessmentOutput`、不改主表芯片。Consensus 若写成「请先在矩阵加一列」「请 Judge 填这一格」，那一部分否掉。

不挂进：`assessment.status` / `JudgeFulfillmentAssessmentOutput.status`（第一问的嘴）；主表 `fulfillment_status` 芯片（第一问总览）；主表新芯片（打开 / 投影，仍交 061）。计算仍是 058 的读。以后若存，只物化同一份派生读。`JudgeResult.summary` 继续当反例：同一张评估卡上可以有派生展示，不必让模型再写一个字段。

**Judgment / Verdict**：real-problem。以后若打开，挂在 fulfillment_panel 矩阵同一行、Status 旁边。不进 status，不改主表芯片。本轮不加列。

## Improvement Proposal

**Problem**: 方案名改口后，挂点会被听成「进芯片」或「本轮给矩阵加列」。
**Proposed Change**: 只锁绑名。不重开 060 / 079，不布置前端。

```text
挂在 fulfillment_panel 矩阵同一行、Status 旁边。
那是现行出口上唯一已经按第一问那一件分行的格子。
现在那一格不存在。
不进 assessment.status / JudgeFulfillmentAssessmentOutput.status。
不改主表 fulfillment_status 芯片，也不在本号布置主表新芯片。
点名 _fulfillment_panel 是出口指针，不是本轮加列。
```

**Implementation Steps**:
1. Consensus 只写上面六句。
2. 不改 `frontend_view.py` L71–81，不改 `summary.html` L766–770。
3. 打开 / 主表投影仍交 061。

**Risks**: 读者把「挂在哪」读成「请先加列」。用「现在那一格不存在 + 本轮不加列」挡。
**Verification**:
1. 对照 `frontend_view.py` L71–81：被点名的那一格现在确实不存在。
2. 对照 `summary.html` L766–770 / L377：矩阵默认可见于 Judge 卡；第一眼仍是芯片。
3. Consensus 若出现「请先加列」「请 Judge 填」「先改主表状态」，本锁失败。

### What I Changed
无。review 模式，只追加本回应。未改 spec / impl / 前端。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `5d262889dc7c1b05`

085 的方案名绑回 060 / 079 已经点名的那一格。不另找格子，不重开位置。

收下 architect 的落点：

- 以后若打开，挂在 fulfillment_panel 矩阵同一行、Status 旁边。
- 那是现行出口上唯一已经按第一问那一件分行的格子。现在那一格不存在。
- 矩阵在 Judge 评估卡上默认展开，不是内部才有的东西。第一眼仍是芯片；那一截仍交 061。
- 不进 `assessment.status` / `JudgeFulfillmentAssessmentOutput.status`。
- 不改主表 `fulfillment_status` 芯片，也不在本号布置主表新芯片。
- 点名 `_fulfillment_panel` 是现行出口指针，不是本轮加列。
- 计算仍是 058 的读。现在不进判定那张嘴；以后若存，只物化同一份派生读。

闸：同 085。
