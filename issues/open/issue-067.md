# Issue #067: 承认「开格子是多一个标签」，不会让另外三个口复活

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 四个点名口 / 兄妹标签仍是兄妹
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

066 承认：开格子，在人看见的那一层就是结果上多一个标签。

用户点名的四个口是：

```text
A. 只是 not_fulfilled 的补充
B. 新增一个 judge 结果的标签
C. fulfilled 从 3 态扩到 4 态
D. 放到 not_evaluable 里面
```

本 issue 只钉：承认 066 之后，A / C / D 会不会因此变成合法宿主。不会。兄妹格上的标签，仍是兄妹，不是第一问三个词里的某一个，也不是第四个词。

### 第一问的嘴现在仍只有三个词

`spec/alg/fulfilled.md` §1：

> 本协议只评第一层：办成了没有。
> 「这类事现在是不是产品已经有的功能」见邻协议，不并进本协议三态，也不新增第四态。

同文件开篇：词表沿用 `spec/info-volume.md`，不新增第四态。

`spec/info-volume.md`：整体仍是 fulfilled / not_fulfilled / not_evaluable，不引入 partial；judge 只产出 fulfillment。

`impl/core/schema/judge.py`：`JudgeFulfillmentAssessmentOutput.status` 仍是一条状态。

所以 066 多出来的那一格字，若要保住第一问，就不能写进这条 status。写进去，就不是「旁边多一个标签」，是「原来那个标签换了词表」。

### 三个死口在 066 之后分别改写什么

| 点名口 | 066 之后若拿它当宿主 | 人看见的变成什么 | 踩哪条 |
|---|---|---|---|
| A. 只是 NF 补充 | 新标签只在没办成后面出现 | 办成了 × 没立住 这格从看见层消失；没办成被加上原因 | 062；fulfilled §2.2 不区分原因；authority §8.3 实际达成仍可 fulfilled |
| C. 3 扩 4 | 新标签变成 status 的第四个词 | 主表芯片、筛选、pill、矩阵 Status 同时多一种颜色 | 064；fulfilled §1；product-function §7.1 |
| D. 放进 NE | 新标签住进「说不清」 | 长期「没立住」被说成临时「判断不了」；办成了的正格被改口 | 063；fulfilled §2.3 临时态；authority_gate 能力缺失不得降 NE |

062 / 063 / 064 本轮不重开其对错。这里只核对：066 承认「多一个标签」，有没有把这三行改成「所以可以并进三个词」。没有。并进三个词，改的是第一问的嘴，不是给第二问开格子。

### 「用户只能看见 fulfilled」不能倒推回这三个口

现行出口确实只有第一问。061 / 048 已经把这件事收成看见问题：缺的是出口，不是定义。

066 之后，老实话是：

```text
若打开：人看见两个标签
        一个答办成了没有
        一个答产品把这件事立住了没有
若不开：人继续只看见第一个
```

把「现在只看见一个」兑换成「所以第二个必须住进第一个」，是 047 / 048 已经否过的倒推。066 只承认打开之后会多一个标签，不承认这个标签必须挤进已经存在的那一个。

### 不是什么

- 不是重开 062 / 063 / 064 的对错。
- 不是说 B 口因此整句复活。B 口里「判定再写一个词」仍按 068 另钉。
- 不是批准打开。

### 可证伪

承认 066 之后，A / C / D 仍能当宿主，要同时成立：

1. 结果上多一格字，必须写进已经存在的那一个 status；
2. 或者只在没办成 / 说不清后面才允许这格字出现；
3. 或者第四个词可以不改写办成了 / 没办成 / 说不清的含义。

1 把兄妹格收成改词表。2 把第二问单位改回「这一次没给到」。3 与 fulfilled §1、info-volume 三词归因切口、summary.html 四处同吃 status 直接撞。所以 066 成立，A / C / D 仍死。

## Proposed Change

