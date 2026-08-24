# Issue #014: 「去年」和「格式外/称谓」共享「不能换 F」，但不共享「尚未支持」

**Class**: boundary
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Protocol / 产品定位切片
**Cases**: 只作形态举例。不重开 007 / 009，不代选「去年算不算核心」。

## Verifier Discovery

用户感觉 2 和 3 像同一类，自己也说还没拆清楚。本 issue 只拆抽象，不判那几条该 F 还是 NF。

### 二者真正共享的

两边都是：

1. 用户来要的整件事，没有按完整业务需求交付（年筛选没有；非法单号/称谓没有变成可执行条件）。
2. 按当前已 Load 的产品空间，系统没有（也不该）编造一个越界条件。
3. 因此 **不能** 用「我尽力了 / 我如实说了」把整体标成 fulfilled。`fulfilled.md` §5、§7.1、§7.8、D3 对两边同样成立。

共享的是「需求轴上的禁令」，不是「产品轴上的同一格」。

### 二者不共享的：产品定位切片

用 `fulfilled.md` §3 第二步 + `authority.md` §8.3 + `material-positioning.md` 的空间/选择分离，切三格：

| 格 | 问的是什么 | 形态举例 | Authority / 空间上像什么 | 若合成一个「尽力了」标签会怎样 |
|---|---|---|---|---|
| α 定位内尚未支持 | 产品声称做这类检索，这一维当前明确做不了 | 「林秀微 + 全家保 + 去年」里的投保年 | `职责内能力缺失`（应具备但未实现）。空间里没有「投保年」维，但主对象（姓名/险种）在空间内 | 应进产品缺口 / 长期优化点。标签语义是「尚未支持」 |
| β 未形成产品对象 | 用户给的东西落不到产品可执行对象上 | 格式外编号 `P07000000`；称谓「老板娘」当姓名 | 不是「应支持这个非法值却没支持」。positioning 不变量 3 / §8.3：空间外输出是发现信号，不是空间的一部分。输入坏是 NE 的合法格（§2.3 / §3.1） | 若标「尚未支持」，下一步就会变成「去支持 P07000000」——这是错的产品方向 |
| γ 定位外 | 根本不是这个产品的事 | 客户搜索里问天气、查车牌 | `职责外` → NE（职责外） | 已经有格子；再标「尚未支持」会把职责外做进路线图 |

用户自己要的那句话是：

> 产品功能定位以内，但是系统可以明确清楚当前能力尚未支持的点

这句话**只覆盖 α**。β 不是「尚未支持」，是「不是产品对象」。γ 不是「定位以内」。

所以 2 默认落 α（投保年在客户搜索产品位内、当前不支持——这是产品常识级定位，不是本轮给 I046 改判）。3 默认落 β（格式外编号尤其干净；称谓是否将来要支持，章程 §4.4 留给用户，不得在本轮把称谓并进 α）。

### 若先合成一个标签，会重新制造两类错

1. **α 被当成系统 bug**：只有需求三态时，正确披露「投保年暂不支持」和漏掉姓名条件都叫 NF，产品侧无法单独看见「能力缺口且处置对」。
2. **β 被当成能力缺口**：一个「尽力了 / 可支持」标签若同时收编格式外，路线图会被喂进「支持残号」「把老板娘当姓名」。009 Consensus 已经排除「拒绝=F」和「强要空间外交付」。

007 要两边同侧的是 α 内部的 blocking（去年是核心还是附加），不是 α 和 β 合并。009 要排除的是 β 的两端（F 和 NF），不是把 β 改名为尚未支持。

### 和 013 的边界

013 钉「单轴不够」。014 钉「轴 2 至少要能分开 α 和 β」。没有 014，轴 2 会变成用户担心的那种 IT/大筐标签。

### 不是什么

