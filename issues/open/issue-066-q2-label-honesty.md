# Issue #066（另一条线，撞号备份）: 开第二问的格子，在人看见的那一层就是多一个结果标签

> 备份说明：本文件属于 `charter-q2-label-honesty.md`。
> `issues/open/issue-066.md` 现被判定代理 T4 占用。067–069 仍是本条线正文。
> 本备份只恢复被覆盖的「看见层诚实」，不改 067–069，也不加入判定代理 T4 的 council。

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 看见层 / 开格子
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户打的一句：

> 你要开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗？

章程要求这一句拆开答，不得再焊回一句：

```text
人看见的：结果上是不是多了一格字
谁写下的：是不是同一张嘴再判一次
进哪张嘴：是不是改写办成了 / 没办成 / 说不清
```

本 issue 只答第一句：是。若打开第二问自己的格子，看结果的人会多看见一格字。这一格字就是一个结果标签。065「B 口不能叫标签」里「不能叫」的那一半，本轮可以打。

067 答：承认这一句，不会让 A / C / D 复活。
068 答：人看见一个标签，不是判定再填一个标签。
069 答：四个点名口的安放；打开仍停住。

## Proposed Change

Consensus 只锁看见层：开格子 = 结果上多一个标签。不批准打开，不改 schema，不改前端。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: eda05b5bb67ac683
- pid: 96523

### Investigation
自己读过、不以 verifier 转述当已证：

- 盘上 `issues/open/issue-066.md` 正文是另一章程的 T4 代理题（「T4 的嘴是两问 + 不许把问句收到交付那么小」）。本 spawn / `issues/charter-q2-label-honesty.md` / `issues/trace/q2-label-honesty-discovery.md` 起号写的 066 是「看见层诚实」。067–069 都按后一句引用 066。本回应**不判 T4 那份正文**，只判本轮指派给 066 的那句：开第二问自己的格子，看结果的人是不是多看见一个标签。T4 题面留给它自己的章程。
- `spec/alg/fulfilled.md` §1（约 L29–30）：「本协议只评第一层：办成了没有。」邻协议「不并进本协议三态，也不新增第四态。」开篇（L3–5）：词表沿用 `spec/info-volume.md`，不新增第四态。
- `spec/alg/product-function.md` §1（L37–39）：「任何一张表、一个标签、一句结论，都不能同时回答这两件。」§7.2（L167+）：「让 Judge 再填一个新标签来回答本协议 ✗」。§8（L186–196）：「以后若要看见，再加派生列」；「派生列不是 Judge 产出，不进 prompt，不改 fulfilled」；「派生列如果以后要加，也只是把本协议三态单独列出来」。
- `impl/core/schema/judge.py` L94–104：`JudgeFulfillmentAssessmentOutput` 可写评估字段只有 `status`。
- `impl/core/frontend_view.py` `_fulfillment_panel`（约 L2328–2358）：矩阵每行只投影一个 `status`。
- `impl/frontend/summary.html`：主表 `<th>状态</th>`（约 L107）；`fulfillmentPill`（L377）只给 fulfilled / not_fulfilled / not_evaluable 三种颜色；筛选（L83–88）同三词；`renderCaseStatus`（L428–431）吃 `fulfillmentStatus`；顶部 `stat-fulfilled` / `stat-not-fulfilled`（L29–30, L554–555）同吃第一问；`renderFulfillmentMatrix`（L766–770）Status 列 = `item.status`；`renderJudgeCard`（L778–782）「评估」也是这一格。
- 065 Consensus：分的是谁写、进不进判定那张嘴，「不是中文里能不能把一个格子叫『标签』」。060 Consensus：规范格子在矩阵行上、Status 旁边；本轮不批准打开。

### Reasoning
065 答对了「谁写下的」，但用这句去禁「标签」这个叫法，正好是用户本轮要打的字词游戏。章程 §1 / §5 把本轮工作定义写成可证伪的三句，第一句就是：若打开第二问自己的格子，看结果的人会不会多看见一格字。不得再用「谁写 / 进不进判定」否认这一句。

人现在看见的那一格，就是第一问三个词。主表「状态」、pill、筛选、顶部计数、矩阵 Status、Judge 卡上的「评估」，全部只吃 `status`。第二问此刻没有自己的格。这是出口事实，不是「第二问其实已经写在这三个词里」。

