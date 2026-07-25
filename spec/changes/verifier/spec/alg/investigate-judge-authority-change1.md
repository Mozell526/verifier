# Judge Pre-Actual Expectation 与 Authority Applicability 协议

本文是 `spec/alg/investigate-judge.md` 与
`spec/alg/investigate-judge-authority.md` 的增量变更规范，解决两个相互关联的
Judge 可信度问题：

1. 当前 Case 验收项和 `blocking` 可能在 Judge 已看到 actual 后才生成；
2. authority applicability 缺失、错误或未知时，Judge 仍可能继续给出确定结论。

本文不改变 `InvestigationManifest`、`JudgeResult`、`BusinessExpectation`、
`FulfillmentAssessment` 或三态聚合的公共 schema。新增对象属于 Judge 内部运行时
治理和审计边界。发生歧义时，以本文对 pre-actual 冻结和 authority fail-closed 的
要求为准，其余流程继续遵守原协议。

---

# 第一章：Spec 标准——最终长期协议

## 1.1 目标

Judge 必须在不知道当前 actual 内容和质量的前提下，先确定当前 Case 要检查什么；
actual 可见后，Judge 只能依据已经冻结的验收项进行评估，不能重新定义验收标准。

当某个判断依赖枚举现实、业务语义、查询等价性、责任边界或其他 AuthorityAnalysis
时，是否适用以及依赖哪个 authority 不能由 LLM 自报后直接生效。核心运行时必须
验证 applicability；无法证明“不需要 authority”时，缺失、未知或错误绑定必须
保守落为 `not_evaluable`，不得静默继续判断。

长期运行链路为：

```text
项目级 Judge Investigation
  ├── BusinessExpectation
  ├── LiveBoundary
  ├── EvaluationDimension
  └── AuthorityAnalysis
          ↓ Solidify 最小投影
Case 输入 + reference + 输出合同（不含 actual）
          ↓ Phase 1: Expectation Planning
FrozenExpectationPlan
          ↓ 冻结并记录 plan hash
actual + 合法外部证据
          ↓ Phase 2: Assessment
JudgmentClaim[]
          ↓ Project AuthorityApplicabilityResolver / Comparator
AuthorityApplicabilityDecision[]
          ↓ Core Authority Gate
FulfillmentAssessment[]
          ↓ 现有公共聚合
JudgeResult
```

## 1.2 核心不变量

### 1.2.1 评分标准先于答案

- Phase 1 不得读取当前 Case 的 `raw_response`、`extracted_output`、最终 output、
  actual 派生日志或 comparator 结果；
- 当前 Case 原子验收项、`blocking`、关联产品期望和评估维度必须在 Phase 1 冻结；
- Phase 2 不得新增、删除、合并、拆分或修改冻结的验收项，也不得修改 `blocking`；
- Prompt 中写“请先确定 blocking”不能替代代码级输入隔离、对象冻结和审计；
- actual 为空或 schema 非法是 Phase 2 的事实，不得被用来改变 Phase 1 的验收计划。

### 1.2.2 看不到答案不等于不知道输出格式

Phase 1 可以看到稳定的输出合同知识，包括：

- Live output JSON Schema；
- 字段、值类型、操作符和结构约束；
- capability manifest；
- 下游消费协议；
- 项目级 BusinessExpectation、LiveBoundary 和 EvaluationDimension 的最小投影；
- 与当前 Case actual 无关的通用格式示例；
- 当前 Case 用户请求，以及项目协议明确允许的 reference。

Phase 1 不得看到：

- 当前 actual 的字段、值或输出片段；
- 从 actual 计算出的 `wrong`、`missing`、`extra`、相似度或 verdict；
- 当前业务执行的成功/失败标签；
- 能够反推出当前 actual 质量的 comparator、review 或历史结论。

输出 schema 描述“答案应采用什么格式”，actual 描述“本次实际答了什么”。前者必须
提供给 Phase 1，后者必须隔离到 Phase 2。

### 1.2.3 Authority applicability 必须 fail-closed

每个对 assessment 有决定作用的 JudgmentClaim 必须得到一个结构化 applicability
decision，状态只能是：

