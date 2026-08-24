# Judge：Authority 结果约束与澄清恢复增量协议

本文增量遵从：

- `spec/alg/investigate-judge.md`
- `spec/alg/investigate-judge-authority.md`

本文只补充三件事：

1. Investigation 能确定 Authority 时，Solidify 和 Judge 采用调查结论；
2. Investigation 无法确定时，Solidify 将它交付为确定性 `not_evaluable` 限制；
3. 人类补充信息后，只有重新 Investigation、再重新 Solidify，才可能解除限制。

本文不规定下游如何形成当前 Case 验收点，但规定 Authority Gate 的唯一输入接口：
每个可评价判断单元必须提供自身 ID、评价维度 ID，以及它实际依赖的
`AuthorityAnalysis.analysis_id` 集合。具体由哪个 Planning schema 承载该集合，不属于
本文。

---

# 第一章：Spec 标准——最终长期协议

## 1. Authority 的业务规则

Authority 只回答：

> 多份文档、代码、配置、业务资料或运行事实对同一问题发生冲突时，以什么为准？

```text
多个来源发生冲突
    ↓ Investigation
AuthorityAnalysis
    ├─ resolved：已经确定以什么为准
    │      ↓ Solidify
    │   交付已确认的 Context / Tool
    │      ↓ Judge
    │   按调查结论判断
    │
    └─ unresolved：仍无法确定，需要澄清
           ↓ Solidify
        固定调查版本，由 Core 编译限制
           ↓ Judge
        依赖该 Authority 的判断只能为 not_evaluable
```

不得：

- 按固定优先级、文件名或“看起来更官方”直接选边；
- 由 Solidify 或 Judge 重新调查、补齐或改写 Authority；
- 只在 Prompt 中提示 unresolved，却仍允许相关判断输出肯定结论；
- 把 unresolved 扩散到不依赖该 Authority 的判断；
- 收到人类补充后自动重新调查或自动解除限制。

## 2. 最小 schema 数据流

本文不新增 schema，只复用：

```text
AuthorityAnalysis
    ├─ evidence_ref_ids → InvestigationManifest.evidence_refs
    └─ tool_requirement_ids → InvestigationManifest.tool_requirements

Solidify 既有交付
    ├─ RoleAssetMapping
    ├─ Solidify receipt
    ├─ ContextUnitRecord / ContextUnit
    └─ VerifiableTool
```

不新增 `SolidifiedAuthorityAnchor`。`AuthorityAnalysis.anchor` 已经保存
resolved/unresolved、调查结论、无法确定的原因和澄清问题；Solidify 又不得修改这些
内容，再复制一份 Anchor 只会形成第二份真相。

基线中已有的 runtime `authority_anchors` / Authority constraint 可以继续作为 Core
从 `AuthorityAnalysis` 确定性编译出的只读运行视图；它不是 Harness AI 另行填写或
持久化的 Authority 业务 schema，也不能反过来覆盖调查结论。

### 2.1 唯一 Authority 业务真相

```python
AuthorityAnalysis(
    analysis_id=...,
    judgment_point=...,
    dimension_ids=(...),
    source_claims=(...),
    anchor=AuthorityAnchor(
        status="resolved" | "unresolved",
        description=...,
        causal_reasoning=...,
        unresolved_question=...,
        ...
    ),
    evidence_ref_ids=(...),
    tool_requirement_ids=(...),
    verification_mode="static" | "dynamic",
)
```

- resolved：使用 `anchor.description` 作为已确认 Authority；
- unresolved：使用 `anchor.causal_reasoning` 说明为何不能确定，使用
  `anchor.unresolved_question` 说明人类需要补充什么；
- EvidenceRef 和 ToolRequirement 继续通过现有 ID 引用；
- Context、Tool、receipt、metadata 和 Judge Prompt 都不得产生另一套 Authority
  结论。

### 2.2 Harness AI 与代码的分工

