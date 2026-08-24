# Issue #058: 第二问不是再开一张嘴，是读已经裁完的产品事实

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Compute / 谁算第二问
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户本轮问的是实现，不是再换一句口语：这个东西到底怎么算出来。

046–048 已经否掉三条假路：Judge 再填一格、fulfilled 新枚举、只在没办成后出现。
040 留下的计算位置是：

> 产品事实从哪来：已经裁完的能力/职责判断，及其依据资料

本 issue 只钉：这句话落到现行系统里，是哪一次读，不是哪一次新判。

### 现在谁在写字

`impl/core/schema/judge.py` 里，模型可写的评估字段仍只有：

```text
JudgeFulfillmentAssessmentOutput.status
```

`FulfillmentAssessment` 另有 `authority_tool_call_ids`，那是引用，不是第二问答案。

`spec/info-volume.md`：

> judge 只产出 fulfillment（细粒度 + 整体两层），不产 verdict。

所以第一问的嘴已经定了。第二问若再让这张嘴填一次，047 Consensus 已经写过后果：刚写了办成了，下一句就倾向写成立住了。那是对齐，不是产品事实。

### 产品事实其实已经有裁口

`spec/alg/authority.md` §8.3 具名三种 statement：

```text
职责外
职责内能力缺失
职责内正常
```

这三种不是第二问，是第二问要读的原料。040 说「没立住」= 职责内能力缺失的投影。对应读法只能是：

```text
职责内正常         → 立住了
职责内能力缺失     → 没立住
职责外             → 说不清（差在哪儿=职责外）
unresolved         → 说不清（差在哪儿=依据不充分）
同一件上裁口打架   → 说不清（差在哪儿=同一件上裁口不一致）
这一件还没有裁口   → 说不清（差在哪儿=依据不充分）
```

这是读已经写下的前缀，不是新分类器。禁止另做的读法：

```text
办成了             ⇏ 立住了
没办成             ⇏ 没立住
is_supported=false ⇏ 没立住
required_capabilities 里有这个词 ⇏ 立住了
系统说了「暂不支持」⇏ 没立住
```

`impl/core/authority_gate.py` 现在已经在读这些前缀，但只拿去改第一问：职责外强制说不清，能力缺失不得降成说不清。它不是第二问的出口。第二问是同一份裁口的第二个消费者。

### 「已经裁完」不是「这一次刚好问过」

Authority 是可选的。Judge 只在第一问需要裁边界时才调。姓名查找办成了，常常没有 `authority_tool_call_ids`。

若第二问只读这一次调用：

| 这一件 | 常见现场 | 只读这一次调用会变成 | 错在哪 |
|---|---|---|---|
| 按姓名找，而且给到了 | 往往没调 authority | 说不清 | 产品早就立住按姓名找；缺的是这一次提问，不是产品事实 |
| 按姓名找，漏了 | 往往也没调 | 说不清 | 过严案会看起来像「根本没这项功能」 |
| 投保年缺口 | 调了，裁成能力缺失 | 没立住 | 这一格碰巧算对 |
| 查天气 | 调了，裁成职责外 | 说不清 | 这一格碰巧算对 |

只读这一次调用，会把「立住了」系统性地收成「说不清」。成功案和过严案都会被吃掉。这和「只有没办成才有第二问」是同一类残缺，只是残在另一侧。

040 写的是「已经裁完的判断，及其依据资料」。依据资料是产品自己认账的材料，不是这一次交付，也不是库存字段表。所以计算位置是：

```text
先看：这一条期望上，已经写下的能力/职责裁口
没有：再读同一件所依据的、已经用来裁过同类问题的资料
       仍没有裁口 → 说不清（依据不充分）
不准：用这一次办成了没有去补
不准：新开一个 Judge 标签
不准：把 is_supported / catalog 当成裁口
```

「以后若要每一行都有第二问」，可以在 Judge 写完第一问之后，对还没有裁口的那一件问同一类 authority 问题。那仍不是 Judge 填，也不是新分类器。开不开这第二趟，是运行成本，交章程 §4，本 issue 不代选。

### 可证伪

