# Judge Pre-Actual Plan 与 Authority Solidify 增量协议

本文只修改 Judge 的运行时数据流，作为以下两份基线规范的增量：

- `spec/alg/investigate-judge.md`
- `spec/alg/investigate-judge-authority.md`

两份基线规范中的调查合同和公共 Judge schema 继续有效。本文只新增一个内部
dataclass，并规定它如何与现有 schema 和 Solidify 资产串联：

```text
AuthorityAnalysis
    ↓ Harness AI 在 Solidify 阶段落实
ContextUnit / VerifiableTool
    +
RoleAssetMapping.metadata / ContextUnitRecord.tags
    ├── scopes
    ├── dimensions
    ├── coverage_keys
    ├── authority_status
    ├── authority_sources
    ├── resolution_tool_ids
    ├── runtime_directive
    └── revision
            ↓

RunTrace
  ├── pre-actual projection
  │       ↓
  │   FrozenExpectationPlan
  │     ├── expectations[*].boundary.evaluation_dimension_ids
  │     ├── expectations[*].boundary.coverage_keys
  │     └── knowledge_scopes
  │
  └── actual + Comparator / VerifiableTool ToolResult
          ↓
      FulfillmentAssessment[] 初始结果
          ↓
      Authority Applicability Gate
          ↓
      FulfillmentAssessment[] 最终结果
          ↓
      JudgeResult + authority gate audit
```

本文不修改：

- `JudgeInvestigationContract`
- `AuthorityAnalysis`
- `BusinessExpectation`
- `FulfillmentAssessment`
- `JudgeResult`
- 三态词表和 overall 聚合协议

本文中的“计划”是当前 Case 的验收标准；Authority 的运行时形态继续使用
Solidify 已有的 ContextUnit、VerifiableTool、候选 Role 和 receipt，不新增第二套
Knowledge schema。

---

# 第一章：业务不变量

## 1.1 标准必须先于 actual

Judge 必须在当前 Case 的 actual 首次可见前确定：

- 当前 Case 适用哪些产品级业务期望；
- 要检查哪些原子结果；
- 每项验收标准；
- 每项 `blocking`；
- 当前判断需要哪些固化资产 scope。

actual 首次可见后，任何组件都不得：

- 新增、删除、合并或拆分 expectation；
- 修改验收标准；
- 修改 `blocking`；
- 让 Comparator 反向创建新的业务标准。

这条规则的业务意义是保证 Judge 先写评分标准，再看被评估系统的答案。

## 1.2 Authority 是 Solidify 的可复用资产，不是 Case 审批

`AuthorityAnalysis` 是项目级调查结果。它不能要求 LLM 为每条 Case 填写
`authority_analysis_ids`，也不能作为完整调查 JSON 直接进入 Prompt。

Harness AI 在 Solidify 阶段根据 `AuthorityAnalysis` 做工程判断，并将调查结果落实到
现有固化资产：

- 静态规则注册为有 Role 权限的 ContextUnit；
- 动态事实能力复用、包装或新建 VerifiableTool；
- 候选 Judge 通过现有扩展点消费这些资产；
- unresolved 只保留为有限范围的限制说明；
- Solidify receipt 记录“调查来源 → 固化资产 → runtime observable”。

Runtime 不读取完整 `AuthorityAnalysis`，也不执行 Solidify。

## 1.3 直接事实、未知事实和外部约束必须区分

- actual 明确缺少用户要求：通常是 `not_fulfilled`；
- actual 无法取得或无法确认：通常是 `not_evaluable`；
- Authority 只解决业务标准或外部事实问题，不能把所有缺失都改成
  `not_evaluable`；
- 内部配置、模型常识和当前 Comparator 结果不能自动成为未确认业务事实的替代品。
- 因 Authority 限制而产生的 `not_evaluable` 必须能从对应
  `FulfillmentAssessment` 定位到受限 scope、业务原因、固化资产和来源
  `AuthorityAnalysis`；不能只留下不可审计的自然语言总结。

---

# 第二章：最小 dataclass schema

本文只新增以下一个 dataclass。其余阶段使用已有 schema、普通函数参数或已有
审计 artifact，不再新增中间业务对象。

## 2.1 `FrozenExpectationPlan`

```python
from dataclasses import dataclass
from typing import Any

from impl.core.schema import BusinessExpectation


@dataclass(frozen=True)
class FrozenExpectationPlan:
    """actual 可见前封存的当前 Case 验收计划。"""

    plan_id: str
    trace_id: str

    # 复用现有 runtime BusinessExpectation。
    # 实现必须在封存时做 canonical copy，不得暴露可变原对象。
    expectations: tuple[BusinessExpectation, ...]

    # 计划所需的已注册 ContextUnit / VerifiableTool scope。
    # 这是能力/主题标识，不是 per-case authority ID。
    knowledge_scopes: tuple[str, ...]

    # 对不含 actual 的 canonical plan payload 计算。
    plan_sha256: str
```

