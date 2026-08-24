# Issue #013: fulfilled 单轴无法同时回答「办成了没有」和「产品位内是否尽到当前可支持」

**Class**: boundary
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Protocol / 评测词表（不是某一条 case 的对错）
**Cases**: 不作本轮判定对象。仅用「去年」和「格式外」说明碰撞。

## Verifier Discovery

用户问的是原则：当前 `fulfilled` 判断的是用户需求是否满足；有时还要看「产品功能定位以内、系统能否明确当前尚未支持」。这层现在缺。2 和 3 只是让这层缺口露出来，不是本 issue 要重判的对象。

### 触发输入

用户原话（本轮）：2 和 3 像同一类——确实不满足业务需求，但系统当前已有能力和资料下也算尽力了；希望单独开标签，用词不要业务向的 fulfilled，而要产品定位内的可支持承认；不要做成完全 IT 的东西。要围绕原则上辩论：新增标签，还是改 `fulfilled.md`。

### 期望（协议里已经分开的两件事）

`spec/alg/fulfilled.md` §1 原文把 Judge 收成一件事：

> 我们：评测系统（Judge），只看一件事——系统有没有帮用户办成想办的事。
>
> 判断分两层：第一层：用户要的事办成了没有？第二层：手里的材料够不够回答第一层？

同文件开篇：

> 词表沿用 `spec/info-volume.md`，不新增第四态。

`spec/info-volume.md` 对整体状态写明：

> 值域完全相同，依然是 fulfilled / not_fulfilled / not_evaluable，不引入 partial 之类的新枚举

`spec/alg/authority.md` §1 把另一件事单独拆走：

> Authority Agent 只解决“标准是否确定”，不判断某个实际输出是否满足用户要求。

§8.3 职责内能力缺失的消费仍回到需求轴：

> statement = 职责内能力缺失（应具备但未实现/表达不了）
>     → 不强制改状态；Judge 结合 live 实际交付判断：
>         期望未达成 → not_fulfilled（理由 + 长期优化点）
>         实际达成   → fulfilled
>     → 不能因为“功能未实现”自动降级为 not_evaluable

也就是说：协议已经承认「职责 / 能力」是另一类问题，但 Judge 对外只留下需求三态。用户要的「产品位内尚未支持是否被承认」在出口处被压扁了。

### 实际

三态把三种不同的「没办成」压成同一个词，或错误地挤进另外两个词：

| 实际发生的事 | 硬塞进 F | 硬塞进 NF | 硬塞进 NE |
|---|---|---|---|
| 核心结果没给到 | §7.1 禁止用态度换 F | 正确（需求没满足） | §7.2 禁止把没交付包装成说不清 |
| 产品位内、可明确尚未支持，且系统如实披露 | §7.1 / D3 禁止「如实拒绝=办成」 | 看起来像系统犯错，和漏条件无法区分 | NE 的定义是「说不清办没办成」，不是「没办成但处置对」；且是临时态 |
| 未形成产品可执行对象（格式外 / 输入坏） | 同样撞 D3 | 等于要求系统交出空间外对象（009 已否） | 输入坏这一格合法，但丢失「处置是否正确」 |

`fulfilled.md` §2.2 原文把「功能未实现」直接写进没办成：

> 不区分原因：… 功能本身未实现，但用户期望已提出。

这对**需求轴**是对的：用户要的年筛选没给到，就不是办成了。但它同时删掉了产品轴：系统是否在产品定位内正确承认「投保年尚未支持」。

### 已有字段为什么不够

必须先核「是不是已经能回答」，再谈新标签（章程 §5）。

1. **`blocking`**（`impl/core/schema/judge.py` `BusinessExpectation.blocking`；`impl/core/judge.py` 只按 blocking 聚合 overall）  
   回答的是「这维缺了会不会阻断核心目的」。它是权重，不是产品支持处置。一个 non-blocking 的「去年」仍然只能标 F/NF/NE，仍然回答「这维需求满足了没有」。归因侧（`info-volume.md`）对 NF/NE 会追失败根因——「正确披露尚未支持」会被当成缺陷去追。

2. **`required_capabilities`**  
   在期望上声明「需要什么能力」。不是评估「当前产品位是否支持、系统有没有正确承认」。

