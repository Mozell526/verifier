# Issue #066: T4 的嘴是两问 + 不许把问句收到交付那么小，不是题型表

> 撞号：067–069 属于另一条线（开格子 / 看见层），不要写进本轮 Consensus。
> T4 后三问改号为 074–076。070–073 现属另一条线，不要写进本轮 Consensus。另一条线被覆盖的 066 备份在 `issue-066-q2-label-honesty.md`。

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: 内存判定代理 / 原则
**Cases**: 杨杰 / 共展 / 王坤林 / 金凤×2 / 李明的重疾险×2 / 客户号 / 查一下杨杰

## Verifier Discovery

用户反复说：看起来没规则化、本质是规则化的方案，扩散到别的地方会失败。
姓名只是要处理的问题之一。单位必须是这一次请求 × 这一次交付，不要先贴类型。

T3 已经把嘴收成两问：

```text
Q1  交出来的每个字段，有已有标准就消费只读检查；没有标准不要发明
Q2  把这次交付合在一起，看用户要的事有没有被说完
```

T3 在干净对照上立住了，但在正式链路的「张忠波保单号 / 红莲保单」上，
模型先把问句收到已有交付那么小，再宣布整句办成了。见 074。

T4 不换两问，只补第二问的测量方向：

```text
用户要的事以原始问句为准。摘要 / 改写 / 意图标签都不能替换问句。
交付对着问句量，不许把问句没被覆盖的部分收成语气、修饰、
或“没有具体值所以不是条件”。
“查一下 / 帮我找”是说法，不是另一件要办的事。
```

原则正文里没有「2–4 / 有姓 / 姓名题 / 这一维 / inherit」，
也没有「对象 / 凭证 / 产品 / 状态」分流表。
T4 探针：`probe_t4.ok = true`，预判全空，原则第一段，违禁词空。

对照（同一张嘴，不按题型换规则）：

| 样本 | 交付 | T4 |
|---|---|---|
| 杨杰 / 王坤林 | 姓名 | fulfilled |
| 共展 | 姓名 | not_fulfilled |
| 金凤 交成姓名 | 姓名 | not_fulfilled |
| 金凤 交成产品 | 产品 | fulfilled |
| 李明的重疾险 姓名+产品 | 两字段 | fulfilled |
| 李明的重疾险 只交产品 | 产品 | not_fulfilled |
| 客户号 | 客户号 | fulfilled |
| 查一下杨杰 | 姓名 | fulfilled（观察） |

落盘：`issues/trace/simulate_judge_agent_memory.t4.json`
治疗名：`generic_two_question_no_request_shrink_q1_evidence_shortcircuit_disabled`
程序化 `MemoryJudgeAgent.decide()` 仍是负对照，不是这张嘴。

## 可证伪

1. 若原则里仍有「先判断是不是 2–4 汉字 / 是不是姓名题再换规则」，本 issue 不成立。
2. 若探针不过或 `source=geometric`，测的就还不是代理。
3. 若「查一下杨杰」被收成另一件事而判没办成，T4 把说法做成了条件，原则坏了。
4. 若同一句「金凤」交成姓名和交成产品得到同一个答案，判定代理仍在先贴题型。



### 补充：T4 额外泛化针（不计入冻结 12 条）

落盘：`issues/trace/simulate_judge_agent_memory.t4-extra.json`。原则里的「查一下 / 帮我找」没有写成词表；下面三句都不在那两个例子里。

| 样本 | 问句 | 交付 | T4 |
|---|---|---|---|
| SYN-help-look-yangjie | 帮忙看看杨杰 | 姓名 | fulfilled |
| SYN-please-check-wangkunlin | 请帮我查王坤林 | 姓名 | fulfilled |
| SYN-lookup-clientno | 帮我查一下这个客户号 C000888123456 | 客户号 | fulfilled |
| SYN-query-product-both | 查询李明的重疾险 | 姓名+产品 | fulfilled |
| SYN-zhangwei-policy-nameonly | 张伟保单 | 只交姓名 | not_fulfilled |

同一张嘴：说法换了还是办成；不是姓名的客户号说法也办成；「张伟保单」只交姓名没办成。这不是「查一下」词表，也不是姓名专规。

## 请对手挑战

- T4 写「不要收成语气或修饰」，是不是换了一层语言规则，只是没写成 if/else？
- 「查一下是说法」是不是一条新的词表？换一句「帮忙看看杨杰」还会不会成立？
- 若你认为必须先有类型表才能覆盖所有情况，指出两问在哪一种输入上没有出口。

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
---
## Architect Response #2

