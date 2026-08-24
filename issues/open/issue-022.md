# Issue #022: 第二问必须和 fulfilled 同一层级：一件业务事实，不是评测员打分

**Class**: boundary
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Protocol / 抽象层级
**Cases**: 不作本轮判定对象。

## Verifier Discovery

用户说上一轮那句太窄：「在这个产品该做的范围内，系统有没有正确承认：这一点我们现在还不支持？」不像 `fulfilled.md` 那种层级。「尽力了」可以看，但不确信最好。「放对地方 / 处置站不站得住」不合适，不懂位置是什么。

本 issue 只钉层级。候选问法的死活在 024。和 fulfilled 怎么切开在 023。

### fulfilled.md 的层级是什么（不是文风）

`spec/alg/fulfilled.md` §1 原文：

> 我们：评测系统（Judge），只看一件事——系统有没有帮用户办成想办的事。
>
> 判断分两层：第一层：用户要的事办成了没有？第二层：手里的材料够不够回答第一层？

同文件开篇：词表沿用 `spec/info-volume.md`，不新增第四态。§2.2：没办成「不区分原因」。期望从用户视角写，不是「输出正确的查询结构」。

`spec/info-volume.md`：judge 只产出 fulfillment，不产第二套对错；不引入 partial。

所以「fulfilled 那种层级」是五条结构，不是把句子写得口语一点：

1. 从业务事实提问，不是从实现 / 接口 / 字段表提问
2. 只看一件事
3. 封闭小词表
4. 压缩原因，不把根因当状态
5. 「材料够不够」是能不能回答的前提，不是另一个分数

`spec/alg/authority.md` §1 把另一件事已经拆走：Authority 只解决「标准是否确定」，不判断实际输出是否满足用户要求。那是输入，不是对外出口。

### 上一轮那句为什么不够级

「系统有没有正确承认：这一点我们现在还不支持」问的是评测员对一次披露的打分。它预设了三件事已经成立：产品位内、当前不支持、承认是对的。这是一个检查项，不是和「办成了没有」并列的业务事实。换一批产品、换一种「今天办不了」，这句话就要重写。这就是用户说的「不够泛化」。

「尽力了」同样不够级。它评的是态度和努力，不是产品事实。`fulfilled.md` §5 / §7.1 / D3 已经禁止用态度换交付结论。它可以当某一格上的观感，不能当第二问本身。

「放对地方」「处置站不站得住」也不够级，而且词是空的。协议里没有「位置」这个对象。用户已经明说不懂位置是啥意思。`info-volume.md` 删掉第二套对错，正是因为 fulfilled 已经是对错轴；「站不站得住」会把它偷回来。

### 同级第二问必须长什么样

若还要第二问，它必须能填进和 §1 一样的槽：

```text
并列的两件业务事实（不是「第一层 / 第二层」——第二层已被「材料够不够」占用）：
  交付：用户要的事办成了没有？
  ？？：________________________？
```

空格里必须是产品事实，能对任何产品问，不依赖「承认」「位置」「尽力」。材料不够时，第二问也可以说不清，但不能把「说不清」当成它的主业。

### 不是什么

- 不是推翻 013：单轴出口仍然不够。本 issue 说的是「缺的那一层该是什么层级」，不是「其实一层就够」。
- 不是给 fulfilled 加第四态，也不是改 §2.2「不区分原因」。
- 不是现在起中文名。

### 可证伪修复（原则）

任一候选问法，若不能单独成立为「一件业务事实 + 封闭词表」，或必须靠「承认 / 尽力 / 位置 / 处置」才能听懂，则未达 fulfilled.md 层级。

### 未消元

具体哪一句活下来，见 024。

---
## Architect Response #1

### Investigation

Read in full, independently of the verifier paraphrase:

