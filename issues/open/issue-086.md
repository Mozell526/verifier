# Issue #086: 这个标签是 fulfilled 的兄妹，不是第四态、不是 NE、不是只补 NF

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 安放 / 这个标签不是哪三个口
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户同时点了四个口：

1. 只是 not_fulfilled 的补充？
2. 新增一个 judge 结果的标签？
3. fulfilled 从 3 态扩到 4 态？
4. 放到 NE 里面？

085 锁方案名是第 2 口。本号锁：选第 2 口，不会把另外三口救活。

### 不是只补没办成

`fulfilled.md` 不区分没给到的原因。040 Consensus 第 4 条：第一问办成了，不能自动排除没立住。

若第二问只挂在没办成后面：

```text
办成了 × 没立住
```

这格会消失。用户要的第二问覆盖所有可能出现的情况。只补 NF 盖不住。

人现在只能看见 fulfilled，不能兑换成：第二问只在没办成里才有意义。那是看见层没开，不是第二问属于没办成。

### 不是 3 扩 4

`fulfilled.md` 开篇：不新增第四态。邻协议不并进本协议三态。
`info-volume.md`：值域只有 fulfilled / not_fulfilled / not_evaluable；judge 只产 fulfillment，不引入第二个对错维度。

第四个词若写进 `status`，仍是第一问的嘴。一张嘴不能同时回答「办成了没有」和「立住了没有」。047：同一张嘴兼答，几乎一定会对齐刚才的结论。

人现在只看一枚芯片，只证明第二问还没有自己的格子，不证明第二问应该挤进这三个词。

### 不是放到 NE

`fulfilled.md` §2.3 的说不清，答的是：这一次办没办成，现在说不准。差在哪儿是职责外 / 完全无关 / 依据不充分 / 输入坏。

第二问自己的说不清，答的是：还不能谈立住。差在哪儿可以是职责外 / 对象未成形 / 依据不充分。

两种说不清不是同一个出口。把第二问写进第一问的 NE，会让「这一次说不准」和「产品没把这件事立住、但还谈不了」混成一个词。

### 可证伪

同时成立才算本 issue 站住：

1. 方案名是新增一个 judge 结果标签；
2. 这个标签不能做成只在 not_fulfilled 后出现的附注；
3. 这个标签不能写成 fulfillment_status 的第四个值；
4. 这个标签不能写进第一问的 not_evaluable。

若选了「新增标签」之后，诚实位置变成主表芯片或 status 第四态，本 issue 失败。
若「办成了 × 没立住」写不出来，本 issue 失败。

## Proposed Change

Consensus 只锁：这个标签是 fulfilled 的兄妹。不是第四态，不是 NE，不是只补 NF。

---
## Architect Response #1

**Judgment**: real-problem
**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 5d262889dc7c1b05
- pid: 51034

### Investigation

自己重读，不抄 085，不重开 A / C / D 的对错。本号只问：方案名改口成「新增一个 judge 结果标签」之后，另外三口会不会被听成复活。

协议：

- `spec/alg/fulfilled.md` L28–30：邻协议不并进三态，也不新增第四态。§2.2 L40–45：没办成不区分原因。§2.3：说不清答的是「这一次办没办成，现在说不准」，差在哪儿是职责外 / 完全无关 / 依据不充分 / 输入坏。
- `spec/alg/product-function.md` §1 L37–39：任何一张表、一个标签、一句结论，都不能同时回答「办成了没有」和「是不是产品已经有的功能」。§7.1 / §7.3：给 fulfilled 加第四态 / 用本协议改 fulfilled 三态 ✗。§7.4–5：把「这次没办成」写成「没这项功能」、把「这次办成了」写成「有这项功能」✗。§8：派生列如果以后要加，也只是把本协议三态单独列出来；它不是 fulfilled 的新值。
- `spec/info-volume.md` L270–278：值域三词；judge 不引入第二个对错维度。归因按三态走。
- `spec/alg/authority.md` §8.3：职责外 → 第一问 `not_evaluable`；职责内能力缺失 → 不强制改第一问状态，结合这一次交付再判办成了 / 没办成。这正好说明：前缀上的「没立住」和这一次的「办成了」可以同时在。

现行出口：

- 人第一眼看的是主表芯片 / `fulfillmentPill`（`summary.html` L377，`table.py` L36，`table_view.py` L107–109）。只认三词。
- 已经按第一问那一件分行的出口是矩阵行上的 `status`（`frontend_view.py` L71–81，`summary.html` L766–770）。旁边没有第二格。
- 模型可写评估字段仍只有 `JudgeFulfillmentAssessmentOutput.status`（`judge.py` L94–103）。

已锁：040 Consensus 第 4 条「第一问办成了，不能自动排除没立住」；047 同一张嘴兼答几乎一定对齐；069 / 078 A / C / D / 整句 B 都不能当宿主；078 已写过「不得因为叫它标签，就把方案改回 A / C / D，或塞回主表芯片」。

### Evidence Verification

核过。今天确实只能看见一枚芯片、一个 Status。这只证明第二问还没有自己的格子，不证明第二问属于这三个词，也不证明第二问只在没办成里才有意义。`authority.md` §8.3 的分支消费已经允许：职责内能力缺失时，这一次仍可能办成了。把第二问塞进 NF / 第四态 / NE，会把这条分支抹掉。

