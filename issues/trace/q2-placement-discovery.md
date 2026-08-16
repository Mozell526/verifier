# Discovery — 第二问现行出口与四层落点

章程：`issues/charter-q2-placement.md`
日期：2026-08-16
范围：只读协议 + 现行出口。不跑 judge。不改 impl。

## 已经锁死、本轮当给定

- 040 / report-no-rule-total：两问对象同一件，只换证据单位。第二问不算类型表。
- 046–048：不是 NF 专属；不是 Judge 兼答；不加第四态；不加 Judge 新标签。
- 用户标注：产品事实来自「已经裁完的能力/职责判断，及其依据资料」。

053–057 的「第二问」是另一件事（整句有没有被这一维说完）。本轮不引用它们的定义。

## 现行出口（读到的）

### 1. Judge 只写第一问

`impl/core/schema/judge.py`：

- `JudgeFulfillmentAssessmentOutput.status`：办成了没有
- `FulfillmentAssessment.status`：同一句
- `authority_tool_call_ids`：这一条期望引用了哪些 authority 调用
- 没有第二问字段

`spec/info-volume.md`：judge 只产出 fulfillment（细粒度 + 整体），不产 verdict，不引入 partial。

### 2. 用户现在看见的「状态」是整体第一问

`impl/frontend/summary.html`：

- 顶部统计：Fulfilled / Not Fulfilled
- 筛选：全部达成状态 = fulfilled / not_fulfilled
- 用例表列名「状态」：`renderCaseStatus` ← `fulfillmentStatus` ← `overall_fulfillment.status`
- `fulfillmentPill` 只有三种颜色：ok / bad / warn

`impl/core/table_view.py` L160–165 / L277–294：行上的 `status` / `fulfillment_status` 都来自 overall fulfillment。

### 3. 细粒度第一问已经挂在矩阵里

`impl/core/frontend_view.py` `_fulfillment_panel`：

```
Expectation | Expected | Capabilities | Status | Blocking
```

`Status` = 这一条 expectation 的 `FulfillmentAssessment.status`。
`Capabilities` = `required_capabilities`，是库存式能力名列表，不是第二问。

`renderFulfillmentMatrix`（summary.html L766–770）原样画出这五列。

### 4. Authority 已经在裁产品事实，但只被拿去改第一问

`spec/alg/authority.md` §8.3：

```
职责外           → 第一问说不清
职责内能力缺失   → 不改写办成了没有；没给到=没办成，给到了=办成了
职责内正常       → 继续原评价
```

`impl/core/authority_gate.py`：

- 读 statement 前缀：`职责外` / `职责内能力缺失` / `职责内正常`
- 职责外 → 强制 `not_evaluable`
- 职责内能力缺失且被写成 NE → 拉回 `not_fulfilled`
- 职责内正常 → 不覆盖
- 不产出第二问三态

所以：产品事实已经有裁口，现行消费者只有第一问。

### 5. 这一次不一定裁过

Authority 是可选的。Judge 只在需要裁边界时才调。姓名查找办成了，常常没有 `authority_tool_call_ids`。

因此「只读这一次调用」会让多数「立住了」变成「说不清」。
040 写的是「已经裁完的能力/职责判断，及其依据资料」，不是「这一次刚好问过」。
也禁止读 `is_supported` / catalog / current_behavior。

### 6. 协议文件和 040 有一处旧操作化

`spec/alg/product-function.md` 仍写「这类事 / 认种类」，§3 还有整案按种类汇总。
039 / 040 已退休「认哪一类 / 那一档」。
本轮不改协议正文。实现时不得跟着旧 §3 去编类型表。

§8–9 已经写过落点方向：不加枚举、不加 Judge 新标签、以后若看见再加派生列、现在不改 schema / 前端。

## 碰撞（只作落点，不重判）

| 期望（第一问那一件） | 第一问出口 | 若把第二问塞进「状态」 | 若按同一条期望读已裁口 |
|---|---|---|---|
| 按姓名找（漏了） | 没办成 | 过严和「没这项功能」混成一个红点 | 立住了 |
| 投保年 / 「去年」 | 没办成或被盖住 | 整案一个词 | 没立住 |
| 投保人 / 全家保 | 办成了 | 成功案上看不见第二问 | 立住了 |
| 查天气 | 说不清 | 和没立住一个黄点 | 说不清（职责外） |
| 能力缺失但这回给到了 | 办成了 | 要么改口成没办成，要么假装立住了 | 没立住 |

## 本轮要钉的四件事

1. 谁算：不是 Judge，不是 fulfilled 枚举；只读已裁口 + 依据资料。这一次没裁过，不得用办成了反推。
2. 粒：同一条期望。没有案件级类型列。
3. 四层：协议 / 计算 / 存放 / 看见必须拆开。
4. 现在不改出口。看见与否仍交用户。