- `required`：该判断依赖一个或多个 AuthorityAnalysis；
- `not_required`：该判断是无需外部权威即可确认的直接事实，并有确定性依据；
- `unknown`：当前无法证明是否需要 authority，或无法可靠解析其依赖。

处理规则：

```text
required + 合法 resolved authority
  → 允许使用已验证锚点判断

required + unresolved authority
  → 关联 assessment = not_evaluable

required + 动态验证能力不可用
  → 不得假设 case 级动态事实；按 authority directive 保守处理

required + 空 ID / 未知 ID / 维度不相交
  → authority binding error；关联 assessment = not_evaluable

unknown
  → 关联 assessment = not_evaluable

not_required + 可信确定性依据
  → 允许直接判断

not_required + 仅有 LLM 文本声明
  → 不接受；规范化为 unknown
```

空 authority 列表不能同时代表“确定不需要”和“调用方漏填”。没有显式、可验证的
`not_required` decision 时，空绑定必须按 `unknown` 处理。

## 1.3 职责边界

### 1.3.1 Core Judge Runtime

核心层负责：

- 构造不含 actual 的 Phase 1 输入视图；
- 校验、冻结和哈希 ExpectationPlan；
- 确保 Phase 2 只能引用冻结计划；
- 定义 AuthorityApplicabilityDecision 状态机；
- 校验 product expectation、dimension 和 authority ID；
- 校验 authority 与 dimension 的作用域相交；
- 对 missing、unknown、非法绑定和 unresolved 执行统一 fail-closed；
- 记录 plan、assessment 与 authority decision 的审计关系；
- 最终组装现有公共 `JudgeResult`。

核心层不得写死某个项目的字段、枚举、口语映射或查询等价规则。

### 1.3.2 Project Judge / Comparator

项目层负责：

- 提供当前项目的输出 schema、能力清单和下游协议；
- 将当前用户需求实例化为项目可理解的验收内容；
- 在 Phase 2 将比较过程表达为结构化 JudgmentClaim；
- 根据真实采用的判断依据解析 authority applicability；
- 将语义映射、枚举合法性、查询等价性等判断映射到对应 authority ID；
- 为 `not_required` 提供项目代码或 Comparator 产生的确定性 basis。

项目层不得决定“非法 binding 也继续放行”，不得用空列表绕过核心门禁。

### 1.3.3 Draft Skill

Draft Skill 负责 Investigate、Solidify 和 Draft Loop 治理：

- 检查 AuthorityAnalysis 与 EvaluationDimension 的覆盖关系；
- 检查项目是否提供 authority applicability resolver 或等价 Comparator 输出；
- 检查 Solidify 是否只投影最小稳定运行时内容；
- 检查 smoke 覆盖 `required`、`not_required`、`unknown`、未知 ID、错维度；
- 检查 candidate 是否真实经过 ExpectationPlan 冻结和 Core Authority Gate；
- 在 Draft Review 中拒绝“未绑定 authority 却给确定 verdict”的结果；
- 在冻结 Current/Draft 数据上证明改善且无退化。

Draft Skill 不参与每个线上 Case 的实时 applicability 裁决，也不能用 review 文本替代
核心运行时门禁。

### 1.3.4 Investigation 与 Solidify

Investigation 继续保存完整业务合同、因果链和证据。Solidify 只生成运行时需要的：

- 产品期望和评估维度的最小投影；
- authority anchor 的 ID、dimension scope、status、directive 和可用验证接口；
- 项目 applicability resolver 所需的稳定映射；
- ContextUnit、Comparator 或 VerifiableTool。

完整 `AuthorityAnalysis`、`source_claims`、`causal_chain`、`causal_reasoning` 和调查过程
证据不得注入 Phase 1 或 Phase 2 Prompt。

## 1.4 内部运行时 Schema

以下 schema 是内部治理对象，不加入公共 `JudgeResult`。

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class FrozenExpectationPlan:
    schema_version: int
    plan_id: str
    project_id: str
    trace_id: str

    # 只基于 pre-actual 输入计算；用于证明计划没有事后变化。
    planning_input_sha256: str
    items: tuple[CaseExpectationPlanItem, ...]

    # 对 canonical plan payload 计算，不包含 actual。
    plan_sha256: str


