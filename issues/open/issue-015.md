# Issue #015: 不要改 fulfilled 三态，也不要第四态；缺的是正交的产品支持处置出口

**Class**: boundary
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Protocol / 出口形状
**Cases**: 无。本 issue 只比较抽象方案。

## Verifier Discovery

013 说单轴不够。014 说 α/β 不能合成一格。本 issue 比较「改 fulfilled.md」和「新增标签」哪条不踩现行禁令，并且不把这层做成 IT 能力审计。

### 候选方案与当场否决

**方案 A：给 fulfilled 增加第四态**（partial / capability_limited / 尽力了）

当场否决。`fulfilled.md` 开篇「不新增第四态」；`info-volume.md`「不引入 partial」。第四态还会把两轴压回一个词：消费者仍然不知道这是需求没满足，还是能力尽到了。归因协议按三态追失败，第四态会把整条归因链路撕开。

**方案 B：改 fulfilled 定义，让「当前能力下尽力了」可以是 F**

当场否决。§5「如实拒绝、态度好 ≠ 办成」；§7.1 / §7.8 / D3 就是为删掉 draft 里「能力边界外正确拒绝 → 核心目标算办成」。这是协议里已经付出过代价的禁令，不能为了 2/3 的直觉再开回去。

**方案 C：把「尚未支持」塞进 NE**

部分合法、整体不够。NE 的四格是职责外 / 完全无关 / 依据不充分 / 输入坏（§2.3）。β 的「输入坏」可以走 NE。α 的「职责内能力缺失」§2.2 / §8.3 明确走 NF，且「不能因为功能未实现自动降级为 not_evaluable」。NE 还是临时态，要限期关闭。把「投保年尚未支持」做成说不清，等于宣布这不是长期产品缺口。

**方案 D：做一个 IT 能力标签**（字段 `is_supported`、接口有没有、操作符支不支持）

当场否决。用户不要完全 IT 的东西。`fulfilled.md` §7.11 禁止凭字段表没有就推定职责外。`material-positioning.md` 不变量 1 / §8.1：current_behavior 不能当正式规则，也不得把任意系统内配置标成 `inlive_boundary` 绕 Gate。轴 2 必须问「产品定位内是否声称做这件事、当前能否明确尚未支持」，问题模板已经在 `authority.md` §8.2：

> `<产品/模块> 是否支持 <用户要的能力>？或 <事项> 是否属于 <产品> 职责？`

这是产品问题，不是「YAML 里这行是 false」。

**方案 E：正交出口（推荐）**

需求轴三态不动。另留一个 **Judge 对外可读** 的产品支持处置，挂在切片（assessment / expectation）上，不进 overall 三态。

最小语义（中文名 / 枚举名留给章程 §4.1，这里只钉区分）：

| 处置 | 产品语言 | 从哪来（不是 IT 自报） | 需求轴仍怎么走 |
|---|---|---|---|
| 定位内已支持 | 这是产品现在就该办的 | Authority `职责内正常` 或空间内可表达维 | 按交付判 F/NF |
| 定位内尚未支持 | 产品位内，当前可明确还做不了 | Authority `职责内能力缺失`，且有独立资料钉住，不是字段表自报 | 该维需求未达成仍可 NF；是否 blocking 由核心/附加决定（007 留给用户） |
| 定位外 | 不是这个产品的事 | Authority `职责外` | NE（职责外） |
| 未形成产品对象 | 用户给的不是可执行对象 | 输入坏 / 空间外非法值（positioning 不变量 3） | NE 或 non-blocking 说明；排除 F 和 NF（009） |
| 未定论 | 现在说不清支不支持 | Authority unresolved + 缺料清单 | NE（依据不充分），临时 |

再加一个 **处置是否正确** 只评产品轴，不改需求轴：正确承认并披露 / 沉默或越权承诺 / 编造了空间外条件。这样「尽力了」变成可检验的处置质量，而不是一个新的办成。

