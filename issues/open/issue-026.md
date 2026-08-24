# Issue #026: coverage-gate 用同一句「整句是否被 live 收成一个身份」对齐 1A，不必再写姓名状态机

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: In-memory judge overlay（候选形状，未发版）
**Cases**: 混合包 48；集 A 341；对照 wide / surname / role

## Verifier Discovery

用户要的是：在内存里调试 judge，看哪种处理更好，且要有泛化性。本轮只加一个短候选 `exit_live_identity`，负对照沿用已证伪的三口。

### 触发输入

```bash
python3 issues/trace/simulate_1a_coverage_program.py
```

SHA-256 `f180cb60bcbde3a978bbaa64e28971988676d4ea97194fd990d4be05bd72e835`

候选（整函数）：仅当 live 恰好一个字段、值等于整句问句时才 overlay。

- 字段是 `clientNo` / `polNo` → F
- 字段是 `searchClientName`，问句是 2–4 汉字，不在产品/地址目录，且姓氏目录命中 → F
- 其余 inherit

不读 pack `role`。不解析「保单号」「的」「买了」。

### 期望

1A：2–4 字中文名可单独撑 F；杨杰与王坤林同侧=F；共展/豆芽仍 NF。
双闸：集 A 盘客/假姓名/目录产品不得回退；集 B 真名 / 合法单号 F 不得掉；姓名+产品不得用问句补姓名。
奥卡姆：候选必须比 role 的题型机短，且能解释为什么换到单号场景不必再写一套。
不是 oracle：混合包 41/47、341 准确率。

### 实际

混合包 47 条有期望：

| 列 | agree | 唯一 miss |
|---|---|---|
| current | 36 | I336 + HB002/003/005/006 + HB009–014 |
| wide | 27 | 假姓名/地名/业务词被抬 F |
| surname | 35 | 五条保单号被误杀 + 家办客户 |
| role | 41 | 仅 HB009–014 |
| live_identity | 41 | 仅 HB009–014 |

集 A：

| 列 | F/NF | 翻面 |
|---|---|---|
| current | 213/128 | — |
| wide | 238/103 | 抬 25，含共展/豆芽/昊轩 |
| surname | 210/131 | 抬王坤林+家办客户；砍 5 条保单号 |
| role | 215/126 | 抬王坤林+**红莲保单** |
| live_identity | 214/127 | **只抬王坤林** |

集 A 上 live_identity 的 57 次 overlay 拆开是：53 条整句单号本来就是 F，3 条整句真名本来就是 F（杨杰/郑鑫/匡西永），1 条 1A 要求的抬 F（王坤林）。同一函数确认单号和姓名，没有 `PERSON_THEN_POLICY`。

混合包 overlay：live_identity 15 次（12 条裸名 + HB015–017 整句单号）。HB018「找一下客户号…」值≠问句，inherit，当前已是 F。姓名+保单号 inherit，当前已是 F。姓名+产品 inherit NF。

昊轩：无姓，inherit，不代选 §4.3。

### 根因层

「更好」不是更高的 41/47。role 已经 41/47，却被用户否掉。更好的标准是：

1. 双闸过（集 A 只抬王坤林，不抬假姓名/盘客/目录产品/红莲保单）
2. 出口问的是 live 覆盖，不是题型
3. 同一句能覆盖姓名和单号，换问题不必加表
4. 补不了的（姓名+产品 live 丢姓名）老实 NF

这是 `_operator_justified` 那种确定性闸：目录当输入，代码选定出口，prompt 不得自行放行。不是第四套姓名 DSL。

### 已知限度（必须写明）

- 姓氏表仍是 1A 的目录先验，不是长期「是不是人名」检测器。新的「有姓假名」会走 F。
- 整句覆盖管不了「张忠波保单号」。本轮靠 inherit。次要词不否决主对象，是以后要搬的 **blocking 标签**，不是再写一条保单号正则。
- 姓名+产品六条仍是 019 的 parse 红灯。改判定补不了。

### 和 019 / 021 的边界

- 019：六条丢姓名。本 issue 再次确认候选没有用问句补姓名。不重开。
- 021：四口对照且禁止并进代码。本轮加的是更短候选，仍禁止并进。

### 不是什么

- 不是发版建议。
- 不是宣布 41/47 已达天花板。
- 不是把姓氏表升级成架构。

### 可证伪修复

若某口在值≠问句时仍靠题型抬 F（I248），或靠砍「保单号」过双闸（surname），或把 HB009–014 从问句补成 F，则不是 coverage-gate。验收命令同上，看 `set_a.flips.live_identity` 是否仍只有 I539，以及 `mixed.scores.live_identity.misses` 是否仍只有 HB009–014。

---

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 8eecb710b62b55a7
- pid: 95897

### Investigation

独立重跑脚本，SHA-256 仍是 `f180cb60bcbde3a978bbaa64e28971988676d4ea97194fd990d4be05bd72e835`。自己读了 `whole_query_cover`（L122–130）和 `exit_live_identity`（L293–314），没有抄 verifier 数字。

函数体只做这件事：先要 `len(fields)==1 and len(values)==1 and values[0]==query`，再按字段政策出口。`field in {clientNo, polNo}` → F；`field==searchClientName` 且整句 2–4 汉字、不在产品/地址目录、姓氏目录命中 → F；其余 `None`（inherit）。不读 `pack_role`，不解析「保单号 / 的 / 买了」。`pack_role` 只出现在装包、按角色报表、以及负对照 `wide`/`surname`/`role` 的早退里。