@dataclass(frozen=True)
class CaseExpectationPlanItem:
    case_expectation_id: str

    # 对应调查合同中的产品级 BusinessExpectation。
    product_expectation_id: str

    # 对应调查合同中的 EvaluationDimension。
    evaluation_dimension_ids: tuple[str, ...]

    expected_outcome: str
    acceptance_criteria: tuple[Any, ...]
    blocking: bool

    # 由 dimension coverage 得到的可能 authority 集合，不代表全部必然适用。
    authority_candidate_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class JudgmentClaim:
    claim_id: str
    case_expectation_id: str
    evaluation_dimension_ids: tuple[str, ...]

    # 项目定义的结构化判断类型，例如 direct_missing_condition、
    # semantic_mapping、enum_legality、query_equivalence。
    claim_kind: str
    proposed_status: Literal["fulfilled", "not_fulfilled", "not_evaluable"]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class AuthorityApplicabilityDecision:
    claim_id: str
    status: Literal["required", "not_required", "unknown"]
    authority_analysis_ids: tuple[str, ...]

    # 必须来自 core、项目 resolver、Comparator 或 VerifiableTool 的结构化输出。
    # LLM 自由文本不能单独成为可信 basis。
    basis_type: Literal[
        "core_direct_fact",
        "project_resolver",
        "comparator_result",
        "tool_result",
        "unverified_llm_claim",
    ]
    basis_ref_ids: tuple[str, ...]
    reason: str = ""