### 字段业务意义

- `plan_id`：本次封存计划的身份；
- `trace_id`：计划属于哪次 Case；
- `expectations`：本 Case 最终要检查什么，以及每项的验收标准和
  `blocking`；
- `knowledge_scopes`：评估这些 expectation 需要哪些已固化知识；
- `plan_sha256`：证明 Assessment 使用的是同一份计划。

`FrozenExpectationPlan` 不复制产品级 `BusinessExpectation` 调查对象。它只保存
当前 Case 由用户请求、产品合同和评估维度投影出的 runtime expectation。

## 2.2 Authority 的运行时形状不是新增 dataclass

`AuthorityAnalysis` 的运行时落地继续使用现有资产和协议：

```text
AuthorityAnalysis
  ├── 静态、已确认的规则
  │     → 现有 ContextUnit / Context builder
  ├── 需要读取当前事实的能力
  │     → 现有 VerifiableTool / ToolImplementationRef
  ├── 仍未确认的问题
  │     → 有限 ContextUnit 限制说明，或保留 unresolved
  └── 所有映射
        → 现有 Solidify receipt
```

每个由 Authority 固化而来的资产必须在现有 `RoleAssetMapping.metadata` 中注册
以下信息，并在注册为 `ContextUnitRecord` 时保留到 `tags`：

```yaml
metadata:
  scopes:
    - client_search.authority.semantic-mapping
  dimensions:
    - search-intent-preservation
  coverage_keys:
    - semantic_mapping
  authority_status: unresolved
  authority_sources:
    - semantic-mapping-authority
  runtime_directive: not_evaluable_when_required
  limitation_reason: 缺少业务术语表或用户澄清，无法确认口语概念的唯一字段映射。
  revision: 2b24c53
```

字段业务意义：

- `scopes`：`FrozenExpectationPlan` 用什么稳定标识选择该资产；
- `dimensions`：资产服务哪些评估问题；
- `coverage_keys`：资产具体约束这些维度中的哪类原子验收项；
- `authority_status`：来源 Authority 当前是 `resolved` 还是 `unresolved`；
- `authority_sources`：来源 `AuthorityAnalysis.analysis_id`；
- `runtime_directive`：匹配到当前 expectation 后采用的确定性动作；
- `limitation_reason`：面向业务人员解释当前无法确认什么；
- `revision`：本次判断采用的固化资产版本。

这些字段是已有 Role asset 和 ContextUnit 的注册元数据，不是第二套 Knowledge
schema。`authority_status` 不得由 runtime 解析 ContextUnit 自由文本推断；
`limitation_reason` 不能代替结构化的 status、scope、dimension 和 coverage 注册。

`resolution_tool_ids` 不是独立的运行时白名单。对每个
`authority_sources`，它必须同时满足：

```text
RoleAssetMapping.metadata.resolution_tool_ids
    ⊆ AuthorityAnalysis.tool_requirement_ids
    ⊆ InvestigationManifest.tool_requirements
```

并且被注册的 ToolRequirement 必须有可执行实现。这样当前 Case 的
`ToolResult.outputs.authority_resolutions` 才能沿
`AuthorityAnalysis → InvestigationManifest → Solidify Tool → Gate` 闭环；
未在调查合同中声明、未在 manifest 中实现或仅由模型/evidence 自报的 ToolResult
都无权解除 unresolved Authority。

Solidify 产物必须满足：

- runtime 可以按 `FrozenExpectationPlan.knowledge_scopes` 选择已注册资产；
- 资产保留 Authority 状态、来源、适用范围和 revision；
- unresolved 不生成肯定业务答案；
- ContextUnit、Tool 和候选 Judge 的真实加载/调用可被 receipt 或 runtime audit 观察；
- runtime 不读取完整调查包。

---

# 第三章：现有 schema 与新增 schema 的数据流

## 3.1 `RunTrace → FrozenExpectationPlan`

Core 从现有 `RunTrace` 构造 pre-actual 输入，使用 allowlist，而不是先序列化
完整 Trace 再删除字段。

允许使用：

- Case identity；
- 当前用户请求和允许的 reference；
- `JudgeInvestigationContract` 的最小业务投影；
- Live output contract；
- 稳定项目 Context；
  - 已经注册的 ContextUnit/VerifiableTool scope 列表。

禁止使用：

- `raw_response`；
- `extracted_output`；
- final output；
- actual 派生的 `wrong/missing/extra`；
- Comparator 结果；
- 当前 Case 的成功/失败标签；
- 当前 Case 的历史 verdict。

