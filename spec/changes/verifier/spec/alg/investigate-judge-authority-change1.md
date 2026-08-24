# Judge Pre-Actual Expectation 与 Authority Knowledge 协议

本文是 `spec/alg/investigate-judge.md` 与
`spec/alg/investigate-judge-authority.md` 的增量变更规范，解决两个问题：

1. 当前 Case 验收项和 `blocking` 可能在 Judge 已看到 actual 后才生成；
2. AuthorityAnalysis 虽然存在，但当前主要通过 case-time ID 绑定生效，没有自然地
   转化为 Judge 真正可使用的知识、规则和验证能力。

本文不修改 `InvestigationManifest`、`JudgeResult`、`BusinessExpectation`、
`FulfillmentAssessment` 或三态聚合的公共 schema。新增对象属于 Judge 内部运行时和
审计边界。发生歧义时，以本文对 pre-actual 冻结和 Authority 知识固化的要求为准，
其余流程继续遵守原协议。

---

# 第一章：Spec 标准——最终长期协议

## 1.1 目标

Judge 必须在不知道当前 actual 内容和质量的前提下，先确定当前 Case 要检查什么；
actual 可见后，只能依据已经冻结的验收项进行评估，不能重新定义验收标准。

AuthorityAnalysis 的长期职责是治理 Judge 的知识来源：Investigate 确定哪些结论可信、
哪些仍然未知；Solidify 将这些调查结果转化成可被 Judge 自然消费的 ContextUnit、
Comparator 规则和 VerifiableTool。Authority 不是每条 case 判断的审批流程，也不要求
LLM 为每个 expectation 填写 authority ID。

长期运行链路为：

```text
项目级 Judge Investigation
  ├── BusinessExpectation
  ├── LiveBoundary
  ├── EvaluationDimension
  └── AuthorityAnalysis
          ↓ Solidify
  Authority ContextUnit / Comparator Rule / VerifiableTool
          ↓
Case 输入 + reference + 输出合同（不含 actual）
          ↓ Phase 1: Expectation Planning
FrozenExpectationPlan
          ↓ 冻结并记录 plan hash
按计划维度加载相关 Authority Knowledge
          ↓
actual + 合法外部证据
          ↓ Phase 2: Assessment
FulfillmentAssessment[]
          ↓ 现有公共聚合
JudgeResult
```

## 1.2 核心原则

### 1.2.1 评分标准先于答案

- Phase 1 不得读取当前 Case 的 `raw_response`、`extracted_output`、最终 output、
  actual 派生日志或 Comparator 结果；
- 当前 Case 原子验收项、`blocking`、关联产品期望和评估维度必须在 Phase 1 冻结；
- Phase 2 不得新增、删除、合并、拆分或修改冻结的验收项，也不得修改 `blocking`；
- Prompt 中写“请先确定 blocking”不能替代代码级输入隔离、对象冻结和审计；
- actual 为空、缺失或 schema 非法是 Phase 2 的事实，不得反向改变 Phase 1 的计划。

### 1.2.2 看不到答案不等于不知道输出格式

Phase 1 可以看到稳定的输出合同知识：

- Live output JSON Schema；
- 字段、值类型、操作符和结构约束；
- capability manifest；
- 下游消费协议；
- BusinessExpectation、LiveBoundary 和 EvaluationDimension 的最小投影；
- 与当前 Case actual 无关的通用格式示例；
- 当前用户请求，以及项目协议明确允许的 reference。

Phase 1 不得看到：

- 当前 actual 的字段、值或输出片段；
- 从 actual 计算出的 `wrong`、`missing`、`extra`、相似度或 verdict；
- 当前执行的成功/失败标签；
- 能够反推出当前 actual 质量的 Comparator、review 或历史结论。

输出 schema 描述“答案采用什么格式”，actual 描述“本次实际答了什么”。前者必须提供
给 Phase 1，后者必须隔离到 Phase 2。

### 1.2.3 Authority 是知识治理，不是运行时审批

AuthorityAnalysis 回答的是项目级问题：Judge 判断某类业务问题时，哪些知识可信，
哪些结论不能假设。它不负责对每个 case 重复审批。

长期协议禁止以下模式：

```text
每条 runtime expectation
  → 要求 LLM 填 authority_analysis_ids
  → 根据空列表猜测“无需 authority”还是“漏填”
  → 再执行一轮 case-time authority 审批
```

