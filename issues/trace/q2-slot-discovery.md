# Discovery — 第二问四个结果口

日期：2026-08-16
章程：issues/charter-q2-slot.md
范围：只读协议和现行出口。不重跑 judge。不改代码。

## 用户点名的四个口

```text
A. 只是 not_fulfilled 的补充
B. 新增一个 judge 结果的标签
C. fulfilled 从 3 态扩到 4 态
D. 放到 not_evaluable 里面
```

两问结构已锁，见章程 §2。本轮不改题面。

## 现行出口（自己读过）

- `spec/alg/fulfilled.md` §1：只看办成了没有；邻协议不并进三态，不新增第四态。
- 同文件 §2.2：没办成不区分原因，含功能未实现。
- 同文件 §2.3：NE = 材料不够判断办没办成；临时态。
- `spec/alg/authority.md` §8.3：能力缺失不强制改状态；实际达成 → fulfilled；不得因功能未实现降 NE。
- `impl/core/authority_gate.py`：职责外强制 NE；能力缺失不得降 NE。
- `impl/core/schema/judge.py`：Judge 可写评估字段只有 status。
- `impl/core/frontend_view.py` `_fulfillment_panel`：矩阵每行一个 status。
- `impl/frontend/summary.html`：主表「状态」、筛选、计数、pill 只吃三词。
- `spec/info-volume.md`：不引入 partial；整体 F 不追失败。
- `spec/alg/product-function.md` §7.1 / §7.2：第四态 ✗；Judge 再填新标签 ✗。

## 已锁、只引用

- 046：不是只有 NF 才有
- 047：不是同一轮 Judge 再填
- 048：不是给 status 加枚举
- 015-A / 015-C：第四态死；用 NE 表达尚未支持死
- 058：第二问是读，不是再开一张嘴
- 060：四层拆开；规范格子在矩阵 Status 旁边
- 061：打开那一格是项目决定

## 本轮起号

062 A / 063 D / 064 C / 065 B