Core 调用以下逻辑，调用可以由确定性代码或独立 Planning LLM 实现：

```python
def build_frozen_expectation_plan(
    trace: RunTrace,
    contract: JudgeInvestigationContract,
) -> FrozenExpectationPlan:
    ...
```

冻结前必须验证：

- `expectations` 非空；
- expectation ID 唯一；
- 每项引用合法的产品期望和评估维度；
- 每项使用项目注册的 `coverage_keys` 描述它覆盖的原子业务语义；
- 每项有明确验收标准；
- `blocking` 是明确布尔值；
- 用户请求中的关键条件、组合关系和禁止额外约束均被覆盖；
- `knowledge_scopes` 只包含项目已注册的 scope；
- canonical plan payload 不包含 actual 或 actual 派生字段。

覆盖检查属于 Plan validator，不新增 `IntentAtom` schema。若当前项目无法证明
用户要求已被覆盖，Plan 必须失败并返回公共 `not_evaluable`，不得以空计划或
事后补 expectation 继续执行。

`coverage_keys` 必须来自项目业务合同或 Solidify 注册元数据中的稳定词表，不能由
Planning LLM 为单个 Case 临时发明。它只描述原子验收语义，例如
`explicit_conditions`、`boolean_logic`、`no_unexpressed_constraints`、
`semantic_mapping`，不描述 actual 的对错。

## 3.2 `AuthorityAnalysis → Solidify 资产`

Harness AI 在 Solidify 阶段逐项处理调查阶段已有的 `AuthorityAnalysis`，并决定
使用现有 ContextUnit、VerifiableTool、候选 Judge 代码中的哪一种或多种落地方式。
这不是 runtime API，也不是从 JSON 机械生成代码的编译器。

### resolved Authority

如果结论是静态、已确认的规则，Solidify 可以注册为 ContextUnit，并保留：

- source Authority ID；
- scope、dimension 和 coverage；
- `authority_status=resolved`；
- 适用范围和禁止外推范围；
- source revision；
- 成功加载的 runtime observable。

如果结论需要当前 Case 的动态事实，Solidify 必须复用、包装或新建
VerifiableTool，并记录 ToolImplementationRef。Tool 不得执行开放式调查。

### unresolved Authority

Solidify 不得生成肯定业务答案。可以注册一份有限的 ContextUnit 限制说明，
也可以保留 unresolved 并让候选 Judge 按协议返回 `not_evaluable`。限制说明必须
明确：

- 当前无法确认什么；
- 哪类判断因此受限；
- 哪些直接事实仍然可以判断；
- 需要什么新证据才能解除限制。

对应资产必须注册 `authority_status=unresolved`、有限的 `coverage_keys`、
`runtime_directive=not_evaluable_when_required` 和面向业务的
`limitation_reason`。不得把 unresolved 直接转换成“整个维度不可评估”。

如果某项 unresolved Authority 可以由当前 Case 的动态事实解除，资产还必须显式
注册 `resolution_tool_ids`。其业务含义是“哪些已固化 Tool 有权为当前 Case
补齐这项事实”，不是“哪些 Tool 可以修改 Judge 结果”。未注册 Tool、模型文字和
普通 evidence 都无权解除限制。

### scope 约束

Solidify 资产使用项目声明的稳定 scope 元数据。Judge 只加载：

```text
FrozenExpectationPlan.knowledge_scopes
    ∩
Role 已注册资产的 scope
```

被选资产仍须检查适用 dimension 是否与当前 expectation 的评估维度相交。
Judge 不需要知道调查过程，也不需要填写 Authority ID。

## 3.3 expectation 与 Authority scope 的适用关系

`FrozenExpectationPlan.knowledge_scopes` 只决定当前 Case 可以加载哪些资产，不足以
单独证明某条 expectation 依赖某个 Authority。适用关系必须由已有 schema 字段和
资产注册元数据共同确定：

```text
scope ∈ FrozenExpectationPlan.knowledge_scopes
    AND
expectation.boundary.evaluation_dimension_ids
    ∩ asset.metadata.dimensions ≠ ∅
    AND
expectation.boundary.coverage_keys
    ∩ asset.metadata.coverage_keys ≠ ∅
```

三层条件的业务意义分别是：

- scope：当前 Case 是否需要这类固化知识；
- dimension：该知识是否服务当前评估问题；
- coverage：该知识是否具体约束当前原子验收语义。

只满足 dimension、但 coverage 不相交时，不得影响该 expectation。同一个
dimension 中的明确条件遗漏和未确认语义映射必须能够得到不同结果。

Plan validator 必须确认：

