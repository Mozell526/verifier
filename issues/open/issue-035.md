# Issue #035: 整句覆盖门不是原则，只是「单字段且值=问句」的局部代理

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: In-memory judge overlay（不是生产代码；负对照）
**Cases**: 杨杰 / 王坤林 / 红莲保单 / 张忠波保单号 / 家办客户；对照 object_cover 在冻结数据上零行差异

## Verifier Discovery

用户原话：方案很奇怪，又很难说清哪里错；担心扩散到别处容易失败；看似没有规则化，本质其实是规则化。主会话已认账：覆盖门只对「用户只打了一个词、系统只交一个字段、这个字段还长得像姓名或单号」成立。正式标准是「用户要的事办成了没有」，不是「live 值 == 整句问句」。

本 issue 只钉：上一轮候选的形状是局部代理。替代原则在 036。冻结数字在 037。源头仍不能并进判定在 038。

### 触发输入

```bash
python3 issues/trace/simulate_1a_principle_program.py
```

落盘 `issues/trace/simulate_1a_principle_program.json`
SHA-256 `0205668a62c18e516a12d973e3273988235a02b6caafaf9a9807341548d95367`

旧脚本 `simulate_1a_coverage_program.py` 没改。`exit_live_identity` 仍在，只作负对照 / 局部地板。

`whole_query_cover`（旧脚本 L122–130）先要求：

1. 字段条数 == 1
2. 值条数 == 1
3. 值 == 整句问句

三条同时成立才让 `exit_live_identity` 有资格出口。这就是用户说的「看似没规则化」。它没有 12 种题型名，但出手条件是三个死门槛。

### 期望

`spec/alg/fulfilled.md` §1：只看一件事——系统有没有帮用户办成想办的事。证据是 live 交出来的条件，不是问句和值的字符串相等。

用户本轮：设计要原则 / 标准 / 边界，排除歧义，覆盖所有可能出现的情况。覆盖门不能再被卖成可泛化架构。

### 实际

覆盖门在冻结数据上很好看：混合包 41/47，集 A 只抬王坤林。但这是因为它**大多数题根本没出手**。

反例不在分数里，在门槛外：

| 问句 | live | 覆盖门 | 为什么没资格 |
|---|---|---|---|
| 红莲保单 | 红莲 | 不改判 | 值 ≠ 问句 |
| 张忠波保单号 | 张忠波 | 不改判 | 值 ≠ 问句 |
| 找一下客户号C000777123456 | C000777123456 | 不改判 | 值 ≠ 问句 |
| 李明重疾险（合成） | 李明 + 重疾险 | 不改判 | 字段多于 1 |
| 家办客户 | 空 | 不改判 | 没有字段 |

341 条几乎没改判，不是已经泛化，是第三个死门槛把题挡在门外。

### 根因层

把「值等于整句」升格成架构，等于用一种句子形态代理「办成了没有」。形态碰巧覆盖杨杰 / 王坤林 / 整句单号，就显得干净。换到「查一下李明」「李明重疾险」「红莲保单」，同一条原则立刻没手可出。这就是用户担心的扩散失败。

025 已 Consensus：`exit_role` 是题型机。本 issue 不重开 025，只补用户否掉覆盖门气质之后还缺的钉：覆盖门也不是原则。

### 和 025 / 026 的边界

- 025：题型机被否。不重开。
- 026：覆盖门过双闸、比题型机短。那个「过双闸」作为局部地板仍成立。本 issue 否的是把它做成可泛化架构，不否「只抬王坤林」这张旧表。

### 不是什么

- 不是说覆盖门在冻结数据上算错了。
- 不是要求立刻剥「查一下」让更多题改成功。
- 不是把 41/47 作废成「连局部地板都没有」。

### 可证伪修复

原则文必须写明：整句相等 = 对象覆盖在「恰好一个字段且值=问句」时的特例。候选函数不得再叫 coverage-gate，也不得把 `live_identity` 当唯一候选。若新文案仍把「值==问句」写成充分原则，本 issue 未修。

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 770d8502492aedbc
- pid: 44788

### Investigation

