# Issue #090: 这块东西盖不住时，不能塞进 fulfilled 的三个词

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 安放 / 不是 NF 补充、不是 3 扩 4、不是 NE
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

本号不叫它第二问。只问：用户认得的这一块，能不能住进 fulfilled 现在的三个词。

这块东西的单位是「这件事 × 产品事实」，不看这一次交付。fulfilled 的单位是「这一次请求 × 这一次交付」，不看产品立住了没有。两套单位对不上，一个词答不了两套。

`fulfilled.md` §1：本协议只评办成了没有；邻题不并进三态，也不新增第四态。
`fulfilled.md` §2.2：没办成不区分原因。
`fulfilled.md` §2.3：说不清答的是这一次办没办成，现在说不准。
`product-function.md` §1：任何一张表、一个标签、一句结论，都不能同时回答两件。
`authority.md` §8.3：职责内能力缺失时，不强制改状态；这一次仍可能 fulfilled。
040 第 4 条：办成了，不能自动排除没立住。

三个点名口各自塌在哪：

只补 not_fulfilled：
  这块东西在「办成了」时仍可能是没立住。只挂在没办成后面，这格会消失。
  人现在只看见 fulfilled，不能兑换成：这块东西只在没办成里才有意义。

3 扩 4：
  第四个词若写进 `status`，嘴还是 fulfilled 的嘴。
  `info-volume.md`：值域只有三个词；judge 只产 fulfillment。
  主表芯片 / `fulfillmentPill` 现在只认三词，只证明这块东西还没有自己的出口，不证明它该挤进这三个词。

放到 not_evaluable：
  fulfilled 的说不清答「这一次办没办成，现在说不准」。
  这块东西的说不清答「还不能谈立住」。
  两种说不清不是同一个出口。

这些塌法从这块东西自己的单位推，不从「它是第二问」推。

### 可证伪

同时成立才算本 issue 站住：

1. 只补 NF / 3 扩 4 / 放进 NE，整句都不能当宿主；
2. 论证不得依赖「因为这是第二问」；
3. 「办成了 × 没立住」还得能写，依据是 040 + authority §8.3 + 这块东西不看这一次交付，不是 fulfilled 自己要第四态。

若另找理由把这块东西写进三个词，本 issue 失败。

## Proposed Change

Consensus 只锁：这块东西的出口不是 fulfilled 的三个词，也不是只挂在没办成后面。

## Evidence（本轮对照，不是新主张）

这块东西的单位是「这件事 × 产品事实」。fulfilled 的单位是「这一次请求 × 这一次交付」（040）。单位不同，不能共用一个词。

**不是只补 not_fulfilled**

- 040 第 4 条：第一问办成了，不能自动排除「没立住」。
- `authority.md` §8.3：`职责内能力缺失` → 不强制改状态；实际达成 → fulfilled。
  所以「办成了 × 没立住」必须还能写。只在 NF 后出现，这一格会消失。
- `fulfilled.md` §2.2：没办成不区分原因。把这块东西做成 NF 的附注，等于用原因去改没办成。

**不是 fulfilled 3 扩 4**

- `fulfilled.md` 文首 + §1：词表沿用 `spec/info-volume.md`，不新增第四态。
- `info-volume.md`：细粒度 / 整体值域都是 fulfilled / not_fulfilled / not_evaluable，不引入新枚举。
- `product-function.md` §7.1：给 fulfilled 加第四态 ✗。
- 第四个词若写进 `JudgeFulfillmentAssessmentOutput.status`，仍是同一张嘴。047：同一张嘴兼答，几乎一定对齐刚才的办成了没有。

**不是放到 not_evaluable**

- `fulfilled.md` §2.3：说不清答「该给个说法，但材料不够，无法确定办没办成」。
- 这块东西自己的说不清答「还不能谈立住」（040）。两种说不清不是同一个出口。
- `authority.md` §8.3：职责内能力缺失不能因为「功能未实现」自动降级为 not_evaluable。
  「没立住」若塞进 NE，会把已经裁完的产品事实改写成「这一次说不准」。