长期协议采用以下模式：

```text
AuthorityAnalysis
  → Solidify 为 Judge 知识或验证能力
  → Runtime 只使用已经固化的能力
  → 能力无法回答时保持 not_evaluable
```

### 1.2.4 不把未知固化成知识

- `resolved` Authority 可以生成事实知识、判断规则和 Tool 使用知识；
- `unresolved` Authority 不得生成未经证实的业务结论；
- `unresolved` 可以生成限制边界 ContextUnit，明确哪些推断不能做、哪些直接判断仍然
  可以做、需要什么证据才能解除限制；
- 限制边界不是负面结论，也不能把整个 EvaluationDimension 全局判为
  `not_evaluable`；
- Judge 只有在当前判断确实落入该限制边界、且没有其他直接证据时，才保守返回
  `not_evaluable`。

## 1.3 职责边界

### 1.3.1 Core Judge Runtime

核心层负责：

- 构造不含 actual 的 Phase 1 输入视图；
- 校验、冻结和哈希 ExpectationPlan；
- 确保 Phase 2 只能引用冻结计划；
- 按 plan 中的 EvaluationDimension 装载项目已经注册的 Authority ContextUnit 和 Tool；
- 阻止 Assessment 修改计划；
- 记录 plan、ContextUnit、ToolResult 和 assessment 的审计关系；
- 最终组装现有公共 `JudgeResult`。

核心层不解释某个项目的业务术语，不写死字段、枚举、查询等价规则，也不在运行时重新
执行开放式 Authority 调查。

### 1.3.2 Project Judge / Comparator

项目层负责：

- 提供输出 schema、能力清单和下游协议；
- 将当前用户需求实例化为项目可理解的验收内容；
- 使用 Solidify 后的 ContextUnit、Comparator 规则和 Tool；
- 对直接可观察事实正常判断；
- 对需要业务语义或外部事实、但现有固化能力无法确认的情况返回
  `not_evaluable`；
- 不使用当前配置、模型常识或自由文本推理补造未 resolved 的权威结论。

项目层不再要求 LLM 输出 `authority_analysis_ids`，也不得把完整 AuthorityAnalysis
直接交给模型自行解释。

### 1.3.3 Draft Skill

Draft Skill 负责 Investigate、Solidify 和 Draft Loop 治理：

- 检查 AuthorityAnalysis 是否有完整因果链、证据和状态；
- 将 resolved Authority 固化为 ContextUnit、Comparator 规则或 Tool；
- 将 unresolved Authority 固化为有限范围的限制知识，而不是伪造答案；
- 检查 ContextUnit 是否有明确作用域、证据来源和禁止外推范围；
- 检查候选 Judge 是否实际加载和使用固化资产；
- 检查明确事实没有被过度阻断，未知语义没有被模型猜测补齐；
- 在冻结 Current/Draft 数据上证明改善且无退化。

Draft Skill 不参与每个线上 Case 的实时审批，也不能用 review 文本替代运行时能力。

### 1.3.4 Investigation 与 Solidify

Investigation 保存完整业务合同、因果链、证据、ToolRequirement 和 unresolved question。
Solidify 将调查结果编译成 Judge 可消费的最小资产。

完整 `AuthorityAnalysis`、`source_claims`、`causal_chain`、`causal_reasoning` 和调查过程
证据不得直接注入 Planning 或 Assessment Prompt。

## 1.4 FrozenExpectationPlan

以下对象是内部治理对象，不加入公共 `JudgeResult`：

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FrozenExpectationPlan:
    schema_version: int
    plan_id: str
    project_id: str
    trace_id: str

    # 只基于 pre-actual 输入计算。
    planning_input_sha256: str
    items: tuple[CaseExpectationPlanItem, ...]

    # 对 canonical plan payload 计算，不包含 actual。
    plan_sha256: str


@dataclass(frozen=True)
class CaseExpectationPlanItem:
    case_expectation_id: str

    # 对应调查合同中的产品级 BusinessExpectation。
    product_expectation_id: str

    # 用于装载判断知识，并约束本验收项评价角度。
    evaluation_dimension_ids: tuple[str, ...]

    expected_outcome: str
    acceptance_criteria: tuple[Any, ...]
    blocking: bool