3. **`authority_tool_call_ids`**  
   只证明这次判断引用过哪次 `authority.resolve`。Authority 的 statement 类型（职责外 / 职责内能力缺失 / 职责内正常）不会作为 Judge 对外字段活下来。消费者打开一条评估，只看见 F/NF/NE。

4. **`inlive_boundary` / `is_supported`**  
   是资料定位和目录材料，回答「空间里有没有这维」。`material-positioning.md` 不变量 1：`current_behavior` 只能解释现状，不能当正式规则。用户也明确不要做成 IT 能力审计。把字段表 `is_supported=false` 直接当标签，正好踩 `fulfilled.md` §7.11「凭字段表里没有就推定职责外」。

所以缺口不是「协议里从来没人想过能力」，而是 **Judge 出口只有需求轴**。能力/职责在 Authority 入口被裁决，到出口被三态吃掉。

### 根因层

评测词表是单轴的。单轴可以诚实地回答「办成了没有」，不能同时诚实地回答「产品位内是否尽到当前可支持」。这不是模型选错半句（012），也不是 341 缺头部闸（010）。即使 006–012 全修完，用户问「这条是需求没满足，还是当前能力下已经尽到产品位」，对外仍然只有一个词。

### 和 007 / 009 的边界

- 007：同一句「去年」blocking 被模型自选，I046 / I161 不同侧。那是出口选择失控。
- 009：格式外空条件被打 NF，旧 F 又撞 D3。那是空间闸缺失。
- 本 issue：即使 blocking 选对、空间闸也有，**对外词表仍然无法区分「漏做了」和「尚未支持且承认了」**。007/009 是表面；本 issue 是词表层。

### 不是什么

- 不是要把「尽力了」做成第四个 fulfilled 值（开篇已禁第四态，info-volume 禁 partial）。
- 不是要把如实拒绝改回 F（D3 / §7.1）。
- 不是现在就给字段起名（章程 §4.1）。
- 不是重判 I046 / I034。

### 可证伪修复（原则，不是实现）

承认两轴，且需求轴词表不动：

- 轴 1 仍是 `fulfilled` 三态：用户要的事办成了没有。功能未实现、核心没给到，继续可以是 NF。
- 轴 2 是产品定位内的支持处置，必须能独立读出：定位内已支持 / 定位内可明确尚未支持 / 定位外 / 未形成产品对象 / 资料未定论。
- 轴 2 不得由 `is_supported` 或 current_behavior 自学；必须能回到 Authority 的职责/能力裁决，或空间「有没有这维」（positioning），而不是「这次代码怎么跑」。

没有轴 2 之前，禁止用「再调 F/NF/NE」回答用户这层问题。

### 未消元

- 轴 2 落在 assessment 还是另开摘要，留给 015。
- 2 和 3 是不是同一格，留给 014。

---
## Architect Response #1

### Investigation

Read in full: this issue; `issues/charter.md`; `issues/learning.md`; `issues/trace/support-axis-discovery.md`.
Quoted, not remembered:
- `spec/alg/fulfilled.md` L3–L5, L16, L23–L25, L38–L48, L50–L69, L128–L138, L158–L164, L184–L194, L207 (D3)
- `spec/info-volume.md` L270–L283
- `spec/alg/authority.md` L18, L295–L298, L470–L487, L489–L507
- `spec/alg/material-positioning.md` L86–L94, L186–L191
- `impl/core/schema/judge.py` L11–L40, L55–L60
- `impl/core/judge.py` L135–L161 (`_FULFILLMENT_STATUS_VOCAB`, blocking-only overall)
- `impl/core/authority_gate.py` L133–L141, L209–L268 (prefix parse + `authority_capability_gap` evidence)
- `spec/alg/investigate-judge.md` L687
Did not re-judge I046 / I161 / I034 / I616. Did not treat the write-up as already true.

### Spawn Evidence
- spawn-id: e288ae27bc0d2d22
- pid: 32717

**Judgment**: real-problem

**Evidence Verification**:
The single-axis claim is true as an *export* fact, false as a “protocol never thought about capability” story.

