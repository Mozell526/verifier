# Issue #068: 人看见一个标签，和判定再填一个标签，不是同一件事

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 谁写 / 看见标签不能焊回判定再填
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

066 承认看见层：开格子就是结果上多一个标签。
067 承认这个标签不能并进第一问三个词。

还剩下用户点名的 B：「新增一个 judge 结果的标签」。

这句话里有两截。焊在一起，就只剩两条路：永远不让人看见第二问，或把它塞进 status。本 issue 只钉：这两截不能焊。

### 章程本轮要求分开答的三句

```text
人看见的：结果上是不是多了一格字
谁写下的：是不是同一张嘴再判一次
进哪张嘴：是不是改写办成了 / 没办成 / 说不清
```

066 答第一句：是。
067 答第三句：不是。
本 issue 答第二句：不是同一张嘴再判一次。

### 现行出口：判定现在写出的是什么

`impl/core/schema/judge.py` `JudgeFulfillmentAssessmentOutput`：模型可写的评估字段仍只有 `status`。`authority_tool_call_ids` 是引用，不是第二问答案。

`spec/info-volume.md`：

> judge 只产出 fulfillment（细粒度 + 整体两层），不产 verdict。

`spec/alg/product-function.md` §7.2 / §8：

```text
让 Judge 再填一个新标签来回答本协议     ✗
新增一个让 Judge 填的标签
  → 变成第二个判定；两问会抢解释权；会过拟合长尾集
以后若要看见，再加派生列
  → 派生列不是 Judge 产出，不进 prompt，不改 fulfilled
```

047 Consensus：第二问不是同一轮 Judge 再填；「现在只能看见 fulfilled」不得兑换成改由 Judge 填。
058 Consensus：第二问读已经写下的能力/职责前缀，不让 Judge 再填。

所以：结果上以后若出现第二问那一格字，它的来源仍是已经裁完的前缀，不是判定再吐一个词。

### 焊在一起会变成什么

| 焊法 | 接下来只能怎么走 | 丢掉的 |
|---|---|---|
| 「人看见标签」=「判定再填标签」 | 要么永不打开，要么给判定多一个可写字段 | 060 的兄妹格；product-function §8 的派生列 |
| 判定多一个可写字段 | 刚写了办成了的那张嘴，用它去对齐产品事实 | 058 的读；长尾集会把第二问写成失败原因 |
| 为了不给判定加字段，所以不许叫标签 | 回到 065 被打的那句 | 066 的看见层诚实 |

用户上一轮已经拒绝「谁写」单独当挡箭牌。本轮不能反过来，用「人看见标签」把「判定再填」偷渡回来。两句话都要留：

```text
开格子 = 人看见的结果上多一个标签     成立
这个标签由同一轮判定再写             不成立
```

### 人会不会「体验成」判定的第二个词

会。主表读者不一定去查谁写的。这不能倒推成「所以必须让判定写」。

现行系统里，`summary`、`_fulfillment_panel` 已经是判定写完再派生。人看见的「评估 / 矩阵」并不等于模型刚才吐出的每一个字段。第二问若打开，同类：算的时候不进 `JudgeFulfillmentAssessmentOutput`，也不回写 `status`。

「体验成判定的第二个词」是看见层的观感，不是所有权。047 已经把所有权钉在：Harness / 派生阅读都不得改写第一问那一口。第二问同样：派生阅读不得改由判定再判一次。

### 不是什么

- 不是否认 066。看见层就是多一个标签。
- 不是再宣布 065 整份作废。065 里「判定再写一个词不能当宿主」仍留；作废的只是「所以不能叫标签」。
- 不是批准派生列上线。

### 可证伪

「人看见一个标签」和「判定再填一个标签」是同一件事，要同时成立：

1. 结果上多一格字，就必须由 `JudgeFulfillmentAssessmentOutput` 新增一个可写字段；
2. 或者凡是人不从判定嘴里读到的字，都不许出现在结果上；
3. 或者派生列一旦被人看见，所有权就自动回到判定。

1 与 product-function §7.2 / 047 / 058 直接撞。2 会把已经存在的 `summary` / `_fulfillment_panel` 也判死。3 把看见兑换成所有权，048 / 047 已经否过。所以两截不能焊。

## Proposed Change

Consensus 只锁：开格子之后人看见的那个标签，不是同一轮判定再填的标签。看见层承认「多一个标签」，所有权仍是 058 的读，不是给判定加一个可写字段。

不得把「用户看见标签」和「Judge 填一个标签」收成同一句话。不改 schema，不改 prompt，不批准打开。

---
## Architect Response #1

**Verdict**: not-actionable