```

Plan 不保存 current actual，不保存 verdict，也不要求保存 per-case authority binding。

## 1.5 Phase 1：Expectation Planning

### 1.5.1 输入

核心层必须从 RunTrace 以 allowlist 构建 `JudgePlanningInputView`，只包含：

- case identity；
- 当前用户请求、对话上下文和允许的 reference；
- 产品级业务合同和 LiveBoundary 最小投影；
- EvaluationDimension；
- Live output schema 与下游协议；
- 字段能力和稳定的非 actual ContextUnit。

不得先序列化完整 RunTrace 再删除少数字段。

### 1.5.2 输出与验证

Phase 1 输出 CaseExpectationPlanItem。核心层必须检查：

- 验收项非空、ID 唯一且原子；
- 每项引用存在的产品期望；
- 每项至少引用一个合法 EvaluationDimension；
- dimension 确实服务对应 product expectation；
- `blocking` 是明确布尔值；
- plan 不含 actual、assessment、verdict、wrong/missing/extra；
- plan 可以稳定序列化并计算 `plan_sha256`。

验证通过后计划冻结。后续组件只能按 `plan_id + plan_sha256` 引用，不能持有可变对象
并原地修改。

### 1.5.3 失败处理

Phase 1 调用失败、计划为空、引用非法或无法证明输入未包含 actual 时，本次 Judge 必须
以协议失败结束并返回 `not_evaluable`。项目后处理不得补造验收项把失败改成成功。

## 1.6 Authority 到 Judge Knowledge 的固化

### 1.6.1 Resolved 静态 Authority

`resolved + verification_mode=static` 可以生成一个或多个 Judge ContextUnit。

建议按使用目的拆分，而不是把完整 AuthorityAnalysis 复制成一个大文档：

```text
事实知识
  已确认的业务事实或下游协议

判断规则
  Judge 可以怎样使用该事实

适用范围
  适用哪些 dimensions、字段或业务场景

禁止外推
  哪些相似场景不能套用该结论

反例
  哪些表面相似的表达实际不等价

刷新条件
  哪些 source revision 或外部事实变化后必须重新调查
```

每个 ContextUnit 必须保留：

- 来源 AuthorityAnalysis ID；
- 适用 EvaluationDimension IDs；
- 支撑结论的 EvidenceRef 指针；
- 适用条件和禁止外推范围；
- source revision 或等价 freshness 信息；
- Role 权限，仅允许声明的 Judge 操作读取。

ContextUnit 内容可以是对证据的结构化整理，但不能超出已验证 evidence 和 anchor
结论。AI 生成的扩展知识不能因为写进 ContextUnit 就自动获得权威性。

### 1.6.2 Resolved 动态 Authority

`resolved + verification_mode=dynamic` 通常生成：

```text
ContextUnit
  说明何时调用 Tool、输入含义、结果如何解释、哪些结论不能推出

VerifiableTool
  执行封闭式事实读取或比较，返回当前 Case 的可验证事实
```

Tool 必须来自 AuthorityAnalysis 已声明的 ToolRequirement。Solidify 不得自行创造未声明
的外部能力，也不得在 Tool 内重新进行开放式调查。

### 1.6.3 Unresolved Authority

unresolved 不生成“答案知识”，但可以生成限制边界 ContextUnit：

```text
当前无法确认的问题
  例如：“高净值客户”是否等于 clientLevel=A

不得采用的假设
  例如：不得把内部 value_mappings 自动视为业务认可标准

仍然允许的直接判断
  例如：用户明确要求某条件而 actual 完全缺少该条件

触发限制的场景
  例如：只有依赖口语到枚举的语义等价判断时才受限

解除限制所需证据
  例如：业务术语表、用户确认或经过验证的下游结果
```

限制 ContextUnit 必须范围明确。不得只写“该 dimension unresolved，所以全部
not_evaluable”。

### 1.6.4 Solidify 映射

每个 AuthorityAnalysis 必须在 Solidify receipt 中具有独立映射：

```text
authority:<analysis_id>
  → context_unit:<unit_id> [...]
  → tool:<tool_id> [...]
  → runtime observable