- 每个 `knowledge_scope` 均已注册；
- 每个被引用 scope 均有非空 dimension 和 coverage 注册；
- expectation 使用的 coverage key 来自稳定注册词表；
- 当前 expectation 是否依赖 Authority 可以由上述交集规则确定；
- runtime 不需要 per-case `authority_analysis_ids`。

## 3.4 `FrozenExpectationPlan + Solidify 资产 + actual → JudgeResult`

actual 首次可见后，Core 才允许调用 Assessment：

```python
def assess_frozen_plan(
    plan: FrozenExpectationPlan,
    registered_context_and_tools: Any,
    actual: Any,
    evidence: tuple[Any, ...],
) -> JudgeResult:
    ...
```

Assessment 只能：

- 评估 `plan.expectations` 中已存在的 expectation；
- 使用与当前 scope、dimension 和 coverage 匹配的已注册 ContextUnit/VerifiableTool；
- 记录 fulfilled、not_fulfilled 或 not_evaluable；
- 记录 evidence 和 gaps；
- 生成现有 `JudgeResult`。

Assessment 不得：

- 新增 expectation；
- 修改 plan 中的 `blocking`；
- 修改验收标准；
- 读取完整调查包；
- 把 unresolved 限制当作已确认业务答案；
- 用内部配置或模型常识补造缺失 Authority；
- 把一个受限判断扩散到不依赖该知识的 expectation。

最终结果仍然使用既有公共 schema：

```text
FrozenExpectationPlan.expectations
    → JudgeResult.business_expectations

Assessment output
    → JudgeResult.fulfillment_assessments

现有聚合逻辑
    → JudgeResult.overall_fulfillment
```

## 3.5 Authority Applicability Gate

Assessment LLM 先为冻结的 expectation 生成初始 `FulfillmentAssessment[]`。
在公共 normalize/finalize 和 overall 聚合前，Core 必须执行确定性的 Authority
Applicability Gate：

```python
def apply_authority_constraints(
    plan: FrozenExpectationPlan,
    registered_assets: Any,
    protocol_tool_results: tuple[ToolResult, ...],
    assessments: list[FulfillmentAssessment],
) -> list[FulfillmentAssessment]:
    ...
```

该函数不是新增 schema，只负责连接已有
`FrozenExpectationPlan`、`ContextUnitRecord.tags` 和
`FulfillmentAssessment`。

Gate 必须：

- 只读取 `plan.knowledge_scopes` 选中的已注册资产；
- 按 3.3 的 scope、dimension、coverage 交集定位受影响 expectation；
- 对 `resolved` 资产不改写 assessment 状态，但在 assessment 上引用实际使用的
  Authority source、ContextUnit 和 revision；
- 对 `unresolved` 资产，先检查该资产 `resolution_tool_ids` 中的 Tool 是否返回
  当前 Case 的显式 resolution claim；
- 只有 ToolResult 执行成功，且 claim 的 scope、dimension、coverage 都覆盖当前
  适用交集时，才把该 Authority 视为 `resolved_for_current_case`；
- current-case resolution 不改写模型基于 Comparator 证据给出的 fulfilled /
  not_fulfilled 状态，但必须记录 Tool、resolution basis 与 Authority 来源；
- 对没有有效 current-case resolution、且当前判断确实依赖该 Authority 的
  assessment，确定性设置：
  - `status="not_evaluable"`；
  - `score=None`；
  - `confidence=None`；
  - 在 `actual_evidence` 写入业务限制原因；
  - 在 `evidence_refs` 写入来源 Authority、ContextUnit 和 revision；
- 不新增、删除、合并或修改 `BusinessExpectation`；
- 不影响 dimension 或 coverage 不匹配的 expectation；
- 不把可以由用户请求、actual 和 Comparator 直接证明的遗漏、额外条件、格式错误
  改成 `not_evaluable`。

current-case resolution 复用现有 `ToolResult.outputs`，不新增 schema。最小输出为：

```json
{
  "tool_id": "client_search.condition_compare",
  "status": "succeeded",
  "outputs": {
    "authority_resolutions": [
      {
        "scope": "client_search.authority.semantic-mapping",
        "dimension_ids": ["search-intent-preservation"],
        "coverage_keys": ["semantic_mapping"],
        "status": "resolved_for_current_case",
        "decisive": true,
        "basis": "current_oracle_expected_conditions"
      }
    ]
  }
}
```

这条 claim 只表示“当前 Case 已有足够依据判断”，不表示 actual 一定正确。
fulfilled / not_fulfilled 仍由冻结 expectation 与 expected/actual 对比决定。
例如当前用户确认或允许的 current oracle 明确给出期望字段映射时，Comparator
可以据此证明 actual 一致或不一致，并只解除
`semantic-mapping` 的当前 Case 限制；它不能证明两个不同下游查询形式的结果集
等价。`query-equivalence` 只能由已声明的同一快照结果比较 Tool 或封闭的业务等价
规则解除。没有 current oracle 或等价证据时不得产生 decisive claim。