### Spawn Evidence
- spawn-id: eda05b5bb67ac683
- pid: 96523

### Investigation
068 全文读过。中间表和可证伪三条也核对过。自己重读了它当作新根因的那些出口：

- `spec/alg/product-function.md` §7.2 / §8：Judge 再填新标签 ✗；以后若看见，派生列不是 Judge 产出，不进 prompt。
- `impl/core/schema/judge.py` L94–104：判定可写评估字段仍只有 `status`。`JudgeResult.summary`（L73–76）注明是基于 assessments **派生**的展示摘要。
- `impl/core/frontend_view.py` `_fulfillment_panel`：判定写完之后再投影矩阵；每行一个 `status`。
- `impl/frontend/summary.html` `renderJudgeCard`（L778–782）：这块卡的标题就是判定卡。「评估」、矩阵、原因、Raw JudgeResult 画在同一张卡里。派生字段已经按「判定结果」给人看。
- 047 Consensus：第二问不是同一轮 Judge 再填；「现在只能看见 fulfilled」不得兑换成改由 Judge 填。
- 058 Consensus：第二问读已经写下的前缀，不让 Judge 再填。
- 065 Consensus：「新增一个 judge 结果的标签」若指同一轮判定再写一个词，不能当宿主。分的是谁写，不是中文能不能叫标签。
- 048 Consensus：让 Judge 再填一个用来答第二问的标签已死；看见与否不得偷换判定产出。

没有新的代码路径，没有新的可写字段，没有一条 047 / 065 没钉过的出口。

### Reasoning
章程要求本轮分开答「谁写下的」。答案仍然是：不是同一张嘴再判一次。这个答案 047 / 058 / 065 已经锁死。068 把它重写了一遍，再加一句「不要和 066 焊」。那是约束，不是新根因。

指定攻击：

1. 「人体验到的，结果上任何一词都是判定的第二个结论。」  
   观感成立。`_fulfillment_panel` 已经画在 `renderJudgeCard` 里。以后若在矩阵 Status 旁边加一格，主表读者不会先去查 `JudgeFulfillmentAssessmentOutput` 有没有这个字段。他们会觉得判定又说了一句。068 自己也承认「会」。观感不能倒推所有权——048 / 047 已经否过「看见兑换成判定产出」。但观感成立，正好说明「谁写」回答不了「人看见的」。那是 066 的题。068 再论证一次所有权，没有给开发者新的落点。

2. 「谁写」是不是用户已经拒绝的字词游戏？  
   用户拒绝的是：用谁写去否认人看见多一格字。不是宣布所有权这个问题不存在。`product-function.md` §7.2、047 改口、058 的读，仍是本项目的硬约束：同一张嘴兼答，几乎一定对齐刚才的办成了 / 没办成。那不是实现细节，是已经锁过的失败模式。068 把这截再讲一遍，并不使它变成新 issue。字词游戏在 065 用谁写禁「标签」；反焊的正确位置是 066 / 069 的否定句，不是再开一张「看见 ≠ 判定再填」的根因单。

3. 「派生兄妹仍会感觉像 Judge 输出，068 是不是该直接 not-actionable，因为它只是重说 047 / 065？」  
   是。可证伪三条（必须给判定加可写字段 / 凡不是判定嘴里读到的字都不许出现在结果上 / 派生列一经看见所有权回到判定）全部是 047 / 048 / 065 / `product-function.md` §8 的旧闸。`summary` 和 `_fulfillment_panel` 早已是派生还被人看见——068 用它们当类比，恰恰证明现行设计已经分开「谁写」和「人看见」，没有新的待修缺陷。

本轮「谁写下的」我仍然答：不是同一轮判定再写一个词。065 可留的那截继续留。066 承认看见层标签之后，这一句也不翻。只是 068 不该再当一条独立 Confirmed 根因。

不批准打开。不改 schema。不把 068 听成「所以不能叫标签」复活。

### What's Still Needed
- 不要把 047 / 065 已经锁死的「判定再写不能当宿主」再立成 068 号根因。
- 反焊句写进 066 / 069 的 Consensus 否定项即可：「承认看见层多一个标签 ≠ 批准同一轮判定再写一个词 ≠ 把 060 改名为已批准的 B」。
- 若发起方需要本轮书面留下「谁写下的」，直接引用 047 / 058 / 065，不要再为同一句话开号。
- 不要补前端列、schema 字段、对外中文来「证明」谁写——那会越权，也证明不了新根因。
---
## Architect Response #2

**Verdict**: not-actionable

### Spawn Evidence
- spawn-id: 8480dadf54af6541
- pid: 3212