- 不是裁定去年算不算核心（章程 §4.3）。α 里无论去年是 blocking 还是 non-blocking，它仍然是「定位内尚未支持」，不是 β。
- 不是裁定称谓将来要不要做成角色检索（章程 §4.4）。本 issue 只要求：在拍板前，不得把称谓和格式外、投保年写成同一枚举值。
- 不是说 2 和 3 「完全无关」。它们共享需求轴禁令，只是产品轴不同格。

### 可证伪修复（原则）

轴 2 的最小可区分集合必须能分开：

- 定位内、可明确尚未支持（α）
- 未形成产品对象 / 空间外非法输入（β）
- 定位外（γ，已有职责外）

不允许用一个「尽力了」或一个「可支持能力」值同时覆盖 α 和 β。

### 未消元

- 称谓最终进 α 还是 β，用户定。
- 轴 2 的字段怎么挂，见 015。

---
## Architect Response #1

### Investigation

Read in full: this issue; issue-013; issue-009 Consensus; issue-007 Consensus (blocking only, not re-opened).
Quoted:
- `fulfilled.md` L40–L45, L52–L59, L80–L90 (step 2), L128–L138, L160, L184–L191, L207 (D3)
- `authority.md` L295–L298, L461–L467, L489–L507
- `material-positioning.md` L90–L94 (不变量 3：空间外输出是发现信号)
- charter §4.3 / §4.4
Cases used only as shape examples. Did not assign I046 / I034 a new F/NF.

### Spawn Evidence
- spawn-id: e288ae27bc0d2d22
- pid: 32717

**Judgment**: real-problem

**Evidence Verification**:
The shared ban is real. The shared cell is not. The write-up then overreaches by default-parking 「去年」in α.

1. Shared demand-axis ban — confirmed, same text for both shapes.
   `fulfilled.md` L160「如实拒绝、态度好 ≠ 办成」；L184 §7.1「如实拒绝 → 整体算办成了 ✗」；L191 §7.8「用我如实说了判办成了 ✗」；L207 D3 删的就是「能力边界外 + 如实拒绝 → 核心目标算办成」。009 Consensus 已经排除「拒绝=F」。这条禁令对投保年和格式外同样成立。
2. They are not the same product-axis cell — also confirmed, and the split is already latent in the protocol, not invented this round:
   - α 问的是 `authority.md` L499–L503 `职责内能力缺失`：产品声称做这类事，这一维应具备但未实现。需求轴走 NF + 长期优化点，禁止降 NE。
   - β 问的是 `fulfilled.md` L59 / L90「输入坏」+ positioning 不变量 3（L93）：用户给的东西落不到可执行对象。`authority.md` L467：输入坏不依赖 Authority。009：空条件不得 NF，也不得 F。
   - γ 问的是 `authority.md` L495–L497 `职责外` → NE。车牌 / 天气已经在 `fulfilled.md` L56–L57。
3. User’s own sentence only covers α. 「产品功能定位以内，但是系统可以明确清楚当前能力尚未支持的点」不是 β（不是产品对象），也不是 γ（不是定位以内）。用一个「尽力了 / 可支持」值同时收编 2 和 3，会把路线图喂成「去支持 P07000000 / 把老板娘当姓名」。这是真的产品方向错误，不是用词偏好。
4. Pushback — 「2 默认落 α」不是协议事实，本轮不得写成已定。
   - 章程 §4.3 只冻结「去年是核心还是附加」，连这个都不许角色代选。
   - 「投保年在客户搜索产品位内」需要 normative / 业务方确认，不能靠常识，更不能靠 catalog 里有字段且 `is_supported=false`。那正是 `current_behavior` / D6，`fulfilled.md` L194 和 positioning 不变量 1 都禁止用它自证职责内。
   - `fulfilled.md` D5（L209）还写过：字段在清单但不支持，先查「该不该支持」；查不了是说不清，不是自动 α。
   - 因此 014 能钉的是形态，不是 I046 这维已经是 α。把「去年」先写成 α，再顺便写成附加维，会把 007 一起偷运进来。禁止。
5. 称谓：同意 §4.4，拍板前不得和格式外、投保年写成同一枚举值。格式外编号是干净的 β 例；称谓不是。

