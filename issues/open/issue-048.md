# Issue #048: 改口焦虑不能靠 fulfilled 新枚举消掉

**Class**: boundary
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Protocol / 出口形状
**Cases**: 无。本 issue 只比较出口。

## Verifier Discovery

用户本轮的第三句：

> 所以我之前才在考虑是不是应该做成一个新的枚举值

这是把 046 + 047 收成一个出口：既然第二问好像只在失败时有用，又不能让 Judge 事后打自己，就让 Judge 一次写出一个新状态。

这一步会同时踩掉已经锁死的三条。

### 枚举值实际在问哪一句

给 `fulfilled` 加一个值，无论叫「尽力了」「能力外」「现有功能之外」，消费者读到的都还是「状态」这一格。`impl/frontend/summary.html` 现在只有这一格。新值会进：

- `FulfillmentAssessment.status`
- 顶部 Fulfilled / Not Fulfilled 统计
- 「全部达成状态」筛选
- `spec/info-volume.md` 规定的整体三态
- 归因：整体 F 不追失败，整体 NF/NE 才追

`info-volume.md` 原文：

> 值域完全相同，依然是 fulfilled / not_fulfilled / not_evaluable，不引入 partial 之类的新枚举

`fulfilled.md` 开篇：

> 词表沿用 spec/info-volume.md，不新增第四态。

015 Consensus：第四态当场否决，因为一个词仍分不清「需求没满足」还是「能力尽到了」。

### 新枚举会删掉哪一格

用户设想的新值，口语上接近「没办成，但这不是现有功能」。它只覆盖：

```text
没办成 × 没这项功能
```

它盖不住：

| 格子 | 枚举一次说完之后 |
|---|---|
| 没办成 × 有这项功能（王坤林） | 仍是没办成。过严和真没办成又混回去 |
| 办成了 × 有这项功能（金凤） | 仍是办成了。第二问在成功案上继续隐身 |
| 办成了 × 没这项功能（§8.3 明文） | 没有落点。要么改口成没办成，要么假装有功能 |
| 说不清 × 任一 | 继续用说不清装长期缺口，013/015 已死 |

所以新枚举不是「把第二问也给 Judge」。它是「只保留用户此刻最熟的那一格，其余格子删掉」。046 若成立，这里就不得做。

### 「用户现在只能看见 fulfilled」证明的是看见问题

前端原文：表头只有「状态」，筛选只有 fulfilled / not_fulfilled / not_evaluable，统计只有 Fulfilled / Not Fulfilled。

这证明：今天读者只能看见第一问。

这不证明：第二问应该写进第一问的词表。

看见问题的合法出口只有两个，本轮都不许角色代选（章程 §4）：

1. 先不看见。继续只读 fulfilled。第二问留在协议和对照里。
2. 以后另开一列给人看。那一列不是 status 的新值，也不是 Judge 新填的标签。

015 / product-function §8 已经写过第 2 条。用户上一口也说了先别改东西。所以本轮连「放哪一列」都不许画到前端上。

### 对照三种出口

| 出口 | 办成了没有还在不在 | 是不是现有功能还在不在 | 会不会变成改口 |
|---|---|---|---|
| fulfilled 加一个枚举 | 被新值改写 | 只留下失败那一格 | 改口被消灭，两问也被消灭 |
| Judge 再填一个标签 | 还在 | 还在，但同一张嘴会对齐 | 047 已禁 |
| 不进 Judge，需要看见时再派生 | 还在 | 还在，且不回写 status | 不算改口 |

### 可证伪

若存在一个 fulfilled 新枚举值，能同时：

1. 不引入第四态（info-volume / fulfilled 开篇）
2. 不把「没办成 × 有这项功能」和「没办成 × 没这项功能」收成同一个词
3. 不让「办成了」自动消灭「没这项功能」
4. 不让归因按三态走的时候撕开

则本 issue 不成立，应回头考虑枚举。

### 不是什么

- 不是现在批准加派生列
- 不是现在改前端
- 不是给第二问起对外中文名

### 未消元

- 看见与否、放哪一列：章程 §4，交给用户

---

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 7fed62d9178ba6d4
- pid: 14816

### Investigation

只打「要不要给 fulfilled 加枚举值」，不顺手批准看见面：

