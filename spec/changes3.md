# Judge Draft 优化协议：准确性与 Authority 收敛

本文遵从以下基线，不替代、不复制其定义：

- `spec/alg/investigate-judge.md`
- `spec/alg/investigate-judge-authority.md`
- `spec/alg/investigate-judge-authority-change1.md`
- `spec/alg/investigate-judge-authority-change2.md`

本文只处理 30 条 `client_search` 冻结运行暴露出的 Draft 问题，并把修复目标
抽象成可长期复用的 Judge Draft 协议约束。

本文不新增产品级 `BusinessExpectation`、`EvaluationDimension` 或 Authority schema，
不改变 Production Judge 的既有单阶段业务行为，也不把 `client_search` 的字段、词语、
case 或正则写入长期协议。

---

# 第一章：优化后长期 Spec 标准

## 1. 目标与长期边界

Draft 的目标不是产生更多 Point、更多文本或更多 `not_evaluable`，而是在同一冻结
输入上：

```text
Draft 的业务判断更准确
AND
没有可见退化
AND
Authority 依赖可解释、可追溯
AND
执行失败不被伪装成业务结论
```

Draft 只允许优化候选 Role 的调查资产、Context、Tool、Planning 和 Assessment
使用方式。Production 的业务协议和单阶段执行路径保持不变；Draft 只有在用户明确
授权 Promotion 后才能进入 Production。

本文后续所称“Draft 代码”或“Draft Core 校正”，均指候选目录内对既有 schema 和
扩展点的消费逻辑，不表示修改 `impl/core` 通用协议。一次性改造只能发生在：

```text
impl/projects/client_search/draft/**
impl/projects/client_search/draft/investigation/**
tests/**
```

允许新增或调整针对 Draft 行为的测试，但不得改变 Production Judge、通用 schema、
通用聚合协议或其他项目的运行行为。

## 2. 最小 schema 数据流

长期数据流只复用现有 schema：

```text
JudgeInvestigationContract
  ├─ BusinessExpectation
  ├─ LiveBoundary
  ├─ EvaluationDimension
  └─ AuthorityAnalysis
        ↓ InvestigationManifest / Solidify receipt
ContextUnit / VerifiableTool / Authority snapshot identity
        ↓
CaseEvaluationPoint
        ↓ actual-free
FrozenCaseEvaluationPlan
        ↓ actual 可见后
FulfillmentAssessment
        ↓ Authority Gate 与既有聚合
JudgeResult
```

每个 schema 只代表一个业务阶段：

| Schema | 业务阶段 | 业务职责 |
|---|---|---|
| `AuthorityAnalysis` | Investigation | 说明某个项目级判断点涉及哪些冲突来源，以及调查能否确定以什么为准 |
| `ContextUnit` / `VerifiableTool` | Solidify | 把已调查、可复核的事实或验证能力交付给 Judge |
| `CaseEvaluationPoint` | Planning | 描述当前 Case 这次具体要验收的一个业务问题 |
| `FrozenCaseEvaluationPlan` | Planning 完成 | 在 actual 出现前冻结全部 Point 和 Authority 快照 |
| `FulfillmentAssessment` | Assessment | 对每个冻结 Point 给出三态和证据 |
| `JudgeResult` | 聚合交付 | 按既有 blocking 规则汇总结果并输出 summary |

不得新增第二套 CaseExpectation、AuthorityEvidence、PlanningDecision、
CoverageRegistry 或 Judgment schema。

## 3. Production 与 Draft 执行策略隔离

### 3.1 Production

Production 保持既有单阶段流程：

```text
构造 Judge Context
  → 一次 Judge 阶段
  → 既有归一化、自检、项目后处理
  → JudgeResult
```

结构化输出自检或有限重询仍属于同一 Judge 阶段，不得被误报为 Draft Planning。
Production 不创建 `FrozenCaseEvaluationPlan`，不装载 Draft-only Planning contract。

### 3.2 Draft

Draft 可以使用两阶段流程：

```text
当前请求 + 项目合同 + 最小 Context
  → actual-free Planning
  → Core 校验并冻结 FrozenCaseEvaluationPlan
  → actual + FrozenCaseEvaluationPlan
  → Assessment
  → Authority Gate / 聚合
  → JudgeResult
```

Planning 和 Assessment 可以各自发生协议允许的结构化重询，但必须在运行审计中分别
记录阶段、调用次数、异常和耗时。Planning 失败不能直接变成业务三态。

## 4. Planning 合同与失败分类

### 4.1 Planning 只负责什么

Planning LLM 只负责：

