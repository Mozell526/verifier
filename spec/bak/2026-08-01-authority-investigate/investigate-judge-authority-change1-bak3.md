# Judge Pre-Actual Plan 与 Authority 结果约束增量协议

本文是以下两份规范的增量协议：

- `spec/alg/investigate-judge.md`
- `spec/alg/investigate-judge-authority.md`

发生歧义时，以上两份基线优先。本文不替代 Investigate、Solidify、Draft Loop、
Promote、公共三态语义或 Judge 聚合协议，只补充两个运行时缺口：

1. 当前 Case 的原子验收项必须在 actual 可见前冻结；
2. 当某个原子判断依赖 unresolved Authority 且没有独立决定性证据时，Core 必须把
   该判断确定性约束为 `not_evaluable`，不能只依赖 Prompt 提示。

本文遵循奥卡姆剃刀，只新增两个具有独立业务意义的内部 dataclass：

- `FrozenCaseExpectation`：当前 Case 中一项可以独立得到三态的原子判断；
- `FrozenExpectationPlan`：冻结本次 Case 的全部原子判断和 Authority 资产快照。

Authority、Evidence、Gate 和最终结果继续复用基线与当前项目已有的
`AuthorityAnalysis`、`RoleAssetMapping`、Solidify receipt、`ToolResult`、
`EvidenceRef`、`FulfillmentAssessment`、`GateDecision` 和 `JudgeResult`，不建立
第二套 Authority schema、registry 或 Case 审批协议。

---

# 第一章：继承边界

## 1.1 三层业务对象

本文严格区分三层对象：

```text
项目级业务合同
  JudgeInvestigationContract.BusinessExpectation
  LiveBoundary
  EvaluationDimension
  AuthorityAnalysis
          │
          │ Investigate → Solidify
          ▼
已固化 Judge 能力
  authority_anchors
  ContextUnit
  VerifiableTool
  RoleAssetMapping
  Solidify receipt
          │
          │ 当前 Case 投影
          ▼
Case 级判断
  FrozenCaseExpectation
  FrozenExpectationPlan
  FulfillmentAssessment
  GateDecision
  JudgeResult
```

- 项目级 `BusinessExpectation` 描述完整产品的用户和期望结果；
- `EvaluationDimension` 描述从哪个角度评价 Live 对产品结果的贡献；
- `AuthorityAnalysis` 描述某类判断需要相信什么来源以及当前是否已经确认；
- Solidify 把项目级调查编译为最小、可执行、可观察的 Judge 资产；
- `FrozenCaseExpectation` 描述当前 Case 的一个原子判断及其业务来源；
- `FrozenExpectationPlan` 冻结这些原子判断以及本次采用的 Authority 资产版本；
- `FulfillmentAssessment` 和 `JudgeResult` 只评价 actual 是否满足已冻结标准。

项目级调查对象不得直接复制为当前 Case 目标答案，当前 Case 证据也不得反向修改
项目级 Authority 状态。

## 1.2 本文不修改的公共对象

本文不修改：

- `InvestigationManifest`
- `JudgeInvestigationContract`
- 项目级和现有 runtime `BusinessExpectation`
- `LiveBoundary`
- `EvaluationDimension`
- `AuthorityAnalysis`
- `ToolRequirement`
- `RoleAssetMapping`
- Solidify receipt 的公共流程
- `ToolResult`
- `EvidenceRef`
- `FulfillmentAssessment`
- `GateDecision`
- `JudgeResult`
- 三态词表和 overall 聚合协议

本文只规定已有 `RoleAssetMapping.metadata`、`ToolResult.runtime_metadata` 和 evidence
字段中与本链路有关的最小机器合同。这些值必须由 Investigate、Solidify、Core 或
Tool runner 生成和校验，不能成为新的人工业务事实源。

## 1.3 明确废止的历史方向

本文不恢复以下历史设计：

- 不要求 LLM 为每条 Case 填写 `authority_analysis_ids`；
- 不建立 `JudgmentClaim` 或 `AuthorityApplicabilityDecision` 公共 schema；
- 不按整个 Case 或整个 dimension 扩散 `not_evaluable`；
- 不把完整 `AuthorityAnalysis`、`source_claims` 或 `causal_chain` 注入 Runtime；
- 不让 Planning LLM 自行选择一组能够决定 Gate 是否执行的 Authority scope；
- 不使用 `coverage_keys` 作为含义模糊、可多选的 Case 路由协议；
- 不允许 ToolResult 自报自己有权解除 Authority 限制；
- 不把当前 Case 的证据状态命名为或写回项目级 Authority 的 `resolved` 状态。

---

# 第二章：业务不变量

## 2.1 标准必须先于 actual

Judge 必须在当前 Case 的 actual 首次可见前确定：

- 当前 Case 适用哪些产品级业务期望；
- 每个产品期望投影出哪些原子验收项；
- 每个原子验收项关联哪个 EvaluationDimension；
- 每个原子验收项属于哪种 `judgment_kind`；
- 每个原子验收项检查什么；
- 每项是否 `blocking`；
- 本次计划采用哪个 Solidify/Authority 资产快照。