### 已有挂钩，不必另起一套运行时

- 入口已经在：`authority.resolve` 的 statement 类型 + 空间闸（有没有这维）。012 要把出口从 prompt 搬进代码，轴 2 应吃同一道程序，而不是再写一段提示。
- 出口缺的是字段：`FulfillmentAssessment` 目前只有 `status` 和 `authority_tool_call_ids`（`impl/core/schema/judge.py`）。Authority 类型进得去、出不来。
- `JudgeResult` 注释已预留项目特有 `boundary_decision` 不下沉通用三态——方向对，但还不是产品支持处置，也还没有协议。
- `investigate-judge.md` 曾写「本轮不修改 FulfillmentAssessment / 三态词表」。那是当时调查轮次的冻结，不是「永远不许加正交字段」。加第四态才和那条冻结冲突；加正交字段不改三态词表。

### 改 fulfilled.md 还是新开一篇

本轮不改 spec（红线）。原则上：

- **fulfilled.md 只加「这不是什么」**：三态仍只回答办成了没有；禁止用 F 表示尽力；禁止第四态；指向轴 2。
- **轴 2 的定义不要塞进 §2 三态里**，否则下一次又会有人用一个词回答两个问题。
- 新开短文或写进 authority 消费章，由用户在章程 §4.2 选。角色不得代选。

### 和 013 / 014 的边界

013 是为什么要分轴。014 是轴 2 至少几格。015 是格子怎么出口、哪些写法已经死了。

### 不是什么

- 不是现在改 schema。
- 不是让 LLM 再选一个标签（那会回到 012）。
- 不是给 341 加一列人工分。
- 不是消灭「功能未实现 → 需求轴 NF」。α 在需求轴上仍可以是 NF；轴 2 把它从「漏做」里拆出来。

### 可证伪修复（原则）

同时满足才算答上用户的问题：

1. 任意切片能读出需求三态 **和** 产品支持处置，二者可组合，不互相改写。
2. α（去年这类）能标「定位内尚未支持 + 披露是否正确」，同时需求轴按核心/附加走，且不得变 F-because-refused。
3. β（格式外这类）能标「未形成产品对象」，不得标「尚未支持」。
4. 处置来源能回到 Authority 问题模板或空间有无，不能回到字段表自报。
5. overall 仍然只有三态，不引入 partial。

### 未消元 / 升级用户

- 字段中文名、英文枚举（§4.1）
- 写在 fulfilled 附录还是独立 spec（§4.2）
- 称谓进 α 还是 β（§4.4）
- 是否现在改 schema（§4.5）

---
## Architect Response #1

### Investigation

Read in full: this issue; issue-013; issue-014; charter §4.1 / §4.2 / §4.5.
Quoted:
- `fulfilled.md` L3–L5, L38–L69, L160, L184–L194, L207
- `info-volume.md` L270–L283, L305（`boundary_decision` 是项目中间产物，不该当通用字段）
- `authority.md` L295–L298, L461–L467, L476, L489–L507
- `material-positioning.md` L86–L94, L186–L191
- `impl/core/schema/judge.py` L27–L40, L55–L60
- `impl/core/judge.py` L135, L404（禁用 partial / partially_fulfilled）
- `spec/alg/investigate-judge.md` L41, L273, L687（本轮不修改 FulfillmentAssessment / 三态词表）
Compared schemes A–E against those texts. Did not choose a Chinese/English field name.

### Spawn Evidence
- spawn-id: e288ae27bc0d2d22
- pid: 32717

**Judgment**: real-problem

**Evidence Verification**:
The dead encodings are dead. Scheme E is the right *family* and the wrong *minimum inventory*.

**A. 第四态** — 当场否决，成立。
`fulfilled.md` L5「不新增第四态」。`info-volume.md` L271「不引入 partial」。`judge.py` L404 已经把 `partially_fulfilled` / `partial` 列为禁用同义词。第四态仍是一个词回答两个问题，而且会撕开按三态追因的归因链（`info-volume.md` L282–L284）。