Gate 改写后的 `FulfillmentAssessment[]` 才能进入现有 overall 聚合。项目
`reconcile_result()` 不得二次读取调查包或重新执行 Authority 判断。

---

# 第四章：Comparator 与运行时边界

## 4.1 Comparator 的职责

Comparator 是 evidence producer，不是 expectation producer。

它必须在 Plan 冻结后执行，并且只能对已有 expectation 产生：

- expected/actual 对比证据；
- wrong/missing/extra；
- evidence insufficiency；
- tool result。

Comparator 不得调用 `ensure_business_expectation()` 新增 blocking expectation。

任何“actual 当 expected”的兜底都必须删除。缺少 reference 或业务标准时，应由
Plan 阶段失败或 Assessment 返回 `not_evaluable`，不得伪造可比较的 expected。

## 4.2 Runtime Context 边界

Runtime 只能装载 Solidify 注册的 ContextUnit/VerifiableTool，不能把 Judge investigation 目录作为
目录型 mandatory Context 全量加载。

允许进入 Planning/Assessment Prompt 的是：

- 当前阶段允许的 `BusinessExpectation` 投影；
- 匹配的 ContextUnit 内容和已声明 Tool schema/结果；
- Live output contract；
- 合法的 actual/evidence；
- 已声明 Tool 的 schema 和结果。

禁止进入 Prompt 的是：

- 完整 `AuthorityAnalysis`；
- `source_claims`；
- `causal_chain`；
- `causal_reasoning`；
- 调查过程原文；
- 与当前 scope 无关的知识资产。

## 4.3 计划与知识的审计

不新增审计 dataclass。使用现有 artifact/receipt 机制记录：

- `trace_id`；
- `plan_id`；
- `plan_sha256`；
- planning input fingerprint；
- actual 首次可见阶段；
- 实际加载的固化资产 ID；
- 固化资产 → AuthorityAnalysis 来源映射；
- assessment 使用的 `plan_sha256`；
- 最终 evidence 引用。

审计记录不得把完整调查 JSON 复制进 runtime Prompt 或公共 `JudgeResult`。

如果 Authority Gate 将某条 assessment 收敛为 `not_evaluable`，必须同时使用现有
schema 字段记录两类证据。

`FulfillmentAssessment.actual_evidence` 面向业务解释“为什么当前不能判断”：

```json
{
  "kind": "authority_limitation",
  "scope": "client_search.authority.semantic-mapping",
  "authority_status": "unresolved",
  "affected_dimension_ids": ["search-intent-preservation"],
  "affected_coverage_keys": ["semantic_mapping"],
  "reason": "缺少业务术语表或用户澄清，无法确认高净值客户的唯一字段映射。",
  "runtime_directive": "not_evaluable_when_required"
}
```

`FulfillmentAssessment.evidence_refs` 面向审计定位“限制来自哪里”：

```json
{
  "ref_id": "authority:semantic-mapping-authority",
  "context_unit_id": "project.client_search.asset.judge_authority_semantic_mapping",
  "scope": "client_search.authority.semantic-mapping",
  "source_revision": "2b24c53"
}
```

`JudgeResult.evidence` 还必须记录 Gate 的结果转换，至少包括：

```json
{
  "source": "authority_gate",
  "trace_id": "case-001",
  "plan_id": "judge-plan:case-001",
  "plan_sha256": "...",
  "affected_assessments": [
    {
      "expectation_id": "interpret-high-net-worth",
      "scope": "client_search.authority.semantic-mapping",
      "authority_source": "semantic-mapping-authority",
      "original_status": "fulfilled",
      "final_status": "not_evaluable",
      "context_unit_id": "project.client_search.asset.judge_authority_semantic_mapping"
    }
  ]
}
```

`original_status` 与 `final_status` 必须同时存在，使 Review 能区分模型原始判断和
确定性 Gate 收敛。审计只保存最小引用、原因和转换，不复制 `source_claims`、
`causal_chain` 或调查正文。

---

# 第五章：失败处理

## 5.1 Planning 失败

以下任一情况发生时，Judge 以协议失败结束：

- pre-actual 输入无法证明不含 actual；
- Plan 为空；
- expectation ID 重复；
- dimension 或产品期望引用非法；
- 关键用户要求未覆盖；
- plan hash 无法稳定生成。

公共结果为 `overall_fulfillment.status="not_evaluable"`，不得由项目后处理补造
expectation 或 assessment 改成成功。