actual 首次可见后，任何组件都不得：

- 新增、删除、合并或拆分 expectation；
- 修改 acceptance criteria；
- 修改 `blocking`；
- 修改 product expectation、dimension 或 `judgment_kind` 映射；
- 切换 Authority 资产快照；
- 让 Comparator 根据 actual 反向创建业务标准。

这条约束保证 Judge 先写验收标准，再看被评估系统的答案。

## 2.2 Authority 是项目知识，不是 Case 审批

`AuthorityAnalysis.anchor.status` 只表示项目级调查状态：

```text
resolved
unresolved
```

Runtime 不得新增 `resolved_for_current_case` 之类的 Authority 状态。当前 Case
如果获得了直接、决定性的用户事实、业务合同或封闭式 Tool 证据，只能表述为：

```text
当前 Case 已有独立决定性证据
```

它表示该原子判断不再依赖项目级未知结论，不表示项目 Authority 已经被解决，也不得
写回 `AuthorityAnalysis` 或 Solidify 资产。

## 2.3 三态必须按证据依赖局部判断

- actual 明确缺少 Live 应交付的结果，通常是 `not_fulfilled`；
- actual 明确包含错误或额外约束，通常是 `not_fulfilled`；
- actual 无法取得或无法确认，通常是 `not_evaluable`；
- 某个原子判断依赖 unresolved Authority 且没有独立决定性证据时，是
  `not_evaluable`；
- 当前 Case 不属于产品期望的 `use_scenario` 时，不生成该验收项，不产生第四种状态。

Authority 约束不得把直接证据已经证明的 Live 失败包装成 `not_evaluable`，也不得影响
与该 Authority 无关的 expectation。

## 2.4 当前 Case 验收项必须原子化

一个 `FrozenCaseExpectation` 只能对应：

- 一个 runtime `BusinessExpectation`；
- 一个项目级 `product_expectation_id`；
- 一个 `evaluation_dimension_id`；
- 一个 `judgment_kind`；
- 一个最终三态。

如果两项条件可能因为 Authority 或证据状态不同而得到不同三态，就必须拆成两个
`FrozenCaseExpectation`。例如：

```text
判断 A：actual 必须包含 age > 30
  → evaluation_dimension_id = search-intent-preservation
  → judgment_kind = explicit_condition

判断 B：“高净值客户”必须映射为正确 clientLevel
  → evaluation_dimension_id = search-intent-preservation
  → judgment_kind = semantic_mapping
```

不得把 A 和 B 合并为一个 assessment 后，再让 B 的 unresolved Authority 把 A 的
明确失败覆盖成 `not_evaluable`。

## 2.5 原子化不等于破坏业务组合逻辑

子 expectation 不得机械继承父级 `blocking`。只有“该原子项单独失败就会阻断对应
产品结果”时，它才是 blocking。

对于 `A OR B`、替代交付路径或其他无法用独立 blocking 表达的复合命题：

- 不得简单拆成多个 blocking expectation；
- 应保留为一个可由确定性 Comparator 判断的原子业务命题；
- 如果不同分支又具有不同 Authority 依赖，当前公共 schema 无法无损表达时，Planning
  必须失败并记录能力缺口，不能偷偷选择其中一个分支。

本文不为任意布尔组合新增 grouping schema。

---

# 第三章：最小 dataclass schema

## 3.1 `FrozenCaseExpectation`

```python
from dataclasses import dataclass

from impl.core.schema import BusinessExpectation


@dataclass(frozen=True)
class FrozenCaseExpectation:
    """actual 可见前冻结的一项当前 Case 原子判断。"""

    case_expectation: BusinessExpectation
    product_expectation_id: str
    evaluation_dimension_id: str
    judgment_kind: str
```

字段业务意义：

- `case_expectation`：复用现有 runtime `BusinessExpectation`，保存
  `expectation_id`、acceptance criteria、`blocking` 和下游影响；
- `product_expectation_id`：追溯到哪个项目级产品期望，回答“为什么判断”；
- `evaluation_dimension_id`：从哪个角度评价 Live，回答“评价哪项贡献”；
- `judgment_kind`：当前原子项具体判断哪类事实，回答“判断什么”。

`FrozenCaseExpectation` 不保存 Authority ID。Authority 是否适用由 Core 根据
`evaluation_dimension_id + judgment_kind` 和 Solidify mapping 确定，不能由 Planning
LLM 自报。

`case_expectation` 必须在封存时做 canonical copy，不得向 Assessment 暴露可修改的
原对象。一个 `case_expectation.expectation_id` 在同一 Plan 内必须唯一。

## 3.2 `FrozenExpectationPlan`

```python
@dataclass(frozen=True)
class FrozenExpectationPlan:
    """actual 可见前冻结的当前 Case 判断计划。"""

    plan_id: str
    trace_id: str
    expectations: tuple[FrozenCaseExpectation, ...]
    authority_snapshot_sha256: str
    plan_sha256: str
```

字段业务意义：