- 选择当前请求适用的合法产品期望；
- 选择合法评价维度；
- 描述当前 Case 的 `expected_outcome`；
- 给出 `acceptance_criteria` 和 `blocking`；
- 选择当前 Point 实际依赖的 `authority_analysis_ids`。

LLM 不得生成：

- `point_id`；
- `plan_sha256`；
- `authority_snapshot_sha256`；
- Authority 状态、Context ID、Tool ID；
- actual、Comparator、score、confidence 或 verdict。

### 4.2 Core 必须确定性校验

Core 必须拒绝：

- 未知产品期望或评价维度；
- 维度不服务所选产品期望；
- 空的验收条件；
- 同一 Point 的互相矛盾条件；
- 引用不存在、维度不匹配或重复的 Authority ID；
- Planning 输出 actual 或后验判断；
- Plan hash 或 Authority snapshot hash 无法复算。

### 4.3 失败不能伪装

以下情况是执行/协议失败，不是业务 `not_evaluable`：

```text
Planning 缺少必填合同字段
Planning 输出未知 ID
Planning 维度与 Authority 不匹配
Context/Tool 加载失败
LLM 空响应、配额失败、网络失败
```

运行报告必须单独记录：

```text
execution_failure / planning_contract_failure / infrastructure_failure
```

只有 Planning 成功冻结了属于当前业务情景的 Point，但该 Point 缺少决定性业务
证据时，Assessment 才能产出 `not_evaluable`。

### 4.4 Planning 不替调查阶段解决 Authority

Planning 的职责是把当前请求投影为本次要验收的业务 Point：

```text
当前请求
  → 适用的 BusinessExpectation
  → 本次需要检查的 EvaluationDimension
  → expected_outcome / acceptance_criteria / blocking
```

Planning 不负责重新调查资料来源，也不负责自行决定：

- `notes` 和 `value_mappings` 哪一个更权威；
- 某个 enum 是否覆盖下游全集；
- 某个不支持能力应归责于 Live 还是下游；
- AuthorityAnalysis 的状态。

Planning 可以从合法 Authority 目录中声明当前 Point 的候选依赖；但调查包已经
登记了“同一判断对象的来源冲突”时，Draft 代码必须根据该调查事实校正依赖集合，
不能把 Authority 是否绑定完全交给 LLM 自由选择。

## 5. Authority 依赖的长期规则

### 5.1 必须绑定 Authority 的情况

当前 Point 满足以下条件时，必须引用对应 `authority_analysis_id`：

1. 当前 Point 的判断确实依赖一个项目级裁决问题；
2. 已调查材料中存在两个或多个会改变业务结论的说法；
3. Investigation 尚未确定哪一个说法是权威，或动态事实仍不可得；
4. 该 Authority 的 `dimension_ids` 覆盖当前 Point 的维度。

典型抽象现象是：

```text
同一业务概念
  → 当前已激活的两个资料来源给出不同含义
  → 调查无法证明其中一方优先
  → 当前 Point 的结论依赖这次裁决
  → 引用 AuthorityAnalysis
```

这里的“同一业务概念”不是固定关键词集合；不得把某个 case 的词语直接写成长期
触发器。

### 5.2 不得绑定 Authority 的情况

以下情况不得仅凭相似性或字段类型绑定 Authority：

- 用户明确表达了字段、值和操作符，actual 直接结构错误；
- comparator 已能确定字段、操作符或条件缺失；
- 普通不支持能力已由 `LiveBoundary` 明确覆盖；
- 仅因为 Point 属于某个 `dimension_id`；
- 仅因为字段是 enum/list；
- 仅因为用户输入是陌生词；
- 仅因为 Planning LLM 不确定如何拆 Point。

Authority 不是“无法理解时的兜底标签”，也不是“所有枚举都要查下游”的默认
阻断器。

### 5.3 Authority Gate 的结果约束

```text
Point.authority_analysis_ids = ()
  → 不触发 Authority Gate

所有依赖 Authority 已 resolved
  → 可以继续按 Context/Tool 和业务证据判断

任一实际依赖 Authority unresolved
  → 该 Point 确定性约束为 not_evaluable
```

Gate 必须把以下内容写入可追溯 evidence：

- `analysis_id`；
- `judgment_point`；
- 冲突来源；
- 已检查但不足以裁决的证据；
- unresolved 原因；
- 需要人类补充的澄清问题。

Gate 不得让 LLM 通过改写 `reasoning_summary`、改变 Point 或选择另一份 snapshot
绕过限制。

### 5.4 来源冲突的判断对象

Authority 的触发对象是“项目级判断对象”，不是输入词语本身。

调查阶段必须能表达以下关系：