## 5.2 固化资产缺失

- 没有匹配固化资产，但当前判断是直接事实：继续正常判断；
- 缺少 resolved rule，且当前判断确实依赖该规则：`not_evaluable`；
- limitation 未覆盖当前判断：不得影响该判断；
- 动态 Tool 不可用：只影响依赖该动态事实的判断，不影响已确认的静态规则。

“当前判断确实依赖该规则”必须同时满足：

1. scope 位于 `FrozenExpectationPlan.knowledge_scopes`；
2. expectation dimension 与资产 dimension 相交；
3. expectation coverage 与资产 coverage 相交；
4. 资产 `authority_status=unresolved`，或所需动态 Tool 无法提供决定性事实；
5. 该结论无法仅凭用户请求、actual 和 Comparator 的直接事实可靠作出。

任一条件不满足时，Authority limitation 不得修改该 assessment。

## 5.3 actual 为空

- 能确认 Live 应交付结果但实际结果为空：通常 `not_fulfilled`；
- 无法取得或确认 actual：通常 `not_evaluable`；
- 两者不得混淆。

---

# 第六章：client_search 业务例子

用户请求：

```text
找 45 岁以上女性
```

Planning 在 actual 可见前生成：

```python
FrozenExpectationPlan(
    plan_id="...",
    trace_id="...",
    expectations=(
        BusinessExpectation(
            expectation_id="preserve-age-lower-bound",
            blocking=True,
            expected_outcome="保留用户明确表达的年龄下界",
            acceptance_criteria=["年龄下界没有遗漏、增加或改变"],
            boundary={
                "product_expectation_id": "find-target-customers",
                "evaluation_dimension_ids": ["search-intent-preservation"],
                "coverage_keys": ["explicit_conditions"],
            },
        ),
        BusinessExpectation(
            expectation_id="preserve-female-filter",
            blocking=True,
            expected_outcome="保留用户明确表达的女性条件",
            acceptance_criteria=["性别条件没有遗漏、增加或改变"],
            boundary={
                "product_expectation_id": "find-target-customers",
                "evaluation_dimension_ids": ["search-intent-preservation"],
                "coverage_keys": ["explicit_conditions"],
            },
        ),
        BusinessExpectation(
            expectation_id="preserve-condition-combination",
            blocking=True,
            expected_outcome="保持年龄和性别条件的组合关系",
            acceptance_criteria=["不得改变用户表达的 AND/OR/NOT 关系"],
            boundary={
                "product_expectation_id": "find-target-customers",
                "evaluation_dimension_ids": ["search-intent-preservation"],
                "coverage_keys": ["boolean_logic"],
            },
        ),
        BusinessExpectation(
            expectation_id="reject-unrequested-restriction",
            blocking=True,
            expected_outcome="不得增加用户未表达且会改变目标客户集合的限制",
            acceptance_criteria=["不得额外增加城市、等级等强约束"],
            boundary={
                "product_expectation_id": "find-target-customers",
                "evaluation_dimension_ids": ["search-intent-preservation"],
                "coverage_keys": ["no_unexpressed_constraints"],
            },
        ),
    ),
    knowledge_scopes=(
        "client_search.authority.query-equivalence",
        "client_search.authority.enum-values",
    ),
    plan_sha256="...",
)
```

如果 actual 只有女性条件：

```text
preserve-age-lower-bound = not_fulfilled
preserve-female-filter = fulfilled
preserve-condition-combination = not_fulfilled
reject-unrequested-restriction = fulfilled
overall = not_fulfilled
```

如果 actual 为年龄、女性和城市条件：

```text
reject-unrequested-restriction = not_fulfilled
```

即使年龄和性别两项都存在，也不能错误判定为通过。

## 6.1 unresolved 只限制真正依赖它的 expectation

用户请求：

```text
帮我找高净值客户，年龄 50 岁以上
```

当前项目尚未确认“高净值客户”应映射到客户等级、资产规模、收入还是保费规模，
因此 Solidify 资产注册为：

```yaml
metadata:
  scopes:
    - client_search.authority.semantic-mapping
  dimensions:
    - search-intent-preservation
  coverage_keys:
    - semantic_mapping
  authority_status: unresolved
  authority_sources:
    - semantic-mapping-authority
  runtime_directive: not_evaluable_when_required
  limitation_reason: 缺少业务术语表或用户澄清，无法确认高净值客户的唯一字段映射。
  revision: 2b24c53
```

Planning 在 actual 可见前冻结：

