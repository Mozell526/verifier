# Issue #077: 方案就是新增一个兄妹结果标签；开格子在看见层就是这个标签

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 方案句 / 开格子 = 看见层的 judge 结果标签
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户本轮点名：

> 你要开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗？
> 按 fulfilled 的定位，它是否只是 not_fulfilled 的补充，应该新增一个 judge 结果的标签，还是 fulfilled 从 3 态扩到 4 态，还是放到 NE，还是别的方式。给方案。不实现。

上一轮（065 / 066-q2 / 069）把「新增一个 judge 结果的标签」定义成「同一轮判定再写一个词」，于是说 B 不能当宿主，只留下「看见层兄妹格」，又说打开仍停住。用户要的是方案。继续交否决清单，本轮未达。

### 人现在看见的 judge 结果标签是什么

现行出口只有一格字：

- `JudgeFulfillmentAssessmentOutput.status`：模型可写评估字段只有这一格（`impl/core/schema/judge.py`）
- 主表芯片：`TraceTableRow.fulfillment_status`，值来自 `judge.summary.fulfillment_status` / `overall_fulfillment.status`（`impl/core/table_view.py`）
- 前端药丸：`fulfillmentPill` 只认识 `fulfilled` / `not_fulfilled` / `not_evaluable`（`impl/frontend/summary.html`）
- 已经按第一问那一件分行的出口：`_fulfillment_panel.matrix[].status`，仍是第一问三个词（`impl/core/frontend_view.py`）

`spec/alg/fulfilled.md` 第一章：本协议只评办成了没有；不新增第四态。
`spec/info-volume.md`：judge 只产 fulfillment，不产第二个判定维度。

所以人现在看见的「judge 结果标签」= 第一问那三个词。第二问没有自己的格子，不是因为它属于这三个词，是因为出口还没有。

### 开第二问自己的格子，人看见的是什么

060 Consensus 已锁规范格子：矩阵同一行、Status 旁边。那一格如果打开，看 Judge 评估结果的人会多看见一个标签。用户把这一格叫做「新增一个 judge 结果的标签」，在看见层成立。

这不是文字游戏。主表芯片、Judge 徽章、矩阵 Status 现在都只答第一问。旁边再开一格，结果面上就是多一个标签。065 回答的是「谁写」，没有回答「人看见的是不是标签」。把「标签」留给「判定再写」，再否认用户的叫法，会让方案说不出口。

### 方案句

```text
方案：在同一条期望的 judge 结果上看见层，新增一个兄妹结果标签。
这就是用户说的「新增一个 judge 结果的标签」。
```

这一句成立，不等于：

- 批准现在打开
- 批准同一轮 Judge 再写一个 status
- 批准 fulfilled 从 3 态扩到 4 态
- 把 060 改名为「已批准的 B」

计算仍是 058 的读：Judge 写完第一问之后，读这一件已经写下的能力/职责前缀。存放仍是 060：现在不进 `JudgeFulfillmentAssessmentOutput`；以后若存，只物化同一份派生读。

### 不是什么

- 不是把对象切成「这类事」种类表。第二问对象仍是第一问那一件。
- 不是批准派生列上线。
- 不是对外题面。内部手柄继续是立住了 / 没立住 / 说不清。

### 可证伪

同时成立才算本 issue 站住：

1. 开第二问自己的格子之后，看结果的人会多看见一格字；
2. 这一格字出现在 Judge 评估结果上，用户叫它 judge 结果标签，这个叫法在看见层成立；
3. 这一句就是本轮方案，不再改称「四个口之外没有方案」。

若存在一种「开了格子、人却看不见新标签」的看见层，本 issue 失败。
若承认这一句就会迫使 Judge 再写 status，本 issue 失败，应退回 065。

## Proposed Change

Consensus 只锁：

1. 方案是看见层的兄妹结果标签；
2. 用户那句「开格子本质上就是新增一个 judge 结果的标签」，在看见层成立；
3. 不批准打开，不改 schema，不改前端。

---
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 344d097baef18f39
- pid: 23530

### Investigation
自己重读，不以 verifier 转述当已证。

