# Issue #007: 同一类「投保日 is_supported=false + 透明提示」，I046 打 NF、I161 打 F

**Class**: functionality
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output + code-analysis
**Layer**: Configuration（blocking 标签由模型自选，没有代码约束）
**Cases**: I046 去年+学业福（canvas 放在「如实拒绝当 F / 新更好」）；I161 林秀微去年+全家保（canvas 互有对错）

## Verifier Discovery

两条 live 对「去年」的处理相同：条件里都没有投保日，robot_text 都是「提示：投保日期暂不支持搜索，系统将按可支持字段搜索。」新 judge 一边把「去年」做成 blocking 核心（I046 → 整案 NF），一边做成 blocking=false 透明说明并写「不纳入可评价系统错误」（I161 → 整案 F）。

### 同 live

I046 query：`我想查询去年购买了平安学业福的客户名单。`

- conditions: `abbrname MATCH 平安学业福`
- robot: 投保险种简称为平安学业福的客户 + 投保日期暂不支持
- 旧 F / 新 NF

I161 query：`林秀微去年投保全家保的客户`

- conditions: `applicantname MATCH 林秀微` AND `abbrname MATCH 全家保`
- robot: 投保人…并且投保险种… + 投保日期暂不支持
- 旧 NF（旧把林秀微打成应走客户本人姓名，不在本 issue 范围）/ 新 F

### 新 judge expectation 对照

I046：

- blocking=true「按去年投保时间筛选客户」→ NF。actual_evidence 原文：「Catalog已确认保单投保日期字段当前is_supported=false，但该条件仍应被解析并明确处理」
- blocking=false「明确告知投保日期暂不支持搜索」→ F
- 整体 NF

I161：

- blocking=true 投保人 + 全家保 → F
- blocking=false「投保日期去年约束的透明说明」
- boundary.note 原文：「投保日期不可搜索属上游能力边界，不纳入可评价系统错误」
- 整体 F

同一字段 `policies_insure_date` / `is_supported=false`，同一句提示。

### 提示为什么允许两种拆法

`draft/judge.py` 同一段同时写：

- L1512：「is_supported=false … 分别评价核心交付与透明边界说明，不能用说明替代核心结果」
- L1522–1524：「安全拒绝和透明说明必须另建 blocking=false」；「被遗漏的 blocking 维度按实际未交付判 not_fulfilled」

「去年」算不算 blocking 核心，完全由模型当场选择。没有 schema / 代码闸。

### 协议

- §3.1 Authority 关闭：核心结果缺失判 NF；如实拒绝只能 non-blocking，不能替代核心交付。
- §4.1 / §5 / §7.1：如实拒绝本身不能变 F。这解释了盘客/活动族新 NF 为什么对。
- §6：整体 = 核心诉求聚合。哪一维是核心，协议没写死「去年」这一维。
- D5/D6 已点名：字段在清单但不支持时强判 NF 会漂；073 投保日期就是先例。

### 与 canvas 的差别

canvas 把 I046 算「新更好」、I161 算「互有对错」，等于默认「去年必须 blocking」。这是政策选择，不是协议必然。

本 issue 只主张：**同模式不得一个 NF 一个 F**。哪边对，是章程 §4 留给用户的划界：

- 若「去年」是整句唯一对象、或去掉后集合从「某类人」变成「所有人」→ 应统一 blocking NF（盘客族同逻辑）。
- 若主对象（学业福 / 林秀微+全家保）已交付，「去年」是不支持附加维 → 应统一 non-blocking，不得改整体 F/NF。

无论选哪边，I046 与 I161 必须同侧。现在不是。

### 未消元

- 未查本轮 Catalog Load 全文，只依据两条 Judge JSON 自己写的 is_supported=false。
- 未重跑。I161 旧 NF 另有「裸名应走 searchClientName」争议，不并入本根因。

---
## architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 5f7ddad9f3a27ddc
- pid: unknown