| 阶段 | Harness AI | 代码主链 |
|---|---|---|
| Investigation | 调查冲突并生成 `AuthorityAnalysis` | 校验 schema、ID、EvidenceRef 和 ToolRequirement |
| Solidify | 对 resolved Analysis 固化原始 Evidence、忠实投影判断规则，并按 ToolRequirement 构建或复用 Tool | 固定调查版本、校验交付映射、构造并注册 ContextUnitRecord/Tool；为 unresolved 编译 Gate 限制 |
| Judge | 使用已交付 Context/Tool 判断 | 加载 mandatory Context、执行 Tool、强制 Authority 结果约束 |

Harness AI 负责业务内容；代码负责 ID、引用、注册和门禁。

Harness AI 不直接填写 `ContextUnitRecord.id`、`content_ref`、`scope` 或 `roles`，也不为
静态 Authority Context 编写额外 `context_builder`。

### 2.3 Authority 依赖声明与 Gate 的唯一接口

change1 不新增 Case schema。使用 change2 时，Gate 直接消费已有字段：

```text
CaseEvaluationPoint.point_id
CaseEvaluationPoint.evaluation_dimension_id
CaseEvaluationPoint.authority_analysis_ids
FrozenCaseEvaluationPlan.authority_snapshot_sha256
```

字段含义：

- `point_id`：当前被 Gate 约束的验收点身份；
- `evaluation_dimension_id`：该 Point 属于哪个评价维度；
- `authority_analysis_ids`：该 Point 实际依赖的 AuthorityAnalysis ID；不依赖 Authority
  时为空；
- `authority_snapshot_sha256`：Planning 与 Assessment 共同绑定的 Authority 快照。

不得再增加 `judgment_id` 或 Judgment schema。`AuthorityAnalysis.judgment_point` 是
项目级“需要确定什么权威”的问题描述，不是当前 Case Point 的身份。

`AuthorityAnalysis.dimension_ids` 延续基线，声明该 Authority 与哪些评价维度存在项目级
潜在依赖关系；
`authority_analysis_ids` 才表示当前判断**实际依赖哪些 Authority**。二者不能互相
替代：

```text
AuthorityAnalysis.dimension_ids
    = 项目级候选依赖范围

当前判断.authority_analysis_ids
    = 当前 Case 的实际依赖
```

这是对父规范“对应维度保守处理”的精确化：`dimension_ids` 只形成候选范围，不能自动
阻断该维度的所有 Point；只有显式引用该 Analysis 的 Point 才受 Gate 约束。

依赖集合必须在 actual 可见前确定，并绑定同一 Solidify/Authority 快照。Core 只向上游
提供以下候选目录：

```text
analysis_id
judgment_point
dimension_ids
```

目录不包含 `anchor.status`、调查结论或 unresolved 原因，避免上游为了得到更容易的结果
而回避 unresolved Authority。上游只负责根据当前请求，从目录中选择当前判断实际依赖的
ID；不能自由生成 Authority ID，也不能改变 Authority 状态。

Core 必须拒绝：

- 对应 Analysis 不存在于当前快照；
- 对应 Analysis 的 `dimension_ids` 不包含当前 `evaluation_dimension_id`；
- ID 重复；
- actual 可见后增加、删除或替换依赖；
- Planning 与 Assessment 使用不同 Authority snapshot。

Core 校验后按 ID 排序为稳定 tuple。没有 AuthorityAnalysis 的项目使用
规范化空 Authority 集合的 snapshot hash；`authority_analysis_ids=()` 不触发 Authority
限制。

如何理解当前请求、选择依赖以及验证遗漏率，属于上游 Planning 准确性；change1 不引入
额外 LLM 调用、完整 applicability 矩阵或 `judgment_kind`。

### 2.4 Authority snapshot

`authority_snapshot_sha256` 必须由 Core 对以下内容规范化后计算：

```text
AUTHORITY_RUNTIME_PROTOCOL_VERSION
+ 当前 Judge investigation contract 中的全部 AuthorityAnalysis
+ 规范化后待写入/已激活 receipt、且 source_id 以 "authority:" 开头的 mappings
+ 这些 mappings 实际引用的 Context/Tool asset fingerprint
```

hash 不得包含无关 Role asset、普通 Judge Context、Case actual、Assessment、
Comparator 或 ToolResult。字段顺序、ID 顺序和序列化格式必须规范化。

因此：