```

一个 Authority 可以生成多个 ContextUnit；多个 Authority 也可以共同支撑一个明确标注
来源的综合 ContextUnit。但 receipt 必须能够反向定位每个知识片段的来源，不能合并成
不可区分的大段 Prompt 文本。

## 1.7 Authority Knowledge 的运行时装载

Authority ContextUnit 的装载采用维度驱动，而不是 per-case authority ID 绑定：

```text
FrozenExpectationPlan
  → 收集 evaluation_dimension_ids
  → 从 Role Context 注册表选择这些 dimensions 可用的 Authority ContextUnit
  → 在 Assessment 前确定性加载
```

装载还必须满足 ContextUnit 自身的适用范围。仅 dimension 相同但业务主题无关的知识
不得无条件拼入 Prompt。

Runtime 只能看到 Solidify 后的 ContextUnit 和 Tool schema，不读取完整调查包。若某项
知识不存在，Judge 不能用模型常识补造；若限制 ContextUnit 明确覆盖当前判断点，且没有
其他直接证据，相关验收项应为 `not_evaluable`。

Authority Knowledge 的目标不是让 Judge 对每个 case 做更多审核，而是：

- 对已确认问题，直接提供稳定、可复用的判断知识；
- 对未确认问题，阻止特定的未经验证推断；
- 对明确直接事实，保持正常判断能力；
- 让新增业务确认可以通过更新 ContextUnit/Tool 自然提升覆盖率。

## 1.8 Phase 2：Assessment

Phase 2 输入包括：

- FrozenExpectationPlan；
- 当前 actual；
- 按计划维度和适用范围加载的 Authority ContextUnit；
- 允许的外部证据、Comparator 和 ToolResult。

Phase 2 只能输出 assessments 和 gaps，不得输出或修改 expectation plan。

Comparator 必须在计划冻结后运行。它只能评价已有 `case_expectation_id`，不能通过比较
actual 后新增验收项。

判断规则：

- 直接可观察的明确差异可以正常产生 `fulfilled/not_fulfilled`；
- 使用 resolved ContextUnit 或成功 ToolResult 时，可以按其适用范围判断；
- 判断依赖未确认语义、枚举现实、查询等价性或责任边界，而限制 ContextUnit 覆盖该
  判断点时，返回 `not_evaluable`；
- 不得把内部配置或 LLM 常识作为缺失 Authority Knowledge 的替代品；
- 一个受限判断不能全局污染同一 Case 中不依赖该知识的其他验收项。

如果 actual 为空：

- Live 按合同应交付结果且能够确认实际为空，通常为 `not_fulfilled`；
- 无法取得或确认 actual，通常为 `not_evaluable`；
- 两者不得混淆。

## 1.9 Client Search 示例

### 1.9.1 Pre-Actual 计划

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
      "blocking": true
    },
    {
      "case_expectation_id": "preserve-female-filter",
      "product_expectation_id": "find-target-customers",
      "evaluation_dimension_ids": ["search-intent-preservation"],
      "expected_outcome": "查询保留女性筛选条件",
      "acceptance_criteria": ["性别条件语义与用户请求一致"],
      "blocking": true
    }
  ]
}
```

若 actual 只有女性条件，年龄条件完全缺失是直接事实，Judge 可以判年龄验收项
`not_fulfilled`，不需要经过 Authority 审批。

### 1.9.2 Resolved 知识

若业务方确认“高净值客户 = clientLevel=A”，Solidify 可以生成：

```text
ContextUnit: client-search.semantic-mapping.high-net-worth
source_authority: semantic-mapping-authority
dimensions: search-intent-preservation
knowledge: 在已声明业务场景中，“高净值客户”映射为 clientLevel=A
must_not_assume: 不扩展到未确认的客户等级术语
evidence: authority:<业务确认记录>
```

Judge 在适用场景中可以直接消费该知识。

### 1.9.3 Unresolved 限制

若该映射尚未确认，Solidify 生成限制 ContextUnit：

```text
ContextUnit: client-search.semantic-mapping.limitations
source_authority: semantic-mapping-authority
dimensions: search-intent-preservation
unresolved: “高净值客户”对应哪个客户等级尚未确认
must_not_assume: 不得把 current value_mappings 当作业务真相
still_allowed: 可以判断条件是否完全缺失、输出是否无法解析
applies_when: 判断口语表达与客户等级枚举是否等价
```

此时 Judge 只在需要判断该语义等价性时返回 `not_evaluable`，不会阻断年龄条件完全缺失
等直接判断。

