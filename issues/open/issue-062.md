# Issue #062: 第二问不是 not_fulfilled 的补充

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 结果口 A / 是否只挂在没办成后面
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户本轮点名的第一句：按 fulfilled 的定位，第二问是不是只是一个 not_fulfilled 的补充。

046 已经否过「只有 NF 才有」。本 issue 不重开那条原则，只钉实现口：若把第二问做成「没办成之后才出现的附注」，第一问自己的定位会被改写。

### 第一问自己怎么定位

`spec/alg/fulfilled.md` §1：

> 我们：评测系统（Judge），只看一件事——系统有没有帮用户办成想办的事。
> 本协议只评第一层：办成了没有。
> 「这类事现在是不是产品已经有的功能」见邻协议，不并进本协议三态。

同文件 §2.2 没办成：

> 不区分原因：
> ……
> 功能本身未实现，但用户期望已提出。

所以「没办成」里面已经含着「功能未实现」。它不负责再分一次「这是不是产品立住的事」。第二问若只在没办成后面开口，就是把 §2.2 禁止区分的原因，重新做成一个可见附注。

### 第二问自己看什么

已锁结构：

```text
第二问不看：这一次交付
第二问单位：这件事 × 产品事实
```

「只在 not_fulfilled 后出现」把单位改成了：

```text
这件事 × 这一次没给到
```

这是第一问的单位，不是第二问的单位。

### 现行出口已经留下「办成了 × 没立住」

`spec/alg/authority.md` §8.3：

```text
statement = 职责内能力缺失
    → 不强制改状态
    期望未达成 → not_fulfilled
    实际达成   → fulfilled
```

`impl/core/authority_gate.py` 同一条：能力缺失不得降成 `not_evaluable`，也不强制改成 `not_fulfilled`。

`spec/alg/product-function.md` §6 九格里有「办成了 × 没这项功能」。

若第二问只是 NF 补充，这格从出口上消失。不是「暂时不显示」，是「按 fulfilled 的定位，这格不该存在」。但 §8.3 明文让它存在。

### 只挂在 NF 后，四个格子会变成什么

| 第一问 × 第二问 | 只当 NF 补充之后 | 踩哪条 |
|---|---|---|
| 没办成 × 没立住 | 看起来解决了。第二问变成失败原因 | fulfilled §2.2 不区分原因 |
| 没办成 × 立住了 | 仍是没办成。过严和真缺口又焊回一个词 | 已锁第二问不看这一次交付 |
| 办成了 × 立住了 | 第二问隐身。成功案不再问产品事实 | product-function §10 能单独回答 |
| 办成了 × 没立住 | 没有落点。要么改口成没办成，要么假装立住了 | authority §8.3；030 Consensus |

「用户现在只能看见 fulfilled」证明的是看见层还没开，不是第二问属于没办成。主表「状态」、筛选、顶部计数吃的都是第一问三个词。少看见一格，不能倒推出第二问是这三个词里某一个的子集。

### 不是什么

- 不是重判投保年 / 姓名 / 天气。
- 不是批准以后在 NF 行画脚注。
- 不是说「没办成的时候常常也能读到没立住」。那是两问对照后的读法，不是宿主关系。

### 可证伪

同时成立才算「只是 NF 补充」：

1. 办成了的行上，第二问不许开口；
2. 没办成的行上，第二问负责解释为什么没办成；
3. §8.3「实际达成 → fulfilled」不再需要单独一格。

现行协议三条都不成立。所以 A 口不能当宿主。

## Proposed Change

Consensus 只锁：第二问不是 not_fulfilled 的补充，也不能做成 NF 后才出现的附注。

不改 schema，不改前端，不宣布对外中文。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: c902435f16f979ab
- pid: 79074

### Investigation
自己重读，不抄 verifier 转述：

- `spec/alg/fulfilled.md` 开篇 + §1 + §2.1 / §2.2 / §2.3：三态只评「办成了没有」；邻协议不并进；不新增第四态。§2.1 办成了必须「职责内」。§2.2 没办成「不区分原因」，明文含「功能本身未实现」，且「不降级为说不清」。
- `spec/alg/authority.md` §8.3：`职责外 → not_evaluable`；`职责内能力缺失 → 不强制改状态`，`期望未达成 → not_fulfilled`，`实际达成 → fulfilled`，且「不能因为功能未实现自动降级为 not_evaluable」。
- `impl/core/authority_gate.py` 213–268：职责外无论原 status 都强制 `not_evaluable`。职责内能力缺失只在当前已是 `not_evaluable` 时改成 `not_fulfilled`；若 Judge 已写 `fulfilled` / `not_fulfilled`，gate 不覆盖。
- `spec/alg/product-function.md` §1 / §6 / §10：两件不能一张表同时答；九格里有「办成了 × 没这项功能」；本协议能单独回答，不需要先看 fulfilled。
- `impl/core/schema/judge.py` 94–104：`JudgeFulfillmentAssessmentOutput` 模型可写评估字段只有 `status`；`authority_tool_call_ids` 是引用。
- `impl/core/frontend_view.py` 61–85：`_fulfillment_panel` 每行只放一个 `status`。
- `impl/frontend/summary.html` 107 / 377 / 426–431 / 552–555 / 766–768：主表「状态」、`fulfillmentPill`、筛选、顶部计数、矩阵 Status 都只吃第一问三词。顶部 `stat-not-fulfilled` 甚至把 `not_evaluable` 一并算进「没办成」计数。
- 已锁 Consensus（只引用）：046（不是 NF 附注）；030（Q1=办成了不得自动写成不得叫；§8.3 允许能力缺失 + 实际达成 → fulfilled）；015-C（用 NE 表达尚未支持已死）；060 / 061（看不见 ≠ 属于没办成；打开另格仍交章程 §4）。

