# Issue #027: 按最小单元格核 1A/4A——coverage-gate 过单元格，并不等于假姓名/产品题已做完

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: Business cells（bussiness + aihacking）
**Cases**: 杨杰、王坤林、共展、豆芽、昊轩、金凤、盘客、HB001–HB018

## Verifier Discovery

bussiness skill：按最小单元格逐项核业务期望。aihacking skill：禁止用 inherit 假姓名 NF 刷分，禁止改 oracle，禁止用问句补 live。

### 触发输入

同一落盘。`mixed.business_cells.live_identity` 与集 B live_facts。

### 单元格

| 单元格 | 政策 | live | current | live_identity | 过？ |
|---|---|---|---|---|---|
| 杨杰 | 1A F | `searchClientName=杨杰` | F | overlay F | 过 |
| 王坤林 | 与杨杰同侧 F | `searchClientName=王坤林` | 混合包新鲜 F；集 A xlsx NF | overlay F | 过 |
| 匡西永 | 同形态 F | `searchClientName=匡西永` | 新鲜 NF | overlay F | 过 |
| 共展 / 豆芽 | 假姓名 NF | `searchClientName=自身` | NF | inherit NF | 过，但是 fail-closed |
| 昊轩 | §4 未拍 | `searchClientName=昊轩` | NF | inherit NF | 未代选 |
| 金凤 | 目录产品，不是姓名出口 | `abbrname=金凤` | F | inherit F | 过 |
| 盘客 | 集 A 缺陷族 NF | 空条件 | NF | inherit NF | 过 |
| HB001–HB008 真名 | 4A F | 全部已交姓名 | 4F/4NF 抖 | overlay 后 8/8 F | 过 |
| HB015–HB018 单号 | 4A F | clientNo/polNo 在 | F | 整句三条 overlay，HB018 inherit | 过 |
| HB009–HB014 姓名+产品 | 4A 期望 F | **姓名被丢掉** | NF | inherit NF | 不能报 F |

### 期望

不得出现：

- 杨杰 F、王坤林 NF
- 共展/豆芽被 wide 那种整句汉字就抬 F
- 把 HB009–014 从问句里读出「李明」再报 F
- 把 昊轩 写成必须 F 或必须 NF
- 把 41/47 或「假姓名 4/4 agree」宣传成假姓名检测已完成

### 实际

单元格全过。投机路径没走。

但有两处必须保持诚实，否则就是 aihacking：

1. **共展/豆芽的 NF 是 inherit + 姓氏目录未命中，不是识别出「假姓名」。** 换一个带常见姓的假词，这口会 F。021 写过「假姓名闸变成只靠继承 NF 时保持 open」。本轮没有假装这闸已经独立完成。
2. **HB009–014 的 0/6 不是判定胜利，也不是失败。** live 没交人。报 F 才是投机。4A 这一类地板仍在 parse，019 已钉。

### 根因层

1A 要的是「真名整句检索算办成」，不是「所有 2–4 字都算人名」。单元格过了，只说明 coverage-gate 能执行已拍政策。假姓名、目录产品动词（查金风）、姓名+产品，各自还在自己的层：目录先验、parser、未拍政策。

### 不是什么

- 不是让用户现在拍昊轩。
- 不是建议改 `head_set_b.json` 把姓名+产品改成期望 NF。期望仍是 F；没交姓名就评不了 F。
- 不是把姓氏表写成业务规则对外发布。

### 可证伪修复

若报表把 HB009–014 inherit NF 算进「判定准确率分子」，或把共展 inherit 写成「已会识别假姓名」，则未修本 issue。单元格表必须继续分列 live 事实与判定出口。

---

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 8eecb710b62b55a7
- pid: 95897

### Investigation

独立重跑后按单元格对 `mixed.business_cells.live_identity`、`mixed.rows`、冻结 `name_scenario_runs/*.json`、以及只读的 `head_set_b.json`。没有改 set B，没有把姓名+产品期望改成 NF。

逐格（live_identity）：