**B. 改 F 定义，让尽力了可以是 F** — 当场否决，成立。
这就是 D3（L207）已经付过代价删掉的 draft 规则。§5 L160、§7.1 L184、§7.8 L191 不是风格问题，是禁令。不能为了 2/3 的直觉开回去。

**C. 塞进 NE** — 「部分合法、整体不够」成立，但要收窄。
NE 四格（L56–L59）里，β 的需求轴家就是「输入坏」；γ 的家就是「职责外」。α 明确不能住进 NE：`fulfilled.md` L48「功能未实现也是没办成，不降级为说不清」；`authority.md` L503「不能因为功能未实现自动降级为 not_evaluable」；L69 NE 还是临时态，限期关闭。把「投保年尚未支持」做成说不清，等于宣布这不是长期产品缺口。C 的错是「只用 NE 表达产品轴」，不是「β 走输入坏 NE」本身违法。

**D. IT 能力标签** — 作为 *标签定义* 否决，成立；作为 *证据输入* 不要一刀切。
用户不要完全 IT 的东西。§7.11、positioning 不变量 1 / §8.1 禁止用字段表 / `current_behavior` 自证职责外或正式规则。轴 2 必须问 §8.2 那句产品问题，不是「YAML 这行是 false」。
但 catalog `is_supported`、操作符空间仍然可以当 Authority 的候选资料，定位最多是 `current_behavior` 或已登记的 `inlive_boundary`。禁的是「字段自报 = 标签」，不是「永远不许看目录」。

**E. 正交出口** — 家族活着，verifier 的「最小语义」过大。

1. 用户原问是「新增标签，还是改 `fulfilled.md`」。协议能直接回答的是：改三态定义（B）和加第四个 fulfilled 值（A）都非法。活着的肯定项只有「另开一层、不进 overall 三态」，或「什么都不加、继续忍受出口缺口」。后者答不上用户的问题，但是章程 §4.5 的合法选项，不是协议解。
2. E 表里的五格不是最小。`定位外` / `未定论` / `未形成产品对象` 已经是需求轴 NE 成因或 Authority 三类之一。再在轴 2 复制一遍，会得到第二套三态。用户要的标签只有「定位内尚未支持」。014 的硬约束是 β/γ 不得吃这格，不是 β/γ 必须先有自己的一等取值。
3. 「定位内已支持」不是用户要的。支持的时候 Q1 已经能工作。补成完整划分看起来干净，但会新造一种读法：轴 2=已支持 且 轴 1=NF（漏做）——本意可组合，消费者会把两轴再揉回去。
4. 「处置是否正确」是第三个问题（披露质量），既不是办成了没有，也不是支不支持。把它塞进 015，轴数会从 2 变成 3。本轮先不要绑进同一字段。
5. 「入口已经在 Authority statement 类型，轴 2 应吃 012 同一道程序」——半对。Authority 三类前缀产生不了 β；β 是空间/输入闸（009/012），`authority.md` L467 还写明输入坏不依赖 Authority。一条程序吃不下 α 和 β。
6. `JudgeResult` L59 的 `boundary_decision` 不是预留钩子。`info-volume.md` L305 把它列进「该砍的项目中间产物，不该当通用字段」。方向「项目特有的东西不要污染通用三态」是对的，但不能把这条注释读成产品支持处置已经有座位。
7. `investigate-judge.md` L687「本轮不修改现有 FulfillmentAssessment / 三态词表」是真冻结，不是 verifier 一句话就能宣布作废。本辩论轮本来就不改 schema（章程 §3 / §4.5）。以后若用户选择加正交字段，那是显式解除这条冻结，不是「正交字段从来不叫改三态所以冻结从未存在」。

**Reasoning**:
015 该锁的是 *死路* 和 *活着的家族*，不该锁五值表、处置质量字段、以及挂在 assessment 还是 Authority schema。