- `plan_id`：本次计划的稳定身份；
- `trace_id`：计划属于哪次 Case；
- `expectations`：当前 Case 的全部原子判断；
- `authority_snapshot_sha256`：本次计划采用的 Solidify/Authority 资产快照；
- `plan_sha256`：证明 Assessment 使用的是同一份未被 actual 改写的计划。

`authority_snapshot_sha256` 必须覆盖本次 Judge 实际激活的：

- Solidify receipt identity；
- Authority source/status；
- Authority 到 asset 的 mapping；
- dimension 与 `judgment_kind` 路由；
- asset revision 和可用性。

项目没有 AuthorityAnalysis 时，也必须使用规范化空 Authority snapshot 的稳定 hash，
不能使用空字符串表达“未校验”。

`plan_sha256` 必须覆盖完整 `FrozenCaseExpectation[]`、
`authority_snapshot_sha256` 和 plan identity。canonical payload 中不得包含 actual、
Comparator 结果、verdict、score 或 confidence。

## 3.3 为什么不继续使用 BusinessExpectation.boundary

现有 `BusinessExpectation.boundary: Dict[str, Any]` 可以继续保存项目通用边界信息，
但本文不再把 product/dimension/`judgment_kind` 的核心串联隐藏在自由字典里。

原因是这三个字段共同决定：

- 当前 Case 判断来自哪里；
- Authority 是否适用；
- Gate 是否可以改写结果；
- 最终结果如何审计。

它们具有独立、稳定的业务意义，值得进入最小 typed schema。

## 3.4 `judgment_kind`

`judgment_kind` 不是测试覆盖率、Authority ID 或 verdict。它表示：

> 当前原子 expectation 正在判断哪一类可重复出现的业务事实。

client_search 可以固化：

```text
explicit_condition
boolean_logic
unexpressed_constraint
semantic_mapping
enum_legality
query_equivalence
live_boundary
```

这些名称由项目调查和 Solidify 固化，不是本文定义的全局固定枚举。不得使用字段名、
Case ID、actual 错误内容或临时自然语言作为 `judgment_kind`。

项目可用的 `judgment_kind` 词表取自本次实际激活的 Judge
`RoleAssetMapping.metadata.judgment_kinds` 的并集，并由 Solidify receipt 冻结：

- 候选 Judge/Comparator asset 声明自己能够判断哪些 kind；
- Authority asset 声明自己约束其中哪些 kind；
- Plan 只能使用已激活资产支持的 kind；
- Authority asset 的 kind 必须是 Judge 可判断 kind 的子集。

这样不需要再建立独立 coverage/judgment registry。

一个 `FrozenCaseExpectation` 只能有一个 `judgment_kind`。如果一个 acceptance
criterion 同时依赖多类判断且可能产生不同三态，必须拆分；无法无损拆分时按 2.5
处理。

---

# 第四章：Authority Solidify 投影

## 4.1 继续使用基线 Authority 数据流

本文不新增 Authority runtime dataclass。`AuthorityAnalysis` 继续按照基线固化：

```text
AuthorityAnalysis
    ↓ Solidify
authority_anchors 最小投影
    ├── analysis_id
    ├── dimension_ids
    ├── resolved / unresolved
    ├── conclusion / unresolved_question
    ├── verification 声明
    └── 保守 runtime directive
    ↓
ContextUnit / VerifiableTool / RoleAssetMapping / receipt
```

Runtime 不得读取完整 Judge investigation contract 来重新确认 Authority。

## 4.2 RoleAssetMapping 的最小机器合同

每个 `authority:<analysis_id>` 必须有独立、可观察的 Solidify mapping。已有
`RoleAssetMapping` 至少保留：

```yaml
asset_id: client-search-semantic-mapping-limit
kind: context
roles:
  - judge
metadata:
  authority_sources:
    - semantic-mapping-authority
  dimension_ids:
    - search-intent-preservation
  judgment_kinds:
    - semantic_mapping
  authority_status: unresolved
  limitation_reason: 缺少业务术语表或用户确认，无法确定唯一字段映射。
  revision: 2b24c53
```

字段来源必须唯一：

- `authority_sources`、`authority_status` 来自 `AuthorityAnalysis`；
- `dimension_ids` 来自 `AuthorityAnalysis.dimension_ids`；
- `judgment_kinds` 由 Solidify 根据 Authority judgment point 映射到稳定原子语义；
- `asset_id` 使用现有 Role asset 身份，不再发明第二个 scope；
- `limitation_reason` 来自 unresolved question 的业务化最小投影；
- `revision` 标识本次 Solidify 采用的调查与资产版本。

项目配置不得分别手写出互相冲突的 Authority 状态。Validator 必须把 Solidify receipt
及其源 AuthorityAnalysis 作为一致性依据。

非 Authority 的候选 Judge、Comparator 或 Context asset 也可以在
`RoleAssetMapping.metadata.judgment_kinds` 声明其支持的原子判断类型。Authority
asset 的 `judgment_kinds` 只表示对其中哪些类型施加来源约束，不代表它拥有这些
判断类型。

## 4.3 runtime directive 必须派生

`runtime_directive` 不是独立配置真相，必须由 Authority 状态和已固化能力派生：

