# Discovery — q2-is-label

本轮不重跑 judge。只对照协议、现行出口、已锁 Consensus。

## 用户本轮点名

开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗？
按 fulfilled 的定位：只是 NF 补充？新增一个 judge 结果标签？3 扩 4？放到 NE？还是别的方式？给方案。不实现。

## 两问结构（用户标注，已锁）

第一问已经有出口：这一次办成了没有 → 办成了 / 没办成 / 说不清。
第二问出口还没有：用户要的这件事，产品把它立成自己会做的事了没有 → 立住了 / 没立住 / 说不清。
对象同一件。不得另立类型表。

## 现行出口（人现在看见的 judge 结果标签）

1. `impl/core/schema/judge.py`
   - `FulfillmentAssessment.status`：每条期望一格
   - `JudgeFulfillmentAssessmentOutput` 模型可写评估字段只有 `status`
   - `JudgeResult.summary`：基于 fulfillment_assessments 派生的展示摘要，已经证明同一张评估卡上可以有派生展示

2. `impl/core/schema/table.py`
   - 主表只有 `fulfillment_status`

3. `impl/core/table_view.py`
   - 芯片值 = judge_summary.fulfillment_status / overall.status / 行 status

4. `impl/core/frontend_view.py` `_fulfillment_panel`
   - 矩阵每行只有一个 `status`，来自 `assessment.status`
   - 列：expectation_id / downstream_consumer / expected_outcome / required_capabilities / status / score / blocking / downstream_impact
   - 没有第二问那一格

5. `impl/frontend/summary.html`
   - `fulfillmentPill` 只认三词
   - `renderFulfillmentMatrix` 列是 Expectation / Expected / Capabilities / Status / Blocking
   - `renderJudgeCard` 的「评估」也是这一格

## 协议

- `spec/alg/fulfilled.md`：只评办成了没有；邻协议不并进三态，也不新增第四态
- `spec/alg/product-function.md` §1：任何一张表、一个标签、一句结论，都不能同时回答这两件
- 同文件 §7.2：让 Judge 再填一个新标签来回答本协议 ✗
- 同文件 §8：禁给 fulfilled 加枚举；禁新增一个让 Judge 填的标签；以后若要看见，再加派生列；派生列不是 Judge 产出
- `spec/info-volume.md`：judge 只产出 fulfillment，不需要再引入第二个对错维度

## 已锁、本轮不重开

- 040：两问同级，对象同一件；办成了不能自动排除没立住
- 047：同一张嘴兼答两问，几乎一定会对齐刚才的办成了没有
- 058：第二问是读已经裁完的前缀，不是再开一张嘴
- 060：规范格子 = 矩阵同一行、Status 旁边；现在不进 JudgeFulfillmentAssessmentOutput
- 061：打开 escalate，位置已锁
- 065：若「新增一个 judge 结果的标签」= 同一轮判定再写一个词，不能当宿主
- 066-q2：若打开第二问自己的格子，看结果的人会多看见一个标签
- 069：四个点名口没有一个能整句当宿主
- 077–080：方案写成「看见层兄妹结果标签」，同时说「写/枚举层选的是别的方式」

## 本轮增量

077 把方案名写成「别的方式」。用户把「开格子本质上不就是新增一个 judge 结果的标签吗」又问了一遍。
本轮要锁：方案名就是「新增一个 judge 结果标签」。不再选「别的方式」。