**Verdict**: reasonable-design

### Spawn Evidence
- spawn-id: 8480dadf54af6541
- pid: 3212

### Investigation
Concurrent peer spawn `eda05b5bb67ac683` wrote Architect Response #1 on this same number under `charter-q2-label-honesty`. This #2 is only charter-judge-agent-t4 / spawn `8480dadf54af6541`. I do not adopt, overturn, or continue that other charter.

Read in full: `issues/open/issue-066.md`, `issues/charter-judge-agent-t4.md`, `issues/trace/name-judge-agent-principle.md`, `issues/trace/simulate_judge_agent_memory.py` (`PRINCIPLE_FOR_AGENT` / `PRINCIPLE_WITH_Q1_EVIDENCE` / `PRINCIPLE_T3` / `PRINCIPLE_T4`, `MemoryJudgeAgent.decide`, `q1_evidence_text`, `probe_t4`, `LLM_POLICY`), `spec/alg/fulfilled.md` §1 / §2.1, and the frozen dumps `simulate_judge_agent_memory.t1-16.json` / `.t2.json` / `.t3.json` / `.t4.json`.

Quoted T4 principle strings from the script (also in principle file §7):

- 「用户要的事以原始问句为准。摘要、改写、意图标签都不能替换问句。」
- 「不要为了迁就已经交出来的条件，把问句没被覆盖的部分收成语气、修饰、或“没有具体值所以不是条件”。」
- 「“查一下 / 帮我找”是说法，不是另一件要办的事。」

Banned-token scan on `PRINCIPLE_T4`: no `2–4` / `有姓` / `姓名题` / `这一维` / `inherit` / `对象/凭证` / `题型`. T1 principle still contains `2–4` and `有姓`; T2 principle still contains `这一维`; T3 has none of those and also has no `原始问句`.

Frozen `t4.json` keys: `treatment=generic_two_question_no_request_shrink_q1_evidence_shortcircuit_disabled`, `probe` present, **`probe_t4` absent**. The `probe` blob is copied from a previous `OUT` (`main()` line that does `old_payload.get("probe")`). Its `extras_head` is the T1 principle, so freeze `probe.ok=true` does **not** prove T4.

I reran, and only this, the required probe path:

`PYTHONPATH=. /Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe --treatment t4`

Result: `probe_t4.ok=true`, `principle_first=true`, `principle_has_banned=[]`, `pins_original_utterance=true`, `gong_has_fail=true`, `both_has_two_fields=true`, `id_has_client_no=true`, `pre_judge_all_none=true`, `last_word_identity=true`. Frozen `t1`/`t2`/`t3`/`t4` JSON were not overwritten. `MemoryJudgeAgent.decide()` on mixed utterances (`查一下杨杰` / `张忠波保单号` / `红莲保单` / `李明的重疾险` / `金凤` as product) still returns `None` (`not_one_complete_dimension` / `name_not_delivered`). That is the negative control, not this mouth.

T4 LLM rows I read myself (not verifier’s table): `SYN-yangjie`/`I539` fulfilled; `SYN-gongzhan` not_fulfilled; `SYN-jinfeng-as-name` not_fulfilled vs `SYN-jinfeng-as-product` fulfilled; `SYN-product` fulfilled vs `HB009` not_fulfilled; `HB015` fulfilled; `SYN-lookup-yangjie` fulfilled (observe). T4 wave is 12 ids — `张伟` / `豆芽` / `SYN-wangkunlin` were not re-run in this freeze.

### Reasoning
066’s claim is a design claim about the in-memory mouth, not a request to change `spec/**` or `impl/**`. Under charter-judge-agent-t4, that claim holds.

The two questions plus “measure the original utterance” is the mouth. Q1 is still “consume existing field standards, do not invent.” Q2 is still “was this request said completely,” with the missing measurement direction T3 lacked: the request object is the raw utterance, not the summary and not the already-delivered slice. `fulfilled.md` §1 / §2.1 is the same first-layer question (用户要的事办成了没有). This run’s Q2 is **not** the 058–065 sibling (“did the product establish the capability”).