现行出口也只有这三个词：

- `impl/core/schema/judge.py`：`FulfillmentAssessment.status` / `JudgeFulfillmentAssessmentOutput.status` 是模型可写评估字段里唯一的状态字
- `impl/core/frontend_view.py` `_fulfillment_panel`：矩阵每行只有一个 `status`，来自 assessment.status
- `impl/frontend/summary.html` `fulfillmentPill`：只认 fulfilled / not_fulfilled / not_evaluable

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 44e93555a7a3fdcb
- pid: 79817

### Investigation

自己对了这块东西的单位、fulfilled 的单位、三个点名口的原文：

- 用户认得的那一块：单位是「这件事 × 产品事实」；不看这一次交付；出口是立住了 / 没立住 / 说不清
- `spec/alg/fulfilled.md` §1 L23-L30：只评办成了没有；邻题不并进三态，也不新增第四态
- 同文件 §2.2 L42-L52：没办成不区分原因；「功能本身未实现」也只是没办成
- 同文件 §2.3 L54-L73：说不清答的是这一次办没办成、现在说不准
- `spec/alg/product-function.md` §1 L31-L39：任何一张表、一个标签、一句结论，都不能同时回答两件
- 同文件 §7 L170-L172、§8 L188-L198：给 fulfilled 加第四态 ✗；新增一个让 Judge 填的标签 ✗；以后若看见，再加派生列
- `spec/alg/authority.md` §8.3 L499-L503：职责内能力缺失不强制改状态；实际达成仍可以是 fulfilled
- `spec/info-volume.md` L260-L277：值域只有三词；judge 只产 fulfillment，不引入第二个对错维度
- 040 Consensus 第 4 条：办成了，不能自动排除没立住
- 现行出口：`JudgeFulfillmentAssessmentOutput.status`（`impl/core/schema/judge.py` L94-L103）是模型可写评估字段里唯一的状态字；`TraceTableRow.fulfillment_status`（`impl/core/schema/table.py` L36）；`fulfillmentPill`（`impl/frontend/summary.html` L377）只认三词；矩阵 Status 来自 `assessment.status`（`impl/core/frontend_view.py` L77）

未用「因为这是第二问」推这三个口。未把 086 的「兄妹标签」当成本号身份。

### Reasoning

三个点名口各自塌在单位，不塌在外号。丢掉「第二问」之后，它们仍然不能当宿主。若有人说「既然不叫第二问，也许可以塞回三个词」，那是本轮要打的偷换，不是出路。

1. **两套单位对不上。** fulfilled 的单位是「这一次请求 × 这一次交付」，不看产品立住了没有。这块东西的单位是「这件事 × 产品事实」，不看这一次给没给到。`product-function.md` §1：一个词不能同时答两件。这不是「兄妹问所以不能共用」，是两套单位本身共用不了。

2. **只补 not_fulfilled：办成了时这格会消失。** `authority.md` §8.3 写明职责内能力缺失不强制改状态，实际达成仍可以 fulfilled。040 第 4 条把「办成了 × 没立住」写成必须能写的一格。只挂在没办成后面，等于宣布这块东西只在失败后才有意义。人现在只看见 fulfilled，不能兑换成「它只属于没办成」。`fulfilled.md` §2.2 还禁止没办成再按原因开口；把它当 NF 附注，会把「没立住」收成失败原因码。

3. **3 扩 4：第四个词若写进 `status`，嘴还是 fulfilled 的嘴。** `fulfilled.md` §1 已经禁止邻题并进、禁止第四态。`info-volume.md` 值域只有三词。主表芯片 / `fulfillmentPill` 只认三词，只证明这块东西还没有自己的出口，不证明它该挤进这三个词。挤进去以后，「办成了」和「立住了」仍会抢同一格；`authority.md` §8.3 允许的交叉格会消失。