对用户原问的直接裁决：
- 改 `fulfilled.md` §2 三态，让「尽力了」变成 F 或变成第四态 → 死。
- `fulfilled.md` 可以加「这不是什么」指针（三态仍只回答办成了没有；禁止 F-because-refused；禁止第四态；产品承认另见轴 2）。轴 2 的定义不要写进 §2，否则下次又会有人用一个词回答两个问题。
- 若要回答用户这层问题，只能加一层与三态正交、不进 overall 的标签。中文名、英文枚举、写在附录还是独立 spec、现在改不改 schema → 章程 §4.1 / §4.2 / §4.5，角色不得代选。

## Improvement Proposal

**Problem**: 能回答用户原问的合法编码只剩「与 fulfilled 三态正交的一层」；A/B 以及「把 α 塞进 NE」在现行协议下已经死了。E 的五值+披露质量不是最小实现。

**Proposed Change**: 把 015 收成否定表 + 一族活编码。不要在本 issue 选出最终字段表。

**Design**:
    死编码（写进 Consensus，可当后续 veto）
      A  fulfilled 第四态 / partial
      B  「当前能力下尽力了」算 F
      C  用 NE 表达 α（β 走输入坏 NE 仍合法）
      D  用 is_supported / 接口有无 / 操作符表当标签本身

    活家族（只到这一层）
      需求轴三态值域不动，overall 仍只聚合 blocking 的 Q1。
      另有一层对外可读的产品承认，不回写 status。
      该层至少能标出「定位内、当前可明确尚未支持」，且 β/γ 不能吃到这个取值。
      来源：Authority §8.2 问题模板，或空间有无；不是字段表自报。
      实现时复用 authority_gate 已在解析的三类前缀，不要平行再造一套职责分类。
      β 继续走已有空间/输入闸，不要假装 Authority 三类能产出「未形成产品对象」。

    本轮明确不锁
      五值划分、披露质量三值、挂 assessment 还是升级 Authority statement 类型、
      写进 fulfilled 附录还是新短文、现在是否改 schema。

    fulfilled.md 若日后改（用户选 §4.2 之后）
      只加「这不是什么」+ 指向轴 2。
      不改 §2.1–§2.3 值域，不把轴 2 写进 §2。

**Implementation Steps**:
1. Consensus 采纳上面的死编码表和活家族，不采纳 E 表当「最小语义」。
2. 用户拍板 §4.1 / §4.2 / §4.5 之前，任何实现 PR 都应视为越权。
3. 若用户日后选「现在改 schema」，必须同时写明解除 `investigate-judge.md` L687，并改归因：轴 2=定位内尚未支持 且披露正确时，不得再按普通 NF 追「漏条件」根因。那是下一轮，不是本轮。

**Risks**:
- 把 E 五值当最小，会复制 NE 成因，消费者仍会把两轴揉成一个词。
- 把披露质量绑进来，会在还没回答「尚未支持」之前先加第三轴。
- 假装 012 一道程序能产出 β，会把非法输入重新送进 Authority，和 §8.1 冲突。

**Verification**:
    python3 -c "from pathlib import Path; ful=Path('spec/alg/fulfilled.md').read_text(); vol=Path('spec/info-volume.md').read_text(); inv=Path('spec/alg/investigate-judge.md').read_text(); sch=Path('impl/core/schema/judge.py').read_text(); j=Path('impl/core/judge.py').read_text(); assert '不新增第四态' in ful; assert '不引入 partial' in vol; assert '本轮不修改现有' in inv and 'FulfillmentAssessment' in inv; assert 'boundary_decision' in sch and '不进通用 schema' in sch; assert 'partially_fulfilled' in j and '禁用' in j; print('015 vetoes still in source')"

人工否决测试（原则，不跑 judge）：任一提案若出现「第四态」「尽力了算 F」「α 改标 NE」「is_supported=标签」，判为未修 015。

