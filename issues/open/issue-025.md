# Issue #025: `exit_role` 是姓名题型状态机，换题型就不够用；用户已否这套形状

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: In-memory judge overlay（不是生产代码；负对照）
**Cases**: I248 红莲保单；I007/I103 保单号；对照 live_identity 不用这些规则也到同一混合分

## Verifier Discovery

用户原话：按场景角色分流太规则化，姓名只是要处理的问题之一。上一轮 `exit_role` 正是这套形状：百家姓 + 复姓表 + `PERSON_THEN_POLICY` + 业务词表 + 停住表。混合包 41/47 好看，不能证明可泛化。

### 触发输入

```bash
python3 issues/trace/simulate_1a_coverage_program.py
```

落盘 `issues/trace/simulate_1a_coverage_program.json`
SHA-256 `f180cb60bcbde3a978bbaa64e28971988676d4ea97194fd990d4be05bd72e835`

`exit_role` 仍在脚本里，只作负对照。它主动 overlay 的集 A 十条包括：

| ID | query | live 值 | role | 说明 |
|---|---|---|---|---|
| I248 | 红莲保单 | `红莲` | overlay F | 问句长得像四字名，值不等于问句 |
| I007 等 | 张忠波保单号 | `张忠波` | overlay F | `PERSON_THEN_POLICY` 正则 |
| I103 | 高吉禄的保单号 | `高吉禄` | inherit F | `{2,4}` 贪心吃「的」，主动路没打上 |
| I344 | 查金风 | `金风` | overlay NF | 靠「问句里有目录产品」 |

同一脚本里的 `exit_live_identity` 不读这些正则，也不读混合包 `role` 字段。混合包同样 41/47，集 A 却不抬 I248。

### 期望

012 Consensus：搬进代码的是出口和 blocking 标签，对齐 `_operator_justified`；不要另起规则 DSL。
泛化 skill：禁止为少数 case 写成只适配这些 case 的规则机。
用户本轮：姓名只是问题之一，按题型分流没有泛化性。

### 实际

`exit_role` 的架构问题不是「41/47 不够高」。问题是它问的是「这句像不像某一种姓名题」，不是「live 交没交用户要的身份」。

I248 是反例：live 交的是 `searchClientName=红莲`，问句是「红莲保单」。role 看问句是 2–4 汉字且「红」在姓氏表，就抬 F。这是题型匹配，不是证据覆盖。

I103 是另一面：为了处理「的保单号」写了正则，正则自己把自己咬死，只好 inherit。规则机越长，越要靠继承补洞。

### 根因层

把「姓名场景」理解成 12 个 pack role（true_bare_name / name_plus_policy / …）再为每个 role 写出口，这是用题型当架构。下一题若是「去年」「称谓」「姓名+地址」，还得再加表。012 已经说不要这样。

可留下的不变量不是这些表：

1. 只认 live 交出来的事实
2. 证据角色（人/物/号），不是题型
3. 次要词不能否决已交对的主对象——这是标签，不是「保单号」正则
4. 政策未拍则 abstain

### 和 021 / 012 的边界

- 021 已 Consensus：role 不得并进 `judge.py`。本 issue 不重开那个结论，只补用户否掉之后的形状证据。
- 012 已 Consensus：宿主在提示里。本 issue 不重开，只说明「再做一套姓名 DSL」同样违 012。

### 不是什么

- 不是说 41/47 作废。分可以一样，形状不能一样。
- 不是要删姓氏目录。目录可以当 1A 的输入，不能当题型路由器。
- 不是本轮改 `judge.py`。

### 可证伪修复

任一新出口若仍依赖 `PERSON_THEN_POLICY`、混合包 `role` 分流、或「问句长得像四字名」即可抬 F，则未修。验收：I248 在值≠问句时不得因题型被抬 F；I103 不得靠「的保单号」正则才过。

---

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 8eecb710b62b55a7
- pid: 95897

### Investigation

独立重跑 `python3 issues/trace/simulate_1a_coverage_program.py`。落盘仍是
`issues/trace/simulate_1a_coverage_program.json`，SHA-256
`f180cb60bcbde3a978bbaa64e28971988676d4ea97194fd990d4be05bd72e835`，与 issue 所引一致。未改脚本、未重跑 48 次 LLM。

重读 `exit_role`（`simulate_1a_coverage_program.py` L263–290）、`PERSON_THEN_POLICY`（L30）、`exit_live_identity`（L293–314）、`whole_query_cover`（L122–130）。负对照 `wide`/`surname`/`role` 都读 `pack_role == "undecided_given_name"` 作出口早退；`exit_live_identity` 函数体不读 `pack_role`，也不引用 `PERSON_THEN_POLICY`。

本机核对 I248 / I103 的真实代码路径，而不是只看 verifier 的叙述：