- AuthorityAnalysis 的状态、结论、证据/工具引用变化会改变 snapshot；
- Authority Gate 编译协议变化会改变 snapshot；
- Authority Context/Tool 的实际交付变化会改变 snapshot；
- 无关 Context 或角色资产变化不会改变 snapshot；
- snapshot 变化只使旧 Plan/Assessment 输入失效，不自动触发 Investigation 或
  Solidify。

### 2.5 依赖选择的准确性边界

Core 可以确定性校验 ID、维度范围、重复和 snapshot，但不能只靠结构校验证明 Planning
没有漏选或误选 Authority。本文不为此新增 coverage registry、适用性矩阵或第二次 LLM
调用。

Draft 至少必须冻结以下回归案例：

1. 当前 Point 明确依赖某个 Authority，必须选中对应 `analysis_id`；
2. 同一维度中的另一个 Point 与该 Authority 无关，必须保持空依赖；
3. 应依赖却输出空集合，记为 dependency omission 并阻断 Promotion；
4. 误选无关 Authority，记为 dependency over-selection 并阻断 Promotion。

dependency omission rate、dependency over-selection rate 和 `not_evaluable` rate 必须
同时观察：前者防止绕过 Gate，后两者防止 Authority 误扩散。

## 3. ContextUnit 与 Authority 的串联

### 3.1 内容来源

```text
AuthorityAnalysis.evidence_ref_ids
    ↓
InvestigationManifest.evidence_refs
    ↓ location_ref / payload 指向的 evidence artifact 原文
Solidify
    ↓ 不改写原文
Evidence ContextUnit

AuthorityAnalysis.anchor.description
+ AuthorityAnalysis.anchor.verification_method
    ↓ Solidify Harness AI 忠实投影
Authority 判断规则 ContextUnit
```

对 resolved Analysis：

- Evidence ContextUnit 保留 EvidenceRef 指向的原始材料，不得用 AI 摘要替代；
- Authority 判断规则 ContextUnit 只投影调查已经确认的结论和验证方法；
- resolved Analysis 同时存在 Evidence 和规则时分别使用两个既有 Context 资产，使原文
  hash 和规则 projection 都能独立校验；两者必须经 receipt 回到同一
  `AuthorityAnalysis`。

“Evidence ContextUnit”和“Authority 判断规则 ContextUnit”只是本文说明内容职责的称呼，
不是新的 `kind`、dataclass 或注册类型。

unresolved 遵从基线，不生成业务规则 ContextUnit 或 Judge 运行时 Tool。Core 直接从
同一快照中的 `AuthorityAnalysis.anchor.causal_reasoning` 和 `unresolved_question`
编译 Gate 限制与 Judge summary，不生成猜测答案，也不把这些调查过程字段注入 Judge
Prompt 或最小 runtime `authority_anchors`。

### 3.2 最小 ID 链

```text
AuthorityAnalysis.analysis_id = A
    ├─ evidence_ref_ids → EvidenceRef → evidence artifact 原文
    ├─ anchor → 已确认规则
    └─ Core 派生 source_id = "authority:" + A
           ↓ Solidify receipt
        RoleAssetMapping.asset_id = X
           ↓ Core 既有 ID 规则
        ContextUnit.id = "project.<project_id>.asset.<X>"
           ↓ mandatory_context
        Judge
```

`analysis_id` 来自 Investigation；`authority:<analysis_id>`、ContextUnit ID 和 Tool ID
由 Core 按既有规则生成；Harness AI 只固化原文或忠实投影规则，不生成运行时 ID。

resolved mapping 记录 Evidence Context、规则 Context 和可选 Tool asset。unresolved
不建立业务 Context/Tool，但仍必须有独立
`authority:<analysis_id>` mapping 和 runtime observable，证明 Core 已编译
`not_evaluable_when_authority_is_required`。

## 4. Tool 与 Authority 的串联

```text
resolved AuthorityAnalysis.analysis_id = A
    ├─ tool_requirement_ids = [T]
    │      ↓
    │   ToolRequirement.tool_id = T
    │      ↓ Solidify Harness AI 构建或复用
    │   VerifiableTool.tool_id = T
    │
    └─ "authority:" + A
           ↓ Solidify receipt
        Tool asset_id
```