```text
resolved + 所需能力可用
  → apply_resolved_anchor

resolved + 已确认静态规则可用，但当前动态事实能力不可用
  → apply_resolved_anchor_but_do_not_assume_unverified_dynamic_facts

unresolved
  → not_evaluable_when_authority_is_required
```

对于 unresolved Authority，Solidify：

- 不生成肯定业务答案；
- 不生成开放式来源调查 Tool；
- 可以生成最小 limitation observable 或 runtime anchor，使结果可解释；
- 必须记录该 Authority 是否真实进入候选 Judge 的运行时可观察链路。

limitation observable 不是答案知识，不违反基线中“unresolved 不构建答案
ContextUnit/Tool”的边界。

## 4.4 Tool 不能自授权

`AuthorityAnalysis.tool_requirement_ids` 表示验证 Authority 锚点所需的
ToolRequirement，不自动表示这些 Tool 可以在当前 Case 中修改 Authority 状态。

当前 Case Tool 证据只有同时满足以下条件时，Core 才能把它视为独立决定性证据：

1. ToolRequirement 已在 InvestigationManifest 声明；
2. Solidify 已把它编译为可执行 VerifiableTool；
3. Solidify receipt 明确记录 Tool、Authority source、dimension 和
   `judgment_kind` 的映射；
4. Tool runner 执行成功；
5. Tool 的封闭式结果语义表明当前判断已有充分事实，而不是仅仅调用成功；
6. provenance 由 runner 根据激活 receipt 附加，不能来自 Tool 自己在 `outputs`
   中的声明。

因此本文不定义：

- `RoleAssetMapping.metadata.resolution_tool_ids`；
- `ToolResult.outputs.authority_resolutions`；
- `resolved_for_current_case` Authority 状态。

## 4.5 ToolResult.runtime_metadata 最小合同

项目 Tool 保留自己的事实输出。对于可能成为 Authority-independent 决定性证据的
ToolResult，runner 必须在现有 `runtime_metadata` 中附加：

```yaml
authority_snapshot_sha256: ...
solidify_receipt_sha256: ...
authority_sources:
  - semantic-mapping-authority
dimension_ids:
  - search-intent-preservation
judgment_kinds:
  - semantic_mapping
evidence_status: decisive
evidence_basis: current_user_fact
source_revision: ...
```

其中：

- `evidence_status` 只能是 `decisive` 或 `insufficient`；
- `evidence_basis` 必须来自项目已登记的封闭词表，例如
  `current_user_fact`、`product_contract_fact`、`closed_tool_observation`；
- `solidify_receipt_sha256` 必须对应生成 Plan snapshot 的 receipt；
- `authority_snapshot_sha256` 必须等于 Plan 使用的 snapshot；
- `authority_sources`、dimension、judgment kind 和 revision 必须来自 receipt；
- Tool 只能返回业务事实，不能自己构造或覆盖这些 runner-owned 字段。

`FulfillmentAssessment.evidence_refs` 必须把这份 ToolResult/EvidenceRef 绑定到具体
`case_expectation.expectation_id`。Gate 只检查当前 assessment 已绑定的证据，不能因为
其他 expectation 使用过同一 Tool 就全局解除限制。

---

# 第五章：Schema 数据流

## 5.1 Investigate → Solidify

```text
JudgeInvestigationContract.BusinessExpectation
  ├── expectation_id
  └── desired_outcome

EvaluationDimension
  ├── dimension_id
  └── expectation_ids

AuthorityAnalysis
  ├── analysis_id
  ├── dimension_ids
  └── anchor.status
          ↓ Harness AI / Solidify
RoleAssetMapping
  ├── asset_id
  └── metadata:
        authority_sources
        dimension_ids
        judgment_kinds
        authority_status
        revision
          ↓
Solidify receipt + runtime observable
```

Harness AI 负责根据调查结果决定复用、包装或构建哪些资产。本文不要求把
AuthorityAnalysis 机械编译成代码，也不允许 Runtime 重新执行 Solidify。

Solidify 失败条件：

- AuthorityAnalysis 没有独立 mapping；
- mapping 没有保留 dimension；
- Authority 判断点没有稳定 `judgment_kinds`；
- resolved 动态 Authority 声明的 ToolRequirement 没有明确可用性；
- unresolved 被固化成肯定答案；
- runtime observable 无法证明资产真实加载；
- receipt 与 AuthorityAnalysis 状态或来源不一致。

## 5.2 项目合同 → FrozenCaseExpectation

Planning 阶段可以读取：

- 当前 Case 用户请求；
- reference；
- 项目级 BusinessExpectation；
- LiveBoundary；
- EvaluationDimension；
- Solidify 编译出的稳定 `judgment_kind` 词表和能力边界；
- 已知输入缺失情况。

Planning 阶段不得读取：

- actual；
- actual 摘要；
- Comparator 结果；
- 候选 verdict；
- 当前 Case score/confidence；
- 为了解释 actual 偏差而生成的后验规则。

每个 `FrozenCaseExpectation` 的来源关系必须是：

