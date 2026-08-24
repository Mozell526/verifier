# Issue #047: 「Judge 说了 fulfilled 还会不会改口」把两问收成了一张嘴

**Class**: boundary
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Protocol / 谁答第二问
**Cases**: 无。本 issue 只拆「改口」这个感觉。

## Verifier Discovery

用户本轮的第二句：

> 要做判断的不是你这个 harness AI，而是 judge 吧。judge 如果都判定成 fulfilled 了，他等会还有违逆自己结论吗？

这句有一半是对的：逐案「办成了没有」确实是 Judge 的嘴。错在把第二问也塞进这张嘴里，再问它会不会打自己。

### 现在这张嘴实际产什么

`impl/core/schema/judge.py` 里 Judge 模型可写的评估字段是：

```text
JudgeFulfillmentAssessmentOutput.status
```

`spec/info-volume.md`：

> judge 只产出 fulfillment（细粒度 + 整体两层），不产 verdict。

`impl/frontend/summary.html` 的「状态」列和筛选只吃这条 status。

所以用户看见的那一口，确实是 Judge。Harness / 本轮理事会都不该去改这条 status。这一点接受。

### 「改口」要成立，必须先假定第二问也由这张嘴再答一遍

只有下面这个流程才会出现「违逆自己」：

```text
同一轮 Judge 先写：办成了
同一张嘴稍后写：这类事没这项功能
读者把它听成：刚才说办成了，现在又说办不成
```

这个听法成立的前提是：两句话被当成对同一件事的两次判决。`fulfilled.md` §1 和 `product-function.md` §1 写明它们不是同一件事。

authority §8.3 走的是另一条路：

```text
Authority 先裁：职责内能力缺失
Judge 再看这次给没给到
    没给到 → 没办成
    给到了 → 办成了
```

这里没有「Judge 先说办成了，再回头改口说没功能」。功能这一句若存在，来自另一份材料、另一道裁，而且时间上通常更早。Judge 读到「能力缺失」之后，仍然可以依法写 fulfilled。这不是违逆，是协议要求的组合。

030 Consensus 已经写过计算位置：

> Authority 已裁的 statement 投影，不是评测员重判三类前缀。

`product-function.md` 开篇同一方向：

> 不进入 Judge 产出，不进入结果表词表。
> 以后若要看见，再另定派生列，不另开判定。

### 协议里有一道真缝，用户打中了

`product-function.md` §1 写「三个角色同 fulfilled.md」。
`fulfilled.md` §1 写「我们 = 评测系统（Judge）」。
同文件又写「不进入 Judge 产出」。

用户说「判断的是 Judge 不是 harness」，打的就是这道缝。必须收紧，不能装没看见：

```text
同一套评测立场（用户 / 业务系统 / 我们）
  ≠ 同一轮 Judge 补全里的同一张嘴

「我们」= 评测系统整体
  办成了没有     → 这一案的 Judge 出口
  是不是现有功能 → 产品自己认账的材料 / Authority 已裁事实的投影
```

Harness AI 不得事后改 Judge 的 fulfilled。
Judge 也不得再填一个标签来答第二问。`product-function.md` §7.2 已禁。

原因不是「第二问不重要」，是：同一张嘴兼答两问，模型会把两句对齐。刚写了办成了，下一句就倾向写成有这项功能；刚写了没这项功能，下一句就倾向改成没办成。用户担心的「不会违逆自己」，在同一张嘴里几乎一定发生——那是对齐，不是真理。

### 对照

| 谁答 | 办成了之后出现「没这项功能」 | 算不算改口 |
|---|---|---|
| 同一轮 Judge 再填一格 | 读者会听成改口；模型也会自己对齐 | 会。所以禁止 |
| 给 fulfilled 加一个新枚举，让同一张嘴一次说完 | 改口被消灭，格子也被消灭 | 见 048 |
| Authority / 产品认账材料投影，不回写 status | 另一问的另一份答案 | 不算。Judge 的 fulfilled 原句不动 |

### 可证伪

若能证明第二问必须由 `JudgeFulfillmentAssessmentOutput.status` 的同一轮补全来答，且不违反 product-function §7.2「不让 Judge 再填新标签」、也不把两问收成一句，则本 issue 不成立。

若能证明「我们 = Judge」只能读成「第二问也是 Judge 逐案出口」，则必须改 product-function 开篇，而不是把第二问并进 fulfilled。本轮不改协议正文，只把这道缝标出来。

### 不是什么

- 不是说 harness 可以改判
- 不是说现在就要在前端加一列
- 不是重开「第二问问的是哪一句中文」

