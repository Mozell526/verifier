# Discovery — 开格子是不是新增一个结果标签

日期：2026-08-16
章程：issues/charter-q2-label-honesty.md
范围：只读协议和现行出口。不重跑 judge。不改代码。

## 用户本轮打的一句

> 你要开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗？

并要在这句话成立或不成立之后，重新安放：

```text
A. 只是 not_fulfilled 的补充
B. 新增一个 judge 结果的标签
C. fulfilled 从 3 态扩到 4 态
D. 放到 not_evaluable 里面
```

两问结构已锁，见章程 §2。本轮不改题面。065「B 口不能叫标签」可以打。006–064 不重开其对错。

章程要求分开答、不得再焊回一句：

```text
人看见的：结果上是不是多了一格字
谁写下的：是不是同一张嘴再判一次
进哪张嘴：是不是改写办成了 / 没办成 / 说不清
```

## 现行出口（自己读过）

- `spec/alg/fulfilled.md` §1：只看办成了没有；邻协议不并进三态，不新增第四态。
- 同文件 §2.2：没办成不区分原因，含功能未实现。
- 同文件 §2.3：NE = 材料不够判断办没办成；临时态。
- `spec/alg/authority.md` §8.3：能力缺失不强制改状态；实际达成 → fulfilled；不得因功能未实现降 NE。
- `impl/core/authority_gate.py` 213–268：职责外强制 NE；能力缺失只把误写 NE 抬回 NF，不覆盖已有 F。
- `impl/core/schema/judge.py` 94–104：Judge 可写评估字段只有 status。
- `impl/core/frontend_view.py` `_fulfillment_panel`：矩阵每行一个 status。
- `impl/frontend/summary.html`：主表「状态」、`fulfillmentPill`、筛选、`stat-not-fulfilled`、`renderFulfillmentMatrix` 的 Status 列只吃第一问三个词。
- `spec/info-volume.md`：不引入 partial；judge 只产出 fulfillment。
- `spec/alg/product-function.md` §7.1 / §7.2 / §8：第四态 ✗；Judge 再填新标签 ✗；以后若看见再加派生列，派生列不是 Judge 产出。

## 已锁、只引用

- 046：不是只有 NF 才有
- 047：不是同一轮 Judge 再填
- 048：不是给 status 加枚举
- 015-A / 015-C：第四态死；用 NE 表达尚未支持死
- 058：第二问是读，不是再开一张嘴
- 060：四层拆开；规范格子在矩阵 Status 旁边
- 061：打开那一格是项目决定
- 062 / 063 / 064：A / D / C 不能当宿主
- 065：判定再写一个词不能当宿主。本轮可打的是它「不能叫标签」那一句

## 本轮起号

070 看见层诚实 / 071 不复活 A/C/D / 072 看见≠判定再填 / 073 全局安放

066 已被并行章程 charter-judge-agent-t4.md 占用。067–069 初稿已迁到 071–073，避免 T4 续写覆盖。