4. **放到 not_evaluable：两种说不清不是同一个出口。** fulfilled 的说不清答「这一次办没办成，现在说不准」。这块东西的说不清答「还不能谈立住」（职责外 / 对象未成形 / 依据不充分）。职责内能力缺失在这块东西上是「没立住」，在 fulfilled 上偏偏不是 NE。塞进 NE，不是把说不清合并，是把「没立住」和「这一次说不准」焊死。

5. **这些塌法不依赖「它是第二问」。** 依据是这块东西自己的单位 + 040 第 4 条 + `authority.md` §8.3 + `fulfilled.md` §1 / §2.2 / §2.3 + `product-function.md` §1。086 用「兄妹标签」说过同一句死法；本号重说时不得把那句身份借回来。

不整号 escalate：三个口能不能当宿主，本号就能锁死。打开与否仍交 061。

### Improvement Proposal

**Problem**: 这块东西的出口若写进 fulfilled 的三个词，或只挂在没办成后面，单位会塌，交叉格也会丢。

**Proposed Change**: Consensus 只锁「不是这三个口」。不发明字段，不批准打开。

**Design**:

    这块东西的出口不是 fulfilled 的三个词，也不是只挂在没办成后面。

    死：
      只给 not_fulfilled 作补充
      fulfilled 从 3 态扩到 4 态（第四个词写进 status / fulfillment_status / overall）
      放到 not_evaluable 里

    「办成了 × 没立住」还得能写。
    依据：040 第 4 条 + authority.md §8.3 + 这块东西不看这一次交付。
    不是 fulfilled 自己要第四态。

    论证不得写成「因为这是第二问」。
    也不得写成「不叫第二问了，所以可以塞回三个词」。

**Implementation Steps**:
1. Consensus 采用上面三口死亡证明。
2. 092 的方案句必须以这块东西为主语另开出口，不得再从这三个口里捡一个回来。
3. 不改 `status` 枚举，不改 `fulfillmentPill`，不改协议正文。

**Risks**: 把「芯片只认三词」误读成「所以必须扩成四词」。那是看见层还没开，不是值域许可。

**Verification**: 本号 Consensus 必须同时勾上：(1) NF-only / 3扩4 / NE 整句都不能当宿主；(2) 没有「因为这是第二问」；(3) 「办成了 × 没立住」仍能写。

**Why I Cannot Apply It**: 只读 peer；本号只锁「不是哪三个口」，实现仍停。

### What I Changed

- `issues/open/issue-090.md`: append-only Architect Response #1

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 8481552ab6d86f98
- pid: 85394

### Investigation

r2。不续写 spawn `44e93555a7a3fdcb`。自己对了两套单位和三个点名口的原文。

- 用户贴出的那一块：单位「这件事 × 产品事实」；不看这一次交付；出口立住了 / 没立住 / 说不清。
- `spec/alg/fulfilled.md` §1 L28–L30：只评办成了没有；不并进，不加第四态。
- 同文件 §2.2 L42–L52：没办成不区分原因；「功能本身未实现」也只是没办成。
- 同文件 §2.3 L54–L56：说不清答「该给个说法，但材料不够，无法确定办没办成」。
- `spec/alg/product-function.md` §1 L38–L39：一张表 / 一个标签 / 一句结论不能同时答两件。
- 同文件 §7.1 L170：给 fulfilled 加第四态 ✗。§8 L188–L198：不加枚举；不加让 Judge 填的新标签；以后若看见，再加派生列。
- `spec/alg/authority.md` §8.3 L499–L503：职责内能力缺失不强制改状态；实际达成 → fulfilled；不能因为「功能未实现」自动降级为 not_evaluable。
- `spec/info-volume.md` L260–L277：细粒度 / 整体值域都是三词；judge 只产 fulfillment，不引入第二个对错维度。
- 040 Consensus 第 4 条：办成了，不能自动排除没立住。
- 现行出口：`JudgeFulfillmentAssessmentOutput.status`（`judge.py` L97）是模型可写评估字段里唯一的状态字；`table.py` L36 `fulfillment_status`；`frontend_view.py` L77 矩阵行只有一个 `status`；`summary.html` L377 `fulfillmentPill` 只认三词。