1. Judge is specified to answer one question. `fulfilled.md` L16:「只看一件事——系统有没有帮用户办成想办的事。」L23–L25 只有「办成了没有」和「材料够不够回答第一层」。开篇 L5「不新增第四态」。`info-volume.md` L271「不引入 partial」。
2. Capability / duty is a *different* question and already has a home. `authority.md` L18: Authority「只解决“标准是否确定”，不判断某个实际输出是否满足用户要求。」§8.2 L476 问题模板就是「是否支持 / 是否属于职责」。§8.3 L499–L503: `职责内能力缺失` 期望未达成 → `not_fulfilled` + 长期优化点，且「不能因为功能未实现自动降级为 not_evaluable」。
3. Existing Judge-facing fields do **not** independently answer the user’s second question:
   - `BusinessExpectation.blocking` (`schema/judge.py` L15; `judge.py` L138–L161) is weight for overall aggregation, not product-support disposition. A non-blocking 「去年」is still only F/NF/NE.
   - `required_capabilities` (`schema/judge.py` L19) is an expectation declaration, not an assessment of current positioning or of whether Live correctly acknowledged a gap.
   - `authority_tool_call_ids` (`schema/judge.py` L37–L40) is a pointer to a tool call. It does not publish the statement type.
   - `inlive_boundary` / catalog `is_supported` answer「空间里有没有这维 / 系统现在怎么配」。`material-positioning.md` 不变量 1（L86–L89）: `current_behavior` 不能冒充正式规则。`fulfilled.md` L194 §7.11 禁止凭字段表没有就推定职责外。把 `is_supported=false` 当标签正好踩这两条。
4. Deeper than the write-up: the 3-way duty/capability class already exists, but it is a *hidden intermediate*. `authority.md` L295–L298 写明结论类型是「prompt 约束，不新增 schema 字段」。Runtime `authority_gate.py` L133–L141 把「职责外 / 职责内能力缺失 / 职责内正常」前缀解析成 `boundary_outside` / `capability_gap` / `within_scope`，再用来改写 `status`（职责外→NE，能力缺失且被写成 NE→拉回 NF），偶尔往 `evidence_refs` 塞 `kind=authority_capability_gap`。消费者打开一条评估，结构化出口仍只有 `_FULFILLMENT_STATUS_VOCAB` 三值。归因 `info-volume.md` L282–L284 对整体 NF/NE 追失败根因——正确披露「投保年暂不支持」一旦落成 NF，就会被当缺陷去追。
5. Therefore: 三态可以诚实地回答需求轴；不能同时作为产品轴的第一类出口。这不是 007 的 blocking 漂移，也不是 009 的空间闸，也不是 012 的「LLM 选半句」。即使那三道闸全修完，对外仍无法独立读出「这条是漏做，还是定位内尚未支持且被承认」。

**Reasoning**:
I do **not** accept the framing that `fulfilled.md` §2.2「删掉了产品轴」。产品轴从来不是 Judge 的题。§2.2 L40–L45「不区分原因」对需求轴是对的，而且是付过代价的：D3 / §5 / §7.1 专门删掉「如实拒绝 → 办成」。把「尽力了」塞回 F，或发明第四个 fulfilled 值，都是在拆已经钉死的需求轴。

真正的裂缝是：**产品支持问题已经被问过、也被分成三类，但只被当成挑选 F/NF/NE 的中间变量，没有可组合、不改写需求轴的对外结果。** `reasoning_summary` 和 tool audit 里也许有散文，那不是章程 §5 要的「先核已有字段是不是已经能回答」。四个已有字段加上 evidence bag 里偶发的 `authority_capability_gap`，都不能让下游稳定读出「需求三态 × 产品支持处置」。

013 只需要钉这一句。轴 2 要几格是 014；格子挂在哪是 015。本 issue 的可证伪修复不得偷运五值枚举，也不得把「去年」「格式外」预先填进格子。

## Improvement Proposal

**Problem**: Judge 对外词表是单轴的；Authority 的职责/能力分类进得去、不能作为不改写三态的第一类结果读出来，所以「办成了没有」和「产品位内是否尽到当前可支持」无法同时被诚实地回答。

**Proposed Change**: 承认两问，需求轴不动。不要在本 issue 设计完整产品轴枚举。

**Design**:
    Q1 需求轴（已有，禁止改值域）
      FulfillmentAssessment.status ∈ {fulfilled, not_fulfilled, not_evaluable}
      overall 仍只由 blocking 的 Q1 聚合（impl/core/judge.py L138–L161）
      禁：第四态 / partial / 「如实拒绝=F」

    Q2 产品支持处置（新的对外可读结果，本 issue 只要求存在）
      必须能和 Q1 组合，且不得回写 status
      必须能回到 authority.md §8.2 问题模板，或 positioning「空间里有没有这维」
      禁止用 catalog is_supported / current_behavior 自学
      禁止在 013 里指定 α/β/γ 取值表（那是 014）
      禁止在 013 里指定挂 assessment / Authority schema / 独立 spec（那是 015 + 章程 §4.1/§4.2/§4.5）