- this issue; `issues/trace/sibling-question-discovery.md`; charter `issues/charter-sibling-question.md` §1–§5
- `spec/alg/fulfilled.md` §1, §2.1–§2.3, §3, §4.1, §5, §7.1/§7.5/§7.8, D3
- `spec/info-volume.md` L270–L278（三态、不引入 partial、删掉第二套对错）
- `spec/alg/authority.md` §1（只解决标准是否确定，不判断实际输出是否满足用户要求）
- `spec/alg/material-positioning.md` §1–§3、不变量 1（「定位」的对象是资料相对 Live，不是用户请求的摆放）
- 013 / 014 / 015 Consensus blocks only

Did not re-judge cases. Did not read 006–021 beyond the three Consensus locks.

### Spawn Evidence

- spawn-id: ad014f66ee11ca7f
- pid: 79816

**Judgment**: real-problem

**Evidence Verification**:

协议里「fulfilled 那种层级」是对象 + 压缩方式，不是口语腔。原文不是 verifier 的五条口号。

`fulfilled.md` §1：

> 我们：评测系统（Judge），只看一件事——系统有没有帮用户办成想办的事。
>
> 判断分两层：第一层：用户要的事办成了没有？第二层：手里的材料够不够回答第一层？

同文件开篇：词表沿用 `info-volume.md`，不新增第四态。§2.2：没办成「不区分原因」，并把「功能本身未实现，但用户期望已提出」收进没办成。§5 / §7.1 / §7.5 / §7.8 / D3：如实拒绝、态度好、系统表现不错，都不能换交付结论。

`info-volume.md` L271 / L277–L278：不引入 partial；judge 只产 fulfillment；`verdict`（correct/incorrect）被删，因为 fulfilled 已经是对错轴。

`authority.md` §1：

> Authority Agent 只解决“标准是否确定”，不判断某个实际输出是否满足用户要求。

`material-positioning.md` §1 的两个问题是「资料站在哪里 / 资料能证明什么」。§2 唯一判定轴是资料陈述是否独立于被测系统。不变量 1：`current_behavior` 只能解释现状，不能冒充正式规则。这里的「定位」没有用户请求的「位置」这个对象。

013 Consensus 已锁：单轴出口答不了第二件事；Authority 三类 statement 是挑 F/NF/NE 的隐藏中间量，挑完就吃掉。015 Consensus 已锁：若有 Q2，只能与三态正交；方案 E + 披露质量是第三轴；「尽力了」= F 死。

**Reasoning**:

层级约束是真的。把三句候选一齐叫「评测员打分」是修辞，不是协议切法。

1. 「正确承认尚未支持」不够级，但不够级的原因不是「凡评测员开口都是打分」。Judge 自己就是评测员；Q1 也是评测员在判一件业务事实。这句话死在**判定对象**：它预设产品位内、当前不支持、承认对不对这三件已经成立，再给一次披露打分。013 把它写成 Q2 时，已经把 α 格和「正确承认」绑在一起；015 已否披露质量第三轴。换产品、换一种「今天办不了」，检查项就要重写——这是用户说的不够泛化，成立。

2. 「尽力了」也不是打分项。它是民间压缩词：把右上能力缺口、职责外、事没成形、再加上态度，收成一个观感。014 已写过它会喂错路线图；fulfilled §5 禁止用态度换交付。用户说可以看，只能当某一格上的旁白，不能当第二问本身。

3. 「放对地方 / 处置站不站得住」更不是打分项。词是空的。协议里的「定位」是资料相对 Live 的独立性，不是把用户的事摆进某个站。用户已经明说不懂位置。硬用「站得住」会把 `info-volume.md` 删掉的第二套对错偷回来。

同级第二问必须能填的槽，不是「第一层 / 第二层」——第二层已被「材料够不够」占用。015 写得比本 issue 的「并列两件业务事实」更准：若还有第二问，它是与三态正交的一层，不回写 `status`，不进 `overall`。对象必须是产品事实，不能靠「承认 / 尽力 / 位置 / 处置」才能听懂。

本 issue 不推翻 013，不加第四态，不改 §2.2，不起中文名。这些边界我接受。

