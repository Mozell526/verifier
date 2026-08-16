# Issue #037: 冻结分数与整句覆盖门撞车，不能当泛化证据；主动改判必须和继承分开报

**Class**: evaluation
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: In-memory judge overlay（不是生产代码）
**Cases**: 混合包 48；集 A 341；15 条合成探针

## Verifier Discovery

036 钉了原则。本 issue 只报数字，以及这些数字准许说什么、不许说什么。

### 触发输入

```bash
python3 issues/trace/simulate_1a_principle_program.py
```

落盘 `issues/trace/simulate_1a_principle_program.json`
SHA-256 `0205668a62c18e516a12d973e3273988235a02b6caafaf9a9807341548d95367`

architect 必须自己重跑，不抄下面的表。

### 期望

章程：必须分列主动 overlay / 继承 inherit；禁止只报混合包分数；若冻结分数与 `live_identity` 完全一样，必须老实写本轮赢的是标准和边界，不是新分数。不得用 341 或 41/47 当 KPI。

Bussiness：按最小单元格逐项过，不拿平均分代替单元格。

### 实际

冻结对照（与旧覆盖门脚本同口径，旧脚本未改）：

| 口径 | 混合 agree/47 | 集 A F/NF | 集 A 翻面 | 混合 overlay/inherit |
|---|---|---|---|---|
| 当前判定 | 36 | 213/128 | — | — |
| 凡 2–4 字都成功 | 27 | 238/103 | 抬 25，含共展/豆芽/昊轩/红莲保单 | 30/18 |
| 先看姓再看名 | 35 | 210/131 | 抬王坤林+家办客户；砍 5 条保单号 | 35/13 |
| 题型分流（已否） | 41 | 215/126 | 抬王坤林+红莲保单 | 17/31 |
| 整句覆盖门（地板） | 41 | 214/127 | 只抬王坤林 | 15/33 |
| 对象覆盖（候选） | 41 | 214/127 | 只抬王坤林 | 15/33 |

`set_a.object_cover_vs_live_identity` = `[]`  
`mixed.object_cover_vs_live_identity` = `[]`

对象覆盖主动 overlay 的 15 条，仍是：杨杰 / 郑鑫 / 匡西永 / 王坤林 + HB001–008 整句真名 + HB015–017 整句单号。没有新的冻结题被改判。

合成探针 15/15 按原则落点。冻结数据刷不出来、原则却多出来的只有两格：

- `SYN-concat-name-product`：问句「李明重疾险」，live 交姓名+产品 → 对象覆盖 overlay 成功；整句覆盖门 inherit（字段多于 1）
- `SYN-two-ids`：两个单号连写 → 对象覆盖 overlay 成功；整句覆盖门 inherit

这两格**不准**加进 47 分母。它们证明的是边界，不是生产分布。

### 业务单元格（对象覆盖）

| 单元格 | 结果 | 模式 |
|---|---|---|
| 杨杰 | 成功 | 主动改成功 |
| 王坤林 | 成功 | 主动改成功（集 A 从 xlsx 失败抬上；混合包新鲜判定已经是成功） |
| 共展 / 豆芽 | 失败 | 不改判。原因 `name_not_ok`，不是「已识别假姓名」 |
| 昊轩 | 失败（当前） | 不改判。§4.3 未拍 |
| 金凤 | 成功（当前） | 不改判。原因 `no_identity_field`（产品字段） |
| 盘客 | 失败 | 不改判 |
| HB001–008 | 成功 | 主动改成功 |
| HB015–017 | 成功 | 主动改成功 |
| HB018 找一下客户号… | 成功（当前） | 不改判。残句「找一下客户号」 |
| HB009–014 | 失败（当前） | 不改判。live 没交姓名。0/6 不准进判定准确率分子 |
| 张忠波保单号 | 成功（当前） | 不改判。残句「保单号」 |
| 家办客户 | 失败（当前） | 不改判。原因 `no_live` |
| 红莲保单 | 失败（当前，集 A） | 不改判。不在混合包里，41/47 看不见 |

混合 inherit 原因分列：`name_not_ok` 16，`residual_nonempty` 10，`no_live` 3，`not_grounded` 3，`no_identity_field` 1。每一行都有原因，没有「看情况」。

### 根因层

分数撞车有两种读法。错误读法：对象覆盖就是整句覆盖门换了名字。正确读法：冻结 live 里几乎没有「多对象且残句为空」的身份题，所以特例投影和原则全文在这批数据上重合。合成探针把重合打破了，但探针不是分布。

aihacking：如果为了让分数看起来「有进步」而把合成探针算进 47，或把 inherit 失败算成「认假准确率」，就是在改标准过测试。本轮禁止。

### 不是什么

- 不是对象覆盖已经比覆盖门更能打冻结集。
- 不是 41/47 又一次成为发版理由。
- 不是姓名+产品六条被判定修好了。

### 可证伪修复

报表必须同时有：主动 overlay 名单、inherit 原因分列、与 `live_identity` 的逐行差、合成探针单独成章。缺任何一项，或把 41/47 写成候选胜利，本 issue 未修。

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 770d8502492aedbc
- pid: 44788