## 1.10 Prompt 与调用边界

Judge 使用两次独立结构化调用：

1. Planning call：只允许输出 FrozenExpectationPlan 的未哈希内容；
2. Assessment call：只允许输出 assessments、evidence 和 gaps。

两次调用可以使用同一模型，但必须采用不同输入视图和 output schema。禁止依赖单次
Prompt 中“先思考 expectations，再看 actual”的文字顺序。

为控制成本，可以：

- 缓存稳定 schema、ContextUnit 和产品合同；
- 对相同请求/reference 指纹复用已验证 planning result；
- 对能由确定性代码实例化的验收项跳过 Planning LLM；
- Assessment 只加载计划维度相关的最小 ContextUnit。

缓存键必须包含项目 revision、调查合同 revision、用户请求/reference 指纹和 planning
schema version。不得跨不兼容 revision 复用计划。

## 1.11 审计要求

每次 Judge 运行至少记录：

- planning input fingerprint；
- plan ID、plan hash 和生成时间；
- actual 首次可见的阶段；
- assessment 引用的 plan hash；
- 本次加载的 ContextUnit IDs 和调用的 Tool IDs；
- ContextUnit/Tool 到 AuthorityAnalysis 的 Solidify 映射；
- 最终 assessment 到 plan item 和 evidence 的映射。

审计数据通过 artifact 引用完整调查证据，不把完整 AuthorityAnalysis 复制进 runtime
Prompt 或公共结果。

## 1.12 Validator、Solidify 与 Draft Review 门禁

### Validator

Validator 必须验证 plan schema、ID 唯一性和引用关系，以及 Authority Knowledge 的来源
映射。它不使用脆弱关键词检查代替业务语义审查。

### Solidify

Solidify smoke 必须经过真实 project loader 和最终 Judge 输入构建链路，并验证：

- Planning 输入有 output schema、无 actual 和 actual 派生结果；
- 最终 Prompt 不含完整调查字段；
- plan 在 Assessment 前被冻结；
- Assessment 不能修改 plan；
- 每个 resolved Authority 产生可定位的 ContextUnit/Tool；
- 每个 unresolved Authority 只产生限制知识，不产生未经证实的答案；
- 直接事实仍能正常判断；
- 需要未确认语义的判断保持 `not_evaluable`；
- 候选真实加载并使用固化资产。

### Draft Review

Judge Draft Review 必须检查：

- plan 是否由产品期望、当前请求和维度共同支持；
- plan 是否在 actual 前生成，blocking 是否被冻结；
- actual 是否只在 Phase 2 首次可见；
- Authority ContextUnit 是否来自有效 analysis 和 evidence；
- resolved 知识是否在适用范围内使用；
- unresolved 限制是否只阻断相关推断，没有过度审核直接事实；
- Judge 是否使用内部配置或模型常识补造未确认结论；
- Draft 是否相对 frozen Current 提升准确性且无可见退化。

## 1.13 长期验收标准

- Judge 不能在同一次可见 actual 的调用中同时制定验收计划；
- Phase 1 知道输出合同但不知道当前 actual；
- FrozenExpectationPlan 具有稳定 hash，Phase 2 只能引用不能修改；
- Comparator 只能评估已冻结验收项，不能事后新增 blocking expectation；
- AuthorityAnalysis 通过 Solidify 生成 ContextUnit、Comparator 规则或 Tool；
- runtime 不要求 LLM 输出 per-case authority IDs；
- resolved 知识具有证据、作用域、禁止外推范围和 freshness；
- unresolved 只生成限制知识，不生成答案；
- 明确直接事实不会被 Authority 机制过度阻断；
- 未确认语义不能被内部配置或模型常识补齐；
- 完整调查 JSON 不进入 Planning 或 Assessment Prompt；
- 现有 Judge 公共结果 schema 和三态聚合协议保持不变；
- Solidify 和 Draft Review 能用真实运行证据复核以上不变量。

---

# 第二章：Changes——现状差异与一次性改造任务

## 2.1 当前状态与目标差异

### 2.1.1 Expectation 与 Assessment 未隔离