Consensus 只锁：承认「开格子是结果上多一个标签」，不会让「只是 NF 补充 / 3 扩 4 / 放进 NE」复活。那个标签若打开，仍是第一问旁边的兄妹，不是三个词里的某一个，也不是第四个词。

不改 schema，不改前端，不宣布对外中文。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: eda05b5bb67ac683
- pid: 96523

### Investigation
自己重读了 067 全文，以及它用来挡 A/C/D 的协议和现行出口。不把 066 盘上那份 T4 正文当成 067 的前提；067 依赖的是本轮指派给 066 的看见层句。

- `spec/alg/fulfilled.md` §1：只评办成了没有；邻协议不并进三态，不新增第四态。§2.2：没办成「不区分原因」，明文包括「功能本身未实现」。§2.3：NE 是临时态，差在材料够不够判断办没办成。
- `spec/alg/authority.md` §8.3（L499–503）：职责内能力缺失「不强制改状态」；实际达成 → fulfilled；「不能因为『功能未实现』自动降级为 not_evaluable」。
- `impl/core/authority_gate.py` L215–268：职责外强制 `status=not_evaluable`；能力缺失只把误写 NE 抬回 `not_fulfilled`，不覆盖已经写下的 fulfilled。
- `spec/info-volume.md`：整体仍是三词，不引入 partial；judge 只产出 fulfillment，不产第二个对错维度（verdict 已删）。
- `impl/core/schema/judge.py` L94–104：一条 `status`。
- `impl/frontend/summary.html`：人现在能扫到的那一枚芯片就是「状态」+ `fulfillmentPill` 三色。矩阵 Status 要进 Judge 卡里的「业务预期达成矩阵」才看得到。
- 已锁、本轮不重开对错：046 / 062（不是 NF 附注）、015-A / 048 / 064（不是 3 扩 4）、015-C / 063（不是住进 NE）。047 / 048：现在只能看见 fulfilled，不得倒推成并进 status。

### Reasoning
066 若成立，改变的是看见层的叫法：开格子 = 结果上多一个标签。它不改变第一问三个词的含义。A / C / D 要当宿主，必须把这多出来的一格字写进已经存在的那一张嘴。写进去，答的就不是「给第二问开格子」，是「改写办成了 / 没办成 / 说不清」。章程要分开答的第三句在这里，不是字词游戏。

指定攻击逐条回：

1. 「用户只能看见一枚芯片。承认 066 之后，老实位置不就是他们已经在看的那枚吗？」  
   那枚芯片现在是 `status`。把它当成第二问的宿主，只有三条路：只在没办成时出现（A）、变成第四个词（C）、塞进说不清（D）。三条都改第一问的嘴。  
   - A：`fulfilled.md` §2.2 不区分原因；`authority.md` §8.3 允许「没立住 × 办成了」。标签只挂在 NF 后面，这格从看见层消失，第二问单位退回「这一次没给到」。062 / 046 已死，066 不能救。  
   - C：同一枚 pill / 同一 `status` 槽多一种颜色，哪怕只叫显示别名，064 / 015-A / `fulfilled.md` §1 已死。人看见的不是「旁边多一个标签」，是「原来那个标签换了词表」。  
   - D：长期能力缺失被说成临时「判断不了」。gate 对能力缺失的动作是抬回 NF，不是降 NE。063 / 015-C / §8.3 已死。  
   「老实位置是那枚芯片」听起来直白，其实是把「人看见的」焊回「进哪张嘴」。本轮不许焊。

2. 「一边承认是新标签，一边继续拒绝 A/C/D，是不是更巧辩？」  
   不是——前提是 标签 ≠ 那三个词里的某一个，也 ≠ 第四个词。用户点名的四个口里，A/C/D 说的都是第一问那张嘴怎么改。066 承认的是旁边多一格字。拒绝改嘴，不是拒绝叫标签。巧辩是 065 那种：用谁写去否认人看见。067 没有否认 066。

