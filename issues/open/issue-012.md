# Issue #012: 姓名 / blocking / 空间三道闸都写在提示里，模型当规则机跑，改句子不能泛化

**Class**: functionality
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis + test-output
**Layer**: Architecture（判定程序的宿主放错了：该进代码的过程留在 L1479–1525 字符串）
**Cases**: 006–009 已确认的四族 + 011 同形态左右互搏；不是新的一条错判

## Verifier Discovery

006–009 各钉了一处提示内部打架。011 证明同一形态在新 judge 里已经自己打自己。把这些当成四条互不相关的文案缺陷去「再补一句」，正好踩泛化 skill 的 a（过度规则化）和 c（只改结果不改源头）。本 issue 钉源头：这三道必须稳定的闸，目前全部靠模型读一段互相否决的中文。

### 代码里没有这三道闸

`impl/projects/client_search/draft/judge.py`：

- L1479–1525「client_search 直接证据」是姓名证据、blocking、拆 expectation、空条件、is_supported=false 的**全部规范条文**。
- `ClientSearchJudge`（L1747 起）只 `build_context` / `judge_execution` / `normalize_result` / `reconcile_result`，不分类 token，不裁定 blocking。
- 存在 `_unsupported_boundary_evidence`（约 L454）等**材料**函数，能把 `is_supported=false` 送进 context；没有函数规定「去年」此条 blocking 还是 non-blocking，也没有函数在拆 expectation 前检查空间里有没有该维。

原文关键句（同一段）：

- L1481：「每个可独立判断的请求维度拆一条 expectation」
- L1497：「字段定义只证明该字段声明的语义」
- L1504–1508：裸词要独立人名证据，括号里又写「或该形态就是姓名检索」
- L1512：「is_supported=false … 分别评价核心交付与透明边界说明，不能用说明替代核心结果。」
- L1513：「以下内容永远不能单独成为 blocking 核心交付：不错误映射、不编造条件、拒绝越界请求、告知当前限制、未识别到条件。」
- L1514–1519：明确业务对象但无条件 → Authority 关闭时「按当前交付判 not_fulfilled」
- L1522：「安全拒绝和透明说明必须另建 blocking=false 的 expectation。」
- L1523–1524：「若 actual 只交付请求的一部分，必须按可独立判断的请求维度拆分 expectation」

这不是「缺一条规则」。这是把规则机交给生成模型：每次检索到的 catalog 句子不同，咬到的半句就不同。011 的杨杰 vs 王坤林、007 的 I046 vs I161，是同一机制的两个表面。

### 已经发生的「只改句子」失败模式

同一段提示已经同时要求：

| 条款 | 模型可推出 |
|---|---|
| 形态就是姓名检索 | 杨杰/郑鑫/匡西永 F |
| 字段定义 / live 路径不够 | 昊轩/王坤林 NF |
| 拆每个可独立维 + 说明不能替代核心 | I046「去年」blocking NF |
| 透明说明 blocking=false | I161「去年」non-blocking，整案 F |
| 每个可独立维都拆 | I263 弟弟年龄变成 blocking |
| 明确对象+空条件=NF | I034/I616 盖住格式外拒识 |

再往这段里加方案 A–D 的句子，只是再增加可咬半句，不消除自选。泛化 skill：a 过度规则化，c 只改结果不改源头。010 说明评价函数还在奖励这种改法（341 badcase 更好看）。

### 协议

- fulfilled §3.1 Authority 关闭：核心缺失 → NF；如实拒绝只能 non-blocking，不能替代核心。这是**程序**，不该每案由模型重读一遍决定「去年」算不算核心。
- material-positioning 不变量 2：inlive_boundary 只升级空间（有什么），不升级选择（本次选哪个）。空间闸（008）必须在拆 expectation 之前用资料判定「有没有这维」，不能让模型先拆出「弟弟比本人小」再找字段。
- 不变量 1：current_behavior 不能冒充正式规则。把「本轮 Search 碰巧 Load 到哪条 enhanced_rule」当成杨杰可 F、王坤林不可 F 的理由，就是用检索运气当规则。

### 和 010、011、006–009 的边界

- 006–009：各是一条表面矛盾。已 Consensus，不重开。
- 011：姓名这一个程序的内部漂移，是 012 的主症状之一，不是 012 的全部。
- 010：评价函数缺头部闸，解释「为什么这种改法会一直被当成进步」。012 解释「改哪里才能真的泛化」。
- 012 不是把四条 issue 卷成一条。删掉 012，006–009/011 仍各是可修的表面；只修表面、不搬宿主，下一轮换词还会漂。

### 可证伪修复（搬进代码的三个过程）

禁止再往 L1479–1525 加例外句。把三道闸写成确定性过程（可用 catalog 作输入，不可用模型选出口）：

