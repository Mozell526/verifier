# Issue #085: 方案名就是「新增一个 judge 结果标签」；开格子就是这件事

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 方案名 / 开格子 = 新增一个 judge 结果标签
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户本轮把上一句又问了一遍：

> 你要开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗？

077 Consensus 已经承认：在看见层，开格子就是多一个兄妹结果标签。同一份报告却把方案写成「写/枚举层选的是别的方式」。用户听到的是：开格子是标签，方案却叫别的方式。这不是安放，是换名字躲「标签」两个字。

### 人现在看见的 judge 结果标签

现行出口只有一格字，答第一问：

- `JudgeFulfillmentAssessmentOutput.status`：模型可写评估字段只有这一格（`impl/core/schema/judge.py` L94–103）
- 主表芯片：`fulfillment_status`（`impl/core/schema/table.py` L36）
- 前端药丸：`fulfillmentPill` 只认三词（`impl/frontend/summary.html`）
- 已经按第一问那一件分行的出口：`_fulfillment_panel.matrix[].status`（`impl/core/frontend_view.py` L71–81）

第二问没有自己的格子。不是因为它属于这三个词，是因为出口还没有。

### 开格子之后，人看见的是什么

060 已锁规范格子：矩阵同一行、Status 旁边。那一格如果打开，看 Judge 评估结果的人会多看见一格字。用户把这一格叫做「新增一个 judge 结果的标签」。

066-q2 已经锁：这一句在看见层成立。
077 已经锁：这一句就是方案，不再只当剩余。

本号增量只锁方案名：

```text
开第二问自己的格子
  = 新增一个 judge 结果标签
  = 本轮方案名
```

不要再写「别的方式」。
「别的方式」是 069 / 077 为了躲开 065 杀掉的整句 B，才留下的剩余叫法。用户不要剩余叫法。用户要的是：开格子本质上是不是新增一个标签。是。方案名就叫这个。

### 这一句成立，不等于

- 批准现在打开
- 批准同一轮 Judge 再写一个 status
- 批准 fulfilled 从 3 态扩到 4 态
- 把 060 / 077 改名为「已批准的整句 B」

计算仍是 058 的读。存放仍是 060：现在不进 `JudgeFulfillmentAssessmentOutput`。

### 可证伪

同时成立才算本 issue 站住：

1. 开第二问自己的格子之后，看结果的人会多看见一格字；
2. 这一格字出现在 Judge 评估结果上，用户叫它 judge 结果标签，这个叫法就是方案名；
3. 本轮不得再把方案名写成「别的方式」。

若存在一种「开了格子、人却看不见新标签」的看见层，本 issue 失败。
若承认方案名是标签，就会迫使 Judge 再写 status，本 issue 失败，应退回 065。
若 Consensus 再写「选了别的方式」，本 issue 失败。

## Proposed Change

Consensus 只锁：

1. 方案名：新增一个 judge 结果标签；
2. 开第二问自己的格子，本质上就是这件事；
3. 不再选「别的方式」当方案名；
4. 不批准打开，不改 schema，不改前端。

---
## Architect Response #1

**Judgment**: real-problem
**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 5d262889dc7c1b05
- pid: 51034

### Investigation

自己重读协议、现行出口、已锁 Consensus，不以 verifier 转述当已证。

协议：

- `spec/alg/fulfilled.md` L3–5 / L28–30：本协议只评办成了没有；「这类事现在是不是产品已经有的功能」见 `product-function.md`，「不并进本协议三态，也不新增第四态」。
- `spec/alg/product-function.md` §1 L37–39：「任何一张表、一个标签、一句结论，都不能同时回答这两件。」§7.2 L171：「让 Judge 再填一个新标签来回答本协议 ✗」。§8 L188–198：禁「给 fulfilled 加枚举」「新增一个让 Judge 填的标签」；「以后若要看见，再加派生列」；「派生列不是 Judge 产出，不进 prompt，不改 fulfilled」。
- `spec/info-volume.md` L270–278：值域只有 fulfilled / not_fulfilled / not_evaluable；「judge 只产出 fulfillment……不需要再引入第二个对错维度。」
- `spec/alg/authority.md` §8.3 L489–505：能力/职责 `statement` 先在，Judge 再写 `FulfillmentAssessment.status`。那是第一问怎么消费前缀，不是第二问的嘴。