当前通用 Judge 在一次 `complete_json()` 调用中同时生成
`business_expectations` 和 `fulfillment_assessments`。该调用的 user payload 已包含
RunTrace actual，因此“在 actual 前确定 blocking”只有 Prompt 声明，没有代码级隔离、
冻结对象或审计证据。

`client_search` 还会在构建 Judge context 时提前运行 `condition_comparison`，使
`wrong/missing/extra` 等 actual 派生结果在 expectation 生成前可见。

项目 `reconcile_result` 中的 Comparator 可以在看到 actual 后调用
`ensure_business_expectation()` 新增 blocking expectation。

### 2.1.2 Authority 当前采用不自然的 case-time 绑定

现有 `enforce_authority_directives()` 依赖 expectation boundary 中的
`authority_analysis_ids`。这要求 LLM 或项目后处理对每条 case 判断声明 authority
依赖，并产生以下问题：

- 空列表无法区分“确实不需要”和“调用方漏填”；
- 未知 ID 和错维度可以静默跳过；
- 项目 Comparator 固定写空列表仍可产生确定 verdict；
- Authority 成为额外审批元数据，而不是 Judge 实际使用的知识；
- smoke 容易只证明手工绑定有效，不能证明 Authority 改善真实判断能力。

### 2.1.3 完整 Investigation 仍可能进入 Prompt

Judge investigation 当前可以作为目录型 mandatory Context 被递归装载。即使专用 runtime
projection 已删除调查过程字段，通用 Context loader 仍可能把完整 contract JSON 重新
拼入 system prompt。

这使 Solidify 后的最小知识与原始调查材料同时存在，形成两套运行时来源。

### 2.1.4 Authority Knowledge 资产尚未形成

当前 Solidify receipt 可以记录 AuthorityAnalysis 到候选资产的映射，但缺少稳定的
Authority ContextUnit 生产约定：

- resolved anchor 没有统一拆分为事实、规则、范围和限制知识；
- unresolved anchor 主要依赖 runtime directive，没有形成可理解的限制 ContextUnit；
- 项目 Comparator 仍直接读取可能未经权威确认的当前配置；
- Judge 无法通过 Context 搜索或装载自然获得经过治理的权威知识。

## 2.2 一次性改造原则

- 两阶段 ExpectationPlan 属于通用 Core 能力；
- Authority 主要在 Investigate/Solidify 阶段发挥作用；
- resolved Authority 生成可用知识和验证能力；
- unresolved Authority 只生成有限范围的限制知识；
- 不建立逐 claim Authority 审批状态机；
- 不要求 LLM 填写 per-case authority ID；
- 不把所有 case 绑定所有 Authority；
- 不把整个 EvaluationDimension 因一个 unresolved 问题全部关闭；
- 不修改公共 JudgeResult schema；
- 不以更多 Prompt 文本替代代码级隔离和正式 ContextUnit。

## 2.3 一次性改造任务

### Task 1：增加 FrozenExpectationPlan

- 新增 `FrozenExpectationPlan` 和 `CaseExpectationPlanItem`；
- 提供严格序列化、反序列化和 canonical hash；
- 校验 product expectation 和 evaluation dimension 引用；
- 保持公共 `JudgeResult`、`BusinessExpectation` 和 `FulfillmentAssessment` 不变；
- 为 plan 增加 active artifact 或等价审计存储，但不得包含 actual。

### Task 2：拆分 Judge 两阶段运行

- 从 RunTrace 以 allowlist 构建 `JudgePlanningInputView`；
- 增加 Planning output spec，只允许生成 expectation plan；
- Planning 不传 `raw_response`、`extracted_output`、最终 output 和 Comparator 结果；
- Planning 完成后验证并冻结 plan；
- 增加 Assessment output spec，不允许重新输出 business expectations 或 blocking；
- Assessment 只消费 frozen plan、actual 和合法 evidence；
- planning failure 直接产生诚实的 `not_evaluable`，项目不得补造 assessment；
- 最终将 frozen plan item 映射到现有 runtime BusinessExpectation。

### Task 3：调整 Comparator 执行顺序

- 将 `condition_comparison` 从 `build_context/build_intent_frame` 移到 plan 冻结之后；
- Comparator 输入必须包含 `plan_id/plan_sha256/case_expectation_id`；
- 禁止 Comparator 在 Assessment 阶段调用 `ensure_business_expectation()` 新增验收项；
- Comparator 只对已冻结 plan item 产生 evidence 和 gap；
- 删除把 actual 当 expected 的兜底；缺少 reference 时按协议生成或标记证据不足。