```

## 1.5 Phase 1：Expectation Planning

### 1.5.1 输入

核心层必须从 RunTrace 构建专用 `JudgePlanningInputView`。该视图只包含：

- case identity；
- 当前用户请求、对话上下文和允许的 reference；
- 产品级业务合同和 LiveBoundary 最小投影；
- EvaluationDimension；
- Live output schema 与下游协议；
- 字段能力和稳定 ContextUnit；
- authority analysis ID、dimension scope 和 status 的最小目录。

构造器必须以 allowlist 选择字段，不能先序列化完整 RunTrace 再删除少数字段。

### 1.5.2 输出与验证

Phase 1 输出 CaseExpectationPlanItem。核心层必须检查：

- 验收项非空、ID 唯一且原子；
- 每项引用存在的产品期望；
- 每项至少引用一个合法 EvaluationDimension；
- dimension 确实服务对应 product expectation；
- `blocking` 是明确布尔值；
- authority candidate 只能来自关联 dimensions 的 AuthorityAnalysis；
- plan 不含 actual、assessment、verdict、wrong/missing/extra；
- plan 可以稳定序列化并计算 `plan_sha256`。

验证通过后计划冻结。任何后续组件只能按 `plan_id + plan_sha256` 引用，不能持有可变
对象并原地修改。

### 1.5.3 失败处理

Phase 1 调用失败、计划为空、引用非法或无法证明输入未包含 actual 时，本次 Judge 必须
以协议失败结束并返回 `not_evaluable`。项目后处理不得补造验收项把失败改成成功。

## 1.6 Phase 2：Assessment

Phase 2 输入包括：

- FrozenExpectationPlan；
- 当前 actual；
- 允许的外部证据和 ToolResult；
- Phase 2 可用的 Comparator；
- 最小 authority anchors。

Phase 2 输出 JudgmentClaim 和候选 assessment，不得输出或修改 expectation plan。

Comparator 必须在计划冻结后运行。其结果必须引用一个冻结的
`case_expectation_id`，不能通过比较 actual 后新增验收项。

如果 actual 为空：

- Live 按合同应交付结果且能够确认实际为空，属于直接事实，可对相关计划项产生
  `direct_missing_output` claim，通常为 `not_fulfilled`；
- 无法取得或确认 actual，产生 `actual_unavailable` claim，通常为
  `not_evaluable`；
- 两者不得混淆。

## 1.7 Authority Applicability Resolver

### 1.7.1 两阶段 authority 信息

Phase 1 只能声明某验收项的 `authority_candidate_ids`。最终是否需要某个 authority，
可能取决于 Phase 2 实际使用的判断方式。例如：

- actual 完全缺少用户明确要求的条件，可由直接缺失事实判断；
- actual 使用了口语别名，需要语义映射 authority；
- actual 使用某枚举值，需要枚举现实 authority；
- actual 与 reference 形式不同但可能等价，需要查询等价性 authority。

因此最终 applicability 可以在 actual 可见后解析，但它只能决定“是否有足够依据评价
已冻结验收项”，不能修改验收项本身。

### 1.7.2 Resolver 接口

项目 resolver 接收：

```text
FrozenExpectationPlan item
+ JudgmentClaim
+ Comparator/Tool 的结构化 evidence
+ 当前可用 authority anchors
```

并返回 AuthorityApplicabilityDecision。Resolver 必须是项目注册的确定性代码、
Comparator 或 VerifiableTool；LLM 可以提出建议，但不能单独把 decision 提升为可信
`required` 或 `not_required`。

### 1.7.3 Core Authority Gate

核心门禁逐 claim 检查：

1. `required` 必须至少引用一个 authority；
2. authority ID 必须存在；
3. authority dimension scope 必须与 claim 和 plan item 相交；
4. authority 必须属于该 plan item 的 candidate coverage，或由受信 ToolResult 提供
   新的显式覆盖证据；
5. unresolved authority 按 directive 使相关 claim 不可评估；
6. resolved dynamic authority 缺少本次必要 ToolResult 时，不得假设动态事实；
7. `not_required` 必须具有非 LLM 的 basis type 和非空 basis refs；
8. `unknown`、非法 decision 或缺失 decision 一律不可评估；
9. 每个最终 assessment 必须能追溯到 plan item、claim 和 applicability decision。

当一个 assessment 依赖多个 claim 时，只要任一决定性 claim 为 `unknown`、非法或需要
unresolved authority，且其他证据不足以独立得出该 assessment，该 assessment 必须为
`not_evaluable`。不得用不相关 claim 的确定性覆盖权威缺口。

## 1.8 Client Search 规范示例

用户请求：

```text
找 45 岁以上女性
```

Phase 1 在看不到 actual 时冻结：

```json
{
  "items": [
    {
      "case_expectation_id": "preserve-age-lower-bound",
      "product_expectation_id": "find-target-customers",
      "evaluation_dimension_ids": ["search-intent-preservation"],
      "expected_outcome": "查询保留用户明确表达的年龄下界",
      "acceptance_criteria": ["年龄下界语义不被遗漏或改变"],
      "blocking": true,
      "authority_candidate_ids": ["semantic-mapping-authority"]
    },
    {
      "case_expectation_id": "preserve-female-filter",
      "product_expectation_id": "find-target-customers",
      "evaluation_dimension_ids": ["search-intent-preservation"],
      "expected_outcome": "查询保留女性筛选条件",
      "acceptance_criteria": ["性别条件语义与用户请求一致"],
      "blocking": true,
      "authority_candidate_ids": [
        "semantic-mapping-authority",
        "enum-value-authority"
      ]
    }
  ]
}
```

若 actual 只包含女性条件，Comparator 产生：

```json
{
  "claim_id": "age-condition-absent",
  "case_expectation_id": "preserve-age-lower-bound",
  "claim_kind": "direct_missing_condition",
  "proposed_status": "not_fulfilled",
  "evidence_refs": ["comparison:age-condition-absent"]
}
```

Resolver 返回 `not_required + comparator_result`，因为“用户明确要求的条件完全不存在”
无需解决枚举或同义映射问题。核心门禁允许 `not_fulfilled`。

若 actual 使用 `clientLevel=A` 表达“高净值客户”，Comparator 产生
`semantic_mapping` claim。Resolver 必须绑定 `semantic-mapping-authority`；若该 anchor
unresolved，最终 assessment 为 `not_evaluable`，不能因为空 binding 而保留
`fulfilled`。

## 1.9 Prompt 与调用边界

推荐使用两次独立结构化调用：

1. Planning call：只允许输出 FrozenExpectationPlan 的未哈希内容；
2. Assessment call：只允许输出 claims、assessments 和 gaps。

两次调用可以使用同一模型，但必须采用不同输入视图和不同 output schema。禁止依赖
单次 Prompt 中“请先思考 expectations，再看 actual”的文字顺序，因为模型在开始生成
前已经看到了全部输入。

为控制成本，可以：

- 对稳定的 schema、ContextUnit 和产品合同做缓存；
- 对相同请求/reference 指纹复用已验证 planning result；
- 对能由确定性代码实例化的验收项跳过 Planning LLM；
- 保持 Phase 2 只接收最小 plan 和 case evidence。

缓存键必须包含项目 revision、调查合同 revision、用户请求/reference 指纹和 planning
schema version。不得跨不兼容 revision 复用计划。

## 1.10 审计要求

每次 Judge 运行至少记录：

- planning input fingerprint；
- plan ID、plan hash 和生成时间；
- actual 首次可见的阶段；
- assessment 引用的 plan hash；
- 每个 claim 的 applicability status、authority IDs 和 basis refs；
- authority gate 的通过、降级或协议错误原因；
- 最终 assessment 到 plan item 的映射。

审计数据不得把完整 AuthorityAnalysis 注入 Judge Prompt。调查证据可通过独立 artifact
引用，不复制进 runtime result。

## 1.11 Validator、Solidify 与 Draft Review 门禁

### Validator

Validator 必须验证内部 schema、枚举、ID 唯一性和引用关系，但不假装用关键词检查代替
业务语义审查。

### Solidify

Solidify smoke 必须经过真实 project loader 和最终 Judge 输入构建链路，并验证：

- Planning 输入不含 actual 和 actual 派生结果；
- 最终 Prompt 不含完整调查字段；
- plan 在 Assessment 前被冻结；
- Assessment 不能修改 plan；
- required + resolved、required + unresolved、not_required、unknown 均按协议处理；
- 空 ID、未知 ID、错维度和仅 LLM 声明 not_required 均不能 fail-open；
- 项目 Comparator 输出真实 judgment claims 和 applicability basis。

### Draft Review

Judge Draft Review 必须检查：

- plan 是否由产品期望、当前请求和维度共同支持；
- plan 是否在 actual 前生成；
- blocking 是否被冻结；
- actual 是否只在 Phase 2 首次可见；
- authority applicability 是否覆盖每个决定性 claim；
- `not_required` 是否具有可信 basis；
- unresolved/unknown 是否保持 `not_evaluable`；
- Draft 是否相对 frozen Current 提升判断准确性且无可见退化。

## 1.12 长期验收标准

- 任何项目 Judge 都不能在同一次可见 actual 的调用中同时制定验收计划；
- Phase 1 知道输出合同但不知道当前 actual；
- FrozenExpectationPlan 具有稳定 hash，Phase 2 只能引用不能修改；
- Comparator 只能评估已冻结验收项，不能事后新增 blocking expectation；
- authority applicability 具有 `required/not_required/unknown` 三态；
- 空、未知和错维度 authority binding 不再静默放行；
- LLM 不能单独证明 `not_required`；
- unresolved authority 只影响实际依赖它的 claim，不全局污染无关验收项；
- 完整调查 JSON 不进入 Planning 或 Assessment Prompt；
- 现有 Judge 公共结果 schema 和三态聚合协议保持不变；
- Solidify 和 Draft Review 能用真实运行证据复核以上不变量。

---

# 第二章：Changes——现状差异与一次性改造任务

## 2.1 当前状态与目标差异

### 2.1.1 当前 expectation 与 assessment 未隔离

当前通用 Judge 在一次 `complete_json()` 调用中同时生成
`business_expectations` 和 `fulfillment_assessments`。该调用的 user payload 已包含
RunTrace actual，因此“在 actual 前确定 blocking”只是一条 Prompt 指令，没有代码级
隔离、冻结对象或审计证据。

`client_search` 还会在构建 Judge context 时提前运行 `condition_comparison`，使
`wrong/missing/extra` 等 actual 派生结果在 expectation 生成前可见。

项目 `reconcile_result` 中的 Comparator 可以在看到 actual 后调用
`ensure_business_expectation()` 新增 blocking expectation，进一步违反 pre-actual
要求。

### 2.1.2 当前 authority applicability 为 fail-open

现有 `enforce_authority_directives()` 只遍历 expectation boundary 中显式填写的
`authority_analysis_ids`：

- 空列表不会触发任何检查；
- 未知 authority ID 直接跳过；
- authority 与 dimension 不相交直接跳过；
- LLM 输出校验不验证 authority binding 的完整性和合法性。

`client_search` 的确定性 Comparator 又固定绑定
`authority_analysis_ids=[]`，但仍然可以生成 `fulfilled/not_fulfilled`。因此四个
unresolved anchor 只有在调用者正确自报 binding 时才生效，漏报和错报反而绕过保护。

### 2.1.3 当前 smoke 覆盖不足

现有 authority smoke 证明手工构造的合法 binding 能触发 enforcement，但没有证明：

- 真实 Planning 路径不会看到 actual；
- 真实 candidate 能产生完整 applicability；
- 空、未知和错维度 binding 会 fail-closed；
- Comparator 的真实语义等价路径会绑定对应 authority；
- 最终 system/user Prompt 不泄漏完整调查结构。

将 `unbound_unchanged=true` 作为成功条件也无法区分“确定不需要 authority”和“漏填
authority”。

### 2.1.4 当前 Draft Skill 只有 review criterion，缺少运行时强制

Draft Role Review 已列出 pre-actual、authority scope 和 unresolved conservatism 等
criterion，但 review receipt 只能审查已经产生的结果，不能阻止 runtime fail-open。
这些 criterion 需要保留，同时必须由核心运行时产生可验证的 plan/applicability audit。

## 2.2 一次性改造原则

- 核心机制放在 `impl/core`，不能只修 `client_search`；
- `client_search` 作为首个项目接入，提供业务 claim 和 authority 映射；
- 先建立隔离和 fail-closed，再扩大 authority resolved 覆盖率；
- 不通过“所有 case 都绑定所有 authority”规避 applicability 设计；
- 不通过“所有空 binding 都无条件 not_evaluable”损害明确直接事实的评估能力；
- 不修改现有公共 JudgeResult schema；
- 不以 Prompt 文案、手工 smoke 或 review 文本替代运行时门禁。

## 2.3 一次性改造任务

### Task 1：增加内部 ExpectationPlan schema

- 新增 `FrozenExpectationPlan`、`CaseExpectationPlanItem`、`JudgmentClaim` 和
  `AuthorityApplicabilityDecision`；
- 提供严格序列化、反序列化和 canonical hash；
- 增加 product expectation、dimension、authority candidate 的引用校验；
- 保持公共 `JudgeResult`、`BusinessExpectation` 和 `FulfillmentAssessment` 不变；
- 为 plan 增加 active artifact 或等价审计存储，但不得包含 actual。

### Task 2：拆分 Judge 两阶段运行

- 从 RunTrace 以 allowlist 构建 `JudgePlanningInputView`；
- 增加 Planning output spec，只允许生成 expectation plan；
- Planning 调用不传 `raw_response`、`extracted_output`、最终 output 和 comparator 结果；
- Planning 完成后验证并冻结 plan；
- 增加 Assessment output spec，不允许重新输出 business expectations 或 blocking；
- Assessment 只消费 frozen plan、actual 和合法 evidence；
- terminal planning failure 直接产生诚实的 `not_evaluable`，项目不得补造 assessment；
- 在最终组装时将 frozen plan item 映射到现有 runtime BusinessExpectation。

### Task 3：调整 Comparator 执行顺序

- 将 `condition_comparison` 从 `build_context/build_intent_frame` 移到 plan 冻结之后；
- Comparator 输入必须包含 `plan_id/plan_sha256/case_expectation_id`；
- 禁止 Comparator 在 Assessment 阶段调用 `ensure_business_expectation()` 新增验收项；
- Comparator 只对已冻结 plan item 生成 JudgmentClaim、evidence 和 gap；
- 删除把 actual 当 expected 的兜底行为；缺少 reference 时按协议生成或标记证据不足。

### Task 4：实现 Core Authority Gate

- 增加 `required/not_required/unknown` 状态机；
- 校验 authority ID 存在性、dimension scope 和 plan candidate coverage；
- missing、unknown、错维度和非法 binding 统一 fail-closed；
- unresolved anchor 只降级依赖该 anchor 的 claim；
- resolved dynamic anchor 缺少必要 ToolResult 时禁止假设动态事实；
- `not_required` 只接受 core、project resolver、Comparator 或 ToolResult basis；
- `unverified_llm_claim` 不能证明 `not_required`；
- 输出结构化 gate audit 和 reason，不静默 `continue`。

### Task 5：增加项目 AuthorityApplicabilityResolver 扩展点

- 在 ProjectJudge 或独立项目协议中增加 resolver 扩展点；
- resolver 必须接收 frozen plan item、JudgmentClaim 和结构化 evidence；
- resolver 返回 AuthorityApplicabilityDecision，不直接修改 assessment；
- 未实现 resolver 的迁移项目对非直接事实返回 `unknown`；
- 没有 Investigation/AuthorityAnalysis 的历史项目保持兼容，但不得伪造 authority
  coverage；其迁移状态必须可见。

### Task 6：迁移 client_search

- 从当前 query Comparator 产生结构化 claim kind；
- 至少覆盖：
  - `direct_missing_condition`；
  - `direct_extra_condition`；
  - `exact_condition_match`；
  - `semantic_mapping`；
  - `enum_legality`；
  - `query_equivalence`；
  - `downstream_protocol_support`；
- 建立 claim kind 到 evaluation dimension 和 authority candidate 的映射；
- 语义映射绑定 `semantic-mapping-authority`；
- 枚举合法性绑定 `enum-value-authority`；
- 查询形式等价绑定 `query-form-equivalence-authority`；
- 责任边界判断绑定 `evaluation-boundary-authority`；
- 删除 `_bind_search_condition_expectation(... authority_analysis_ids=[])`；
- 对用户明确要求但 actual 完全缺失的条件提供 Comparator basis，允许可信
  `not_required`；
- 对无法分类的判断返回 `unknown`，不得沿用原 verdict。

### Task 7：修复运行时 Context 投影

- Judge Investigation 不得作为目录型 direct mandatory Context 全量装载；
- 增加 Judge 专用 context builder，或强制 investigation asset 经过现有最小投影器；
- Planning 和 Assessment 分别声明允许的 ContextUnit；
- 最终 Prompt 检查必须确认不存在 `authority_analyses`、`source_claims`、
  `causal_chain`、`evidence_ref_ids` 和 `causal_reasoning`；
- 保留完整调查包用于 validator、Solidify 和审计，不删除调查证据。

### Task 8：更新 Draft Skill、ROLE、MAP 和模板

- 在 Judge ROLE 中加入两阶段 Planning/Assessment 要求；
- 在 Solidify checklist 中加入真实 Prompt 隔离检查；
- 增加 applicability resolver、claim coverage 和 basis 审查；
- Draft Review 必须引用 plan hash 和 gate audit；
- `improved` 决策要求所有决定性 claim 都有合法 applicability；
- 更新 MAP 指向新 schema、扩展点、probe 和测试；
- 模板中提供 direct fact、required、unknown 的最小示例和反例。

### Task 9：增加测试

#### Core schema 与冻结

- plan round-trip 和 canonical hash；
- actual 字段进入 Planning view 时拒绝；
- 空 plan、重复 ID、非法 product/dimension 引用拒绝；
- plan 冻结后修改失败；
- Assessment 引用错误 plan hash 拒绝；
- Assessment 尝试修改 blocking 或新增 expectation 拒绝。

#### Authority Gate

- required + resolved 允许判断；
- required + unresolved 变为 `not_evaluable`；
- required + 空 ID、未知 ID、错维度均 fail-closed；
- unknown 变为 `not_evaluable`；
- not_required + Comparator basis 允许直接事实判断；
- not_required + LLM-only basis 被拒绝；
- 一个 unresolved claim 不污染不依赖它的其他 plan item；
- resolved dynamic anchor 缺 ToolResult 不得假设动态事实。

#### 真实项目链路

- 捕获真实 Planning prompt，确认有 output schema、无 actual；
- 捕获真实 Assessment prompt，确认 plan hash 固定且 actual 首次出现；
- 捕获最终 mandatory Context，确认完整调查字段未泄漏；
- client_search 缺少明确条件判 `not_fulfilled`；
- client_search 语义映射 authority unresolved 判 `not_evaluable`；
- client_search 查询等价 authority 漏绑不能判 `fulfilled`；
- 空 actual 与 actual unavailable 分别走 `not_fulfilled/not_evaluable`；
- malformed actual 依据已冻结下游可消费性 expectation 判定；
- 真实 candidate reconcile 不依赖手工预绑定测试对象。

### Task 10：重建 Solidify 与 Draft Loop 证据

- 重建 client_search Judge investigation validation receipt；
- 重建 Solidify mappings 和 runtime observables；
- smoke 必须执行真实两阶段 candidate 路径；
- 冻结包含明确正确、明确错误、外部约束和 authority unresolved 的业务 cases；
- 由独立业务 oracle 审查 Current/Draft；
- 记录判断准确性、not_evaluable 合理性和可见退化；
- 只有 Draft 被证明更准确且无退化时才提出 Promotion。

## 2.4 迁移顺序

### 阶段 A：恢复评估可信度

1. 增加 FrozenExpectationPlan 和 Planning view；
2. 拆分 Planning/Assessment；
3. 移动 Comparator 到冻结之后；
4. 增加 Core Authority Gate；
5. 修复完整 investigation Prompt 泄漏。

该阶段完成前，现有 Judge 结果不能作为新协议已满足的证据。

### 阶段 B：恢复业务覆盖率

1. 为 client_search 实现 resolver 和 claim taxonomy；
2. 区分可信 direct facts 与 authority-dependent judgments；
3. 接入可获得的外部 ToolResult；
4. 对暂时 unresolved 的业务问题保持 `not_evaluable`；
5. 根据真实需求逐步 resolve 权威锚点，而不是降低门禁。

### 阶段 C：证明业务价值

1. 建立独立业务 oracle；
2. 冻结 Current/Draft cases；
3. 运行对照并审查误判、漏判和不合理 `not_evaluable`；
4. 修复退化并重复验证；
5. 满足 Promotion 条件后再请求用户授权。

## 2.5 一次性改造验收

- Core 存在可复用的 FrozenExpectationPlan 和 Authority Gate；
- client_search 只在 plan 冻结后向 Assessment 暴露 actual；
- Planning 能看到 Live schema，但捕获的输入中不存在当前 actual 和 comparator 结果；
- Comparator 不再事后创建 blocking expectation；
- 每个 assessment 都引用稳定 plan hash；
- 每个决定性 JudgmentClaim 都有 AuthorityApplicabilityDecision；
- 空、未知和错维度 authority binding 均不能保留确定 verdict；
- LLM 无法通过声明 `not_required` 绕过门禁；
- 明确直接缺失等事实仍可正常判 `not_fulfilled`，不会被全局 authority 阻断；
- unresolved 只影响实际依赖它的判断；
- 最终 Planning/Assessment Prompt 不包含完整调查结构；
- Solidify smoke 覆盖真实两阶段 loader、candidate、Comparator、resolver 和 gate；
- Draft Role Review 能从 plan、claim、applicability 和 gate audit 复核每个 verdict；
- 离线完整测试、项目检查和配置检查通过；
- Current/Draft 业务对照证明准确性改善且无可见退化后，才允许提出 Promotion。

## 2.6 非目标

本次改造不负责：

- 直接解决所有外部业务 authority；
- 强制所有项目使用 client_search 的 claim taxonomy；
- 修改公共 JudgeResult 或增加第四种 fulfillment 状态；
- 让 Draft Skill 参与线上实时判断；
- 用更多 Prompt 文本替代代码级隔离；
- 通过全量绑定所有 authority 或全量 `not_evaluable` 伪造安全；
- 在没有 Current/Draft 证据时自动 Promotion。