```text
判断对象
  → 相关 SourceClaim[]
  → 每个 SourceClaim 的 origin / producer / consumption_path / failure_modes
  → 调查结论 resolved 或 unresolved
```

例如：

```text
判断对象：孤儿单对应的客户类型

来源 A：capability_manifest.notes
来源 B：capability_manifest.value_mappings

两者对同一概念给出不同映射
调查无法确定正式口径
  → 当前依赖该映射的 Point 必须绑定既有 semantic-mapping-authority
```

这不是为“孤儿单”增加关键词规则，而是要求调查包登记一类可泛化的业务现象：

```text
同一判断对象
  + 多个已激活来源
  + 来源声明互相冲突
  + 当前调查无法裁决
```

如果当前 Point 只涉及明确字段、明确操作符或已确认的 LiveBoundary，则不得因为
它使用 enum/list 字段或属于同一维度而自动绑定 Authority。

## 6. LiveBoundary 与 Point 生成顺序

Point 生成前必须先应用 `LiveBoundary`：

```text
当前请求
  → 判断是否属于产品业务情景
  → 判断请求中的事项是否属于 Live 责任
  → 只为 Live 可归责的事项生成 blocking Point
  → 对外部能力限制保留边界证据
```

当 Live 没有表达某类查询能力时：

- 如果产品边界明确规定“该能力不支持且应提示用户”，正确提示可以是 `fulfilled`；
- 如果 Live 伪造了替代条件、误映射到其他字段，属于 `not_fulfilled`；
- 如果责任边界本身未确认，才使用对应 `evaluation-boundary-authority`；
- 不能把“必须输出一个 Live 无法表达的条件”写成 blocking 验收项。

## 7. 三态与整体聚合

### 7.1 Point 级

每个冻结 Point 必须恰好得到一个：

```text
fulfilled
not_fulfilled
not_evaluable
```

Assessment 不得新增、删除、合并、拆分 Point，也不得修改其 blocking 或
acceptance criteria。

### 7.2 Overall 级

整体聚合必须由代码按冻结 Point 确定性完成：

1. 存在 blocking `not_fulfilled`：整体 `not_fulfilled`；
2. 没有 blocking `not_fulfilled`，但存在 blocking `not_evaluable`：整体
   `not_evaluable`；
3. 所有 blocking Point 为 `fulfilled`：整体 `fulfilled`；
4. 非 blocking Point 的 `not_evaluable` 不得单独把整体降为 `not_evaluable`；
5. `overall_fulfillment.status`、Point assessments 和 Judge summary 必须表达同一
   聚合事实。

如果整体为 `fulfilled`，summary 不得声称“关键 Authority 未解决”；如果存在
未解决 Authority，只能说明它影响了非 blocking 或不影响整体的附加 Point。

## 8. 输入规模与工具约束

### 8.1 Investigation / Solidify / Planning 的 key-index 串联

调查阶段不新增字段定义 schema，而是在既有 `InvestigationManifest` 中登记最小
字段检索能力：

```text
ToolRequirement: field_search_keys
ToolRequirement: field_search_definition
```

Solidify 在 Draft 区域提供两个候选工具：

```text
field_search_keys(query)
  → [{key, short_name}]

field_search_definition(key)
  → 单个 key 的最小定义、允许操作符、必要枚举/映射和 source_refs
```

`field_search_keys` 只解决“可能查哪个字段”；`field_search_definition` 才提供
当前 Point 所需的最小字段事实。两个工具的结果必须能回到调查包中的 EvidenceRef
或 ToolRequirement，不得由 LLM 临时编造字段、枚举或来源 ID。

数据流是：

```text
Investigation
  → 登记字段来源、冲突判断点和 ToolRequirement
Solidify
  → 固化 key index 与单 key 最小定义工具
Planning
  → 先取得候选 key，再读取被选中的单 key 定义
  → 生成 CaseEvaluationPoint
Draft Core
  → 根据 source_refs 对已登记的 Authority 冲突做依赖校正
Assessment
  → 仅在缺少决定性事实时再次使用单 key Tool
```

`source_refs` 只用于溯源和冲突识别，不是新的 schema，也不替代
`AuthorityAnalysis.evidence_ref_ids`。

### 8.2 最小运行输入

Planning 默认只读取：

- 当前请求；
- 产品期望和维度的最小目录；
- 当前候选字段 key/短名称索引；
- 已声明的最小 Context；
- 当前可能相关的 Authority ID 与 `judgment_point`。

大型字段定义、完整枚举、enhanced rules 和历史资料必须遵循：

```text
field/tool key index
  → 选定单个 key
  → 单 key 最小定义
  → 只有缺少决定性事实时才执行 Tool
```

