# Issue #008: 拆 expectation 没有空间闸——把常识维做成 blocking（I263）；I638 弱相关

**Class**: boundary
**Severity**: medium
**Status**: verifier-raised
**Evidence**: test-output + code-analysis
**Layer**: Configuration / Interaction
**Cases**: I263 小雨弟弟（canvas 过严，主证）；I638 C00OO731392（canvas 过严，弱）

## Verifier Discovery

### I263（主）

query `小雨弟弟`。同 live：

```
searchClientName MATCH 小雨
familyInfo.familyrelation MATCH 兄弟姐妹
familyInfo.familyclientsex MATCH 男
robot: 客户姓名为小雨并且有兄弟姐妹并且兄弟姐妹性别为男的客户
```

旧 F：弟弟的可表达代理 = 关系 + 性别。

新 NF：第三条 blocking「弟弟年龄小于客户本人」未交付。reasoning：「弟弟还包含年龄小于客户本人的关系语义；当前条件未表达该年龄约束，因此核心筛选范围偏宽。」

新 judge 自己写的 expected.conditions 只有姓名+兄弟姐妹+男，**没有**相对年龄条件；intent_summary 却写成「有年龄小于客户本人的男性兄弟姐妹」。缺的年龄来自模型对「弟弟」的常识扩维，不是 actual，也不是已 Load 的相对比较能力。

这违反同一份提示 L1485：「wrong/missing/extra 必须来自当前 actual，不能来自猜测」。

空间侧：`project.yaml` 有 `familyInfo.familyclientage` / `familyInfo.familyclientbirthday`（家庭成员**绝对**年龄/生日），没有「比客户本人小」的相对比较字段或操作符。canvas 写「当前空间没有相对年龄字段」方向对，但说成「没有年龄字段」不准确——有绝对年龄，缺的是相对比较。

协议：positioning 不变量 2 只升级空间、不升级这次选哪个。把空间里表达不了的常识维做成 blocking，等于升级了「这次必须选出相对年龄」。

### I638（弱，不要和 I263 绑死成同一强度）

query `C00OO731392`。同 live：`query_logic=OR`，`clientNo MATCH` + `polNo MATCH` 同值。robot：「暂时没判读出这组数据代表什么，已帮您在手机号、客户号、保单号中一起查找匹配的客户」。

新：clientNo 那条 F；另造 blocking「避免增加未表达的保单号筛选」→ NF。reasoning：「额外加入 polNo，扩大了未表达的检索范围」。

提示 L1484 写的是「无依据的**额外收窄**」判 NF。OR 是扩大。模型用收窄条款打扩大。

旧 F：C 前缀通常不进 polNo 格式空间，多一个死分支几乎不改结果集。历史字段口径（retry-report）：`standard_format` = 「P或A开头后跟15至17位数字或字母，兼容历史14位」。`C00OO731392` 不是该格式。

弱在哪里：fulfilled §4.2 的「加多条件」确实可以覆盖 extra 字段。若下游 polNo 真吃 C 前缀，OR 就是真扩大。本条强度低于 I263，只证明「意图拆解会多造一条 blocking」。

### 提示

L1479–1481：「每个可独立判断的请求维度拆一条 expectation」。没有先问：当前 inlive 空间能否表达这一维。

### 未消元

- 未在本轮 Catalog 实查 familyclientage 的 operators 是否能做「小于客户本人」。
- I638 未验证下游是否真的丢弃格式外 polNo。

---
## architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 5f7ddad9f3a27ddc
- pid: unknown