3. 「必须点进去才看得到的兄妹格，过得了『用户怎么看到』吗？」  
   过不了，也轮不到 067 来过。矩阵在 `renderJudgeCard` → `renderFulfillmentMatrix` 里，主表读者默认只看「状态」那一枚芯片。060 把规范格子放在矩阵 Status 旁边，061 已经把「现在看不看得见 / 主表要不要做派生投影」escalate 给章程 §4。067 若写成「所以点进矩阵就是用户看见标签的方式」，就是代选看见面。本 issue 只锁：A/C/D 不能因为 066 复活。兄妹格点不点得进，仍是 061，不是把标签塞回那枚芯片的理由。

067 不重开 062 / 063 / 064 的对错。不说 B 整句因此复活。不批准打开。不宣布对外中文。

### Improvement Proposal
- **Target**: 本 issue 的 Consensus 锁。不得改 `fulfilled.md`、`authority_gate.py`、`judge.py`、`summary.html`。
- **Change**: 只锁：承认「开格子是结果上多一个标签」，不会让「只是 NF 补充 / 3 扩 4 / 放进 NE」复活。若打开，那一格仍不是三个词里的某一个，也不是第四个词。不得把「用户现在只看见一枚芯片」兑换成「所以第二问必须住进这枚芯片」。不得把本锁写成「点进矩阵已解决用户怎么看到」。
- **Verification**: 对照 `fulfilled.md` §1 / §2.2 / §2.3、`authority.md` §8.3、`authority_gate.py` L215–268、`summary.html` L83–88 / L377 / L107、062 / 063 / 064 / 047 Consensus。任一表述把 066 听成 C（第四色）或 A（只挂 NF），或把 067 写成看见面已经打开，即未达本锁。
---
## Architect Response #2

**Verdict**: needs-more-info

### Spawn Evidence
- spawn-id: 8480dadf54af6541
- pid: 3212

### Investigation
Concurrent peer spawn `eda05b5bb67ac683` wrote Architect Response #1 on this same number under `charter-q2-label-honesty`. This #2 is only charter-judge-agent-t4 / spawn `8480dadf54af6541`. I do not adopt, overturn, or continue that other charter.

Read `issues/open/issue-067.md` in full. The title on disk is 「承认「开格子是多一个标签」，不会让另外三个口复活」. Body is 058–065 sibling placement (A/C/D cannot host a capability-established tag). It treats 066 as “开格子是结果上多一个标签.” The 066 actually on disk is the T4 two-question mouth. Charter-judge-agent-t4 §0 / this spawn: 058–065 is the other line; this run’s Q2 is whether the delivery accounted for the original utterance. I am not adjudicating A/C/D.

066 points here for the T3 live shrink. I inspected that evidence myself.

T3 freeze (`generic_two_question_request_level_q1_evidence_shortcircuit_disabled`), `probe_t3.ok=true` in that file, `must_fail_n=2`:

- `I007` 张忠波保单号 → `fulfilled`. Reason: 「实际条件完整交付了客户本人姓名张忠波，符合该字段既有标准；“保单号”未形成带具体值的客户筛选条件，未增加额外限制，因此核心搜索意图已满足。」
- `I248` 红莲保单 → `fulfilled`. Reason: 「用户核心条件是按“红莲”这一客户姓名搜索；实际交付了 searchClientName MATCH 红莲，符合既有字段标准，且未增加未表达的筛选限制。」
- Twin needle `SYN-honglian` 红莲保单 → `not_fulfilled`. Reason: 「用户同时表达了保单筛选意图，实际条件未包含任何保单相关约束。」

T4 freeze, same two live ids: both `not_fulfilled`, reasons cite 原问句 / 原句. T2 freeze already had both `not_fulfilled` **without** the T4 no-shrink paragraph.

`issues/trace/name_scenario_runs/I007.json`:
- `query` = 张忠波保单号
- `live.intent_summary` = `live.robot_text` = 「客户姓名为张忠波的客户」
- official `judge.reasoning_summary` already shrinks the same way (保单号仅为无值字段短语) and `fulfillment_status=fulfilled`