```text
JudgeInvestigationContract.BusinessExpectation.expectation_id
    → FrozenCaseExpectation.product_expectation_id

EvaluationDimension.dimension_id
    → FrozenCaseExpectation.evaluation_dimension_id

当前 Case 用户输入/reference + LiveBoundary
    → FrozenCaseExpectation.case_expectation

Solidify 稳定判断词表
    → FrozenCaseExpectation.judgment_kind
```

Planning LLM 可以提出当前 Case 原子 expectation，但 Core validator 必须独立确认：

- product expectation 真实存在且当前 `use_scenario` 适用；
- dimension 真实存在并服务该 product expectation；
- `judgment_kind` 已由 Solidify/项目合同登记；
- acceptance criteria 与 `judgment_kind` 语义一致；
- expectation 足够原子；
- `blocking` 符合产品结果，而不是根据 actual 推导。

## 5.3 FrozenCaseExpectation[] → FrozenExpectationPlan

```python
def build_frozen_expectation_plan(
    trace_without_actual,
    product_contract,
    solidify_receipt,
) -> FrozenExpectationPlan:
    ...
```

Plan builder 必须：

1. 根据 `use_scenario` 选择当前 Case 适用的产品期望；
2. 根据 LiveBoundary 排除不属于 Live 的责任；
3. 关联单个 EvaluationDimension；
4. 生成原子 `FrozenCaseExpectation`；
5. 验证 `judgment_kind`；
6. 在 actual 可见前确定 `blocking`；
7. 计算 `authority_snapshot_sha256`；
8. canonicalize 后计算 `plan_sha256`。

如果 Solidify receipt 或 Authority mapping 在 Planning 与 Assessment 之间变化，
snapshot 校验必须失败并停止本次 Plan。系统可以在新的输入周期创建新 `plan_id`，
但不得让同一 Plan 静默采用新 Authority。

## 5.4 Plan → Authority applicability

Core 根据以下规则确定每个原子 expectation 的适用 Authority：

```text
FrozenCaseExpectation.evaluation_dimension_id
    ∈ RoleAssetMapping.metadata.dimension_ids
AND
FrozenCaseExpectation.judgment_kind
    ∈ RoleAssetMapping.metadata.judgment_kinds
```

`asset_id` 是匹配后的资产身份和审计信息，不是 Planning 输入。只满足 dimension 但
`judgment_kind` 不匹配时，该 Authority 不适用。

Authority 适用关系必须在 actual-free Plan 校验阶段确定，并由
`authority_snapshot_sha256` 冻结。Runtime 可以重新验证 snapshot 和引用完整性，但
不得在看到 actual 后改变适用关系。

## 5.5 actual → ToolResult/EvidenceRef → FulfillmentAssessment

Plan 冻结后才允许读取 actual：

```text
FrozenExpectationPlan
  + actual
  + 已固化 Comparator / VerifiableTool
      ↓
ToolResult / EvidenceRef
      ↓ expectation_id
FulfillmentAssessment
```

Comparator 是 evidence producer，不是 expectation producer。它只能对已有
`case_expectation.expectation_id` 产生：

- expected/actual 对比事实；
- missing/wrong/extra；
- 证据不足；
- ToolResult；
- EvidenceRef；
- runner-owned provenance。

Comparator 不得新增 expectation、修改 acceptance criteria 或声称修改 Authority
状态。

## 5.6 Authority Result Gate

Assessment LLM 输出初始 `FulfillmentAssessment[]` 后，在公共 normalize/finalize 和
overall 聚合前，Core 执行确定性 Gate：

```python
def apply_authority_constraints(
    plan: FrozenExpectationPlan,
    active_role_assets: tuple[RoleAssetMapping, ...],
    assessments: list[FulfillmentAssessment],
    evidence_refs: tuple[EvidenceRef, ...],
) -> tuple[list[FulfillmentAssessment], list[GateDecision]]:
    ...
```

Gate 对每个 `FrozenCaseExpectation` 独立处理：

| 适用 Authority | 当前 assessment 的独立决定性证据 | 初始判断依据 | 最终处理 |
|---|---|---|---|
| 无 | 任意 | 任意 | 不因 Authority 改写 |
| resolved | 充分 | 符合已确认规则 | 保留 assessment |
| resolved，但所需动态事实不可取得 | 无 | 依赖该动态事实 | `not_evaluable` |
| unresolved | 有 | 结论不再依赖未知 Authority | 保留 assessment |
| unresolved | 无 | fulfilled/not_fulfilled 依赖未知 Authority | `not_evaluable` |
| unresolved | 无 | 独立证据已证明直接缺失、解析失败或明确越界 | 保留 `not_fulfilled` |

当 Gate 约束为 `not_evaluable` 时，必须：

- `status="not_evaluable"`；
- `score=None`；
- `confidence=None`；
- 在 assessment evidence 中记录受限业务判断；
- 产生一个 `GateDecision`；
- 引用 Authority source、asset ID、dimension、`judgment_kind`、revision 和 snapshot；
- `GateDecision` 记录 original status 和推荐转换，转换后的 assessment/JudgeResult
  记录 final status。