**Why I Cannot Apply It**: 红线禁止改 spec/schema；字段名和落点是用户项。architect 只能锁死路。
---
## Architect Response #2

### Investigation

Read in full: this issue; issue-013 / 014 (including their Architect Response #1); charter §3 / §4.1 / §4.2 / §4.5.
Quoted / inspected myself:
- `fulfilled.md` L4–L5, L16, L40–L69, L80–L91, L160, L184, L194, L207, L209, L226–L227
- `info-volume.md` L270–L278, L282–L284, L303–L305
- `authority.md` L295–L298, L467–L468, L476, L489–L507
- `investigate-judge.md` L687
- `impl/core/schema/judge.py` L55–L60 (`boundary_decision` comment)
- `impl/core/judge.py` L135, L404 (`partially_fulfilled` 禁用)
Re-ran 015 protocol asserts: all True. Also confirmed `info-volume.md` L277–L278:「不需要再引入第二个对错维度」.

### Spawn Evidence
- spawn-id: 6286c10358770df9
- pid: 39666

**Judgment**: escalate-to-project

**Evidence Verification**:
Verifier’s *vetoes* match the oracle. Verifier’s *positive encoding* (scheme E’s five-value table + disclosure-quality third axis + hang it on `FulfillmentAssessment` now) does not.

Dead encodings — I independently confirm, these are not product taste:
- **A** fourth fulfilled state / partial: `fulfilled.md` L4–L5「不新增第四态」; `info-volume.md` L271「不引入 partial」; `judge.py` L404 禁用 `partially_fulfilled`. A fourth status would also smash two questions back into one word and tear `info-volume.md` L282–L284 attribution (which only knows F vs NF/NE).
- **B** 「当前能力下尽力了」= F: `fulfilled.md` L160, L184, L207 / D3. Draft already paid to delete this. Reopening it is not an option.
- **C** park α in NE: `authority.md` L499–L503 and `fulfilled.md` L45, L82–L84, L134 explicitly send 职责内能力缺失 + 未达成 → NF, and forbid auto-NE. NE is also temporary (`fulfilled.md` L69). α as NE would declare a long-term product gap “unclear”. β-as-输入坏-NE remains legal (`fulfilled.md` L59; `authority.md` L467).
- **D** IT self-report (`is_supported`, operator table, interface presence) *as the tag*: user forbade an IT audit; `fulfilled.md` L194 §7.11 and positioning invariant 1 forbid it as a rule. `fulfilled.md` L226–L227 task 5 already assigned `is_supported` a *different* job — feed the existing 3-state (“in catalog” vs “actually supported”), not become a public product-support label.

Live family — also technical, not a name:
- If the user wants Q2 visible, the only remaining legal family is **orthogonal to the 3-state, not written back into `status`, not aggregated into overall**.
- `info-volume.md` L277–L278 deleted a second correctness dimension because fulfilled already *is* the right/wrong axis. Axis 2 must be a product-acknowledgment disposition, **not** a second verdict.

Where verifier overreaches — this is why the verdict is escalate, not real-problem:
1. Scheme E’s five rows +「处置是否正确」is not minimum. Disclosure quality is a third axis. β/γ already have demand-axis homes; they do not have to be first-class axis-2 values (see 014).
2. 「入口已经在 Authority statement 类型，轴 2 应吃 012 同一道程序」is half right. `authority_gate.py` prefixes produce α/γ, not β. `authority.md` L467: 输入坏 does not go through Authority. One program cannot emit both.
3. `JudgeResult` L59 `boundary_decision` is **not** a reserved seat. `info-volume.md` L305 lists it among project-specific intermediates to *cut* from the generic schema.
4. `investigate-judge.md` L687「本轮不修改现有 FulfillmentAssessment / JudgeResult / 三态词表和 overall 聚合 schema」is a real freeze. Orthogonal field *is* a schema change. This debate charter §3 / §4.5 forbids making that change, and forbids roles from deciding to make it.
5. Charter §4.1 / §4.2 / §4.5 are explicit user items: whether to expose both questions; whether the definition lives in a `fulfilled.md` appendix, a short spec, or an authority consumption chapter; whether to change schema *now*. 015’s recommended E picks all three.

**Reasoning**:
015 should lock *dead roads* and name the *living family*. It must not lock a field table, a hang-point, or “change schema now.”

Direct answer to the user’s original fork:
- Change `fulfilled.md` §2 so「尽力了」becomes F, or becomes a fourth status → **dead**.
- `fulfilled.md` *may later* grow a「这不是什么」pointer (3-state still only answers 办成了没有; no F-because-refused; no fourth state; product acknowledgment lives on axis 2). Axis 2’s definition must not be written into §2, or the next reader will again use one word for two questions.
- Whether that pointer + orthogonal layer is built, what it is called, where the spec lives, and whether schema moves in this generation → **user**, charter §4.

I am not saying the ontology gap in 013 is imaginary. I am saying 015, as filed, is the *placement and shipping* issue, and those knobs are out of role scope. Calling 015 `real-problem` would smuggle “add field E on `FulfillmentAssessment`” past §4.5.

**What must be decided (by project owner / user)**:
1. §4.1 要不要对外同时看见 Q1 和「产品位内当前是否正确承认尚未支持」。
2. §4.2 若要：定义写在 `fulfilled.md` 附录、独立短文，还是 authority 消费章。
3. §4.5 现在是否改 schema。若选「现在改」，必须同时显式解除 `investigate-judge.md` L687，并改归因：轴 2=定位内尚未支持 且披露正确时，不得再按普通 NF 追「漏条件」。
4. 展示用中文名（§4.3）若只是展示名，不改三态。

Vetoes the user is **not** free to reopen without amending the oracle:
- A fourth fulfilled state / partial
- 「尽力了」= F
- α expressed as NE
- `is_supported` / interface / operator table *as the tag itself*

Until those four decisions are made, any implementation PR is out of scope for this charter. Architect cannot apply a field, a spec edit, or a Chinese name.

**Why I Cannot Apply It**: 红线禁止改 `spec/**` / `impl/**`。015 剩下的活选项就是章程 §4.1 / §4.2 / §4.5。这不是再辩一轮协议就能闭合的。

---
## Consensus
**Verdict**: escalate-to-project
**Official peer**: Architect Response #2 · spawn-id `6286c10358770df9`

015 是给项目负责人的决策题，不是再辩一轮协议就能闭合的实现题。不改成 real-problem，以免把「现在就加字段 E」走私进章程 §4.5。

**已死（不改 oracle 就不能重开）：**

- A. fulfilled 第四态 / partial
- B. 「尽力了」= F
- C. 用 NE 表达 α（β 走输入坏 NE 仍合法）
- D. 用 `is_supported` / 接口有无 / 操作符表当标签本身

**活着的家族：** 若用户要 Q2，只能是与三态正交、不回写 `status`、不进 overall 的一层。它是产品承认处置，不是第二套对错。`fulfilled.md` 以后最多加「这不是什么」的指针；轴 2 的定义不得写进 §2 三态。

**verifier 越权，本共识否掉：**

- 方案 E 五值 + 披露质量 = 第三轴，不是最小。β/γ 已有需求轴归宿，不必先做成轴 2 正式值。
- Authority 三类前缀产得出 α/γ，产不出 β（输入坏不走 Authority）。
- `JudgeResult.boundary_decision` 不是预留钩子；info-volume 把它列进该砍的项目中间产物。
- `investigate-judge.md` 冻结是真的；加正交字段就是改 schema。本轮红线禁止角色代选。

交给用户的只剩章程 §4.1 / §4.2 / §4.5（外加若只要展示名则 §4.3）。在这四件事拍板前，任何实现 PR 都出本轮章程范围。