规则：

- Tool 必须来自 `AuthorityAnalysis.tool_requirement_ids`；
- `VerifiableTool.tool_id` 必须等于 `ToolRequirement.tool_id`；
- Tool asset ID、Tool ID、ContextUnit ID 是不同身份；
- Investigation 使用 Tool 得到的事实必须先成为 EvidenceRef，才能支撑 Analysis；
- Judge 运行时 Tool 只能读取当前事实，不能改变 Authority 状态；
- unresolved 的 ToolRequirement 只表示重新调查所需能力，Solidify 不为它交付 Judge
  运行时 Tool，也不得靠运行时 Tool 自动解除。

resolved dynamic 中，如果已经知道“以什么为准”，但 Tool 暂时取不到当前事实，相关判断
可以因为动态证据不足而 `not_evaluable`；这不等于 Authority unresolved。

## 5. Judge 结果与人类恢复

当某个当前 Case 验收点已经声明依赖某个 Authority：

```text
authority_analysis_ids 为空
    → 不触发 Authority 限制

authority_analysis_ids 中的 Analysis 全部 resolved
    → Judge 使用对应 Context 和合法 Tool 判断

authority_analysis_ids 中任一 Analysis unresolved
    → 代码无条件强制该验收点为 not_evaluable
```

这是 Judge 结果聚合前的确定性约束，不是 Prompt 建议。

unresolved 表示项目级调查尚未确定“以什么为准”。当前 Case 的用户输入、Comparator
结果、Judge LLM 声明或运行时 ToolResult 都不能直接绕过它。新材料必须先进入重新
Investigation，使新的 AuthorityAnalysis 变为 resolved，再重新 Solidify 后才能解除
限制。

Judge summary 必须说明：

- `analysis_id` 和 `judgment_point`；
- 哪些来源发生冲突、为什么不能确定；
- 人类需要澄清什么；
- 哪些当前 Case 验收点因此 `not_evaluable`。

人类补充后的恢复链：

```text
人类补充
    ↓ 登记为 EvidenceRef 或可追溯业务资料
用户明确要求重新 Investigation
    ↓
新的 AuthorityAnalysis
    ↓ 用户明确要求或正常流程重新 Solidify
新的 Context / Tool / receipt
    ↓
Judge 使用新交付
```

文件或 hash 改变只能让旧 receipt 失效，不能自动重新 Investigation、自动 Solidify 或
自动解除限制。

若当前判断冻结后 Authority snapshot 发生变化：

- 拒绝使用旧依赖集合继续 Assessment；
- 上游可以在 actual 不可见的新执行中重新形成判断及依赖；
- 不得在已看见 actual 的同一执行中改选 Authority；
- 不得因此自动运行 Investigation 或 Solidify。

## 6. 中文案例

项目中，产品术语资料和历史案例对“客户价值与分群类术语的正式定义来源”说法不同，
调查又无法确认生产流程正式采用哪一套。

### Investigation Harness AI

先在同一 `InvestigationManifest` 中登记可追溯来源：

```python
evidence_refs=(
    EvidenceRef(
        ref_id="business-glossary",
        kind="business_material",
        stage="investigation",
        summary="当前产品术语资料原文",
        location_ref=LogicalPathRef(
            location_scope=PathScope.BUSINESS_SOURCE,
            location="docs/customer-segmentation-glossary.md",
        ),
    ),
    EvidenceRef(
        ref_id="historical-cases",
        kind="business_material",
        stage="investigation",
        summary="使用另一套分群定义的历史验收案例原文",
        location_ref=LogicalPathRef(
            location_scope=PathScope.BUSINESS_SOURCE,
            location="cases/customer-segmentation-history.json",
        ),
    ),
)
```

再生成完整 AuthorityAnalysis：