- `spec/info-volume.md`：细粒度 / 整体值域都是 fulfilled / not_fulfilled / not_evaluable，「不引入 partial 之类的新枚举」；judge 只产 fulfillment；整体 F → 归因 `no_issue`，整体 NF/NE 才追失败。
- `spec/alg/fulfilled.md` 开篇：「词表沿用 spec/info-volume.md，不新增第四态。」
- `spec/alg/product-function.md` §6：「尽力了」只是「没办成 × 没这项功能」的读法，不是状态。
- 同文件 §7.1 / §7.2 / §8：给 fulfilled 加第四态 ✗；让 Judge 再填新标签 ✗；加枚举值的理由写明——一个标签答两件事、和三态冲突、归因按三态走会被打乱、「没办成」的业务含义会被改掉。
- `spec/alg/authority.md` §8.3：能力缺失不靠改 status 词表来表达；F 和 NF 都留着。
- `impl/core/schema/judge.py`：`FulfillmentAssessment.status` / `overall_fulfillment` 仍是一条状态。
- `impl/frontend/summary.html`：统计、筛选、「状态」列只吃三词。新值一旦进 status，会同时进这三处。
- 013 Consensus：禁止用调三态补 Q2。
- 015 Consensus：路径 A「fulfilled 第四态 / partial」已死；活家族是正交、不回写 status、不进 overall。挂在哪、改不改 schema 是项目决策。
- 031 Consensus：本轮不得宣布对外中文，不得把看见/字段走私进 Consensus。
- 046 / 047 本轮若成立：Q2 不依附 NF；Q2 不进同一张嘴。

### Evidence Verification

用户第三句的出口我按「新枚举值进 status」来验，也按更窄的「只在 NF 下出现的原因码」来验。前者直接踩 info-volume / fulfilled 开篇 / 015-A。后者不是第四个 overall 状态，但仍会踩 046、047、§2.2，且满足不了用户「一个词一次说完」的直觉。

verifier 对照表里「新枚举只盖住没办成 × 没这项功能」成立——口语上的新值就是那一格的别名。它盖不住王坤林（NF × 有功能）、金凤（F × 有功能）、§8.3（F × 没功能）。前端只看见 fulfilled，只能证明看见问题，不能证明词表该膨胀。

verifier 把「以后另开一列」写成合法出口之一，方向来自 015 / product-function §8，但本 issue 若把它写进结论，就代选了看见面。这一句我拒收。048 只准判枚举，不准批准列。

### Reasoning

046 + 047 若成立，用户会走到「那让 Judge 一次写出一个新状态」。这一步看起来消掉改口，其实把两问焊回一个词。

**1. 任何改 status 词表的做法，都还在答「状态」这一格。**

新值不论叫「尽力了」「能力外」「现有功能之外」，消费者仍从 `FulfillmentAssessment.status`、顶部计数、「全部达成状态」筛选、info-volume 三态、归因开关去读它。info-volume 写死了值域和「整体 F 不追失败」。少一个 F，或多一个不是 NF 的失败词，归因切口都会撕开：该追的不追，或不该改含义的「没办成」被改掉。015 当场否决第四态，理由就是一个词分不清「需求没满足」还是「能力尽到了」。

**2. 用户想要的那个词，只买到九格里最熟的一格。**

「没办成，但这不是现有功能」= 盘客格。写成 status 新值之后：

| 格子 | 一个词说完之后 |
|---|---|
| 没办成 × 没这项功能 | 被新词吃掉。看起来解决了 |
| 没办成 × 有这项功能 | 仍是没办成。过严和真没办成混回同一个词 |
| 办成了 × 有这项功能 | 仍是办成了。第二问在成功案上继续隐身 |
| 办成了 × 没这项功能（§8.3 / 030） | 没落点。要么改口成没办成，要么假装有功能 |
| 说不清 × 任一 | 继续用说不清装长期缺口（013/015 已死） |

所以新枚举不是「把第二问也给 Judge」。它是「只保留此刻最熟的那一格」。046 若成立，这里不得做。

**3. 更窄的 NF 原因码也救不了「做成一个新的枚举值」。**

攻击问：不新增第四个 overall 状态，只在 NF 下挂一个 reason-code，行不行？

```text
status ∈ {fulfilled, not_fulfilled, not_evaluable}   # 看起来没加第四态
nf_reason 仅当 status=NF 时出现                      # 用户直觉：失败才说
```

这能避开「overall 变成四态」。它仍然非法，而且答非所问：