论证没有写成「因为这是第二问」。

### Reasoning

三个点名口塌在单位，不塌在外号。丢掉「第二问」之后，它们仍然不能当宿主。若有人说「既然不叫第二问，也许可以塞回三个词 / 只补 NF / 放进 NE / 让 Judge 再填」，那是本轮要打的偷换。

1. **单位对不上。** fulfilled 是「这一次请求 × 这一次交付」。这块东西是「这件事 × 产品事实」，不看这一次给没给到。一个词答不了两套。
2. **只补 not_fulfilled。** §8.3 + 040 第 4 条要求「办成了 × 没立住」还能写。只挂在没办成后面，办成了时这格消失。§2.2 还禁止把没办成再按原因开口。
3. **3 扩 4。** 第四个词若写进 `status` / `fulfillment_status` / overall，嘴还是 fulfilled 的嘴。芯片只认三词，只证明出口还没有，不证明该挤进去。
4. **放到 NE。** fulfilled 的说不清是「这一次办没办成，现在说不准」。这块东西的说不清是「还不能谈立住」。职责内能力缺失在这边是没立住，在 fulfilled 上偏偏不是 NE。焊进 NE，是把已经裁完的产品事实改写成这一次说不准。

这些塌法从这块东西自己的单位推。不整号 escalate。打开仍交 061。

### Improvement Proposal

- **Target**: `issues/open/issue-090.md` 待写 Consensus。
- **Change**:

```text
这块东西的出口不是 fulfilled 的三个词，也不是只挂在没办成后面。

死：只补 not_fulfilled
死：fulfilled 3 扩 4（第四个词写进 status / fulfillment_status / overall）
死：放到 not_evaluable

「办成了 × 没立住」还得能写。
依据：040 第 4 条 + authority.md §8.3 + 这块东西不看这一次交付。
不是 fulfilled 自己要第四态。
不得写成「因为这是第二问」。
不得写成「不叫第二问了，所以可以塞回三个词」。
```

- **Verification**: Consensus 若把三个口里任何一个收回来当宿主，或论证靠「因为这是第二问」，本号失败。

### What I Changed

- `issues/open/issue-090.md`: 只追加本段 r2 Architect Response #1。未改项目源码、协议、数据。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `8481552ab6d86f98`

接受 architect r2。三个点名口塌在单位，不塌在外号。丢掉「第二问」之后，它们仍然不能当宿主。

```text
这块东西的出口不是 fulfilled 的三个词，也不是只挂在没办成后面。

死：只补 not_fulfilled
死：fulfilled 3 扩 4（第四个词写进 status / fulfillment_status / overall）
死：放到 not_evaluable

「办成了 × 没立住」还得能写。
依据：这块东西自己不看这一次交付
      + authority.md §8.3（职责内能力缺失不强制改状态；实际达成仍可办成了）
      + 040 第 4 条（办成了，不能自动排除没立住）
      + fulfilled.md §1（只评办成了没有；不并进，不加第四态）
      + fulfilled.md §2.3（说不清答的是这一次办没办成现在说不准）
      + product-function.md §1 L38（一张表 / 一个标签 / 一句结论不能同时答两件）
不是 fulfilled 自己要第四态。
不得写成「因为这是第二问」。
不得写成「不叫第二问了，所以可以塞回三个词」。
```

不改 `status` 枚举，不改 `fulfillmentPill`，不改协议正文。打开仍停住。

闸：同 089。