1. **姓名程序**（011 的 1–3 步）：目录先于形态；2–4 汉字走同一出口；拉丁/单字/称谓不得仅凭形态撑 F。
2. **blocking 程序**（007 族）：唯一核心对象缺失 → blocking NF；主对象已交付后的不支持附加维 → 固定 non-blocking。划界政策仍是章程 §4，但划界结果不得由模型逐案选。
3. **空间闸**（008/009 族）：没 Load 到能表达该维的字段/操作符/格式，不得把该维做成 blocking expectation。

验收不点名 341 ID：盘客仍 NF，共展仍 NF，目录产品不走姓名；杨杰与王坤林同侧；I046 与 I161 对「去年」同侧；弟弟年龄不得仅因常识拆成 blocking。具体「去年算不算核心」「2–4 字能否单独撑 F」仍升级用户。

### 未消元

- 未实现这三道闸，也未做 ablation（搬进代码 vs 再写三句 prompt）。本 issue 只主张宿主在错的一层。
- `_unsupported_boundary_evidence` 是否已经足够支撑 blocking 程序的输入，peer 应自己读，不默认「材料函数=判定函数」。
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 37225eeb6839ec61
- pid: 45981

### Investigation

读了 `impl/projects/client_search/draft/judge.py` 的宿主，不只是 verifier 摘的句子。

`L1477–1526`「## client_search 直接证据」是姓名证据、blocking、拆 expectation、空条件、`is_supported=false` 的全部规范条文。同一段里同时存在：

- L1481 / L1523：每个可独立判断的请求维度拆一条 expectation
- L1497：字段定义只证明字段语义
- L1504–1508：裸词要独立人名证据，括号里又有「或该形态就是姓名检索」
- L1512：说明不能替代核心结果
- L1513：拒绝/告知限制/未识别永远不能单独成为 blocking 核心
- L1514–1519：明确对象 + 无条件 → Authority 关闭时按当前交付 NF
- L1522：安全拒绝和透明说明必须 `blocking=false`

`ClientSearchJudge`（L1747–1782）只有 `build_context` / `judge_execution` / `normalize_result` / `reconcile_result`。reconcile 里现有的确定性东西是：

- `apply_condition_comparison`（L866）：只回填 wrong/missing/extra，不裁定 F/NF，不裁定 blocking
- `_apply_operator_capability_check`（L985 起）：操作符能力闸；`project.yaml` 里 Authority 关闭时直接 return
- `fail_closed_authority_off_judge_result`（`judge_execution.py` L95）：Authority 关闭时把 NE 收成 NF，不分类 token，不划 blocking

`_unsupported_boundary_evidence`（L454）+ `_enrich_unsupported_boundary_evidence`（L627）是材料函数：抽出「暂不支持」通知、请求重叠、`is_supported=false` 字段，送进 context。它们 **不** 规定「去年」此条 blocking 还是 non-blocking。I161 的 actual_evidence 引用了这份材料并做成 non-blocking 说明；I046 有同样的「投保日期暂不支持搜索」通知，却把「按去年投保时间筛选」做成 blocking=True → 整案 NF。材料 ≠ 判定。

对照新表（不重开 007/008，只核 012 的「同一宿主」主张）：

- I046 `我想查询去年购买了平安学业福的客户名单。` → NF；expectation「按去年投保时间筛选客户」blocking=True
- I161 `林秀微去年投保全家保的客户` → F；「投保日期去年约束的透明说明」blocking=False，核心姓名+险种 F
- I263 `小雨弟弟` → NF；「弟弟年龄小于客户本人」blocking=True（常识维，空间里没有相对年龄字段）
- I034 / I616 空条件 +「明确对象」→ NF（009 族，不重开）

代码里已经有先例：`_operator_justified`（L906–911）写明「确定性 gate，prompt 不得自行放行其他例外」。姓名 / blocking / 空间三道闸还停在字符串里。

未实现这三道闸，也未做 ablation。本轮章程 §6 本来就不实现。

### Reasoning

012 不是把 006–009/011 卷成一条统计。删掉 012，那五条表面各自仍可修；只修表面、不搬宿主，下一轮换词还会漂。这是架构层的真问题。

根因是：必须稳定的 **出口选择** 被交给生成模型去读一段互相否决的中文。每次 catalog 检索到的句子不同，咬到的半句就不同。011 的杨杰 vs 王坤林、007 的 I046 vs I161，是同一机制的两个表面，不是两个无关的文案 bug。

协议已经把这三件事写成程序，不是写成「请模型理解」：