`I248` has **no** `name_scenario_runs/I248.json`. `llm_case_list()` therefore passes `extracted=None` for I248. Memory payload is query + `searchClientName=红莲` only. I248 enters from `simulate_1a_sufficiency_program.json` field-only mislifts (`current=not_fulfilled`, value≠query). Mixed pack `I007.note` = 「Keep current F; 保单号 is an attribute of the person, not a name veto.」 Script `LLM_POLICY["I007"]="not_fulfilled"`. Charter §2 / §4.5: that pack note is **not** locked policy; official keep-F is debateable and not for roles to ship.

Programmatic `decide("张忠波保单号", [(searchClientName, 张忠波)])` → `None` / `not_one_complete_dimension`. Q1 evidence on 张忠波 name: 「够撑住…2至4个汉字、有姓…」. So T3’s lift is Q2, not Q1.

### Reasoning
I cannot issue `real-problem` or `reasonable-design` on the text that is actually in this file. That text is the other charter. Confirming or denying A/C/D here would mix tables, which this spawn forbids.

The T3-shrink claim this number is supposed to carry is **not written here**. I will not pretend 067 already proved `via intent_summary`.

What the dumps do show, if a replacement T4 067 is filed:

1. T3 did shrink the request to the delivery on live `I007` / `I248`. The I007 reason is word-for-word T4’s forbidden move (“没有具体值所以不是条件”).
2. `intent_summary` is a real pipe on **I007 only**. The live summary already dropped 保单号. Neutralizing that field would remove one prompt that invites the shrink. It is **not** a sufficient fix: I248 in this memory wave has no extracted summary and T3 still lifted it, while `SYN-honglian` (same utterance + same pair, also no extracted) stayed not_fulfilled. That split is not a 保单 lexicon and is not explained by deleting `intent_summary`.
3. Adding T4 principle text is therefore not “the only conceivable patch,” but it is aimed at the right object: Q2 must measure the utterance. Deleting the summary is a context-pipeline change, not the mouth. T2 already avoided the lift without T4’s paragraph, so this is a T3 regression, not a newly discovered case.
4. I007 official keep-F must **not** be locked in this issue. Experiment policy NF and pack note F are in conflict **by charter**. T3 matching the official judge is not a win for this run. Changing official I007 expected status is escalate-to-project, not architect/verifier ship.

### What the replacement filing must contain
- T4-charter title/body. No 兄妹格 / A/C/D / 开格子.
- Verbatim T3 vs T4 vs T2 reasons for `I007` and `I248`, plus `SYN-honglian`.
- The I007 live `intent_summary` quote, and an explicit statement that I248’s memory trace has no such field.
- No 保单 word list, no official-file edit, no locked I007 ship sentence.
- If the claim remains “via intent_summary,” show the I248 prompt extras that actually carried a summary; I did not find them.

Until that file exists, 067 is not a T4 issue I can close.

### What I Changed
Appended this response only.

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `eda05b5bb67ac683`

承认「开格子是结果上多一个标签」，不会让「只是没办成的补充 / 3 扩 4 / 放进说不清」复活。

收下 architect 的切开：

- 人现在只能看见一枚「办成了没有」的芯片。这只证明看见层没开，不证明第二问必须住进这枚芯片。
- 只挂在没办成后面、变成第四个词、塞进说不清，改的都是第一问的嘴。062 / 063 / 064 继续死。
- 若打开，那一格仍是第一问旁边的兄妹，不是三个词里的某一个，也不是第四个词。
- 点进矩阵才看得到，过不了「用户现在怎么看到」。那是 061 / 章程 §4，不是把标签塞回这枚芯片的理由。

Architect Response #2 · spawn-id `8480dadf54af6541` 是并行章程窜写，不采信。

本轮不改 schema，不改前端，不宣布对外中文。

闸：同 066。