### Investigation
- 复核 trace：I046 `exps[按去年投保时间筛选客户] blocking=true → not_fulfilled`、`exps[明确告知暂不支持] blocking=false → fulfilled`，整体 NF；I161 `exps[投保日期去年约束的透明说明] blocking=false → fulfilled`，boundary.note「不纳入可评价系统错误」，整体 F。两条 live 同为「policies_insure_date is_supported=false + robot 同一句『投保日期暂不支持搜索』提示」，条件里都没有投保日。逐字对上。
- 核对 `draft/judge.py`：L1512「is_supported=false…分别评价核心交付与透明边界说明，不能用说明替代核心结果」；L1522「安全拒绝和透明说明必须另建 blocking=false 的 expectation」；L1524「被遗漏的 blocking 维度按实际未交付判 not_fulfilled」。三句同时在场，但「某不支持维度算 blocking 核心还是透明说明」没有任何判定规则。
- 核对协议：fulfilled §3.1「如实拒绝只能作为独立 non-blocking 透明说明，不能替代核心交付」；§6 整体=核心诉求聚合、职责内必须有 blocking 必办项。但协议没有写死「去年/投保日」这一维属于核心还是附加。§8 D5/D6 明确点名「字段在清单但实际不支持」会判漂，073 投保日就是先例。
- 排除「两条本就不同」的可能：I046 与 I161 的日期维处理在 live 层完全同构（同字段、同 is_supported=false、同提示、同样未交付日期条件）。唯一差异是 I161 多交付了一个投保人姓名。这是「多交付了一维」，不是「日期维本身语义不同」，不构成 blocking/非 blocking 翻转的依据。

### Reasoning
同一轮新 judge 对同一模式给出相反 blocking 标签：I046 把「去年」做成 blocking 核心 → 整案 NF；I161 把同型「去年」做成 blocking=false 透明说明 → 整案 F。我尝试为这个差异找原则依据：

- 若以「去掉该维后集合是否从『某类人』变『所有人』」为尺：I046 去掉「去年」后仍是「购买平安学业福的客户」（某类人），I161 去掉后是「林秀微投保全家保的客户」（也是某类人）。两案同侧，都应 non-blocking。按此尺，I046 的 NF 反而是错的。
- 若以「时间是主谓词的核心限定」为尺：两案的「去年」都同等核心，都应 blocking，则 I161 的 F 是错的。

无论采用哪把尺，I046 与 I161 都必须同侧；现实是一 NF 一 F。所以这不是「两条 case 语义本就该不同」，而是 blocking 标签由模型当场自选、无 schema/代码闸导致的口径漂移。这正是 §3.1「如实拒绝只能 non-blocking、不能替代核心交付」与 L1512「说明不能替代核心结果」之间的张力，在「该维算不算核心」上没有裁决规则时被模型各咬一句。verifier 的最低主张「同模式不得一个 NF 一个 F」成立。哪边对（去年 blocking 与否）确属章程 §4 的用户划界，我不越权裁定；但一致性本身是硬要求。不是 reasonable-design：同轮同模式相反判定不是约束下的取舍，是不可复现的漂移。

一点补强（verifier 未强调）：旧 judge 在 I046 把日期当 non-blocking 判 F，说明「日期=非阻塞」其实是更早的稳定口径；新 judge 的 I046 NF 是相对旧口径与自身 I161 的双重漂移。这进一步说明问题在「新 judge 无闸」，而非该模式天然有歧义。

### Improvement Proposal
（permission mode = review，章程红线禁改 judge；建议交由有写权限角色在用户裁定后实施）
- **Target**: `impl/projects/client_search/draft/judge.py` L1512 与 L1522–1524 之间，补一条确定性分类规则；理想做法是代码/schema 固定打标，而非再加一句 prompt。
- **Change**: 对「字段 is_supported=false 且 actual 已给标准透明提示」的维度，统一分类，禁止同轮两种拆法。两方向任选其一但必须全局一致：
  - 方向 A（全 blocking）：不支持字段被遗漏的核心维一律 blocking → NF（会同时把「张三的学业福，去年买的」这类正常混合问整案打 NF，召回塌，慎用）；
  - 方向 B（全 non-blocking）：主对象已交付后，不支持的附加维固定 blocking=false 透明说明，不改整体 F/NF。
  推荐按 verifier/ canvas 的划界写成确定性规则：仅当该维是整句唯一对象、或去掉后目标集合从「某类人」变「所有人」时才 blocking（盘客/活动族由此保住 NF）；否则 non-blocking。关键是 blocking 标签由规则派生，不由模型自选。
- **Verification**: 同 live 重跑 I046、I161、盘客族（I069/I088/I318…）与混合对照「张三的学业福，去年买的」；断言 I046 与 I161 落到同一侧，且盘客族 NF 净胜不回退。

---
## Consensus
**Verdict**: real-problem
**Summary**: 同一「投保日 is_supported=false + 同一句透明提示」，I046 blocking NF、I161 non-blocking F。一致性是硬要求。哪边对是用户划界：若用「去掉该维后仍是某类人」这把尺，两案都应 non-blocking，则 canvas 把 I046 算「新更好」反而是错的。盘客/活动族（整句唯一对象缺失）必须继续 NF，不能和这条一起放。

