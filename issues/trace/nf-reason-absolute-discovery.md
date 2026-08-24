# Discovery — 这块东西是不是 not_fulfilled 的原因说明项

本轮只读，不改判定，不改前端。对照的是：用户贴出的那一块、fulfilled 第一章、authority §8.3、现行原因栏。

## 用户认得的那一块

```text
只看一件事：用户要的这件事，产品把它立成自己会做的事了没有
对象：仍是 fulfilled 那一件
单位：这件事 × 产品事实
不看：这一次交付；这一次承不承认 / 尽没尽力；预置类型表
不区分：没立住的技术原因
出口：立住了 / 没立住 / 说不清
```

主语是这一块。不是「第二问」。

## 现行人能看见的格子

1. 判定嘴：`JudgeFulfillmentAssessmentOutput.status`
   值域：fulfilled / not_fulfilled / not_evaluable
   见 `impl/core/schema/judge.py`

2. 人看见的主词：`fulfillment_status` + `fulfillmentPill(status)`
   见 `impl/core/schema/table.py`、`impl/frontend/summary.html`

3. 同一条期望上的矩阵格：`_fulfillment_panel` 每行只有 `status`
   见 `impl/core/frontend_view.py`

4. 原因栏：`summary_from_fulfillment` → `display_reason` → 评估卡「原因：」
   见 `impl/core/summary.py`、`impl/frontend/summary.html`
   这一栏寄生在 fulfillment 的词上：
   - fulfilled → `fulfilled · N blocking expectations all met`
   - not_fulfilled → `not_fulfilled · blocking=[ids] · ...`
   - not_evaluable → 为什么这一次说不准
   它答的是：刚才那个 fulfillment 词，为什么是这个词。

## 「原因说明项」在现行出口上指什么

不是「只在没办成那一行才给人看」。那是看见时机。

是：住进原因栏，去解释「为什么没办成」。
现行协议已经有这种东西：`fulfilled.md` §2.2 把「功能本身未实现」列成没办成的一种理由。
现行代码也有这种东西：`display_reason`。

## 绝对碰撞（不是口味）

把这块东西放进原因栏，会改掉已锁内容里的哪一项：

1. 单位
   已锁：这件事 × 产品事实，不看这一次交付。
   原因栏：只因这一次被判没办成才存在，答的是这一次失败的原因。
   放进去，单位从「产品事实」改成「这一次失败原因」。

2. 出口
   已锁三态：立住了 / 没立住 / 说不清。
   原因栏没有「立住了」这个第一性出口。
   「立住了」不能当没办成的原因。
   放进去，三态出口被收成「没立住」一个原因值。

3. 不区分技术原因
   已锁：不区分没立住的技术原因。
   原因栏是原因分类处：漏条件 / 改错值 / 功能未实现……
   放进去，这块东西变成原因分类里的一项。

4. 前缀消费顺序
   `authority.md` §8.3：职责内能力缺失先裁完，再看这一次给没给到；
   给到了 → fulfilled；没给到 → not_fulfilled。
   同一份产品事实在选词之前就已经在，而且同时喂给办成了和没办成。
   原因栏发生在选词之后，而且只挂在没办成后面。
   放进去，消费顺序被倒过来。

5. 已锁还能写的组合
   040：办成了，不能自动排除没立住。
   040 碰撞针：漏了姓名 = 没办成 × 立住了；没立住但这回绕过给到了 = 办成了 × 没立住。
   `fulfilled.md` §3 第二步 + §8.3：职责内能力缺失 + 实际达成 → 办成了。
   原因栏写不下「办成了 × 没立住」，也写不下「没办成 × 立住了」。

看见时机（只在没办成那一行才打开）仍停住，不能拿来救原因栏。时机不改身份。

## 其它点名口的绝对碰撞

3 扩 4：第四个词写进 `status`，单位仍是「这一次请求 × 这一次交付」。一块东西两套单位，已锁单位被改掉。

放到 NE：fulfilled 的说不清答「这一次办没办成，现在说不准」；这块东西的说不清答「还不能谈立住」。§8.3 还禁止把职责内能力缺失自动降成 NE。放进去，两种说不清被焊成一个词。

Judge 再写一个结果标签：同一张嘴兼答。047：刚写完办成了，下一句几乎一定对齐成「也立住了」。已锁「产品事实不是这一次给没给到」被改掉。

## 本轮不锁的

打开、对外中文、改不改表。