`GateDecision` 复用现有 schema：

```python
GateDecision(
    gate_id="authority:plan-001:case-high-value",
    gate_type="authority_result_constraint",
    passed=False,
    checked_inputs={
        "expectation_id": "case-high-value",
        "evaluation_dimension_id": "search-intent-preservation",
        "judgment_kind": "semantic_mapping",
        "authority_source": "semantic-mapping-authority",
        "asset_id": "client-search-semantic-mapping-limit",
        "authority_snapshot_sha256": "...",
        "original_status": "not_fulfilled",
    },
    missing_evidence=[
        "缺少独立、决定性的高净值客户字段映射"
    ],
    recommended_transition="not_evaluable",
    reason="判断依赖 unresolved Authority",
)
```

Gate 不得：

- 修改 FrozenExpectationPlan；
- 修改 AuthorityAnalysis 或 authority anchor 状态；
- 影响 dimension/`judgment_kind` 不匹配的 expectation；
- 仅根据 LLM 自然语言声称“证据充分”而解除限制；
- 仅因为 ToolResult `status=succeeded` 就认为事实已经确定；
- 把直接可证的 `not_fulfilled` 改成 `not_evaluable`；
- 在项目 `reconcile_result()` 中再次执行另一套 Authority 判断。

Gate 后的 assessments 才能进入公共 overall 聚合。GateDecision 作为最小审计证据进入
现有 JudgeResult evidence 链路，不新增 JudgeResult 字段。

---

# 第六章：失败与版本语义

## 6.1 Planning 失败

出现以下任一情况时，Planning 不得继续读取 actual：

- 没有适用 expectation，且无法证明当前 Case 确实不属于任何 `use_scenario`；
- `FrozenCaseExpectation` 缺少有效 product expectation；
- dimension 不存在或不服务对应 product expectation；
- `judgment_kind` 缺失、未知或与 acceptance criteria 不一致；
- expectation 把可能产生不同三态的条件合并在一起；
- 无法无损表达具有不同 Authority 依赖的 OR/替代路径；
- plan 包含 actual、Comparator 结果或后验 verdict；
- Authority snapshot 或 plan hash 无法验证；
- Solidify receipt 与实际激活资产不一致。

Planning 失败表示无法安全建立当前 Case 验收标准。它应返回现有公共失败/
`not_evaluable` 路径，不得生成空计划后继续评估。

本条不是要求所有项目无条件配置 Authority registry：

- product expectation 和 dimension 来自基线 Judge investigation contract；
- 项目没有 AuthorityAnalysis 时使用规范化空 snapshot；
- `judgment_kind` 是当前原子判断类型，不是 Authority 专属字段；
- Authority routing 只在项目实际存在 AuthorityAnalysis 时生效。

## 6.2 多轮和重新规划

允许创建新 Plan 的原因：

- 用户提供新输入；
- reference 发生版本化更新；
- 项目合同或 Solidify receipt 正式更新；
- Authority snapshot 正式更新。

不允许创建新 Plan 的原因：

- 只因为看到了 actual；
- 只因为 Comparator 发现偏差；
- 只为了把 `not_evaluable` 改成更肯定的状态。

新 Plan 必须有新的 `plan_id` 和 snapshot/hash。旧 Plan、旧 assessment 和旧
GateDecision 必须保留，不能原地覆盖。

## 6.3 actual 为空

沿用基线三态语义：

- Live 应输出但明确没有输出：通常是 `not_fulfilled`；
- 系统无法取得或确认 actual：`not_evaluable`；
- 当前 Case 不适用某产品期望：不生成对应验收项。

Authority Gate 不得覆盖这些边界。

## 6.4 Authority 导致的 not_evaluable

每个因 Authority 被约束为 `not_evaluable` 的 assessment，必须能够回答：

```text
哪个 case expectation 被影响？
它来自哪个 product expectation？
属于哪个 EvaluationDimension？
它的 judgment_kind 是什么？
哪个 AuthorityAnalysis 仍 unresolved？
实际加载了哪个 Role asset 和 revision？
本次 Plan 使用哪个 Authority snapshot？
缺少什么决定性证据？
Gate 修改前后的状态是什么？
```

审计只保存最小引用和结果转换，不复制 `source_claims`、`causal_chain`、
`evidence_ref_ids` 原文或完整调查目录。

---

# 第七章：client_search 完整业务案例

## 7.1 项目级调查

产品期望：

```text
BusinessExpectation:
  expectation_id = user-searches-right-customer-set
  desired_outcome = 用户得到符合搜索意图的客户集合
```

评估维度：

```text
EvaluationDimension:
  dimension_id = search-intent-preservation
  expectation_ids = [user-searches-right-customer-set]
```

Authority：

```text
AuthorityAnalysis:
  analysis_id = semantic-mapping-authority
  dimension_ids = [search-intent-preservation]
  judgment_point = “高净值客户映射到哪个字段和值？”
  anchor.status = unresolved
```

Solidify mapping：