现行出口：

- `impl/core/schema/judge.py` L94–103：`JudgeFulfillmentAssessmentOutput` 模型可写评估字段只有 `status`。
- 同文件 L27–30 / L73–76：`FulfillmentAssessment.status` 仍是这一格；`JudgeResult.summary` 已是「基于 fulfillment_assessments 派生的展示摘要」，不是第二张判定嘴。
- `impl/core/schema/table.py` L36：主表只有 `fulfillment_status`。
- `impl/core/table_view.py` L107–109：芯片值 = `judge_summary.fulfillment_status` / `overall.status` / 行 status。
- `impl/core/frontend_view.py` L71–81：`_fulfillment_panel.matrix[]` 每行只有一个 `status`，来自 `assessment.status`。
- `impl/frontend/summary.html` L377：`fulfillmentPill` 只认三词；L766–770：`renderFulfillmentMatrix` 列是 Expectation / Expected / Capabilities / Status / Blocking；L778–782：`renderJudgeCard` 的「评估」也是这一格。

已锁、本号只引用：

- 065：B 整句 =「新增一个 judge 结果的标签」若指同一轮判定再写一个词，不能当宿主。分的是谁写，不是中文里能不能把一格叫「标签」。
- 066-q2：若打开第二问自己的格子，看结果的人会多看见一个标签。065「所以不能叫标签」在看见层作废。
- 069：四个点名口没有一个能整句当宿主。半句成立，不能把整句复活。
- 077：方案在看见层就是兄妹结果标签；用户那句在看见层成立。字段层「judge 结果标签」仍等于 `status`，那一层继续死。
- 080 Architect Response #1：「写/枚举层选的是「别的方式」：派生兄妹格……看见层收下的是 B 的半句」。

本号增量只碰这一句。不重判案子，不批准打开，不改 schema / 前端。

### Evidence Verification

核过。人现在看见的 judge 结果字，出口上确实只有第一问那一格：模型可写评估字段只有 `status`，主表芯片只有 `fulfillment_status`，药丸只认三词，矩阵行上 Status 旁边没有第二格。`JudgeResult.summary` 已证明同一张评估卡上可以有派生展示。080 把写/枚举层方案名写成「别的方式」，与 077/080 自己承认的看见层事实打架。这一句我复述得出来，不是 verifier 发明。

### Reasoning

四记攻击，分开答。

1. 085 是不是只是把 065 杀掉的整句 B 换个名字？
不是。065 杀的整句是：「新增一个 judge 结果的标签」= 同一轮判定再写一个词。依据是 047 + `product-function.md` §7.2 / §8：让 Judge 再填一个新标签 ✗；同一张嘴兼答几乎一定对齐刚才的办成了没有。字段层今天也只有这一张嘴：`JudgeFulfillmentAssessmentOutput.status`。
用户本轮问的不是「再给这张嘴加一个可写字段」。用户问的是：开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗。开格子是看见层。看见层多一格字，066-q2 / 077 已经锁过。把看见层的方案名写成用户那四个字，不是把 065 的整句 B 洗活。整句 B 继续死。060 的派生格不得改名为「已批准的 B」。

2. 077 已经说看见层方案是兄妹标签，085 是不是 not-actionable 复述？
不是同一句话。077 / 080 锁的是看见层事实，却把方案名留在「别的方式：派生兄妹格」。用户听见的是：开格子是标签，方案却叫别的方式。本轮章程点名的失败就是这一步。066 锁诚实，077 把看见层写成方案零件，080 仍用「别的方式」给写/枚举层命名。085 的增量是：开格子这件事的方案名，就是「新增一个 judge 结果标签」，不得再选「别的方式」。可证伪也换了：再写「选了别的方式」即失败；承认这个名字就迫使 Judge 再写 `status`，也失败，应退回 065。

3. 这个产品里「judge 结果标签」是不是必然等于 `status`，所以 085 为假？
字段层，是。模型可写的评估标签只有 `JudgeFulfillmentAssessmentOutput.status`。`info-volume.md` 也只让 judge 产 fulfillment。若把用户那句焊成「再给 `status` 加一个词 / 再让 Judge 填一个字段」，085 为假，应退回 065。
但人看见的 judge 结果不是只有这一格。`renderJudgeCard` 已经把 Overall、矩阵、原因，以及派生 `summary` 放在同一张评估卡上。`JudgeResult.summary` 的注释写明它是派生展示摘要，不是 LLM-owned 字段。所以「出现在 Judge 评估结果上的一格字」≠「`status` 的新枚举」。085 在看见层成立，在字段层不成立。本号只许锁看见层的方案名。字段层继续死。