```python
FrozenExpectationPlan(
    plan_id="judge-plan:case-001",
    trace_id="case-001",
    expectations=(
        BusinessExpectation(
            expectation_id="preserve-explicit-age-condition",
            blocking=True,
            expected_outcome="保留用户明确表达的年龄条件",
            acceptance_criteria=["输出包含年龄大于等于 50 岁的等价条件"],
            boundary={
                "product_expectation_id": "find-target-customers",
                "evaluation_dimension_ids": ["search-intent-preservation"],
                "coverage_keys": ["explicit_conditions"],
            },
        ),
        BusinessExpectation(
            expectation_id="interpret-high-net-worth",
            blocking=True,
            expected_outcome="正确承接高净值客户这一业务概念",
            acceptance_criteria=[
                "映射得到业务术语表、用户澄清或其他有效 Authority 支撑"
            ],
            boundary={
                "product_expectation_id": "find-target-customers",
                "evaluation_dimension_ids": ["search-intent-preservation"],
                "coverage_keys": ["semantic_mapping"],
            },
        ),
    ),
    knowledge_scopes=(
        "client_search.authority.semantic-mapping",
    ),
    plan_sha256="...",
)
```

Live actual 为：

```json
{
  "query_logic": "AND",
  "conditions": [
    {"field": "clientLevel", "operator": "eq", "value": "VIP"}
  ]
}
```

Comparator 可以直接证明年龄条件缺失，但不能证明 `clientLevel=VIP` 是“高净值客户”
的权威映射。Authority Gate 分别计算：

```text
preserve-explicit-age-condition:
  dimension 相交
  coverage explicit_conditions ∩ semantic_mapping = ∅
  → 不受 unresolved Authority 影响
  → not_fulfilled

interpret-high-net-worth:
  scope 已被 Plan 选择
  dimension 相交
  coverage semantic_mapping ∩ semantic_mapping ≠ ∅
  authority_status = unresolved
  → not_evaluable
```

最终结果：

```text
preserve-explicit-age-condition = not_fulfilled
interpret-high-net-worth = not_evaluable
overall = not_fulfilled
```

`interpret-high-net-worth` 的 `actual_evidence` 必须说明缺少何种业务事实，
`evidence_refs` 必须定位到 `semantic-mapping-authority`、对应 ContextUnit 和
revision。年龄遗漏是直接事实，不得因为另一个语义映射 unresolved 而逃逸失败。

---

# 第七章：一次性改造任务

## Task 1：增加 `FrozenExpectationPlan`

- 增加 dataclass；
- 实现 pre-actual allowlist projection；
- 实现 canonical hash；
- 校验 expectation、dimension、coverage 和 blocking；
- 禁止 Assessment 修改计划；
- 保持公共 Judge schema 不变。

## Task 2：由 Solidify 落实 Authority 资产

- Harness AI 判断每个 resolved Authority 应注册为 ContextUnit、包装为
  VerifiableTool，还是由候选 Judge 逻辑消费；
- Harness AI 必要时编写 Context builder、Tool wrapper 或候选 Judge 代码；
- unresolved 不生成肯定业务答案，只保留有限限制或明确 unresolved；
- 为 Authority 资产注册 scope、dimension、coverage、status、source、directive、
  limitation reason 和 revision；
- 对可由当前 Case 动态事实解除的 Authority，注册唯一有权产生 resolution claim
  的 `resolution_tool_ids`；
- 将相同元数据保留到 `ContextUnitRecord.tags` 和 Solidify receipt；
- 使用现有 `role_assets`、Context、Tool 和 Solidify receipt；
- 禁止完整调查包进入 runtime；
- 禁止 runtime 要求 LLM 输出 Authority ID。

## Task 3：增加 Authority Applicability Gate

- 使用 scope、dimension、coverage 交集定位受影响 expectation；
- 对真正依赖 unresolved Authority 的 assessment 确定性收敛为
  `not_evaluable`；
- 不影响可由直接事实判断的 expectation；
- 在 `actual_evidence` 写入业务原因；
- 在 `evidence_refs` 写入 Authority、ContextUnit 和 revision；
- 在 `JudgeResult.evidence` 记录 original/final status；
- Gate 在 normalize/finalize 和 overall 聚合前执行；
- 项目 reconcile 不得二次读取调查包或重复执行 Gate。

## Task 4：调整 Comparator 顺序和权限

- Comparator 只能在 Plan 冻结后运行；
- Comparator 只能产生 evidence/gap；
- 删除事后 `ensure_business_expectation()`；
- 删除 actual-as-expected fallback。

## Task 5：调整 Context 装载

- Judge runtime 只加载 Solidify 注册且 scope/dimension/coverage 匹配的
  ContextUnit/Tool；
- investigation 目录不得作为全量 mandatory Context；
- 确认 Prompt 不包含完整调查字段。

## Task 6：更新 client_search