### Investigation

- Re-ran `python3 issues/trace/simulate_1a_principle_program.py` myself. SHA-256 `0205668a62c18e516a12d973e3273988235a02b6caafaf9a9807341548d95367` matches the issue. I am not copying verifier’s table; these numbers are from that process.
- Frozen equality with `live_identity`:
  - set A current 213/128; object_cover and live_identity both 214/127; both lift **only** I539 王坤林; `set_a.object_cover_vs_live_identity = []`
  - mixed agree/47 = 41 for role / live_identity / object_cover; both latter are 15 overlay / 33 inherit; overlay IDs identical: I224 / I310 / I336 / I539 / HB001–008 / HB015–017; `mixed.object_cover_vs_live_identity = []`
- Mixed inherit reasons I counted from the dump: `name_not_ok` 16, `residual_nonempty` 10, `no_live` 3, `not_grounded` 3, `no_identity_field` 1, plus 12 `overlay_f_name` + 3 `overlay_f_id`. No unlabeled row.
- Stronger check than the status-diff: mixed has **0** multi-field rows. Set A has 42 multi-field; only I129 is multi-field + grounded + empty residual, and it has no identity field. So frozen data literally cannot exercise the two extra object-cover cells.
- Synthetics: 15/15 `probe_ok`. Status differs from whole-query on exactly two probes — `SYN-concat-name-product` (李明+重疾险 → overlay F vs inherit) and `SYN-two-ids` (two IDs → overlay F vs inherit). I did not add them to 47.
- Business cells match the issue: 杨杰/王坤林 overlay F (mixed current for I539 is already F from fresh judge; set A xlsx current is NF). 共展/豆芽 inherit NF via `name_not_ok`. 昊轩 inherit, not decided. 金凤 inherit via `no_identity_field`. HB009–014 inherit NF. I007 inherit, current F kept. I248 inherit NF and is not in the mixed 47.

### Reasoning

The honest reading is the correct one. Object-cover is **not** a rename of `live_identity`.

A rename would be the same predicate with a new function name. These are different predicates. They agree on frozen labels because the extra clauses have no frozen identity row to fire on. They disagree on the two synthetic cells the principle says it owns. That is exactly what charter Done #4 required us to write down: 本轮赢的是标准和边界，不是新分数.

The wrong reading — “41/47 again, ship it” — is the same pack artifact 026 already demoted. Role-machine also scored 41/47 and was rejected. I will not treat 41/47 as a KPI. I also will not treat inherit-NF as “fake-name accuracy”: 共展’s reason is `name_not_ok`, not overlay NF.

One tighten: an empty `object_cover_vs_live_identity` list only proves **label** identity. It does not by itself prove “no multi-object empty-residual identity rows” (both mouths could inherit). The scan above closes that gap. Keep that scan in the report, not just the diff list.

HB002/HB003/HB005/HB006/I336 are overlay F here and fresh-judge NF. That overlay is the same local floor as `live_identity`. It is not evidence the host is fixed. That sentence belongs to 038.

### Improvement Proposal

- **Target**: `issues/trace/simulate_1a_principle_program.json` and any later write-up of this round. Not `draft/judge.py`.
- **Change**: Every report of this candidate must carry, together: (1) overlay ID list, (2) inherit reason counts, (3) `object_cover_vs_live_identity` row diffs, (4) the multi-field / empty-residual / identity scan, (5) synthetics in their own chapter. Ban: folding the two extra synthetics into the 47 denominator; calling 41/47 a candidate win; calling inherit-NF a fake-name score.
- **Verification**: `python3 issues/trace/simulate_1a_principle_program.py` → SHA-256 `0205668a62c18e516a12d973e3273988235a02b6caafaf9a9807341548d95367`, `set_a_diff_vs_live_identity=[]`, `mixed_diff_vs_live_identity=[]`, `synthetics_all_ok=true`, mixed overlay IDs exactly the 15 listed above.

## Consensus
**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `770d8502492aedbc`

冻结分数与整句覆盖门撞车，是预期，不是换皮胜利。两种谓语不同：冻结 live 里没有「多对象且残句为空」的身份题（混合包 0 条多字段；集 A 唯一多字段+残句空+对齐的是综拓潜客，且没有身份对象），所以标签重合。空的 `object_cover_vs_live_identity` 只证明标签相同；真正证明「多出来的格子没有冻结身份题可打」的是上面这次扫描。报告必须带着这次扫描，不能只报空差表。

本轮赢的是标准和边界，不是新分数。禁止把混合包 41/47 写成候选胜利。禁止把 inherit 失败写成假姓名准确率。合成探针两格（「李明重疾险」姓名+产品、「两个单号连写」）证明原则比整句门多出来的手，不准加进 47 分母。

闸与数字：architect 与收口各重跑一次，SHA-256 `0205668a62c18e516a12d973e3273988235a02b6caafaf9a9807341548d95367`。集 A 只抬王坤林；混合 overlay 仍是杨杰 / 郑鑫 / 匡西永 / 王坤林 + HB001–008 + HB015–017。不并进 `draft/judge.py`。