```yaml
asset_id: client-search-semantic-mapping-limit
metadata:
  authority_sources:
    - semantic-mapping-authority
  dimension_ids:
    - search-intent-preservation
  judgment_kinds:
    - semantic_mapping
  authority_status: unresolved
  limitation_reason: 缺少业务术语表或用户确认，无法确定唯一字段映射。
  revision: 2b24c53
```

## 7.2 Pre-actual Plan

用户输入：

```text
搜索年龄大于 30 岁的高净值客户
```

Plan 必须拆成两个原子判断：

```python
FrozenExpectationPlan(
    plan_id="plan-001",
    trace_id="trace-001",
    expectations=(
        FrozenCaseExpectation(
            case_expectation=BusinessExpectation(
                expectation_id="case-age",
                blocking=True,
                acceptance_criteria=["actual 包含 age > 30"],
            ),
            product_expectation_id="user-searches-right-customer-set",
            evaluation_dimension_id="search-intent-preservation",
            judgment_kind="explicit_condition",
        ),
        FrozenCaseExpectation(
            case_expectation=BusinessExpectation(
                expectation_id="case-high-value",
                blocking=True,
                acceptance_criteria=["actual 正确表达高净值客户"],
            ),
            product_expectation_id="user-searches-right-customer-set",
            evaluation_dimension_id="search-intent-preservation",
            judgment_kind="semantic_mapping",
        ),
    ),
    authority_snapshot_sha256="authority-snapshot-001",
    plan_sha256="plan-sha-001",
)
```

Authority 匹配结果：

```text
case-age:
  dimension 匹配
  judgment_kind=explicit_condition 不匹配 Authority judgment_kinds
  → 不受 semantic-mapping Authority 影响

case-high-value:
  dimension 匹配
  judgment_kind=semantic_mapping 匹配
  → 依赖 semantic-mapping Authority
```

## 7.3 actual 和最终结果

actual：

```text
缺少 age > 30
使用 clientLevel=B
```

当前没有独立业务事实证明“高净值客户”应映射成哪个字段和值。

最终：

```text
case-age
  → not_fulfilled
  → 用户明确要求 age > 30，但 actual 缺失

case-high-value
  → not_evaluable
  → semantic-mapping-authority unresolved
  → 当前 assessment 没有独立决定性证据
```

不得把两个结果合并成一个 `not_evaluable`。

## 7.4 当前 Case 有直接业务证据

如果用户或受信 current reference 在 actual 可见前明确声明：

```text
本次“高净值客户”指 clientLevel=A
```

并且产品合同认定它是当前 Case 的直接业务事实，则：

- `case-high-value` 仍是 `judgment_kind=semantic_mapping`；
- ToolResult/EvidenceRef 记录该 current user fact；
- runner provenance 标记 `evidence_status=decisive`；
- assessment 可以依据它判断 actual 为 `fulfilled` 或 `not_fulfilled`；
- 项目级 `semantic-mapping-authority` 仍然是 unresolved；
- 后续 Case 不能复用本次映射作为项目真相。

## 7.5 Comparator reference 不能自动成为 Authority

如果 reference 是由同一份未确认 `value_mappings` 或模型推断生成，它仍然依赖
unresolved Authority，不能因为 Comparator 得到 expected/actual 差异就把 evidence
标记为 decisive。

只有来源独立、在 Solidify 或产品合同中已经声明、且当前 Case 适用的决定性证据才能
使当前原子判断不再依赖未知 Authority。

## 7.6 查询等价性

actual 与 reference 查询形式不同，不等于结果集不同。若：

```text
evaluation_dimension_id = downstream-usability
judgment_kind = query_equivalence
```

对应 Authority unresolved，且没有同一数据快照上的封闭结果比较证据：

```text
query-equivalence expectation → not_evaluable
```

语法不同本身不能判 `not_fulfilled`，普通 semantic-mapping Tool 也不能越权证明
query equivalence。

---

# 第八章：实施任务

## Task 1：新增最小 Plan schema

- 新增 `FrozenCaseExpectation`；
- 修订 `FrozenExpectationPlan`；
- 从 Plan 和 LLM output 删除 Planner-owned `knowledge_scopes`；
- 增加 `authority_snapshot_sha256`；
- actual-free 地生成原子 expectation；
- canonical copy 并计算 plan hash；
- actual 可见后拒绝任何计划变更。

## Task 2：Solidify Authority mapping

- 复用基线 authority_anchors、RoleAssetMapping 和 Solidify receipt；
- 每个 AuthorityAnalysis 建立独立 mapping 和 runtime observable；
- 使用现有 `asset_id`，不新增第二个资产身份；
- 由 Solidify 编译 authority source/status、dimension、`judgment_kinds`、limitation
  和 revision；
- runtime directive 由状态和能力可用性派生；
- 不建立第二个 authority registry；
- Runtime 不读取完整 Investigation contract。

## Task 3：原子性和 Plan validator