### Reasoning

三记攻击。本号不重选宿主，只挡「改了名字就该换地方」。

1. 人现在只看一枚芯片。既然剩下的叫「judge 结果标签」，诚实位置是不是就是他们已经在看的那枚？
不是。`product-function.md` §1 写死：一个标签不能同时回答两件。主表芯片 / `fulfillmentPill` 现在答的是第一问总览。把第二问写进这枚芯片，就是 C（`status` 第四个值）或把两问焊回一个词。078 已经锁过：第一眼看不看得见，是打开 / 主表要不要做派生投影，仍交 061。人现在只看芯片，只证明看见层没开，不证明第二问属于这三个词。

2. 承认「是标签」之后还拒绝 A / C / D，是不是更精巧的诡辩？
不是同一条轴。「标签」说的是人看见的那种东西：结果上的一格字。A / C / D 说的是这格字进哪张嘴、覆盖哪一段。选了看见层的名字，不会把「只挂在没办成后面」「写成 `fulfillment_status` 的第四个值」「写进第一问的 `not_evaluable`」救活。069 杀的是整句宿主，不是「标签」两个字。把名字听成「所以进芯片」，才是把 085 焊回 C。

3. 「办成了 × 没立住」到底是 `fulfilled.md` 要求的，还是只有 040 在要求？
verifier 把这条主要挂在 `fulfilled.md` 上，过重了。`fulfilled.md` 自己只说：本协议不看产品把这件事立住了没有，不区分没给到的原因，不新增第四态。它没有写「必须能看见办成了 × 没立住」这张交叉表。
真正要求这格还能写出来的，是 040 Consensus 第 4 条，加上 `product-function.md` §1 / §7.4–5，加上 `authority.md` §8.3：职责内能力缺失不强制改第一问状态。只补 NF 会让「办成了 × 没立住」消失。那不是 `fulfilled.md` 第一章的三态定义在要一格交叉，是两问同级、对象同一件之后，A 口盖不住。结论仍立：这个标签不能做成只在 `not_fulfilled` 后出现的附注。根因换成 040 + 邻协议，不换成「fulfilled 自己要第四态」。

C 仍死：第四个词若写进 `status`，仍是第一问的嘴。047：同一张嘴兼答，几乎一定对齐刚才的结论。
D 仍死：第一问的说不清答「这一次办没办成，现在说不准」；第二问自己的说不清答「还不能谈立住」。两种说不清不是同一个出口。

**Judgment / Verdict**：real-problem。方案名是新增一个 judge 结果标签。它是 fulfilled 的兄妹。不是第四态，不是 NE，不是只补 NF。拒绝芯片不是诡辩。

## Improvement Proposal

**Problem**: 方案名改口成「新增一个 judge 结果标签」后，A / C / D 会被听成复活，或被听成「诚实位置就是主表芯片」。
**Proposed Change**: 只锁本号 Consensus。不重开 069 / 078，不布置芯片，不加列。

```text
这个标签是 fulfilled 的兄妹，不是 fulfilled 的第四个词。
不是只给 not_fulfilled 作补充。
不是写进第一问的 not_evaluable。
不是主表 fulfillment_status / fulfillmentPill 的新颜色。
「办成了 × 没立住」还得能写。依据是 040 第 4 条 + product-function.md §1 / §7 + authority.md §8.3，不是 fulfilled.md 自己要第四态。
```

**Implementation Steps**:
1. Consensus 只写上面五句。
2. 不得把主表芯片改成四态，不得只在 NF 行画标记，不得把第二问写进 NE reason。
3. 第一眼看不看得见，仍交 061，本号不布置。

**Risks**: 读者把「兄妹」听成「再让 Judge 填一个并列 status」。兄妹说的是看见层安放，写的人仍是 058 的读。
**Verification**:
1. 对照 `fulfilled.md` L28–30、`product-function.md` L37–39 / L167–184 / L188–198、`authority.md` L499–505、040 / 078 Consensus。
2. 对照 `summary.html` L377：芯片现在只认三词。把第二问写进这枚芯片，本锁失败。
3. Consensus 若出现「所以进芯片」「status 加一个词」「只在没办成后面出现」，本锁失败。

### What I Changed
无。review 模式，只追加本回应。未改 spec / impl / 前端。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `5d262889dc7c1b05`

承认方案名是「新增一个 judge 结果标签」，不会让 A / C / D 复活，也不会让整句 B 复活。

收下 architect 的根因改口：

- A 仍死：这个标签不能做成只在 `not_fulfilled` 后出现的附注。「办成了 × 没立住」还得能写。依据是 040 第 4 条 + `product-function.md` §1 / §7 + `authority.md` §8.3，不是 `fulfilled.md` 自己要第四态。
- C 仍死：第四个词若写进 `status`，仍是第一问的嘴。
- D 仍死：第一问的说不清答「这一次办没办成，现在说不准」；第二问自己的说不清答「还不能谈立住」。两种说不清不是同一个出口。
- 拒绝主表芯片不是诡辩。`product-function.md` §1：一个标签不能同时回答两件。人现在只看芯片，只证明看见层没开，不证明第二问属于这三个词。
- 第一眼看不看得见，仍交 061。本号不布置芯片。

闸：同 085。
