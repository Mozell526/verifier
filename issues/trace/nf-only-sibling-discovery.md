# Discovery — 产品功能是不是只有 NF 才有

时间：2026-08-16
章程：`issues/charter-nf-only-sibling.md`
范围：只读协议 / 前端看见面 / 0814 投影。不跑 judge，不改代码。

## 用户原话（本轮要打的点）

> 我理解不是只有 not fulfilled 才有这个东西吗？因为要做判断的不是你这个 harness AI，而是 judge 吧。judge 如果都判定成 fulfilled 了，他等会还有违逆自己结论吗？（所以我之前才在考虑是不是应该做成一个新的枚举值）

拆成三个可证伪问题：

1. 产品功能是否逻辑上只依附 `not_fulfilled`？
2. 若 Judge 已写 `fulfilled`，再出现「没这项功能」算不算同一张嘴改口？
3. 这个感觉是否迫使 fulfilled 增加枚举值？

## 读过的原文

- `spec/alg/fulfilled.md` §1：我们 = 评测系统（Judge），只看一件事。开篇不新增第四态。§2.2 没办成不区分原因，含「功能本身未实现」。
- `spec/alg/product-function.md` §1：三个角色同 fulfilled.md；任何一张表、一个标签、一句结论都不能同时回答两件。§6 明确有「办成了 × 没这项功能」。§7.1 / §7.2 禁止第四态、禁止 Judge 再填新标签。§8 派生列不是 Judge 产出。
- `spec/alg/authority.md` §8.3：`职责内能力缺失` 不强制改状态；期望未达成 → NF；**实际达成 → fulfilled**。
- `spec/info-volume.md`：整体三态不引入 partial；judge 只产 fulfillment；整体 F 则归因不追失败。
- `impl/core/schema/judge.py`：`FulfillmentAssessment.status` 只有一条 status；`JudgeLLMOutput` 没有第二问字段。
- `impl/frontend/summary.html`：用户可见「状态」列和筛选只吃 fulfilled / not_fulfilled / not_evaluable。
- 投影 `spec/patch/20260814/product-function-projection-0814.md`：I161 写成「办成了 × 没这项功能」；同时承认这是口径裂缝，不是新标签。
- canvas I046 vs I161：同一类「去年」投保日，新判定一边 NF 一边 F。

## 最强反例（必须让对手打）

1. I161 的 F 可能本身是 fulfilled 口径虫，不是合法格子。若所有「办成了 × 没这项功能」都是 Judge 判错，则正确 Judge 下第二问在 F 上只剩确认项。
2. `product-function.md` 写「三个角色同 fulfilled.md」，fulfilled 里「我们」= Judge；同文件又写「不进入 Judge 产出」。用户说「判断的是 Judge」正好打在这道缝上。
3. 前端只看见 fulfilled。若第二问不进 Judge，用户现在确实看不见。这不能偷换成「所以并进枚举」。

## 不在本轮做的

- 不改前端、不改 schema、不重判 I046/I161、不代选看见与否。