- Re-ran `python3 issues/trace/simulate_1a_principle_program.py`. Wrote SHA-256 `0205668a62c18e516a12d973e3273988235a02b6caafaf9a9807341548d95367`, identical to the issue claim. Old `simulate_1a_coverage_program.py` was imported, not edited.
- Read `whole_query_cover` / `exit_live_identity` in the floor script. Gate is exactly three dead checks: `len(fields)==1`, `len(values)==1`, `values[0]==query`. Only then does field type + 1A surname/catalog decide overlay F. No `pack_role`. Never overlay NF.
- Read `decide_object_cover` (`simulate_1a_principle_program.py` L93–147) and principle §3–§7. Object-cover uses span + residual + field kind. Whole-query is the `|fields|=1 ∧ value=query` projection, already written in principle §7.
- Independent frozen scan: mixed 48 rows are 45 single-field + 3 empty-live, **0 multi-field**. Set A has 42 multi-field rows; the only multi-field, grounded, empty-residual row is I129「综拓潜客」, and it has **no** name/id field. So frozen scores *must* collide with `live_identity`. That collision does not make whole-query the right object.
- Oracle: `spec/alg/fulfilled.md` §1 只评「用户要的事办成了没有」，证据是 live 交出的条件，不是「值 == 整句」。
- Did not reopen 025/026. 026’s “过双闸、只抬王坤林” as a **local floor** still holds on this rerun (set A flip = only I539).

### Reasoning

Attribution is right. Whole-query is **not** already the right object.

`value == 整句` looks like a principle because it has no 12 role names. It is still a sentence-shape proxy: it may speak only when the user typed one token and live returned exactly that token in one field. That is a *sufficient* local detector for “this one delivered object is the whole request”. It is not the meaning of fulfilled. Swap the sentence to「红莲保单」「查一下李明」「李明重疾险」, the same “principle” has no hand. That is the diffusion failure the user named.

Counter-argument I considered: keep whole-query because it is the crispest overlay and frozen production never needs more. Rejected. Crispness is why it is a **floor**, not why it is an architecture. Charter this round already demotes `live_identity` to 局部地板 / 负对照 and forbids reselling 整句覆盖门. The right object is the one 036 names: live objects as grounded spans, leftover text, then field type.

Tighten one sentence in the issue: “341 条几乎没改判” is about **flips vs current** (only 王坤林). Object-cover / live_identity still *overlay* 57 set-A rows (4 names + 53 IDs). The third dead gate is why those overlays are almost all already-F IDs and bare names, not why the function is silent on 341 rows.

025 already killed the role machine. This issue correctly nails the leftover mistake: a short equality gate is still a rule, just a smaller one.

### Improvement Proposal

- **Target**: `issues/trace/name-object-coverage.md` §7 (already drafted); keep `exit_live_identity` in `simulate_1a_coverage_program.py` as negative control only. Do not rename `object_cover` back to coverage-gate. Do not merge either function into `draft/judge.py`.
- **Change**: Freeze this sentence as the only legal relation: 整句相等 = 对象覆盖在「恰好一个字段且值=问句」时的特例。Candidate reports must keep a `live_identity` column and an `object_cover_vs_live_identity` diff. If a later write-up says “值==问句 is the principle”, this issue is unfixed.
- **Verification**: `python3 issues/trace/simulate_1a_principle_program.py` and assert SHA-256 `0205668a62c18e516a12d973e3273988235a02b6caafaf9a9807341548d95367` (or a new dump whose `mixed.object_cover_vs_live_identity` / `set_a.object_cover_vs_live_identity` stay explicit). Confirm `git diff -- issues/trace/simulate_1a_coverage_program.py` is empty.

## Consensus
**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `770d8502492aedbc`

整句覆盖门不是原则。`whole_query_cover` 是三个死门槛：字段条数=1、值条数=1、值=整句。它能抬杨杰 / 王坤林 / 整句单号，是因为这些题碰巧落在门槛里。换到「红莲保单」「查一下李明」「李明重疾险」，同一张嘴立刻没手可出。这就是用户说的「看似没规则化、本质是规则化」，也是扩散失败的形状。

接受收紧一句：「341 条几乎没改判」说的是相对当前判定的翻面（集 A 只抬王坤林）。对象覆盖 / 整句门在集 A 仍会 overlay 57 行（4 个姓名 + 53 个单号），只是这些行几乎本来就是成功。第三个死门槛解释的是「为什么翻面很少」，不是「函数对 341 条保持沉默」。

唯一合法关系（原则文第 7 节，本轮冻结）：整句相等 = 对象覆盖在「恰好一个字段且值=问句」时的特例。`live_identity` 只作负对照 / 局部地板。哪一份后文再把「值==问句」写成充分原则，本 issue 未修。

闸：exit 0，`isolation_valid=true`，`scope_valid=true`。SHA-256 `0205668a62c18e516a12d973e3273988235a02b6caafaf9a9807341548d95367` 与 architect 独立重跑一致。旧脚本 `simulate_1a_coverage_program.py` 没改。不并进 `draft/judge.py`。