```python
AuthorityAnalysis(
    analysis_id="customer-segmentation-definition-authority",
    judgment_point="客户价值与分群类术语的正式定义由什么受治理来源负责",
    dimension_ids=("search-intent-preservation",),
    source_claims=(
        SourceClaim(
            source_id="business-glossary",
            source_label="当前产品术语资料",
            claim="产品术语资料声明自己是客户价值与分群术语的正式定义。",
            causal_chain=CausalChain(
                origin="现有产品资料库",
                producer="产品团队，当前无法确认责任人和生效流程",
                consumption_path="供产品、实施和 Judge 理解业务术语",
                failure_modes=("可能未经过正式发布流程", "可能与生产版本不同步"),
            ),
        ),
        SourceClaim(
            source_id="historical-cases",
            source_label="历史验收案例",
            claim="历史案例使用了另一套客户价值与分群定义。",
            causal_chain=CausalChain(
                origin="历史项目验收记录",
                producer="历史项目参与者，当前无法确认审批主体",
                consumption_path="作为回归案例和人工判断参考",
                failure_modes=("可能只适用于旧版本", "可能记录了临时约定"),
            ),
        ),
    ),
    anchor=AuthorityAnchor(
        status="unresolved",
        description="",
        anchor_type="unresolved",
        verification_method="",
        causal_reasoning=(
            "产品术语资料和历史案例使用不同定义来源，"
            "当前证据无法确认生产流程正式采用哪一个。"
        ),
        unresolved_question=(
            "请确认正式定义来源、责任角色、适用范围和当前生效版本。"
        ),
    ),
    evidence_ref_ids=("business-glossary", "historical-cases"),
    tool_requirement_ids=(),
    verification_mode="static",
)
```

### Solidify Harness AI 与 Core

由于 Analysis 为 unresolved，Harness AI 不生成规则 Context 或 Tool。Core 固定包含该
Analysis 的 Judge investigation contract 指纹，并从 Analysis 直接编译：

```text
analysis_id = customer-segmentation-definition-authority
status = unresolved
causal_reasoning = 产品术语资料和历史案例使用不同定义来源，当前无法确认生产流程采用哪一个
unresolved_question = 请确认正式定义来源、责任角色、适用范围和当前生效版本
```

这不是第二份 Authority 结论，只是同一 Analysis 的只读运行视图。

### Judge

依赖该 Authority 的验收点：

```python
CaseEvaluationPoint(
    point_id="由 Core 生成",
    product_expectation_id="find-target-customers",
    evaluation_dimension_id="search-intent-preservation",
    authority_analysis_ids=(
        "customer-segmentation-definition-authority",
    ),
    expected_outcome="客户分层术语被解释为当前正式业务定义",
    acceptance_criteria=("映射符合正式生效的客户分层定义",),
    blocking=True,
)
```

Gate 输出：

```text
status = not_evaluable
summary = “客户分层正式定义来源未解决；当前资料相互冲突。
           待澄清正式定义来源、责任角色、适用范围和当前生效版本。”
```

只检查“用户明确写出的年龄条件有没有被遗漏”的验收点不依赖该 Authority，仍可正常
得到 `fulfilled` 或 `not_fulfilled`：

```python
CaseEvaluationPoint(
    point_id="由 Core 生成",
    product_expectation_id="find-target-customers",
    evaluation_dimension_id="search-intent-preservation",
    authority_analysis_ids=(),
    expected_outcome="用户明确给出的年龄条件被完整保留",
    acceptance_criteria=("年龄条件没有被遗漏或改写",),
    blocking=True,
)
```

### 人类补充后的恢复

人类提供正式术语表、生效版本和责任人后，材料先登记为 EvidenceRef。只有用户明确要求
重新 Investigation，产生 resolved 的新 `AuthorityAnalysis`，再重新 Solidify，Harness
AI 才固化 Evidence 原文并生成已确认规则的忠实投影：

```yaml
- asset_id: judge_authority_customer_segmentation_evidence
  kind: context
  roles: [judge]
  candidate_path: project://draft/context/customer_segmentation_glossary.md

- asset_id: judge_authority_customer_segmentation_rule
  kind: context
  roles: [judge]
  candidate_path: project://draft/context/judge_authority_customer_segmentation.md
```

receipt 随后建立：

```text
authority:customer-segmentation-definition-authority
    ├─ judge_authority_customer_segmentation_evidence
    │    → project.client_search.asset.judge_authority_customer_segmentation_evidence
    └─ judge_authority_customer_segmentation_rule
         → project.client_search.asset.judge_authority_customer_segmentation_rule
```