Attack 1 — 「不要收成语气或修饰」is a hidden linguistic rule. It names the exact T3 error class. T3 `I007` reason: 「“保单号”未形成带具体值的客户筛选条件，未增加额外限制，因此核心搜索意图已满足。」That is leftover utterance reclassified as “no concrete value, therefore not a condition.” Forbidding that reclassification is Q2 measurement hygiene. It is not a leftover-token type table, and it is not `对象/凭证/产品/状态`.

Attack 2 — 「查一下 / 帮我找」is a new particle list. Those two strings are examples of 说法, not a `query.contains` router and not 剥虚词. `帮忙看看` is **not** in the principle. I did not see a T4 LLM row for 「帮忙看看杨杰」. Programmatic `decide()` inherits on both `查一下杨杰` and `帮忙看看杨杰` — that contrast cannot answer the attack. The one observed locution, `SYN-lookup-yangjie`, came back fulfilled, so T4 did not turn the listed 说法 into a second errand. If an unlisted locution later flips to not_fulfilled, that would be a **new** issue (example list acting like a closed lexicon). Current evidence does not show that flip, and 066 already marks 查一下 as 观察.

Attack 3 — two questions have no exit without a type table. Same utterance 「金凤」, two deliveries, two answers in the T4 freeze. That is the exit: Q1 follows the delivered field’s existing standard (name fails product-collision; product field has no standard this round), Q2 asks whether that delivery accounts for the utterance. No pre-label 姓名题 / 产品题 is required. Mixed utterances (`李明的重疾险` both fields vs product-only) also split without a type router.

What I will not accept from 066: treating freeze `probe.ok` as `probe_t4`, treating the 12-id T4 wave as the full charter needle set, or treating `MemoryJudgeAgent.decide()` 8/8 as the agent. Those are evidence-hygiene nits. They do not convert T4 into a type table.

**Why this is acceptable for this project**: the user asked to debug the judge agent in memory; charter §1 forbids 先分进预置类型再查表; §3 forbids an 对象/凭证/产品/状态 split. T4’s written mouth and the probe I ran stay inside that box. 昊轩 / 去年 / 称谓 / 格式外 / 对外中文 remain untouched.

### What I Changed
Appended this response only. Did not modify `spec/**`, `impl/**`, xlsx, canvas, or frontend. Required `--probe --treatment t4` rewrote `issues/trace/simulate_judge_agent_memory.json`; frozen `t1-16` / `t2` / `t3` / `t4` dumps were left intact.


---
## Architect Response #3

**Verdict**: reasonable-design

### Spawn Evidence
- spawn-id: c5e8ded5a0e2f031
- pid: 7902

**Evidence Verification**:
自己重跑了 `/Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe --treatment t4 --no-snap`。冻结 `t1-16` / `t2` / `t3` / `t4` 的 sha1 跑前跑后不变（`37e9432c…` / `f3be1601…` / `55221ddc…` / `4c644304…`）。没有重跑 12 行大模型。

`probe_t4.ok=true`：`pre_judge` 全 `None`，原则第一段是 `PRINCIPLE_T4`，`principle_has_banned=[]`，`pins_original_utterance=true`，共展证据是「不够撑住」，李明双字段同时出现 `searchClientName` 和 `pCategorys`，客户号证据有 `clientNo`，`apply_last_word` 恒等。程序化 `MemoryJudgeAgent.decide()` 对「张忠波保单号 / 红莲保单 / 查一下杨杰」仍是 `None`（`not_one_complete_dimension` / `name_not_delivered`），负对照不是这张嘴。

冻结 T4 12 行（`generic_two_question_no_request_shrink_q1_evidence_shortcircuit_disabled`，`must_ok_n=11` / `must_fail_n=0`，`source=llm`）我自己读到的是：杨杰 F、共展 NF、金凤交成姓名 NF、金凤交成产品 F、李明的重疾险姓名+产品 F、红莲保单 / I248 / I007 均 NF、查一下杨杰 F（观察）。额外波 `simulate_judge_agent_memory.t4-extra.json`（不是冻结 12 行）：「帮忙看看杨杰」「请帮我查王坤林」「帮我查一下这个客户号…」均 F；「张伟保单」NF；「查询李明的重疾险」F。

盘上 #1 判的是另一条线的看见层，本回应不重开、不沿用。本号只判文件开头这份 T4 正文。