**Reasoning**:
013 说单轴不够。014 的真正载荷是：**用户的归类太粗**。2 和 3 共享「不能用尽力了换 F」，不共享「尚未支持」。

但 verifier 把「轴 2 最小可区分集合必须能分开 α / β / γ」写成好像必须先做一个三值（或五值）产品轴枚举。这不是唯一编码。

用户要的标签只有一格：定位内尚未支持。为了不被滥用，硬约束是 **β、γ 不得吃到这个标签**。β 和 γ 在需求轴上已经分别住在「输入坏 NE」和「职责外 NE」。它们不必为了不被误标，就先在轴 2 拥有自己的一等枚举值。要不要做成完整划分，是 015 的编码问题，不是 014 的存在性证明。

007 要两边同侧的是 α *内部* 的 blocking，不是 α 和 β 合并。009 要排除的是 β 的两端（F 和 NF），不是把 β 改名为尚未支持。这两条我同意，且不重开。

## Improvement Proposal

**Problem**: 若把「去年」和「格式外/称谓」收进同一个「尽力了 / 尚未支持」取值，产品轴会把非法对象当成能力缺口，路线图会走错。

**Proposed Change**: 钉否定约束，不预填哪条 case 进哪格，也不强制轴 2 先做成 α/β/γ 三值枚举。

**Design**:
    共享（只这一条）
      需求轴禁止「尽力了 / 如实拒绝 → F」。对 α 形态和 β 形态同样适用。

    不共享
      「定位内尚未支持」只覆盖 α 形态。
      β 形态（未形成产品对象 / 空间外非法输入）不得使用该标签。
      γ 形态（职责外）不得使用该标签；它已经有职责外 NE。

    本轮禁止代填
      不得写「去年默认 α」。去年是否定位内 = 产品事实，须 Authority + 独立资料，不是常识。
      不得把去年写成附加维（007 / 章程 §4.3）。
      称谓保持未分派（章程 §4.4）。
      格式外编号可继续当 β 的形态例，这是 009 已共识的「不是本可支持」，不是本轮新判 I034。

    最小可证伪修复
      任意「产品位内尚未支持」标签 / 字段 / 取值，用格式外编号去套必须失败。
      用职责外（天气 / 车牌）去套必须失败。
      不要求本轮先公布 β、γ 的轴 2 枚举名。

**Implementation Steps**:
1. Consensus 收：共享的是需求轴禁令，不是产品轴同一格。
2. Consensus 删：verifier 原文「2 默认落 α」。改成「去年 *若* 被业务方确认为定位内检索维，则形态是 α；本轮不确认这一前提」。
3. 轴 2 要不要给 β/γ 单独取值：交给 015，不要在 014 锁死完整划分。

**Risks**:
- 默认 α 会把 catalog `is_supported=false` 洗成产品定位，直接违反 §7.11 / positioning 不变量 1。
- 强制三值枚举会把 015 的「正交出口」膨胀成第二套三态，和需求轴 NE 成因重复。

**Verification**:
    python3 -c "from pathlib import Path; ful=Path('spec/alg/fulfilled.md').read_text(); auth=Path('spec/alg/authority.md').read_text(); pos=Path('spec/alg/material-positioning.md').read_text(); assert '如实拒绝、态度好 ≠ 办成' in ful; assert '输入坏' in ful; assert '职责内能力缺失' in auth and '职责外' in auth; assert '发现信号' in pos; print('014 protocol split still in source')"

再人工核对：若有人提出单一取值同时覆盖「投保年暂不支持」和「P07000000」，该提案不满足本 issue。

**Why I Cannot Apply It**: 本轮不改 spec；去年进不进功能地图、称谓算 α 还是 β，章程留给用户。
---
## Architect Response #2

### Investigation