Core 根据既有规则构造同 ID 的 `ContextUnitRecord` / `ContextUnit` 并注入 Judge。此时
依赖该 Authority 的验收点才恢复正常三态判断。

---

# 第二章：Changes——现状差异与一次性改造

## 1. 当前实现

当前已经具备：

- `AuthorityAnalysis`、AuthorityAnchor、EvidenceRef、ToolRequirement；
- `RoleAssetMapping(kind="context" | "tool")`；
- Solidify receipt 的 `source_ids → asset_ids → runtime_observables`；
- Core 从 `project_id + asset_id` 构造 `ContextUnitRecord.id`；
- mandatory Context 加载、Authority Gate 和三态结果；
- receipt 对调查合同和资产的 hash 校验。

client_search 已有真实链路：

```text
enum-value-authority
    → authority:enum-value-authority
    → judge_authority_enum_values
    → project.client_search.asset.judge_authority_enum_values
```

当前主要差异：

1. Authority 状态和原因仍复制在 asset metadata 中，形成第二份真相；
2. Context 正文尚未被严格校验为 `AuthorityAnalysis` 的忠实交付；
3. spec 没有明确 Harness AI 生成内容、Core 生成 `ContextUnitRecord`；
4. `not_evaluable` summary 可能只显示内部 ID 或笼统证据不足；
5. Tool 暂时不可用与 Authority unresolved 的原因容易混淆；
6. 当前 Gate 使用 `evaluation_dimension_id + judgment_kind + asset metadata` 识别
   Authority 依赖，而 change1 长期协议没有定义这套业务关系；
7. 当前 Gate 允许 Case 级“决定性证据”绕过 unresolved，与“必须重新
   Investigation、再重新 Solidify”冲突。

## 2. 一次性改造任务

### 2.1 实施顺序与单轨切换

change1 的 Gate 依赖 change2 已定义的 `CaseEvaluationPoint` 和
`FrozenCaseEvaluationPlan`。必须按以下顺序实施：

```text
1. 落地 change2 的 Case schema 和 actual-free Planning
2. 从 AuthorityAnalysis 编译 Authority runtime contract
3. 让 Gate 按 authority_analysis_ids 精确约束 Point
4. 删除 judgment_kind + asset metadata 旧 Authority 路由
```

新 Case schema 未启用时不得启用新 Gate；新 Gate 启用后不得回退到旧路由。迁移必须在
一个可回归的原子版本中完成，不能长期保留双轨 Authority 结果。

### 2.2 删除重复 schema

- 不实现 `SolidifiedAuthorityAnchor`；
- Authority 状态以 receipt 绑定的确切 `AuthorityAnalysis.anchor.status` 为准；
- 保留现有 runtime Authority constraint 作为 Core 派生视图，不把它升级成第二份
  Authority 真相；
- 继续使用现有 receipt，不新增 delivery dataclass。

### 2.3 固定 Harness AI 和代码职责

- Investigation Harness AI 生成 `AuthorityAnalysis`；
- 对 resolved Analysis，Solidify Harness AI 固化 Evidence 原文、忠实投影 Authority
  判断规则，并按 ToolRequirement 构建或复用 Tool；
- Harness AI 使用预先登记的 asset ID，不生成 ContextUnitRecord ID；
- Core 从 RoleAssetMapping 和文件构造、注册 `ContextUnitRecord`；
- Solidify 和 Judge 不重新调查或改写 Authority。

Context 交付必须可确定性验证：

```text
Evidence Context
    = content_ref 直接指向 EvidenceRef artifact
      或复制后 source_sha256 == context_asset_sha256

Authority 规则 Context canonical projection
    = analysis_id
    + dimension_ids
    + anchor.description
    + anchor.verification_method
    + tool_requirement_ids
```

Core 根据 AuthorityAnalysis 生成规范化 projection；Harness AI 负责把它物化到预先登记的
资产；Core 比较实际内容与 projection，任何字段缺失、改写或新增规范性结论都拒绝
Solidify。`source_sha256` 由 Core 读取 EvidenceRef artifact 后即时计算，不新增字段；
projection 使用 UTF-8 canonical JSON（key 排序、紧凑分隔符、`dimension_ids` 和
`tool_requirement_ids` 按 ID 排序，且无附加文本）。它是既有 Context 内容格式，不新增
dataclass。