### Investigation
- 复核 trace I263，并直读原始 `context_store/client_search/client_search:I263:1786695659788/judge-2026-08-14T08:23:49Z-d4fd7036-f5b.json` 的 `response.content`：确实存在 `expectation_id="弟弟年龄小于客户本人"`、`blocking=true`、missing `error_type="missing_relative_age_constraint"`；且同文件 `expected.conditions` 只有 `searchClientName 小雨` + `familyrelation 兄弟姐妹(CONTAINS)` + `familyclientsex 男` 三条，**没有**任何相对年龄条件，而 `intent_summary` 却写「有年龄小于客户本人的男性兄弟姐妹，即弟弟」。verifier「missing 来自常识扩维、不是 expected/actual/已 Load 能力」逐字成立。
- 核对 `draft/judge.py`：L1481「每个可独立判断的请求维度拆一条 expectation」未前置「空间能否表达」闸门；L1485「wrong/missing/extra 必须来自当前 actual，不能来自猜测、历史 verdict 或归因信息」。I263 的 missing 相对年龄显然不来自 actual，违反自身条款。
- 消元 verifier「未消元#1」（空间是否有相对年龄）：`project.yaml` 只声明 `familyInfo.familyclientbirthday`（operators GTE/LTE/RANGE，均为**绝对**生日界）与 `familyInfo.familyclientage`（`equivalent_field: familyclientbirthday`，绝对年龄→生日换算）；全文件无任何相对比较字段/操作符，`capability_manifest.py`/project.yaml 也搜不到「小于客户本人/相对年龄/比客户」类语义。空间有**绝对**年龄，缺的是「比客户本人小」的相对比较。verifier 对 canvas「没有年龄字段」的更正准确。
- I638：核对 trace，`query_logic=OR`，clientNo+polNo 同值；新 judge 把它归为 `extra[未表达字段扩展]`，reasoning 用「扩大了未表达的检索范围」。L1484 的判 NF 条款字面是「条件缺失、错误映射、无依据的额外**收窄**」——OR 是扩大，用收窄条款套扩大，属误引。

### Reasoning
I263（主证）成立：新 judge 把一个**空间里表达不了的常识维**（相对年龄）做成 blocking 并判 NF。三重证据：(a) actual 三条条件全对，且就是旧 judge 依据增强规则「姓名+男性兄弟姐妹」对「弟弟」的标准代理；(b) 新 judge 自己的 expected.conditions 也没放相对年龄——它惩罚的是一个它自己都没要求进 expected 的维度；(c) 空间只有绝对年龄，无法表达「小于本人」。这违反同份提示 L1485「missing 必须来自当前 actual，不能来自猜测」，也违反 positioning 不变量2 的精神（inlive_boundary 只升级空间、不升级「这次必须选出哪个」——把不可表达维做成 blocking 等于升级了选择）。根因「意图拆解无『空间里有没有这一维』闸门」站得住。

I638（弱）按 verifier 的分量处理：它只证明「意图拆解会多造一条 blocking」，且新 judge 用「收窄」条款套「扩大」是误引；但 fulfilled §4.2「加多条件」本身可覆盖 extra 字段，若下游 polNo 真吃 C 前缀则 OR 是真扩大，故该条 NF 并非无据。我认可 verifier「不与 I263 绑死成同一强度」的克制，不抬升 I638 强度。

不是 reasonable-design：I263 的 missing 不来自 actual/空间，是模型自造维度过拆解；这也不是目标约束下的有意取舍。主证 I263 单独足以支撑本根因。

### Improvement Proposal
（permission mode = review，章程红线禁改 judge；建议交由有写权限角色实施）
- **Target**: `impl/projects/client_search/draft/judge.py` §意图拆解 L1479–1482（加空间闸）；§逐项核对 L1483–1485（blocking 资格判定）。
- **Change**: 拆 expectation 前先过空间闸：仅当某维已被 actual/已 Load 字段/操作符/格式空间覆盖（即空间能表达该维），才允许把该维做成 blocking。对「空间里根本没有的常识扩维」（如相对年龄、称谓别称）不得做成 blocking，至多 non-blocking 说明。同时把「missing/extra 必须来自 actual 或已 Load 空间」作为 blocking 资格硬条件。注意闸门只挡「空间没有的常识维」，不得赦免「已登记字段本可表达却漏给」（少儿万能险丢『少儿』仍须 NF），与 fulfilled §4.2 一致。对 I638 类：OR 扩大不套用「收窄」条款；extra 是否 NF 依 §4.2 及下游是否真命中而定，不默认 blocking。
- **Verification**: 同 live 重跑 I263（期望不再因相对年龄 NF）、I638；对照「少儿万能险」「18岁的孩子」确认真漏条件仍被抓出（空间闸不误放已登记字段的缺失）。

---
## Consensus
**Verdict**: real-problem
**Summary**: I263 成立：关系+性别已交付，「弟弟=年龄小于本人」是空间里没有的相对比较，被做成 blocking。新 judge 自己的 expected.conditions 也没放相对年龄。I638 保持弱：OR 套「收窄」条款是误引，但 §4.2 加多条件仍可能成立。空间闸只挡常识扩维，不挡已登记字段的真漏。