1. 若存在一种合法读法，让 Judge 在写完 `status` 之后再填第二问，同时还不触发 047「同一张嘴对齐」，本 issue 不成立。
2. 若「只读这一次 `authority_tool_call_ids`」就能在成功的姓名查找上读出「立住了」，而不偷看这一次交付，本 issue 把「已经裁完」说宽了。
3. 若把 statement 前缀映射成三态，其实是在新发明类型，本 issue 把「读」说成了「判」。

### 不是什么

- 不是批准现在就去调第二次 authority
- 不是宣布「立住了」为对外词
- 不是让 authority_gate 改写 fulfilled

### 请对手挑战

- 「已经裁完」会不会被读成「去翻历史所有 authority 决议当库存」？那和被禁的 catalog 差在哪？
- 这一次没裁口就说不清，是不是让第二问在正常流量上长期空着，等于没有出口？
- 前缀映射是不是已经规则化了？换一个不叫「职责内正常」的 statement，读法会不会塌？

### 未消元

- 对象粒是不是同一条期望：见 059
- 算完之后写在哪、看见挂在哪：见 060
- 现在改不改出口：见 061

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: f7ab9fd0b34ddbc9
- pid: 59819

### Investigation

自己重读了计算位置，不把 verifier 的「已经裁完」第二步当成已经合法：

- `spec/alg/authority.md` §5：能力/职责边界类 `statement` 必须写明三种结论类型：`职责外` / `职责内能力缺失` / `职责内正常`。这是 prompt 约束，不新增 schema 字段。
- 同文件 §8.3：这三种 statement 的现行消费者只有第一问。职责外 → `not_evaluable`；职责内能力缺失 → 不强制改状态，按这次交付写 F/NF；职责内正常 → 继续原评价。
- 同文件 §7 / §14.2 / 改造清单第 10 条：不存在跨 case / 跨轮次「问题→结论」复用资产。复用只允许两层——证据空间里的资料，以及同一次 Runtime 任务内按 `decision_question + environment_snapshot_sha256 + Evidence revisions` 去重。结论永远现场综合。
- `spec/alg/fulfilled.md` §1 / `spec/info-volume.md`：Judge 只产 fulfillment（细粒度 + 整体），不产 verdict，不并进产品功能。
- `spec/alg/product-function.md` §7.2 / §8：禁止让 Judge 再填一个新标签；派生列若以后有，也不是 Judge 产出。
- `impl/core/schema/judge.py`：`JudgeFulfillmentAssessmentOutput` 可写评估字段只有 `status`；`authority_tool_call_ids` 是引用，不是第二问答案。`required_capabilities` 在 `BusinessExpectation` / `JudgeBusinessExpectationOutput` 上，是库存名。
- `impl/core/authority_gate.py` L132–192、L213–272：已经在读 §8.3 前缀（`职责外` / `职责内能力缺失` / `职责内正常`），但只拿去改第一问。无匹配前缀时 `_conclusion_kind_from_statement` 返回空串，不发明第四种。扫描范围是**当前 assessment 的 `authority_tool_call_ids` + 当前 trace 的 tool_audit**，audit 之外一律当不存在（L204）。
- 040 Consensus：计算位置 = Authority 已裁的能力/职责 statement **及其依据资料**；不是 catalog / `is_supported` / `current_behavior`；不是这一次给没给到。
- 047 Consensus：投影，不是同一轮 Judge 再填，也不是评测员重判三类前缀。

姓名查找办成了、常常没有 `authority_tool_call_ids`：这和 §7「不必调用」+ §8.1「只有裁职责外 / 能力缺失时必须先问」是对得上的现场，不是 verifier 编的。

### Reasoning

核心前半句成立：第二问不是再开一张嘴。后半句「没有这一次裁口，就去读已经用来裁过同类问题的资料」不成立。那一步会把 040 的「依据资料」读成被禁的结论库存。

**1. 前缀映射不是新分类器，是 §5 / §8.3 / 040 已具名类型的投影。**

040 已经写死：`没立住` = §8.3「职责内能力缺失」的投影。047 禁止的是评测员**重判**三类前缀，不是禁止把已经写下的种类读出来。gate 现在做的就是这种读：`startswith(职责外|职责内能力缺失|职责内正常)` → 三种 kind，未匹配 → 空。第二问若存在，只能做第二个消费者，映射只能是：