不得把全量字段描述、全量历史 case 或完整调查包放进每个 Planning/Assessment
请求。相同 Tool 和参数不得重复调用。

`field_search_keys` 不返回完整字段描述；`field_search_definition` 一次只返回
一个已选中的 key。若 key-index 无法提供足够候选，应记录字段事实不足，而不是把全量
资料注入 Prompt。

## 9. 长期回归和 Promotion 门禁

每轮 Draft 必须同时记录：

- 双侧原始结果；
- Planning/Assessment/结构重询调用次数；
- elapsed time 和可用 token 指标；
- `planning_contract_failure` 数；
- Authority dependency omission rate；
- Authority dependency over-selection rate；
- Authority Gate 触发和有效 `not_evaluable` 率；
- blocking Point 与 overall 聚合不一致数；
- 相对 Production 的改善、退化和证据不足 case。

只有以下条件同时满足才允许 Promotion：

```text
双侧运行无未分类执行失败
AND Draft 业务准确性被逐 case 证据证明更好
AND 没有可见业务退化
AND Authority 漏选/误选达到 review 要求
AND overall/Point/summary 聚合一致
AND unseen promotion checks 不退化
```

更多 Point、更长理由、更高 confidence 或更多 `not_evaluable` 本身都不算改善。

---

# 第二章：Changes——现状差异与一次性改造任务

## 10. 30 条冻结运行基线

本轮使用同一冻结输入运行 Production 与 Draft：

```text
case_count: 30
有效双侧业务比较: 28
Draft Planning 合同失败: 2
Production / Draft 整体状态一致: 18 / 28
```

状态分布：

| 侧别 | fulfilled | not_fulfilled | not_evaluable |
|---|---:|---:|---:|
| Production | 17 | 12 | 1 |
| Draft | 13 | 12 | 5 |

耗时：

```text
Production 平均 67.5 秒 / case
Draft 平均 92.8 秒 / case
Draft 约慢 37.5%
```

完整原始事实以本轮 Draft Loop 报告为准，不把本节数字写入运行时 Prompt：

```text
impl/projects/client_search/draft/.state/judge/iterations/001-run.json
```

## 11. 已确认的问题

### 11.1 Planning 合同失败被包装为业务结果

以下 case 没有形成合法的 actual-free Plan：

```text
source-badcase-068
source-badcase-073
```

现状问题：

- Planning 缺少适用性合同字段；
- Point 与 Authority 维度不匹配；
- 最终以 `not_evaluable` 形式出现在 Draft 结果中；
- 业务评测无法区分“调查证据不足”和“Planning 没有完成”。

长期差异：

```text
当前：Planning failure → 外观上像 not_evaluable
目标：Planning failure → 独立 execution/protocol failure，不能进入业务胜负统计
```

### 11.2 Authority 漏选

`source-badcase-008` 的业务资料对同一“孤儿单”概念给出冲突说法：

```text
notes
  与
value_mappings
```

Draft 没有把这个“已激活资料之间的项目级冲突”识别为 Authority 依赖，而是直接
选择其中一方并输出 `fulfilled`。

这说明当前 Authority 触发逻辑过度依赖“用户表达是否像裸命名实体”和弱映射启发式，
没有覆盖更一般的：

```text
当前 Point 依赖的判断对象
  → 多个已激活资料对该对象给出冲突声明
  → 调查包无法确定裁决
```

一次性改造不得添加“孤儿单”关键词规则；应从已加载的最小业务资料建立可验证的
冲突事实，并让该事实回到既有 `AuthorityAnalysis` ID。

### 11.3 Authority 过度绑定

部分普通枚举或字段能力 case 被 `enum-value-authority` 覆盖，即使当前 Point 已可由
明确条件、字段协议或 LiveBoundary 判断。

现状后果：

- `not_evaluable` 增多；
- Draft 变得更慢；
- 真实结构错误和“枚举全集未知”混在一起；
- 业务方无法判断到底是需要补充 Authority，还是 parser 已经明确错误。

改造必须把“枚举字段”与“枚举全集完整性确实决定当前结论”分开。

### 11.4 LiveBoundary 误归责

公司名称、机构名称或当前能力明确不支持的查询被 Draft 生成了
“必须输出对应结构化条件”的 blocking Point，导致：

```text
Live 明确按不支持边界处理
  → Draft 却判 Live 未完成条件
```

改造必须先应用 LiveBoundary，再决定是否生成 blocking Point；不得用
“Point 越细”替代边界判断。

### 11.5 Point、Gate 与 overall 聚合不一致

`source-badcase-128` 出现：