- 它把门控写进词表：只有 NF 才有第二问。046 已禁。
- 若由 Judge 同一轮填写，是 §7.2 的「新标签」，047 已禁；模型仍会拿它和 status 对齐。
- 它把「没这项功能」收成没办成的原因。fulfilled §2.2 说不区分原因；§8.3 已经允许把理由写在「理由 + 长期优化点」里，不需要新枚举值。
- 消费者一旦拿 `nf_reason=能力缺失` 去跳过归因，就和「功能未实现也是没办成、要长期优化」对着撕。
- 用户要的是「一个状态词一次说完」。原因码不是那个词；若把它抬成筛选/计数用的状态词，它就变回第四态。

因此：不存在一个 fulfilled 新枚举值，能同时（1）不引入第四态（2）不把两格 NF 收成一词（3）不让「办成了」消灭「没这项功能」（4）不撕归因。更窄的 NF 原因码要么不是枚举值（那就离开 048 的题），要么仍塌成两问一句。

**4. 看见问题留在章程 §4，不在本 issue 兑换。**

合法与否的看见面，015 已经写成「正交、不回写 status」。现在看不看、挂哪、叫什么，031 / 章程 §4 交给用户。本轮连「放哪一列」都不许画到结论里。用户上一口也说先别改东西。

## Improvement Proposal

**Problem**: 用 fulfilled 新枚举值消改口焦虑，会删格子、改「没办成」的含义、撕开按三态走的归因。

**Proposed Change**: 只锁出口形状里的否定句。不改 schema，不改前端，不选中文，不批准派生列。

**Design**:

```text
048 锁（只打枚举，不打看见）：

死
- 给 status / overall_fulfillment 增加第四个值（含 partial / 尽力了 / 能力外 / 现有功能之外）
- 用新 status 词替换一部分 not_fulfilled
- 让 Judge 再填一个与 status 并列、用来答第二问的枚举标签（§7.2）
- 把 NF 原因码抬成对外状态词或筛选词

不是 048 的救援
- 只在 NF 下出现的 reason-code：不是第四态，但仍踩 046 / 047 / §2.2
- 「以后另开一列」：015 的活家族方向，不是本轮批准

未决（章程 §4，本 issue 不得代选）
- 现在让不让用户看见第二问
- 看见的话挂哪、叫什么中文
- 现在改不改 schema
```

**Implementation Steps**:

1. Consensus 只收上面的死路径。
2. 删「合法出口 = 另开一列」这种本轮会变成代选的句子；改成「看见面不在 048 裁决」。
3. 不写字段名、列补丁、对外终句。

**Risks**: 把原因码当第四态的变装放行；把 048 写成已经批准派生列；用「用户现在看不见」倒逼改词表。

**Verification**:

```text
# 1. info-volume.md：值域仍是三词，不引入 partial
# 2. fulfilled.md 开篇：不新增第四态
# 3. product-function.md §7.1 / §7.2 / §8：加枚举、加 Judge 标签仍是反面
# 4. 015 Consensus 路径 A 仍死
# 5. 纸面：任何一个新 status 词都无法同时保住
#      NF×有功能、F×有功能、F×没功能、归因三态切口
# 6. Consensus 不得出现字段名 / 列名 / 「本轮采用某某中文」
```

**Why I Cannot Apply It**: 枚举已死，只需锁否定句。看见面和 schema 属章程 §4，只读角色不得代选。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `7fed62d9178ba6d4`

改口焦虑不能靠 fulfilled 新枚举消掉。

收下 architect 的收紧：

死：
- 给 status / 整体判定加第四个值（尽力了 / 能力外 / 现有功能之外 / partial）
- 用新状态词替换一部分「没办成」
- 让 Judge 再填一个用来答第二问的标签
- 把失败原因码抬成对外状态词或筛选词

不是救援：
- 只在没办成下出现的原因码：看起来没加第四态，但仍把第二问收成失败附注，且若由 Judge 填就会对齐
- 「以后另开一列」是看见面方向，不是本轮批准

一个新状态词留不住四件事：现有功能里没办成、现有功能里办成了、办法仍缺但这回给到了、按三态走的归因。用户想一次说完的那一句，只买到「没办成但不是现有功能」最熟的那一格。

看见与否、挂哪、叫什么，仍交章程 §4。本轮不改界面、不加字段。

闸：exit 0，`isolation_valid=true`，`scope_valid=true`。