```text
职责内正常         → 内部手柄「立住了」
职责内能力缺失     → 内部手柄「没立住」
职责外             → 说不清（差在哪儿=职责外）
unresolved 类      → 说不清（差在哪儿=依据不充分）
同一件上 kind 打架 → 说不清（差在哪儿=同一件上裁口不一致）
这一件没有裁口     → 说不清（差在哪儿=依据不充分）
```

这不是 039 那种「先认哪一类」。换一个不叫「职责内正常」的 statement，读法会塌成空 kind → 说不清。塌的是 authority 合同（§5 硬格式），不是第二问另做同义词典。禁止为了少塌去加同义表。

合法读法不存在「Judge 写完 `status` 再填一格还不触发 047 对齐」。同一张嘴兼答，对齐几乎一定发生。可证伪 1 打不穿。

**2. 这一次没裁口就说不清，是诚实出口，不是没出口。**

Authority 可选。§7：条件已能直接比、与资料冲突无关，就不应调用。成功的姓名查找经常没有 `authority_tool_call_ids`，只读这一次调用，读不出「立住了」。这是真的。

它推不出 verifier 的下一跳。040 的全函数已经给了格：分不清「没立住」还是「立住了、这一次没用」→ 说不清（依据不充分），且不得用说不清装长期没立住。说不清是三态之一，不是空指针。空的是「立住了」在幸福路径上的阳性，不是第二问本身。

用这一次办成了去补「立住了」，048 / 040 / product-function §2.3 已死。用「产品材料看起来会裁成职责内正常」去补，是新开一张嘴。两条都比「说不清」更假。

**3. 「已经裁完」不得看过这一次任务。看过就是目录。**

040 写「statement 及其依据资料」。依据资料是**已经写下的那条 statement 的 basis**，用来核对这条裁口，不是第二份分类器。

authority.md 写得很硬：不沉淀「问题→结论」配对；跨 case 复用只在证据空间；同任务内只按 `decision_question` 去重。`authority_gate.py` 也只认当前 trace audit。

verifier 的第二步「再读同一件所依据的、已经用来裁过同类问题的资料」有三种落地，全禁：

| 落地 | 为什么是目录 / 新判 |
|---|---|
| 翻历史 case 的 authority 决议 | 跨 case 结论资产，§7 / §14.2 明文没有 |
| 按「同类问题」去对 `is_supported` / 能力清单 / catalog | 040 点名不是产品事实 |
| 现场读产品文档、自己裁出三种前缀 | 新开一张 Authority/Judge 嘴，不是读 |

「已经裁完」收成：

```text
可读
  1. 这一条 expectation 已经写下的能力/职责 statement
     （本 assessment 的 authority_tool_call_ids，
      以及同一次 Runtime 任务内 §7 允许去重复用的那一次）
  2. 上述 statement 的 basis / 依据资料（核对这条裁口，不另裁）

不可读
  - 别的 case / 别的轮次的决议
  - is_supported / required_capabilities / catalog / current_behavior
  - 这一次办成了没有
  - 「同类问题曾经被裁过」的库存印象

没有裁口 → 说不清（依据不充分）
要不要在 Judge 写完第一问之后，对还没有裁口的那一件再问同一类 authority：
  仍不是 Judge 填，也不是新分类器；开不开这趟是运行成本，交章程 §4。
```

可证伪 2 的方向反了。只读这一次调用，在成功姓名查找上读不出「立住了」，这不能证明要把「已经裁完」说宽；它证明 040 把「依据不充分」留在说不清是对的。把「已经裁完」说宽的是本 issue 原文第二步。

本轮不批准第二次 authority，不宣布「立住了」为对外词，不让 `authority_gate` 改写 fulfilled。

## Improvement Proposal

**Problem**: 第二问若再让 Judge 填，会对齐第一问；若按原文第二步去翻「同类已裁资料」，会变成被禁的结论目录。

**Proposed Change**: 锁窄后的计算位置。不改 `spec/**`、`impl/**`、前端。

**Design**:

```text
058 锁（谁算，不是看见面）：

- 第一问唯一的嘴：JudgeFulfillmentAssessmentOutput.status
- 第二问：读，不是判。第二个消费者读同一份 §8.3 前缀。
- 读的范围：
    这一条 expectation 上已经写下的 statement
    + 同一次 Runtime 任务内 §7 去重复用
    + 该 statement 的依据资料（核对，不另裁）
- 前缀投影（内部手柄，不是对外题面）：
    职责内正常     → 立住了
    职责内能力缺失 → 没立住
    职责外         → 说不清（职责外）
    unresolved / 无前缀 / 无调用 / kind 打架 → 说不清（写差在哪儿）
- 不是新分类器：不新增类型，不加同义表，不重判三类前缀。
- 禁止：办成了⇏立住了；没办成⇏没立住；
        is_supported / catalog / required_capabilities / 「暂不支持」文案
- 禁止：跨 case / 跨轮次决议库存；「同类问题曾经裁过」
- 这一次没裁口 = 说不清（依据不充分）。这是出口，不是残缺。
- 以后若要阳性「立住了」出现在从未问过 authority 的成功件上：
    只能再问同一类 authority 问题，不能回看目录，也不能让 Judge 填。
    开不开这趟：章程 §4，本 issue 不代选。
```

**Implementation Steps**:

1. Consensus 收下「读不是判」，删掉原文「再读已经用来裁过同类问题的资料」。
2. 把「已经裁完」写成上面的可读 / 不可读两栏，不得写成历史决议表。
3. 不写字段名、列名、对外中文。不改 `authority_gate.py` 的第一问消费。

**Risks**: 把投影听成评测员重判前缀；把说不清听成「第二问没出口」再偷用办成了或目录去补；把 §4 的第二趟 authority 听成本轮批准。

**Verification**:

```text
# 1. impl/core/schema/judge.py：JudgeFulfillmentAssessmentOutput 仍只有 status
# 2. impl/core/authority_gate.py：前缀只改第一问；扫描只认当前 trace audit
# 3. spec/alg/authority.md §7 / §14.2：无跨 case「问题→结论」资产
# 4. 纸面：姓名查找办成了且 authority_tool_call_ids 为空 → 第二问只能是说不清（依据不充分）
#    不得读成立住了，也不得去翻别案决议
# 5. 纸面：投保年有「职责内能力缺失」→ 内部手柄没立住；不得回写 status
# 6. Consensus 不得批准本轮第二次 authority，不得宣布对外中文
```

**Why I Cannot Apply It**: 只读 peer。计算位置是锁，不是本轮改 gate / schema。第二趟 authority 属章程 §4。

---
## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `f7ab9fd0b34ddbc9`

第二问不是再开一张嘴。它读已经写下的能力/职责前缀，不让 Judge 再填，也不让评测员重判三类。

收下 architect 的收窄：

- 「已经裁完」只读：这一条期望上已经写下的 statement，加上同一次 Runtime 任务内 §7 允许去重的那一次，加上该 statement 的依据资料（核对这条裁口，不另裁）。
- 删掉原文第二步「再读已经用来裁过同类问题的资料」。那一步是被禁的结论目录，不是 040 说的依据资料。
- 这一次没有裁口 → 说不清（依据不充分）。这是出口，不是残缺。不得用办成了补成立住了，也不得翻别案决议。
- 前缀投影（内部手柄，不是对外题面）：职责内正常 → 立住了；职责内能力缺失 → 没立住；职责外 / unresolved / 无前缀 / 无调用 / kind 打架 → 说不清。
- 以后若要阳性「立住了」出现在从未问过 authority 的成功件上，只能再问同一类 authority，不能回看目录，也不能让 Judge 填。开不开这趟：章程 §4，本轮不批准。

本轮不改 `authority_gate.py` 的第一问消费，不宣布对外中文。

闸：exit 0，`isolation_valid=true`。`scope_valid=false` 的路径全是 host 写的 `impl/data/context_store/**/judge-*.json`（08-14 旧条 + 08-16 旁路落盘）。architect 回应 0 次要改这些文件。按 053–057 惯例豁免，不重开 spawn。wrapper pid 59609 / 回应写 59819，spawn-id 对齐即可。