本轮不重判投保年 / 姓名 / 天气，不改 schema / 前端，不宣布对外中文。

### Reasoning
先打本轮点名的攻击，再锁口。

攻击 1：「§2.1 办成了必须职责内，所以没立住永远不能是 F，第二问只在失败后才有意义。」
这是把两件不同的事焊成一件。§2.1 的「职责内」排除的是职责外，不是排除「职责内但还没立成功能」。`authority.md` §8.3 把后者写成 `职责内能力缺失`，并且明文留下 `实际达成 → fulfilled`。030 Consensus 同一句还活着：Q1=办成了不得自动写成不得叫。`authority_gate.py` 248–268 也没有把已是 `fulfilled` 的能力缺失改掉——它只禁止这条前缀停在 `not_evaluable`。所以「没立住 × 办成了」不是想象格，是协议正格。

攻击 2：「职责外已经进了 NE，剩下的第二问不就是 NF 原因吗？」
职责外进 NE，答的是第一问「这一次办成了没有，现在说不准」，不是第二问「产品把这件事立住了没有」。058 已把职责外投影成第二问自己的说不清，且 `product-function.md` §7.6 禁止把职责外写成「没这项功能」。剥掉职责外之后，剩下的也不是一条 NF 原因码：

| 已裁前缀 | 第一问仍可落 | 第二问读的是 |
|---|---|---|
| 职责内正常 | fulfilled / not_fulfilled | 立住了（过严仍是没办成） |
| 职责内能力缺失 | fulfilled / not_fulfilled | 没立住（§8.3 正格仍可办成了） |
| 无前缀 / unresolved | 说不清或按材料走 | 第二问自己的说不清 |

「长尾里没办成 × 没这项功能偏多」是分布，046 已经说过不是定义。§2.2 已经把「功能本身未实现」收进没办成、并禁止再按原因切开。把第二问做成 NF 后才出现的附注，就是把 §2.2 禁止区分的原因重新做成可见脚注，单位从「这件事 × 产品事实」改成「这件事 × 这一次没给到」。

攻击 3：「用户只能看见 fulfilled，所以 NF 脚注是唯一诚实的实现。」
看见层证明的是出口还没有，不是第二问属于没办成。现行嘴只有第一问那三个词：`JudgeFulfillmentAssessmentOutput.status`、主表「状态」、`fulfillmentPill`、筛选、顶部计数、矩阵 Status。061 Consensus 写过：现在看不见 = 出口还没有（≠ 第二问只属于没办成）。少看见一格，不能倒推出宿主是 NF。打开与否仍交章程 §4，本轮不批准在 NF 行画脚注。

可证伪三条现行出口都不成立：办成了的行上第二问按 `product-function.md` §10 仍须能单独开口；没办成的行上第二问不负责解释为什么没办成；§8.3「实际达成 → fulfilled」仍需要单独一格。所以 A 口不能当宿主。

Verifier 有一处出口转述过满：`authority_gate.py` 对能力缺失不是「完全不改状态」，它会把误写成 NE 的能力缺失改成 `not_fulfilled`。这恰好执行「不得降 NE」，并不取消 §8.3 的 F 正格。根因仍是：A 口改写第一问的单位。不接受把对外中文、新字段或前端列偷运进本结论。

### Improvement Proposal
- **Target**: 本 issue 的 Consensus 锁。不得改 `spec/**`、`impl/**`、xlsx、canvas、前端。
- **Change**: 只锁下面三句，不多锁看见面，不宣布对外中文。
  1. 第二问不是 `not_fulfilled` 的补充，也不能做成 NF 后才出现的附注。
  2. `fulfilled.md` §2.1 的「职责内」不消灭 §8.3「能力缺失 + 实际达成 → fulfilled」；那一格继续合法。
  3. 「用户现在只能看见 fulfilled」只证明看见层未开，不证明第二问属于没办成。
- **Verification**: 重读 `fulfilled.md` §1 / §2.2、`authority.md` §8.3、`authority_gate.py` 213–268、`product-function.md` §6 / §10。确认没有新 schema 字段、没有前端脚注、没有对外题面。同一条期望上若只在 NF 后才允许第二问开口，即未达本锁。

---
## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `c902435f16f979ab`

第二问不是 `not_fulfilled` 的补充，也不能做成没办成之后才出现的附注。

收下 architect 的收窄：

- `fulfilled.md` §2.1 的「职责内」排除的是职责外，不是排除「职责内能力缺失」。§8.3「实际达成 → fulfilled」继续合法。
- `authority_gate.py` 对能力缺失不是完全不改状态：它只把误写成 NE 的能力缺失抬回没办成，不删办成了的正格。
- 职责外进 NE，答的是第一问「这一次说不准」，不是第二问属于没办成。
- 「用户现在只能看见 fulfilled」只证明看见层未开，不证明第二问属于没办成。

本轮不改 schema，不改前端，不在 NF 行画脚注，不宣布对外中文。

闸：exit 0，`isolation_valid=true`。`scope_valid=false` 的路径全是 host 写的 `impl/data/context_store/**/judge-*.json`。architect 回应 0 次要改这些文件。按 058–061 惯例豁免，不重开 spawn。wrapper pid 78885 / 回应写 79074，spawn-id 对齐即可。