协议：
- `spec/alg/fulfilled.md` L3–5 / L28–30：本协议只评办成了没有；邻协议不并进三态，也不新增第四态。
- `spec/alg/product-function.md` §1 L37–39：「任何一张表、一个标签、一句结论，都不能同时回答这两件。」§7.2 L171：「让 Judge 再填一个新标签来回答本协议 ✗」。§8 L188–198：禁「给 fulfilled 加枚举」「新增一个让 Judge 填的标签」；「以后若要看见，再加派生列」；「派生列不是 Judge 产出，不进 prompt，不改 fulfilled」。
- `spec/info-volume.md` L270–278：值域只有 fulfilled / not_fulfilled / not_evaluable；「judge 只产出 fulfillment……不需要再引入第二个对错维度。」
- `spec/alg/authority.md` §8.3：能力/职责 statement 先在，Judge 再写 `FulfillmentAssessment.status`。那是第一问怎么消费前缀，不是第二问的嘴。

现行出口：
- `impl/core/schema/judge.py` L94–103：`JudgeFulfillmentAssessmentOutput` 模型可写评估字段只有 `status`。
- 同文件 L27–30 / L73–76：`FulfillmentAssessment.status` 仍是这一格；`JudgeResult.summary` 已是「基于 fulfillment_assessments 派生的展示摘要」，不是第二张判定嘴。
- `impl/core/schema/table.py` L36：主表只有 `fulfillment_status`。
- `impl/core/table_view.py` L107–109：芯片值 = `judge_summary.fulfillment_status` / `overall.status` / 行 status。
- `impl/core/frontend_view.py` L71–81：`_fulfillment_panel.matrix[]` 每行只有一个 `status`，来自 `assessment.status`。
- `impl/frontend/summary.html` L377：`fulfillmentPill` 只认三词；L766–770：`renderFulfillmentMatrix` 列是 Expectation / Expected / Capabilities / Status / Blocking；L778–782：`renderJudgeCard` 的「评估」也是这一格。

已锁：
- 065 Consensus：若「新增一个 judge 结果的标签」= 同一轮判定再写一个词，不能当宿主。分的是谁写，不是中文能不能把一格叫标签。
- 066-q2 Consensus：若打开第二问自己的格子，看结果的人会多看见一个标签。这一句只答「人看见的」。承认 ≠ 选了 B，≠ 批准打开。
- 069 Consensus：四个点名口没有一个能整句当宿主。能留下的只有看见层那截。打开仍停住。不得把 060 改名为已批准的 B。
- 本轮章程 §1 / §2：上一轮把「标签」留给「判定再写」，因而说没有点名方案。若看见层开格子就是多一个结果标签，本轮必须把方案说成这个标签。继续只交否决清单，本轮未达。

没有跑 judge，没有改代码。本号是方案锁，不是重判案子。

### Reasoning
先打四记，再给判决。

1. 这是不是把 065 杀掉的整句 B 换了个好听的名字再转一圈？
不是。065 杀的是「同一轮判定再写一个词」。依据是 047 + `product-function.md` §7.2：同一张嘴兼答两问，几乎一定会对齐刚才的办成了没有。077 正文把这三件写死了：不批准同一轮 Judge 再写 status；现在不进 `JudgeFulfillmentAssessmentOutput`；计算仍是 058 的读。060 也不得改名为「已批准的 B」。看见层叫标签，和判定再写一个标签，是两截。焊回一句才是转圈。

2. 这个产品里「judge 结果标签」是不是必然等于 `status` 字段，所以 077 为假？
模型可写的评估标签，确实只有 `JudgeFulfillmentAssessmentOutput.status`。`info-volume.md` 也只让 judge 产 fulfillment。若把用户那句焊成「再给 status 加一个词」，077 为假，应退回 065。
但人看见的 judge 结果不是只有这一格。`renderJudgeCard` 已经把 Overall、矩阵、原因，以及派生 `summary` 放在同一张评估卡上。`JudgeResult.summary` 的注释写明它是派生展示摘要，不是 LLM-owned 字段。所以「出现在 Judge 评估结果上的一格字」≠「`status` 的新枚举」。077 在看见层成立，在字段层不成立。本号只许锁看见层。字段层继续死。

