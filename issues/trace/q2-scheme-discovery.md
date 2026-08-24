# Discovery — 第二问方案（开格子是不是新的 judge 结果标签）

日期：2026-08-16
章程：issues/charter-q2-scheme.md
不改代码，不跑 judge。

## 现行出口（人现在看见的）

1. Judge 模型可写评估字段只有一格：

```
impl/core/schema/judge.py
class JudgeFulfillmentAssessmentOutput:
    status: str
```

2. 通用结果对象上，每条期望的判定也只有 `FulfillmentAssessment.status`。
   `authority_tool_call_ids` 是引用，不是第二问答案。

3. 人看见的主表芯片只有一个词：

```
impl/core/schema/table.py
    fulfillment_status: str = ""

impl/core/table_view.py
    return str(judge_summary.get("fulfillment_status") or overall.get("status") or status or "")

impl/frontend/summary.html
    function fulfillmentPill(status){... fulfilled / not_fulfilled / not_evaluable ...}
    function fulfillmentStatus(item){const row=tableRow(item);return row.fulfillment_status || row.status || '';}
```

4. 已经按第一问那一件分行的出口，是 fulfillment_panel 矩阵。每行现在只有一个 Status：

```
impl/core/frontend_view.py `_fulfillment_panel`
    matrix.append({
        expectation_id, expected_outcome, required_capabilities,
        status,   # 来自 assessment.status
        score, blocking, downstream_impact
    })
```

5. live.html / summary.html 的 Judge 徽章、Overall Fulfillment、矩阵 Status 列，读的都是这三个词。
   没有第二问的格子。

## 协议

`spec/alg/fulfilled.md` 第一章：

- 本协议只评第一层：办成了没有。
- 「这类事现在是不是产品已经有的功能」见 product-function.md，不并进本协议三态，也不新增第四态。
- 没办成不区分原因。功能未实现也是没办成，不降级为说不清。
- 职责外 / 完全无关进说不清，不是第二问。

`spec/info-volume.md`：

- 枚举值三层：fulfilled / not_fulfilled / not_evaluable
- judge 只产出 fulfillment，不产第二个判定维度
- 不引入 partial 之类的新枚举

`spec/alg/product-function.md`：

- 和 fulfilled.md 同级，回答另一件事
- 不进入 Judge 产出，不进入结果表词表
- §7.1 给 fulfilled 加第四态 ✗
- §7.2 让 Judge 再填一个新标签 ✗
- §8 以后若要看见，再加派生列；派生列不是 Judge 产出，不进 prompt，不改 fulfilled

注意：product-function.md 正文问的是「这类事」。用户已锁的第二问对象是第一问「这一件」，不得切粗切细。060 Consensus 已写：§3 认种类 / 整案按种类汇总，不得当实现说明书。本轮方案不把对象改成种类表。

## 已锁、本轮不重开

- 058：第二问是读已经写下的能力/职责前缀，不是 Judge 再填
- 060：规范格子 = 矩阵同一行、Status 旁边；不是主表状态芯片的第四种颜色
- 061：打开那一格交章程 §4
- 062–064：不是 NF 补充，不能放进 NE，不能 3 扩 4
- 065：同一轮判定再写一个词不能当宿主
- 066-q2 / 069：开格子在看见层就是多一个结果标签；四个口都不能整句当宿主；打开仍停住

## 本轮新钉的缝

用户现在要的是方案，不是再要一份否决清单。

上一轮把「新增一个 judge 结果的标签」定义成「判定再写一个词」，所以说 B 不能当宿主。
用户问的是：你要开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗？

在现行出口上核对：

| 人现在看见的那一格 | 是什么 |
|---|---|
| 主表「状态」/ fulfillment_status 芯片 | 第一问三个词 |
| 矩阵 Status | 第一问三个词 |
| Judge 徽章 | 第一问三个词 |

若在矩阵同一行、Status 旁边另开一格，看结果的人会多看见一个标签。
这一格出现在 Judge 评估结果上，用户会叫它 judge 结果标签。这个叫法在看见层成立。

它仍然不是：

- JudgeFulfillmentAssessmentOutput.status 的第四个词
- 同一轮 Judge 再写的评估字段
- 只在 not_fulfilled 后面出现的附注
- not_evaluable 的新含义

所以方案句只能是：

```text
新增一个兄妹结果标签，挂在同一条期望的 judge 结果上看见层。
这就是用户说的「新增一个 judge 结果的标签」。
它不是 3 扩 4，不是 NE，不是 NF 附注，也不是判定再写一个 status。
```

打开与否仍交章程 §4。本轮不实现。