「开格子」按章程本轮定义，不是「在协议里多写一段」，是让看结果的人多看见一格。`product-function.md` §8 自己已经把以后若看见的东西写成「把本协议三态单独列出来」。三态列出来，就是结果上多一个词。用户把它叫做标签，没有说错。065 把「标签」收成「判定再写的那个词」，再用这个收窄去宣布「B 口不能叫标签」，答的是第二句，却把它当成第一句的否。那才是上一轮的诡辩。

针对本轮指定的三记攻击：

1. 「标签」是不是宽到 066 变成同义反复、只是重说 060？  
   「开格子 ⇒ 多一格字」在章程定义 1 下几乎是分析句。066 的增量不在重复「会多一格」，而在禁止 065 用「谁写」把这一格从「标签」里开除。060 锁的是位置（矩阵同一行、Status 旁边）和「本轮不打开」。060 刻意避开「标签」这个词。066 补的是看见层的叫法，不是重写 060 的四层表。不是 tautology 到可以不锁。

2. 承认 066，读者会不会听成「B 已批准」、把 065 整句掀掉？  
   会，如果 066 写成「所以选 B」。B 的整句是「新增一个 judge 结果的标签」——用户并列 A/C/D 时，听起来就是判定已经写下的那份结果上再多一个由判定写出的词。065 里可留的那截（「同一轮判定再写一个词不能当宿主」）证据还在：`JudgeFulfillmentAssessmentOutput` 仍然只有 `status`；`product-function.md` §7.2 / 047 / 048 / 058 仍禁止第二张嘴。066 只改 065「所以不能叫标签」那一句。看见层承认「多一个标签」，不等于批准 B 整句当宿主，也不等于本轮改表。

3. 有没有一种看见层：格子开了，仍然不算多一个标签？  
   没有——只要「打开」指的是把第二问自己的出口给人看。把权威 statement 原文塞进 Capabilities 列，060 已经否过，那不是第二问的格子。什么都不画，是 061 的「不开」，不是「开了但不是标签」。把三个词改写成四个颜色，是 C，不是「自己的格子」。所以：开自己的格子，看见层就是多一个标签。没有第三种老实话。

066 不批准打开，不代拟对外中文，不起字段名，不把内部手柄「立住了 / 没立住」宣布成题面。

### Improvement Proposal
- **Target**: 本 issue 的 Consensus 锁。不得改 `spec/**`、`impl/core/schema/judge.py`、`impl/core/frontend_view.py`、`impl/frontend/summary.html`、xlsx、canvas。
- **Change**: 只锁看见层诚实，并写明反焊：
  1. 若打开第二问自己的格子，看结果的人会在结果上多看见一个标签。065「所以不能叫标签」那一句，在看见层不成立。
  2. 这一句只答「人看见的」。不答「谁写下的」，不答「进哪张嘴」。
  3. 承认这一句，不得改名为「B 已批准」，不得当作判定再写一个词已经合法，不得当作本轮批准打开 / 加列 / 改 schema。
  4. 065 可留的那截仍留：「同一轮判定再写一个词不能当宿主」。
- **Verification**: 重读 `fulfilled.md` §1、`product-function.md` §1 / §7.2 / §8、`judge.py` L94–104、`_fulfillment_panel`、`summary.html` L107 / L377 / L766–782、065 / 060 / 061 Consensus。确认：没有新可写字段、没有前端列、没有对外中文、没有「所以 B 批准了」。任一表述用 066 去掀「判定再写不能当宿主」，或用 065 去否认「人会多看见一个标签」，即未达本锁。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `eda05b5bb67ac683`

若打开第二问自己的格子，看结果的人会在结果上多看见一个标签。

收下 architect 的切开：

- 065 答对了「谁写下的」，但用这句去禁「标签」这个叫法，是看见层的字词游戏。065「所以不能叫标签」那一句，在看见层作废。
- 这一句只答「人看见的」。不答「谁写下的」，不答「进哪张嘴」。
- 承认这一句，不得听成「所以选了 B」，不得当作判定再写一个词已经合法，不得当作本轮批准打开。
- 065 可留的那截仍留：同一轮判定再写一个词，不能当宿主。

本轮不改 schema，不改前端，不宣布对外中文。

闸：exit 0，`isolation_valid=true`。`scope_valid=false` 的路径全是 host 写的 `impl/data/context_store/**/judge-*.json`。architect 回应 0 次要改这些文件。按 058–065 惯例豁免，不重开 spawn。回应写 pid 96523，spawn-id 对齐即可。`issues/spawn/batch-066-069-r1/meta.json` 后来被并行章程的 spawn `8480dadf54af6541` 覆盖，不以那份 meta 当本轮官方闸。