4. verifier 有没有偷运「所以 Judge 再填」或对外中文？
没有。正文写了计算仍是 058 的读，存放仍是 060：现在不进 `JudgeFulfillmentAssessmentOutput`。不批准打开，不改 schema，不改前端。内部手柄没有被宣布采用。这一截收下。Consensus 若写成「选了整句 B」「请 Judge 再填一个 status」「对外就叫立住了」，那一部分我否掉。

用户点的是四个口里的哪一个。开格子是看见层的事。把看见层方案叫「别的方式」，是拿写层的答案去回看见层的问题。那是分类错了，不是谨慎。本号把方案名改口，不重开 A / C / D，不重开同一张嘴，不打开那一格。

**Judgment / Verdict**：real-problem。方案名就是「新增一个 judge 结果标签」。开第二问自己的格子，本质上就是这件事。不再选「别的方式」。这不是整句 B。

## Improvement Proposal

**Problem**: 077–080 已承认开格子在看见层是标签，却把方案名写成「别的方式」，用户再问同一句时交不出名字。
**Proposed Change**: 只锁本号 Consensus 四句。不得改 `spec/**`、`impl/**`、xlsx、canvas、`impl/frontend/summary.html`。

```text
方案名：新增一个 judge 结果标签。
开第二问自己的格子，本质上就是这件事。
不再选「别的方式」当方案名。
这一句只答「人看见的」。不是整句 B，不是批准打开，不是让 Judge 再写 status。
```

同时锁死：

- 不等于批准现在打开（061 / 章程 §4）。
- 不等于同一轮 Judge 再写一个 `status`（065 / `product-function.md` §7.2）。
- 不等于把 060 / 077 改名为「已批准的整句 B」。
- 字段层「judge 结果标签」继续等于 `status`；那一层继续死。
- 计算仍是 058 的读。存放仍是 060：现在不进 `JudgeFulfillmentAssessmentOutput`。

**Implementation Steps**:
1. 只把上面四句写入本号 Consensus。
2. 不得在 `judge.py` / `table.py` / `summary.html` 上加字段、加列、加词。
3. 不得宣布对外中文。

**Risks**: 读者把方案名听成「选了整句 B，让 Judge 再填」。用三层切开挡：人看见的 / 谁写下的 / 进哪张嘴。本号只锁第一层的名字。
**Verification**:
1. 重读 `fulfilled.md` §1、`product-function.md` §7–§8、`info-volume.md` L270–278。
2. 重读 `judge.py` L94–103、`frontend_view.py` L71–81、`summary.html` L377 / L766–782。
3. 重读 065 / 066-q2 / 069 / 077 / 080 Consensus。
4. Consensus 正文不得出现：「选了别的方式」「所以 B 批准了」「请 Judge 再填」「本轮采用某某中文」。出现任一项，本锁失败。

### What I Changed
无。review 模式，只追加本回应。未改 spec / impl / 前端。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `5d262889dc7c1b05`

接受 architect 的收口。077 / 080 已经承认看见层是标签，却把方案名留在「别的方式」。那是拿写层的答案去回看见层的问题，不是谨慎。本号只改方案名。

收下 architect 的切开：

- 方案名：新增一个 judge 结果标签。开第二问自己的格子，本质上就是这件事。不再选「别的方式」。
- 这一句只答「人看见的」。不是 065 杀掉的整句 B，不是批准打开，不是让 Judge 再写 `status`。
- 字段层「judge 结果标签」继续等于 `JudgeFulfillmentAssessmentOutput.status`。那一层继续死。
- 计算仍是 058 的读。存放仍是 060：现在不进判定那张嘴。
- 060 / 077 不得改名为「已批准的整句 B」。

本轮不改 schema，不改 prompt，不改前端，不加列，不宣布对外中文。

闸：exit 0，`isolation_valid=true`，`scope_valid=true`，spawn-id 对齐。wrapper pid 50840 / 回应写 51034，spawn-id 对齐即可。