### Task 4：增加 Authority Knowledge Solidify

- 为 resolved 静态 Authority 生成一个或多个 ContextUnit；
- ContextUnit 至少包含来源 analysis、dimension scope、evidence refs、适用条件、禁止
  外推范围和 freshness；
- 为 resolved 动态 Authority 生成 Tool 使用 ContextUnit，并复用已声明
  VerifiableTool；
- 为 unresolved Authority 生成限制 ContextUnit，不生成未经证实的业务答案；
- 限制 ContextUnit 必须说明 still allowed 的直接判断，避免全局过度阻断；
- 允许一个 Authority 生成多个主题化 ContextUnit；
- 综合 ContextUnit 必须保留每个知识片段的来源映射；
- 完整 AuthorityAnalysis 继续留在调查包，不作为 ContextUnit 全文复制。

### Task 5：增加维度驱动的 Authority Context 装载

- FrozenExpectationPlan 确定 evaluation dimensions 后，再选择 Authority ContextUnit；
- 同时检查 ContextUnit 的业务主题和适用范围，不能只按 dimension 全量加载；
- Assessment 开始前确定性注册和装载所选 ContextUnit；
- 记录本次实际加载的 unit IDs；
- 缺少知识时不得自动回退到完整 investigation 或内部配置；
- 没有相关 Authority Knowledge 的直接判断继续正常执行。

### Task 6：迁移 client_search Authority

- 为四个 AuthorityAnalysis 分别设计 ContextUnit 资产；
- 枚举 Authority 生成合法值判断知识、配置冲突知识或限制知识；
- Evaluation Boundary Authority 生成 Live 可归责/不可归责知识；
- Semantic Mapping Authority 生成已确认映射或未确认映射限制；
- Query Equivalence Authority 生成已验证等价规则、Tool 使用知识或限制知识；
- 当前四个 unresolved anchor 不得产生肯定业务结论；
- Comparator 不再把未经确认的 `value_mappings` 或 semantic rules 当作外部业务真相；
- 删除 `_bind_search_condition_expectation(... authority_analysis_ids=[])`；
- 删除由 LLM 输出 per-case authority binding 的 Prompt 要求；
- 保留明确遗漏、格式错误和直接差异的正常判断能力。

### Task 7：修复运行时 Context 边界

- Judge Investigation 不得作为目录型 direct mandatory Context 全量装载；
- 增加 Judge 专用 context builder，或强制 investigation asset 经过 Authority Knowledge
  Solidify 输出；
- Planning 和 Assessment 分别声明允许的 ContextUnit；
- 最终 Prompt 不得包含 `authority_analyses`、`source_claims`、`causal_chain`、
  `evidence_ref_ids` 和 `causal_reasoning`；
- 保留完整调查包用于 validator、Solidify 和审计。

### Task 8：更新 Draft Skill、ROLE、MAP 和模板

- Judge ROLE 加入两阶段 Planning/Assessment 要求；
- 增加 Authority ContextUnit 生成规范；
- Solidify checklist 检查 resolved/unresolved 两类知识；
- Draft Review 检查 ContextUnit 是否真实使用、是否过度审核；
- Review 必须区分直接事实、已确认知识和证据不足；
- 更新 MAP 指向 plan schema、context builder、probe 和测试；
- 模板提供 resolved 知识、unresolved 限制和错误全局阻断的示例。

### Task 9：增加测试

#### Plan 与阶段隔离

- plan round-trip 和 canonical hash；
- actual 字段进入 Planning view 时拒绝；
- 空 plan、重复 ID、非法 product/dimension 引用拒绝；
- plan 冻结后修改失败；
- Assessment 引用错误 plan hash 拒绝；
- Assessment 尝试修改 blocking 或新增 expectation 拒绝。

#### Authority Knowledge

- resolved 静态 Authority 生成证据可定位的 ContextUnit；
- resolved 动态 Authority 生成 ContextUnit + Tool 映射；
- unresolved Authority 不生成肯定结论；
- unresolved 限制包含适用场景、禁止假设和 still allowed；
- ContextUnit 超出 authority anchor 或 evidence 时拒绝；
- dimension 和业务主题不匹配时不加载；
- runtime 不读取完整 AuthorityAnalysis；
- 每个 authority source 都能从 receipt 定位到 observable。