最小验收句子（比 verifier 的五条更窄，避免和 014/015 抢拍板）：
1. 打开任意切片，能独立读出 Q1，并且能独立读出「这是不是产品位内、当前可明确尚未支持」。
2. Q2 为「定位内尚未支持」时，Q1 仍可按交付走 NF；不得因此变成 F-because-refused（`fulfilled.md` L160, L184, L207）。
3. 没有 Q2 之前，禁止用「再调 F/NF/NE」回答用户这层问题。

**Implementation Steps**:
1. Consensus 只收：单轴出口不够；已有 `blocking` / `required_capabilities` / `authority_tool_call_ids` / `inlive_boundary` 不能当 Q2。
2. 把「Authority 三类前缀已经存在、但是 hidden intermediate」写进根因，避免下一轮又去「发明」一套和 `authority_gate.py` 平行的分类。
3. 命名、写哪篇 spec、是否改 schema：留给章程 §4.1 / §4.2 / §4.5，本轮不改 `spec/**`、`impl/**`。

**Risks**:
- 把 013 写成「协议忘了能力」会推动错误修复：再造一套和 Authority 三类平行的标签。
- 在 013 里提前钉五值枚举，会把 014 的 α/β 拆分和 007 的 blocking 一起偷运进来。

**Verification** (copy-pasteable; this round is read-only):
    python3 -c "from pathlib import Path; ful=Path('spec/alg/fulfilled.md').read_text(); auth=Path('spec/alg/authority.md').read_text(); sch=Path('impl/core/schema/judge.py').read_text(); gate=Path('impl/core/authority_gate.py').read_text(); judge=Path('impl/core/judge.py').read_text(); assert '不新增第四态' in ful; assert '只看一件事' in ful; assert '功能本身未实现，但用户期望已提出' in ful; assert 'prompt 约束，不新增 schema' in auth; assert '职责内能力缺失' in auth; assert '不能因为“功能未实现”自动降级为 not_evaluable' in auth; assert 'required_capabilities' in sch and 'authority_tool_call_ids' in sch; assert 'capability_gap' in gate and 'authority_capability_gap' in gate; assert '_FULFILLMENT_STATUS_VOCAB = {\"fulfilled\", \"not_fulfilled\", \"not_evaluable\"}' in judge; print('013 protocol checks ok')"

**Why I Cannot Apply It**: 章程红线本轮不改 `spec/**` / `impl/**`；architect 只追加 issue。命名和落点属用户拍板。
---
## Architect Response #2

### Investigation

Read in full: this issue; charter-unsupported-label.md; support-axis-discovery.md; Architect Response #1.
Quoted / inspected myself (not from verifier paraphrase):
- `spec/alg/fulfilled.md` L4–L5, L16, L23–L25, L30–L69, L80–L91, L128–L138, L160–L164, L184–L194, L207, L209, L226–L227
- `spec/alg/authority.md` L18, L42–L46, L295–L298, L461–L468, L476–L487, L489–L507
- `spec/info-volume.md` L270–L284, L303–L315
- `spec/alg/material-positioning.md` L85–L94
- `spec/alg/investigate-judge.md` L687
- `impl/core/schema/judge.py` L10–L40, L55–L76
- `impl/core/judge.py` L135–L162
- `impl/core/authority_gate.py` L132–L192, L213–L272
- `impl/core/summary.py` L6–L49, L67–L80
Re-ran the 013 protocol asserts: all True.

### Spawn Evidence
- spawn-id: 6286c10358770df9
- pid: 39666

**Judgment**: real-problem

**Evidence Verification**:
Verifier’s quotes of `fulfilled.md` §1 / §2.2 and `authority.md` §8.3 match the source. I do **not** accept the inference that §2.2「删掉了产品轴」.