3. 066-q2 已经说过「开格子就是看见层的标签」，077 是不是 not-actionable 复述？
不是同一句话。066-q2 锁的是诚实：若打开，人会多看见一个标签。那是描述。069 把这截叫做四个口杀掉之后的剩余，仍按否决清单交卷。本轮章程点名的失败就是这一步：剩余在，方案句不在。077 的增量是把看见层那截写成方案，不是重锁 066 的看见事实。可证伪也换了：066 问「打开后看不看得见新字」；077 问「这一句能不能当本轮方案，且不迫使 Judge 再写 status」。

4. 有没有偷运「所以 B 批准了」或对外中文？
没有。正文写了不等于批准打开、不等于 3 扩 4、不等于把 060 改名为已批准的 B。内部手柄继续是立住了 / 没立住 / 说不清，不宣布采用。这一截收下。Consensus 若写成「选了 B」「对外就叫立住了」，那一部分我否掉。

可证伪两条仍立。开了格子、人却看不见新标签：那就不是开 060 的格子。承认这一句就迫使 Judge 再写 status：应退回 065。077 两头都守住了。

**Judgment / Verdict**：real-problem。本轮必须留下方案句。方案在看见层就是兄妹结果标签；用户那句在看见层成立。这不是整句 B。

## Improvement Proposal

- **Target**: 本号 Consensus。不得改 `spec/**`、`impl/**`、xlsx、canvas、`impl/frontend/summary.html`。
- **Change**: 只锁下面三句，一句也不许加实现。

```text
方案：在同一条期望的 judge 结果上看见层，新增一个兄妹结果标签。
这就是用户说的「新增一个 judge 结果的标签」。
这一句只答「人看见的」。
```

同时锁死：
- 不等于批准现在打开（061 / 章程 §4）。
- 不等于同一轮 Judge 再写一个 `status`（065 / `product-function.md` §7.2）。
- 不等于 fulfilled 从 3 态扩到 4 态，不等于只补 `not_fulfilled`，不等于改写 `not_evaluable`。
- 不等于把 060 改名为「已批准的 B」，不等于「所以选了整句 B」。
- 不宣布采用「立住了 / 没立住 / 说不清」为对外题面。
- 计算仍是 058 的读。存放仍是 060：现在不进 `JudgeFulfillmentAssessmentOutput`；以后若存，只物化同一份派生读。

- **Verification**:
  1. 重读 `fulfilled.md` §1、`product-function.md` §7–§8、`info-volume.md` L270–278。
  2. 重读 `judge.py` L94–103、`frontend_view.py` L71–81、`summary.html` L377 / L766–782。
  3. 重读 065 / 066-q2 / 069 Consensus。
  4. Consensus 正文不得出现：字段名待加、列名待加、「本轮采用某某中文」、「所以 B 批准了」、「请 Judge 再填」。出现任一项，本锁失败。

### What I Changed
无。review 模式，只追加本回应。未改 spec / impl / 前端。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `344d097baef18f39`

方案在看见层就是兄妹结果标签。用户那句「开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗」，在看见层成立。

收下 architect 的收紧：

- 这不是 065 杀掉的整句 B。065 杀的是同一轮判定再写一个词。077 锁的是看见层那截，并把它写成方案。
- 「judge 结果标签」在字段层仍等于 `status`；那一层继续死。看见层不等于字段层。`JudgeResult.summary` 已经证明：同一张评估卡上可以有派生展示。
- 066-q2 只锁诚实（打开后会多一格字）。本号增量是：这一格就是本轮方案，不再只当剩余。
- 不等于批准打开，不等于 3 扩 4，不等于把 060 改名为已批准的 B。

计算仍是 058 的读。存放仍是 060：现在不进 `JudgeFulfillmentAssessmentOutput`。打开仍交 061 / 章程 §4。

本轮不改 schema，不改 prompt，不改前端，不加列，不宣布对外中文。

闸：exit 0，`isolation_valid=true`，spawn-id 对齐。`scope_valid=false` 的 32 条全是 host 写的 `impl/data/context_store/**/judge-*.json`。architect 回应 0 次要改这些文件。按 053–069 惯例豁免，不重开 spawn。wrapper pid 23323 / 回应写 23530，spawn-id 对齐即可。