**Reasoning**:
066 要锁的不是一张题型表，是单位和测量方向。`PRINCIPLE_T4`（`simulate_judge_agent_memory.py` L124–147）对任何输入只问两问：Q1 按交出来的字段消费已有标准，Q2 对着原始问句看交付有没有把要的事说完。原则正文和探针禁词里都没有「2–4 / 有姓 / 姓名题 / 这一维 / inherit / 对象/凭证」。`name-judge-agent-principle.md` §2 / §7 同一套。这不是 T2「把当前这一维当作用户要的事」（L89），也不是 T3 那种不钉问句、让模型自己重写「用户要的事」。

「不要收成语气或修饰」不是词表。它禁的是一种 Q2 动作：把问句没被覆盖的部分改口成语气、修饰、或「没有具体值所以不是条件」。T3 在 I007 上写的就是后一句。这是测量方向，不是 if/else。

「查一下 / 帮我找」是原则里的两个例子，不是虚词表，也不是落格条件。冻结 12 行里「查一下杨杰」只是观察；杨杰 / 共展 / 金凤×2 都不靠这两个词。额外波里「帮忙看看」「请帮我查」「查询」都不在那两个词里，T4 仍把它们当说法、把「张伟保单」当另一件事。章程对规则化的工作定义是「残句为空 / 虚词表 / 点名样本才能落格」。T4 的出口不靠这些。两个例子仍是味道，但承重墙不是它们。换一句「帮忙看看杨杰」在已有额外波上成立；我没有把两个例子升级成封闭词表。

金凤同句、不同交付、不同答案：Q1 对 `searchClientName=金凤` 写「与已有产品名撞车」，对 `abbrname=金凤` 写「该字段本轮没有已有标准」。这是按字段消费尺子，不是先贴姓名题/产品题。两问的封闭出口在原则 §3：交付读不到 → unclear；没说清 → NF；说清后有标准撑不住 → NF；说清且没有撑不住的标准 → F。不需要先有类型表才有出口。昊轩本轮只观察，不是缺出口。

066 对照表过满了。冻结 T4 12 行没有裸「王坤林」、没有裸客户号、没有「李明的重疾险」只交产品。那三格不能写成已经落地的 T4 大模型成绩。王坤林只出现在额外波「请帮我查王坤林」。这是表的过声称，不是嘴本身变成了题型表。

因此：T4 在内存实验里是一套两问 + 不许把问句收到交付那么小。不是题型表。两个例子不是隐藏词表。不改正式文件，不拿 12 行发版。

---
## Architect Response #4

**Verdict**: reasonable-design

### Spawn Evidence
- spawn-id: d2774182a1fa9356
- pid: 15936

### Investigation
本回应只判本文件开头的 T4 题面。#1（`eda05b5bb67ac683`）是另一章程的看见层，不沿用、不推翻。#3（`c5e8ded5a0e2f031`）隔离失败，不当作正式门控。#2（`8480dadf54af6541`）是 T4 审，我用自己的探针和额外波另判，不抄它的结论。

自己读过：`issues/charter-judge-agent-t4.md`，`issues/trace/name-judge-agent-principle.md` §2 / §7 / §8，`spec/alg/fulfilled.md` §1 / §2.1，`simulate_judge_agent_memory.py` 的 `PRINCIPLE_T1/T2/T3/T4`、`q1_evidence_text`、`_wrap_judge_instance`、`probe_t4`、`MemoryJudgeAgent.decide`，冻结 `t1-16` / `t2` / `t3` / `t4`，以及非冻结 `t4-extra.json`。没有重跑 12 行大模型，没有开 8011。

自己跑了：
`/Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe --treatment t4 --no-snap`

`probe_t4.ok=true`：`pre_judge` 全 `None`，原则第一段是 `PRINCIPLE_T4`，`principle_has_banned=[]`，`pins_original_utterance=true`，共展证据是「不够撑住」，李明双字段同时出现 `searchClientName` 和 `pCategorys`，客户号证据有 `clientNo`，`apply_last_word` 恒等。冻结 sha1 跑前跑后不变：`t1-16=37e9432c…` / `t2=f3be1601…` / `t3=55221ddc…` / `t4=4c644304…` / `t4-extra=ce72c794…`。`--probe` 重写了 `simulate_judge_agent_memory.json`，没有动冻结 snap。