### 2.4 校验完整 ID 链

Core 必须校验：

```text
AuthorityAnalysis.analysis_id
    ├─ evidence_ref_ids → EvidenceRef → evidence artifact 原文
    ├─ tool_requirement_ids → ToolRequirement
    └─ authority:<analysis_id>
           → receipt
           → Context/Tool asset_id 或 unresolved runtime observable
           → ContextUnitRecord.id / VerifiableTool.tool_id / Gate constraint
```

并保证：

- 每个 `authority:<analysis_id>` 在 receipt 中只有一项独立映射；
- Context asset 存在、角色允许且可加载；
- resolved Evidence Context 保留 EvidenceRef artifact 原文，规则 Context 与
  `anchor.description`、`verification_method` 一致；
- unresolved 不生成业务 Context/Tool，但 mapping 的 observable 必须证明 Gate 已编译，
  summary 直接引用 Analysis 中的 `causal_reasoning` 和 `unresolved_question`；
- 既有 receipt 若要求非空 `asset_ids`，unresolved mapping 使用现有
  `candidate_role` synthetic asset，由 observable 验证运行时 constraint；不新增资产
  schema；
- Tool ID 与 ToolRequirement ID 一致；
- Judge assessment 前已经加载 resolved Analysis 所需的 ContextUnit。

unresolved mapping 使用既有 receipt 形状：

```text
source_ids = ["authority:<analysis_id>"]
asset_ids = ["candidate_role"]
runtime_observables = ["authority-gate:<analysis_id>"]
```

observable 的 evidence JSON 至少包含：

```json
{
  "analysis_id": "当前 Analysis ID",
  "anchor_status": "unresolved",
  "runtime_directive": "not_evaluable_when_authority_is_required",
  "authority_snapshot_sha256": "当前 Authority snapshot"
}
```

Core 必须逐字段复核；只有 `status="succeeded"` 或 evidence 文件存在，不能证明 Gate
已经编译。

为避免 snapshot 与 observable 循环依赖，Solidify 使用两阶段顺序：

```text
规范化待写入的 Authority mappings + 相关资产 fingerprint
    → 计算 authority_snapshot_sha256
    → 运行并校验 Authority observable
    → 写入最终 receipt
```

snapshot hash 使用规范化 mapping 内容，不使用最终 receipt 文件 hash。

### 2.5 改为调查合同驱动

- 不再以 metadata 的 `authority_status`、`limitation_reason` 作为长期真相；
- 迁移期允许读取旧 metadata，但与 AuthorityAnalysis 不一致时拒绝 Solidify；
- Authority 约束从 receipt 绑定的 AuthorityAnalysis 编译；
- Gate 直接通过 `CaseEvaluationPoint.authority_analysis_ids` 查找 Authority，并使用
  `CaseEvaluationPoint.point_id` 定位受影响验收点；
- `AuthorityAnalysis.dimension_ids` 保留基线的项目级候选依赖关系，但不再把该维度的
  每个当前 Case 判断都自动视为实际依赖；
- 删除 Authority 路由对 `judgment_kind` 和 asset metadata 的依赖；
- 本文不新增 Planning schema、coverage registry 或 `judgment_kind` schema。

Core 必须定义代码常量：

```python
AUTHORITY_RUNTIME_PROTOCOL_VERSION = 1
```

当 Authority compiler、依赖匹配或 Gate 结果语义发生变化时递增，并纳入
`authority_snapshot_sha256`。不得用整个 candidate role 文件 hash 代替该版本，否则
无关代码变化会造成 snapshot 抖动。

### 2.6 结果、summary 与恢复

- unresolved 依赖由代码强制为 `not_evaluable`；
- unresolved 不得被 Case EvidenceRef、Comparator 或运行时 ToolResult 绕过；
- 不相关验收点不受影响；
- summary 显示 Authority 问题、冲突原因、待澄清问题和受影响验收点；
- dynamic Tool 不可用不能改写 Authority 状态；
- 人类补充必须经过重新 Investigation 和重新 Solidify；
- Authority snapshot 只包含 AuthorityAnalysis、authority mappings 和相关
  Context/Tool fingerprint；