Read in full: this issue; issue-013 verifier + Architect Response #1; issue-009 Consensus (not re-opened); charter §4.3 / §4.4.
Quoted / inspected myself:
- `fulfilled.md` L40–L45, L52–L59, L80–L91, L128–L138, L160, L184–L191, L194, L207, L209
- `authority.md` L295–L298, L461–L468, L489–L507
- `material-positioning.md` L90–L94 (不变量 3：空间外输出是发现信号)
- issue-009 Consensus: 格式外不得 NF 也不得 F；排除「拒绝=F」与「强要空间外交付」
Re-ran 014 protocol asserts: all True.

### Spawn Evidence
- spawn-id: 6286c10358770df9
- pid: 39666

**Judgment**: real-problem

**Evidence Verification**:
The shared half is already in the oracle and does not need a new word:
- `fulfilled.md` L160 / L184 / L207: 如实拒绝、态度好 ≠ 办成. This binds **both** morphologies. I agree with verifier here.
- `authority.md` L499–L503: 职责内能力缺失 + 期望未达成 → NF, never auto-NE.
- `fulfilled.md` L59 / L91: 输入坏 is a legal NE cell. `authority.md` L467–L468: 输入坏 / 完全无关 **do not** go through Authority.

The unshared half is also in the oracle, and verifier over-assigns it.

1. User’s own sentence only covers α:「产品功能定位以内，但是系统可以明确清楚当前能力尚未支持的点」. β is not a product object. γ is not 定位以内. A single「尽力了 / 尚未支持」value that also eats 格式外 would send the roadmap to「去支持 P07000000」. That is a real product-direction error. 009 Consensus already forbade both「拒绝=F」and「强要空间外交付」.
2. 「2 默认落 α」is **not** a protocol fact. Charter §4.3 only freezes「去年是核心还是附加」— even that is not ours. 「投保年在客户搜索产品位内」needs normative / 业务方 confirmation. Catalog `is_supported=false` is exactly `current_behavior` / D6; `fulfilled.md` L194 and positioning invariant 1 forbid using it to self-prove 职责内. D5 (`fulfilled.md` L209) is stronger: field-in-list-but-unsupported must first ask 该不该支持; if that cannot be answered, it is 说不清, **not** automatic α. Response #1 already rejected default-α; I add D5 as the direct veto.
3. Verifier’s title lumps「格式外/称谓」as one β. 格式外编号 is a clean β *shape* (009: not「本可支持」). 称谓 is **not** the same shape. Charter §4.4 parks whether 称谓 later becomes role search (α) or stays un-executable input (β). Until that call, 称谓 must not share an enum value with 格式外 **or** 投保年.

**Reasoning**:
013 said one axis cannot answer both questions. 014’s actual load is: **the user’s grouping is too coarse**. Cases 2 and 3 share a demand-axis *prohibition*, not a product-axis *cell*.

I reject verifier’s repair as written —「轴 2 最小可区分集合必须能分开 α / β / γ」sounds like “first ship a three-value product enum.” That is not the only encoding, and it is not the minimum.

What must be true:
- Any future token meaning「定位内尚未支持」may be applied only to the α *morphology*.
- β and γ **must fail** that token.
- β and γ do **not** need first-class axis-2 values just to avoid being mis-tagged. They already live on the demand axis: 输入坏 NE (`fulfilled.md` L59, L91) and 职责外 NE (`authority.md` L495–L497; `fulfilled.md` L56–L57). Whether to promote them into a full partition is 015, not 014.

007’s remaining question is blocking *inside* α, not merging α with β. 009 excludes both ends of β (F and NF), not renaming β to 尚未支持. I do not re-open either.

This issue is a **negative constraint** on any later tag. It is not a license to pre-fill I046 / I034 / 称谓 into a function map. Charter already told us not to ask the user to fill that map this round.

## Improvement Proposal

**Problem**: If「去年」and「格式外/称谓」are stored as the same「尽力了 / 尚未支持」value, the product axis treats illegal objects as capability gaps and the roadmap goes the wrong way.

**Proposed Change**: Lock the negative constraint. Do not pre-assign cases. Do not require axis 2 to be an α/β/γ enum.