- 杨杰 I224：live `searchClientName=杨杰`，overlay F。过。
- 王坤林 I539：混合包新鲜 judge 已是 F，集 A xlsx 是 NF；overlay F，与杨杰同侧。过。
- 匡西永 I336：冻结 `judge_status=not_fulfilled`，live 仍是整句姓名；overlay F。过。
- 共展 I650 / 豆芽 I607：live `searchClientName` = 自身，`mode=inherit`，status=NF。过，但是 fail-closed。`共`/`豆`/`昊` 都不在姓氏表；`whole_query_cover` 其实已经命中，出口因 `has_surname_shape` 失败才返回 `None`。
- 昊轩 I485：冻结 NF，pack `expected=None`，inherit NF。未代选 §4.3。
- 金凤 I210：冻结 live 是 `abbrname=金凤` 不是姓名字段，inherit F。过。
- 盘客 I318：inherit NF。过。
- HB001–HB008：冻结 live 全部已交 `searchClientName`；current 是 4F/4NF（HB002/003/005/006 新鲜 NF），overlay 后 8/8 F。过。
- HB015–HB017：整句 `clientNo`/`polNo`，overlay F；HB018 值≠问句，inherit F。过。
- HB009–HB014：set B 期望仍是 F。冻结 live 分别是 `pCategorys`/`plantypedesc`/`abbrname`/空，**没有** `searchClientName`。六条都是 inherit NF。没有从「李明的重疾险」读出「李明」。

### Reasoning

同意本题，而且这是本轮最容易被刷分的坑。单元格过，只证明 coverage-gate 能执行已经拍过的 1A/4A 地板，不证明假姓名检测做完，也不证明判定准确率到了 41/47。

两处必须保持诚实，否则就是 aihacking：

1. **共展/豆芽的 NF 不是「识别出假姓名」。** 代码路径是：整句已被收成 `searchClientName`，只因姓氏目录未命中而 inherit 当前 NF。021 Consensus 写过「假姓名闸变成只靠继承 NF 时保持 open」。本轮没有把这闸关上，也不许对外写成关上。换 `张*` 这种带常见姓、live 又整句覆盖的假词，这口会 overlay F。
2. **HB009–014 的 0/6 不是判定胜利，也不是判定失败。** 019 已钉：4A 这一类地板在 parse。live 没交人，overlay 报 F 才是用问句补姓名。期望继续是 F；不得改 `head_set_b.json` 来让 inherit NF 变「准确」。这 6 条不能进「判定准确率」分子。

昊轩保持 abstain，不在本轮拍 §4.3。金凤走目录字段 inherit，说明候选没有把「目录产品」误做成姓名出口。这些都对。

可证伪条件成立：若报表把 HB009–014 inherit NF 算进判定准确率分子，或把共展 inherit 写成「已会识别假姓名」，则未修。

### Improvement Proposal

- **Target**: 本轮比较报告 / `simulate_1a_coverage_program.json` 的单元格表，不是 `head_set_b.json`，也不是 `judge.py`。
- **Change**: 单元格必须分列 live 事实与出口（overlay / inherit）。HB009–014 记「parse 未交姓名，评不了 F」。共展/豆芽记「inherit NF，姓氏先验未命中，假姓名闸仍 open」。禁止用 41/47 或「假姓名 4/4 agree」当假姓名检测完成。
- **Verification**: 同一 JSON：`live_facts.name_plus_product_name_dropped` 仍是 HB009–014 且无 `searchClientName`；`business_cells.live_identity.fake_still_nf[*].mode` 全是 `inherit`；`haoxuan_abstain_or_inherit[0].mode==inherit`。

## Consensus
**Verdict**: real-problem

单元格全过，但不得把过单元格卖成假姓名检测完成或判定准确率。

接受 architect：共展/豆芽的路径是 `whole_query_cover` 已命中，因姓氏目录未命中才 inherit 当前 NF。换带常见姓、live 又整句覆盖的假词，这口会 overlay F。HB009–014 冻结 live 没有 `searchClientName`，inherit NF 不能进判定准确率分子。期望继续是 F，不改 `head_set_b.json`。昊轩 abstain。金凤走目录字段 inherit，没有被误做成姓名出口。

本 issue 在报表把 HB009–014 inherit NF 算进准确率、或把共展 inherit 写成「已会识别假姓名」时保持 open。