#### 真实项目链路

- 捕获真实 Planning prompt，确认有 output schema、无 actual；
- 捕获真实 Assessment prompt，确认 plan hash 固定且 actual 首次出现；
- 捕获 mandatory Context，确认完整调查字段未泄漏；
- client_search 明确遗漏条件判 `not_fulfilled`；
- client_search 未确认语义映射判 `not_evaluable`；
- client_search 已确认映射 ContextUnit 能驱动正确判断；
- 查询等价知识缺失时不能依赖模型常识判 `fulfilled`；
- 空 actual 与 actual unavailable 分别走 `not_fulfilled/not_evaluable`；
- 真实 candidate 加载 Authority ContextUnit，而不是手工绑定 authority ID。

### Task 10：重建 Solidify 与 Draft Loop 证据

- 重建 client_search Judge investigation validation receipt；
- 重建 Authority ContextUnit mappings 和 runtime observables；
- smoke 执行真实两阶段 candidate 和 Context loader；
- 冻结明确正确、明确错误、外部约束和 authority unresolved 的业务 cases；
- 统计 Authority Knowledge 的实际加载率、`not_evaluable` 率和直接事实误阻断；
- 由独立业务 oracle 审查 Current/Draft；
- 只有 Draft 更准确且无可见退化时才提出 Promotion。

## 2.4 迁移顺序

### 阶段 A：恢复评估可信度

1. 增加 FrozenExpectationPlan 和 Planning view；
2. 拆分 Planning/Assessment；
3. 移动 Comparator 到冻结之后；
4. 修复完整 investigation Prompt 泄漏。

该阶段完成前，现有 Judge 结果不能证明 pre-actual 协议已满足。

### 阶段 B：让 Authority 产生真实能力

1. 增加 Authority Knowledge Solidify；
2. 为 client_search 四个 Authority 生成主题化 ContextUnit；
3. 增加维度和主题驱动装载；
4. 让 Comparator 只使用已确认知识；
5. 对 unresolved 生成有限限制，不降低门禁也不过度阻断。

### 阶段 C：证明业务价值

1. 建立独立业务 oracle；
2. 冻结 Current/Draft cases；
3. 运行对照，审查误判、漏判和不合理 `not_evaluable`；
4. 重点检查 Authority 是否减少错误语义推断，而没有变成过度审核；
5. 满足 Promotion 条件后再请求用户授权。

## 2.5 一次性改造验收

- Core 存在可复用的 FrozenExpectationPlan；
- Planning 能看到 Live schema，但看不到当前 actual 和 Comparator 结果；
- client_search 只在 plan 冻结后向 Assessment 暴露 actual；
- Comparator 不再事后创建 blocking expectation；
- 每个 assessment 引用稳定 plan hash；
- AuthorityAnalysis 能生成证据可定位的 ContextUnit/Tool；
- resolved 知识可被真实 Judge 消费；
- unresolved 不生成肯定答案，只产生有限范围的限制知识；
- runtime 不要求 LLM 输出 authority ID；
- 明确直接事实不会因 Authority unresolved 被过度阻断；
- 未确认语义不能被内部配置或模型常识补齐；
- Planning/Assessment Prompt 不包含完整调查结构；
- Solidify smoke 覆盖真实两阶段 loader、candidate、ContextUnit 和 Tool；
- Draft Review 能从 plan、Context load audit、ToolResult 和 evidence 复核 verdict；
- 离线完整测试、项目检查和配置检查通过；
- Current/Draft 业务对照证明准确性改善且无可见退化后，才允许提出 Promotion。

## 2.6 非目标

本次改造不负责：

- 直接解决所有外部业务 Authority；
- 强制所有项目使用 client_search 的 ContextUnit 主题划分；
- 修改公共 JudgeResult 或增加第四种 fulfillment 状态；
- 建立逐 claim Authority 审批状态机；
- 要求 LLM 为每个 case 填 authority ID；
- 让 Draft Skill 参与线上实时判断；
- 用更多 Prompt 文本替代代码级隔离和正式 ContextUnit；
- 通过全量 `not_evaluable` 伪造安全；
- 在没有 Current/Draft 证据时自动 Promotion。