**Design**:
    共享（只这一条）
      需求轴禁止「尽力了 / 如实拒绝 → F」。α 形态和 β 形态同样适用。

    不共享
      「定位内尚未支持」只覆盖 α 形态。
      β 形态（未形成产品对象 / 空间外非法输入）不得使用该标签。
      γ 形态（职责外）不得使用该标签；它已经有职责外 NE。

    本轮禁止代填
      不得写「去年默认 α」。去年是否定位内 = 产品事实，须 Authority + 独立资料，不是常识，也不是 catalog `is_supported=false`（D5 / §7.11 / positioning 不变量 1）。
      不得把去年写成附加维（007 / 章程 §4.3）。
      称谓保持未分派（章程 §4.4），且不得与格式外、投保年写成同一枚举值。
      格式外编号可继续当 β 的形态例——这是 009 已共识的「不是本可支持」，不是本轮新判 I034。

    最小可证伪修复
      任意「产品位内尚未支持」标签 / 字段 / 取值，用格式外编号去套必须失败。
      用职责外（天气 / 车牌，`fulfilled.md` L56–L57）去套必须失败。
      不要求本轮公布 β、γ 的轴 2 枚举名。

**Implementation Steps**:
1. Consensus 收：共享的是需求轴禁令，不是产品轴同一格。
2. Consensus 删 verifier 原文「2 默认落 α」。改成「去年 *若* 被业务方确认为定位内检索维，则形态是 α；本轮不确认这一前提」。
3. 称谓从「格式外/称谓 = β」里拆开，保持未分派。
4. 轴 2 要不要给 β/γ 单独取值：交给 015，不要在 014 锁死完整划分。

**Risks**:
- Default-α launders catalog `is_supported=false` into product position.
- Forcing a three-value enum duplicates NE causes and steals 015.

**Verification**:
    python3 -c "from pathlib import Path; ful=Path('spec/alg/fulfilled.md').read_text(); auth=Path('spec/alg/authority.md').read_text(); pos=Path('spec/alg/material-positioning.md').read_text(); assert '如实拒绝、态度好 ≠ 办成' in ful; assert '该不该支持' in ful; assert '输入坏' in ful; assert '职责内能力缺失' in auth and '职责外' in auth; assert '发现信号' in pos; print('014 protocol split still in source')"

人工：任一提案若用同一取值同时覆盖「投保年暂不支持」和「P07000000」，未修 014。

**Why I Cannot Apply It**: 本轮不改 spec。去年进不进功能地图、称谓算 α 还是 β，章程留给用户。

---
## Consensus
**Verdict**: real-problem
**Official peer**: Architect Response #2 · spawn-id `6286c10358770df9`

2 和 3 **不是一类**。共享的只有需求轴禁令：「尽力了 / 如实拒绝 ≠ F」。不共享「尚未支持」这一格。

接受 architect 的收紧，并删掉 verifier 原文里越权的部分：

1. 用户原句「产品功能定位以内，系统可以明确当前尚未支持」**只覆盖 α 形态**。β（未形成产品对象 / 空间外非法输入）不是尚未支持；γ（职责外）不是定位以内，且已有 NE。
2. **否掉「2 默认落 α」**。去年是否定位内是产品事实，要 Authority + 独立资料，不能靠常识，更不能靠 catalog `is_supported=false`（fulfilled D5 / §7.11 / positioning 不变量 1）。本轮不确认这一前提。
3. **称谓保持未分派**。格式外编号可以继续当 β 的形态例（009 已共识「不是本可支持」）。拍板前，称谓不得和格式外、投保年写成同一枚举值。
4. 轴 2 **不必**先做成 α/β/γ 三值枚举。最小约束是：任何「定位内尚未支持」标签，套到格式外或职责外必须失败。β/γ 要不要晋升成轴 2 正式取值，交给 015。

007 要两边同侧的是 α 内部的 blocking，不是 α 和 β 合并。009 排除的是 β 的两端（F 和 NF），不是把 β 改名为尚未支持。二者本轮都不重开。