- 为当前四类 Authority 定义 scope；
- 为每类 Authority 注册适用 dimension、coverage、status、directive 和来源；
- resolved 生成规则，unresolved 生成限制；
- 不再使用 per-case `authority_analysis_ids`；
- 保留明确遗漏、额外条件、格式错误等直接判断能力。

## Task 7：增加回归测试

必须覆盖：

- actual 不进入 Planning 输入；
- Plan 为空、重复 ID、非法引用、coverage 不完整时失败；
- Plan hash 修改后 Assessment 拒绝；
- Comparator 不能新增 expectation；
- actual 缺少明确条件时判 `not_fulfilled`；
- 额外未表达条件不会漏判；
- unresolved scope 只影响 dimension 和 coverage 都匹配的 expectation；
- 同 dimension、不同 coverage 的 expectation 不受影响；
- Gate 不新增 expectation、不修改 frozen plan；
- Gate 写入可解释的 `actual_evidence` 和可定位的 `evidence_refs`；
- Gate audit 同时记录 original/final status；
- 已注册 ToolResult 的 scope-local resolution 可保留当前 Case 的肯定或否定判断；
- 未注册 Tool、失败/inconclusive ToolResult、scope/dimension/coverage 不匹配的
  claim 均不能解除 unresolved 限制；
- resolved 与 resolved-for-current-case 的 assessment 都引用 Authority 来源；
- resolved 固化资产可驱动真实判断；
- 未被 `plan.knowledge_scopes` 选择的 Authority 不得影响结果；
- runtime 不读取完整 AuthorityAnalysis；
- 空 actual 与 actual unavailable 分别处理。

---

# 第八章：验收标准

本次增量完成必须满足：

- Core 存在可复用的 `FrozenExpectationPlan`；
- Plan 在 actual 首次可见前完成并具有稳定 hash；
- Plan 覆盖当前用户的关键业务要求和关系；
- Assessment 只能引用已冻结 Plan；
- Comparator 不再创建 expectation；
- `AuthorityAnalysis` 能由 Harness AI 在 Solidify 阶段落实为可观察的
  ContextUnit、VerifiableTool 或候选 Judge 资产；
- Authority 固化资产具有可验证的 scope、dimension、coverage、status、source、
  directive 和 revision 注册元数据；
- 动态 Authority 解除路径通过资产 `resolution_tool_ids` 与现有 ToolResult
  明确串联；
- resolved 资产提供已确认规则，unresolved 只提供限制或保持不可评估；
- Authority Gate 能用 Plan scope 与 expectation dimension/coverage 精确定位
  受影响 assessment；
- 真正依赖 unresolved Authority 的 assessment 被确定性收敛为
  `not_evaluable`；
- 当前 Case 已由注册 ToolResult 明确补齐的 Authority 不再被错误收敛为
  `not_evaluable`，且 resolution claim 可审计；
- Authority 导致的 `not_evaluable` 能从 `actual_evidence` 看出业务原因，并从
  `evidence_refs` 定位来源 Authority、ContextUnit 和 revision；
- Gate audit 能区分模型原始状态和确定性收敛后的最终状态；
- Judge 不要求 LLM 输出 per-case Authority ID；
- 未确认语义不能由内部配置或模型常识补齐；
- 直接事实不会因为 Authority 未解决而被全局阻断；
- 完整 investigation 不进入 Planning 或 Assessment Prompt；
- 现有 `JudgeResult`、`BusinessExpectation`、`FulfillmentAssessment` 和三态聚合保持不变；
- Current/Draft 只有在独立业务对照证明准确性提升且无明显退化后，才允许提出 Promotion。

---

# 第九章：与基线冲突的替代关系

本文对基线中以下运行时约定作增量替代：

1. 基线中通过每条 expectation 的 `authority_analysis_ids` 进行运行时绑定的做法，
   改为 `FrozenExpectationPlan.knowledge_scopes` 选择资产，再通过 expectation
   dimension/coverage 与资产 dimension/coverage 的交集确定适用关系；
2. 基线中把 unresolved 直接扩散为整个 dimension `not_evaluable` 的做法，
   改为由 Authority Applicability Gate 只限制 scope、dimension、coverage 均匹配的
   assessment，并记录业务原因和来源；
3. 基线中将完整调查目录作为 runtime Context 的做法，改为只加载 Solidify 后的
   Solidify 注册的 ContextUnit/VerifiableTool；
4. 基线中允许 Comparator 或项目后处理在 actual 后补充 expectation 的做法，改为
   Plan 冻结后只允许产生 assessment evidence。

除此之外，基线调查流程、AuthorityAnalysis 调查 schema、公共 JudgeResult 和
Current/Draft/Promotion 协议均不变。