```text
某个 Point：Authority Gate → not_evaluable
overall：fulfilled
```

这不是三态本身的问题，而是 Point 的 blocking 设计、Authority 依赖和 overall 聚合
之间没有表达同一业务事实。

改造必须保证：

- Authority 依赖 Point 的 blocking 由 Planning/Core 正确冻结；
- Gate 结果进入既有聚合；
- summary 不得与 overall 互相矛盾。

## 12. 一次性改造任务

### P0：修复 Planning 合同稳定性

目标：

- 30 条冻结 case 全部生成合法 `FrozenCaseEvaluationPlan`；
- Planning failure 不再生成伪业务 `not_evaluable`；
- 每个失败保留明确的协议错误、阶段和输入指针。

范围：

```text
impl/projects/client_search/draft/
tests/
```

不得修改 Production Judge 的单阶段业务路径。

验收：

- 30/30 Planning 成功；
- 0 条 `planning_contract_failure` 被计入业务三态；
- 未知 ID、维度不匹配和空 Point 均被确定性拒绝。

### P0：修复 Authority 绑定精度

目标：

- 对“同一判断对象的已激活资料冲突”可识别、可追溯；
- 冲突无法确定时绑定既有 `AuthorityAnalysis`；
- 已能直接判断的 Point 不绑定 Authority；
- 不新增 Authority schema 或关键词白名单。

实现要求：

1. Investigation 明确登记该类项目级判断点、来源和 unresolved question；
2. Solidify receipt 将来源冲突事实映射到既有 Authority receipt/mapping；
3. key-index 与单 key 定义工具返回最小字段事实和可追溯 `source_refs`；
4. Planning 只选择合法 `analysis_id`，不生成新 ID；
5. Draft 代码根据已登记的冲突判断对象校正 Point 的 Authority 依赖；
6. Draft 代码校验维度和 snapshot；
7. Gate 对实际依赖的 Point 强制 `not_evaluable`；
8. Judge summary 说明冲突双方和人类需要补充的内容。

验收：

- Authority dependency omission 有独立计数；
- Authority dependency over-selection 有独立计数；
- “资料冲突但漏绑定”回归 case 必须进入 `not_evaluable`；
- “直接结构错误/明确不支持”回归 case 不得因 Authority 过绑而变成
  `not_evaluable`。

### P0：修复 LiveBoundary 与聚合

目标：

- 不支持能力不被误归责；
- blocking Point、Authority Gate、overall 和 summary 一致；
- 非 blocking `not_evaluable` 不改变整体结果，但必须可追溯。

验收：

- unsupported boundary case 不产生虚假的 Live blocking expectation；
- blocking Authority unresolved 时整体不能输出肯定结论；
- overall 为 `fulfilled` 时不得声称关键 Authority 未解决；
- 每条 summary 能定位影响整体状态的 Point。

### P1：缩小输入与调用成本

目标：

- Planning 只消费最小目录和单 key 定义；
- `field_search_keys` 不返回完整字段描述；
- `field_search_definition` 一次只返回一个被选中的 key；
- 不加载全量字段、全量枚举或完整历史资料；
- 同一 Tool/参数不重复调用；
- 结构化重询与 Planning/Assessment 分阶段计量。

验收：

- 30 条运行保存调用阶段和耗时；
- Draft 平均耗时不因新增 Gate/Point 显著增加；
- 在准确性不退化前提下，Draft 与 Production 的耗时差距收敛。

### P1：补充回归与评测门禁

至少保留以下四类冻结 case：

1. 资料冲突且 Authority unresolved，必须 `not_evaluable`；
2. 同一维度的无关 Point，不得继承 Authority；
3. 直接结构错误，无需 Authority，必须直接判断；
4. Live 明确不支持，不能误归责为 Live 失败。

每轮必须运行：

```text
30 条冻结 cases
  → Current / Draft 原始报告
  → Role review receipt
  → 逐 case 准确性、Authority、边界和聚合审查
```

只有满足长期 Spec 第 9 节全部 Promotion 门禁，才允许用户考虑 Promotion。

## 13. 不在本次改造范围内

- 不恢复或修改 Production Planning；
- 不新增 `FrozenCaseExpectation`、`CaseAuthorityEvidence`、`judgment_id`、
  `coverage registry` 或第二套 BusinessExpectation；
- 不将 30 条 badcase 的具体词语、字段、正则固化为通用 Authority 规则；
- 不自动因 hash 改变触发 Investigation 或 Solidify；
- 不把更多 LLM 调用当成准确性保证；
- 不用提高 `not_evaluable` 率替代 Authority 识别质量；
- 不在 Draft 尚未证明无退化时 Promote。