### 未消元

- 用户现在只能看见 fulfilled，那是不是迫使做成枚举：见 048

---

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 7fed62d9178ba6d4
- pid: 14816

### Investigation

自己重读了所有权缝，不把「所以第二问归 Authority」当成已经证完：

- `spec/alg/fulfilled.md` §1：「我们：评测系统（Judge），只看一件事——系统有没有帮用户办成想办的事。」紧接着把产品功能指到邻协议，不并进三态。
- `spec/alg/product-function.md` §1 第一句：「三个角色同 fulfilled.md。」同节立刻写「本协议只看另一件事」，并禁止一张表/一个标签/一句结论同时答两件。
- 同文件开篇 / §7.2 / §8：不进入 Judge 产出；「让 Judge 再填一个新标签」永远不许；派生列若以后有，也不是 Judge 产出、不进 prompt、不改 fulfilled。
- `spec/alg/authority.md` §8.2：Authority 不裁「本次输出是否达标」。
- 同文件 §8.3：能力缺失不强制改状态；Judge 仍按这次交付写 F 或 NF。时间顺序是 Authority 先裁能力，Judge 再写 status。
- `spec/info-volume.md`：「judge 只产出 fulfillment（细粒度 + 整体两层），不产 verdict。」
- `impl/core/schema/judge.py`：`JudgeFulfillmentAssessmentOutput` 只有一条 `status`；`JudgeLLMOutput` 没有第二问字段。`FulfillmentAssessment.status` 同样单值。
- `impl/frontend/summary.html`：可见「状态」列、筛选、Fulfilled/Not Fulfilled 统计只吃三态。
- 013 Consensus：产品轴从来不是 Judge 的题；已有字段（`blocking` / `required_capabilities` / `authority_tool_call_ids`）都发布不了 Q2。
- 015 Consensus：若有 Q2，只能与三态正交、不回写 `status`、不进 overall。
- 030 Consensus：计算位置 = Authority 已裁 statement 的投影，不是评测员重判三类前缀。
- 031 Consensus：看见与否、叫什么中文、改不改 schema，交给用户。

### Evidence Verification

用户后半句的机制前提我复算过：只有「同一张嘴先写办成了、再写没功能」才会听成改口。协议里的合法顺序正好反着：Authority / 产品认账材料先裁「这类办法缺不缺」，Judge 再按这次交付写 fulfilled。§8.3 要的就是 Judge 读到「能力缺失」之后**仍可以**写 F。这不是违逆，是分工。

「三个角色同 fulfilled.md」+「我们 = Judge」是真缝，用户打中了。但它推不出「第二问也必须由 `JudgeFulfillmentAssessmentOutput.status` 的同一轮补全来答」。同一份 `product-function.md` 若那样读，开篇和 §7.2 会当场自杀。一致读法是：三个角色是评测立场（用户 / 业务系统 / 我们），不是同一轮 LLM 补全的同一张嘴。

「用户现在只能看见 fulfilled」我核对过前端，是事实。它证明看见面，不证明所有权。本轮不得把它兑换成「所以并进 Judge」。

### Reasoning

用户第二句有一半必须收下：逐案「办成了没有」是 Judge 的嘴。Harness / 理事会不得事后改 `status`。错在下一跳——把第二问也塞进这张嘴，再问它会不会打自己。

**1. 「我们 = Judge」不强制第二问归 status 那张嘴。**

fulfilled.md 把「我们」写成评测系统（Judge），但立刻加上「只看一件事」。product-function.md 抄三个角色，是抄立场，不是抄出口。它自己的题是另一件事，而且写明不进入 Judge 产出。若「我们 = Judge」只能读成「第二问也是逐案 Judge 补全」，要改的是 product-function 开篇的指称，不是把第二问并进 fulfilled。本轮红线不改协议正文，只把缝标出来：

```text
评测立场上的「我们」
  ≠ JudgeFulfillmentAssessmentOutput.status 那一张嘴

Q1 办成了没有     → 这一案的 Judge 出口
Q2 是不是现有功能 → 产品认账材料 / Authority 已裁事实的投影（030）
```

**2. 「Harness 不得改写 fulfilled」是 Q1 的护栏，不是把 Q2 塞进 Judge 的理由。**

用户担心的是 harness AI 在 Judge 说完 F 之后再判一次。这个担心对 Q1 成立。答案是：谁答 Q2，都不许回写 `status`。把 Q2 放进同一轮 Judge，看起来像「让真正的裁判来说」，实际是让同一张嘴兼答两问。product-function §7.2 / §8 禁这个，原因写得很具体：两问会抢解释权，会长尾过拟合。用户怕的「不会违逆自己」，在同一张嘴里几乎一定发生——那是对齐，不是真理。所以「判断的是 Judge 不是 harness」推不出「第二问也要 Judge 再填一格」；它只推出「不要让 harness 改 Q1」。