本机分数（与落盘一致，不是抄的）：

| 列 | 混合 agree/47 | 集 A F/NF | 集 A 翻面 |
|---|---|---|---|
| current | 36 | 213/128 | — |
| wide | 27 | 238/103 | 抬 25，含共展/豆芽/昊轩/红莲保单 |
| surname | 35 | 210/131 | 抬王坤林+家办客户；砍 5 条保单号 |
| role | 41 | 215/126 | 抬王坤林+红莲保单 |
| live_identity | 41 | 214/127 | **只抬 I539 王坤林** |

live_identity 混合 overlay 15：12 条裸名（I224/I310/I336/I539 + HB001–HB008）+ HB015–HB017 整句单号。HB018 `找一下客户号C000777123456` 值=`C000777123456` ≠ 问句，inherit，当前已是 F。I007/I103 姓名+保单号 inherit F。HB009–HB014 inherit NF。昊轩 I485 inherit NF，混合包 `expected=None`，没有代选 §4.3。

冻结痕迹核对（只读 `name_scenario_runs/`）：杨杰/王坤林/匡西永/张伟 live 都是 `searchClientName` = 整句；昊轩同样是整句但 `昊` 不在姓氏表。共展/豆芽 live 也是整句 `searchClientName`，因无姓而 inherit，不是 overlay NF。

额外对照，用来压「41/47 一样所以两口一样」：I248 不在混合包；surname 能把 I548 `家办客户`（冻结 live `fields=[]`）抬 F，live_identity 不能，因为没有整句覆盖。负对照在混合包里靠 `pack_role==undecided_given_name` 把昊轩停住，集 A 无该字段时 wide 仍抬 I485。候选两边都是 inherit，行为一致。

### Reasoning

同意：更好的标准不是再刷一个 41/47。role 已经 41/47，用户否的是形状。本口过双闸的方式是「只在 live 把整句收成一个身份时 overlay」，所以集 A 只抬王坤林，不抬盘客/假姓名/金凤/红莲保单，也不砍保单号。同一闸能确认整句单号，不必再写一套保单号正则——HB015–017 overlay、HB018 inherit，正是覆盖门，不是题型门。

必须收紧三句，防止 026 被卖成「姓名状态机已经退役 / 可以发版」：

1. **41/47 持平是包的伪影。** 两口混合 miss 都是 HB009–014。role 多出来的 `PERSON_THEN_POLICY` / 题型表在包内买不到新的 agree，只在包外买到 I248 泄漏。所以 41/47 不是候选胜利，只说明混合包对「值≠问句却抬 F」不敏感。
2. **这仍是 1A 的目录先验，不是「是不是人名」检测器。** `has_surname_shape` 还在。换一个整句 `searchClientName=张某某` 的假词，这口会 overlay F。假姓名闸仍 open（见 027 / 021 Consensus）。
3. **不是发版。** 章程红线：任何内存口径不得并进判定。张忠波保单号这类「次要词」靠 inherit，不是本口已经实现了 blocking 标签。019 的六条丢姓名，改判定补不了。

在上述限度内，本题成立：要对齐已拍的 1A，不需要再写一套姓名题型状态机。候选形状短于 role（22 对 28 行，且不依赖 `PERSON_THEN_POLICY` / pack role 分流），问的是 live 覆盖。

### Improvement Proposal

- **Target**: 继续把 `exit_live_identity` 只当内存对照列。禁止粘进 `draft/judge.py`。报表必须同时写 overlay/inherit，禁止只报 41/47。
- **Change**: 保持 `whole_query_cover` 合取（单字段 ∧ 值=整句）。姓氏表只作 1A 输入，不作题型路由。昊轩继续 inherit / abstain。
- **Verification**: 同脚本。验收：`set_a.flips.live_identity.lifted_to_f` 仅 I539；`dropped_to_nf` 为空；`mixed.scores.live_identity.misses` 仅 HB009–014；I485 `live_identity_mode=inherit`；I248 不在 live_identity overlay 集。

## Consensus
**Verdict**: real-problem

独立重跑同一脚本。47 条有期望：current 36、wide 27、surname 35、role 41、live_identity 41。集 A：current 213/128，wide 238/103，surname 210/131，role 215/126，live_identity 214/127。live_identity 只抬 I539 王坤林。混合 overlay 15 = 12 条整句真名 + HB015–017 整句单号。

接受 architect 三处收紧：

1. **41/47 持平是包的伪影。** role 多出来的题型机在包内买不到新 agree，只在包外买到 I248。
2. **这仍是 1A 的姓氏目录先验，不是「是不是人名」检测器。** 共展/豆芽 inherit NF 不能当假姓名闸已完成。
3. **不是发版。** 不得把 `exit_live_identity` 并进 `judge.py`。张忠波保单号靠 inherit，不是 blocking 标签已经落地。

补充：行数 22 对 28 只是形状更短的旁证。真正更可泛化的点是同一句问「live 是否把整句收成一个身份」，换到单号不必再写一套正则。I548 家办客户 live 为空，surname 按问句形抬 F，coverage-gate 不抬——这是覆盖门，不是又一张业务词表。姓名+产品六条仍归 019。昊轩 inherit，§4.3 未拍。

本 issue 在候选被并进判定、或报表只报 41/47、或把 inherit NF 写成「已会认假姓名」时保持 open。