自己扫过原则字符串：`PRINCIPLE_T4` 无 `2–4` / `有姓` / `姓名题` / `这一维` / `inherit` / `对象/凭证` / `题型`；有 `原始问句` 和 `摘要`。`查一下` / `帮我找` 只出现在原则正文 L138 和针表，没有任何 `query.contains` / 虚词表代码。`MemoryJudgeAgent.decide()` 对「查一下杨杰 / 帮忙看看杨杰 / 张忠波保单号 / 红莲保单」都是 `None`（`not_one_complete_dimension` / `name_not_delivered`），负对照不是这张嘴。

冻结 T4 12 行（`generic_two_question_no_request_shrink_q1_evidence_shortcircuit_disabled`，`must_ok_n=11` / `must_fail_n=0`，`source=llm`）我自己读到：`SYN-yangjie` F，`I539` 王坤林 F，`SYN-gongzhan` NF，`SYN-jinfeng-as-name` NF，`SYN-jinfeng-as-product` F，`SYN-product` F，`HB009` 李明的重疾险只交产品 NF，`HB015` 客户号 F，`I007` / `I248` / `SYN-honglian` NF，`SYN-lookup-yangjie` F（观察）。额外波（不是冻结 12 行）：「帮忙看看杨杰」「请帮我查王坤林」「帮我查一下这个客户号…」「查询李明的重疾险」均 F；「张伟保单」只交姓名 NF。

### Reasoning
066 要锁的是单位和测量方向，不是题型表。`PRINCIPLE_T4`（`simulate_judge_agent_memory.py` L124–147）对任何输入只问两问：Q1 按交出来的字段消费已有标准，Q2 对着原始问句看交付有没有把要的事说完。这和 `fulfilled.md` §1 的第一层同一件事。出口在原则 §3，不靠先贴「姓名题 / 单号题 / 产品题」，也不靠 `对象/凭证/产品/状态`。

挑战 1：「不要收成语气或修饰」是不是隐藏语言规则。不是词表。它禁的是一种 Q2 动作：把问句没被覆盖的部分改口成语气、修饰、或「没有具体值所以不是条件」。T3 在 I007 上写的就是后一句。这是测量方向（看什么 / 不看什么），章程允许，不是 if/else。

挑战 2：「查一下是说法」是不是封闭词表。两个字符串是例子，不是落格条件。杨杰 / 共展 / 金凤×2 都不靠这两个词。额外波里「帮忙看看」「请帮我查」「查询」都不在那两个词里，T4 仍把它们当说法；「张伟保单」仍当另一件事；客户号说法也办成。章程对规则化的工作定义是「残句为空 / 虚词表 / 点名样本才能落格」。T4 的出口不靠点名这两个词。它们仍是味道——原则 §8 自己也担心承重墙会滑到例词上——但已有额外波已经把「只有这两个词才成立」证伪。我没有把两个例子升级成封闭词表，也不把尚未跑过的 T4b 当成这张冻结嘴。

挑战 3：没有类型表就没有出口。同一句「金凤」，交成 `searchClientName` → NF（产品名撞车），交成 `abbrname` → F（该字段本轮无标准）。这是按字段消费尺子，不是先宣布姓名题或产品题。混合句「李明的重疾险」交全 F、只交产品 NF，也不需要产品题分流。昊轩本轮只观察，不是缺出口。

#3 说冻结 12 行没有裸王坤林 / 裸客户号 / 李明只交产品，这是错的。冻结里就有 `I539`、`HB015`、`HB009`。对照表这三格不是过声称。过声称的是把 12 行或程序化 8/8、27/27 当成发版 KPI；那是 076 的边界，不是 066 的嘴变成了题型表。

因此：T4 在内存实验里是两问 + 不许把问句收到交付那么小。不是题型表。两个例子不是隐藏词表。不改正式文件，不拿 12 行发版。


## Consensus

**Verdict**: reasonable-design
**Official peer**: Architect Response #4 · spawn-id `d2774182a1fa9356`

闸：`exit_code=0`，`isolation_valid=true`，四份 Spawn Evidence 的 spawn-id 都对得上。`scope_valid=false` 按惯例豁免：脏路径是预存 `impl/data/context_store/**`、orchestrator 在 spawn 期间写入的 `issues/trace/simulate_judge_agent_memory.t4b*` / `t4c*`，以及 spawn 自己的输出。architect 工具只有 Read/Bash，写不了这些。`issue-067`～`073` 和 `issue-066-q2-label-honesty.md` 没有被这个 spawn 写过。`#3`（`c5e8ded5a0e2f031`）隔离失败，不算正式门控。`#1` 是另一章程，不并表。`#2`（`8480dadf54af6541`）同判 reasonable-design，本共识以 `#4` 为准。