- 校验 product expectation 和单个 dimension 引用；
- 校验 `judgment_kind` 来自稳定词表；
- 拒绝 acceptance criteria 与 `judgment_kind` 不一致；
- 拒绝把可产生不同三态的条件合并成一个 expectation；
- 明确 blocking 和 OR/替代关系边界；
- 根据 dimension + `judgment_kind` 独立推导适用 Authority；
- 校验 Authority snapshot 和 plan hash；
- 不依赖 Planner 自报任何 Authority selection 判断 Authority 是否适用。

## Task 4：Comparator 和 evidence provenance

- Comparator 在 Plan 冻结后执行；
- Comparator 只为已有 expectation 产出证据；
- Tool runner 根据 Solidify receipt 附加最小 runtime metadata；
- EvidenceRef 绑定具体 expectation；
- 删除 `authority_resolutions` 自报协议和 `resolved_for_current_case` 状态；
- Tool 成功与事实充分必须分别判断。

## Task 5：确定性 Authority Gate

- 在 assessment 后、overall 聚合前执行；
- 按 `FrozenCaseExpectation` 局部处理；
- unresolved 且依赖成立、无独立决定性证据时收敛为 `not_evaluable`；
- 保留独立证据证明的直接 `not_fulfilled`；
- 复用 GateDecision 输出最小审计；
- 项目 reconcile 不得二次执行 Authority 判断。

## Task 6：client_search 迁移

- 将混合 acceptance criteria 拆成原子 FrozenCaseExpectation；
- 为 semantic mapping、enum legality、query equivalence 等固化稳定
  `judgment_kind`；
- 删除 runtime Investigation 读取和重复 authority registry；
- 将 Tool provenance 前移到 Solidify receipt 和 runner；
- 保留 Current 作为对照，不直接 Promotion。

## Task 7：回归测试

至少覆盖：

1. actual 前冻结，actual 后不能改变 expectation、blocking、dimension、
   `judgment_kind` 或 Authority snapshot；
2. Plan 不能通过漏报或伪造 `judgment_kind` 绕过 Gate；
3. 明确字段缺失与 unresolved semantic mapping 得到两个独立状态；
4. unresolved 只影响 dimension + `judgment_kind` 匹配的原子项；
5. 同 dimension、不同 `judgment_kind` 不互相污染；
6. 未登记 Tool、普通 evidence 和 LLM 文本不能解除限制；
7. Tool `succeeded` 但事实不充分时仍保持 `not_evaluable`；
8. Tool 自己伪造 runtime metadata 被拒绝；
9. EvidenceRef 未绑定当前 expectation 时不能解除限制；
10. 当前 Case 直接业务证据可以支持本 Case 判断，但不修改项目 Authority；
11. resolved 静态规则在动态 Tool 不可用时仍可使用，未验证动态事实保持保守；
12. Solidify receipt 或 Authority snapshot 变化后旧 Plan 被拒绝；
13. Runtime payload 不包含 source claims、causal chain 或完整 Investigation；
14. Authority 导致的 `not_evaluable` 可以定位 product expectation、dimension、
    `judgment_kind`、Authority、asset、snapshot 和 original/final status；
15. Live 明确未交付应有输出时仍为 `not_fulfilled`；
16. OR/替代路径不能因为原子拆分被错误变成多个 blocking failure。

---

# 第九章：验收标准

完成本增量协议必须同时满足：

- 整体数据流遵从 `investigate-judge.md` 和 `investigate-judge-authority.md`；
- 只新增 `FrozenCaseExpectation` 和 `FrozenExpectationPlan` 两个内部 dataclass；
- 每个新增 schema 都有唯一业务职责，没有复制 Authority、Evidence 或 Gate；
- 产品级 BusinessExpectation 与当前 Case runtime BusinessExpectation 没有混用；
- `FrozenCaseExpectation` 明确串联 product expectation、dimension、当前 Case
  acceptance criteria 和 `judgment_kind`；
- `FrozenExpectationPlan` 在 actual 前冻结原子判断和 Authority snapshot；
- 当前 Case expectation 真正原子化，单项只产生一个三态；
- `judgment_kind` 取代含义模糊的 `coverage_keys`，且一个原子项只能有一个；
- Authority source/status 只有 Investigation → Solidify 一条真相来源；
- 直接复用 `RoleAssetMapping.asset_id`，不新增第二个资产身份；
- Runtime 不读取完整 Investigation，也不建立第二套 authority registry；
- 当前 Case 证据不修改项目级 Authority 状态；
- Tool 不能通过自己的 outputs 或 runtime metadata 自授权；
- unresolved Authority 从提示语提升为确定性、局部、单向的结果约束；
- 直接缺失、错误和越界不会被 Authority 错误改成 `not_evaluable`；
- Authority 限制原因通过 GateDecision 和 JudgeResult evidence 可定位；
- 公共 FulfillmentAssessment、JudgeResult、三态和 overall 聚合协议不变；
- adversarial 回归覆盖历史上的全局扩散、Planner 绕过、Tool 自授权、
  snapshot 漂移、OR/blocking 误拆和 `not_fulfilled` 逃逸；
- Current/Draft 只有在独立业务对照证明准确性提升且无明显退化后，才允许提出
  Promotion。

本文与两份基线的关系是“继承并补充”，不是“冲突并替代”。