Reproduced, not assumed:
1. Public status vocab is one axis. `impl/core/judge.py` L135: `_FULFILLMENT_STATUS_VOCAB = {"fulfilled", "not_fulfilled", "not_evaluable"}`. `finalize_judge_result` / `_derive_overall_status` (L138–L162) only aggregate blocking Q1. No product-support field enters overall.
2. `FulfillmentAssessment` (`schema/judge.py` L27–L40) has `status` + `authority_tool_call_ids`. No disposition. `BusinessExpectation` has `blocking` (weight) and `required_capabilities` (declared need), not “currently supported / acknowledged”.
3. Authority already *asks* the product question. `authority.md` L476 template:「`<产品/模块> 是否支持 <用户要的能力>？`」. L295–L298: statement must start with `职责外` / `职责内能力缺失` / `职责内正常` — **「这是 prompt 约束，不新增 schema」**. The three prefixes are hidden intermediates by design, not a Judge export.
4. Gate consumes those prefixes to *rewrite Q1*, then throws the type away. `authority_gate.py` L145–L150 parse prefix → `boundary_outside` / `capability_gap` / `within_scope`. L215–L227: `boundary_outside` forces NE. L253–L272: `capability_gap` **only fires when status is already NE**, then rewrites to NF and appends `kind=authority_capability_gap`. If Judge already said NF (the common path for「投保年没给到」), **no `authority_capability_gap` evidence is written**. Q2 is then absent from both `status` and the evidence bag.
5. Downstream still cannot read the distinction. `summary.py` L6–L7: failure dimensions = every `not_fulfilled`. L67–L80: `authority_limitations` only scans **NE** assessments for `kind==authority_limitation`, not `authority_capability_gap`. `info-volume.md` L282–L284: overall NF/NE → chase failure root cause. A correct「投保年暂不支持」disclosure that lands NF is hunted as a defect.
6. `inlive_boundary` / catalog `is_supported` answer “space has this dimension?”, not “product position acknowledges unsupported”. `material-positioning.md` L87–L89 invariant 1: `current_behavior` cannot stand in for a rule. `fulfilled.md` L194 §7.11: cannot infer 职责外 from「字段表里没有」. L209 D5: field-in-catalog-but-unsupported is **not** auto-NF; first ask 该不该支持.

Therefore: existing fields do **not** already answer the user’s second question. Reconstruction via `authority_tool_call_ids` → tool audit → statement prefix is not a first-class answer, and the gate does not even materialize the evidence on the NF-already path.

**Reasoning**:
013 is a real *export* crack, not a claim that Judge forgot how to score demand.

`fulfilled.md` L16 / L23–L25 is explicit: Judge「只看一件事」—办成了没有；第二层只问材料够不够回答第一层. §2.2 L40–L45「不区分原因」+ L45「功能本身未实现，但用户期望已提出」is the correct demand-axis rule. It was paid for: §5 L160, §7.1 L184, D3 L207 all kill「如实拒绝 → 办成」. I refuse any repair that reopens that hole, or that invents a fourth fulfilled value (`fulfilled.md` L4–L5; `info-volume.md` L271).

The crack is: **the product-support question is asked (Authority §8.2) and classified (three statement prefixes), then used only as a picker for F/NF/NE.** After the pick, the classification is not a composable result. Charter §5 asked us to check existing fields first. `blocking`, `required_capabilities`, `authority_tool_call_ids`, `inlive_boundary`/`is_supported`, and the occasional `authority_capability_gap` evidence row all fail that check.

This is not 007 (blocking drift), not 009 (space gate), not 012 (LLM picking half a sentence). Those three can all be fixed and a consumer still cannot independently read「漏做」vs「定位内尚未支持且被承认」.

013 stops here. How many cells axis 2 has is 014. Where it hangs / whether schema changes now is 015 + charter §4.1 / §4.2 / §4.5. I will not pre-fill「去年 / 称谓 / 格式外」into a map; charter §4 parks those.

## Improvement Proposal

**Problem**: Judge’s public vocab is single-axis; Authority’s duty/capability class is a prompt prefix consumed to rewrite status, so「办成了没有」and「产品位内是否正确承认尚未支持」cannot both be read from a JudgeResult.

**Proposed Change**: Consensus records the two questions and forbids answering Q2 by retuning F/NF/NE. Do not design the axis-2 enum in this issue.