- fulfilled §3.1 Authority 关闭：核心缺失 → NF；如实拒绝只能 non-blocking，不能替代核心。
- material-positioning 不变量 2：`inlive_boundary` 只升级空间（有什么），不升级选择（本次选哪个）。空间闸必须在拆 expectation 之前用已 Load 资料判定「有没有这维」。
- 不变量 1：current_behavior 不能冒充正式规则。把「本轮碰巧 Load 到哪条 enhanced_rule」当成杨杰可 F、王坤林不可 F 的理由，就是用检索运气当规则。

010 解释了为什么「再写三句」会被 341 badcase 奖励；012 解释改哪里才能真的泛化。泛化 skill：a 过度规则化、c 只改结果不改源头。往 L1479–1525 加方案 A–D 的句子，只增加可咬半句。

需要收的口，避免 012 滑成「把整个 judge 收成规则机」：

1. 不是消灭 LLM。LLM 仍可写 evidence、对照 actual vs 已定 expectation。搬进代码的是 **出口和 blocking 标签**，不是整篇推理。
2. 实现风格应对齐已有的 `_operator_justified` / `fail_closed`：catalog 作输入，代码选定出口，prompt 不得自行放行。不要另起一套规则 DSL。
3. 「去年算不算核心」「2–4 字能否单独撑 F」仍是章程 §4，不是 012 能拍的。012 只要求：划界结果不得由模型逐案选。
4. `_unsupported_boundary_evidence` 已经够给 blocking 程序当输入（I161 已经在用），不够当判定函数。不要把它误升成闸。

### Improvement Proposal

- **Target**: `impl/projects/client_search/draft/judge.py` 的 context 组装 + `ClientSearchJudge.reconcile_result`（及必要时 `judge_execution.py` 的 fail-closed 邻接）。禁止再往 L1477–1526 加例外句。本轮不实现（章程 §6）。
- **Change**: 把三道闸写成确定性过程，可用 catalog 作输入，不可用模型选出口。
  1. **姓名程序**（011 的 1–3 步）：目录/枚举/地址/盘客先于形态；剩余 2–4 汉字走同一出口；拉丁/单字/称谓不得仅凭形态撑 F。出口值按章程 §4.1 一次性写入代码。
  2. **blocking 程序**（007 族）：唯一核心对象缺失 → blocking NF；主对象已交付后的不支持附加维 → 固定 non-blocking。`is_supported=false` + 透明通知走材料函数的输出，由代码贴 `blocking=false`，不再让模型在 I046/I161 之间自选。「去年算不算核心对象」按章程 §4.2 一次性写入，不逐案重读 L1512 vs L1522。
  3. **空间闸**（008/009 族）：在拆 expectation **之前** 看已 Load 字段/操作符/格式。没 Load 到能表达该维的空间，不得把该维做成 blocking expectation。I263「弟弟比本人小」若空间里没有相对年龄字段，不能仅因常识拆成 blocking。
  4. LLM 只消费程序出口：例如 context 里放 `name_program_exit` / `blocking_assignment` / `unsplittable_dimensions`。reconcile 后若模型改写了这些标签，代码改回。对齐 `_operator_justified` 的「prompt 不得自行放行」。
- **Verification**（验收不点名 341 ID 当规格；下列 ID 只作回归探针）：
  - 盘客/活动仍 NF；共展仍 NF；目录产品不走姓名。
  - 杨杰与王坤林同侧（011）。
  - I046 与 I161 对「去年」同侧：要么都把已交付的姓名/险种当核心、去年当 non-blocking 说明，要么都把去年当核心——由用户选一次，代码固定。
  - 弟弟年龄不得仅因常识拆成 blocking。
  - 回归时禁止只看 341 准确率（见 010）；禁止再加 L1504–1524 的对照句子当修复。
- **Why I Cannot Apply It**: architect 只读。blocking / 姓名出口的政策值属章程 §4。本轮只立根因，不改 draft 代码。

---
## Consensus
**Verdict**: real-problem

姓名 / blocking / 空间三道闸的出口选择现在都在 L1479–1525 字符串里，由模型逐案选半句。这是 006–009 和 011 的共同宿主，不是又一条表面错判。

接受 architect 的收口，避免 012 滑成「把整个 judge 收成规则机」：

1. 不是消灭 LLM。LLM 仍写 evidence、对照 actual。搬进代码的是 **出口和 blocking 标签**。
2. 实现风格对齐已有 `_operator_justified` / fail-closed：catalog 作输入，代码选定出口，prompt 不得自行放行。不要另起规则 DSL，也不要再往这段提示加 A–D 句子。
3. `_unsupported_boundary_evidence` 是材料，不是判定函数；I161 已经在用它，但 blocking 标签仍由模型自选。
4. 「去年算不算核心」「2–4 字能否单独撑 F」仍归章程 §4；012 只要求划界结果不得由模型逐案选。

010 解释为什么「再写三句」会被 341 奖励；012 解释改哪一层才能泛化。本轮不改 draft 代码。