**3. 看不见 ≠ 没有这份答案。**

今天读者只能看见第一问，015 / 031 / 章程 §4 已经承认这是看见问题。非 Judge 出口在结果表上暂时是蒸汽，在协议里不是：030 已经给出计算位置，product-function §8–§9 把它留在对照阅读。蒸汽要不要变成一列，本轮不许代选。更不许为了「现在能看见」把第二问写进唯一可见的那一个词。

**4. 时间顺序也不支持「后来改口」。**

§8.3 不是 Judge 先 F、再回头改成没功能。是能力句先在，status 后写。读者若把两句听成对同一件事的两次判决，错在听法，不在 Judge 违逆。fulfilled §1 和 product-function §1 已经写明不是同一件事。

可证伪两条仍立：证明第二问必须由同一轮 `status` 补全来答，且不踩 §7.2、不收成一句——做不到。证明「我们 = Judge」只能读成逐案第二问出口——那是开篇指称问题，不是并进枚举的理由。

## Improvement Proposal

**Problem**: 「Judge 写了 fulfilled 还会不会改口」把两问收成同一张嘴；缝在「我们 = Judge」的指称，不在「所以第二问要进 status」。

**Proposed Change**: 锁嘴的分工。不改协议正文，不加 Judge 字段，不改前端。

**Design**:

```text
047 锁（谁开口，不是看见面）：

- Q1 的唯一逐案嘴：JudgeFulfillmentAssessmentOutput.status
  Harness / 理事会 / 派生阅读都不得改写它。
- Q2 的计算位置维持 030：
  Authority §8.3 已裁 statement 的投影，或产品自己认账的材料；
  不是评测员重判三类前缀，也不是同一轮 Judge 再填一格。
- 「三个角色同 fulfilled.md」= 同一套评测立场，≠ 同一张补全嘴。
- 同一轮 Judge 再填标签：禁止（product-function §7.2）。
  禁止的原因正是用户担心的对齐 / 改口。
- 「现在只能看见 fulfilled」不得兑换成：
    第二问并进 status / 第二问改由 Judge 填 / 现在加一列。

本轮只标缝，不改 product-function.md 开篇。
```

**Implementation Steps**:

1. Consensus 收嘴的分工，保留「我们 = Judge」是立场缝、不是所有权证明。
2. 删任何「为了不让 harness 裁判，所以第二问进 Judge」的推理。
3. 不写列名、字段名、对外中文。

**Risks**: 把 Authority 三类前缀重新公开成对外三值（024 已死）；把「投影」听成 harness 改判；把看不见当成「所以必须进唯一可见词」。

**Verification**:

```text
# 1. schema/judge.py：JudgeFulfillmentAssessmentOutput 仍只有 status
# 2. product-function.md §7.2：Judge 新标签仍是反面情况
# 3. 030：计算位置仍是已裁 statement 投影
# 4. Consensus 不得要求本轮改协议开篇，也不得批准前端列
# 5. 纸面：Authority=能力缺失 且 Judge=fulfilled —— 按 §8.3 合法，不得叫改口
```

**Why I Cannot Apply It**: 开篇指称若要改字，属于协议正文，本轮红线禁止；看见面属章程 §4。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `7fed62d9178ba6d4`

「Judge 说了办成了，还会不会改口」把两问收成了一张嘴。这个感觉本身，是反对让 Judge 兼答的证据，不是支持加枚举的证据。

收下 architect 的收紧：

- 逐案「办成了没有」只有一张嘴：Judge 的 status。Harness / 理事会不得改写它。
- 第二问的计算位置维持 030：产品自己认账的材料 / Authority 已裁事实的投影。不是同一轮 Judge 再填一格，也不是评测员重判三类前缀。
- 「三个角色同 fulfilled.md」抄的是评测立场，不是同一张补全嘴。开篇「我们 = Judge」是指称缝，本轮只标出，不改协议正文。
- 同一张嘴兼答两问，几乎一定会对齐刚才的结论。用户担心的「不会违逆自己」，在同一张嘴里几乎一定发生——那是对齐，不是真理。
- 「现在只能看见 fulfilled」是看见问题，不得兑换成：第二问并进 status / 改由 Judge 填 / 本轮加一列。

闸：exit 0，`isolation_valid=true`，`scope_valid=true`。