**Design**:
    Q1 需求轴（已有，值域冻结）
      FulfillmentAssessment.status ∈ {fulfilled, not_fulfilled, not_evaluable}
      overall = blocking-only aggregate of Q1 (`impl/core/judge.py` L138–L162)
      禁：第四态 / partial / 「如实拒绝=F」

    Q2 产品承认（本 issue 只要求：对外可读、不回写 status）
      必须能与 Q1 组合
      必须能回到 `authority.md` §8.2 问题模板，或 positioning「空间里有没有这维」
      禁止用 catalog `is_supported` / `current_behavior` 自学
      禁止在 013 指定 α/β/γ 取值表（014）
      禁止在 013 指定挂 assessment / Authority schema / 独立 spec（015 + 章程 §4）
      实现时复用 `authority_gate.py` L132–L150 已解析的三类前缀，不要平行再造一套职责分类
      注意：今天的 `authority_capability_gap` evidence **不是** Q2——它只在 NE→NF 改写时写入（gate L253–L272）

    最小验收（比 verifier 五条更窄）
      1. 打开任意切片，能独立读出 Q1，并且能独立读出「这是不是产品位内、当前可明确尚未支持」。
      2. Q2=定位内尚未支持 时，Q1 仍可按交付走 NF；不得变成 F-because-refused（`fulfilled.md` L160, L184, L207）。
      3. 没有 Q2 之前，禁止用「再调 F/NF/NE」回答用户这层问题。

**Implementation Steps**:
1. Consensus 只收：单轴出口不够；四个已有字段 + evidence bag 偶发 `authority_capability_gap` 不能当 Q2。
2. 根因写成「Authority 三类前缀存在，但是 hidden intermediate」，避免下一轮发明一套平行分类。
3. 命名、写哪篇 spec、现在是否改 schema：章程 §4.1 / §4.2 / §4.5，本轮不改 `spec/**`、`impl/**`。

**Risks**:
- Framing 013 as「协议忘了能力」pushes a second Authority.
- Locking a five-value enum here steals 014/015 and 007’s blocking question.

**Verification**:
    python3 -c "from pathlib import Path; ful=Path('spec/alg/fulfilled.md').read_text(); auth=Path('spec/alg/authority.md').read_text(); sch=Path('impl/core/schema/judge.py').read_text(); gate=Path('impl/core/authority_gate.py').read_text(); judge=Path('impl/core/judge.py').read_text(); assert '不新增第四态' in ful; assert '只看一件事' in ful; assert '功能本身未实现，但用户期望已提出' in ful; assert 'prompt 约束，不新增 schema' in auth; assert '不能因为“功能未实现”自动降级为 not_evaluable' in auth; assert 'required_capabilities' in sch and 'authority_tool_call_ids' in sch; assert 'capability_gap' in gate and 'authority_capability_gap' in gate; assert '_FULFILLMENT_STATUS_VOCAB = {\"fulfilled\", \"not_fulfilled\", \"not_evaluable\"}' in judge; print('013 protocol checks ok')"

**Why I Cannot Apply It**: 章程红线本轮不改 `spec/**` / `impl/**`。命名和落点是用户项。

---
## Consensus
**Verdict**: real-problem
**Official peer**: Architect Response #2 · spawn-id `6286c10358770df9`

单轴出口无法同时回答两件事：

- Q1：用户的事办成了没有（fulfilled 三态，值域冻结）
- Q2：产品位内，当前是否正确承认「尚未支持」

接受 architect 的收口，并写入本共识：

1. 这是**出口裂缝**，不是「协议忘了能力」。Authority §8.2 已经在问能力/职责，三类 statement 前缀也在分类；但分类只是挑 F/NF/NE 的隐藏中间量，挑完就吃掉了。
2. 已有字段都回答不了 Q2：`blocking` 是权重；`required_capabilities` 是期望声明；`authority_tool_call_ids` 是指针，不发布 statement 类型；`inlive_boundary` / catalog `is_supported` 是空间/现状，不能当正式规则。
3. 新证据成立：`authority_capability_gap` **只在 status 已是 NE 时**才改写 NF 并写入 evidence。Judge 直接打 NF（投保年没给到的常见路径）时，evidence bag 里连这条都没有。`summary.py` 把所有 NF 当失败维；`authority_limitations` 只扫 NE。
4. 禁止用调三态来补 Q2：不新增第四态 / partial；不得「如实拒绝 = F」；不得把产品轴写进 fulfilled §2 的题面。产品轴从来不是 Judge 的题。

013 到此为止。轴 2 有几格是 014。挂在哪、现在改不改 schema 是 015 + 章程 §4。本轮不预填「去年 / 称谓 / 格式外」功能地图。