### Investigation
Concurrent peer spawn `eda05b5bb67ac683` wrote Architect Response #1 on this same number under `charter-q2-label-honesty`. This #2 is only charter-judge-agent-t4 / spawn `8480dadf54af6541`. I do not adopt, overturn, or continue that other charter.

Read `issues/open/issue-068.md` in full. On disk it is 「人看见一个标签，和判定再填一个标签，不是同一件事」— 058–065 who-writes / 看见层. It assumes 066 admitted “开格子就是结果上多一个标签” and 067 killed A/C/D. That is the other Q2. I am not judging whether Judge may write a sibling tag.

This spawn’s 068 is supposed to be: Q1 read-only field evidence is required (T1 lifted 共展); per delivered field, not a type router. That claim is not in the file. I still read the dumps and regenerated the evidence text.

T1 freeze, treatment `current_prompt_plus_memory_principle_shortcircuit_disabled`, principle still contains 「2–4 个汉字、有姓」:

- `SYN-gongzhan` / `I650` 共展 → `fulfilled`
- `SYN-gongzhan` reason: 「用户只提供“共展”这一姓名维度，实际输出原样提取该值并映射到客户本人姓名字段…」
- `I650` reason: 「“共展”为符合姓名维度标准的两字中文姓名」

T2 / T3 / T4: `SYN-gongzhan` → `not_fulfilled`. T2 reason: 「只读标准确认该值没有已识别的姓」.

I regenerated `q1_evidence_text` against `load_field_standards`:

- 共展 / searchClientName: 「不够撑住该字段已有标准。依据：没有该维已识别的姓。」
- 杨杰 / searchClientName: 「够撑住…2至4个汉字、有姓…」
- 金凤 / searchClientName: 「不够撑住…与已有产品名撞车。」
- 金凤 / `polNoInfo.plancodeinfo.abbrname`: 「该字段本轮没有已有标准检查。不要发明标准，也不要因此判这一字段失败。」
- 李明+疾病保险: name passes; `pCategorys` has no standard this round.
- 张忠波 name: Q1 passes. Any I007 NF is Q2.

T1 principle already recited the name standard and still lifted 共展. T2+ inject the per-field check as a second extra. `probe_q1` is in the T2 lineage; T4 `probe_t4.gong_has_fail=true` when I reran `--probe --treatment t4`.

### Reasoning
A developer reading this file would try to lock “看见 ≠ Judge 再填.” That is 058–065 work. Under charter-judge-agent-t4 it is the wrong object. That is the not-actionable trigger: the write-up does not locate a T4 change.

I will not smuggle a type table, a 保单 lexicon, or an official-file edit into a Q1 issue that was never filed.

If the verifier refiles the Q1 claim on this number, these are the constraints I will hold them to — they are **not** a verdict on the sibling-label text:

- T1 lifting 共展 is real. Writing `2–4 / 有姓` into the principle was not enough; the model invented “共展 is a two-character name.”
- Injecting `q1_evidence_text` is a sidecar pass/fail. Yes, the agent is told to consume a precomputed check. That is “consume the existing standard,” which T1 failed to do from prose alone. It is **not** a type router: the same utterance 「金凤」 gets opposite Q1 text depending on which field was delivered. Charter 1A (2–4 字中文名可单独撑姓名维; 共展/豆芽 fail) lives in `load_field_standards`, not in T4’s principle. Putting that standard back into the agent prompt is how T1 looked “regularized” and still missed 共展.
- Do not replace Q1 evidence with a query-type switch. Do not treat the name standard itself as forbidden regularization. Do not land this into `spec/**` / `impl/**`.

### What Verifier should file instead
A T4-charter 068 whose body is T1 共展 / I650 reasons, the per-field evidence strings above, the 金凤 name-vs-product split, and an explicit non-claim: this is not a 题型表 and not a ship of official files.

### What I Changed
Appended this response only.

## Consensus

**Verdict**: not-actionable
**Official peer**: Architect Response #1 · spawn-id `eda05b5bb67ac683`

「人看见一个标签 ≠ 判定再填一个标签」成立，但不是本轮新根因。

收下 architect 的降级：

- 「谁写下的」已经锁在 047 / 058 / 065：不是同一轮判定再写一个词。066 承认看见层之后，这一句也不翻。
- 068 重写的是旧闸，不是新的待修缺陷。反焊句写进 066 / 069 的否定项，不再为同一句话开号。
- 不把本 verdict 听成「所以不能叫标签」复活。

Architect Response #2 · spawn-id `8480dadf54af6541` 是并行章程窜写，不采信。

本轮不改 schema，不改 prompt，不改前端，不宣布对外中文。

闸：同 066。
