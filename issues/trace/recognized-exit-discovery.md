# Discovery — recognized-exit

本轮不重跑 judge。只对照用户认得的那一块、协议、现行出口。
主语是用户贴出的那一块，不是「第二问」。

## 用户本轮点名

认得的只有这一块：

```text
只看一件事：用户要的这件事，产品把它立成自己会做的事了没有
对象：仍是第一问那一件
      不得另立类型表
      不得为了更好答第二问，把对象切粗或切细
单位：这件事 × 产品事实
产品事实从哪来：已经裁完的能力/职责判断，及其依据资料
          不是这一次给没给到
          不是库存字段表
          不是「先分成姓名/年/天气」
不看：这一次交付；这一次承不承认 / 尽没尽力；预置类型表
不区分：没立住的技术原因
出口：立住了 / 没立住 / 说不清
```

并问：按 fulfilled 的定位，这块东西是只补 NF，还是新增一个 judge 结果标签，还是 3 扩 4，还是放到 NE，还是别的方式。给方案。不实现。

「不得为了更好答第二问」是这块定义里的禁令，不是承认「第二问」是它的名字。

## 现行出口（人现在看见的字）

1. `impl/core/schema/judge.py`
   - `FulfillmentAssessment.status`：每条期望一格，答的是办成了没有
   - `JudgeFulfillmentAssessmentOutput` 模型可写评估字段只有 `status`
   - `JudgeResult.summary`：基于 fulfillment_assessments 派生的展示摘要

2. `impl/core/schema/table.py`
   - 主表只有 `fulfillment_status`

3. `impl/core/table_view.py`
   - 芯片值 = judge_summary.fulfillment_status / overall.status / 行 status

4. `impl/core/frontend_view.py` `_fulfillment_panel`
   - 矩阵每行只有一个 `status`，来自 `assessment.status`
   - 没有这块东西的出口

5. `impl/frontend/summary.html`
   - `fulfillmentPill` 只认三词
   - `renderFulfillmentMatrix` 列是 Expectation / Expected / Capabilities / Status / Blocking

## 协议

- `fulfilled.md` §1：只评办成了没有；邻题不并进三态，也不新增第四态
- `fulfilled.md` §2.2：没办成不区分原因
- `fulfilled.md` §2.3：说不清答这一次办没办成现在说不准
- `product-function.md` §1：任何一张表、一个标签、一句结论，都不能同时回答两件
- 同文件 §7.2：让 Judge 再填一个新标签 ✗
- 同文件 §8：禁给 fulfilled 加枚举；禁新增一个让 Judge 填的标签；以后若要看见，再加派生列
- `authority.md` §8.3：职责内能力缺失不强制改第一问状态；这一次仍可能 fulfilled
- `info-volume.md`：judge 只产 fulfillment，不引入第二个对错维度

## 已锁内容（本轮用内容，不用外号）

- 040：这件事 × 产品事实；办成了不能自动排除没立住
- 047：同一张嘴兼答几乎一定对齐刚才的办成了没有
- 058：这块东西的计算是读已经裁完的前缀，不是再开一张嘴
- 060：现在不进 JudgeFulfillmentAssessmentOutput；若按同一件分行，现行出口在矩阵行上
- 061：打开 escalate

## 本轮增量

085–088 的方案句以「第二问 / 兄妹」为主语，把方案名写成「新增一个 judge 结果标签」。
用户说认得的只有贴出的那一块，不是「第二问」。
本轮要问：这块东西自己的出口放在哪；「judge 结果标签」是不是它的名字，还是只是一种安放说法。