可证伪原则保留，但改口：任一候选若不能单独成立为「一件产品事实 + 封闭词表」，或必须靠承认 / 尽力 / 位置 / 处置才能听懂，则未达 fulfilled.md 层级。不要再把这条写成「不是评测员打分」。

## Improvement Proposal

**Problem**: 上一轮对外问句停在检查项 / 民间压缩 / 空隐喻，没有和 `fulfilled.md` §1 同级的判定对象。

**Proposed Change**: 只在本 issue 写入层级锁。不改 `spec/**`，不命名对外句子（句子归 024 / 用户）。

**Design**:

```text
第二问若存在，判定对象必须是产品事实，不是一次披露/态度/摆放的评分。
槽位：
  Q1  用户要的事办成了没有？（fulfilled.md §1 第一层，三态冻结）
  材料 手里的材料够不够回答 Q1？（§1 第二层，已被占用）
  Q2  ________________？  （若有：与三态正交，不回写 status，不进 overall）
禁：承认 / 尽力 / 位置 / 处置 作为听懂 Q2 的必要词。
禁：把 Q2 写成 fulfilled 的「第二层」。
禁：把「评测员打分 vs 业务事实」写进协议词表——Judge 永远是评测员，差的是对象。
```

**Implementation Steps**:

1. Consensus 采纳上面的对象锁，不采纳「评测员打分」作为正式切名。
2. 013 的出口裂缝仍在；本 issue 只钉层级，不重开单轴够不够。
3. 对外句子、要不要第二问、改不改 schema，全部留给 024 + 章程 §4。任何把本锁写成字段名的 PR 都越权。

**Risks**: 有人把「产品事实」理解成再问一遍「办成了没有」。那是 023 的切面，不在本 issue 展开，但本锁必须给 023 留出「不得偷走 Q1」的口子。

**Verification**:

```bash
python3 -c "
from pathlib import Path
ful = Path('spec/alg/fulfilled.md').read_text()
vol = Path('spec/info-volume.md').read_text()
auth = Path('spec/alg/authority.md').read_text()
pos = Path('spec/alg/material-positioning.md').read_text()
assert '只看一件事' in ful and '办成了没有' in ful and '材料够不够回答第一层' in ful
assert '不区分原因' in ful and '不新增第四态' in ful
assert '用\"系统态度好\"替代\"用户结果达成\"' in ful
assert '不引入 partial' in vol and '不需要再引入第二个对错维度' in vol
assert '只解决“标准是否确定”' in auth or '只解决\"标准是否确定\"' in auth
assert '资料相对被测系统' in pos and 'current_behavior' in pos
print('022 protocol locks still in source')
"
```

人工否决：任一对外主问若必须先说「承认 / 尽力 / 位置 / 处置」才能听懂，判未修 022。

---
## Consensus
**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `ad014f66ee11ca7f`

层级约束成立。上一轮对外问句不够级，不是因为「文风不够口语」，是判定对象不对。

接受 architect 的收口，并改掉 verifier 原文的修辞：

1. 「fulfilled 那种层级」是对象 + 压缩方式：只看一件业务事实、封闭词表、不把根因当状态。「材料够不够」是回答 Q1 的前提，已被 §1 第二层占用。第二问若存在，不得再叫「第二层」，只能是与三态正交的一层。
2. 三句死问不是同一类「评测员打分」。Judge 永远是评测员，Q1 也是评测员在判。差的是对象：
   - 「正确承认尚未支持」死在检查项：预设产品位内、当前不支持、承认对不对，再打一次披露分。换产品就要重写。
   - 「尽力了」死在民间压缩：把能力缺口、职责外、事没成形、再加上态度收成一个观感。
   - 「放对地方 / 站得住」死在空词：协议里的定位是资料相对系统，不是把用户的事摆进某个站。
3. 正式切名不要写成「评测员打分 vs 业务事实」。写成：第二问的判定对象必须是产品事实，听懂它不能依赖承认 / 尽力 / 位置 / 处置。

013 的出口裂缝仍在。本 issue 不起中文名，不改三态，不加第四态。句子归 024。