- 集 A I248：`query=红莲保单`，`fields=[searchClientName]`，`values=[红莲]`，current=`not_fulfilled`，role overlay=`fulfilled`（唯一和王坤林一起被 role 抬 F 的集 A 翻面）。I248 **不在**混合包 48 条里，所以 41/47 看不见这口泄漏。
- `PERSON_THEN_POLICY.fullmatch("红莲保单")` 捕获的是 `红莲`，不是整句。`保单号?` 使「号」可空，于是「X保单」先走上 L274–282：姓氏形 + 字段是 `searchClientName` + `红莲 in values` → 直接 F。BARE_NAME 四字名那条（L286–289）对 I248 **到不了**。verifier 原文「问句长得像四字名就抬 F」说的是症状，不是这条的实际分支。
- I103：`fullmatch("高吉禄的保单号")` 捕获 `高吉禄的`（`{2,4}` 先吃 4 字，把「的」吞进人名组）。`高吉禄的` 不在 values=`[高吉禄]`，role 主动路返回 `None`，混合包上是 inherit F。和 021 Consensus 已记的贪心自咬同一条，本轮只是形状证据，不重开 021。
- 对照：同一落盘里 live_identity 的集 A overlay 57 次拆开是 32 条整句 `clientNo` + 21 条整句 `polNo` + 3 条整句真名（杨杰/郑鑫/匡西永，本来就是 F）+ 1 次抬 F（王坤林）。I248 不在其中。

### Reasoning

同意本题的架构判断，收紧根因。

`exit_role` 问的是「这句像不像某一种姓名题」，不是「live 有没有把用户要的身份整句交出来」。I248 是可复现的反例：值 `红莲` ≠ 问句 `红莲保单`，却因为 `PERSON_THEN_POLICY` 把问句拆成「人名 + 保单」就抬 F。这正好是用户否掉的形状——百家姓 + 保单号正则 + 题型分流。012 已 Consensus：不要另起规则 DSL；021 已 Consensus：role 不得并进 `judge.py`。本 issue 不重开那两句，只补用户否掉之后还缺的形状钉：混合包 41/47 不能给这台状态机背书，因为它把 I248 漏在包外。

不接受两个过度引申：

1. 不是要删姓氏目录。1A 政策本身就要「2–4 字中文名」，目录可以当输入。禁的是用目录/正则/pack `role` 当题型路由器。
2. 不是本轮改 `judge.py`，也不是把「次要词不否决主对象」偷做成又一条 `X保单` 正则。张忠波保单号当前已是 inherit F；I248 当前是 NF。后者就算以后要谈 blocking 标签，也不能用 `保单号?` 这种题型机先抬上去。

可证伪条件成立：任一新出口若仍依赖 `PERSON_THEN_POLICY`、混合包 `role` 分流、或「值≠问句但问句像姓名题」即可抬 F，则未离开 025。

### Improvement Proposal

- **Target**: 只留在 `issues/trace/simulate_1a_coverage_program.py` 的负对照列；不要把 `exit_role`（L263–290）或 `PERSON_THEN_POLICY`（L30）并进 `impl/projects/client_search/draft/judge.py`。
- **Change**: 后续候选的 overlay 条件必须先过 `whole_query_cover`（单字段且 `value == query`）。禁止再读 `row["pack_role"]` 做出口。I248 在 `values=[红莲]` 且 query=`红莲保单` 时必须 inherit / 不得 overlay F。I103 不得靠「的保单号」正则才过。
- **Verification**: `python3 issues/trace/simulate_1a_coverage_program.py`，检查 `set_a.flips.role.lifted_to_f` 仍含 I248（负对照还在）、`set_a.flips.live_identity.lifted_to_f` 仍只有 I539。

## Consensus
**Verdict**: real-problem

双方独立重跑 `python3 issues/trace/simulate_1a_coverage_program.py`。落盘 SHA-256 仍是 `f180cb60bcbde3a978bbaa64e28971988676d4ea97194fd990d4be05bd72e835`（architect 21:18 重跑后分数未变）。闸：spawn-id `8eecb710b62b55a7`，exit 0，`isolation_valid` + `scope_valid`。wrapper pid 95645 / 回应写 95897，只要求 spawn-id 对齐。

接受 architect 收紧：I248 泄漏成立，但实际分支是 `PERSON_THEN_POLICY`（`保单号?` 使「号」可空）先匹配「红莲+保单」，不是原文写的「问句长得像四字名」那条 `BARE_NAME`。I248 不在混合包，所以 41/47 看不见这口。I103 贪心自咬与 021 同一条，不重开。

`exit_role` 继续只当负对照，不并进 `judge.py`，也不再打补丁把它修成第二套状态机。新出口必须先过 `whole_query_cover`（单字段且值=整句），不得读 pack `role`。

本 issue 在新出口仍靠 `PERSON_THEN_POLICY` / pack `role` 分流 / 「值≠问句但问句像姓名题」抬 F 时保持 open。