- hash 改变只使旧 Plan/receipt 失效，不自动触发任何调查。

Gate 必须从 AuthorityAnalysis 确定性生成一条结构化 evidence：

```python
{
    "kind": "authority_limitation",
    "analysis_id": "...",
    "judgment_point": "...",
    "conflicting_sources": [
        {
            "source_id": "...",
            "source_label": "...",
            "claim": "...",
        },
    ],
    "causal_reasoning": "...",
    "unresolved_question": "...",
    "point_id": "...",
}
```

它使用现有 `FulfillmentAssessment.actual_evidence` 和 `JudgeResult.evidence` 承载，不新增
public schema：

```text
Authority Gate
    → assessment.status = not_evaluable
    → assessment.actual_evidence += authority_limitation
    → finalize_judge_result
    → summary_from_fulfillment
    → JudgeResult.summary.reason
```

当 `not_evaluable` assessment 含有 `authority_limitation` 时，summary 必须优先显示该
结构化原因和待澄清问题，不得继续使用 LLM 原有的笼统 `reasoning_summary` 覆盖它。

## 3. 兼容与失败处理

- 没有 AuthorityAnalysis 的项目保持原行为；
- 新 Gate 启用但 Case schema 仍是旧 `FrozenCaseExpectation` 时拒绝启动，不回退旧路由；
- 任一 Analysis 缺少对应 `authority:<analysis_id>` mapping 时拒绝 Solidify；
  unresolved mapping 不要求业务 Context/Tool asset，但必须具有 Gate observable；
- Evidence copy hash 不一致或 Authority 规则 projection 不一致时拒绝 Solidify；
- unresolved observable 缺少规定字段或字段与 Analysis/snapshot 不一致时拒绝
  Solidify；
- receipt 指向不存在、不可加载或越权 asset 时拒绝运行；
- Context 与 AuthorityAnalysis 冲突时按 Solidify 交付错误处理，不让 Judge 自行选边；
- 上游判断单元引用未知、跨维度或非当前快照的 AuthorityAnalysis 时拒绝进入
  Assessment；
- 旧 metadata 不能在调查合同缺失时恢复 Authority；
- 不增加额外 Case planning LLM 调用，不修改 Judge public result schema。

## 4. 最低验收

- `AuthorityAnalysis` 是唯一 Authority 业务真相；
- change2 Case schema 未启用时，新 Gate 拒绝启动；
- resolved Analysis 的完整 ID 链可以追踪到 ContextUnit/Tool；
- Evidence Context 可以追踪到 EvidenceRef artifact 原文，AI 摘要不能替代原文；
- Evidence copy hash 不一致时拒绝 Solidify；
- Authority 规则 projection 缺字段、改字段或增加规范性结论时拒绝 Solidify；
- Harness AI 只生成业务内容，代码生成运行 ID 和 `ContextUnitRecord`；
- Gate 只通过精确 `authority_analysis_ids` 识别依赖，不再使用
  `dimension + judgment_kind + metadata` 路由；
- Gate 使用现有 `CaseEvaluationPoint.point_id`，不新增 `judgment_id`；
- resolved 使用调查结论；
- unresolved 依赖被确定性限制为带原因的 `not_evaluable`；
- unresolved observable 缺字段或与 Analysis 不一致时拒绝 Solidify；
- unresolved 不会被 Case 证据或运行时 Tool 绕过；
- summary 从结构化 `authority_limitation` 显示冲突、原因、澄清问题和受影响验收点；
- Authority 限制不扩散到无关判断；
- dependency omission 和 over-selection 均有冻结回归案例并阻断退化 Promotion；
- `AUTHORITY_RUNTIME_PROTOCOL_VERSION` 变化会改变 snapshot；
- 无关资产变化不会改变 Authority snapshot；
- Tool 只能来自调查声明的 ToolRequirement；
- 人类补充未经重新 Investigation 和重新 Solidify 不生效；
- 不引入第二份 Anchor、Planning 或 coverage schema。
