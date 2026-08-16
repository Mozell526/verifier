# Discovery — 对象覆盖原则 vs 整句覆盖门

Script: `issues/trace/simulate_1a_principle_program.py`
Dump: `issues/trace/simulate_1a_principle_program.json`
SHA-256: `0205668a62c18e516a12d973e3273988235a02b6caafaf9a9807341548d95367`

Does not overwrite `simulate_1a_coverage_program.py`. Frozen traces reused. No LLM rerun.

## Columns

| col | status | mixed agree/47 | set A F/NF | set A flips |
|---|---|---|---|---|
| current | baseline | 36 | 213/128 | — |
| wide | negative | 27 | 238/103 | lift 25 including 共展/豆芽/昊轩/红莲保单 |
| surname | negative | 35 | 210/131 | lift 王坤林+家办客户; drop 5 保单号 |
| role | rejected machine | 41 | 215/126 | lift 王坤林+红莲保单 |
| live_identity | local floor / negative | 41 | 214/127 | lift **only** 王坤林 |
| object_cover | candidate | 41 | 214/127 | lift **only** 王坤林 |

冻结集 A、混合包上：`object_cover` 与 `live_identity` **零行差异**。
本轮不把 41/47 或「只抬王坤林」写成胜利。

## Candidate

`decide_object_cover`：先把 live 值对齐成问句里的连续跨度，再看残句，再看对象类型。

- 残句非空 → inherit
- 残句空但没有姓名 / 单号字段 → inherit（I129「综拓潜客」）
- 残句空且有姓名，但不过 1A 姓氏门 → inherit（共展 / 豆芽 / 昊轩）
- 残句空且有身份对象、姓名若出现则过 1A 门 → overlay F
- 从不 overlay NF

不读混合包 `role`。不剥「的 / 查一下 / 保单号」。

## 和整句覆盖门的关系

`exit_live_identity` = 本原则在「恰好一个字段且值=整句」时的特例。
冻结痕迹里，混合包 0 条多字段；集 A 多字段残句为空的身份题是 0 条。
所以冻结分数撞车，是数据没刷出特例之外的题，不是原则坍缩回整句相等。

真正多出来的点只在合成探针：

| probe | object_cover | live_identity |
|---|---|---|
| 李明重疾险 + 姓名+产品 | overlay F | inherit |
| 两个单号连写 | overlay F | inherit |
| 李明的重疾险（还有「的」） | inherit | inherit |
| 红莲保单 | inherit | inherit |
| 综拓潜客 | inherit | inherit |
| 共展 | inherit | inherit |

15 条合成探针全部按原则文档落点。`synthetics_all_ok=true`。

## Overlay vs inherit（混合 48）

object_cover / live_identity 都是 15 overlay / 33 inherit。

主动 overlay 15：12 条整句真名 + HB015–017 整句单号。

inherit 的原因分列（混合）：

| reason | n | 例子 |
|---|---|---|
| name_not_ok | 16 | 共展 / 豆芽 / 昊轩 |
| residual_nonempty | 10 | 张忠波保单号 / 查金风 / 找一下客户号… |
| no_live | 3 | 家办客户、部分姓名+产品空 live |
| not_grounded | 3 | 值对不上原文 |
| overlay_f_name | 12 | 杨杰 / 王坤林 / HB001–008 |
| overlay_f_id | 3 | HB015–017 |
| no_identity_field | 1 | 金凤（产品字段） |

## 业务单元格

杨杰 = 王坤林 = 成功。共展 / 豆芽 inherit 失败。金凤 inherit（产品字段，不走姓名出口）。盘客 inherit 失败。昊轩 inherit，未代选。HB009–014 inherit 失败，没有从问句补姓名。

## 冻结分数撞车必须怎么读

不是「新原则已经在 341 上证明更强」。
是：「何时不许出手」被写成了全函数，冻结数据还走不出单字段整句这条老路。