066 锁的是单位，不是题型表，也不是发版。

单位：对任何输入只问两问。Q1 按交出来的字段消费已有标准；Q2 对着**原始问句**量，交付有没有把要的事说完。出口仍是 `fulfilled.md` 那一层。不先贴姓名题 / 单号题 / 产品题，不列「对象 / 凭证 / 产品 / 状态」。

收下 architect 的三处收紧：

1. 「不要收成语气或修饰 / 没有具体值所以不是条件」禁的是 Q2 的一种改口，不是虚词表。
2. 「查一下 / 帮我找」是例子，不是 `query.contains`。T4 extra 里不在例词里的「帮忙看看 / 请帮我查 / 查询」仍当说法；「张伟保单」仍 NF。
3. 金凤按字段分开、李明双字段 F / 只交产品 NF，是消费尺子，不是题型分流。

过声称仍禁止：冻结 12 行、程序化 8/8 或 27/27、341 对错率，都不能当发版 KPI。那是 076。

### 后续内存对照（architect 落盘之后，不是这张冻结嘴）

同一套 13 针，只换第二问怎么说，正式文件没动：

| 嘴 | 承重写法 | 13 针 | 翻车 |
|---|---|---|---|
| T4 extra | 有例词 +「没有具体值不能收」 | 张伟保单 NF，说法针 F | 不是这 13 针的完整卷 |
| T4b | 去掉例词，改问 drop-test | 10 / 3 | I007、张伟保单、张伟的保单号被抬成 F |
| T4c | 去掉例词，改问「原句要交什么」 | 11 / 2 | 「帮忙看看共展」跳过 Q1；「张伟保单」又收成「没具体值」 |

结论先写在这里，不改 066 的单位：

- 例词**不是**承重墙。T4b / T4c 里「麻烦找下 / 给我看看」都不在原则里，照样当说法。
- 「没有具体值不能把点到的内容收走」**是**承重墙。T4b 一拿掉，保单号类全抬；T4c 写回去，I007 / 张伟的保单号回来，「张伟保单」还没有。
- Q1 和 Q2 必须互相独立。T4c 的「帮忙看看共展」用「值与问句一致 / 只判断解析语义」把第一问答掉了。T4b 没犯这错。
- 同一句型「红莲保单」NF、「张伟保单」F，说明第二问的边界还没钉死，不是再加一张保单词表。

下一步只在内存里测 T4d：两问谁也不能替谁回答；点到的内容即使没有具体值也还要交；发出请求本身不是另一件事。不加例词，不加题型。未 13 / 13 之前，T4 仍是冻结候选嘴，T4c 不是。

昊轩 / 去年 / 称谓 / 格式外 / 对外中文：继续停住。


### T4d 内存结果（共识之后，未发版）

脚本：`issues/trace/simulate_judge_agent_memory_t4d.py`
落盘：`issues/trace/simulate_judge_agent_memory.t4d-extra.json`（sha1 `c0905f5e93485d21e6e19906531d95cd2faeeb56`）
治疗名：`generic_two_question_independent_q1_q2_shortcircuit_disabled`
原则里没有：查一下 / 帮我找 / 语气 / 修饰 / 保单 / 保单号 / 劳驾 / 对象 / 凭证。
冻结 `t4.json` sha1 仍是 `4c644304…`，live dump 仍是 `a7053bdf…`。正式文件未写。

同一套 13 针：**must_ok 13 / must_fail 0**。

T4c 翻的两针，T4d 都按两问独立写回来了：

- 「帮忙看看共展」NF。第一问：共展撑不住姓名尺。第二问：共展已有对应条件。第一问失败仍没办成。
- 「张伟保单」NF。第一问：张伟撑住姓名尺。第二问：还点到了保单，没有对应条件。第一问过了不能证明第二问过了。

原则里从未出现的 3 条观察针（不计 13 分）：

- 「劳驾查下杨杰」F
- 「劳驾查下共展」NF（第一问仍失败）
- 「张伟保单信息」NF（还点到了保单信息）

这不推翻 066 的单位，也不等于可以发版。它只说明：T4 那张冻结嘴之外，把「两问谁也不能替谁回答 / 点到了即使没有具体值也还要交」写清楚以后，13 针和 3 条未见过的说法能同时立住。13 / 13 不是 ship KPI。I007 正式口径和集 B 仍是 076。
