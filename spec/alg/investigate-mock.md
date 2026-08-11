# Mock 调查协议

# 第一章：Spec 标准

## 1. 目标与定位

Mock Investigate 必须调查并结构化记录：

1. 业务系统为什么对真实用户有价值；
2. Judge 使用哪些业务质量维度评估 Live；
3. 为了使这些评估维度能够被真实检验，Mock 需要构造什么样的数据集。

该结构只服务 Mock Investigate 与 Mock Solidify。它读取已声明的业务评估范围来指导 Mock 数据生成，但不优化 Judge、不修改 Judge 协议，也不作为 Judge 的运行时 Context。

长期关系不是单向链条，而是业务真实性与评测有效性在 Mock 需求空间中汇合：

```text
BusinessValue                    EvaluationDimension
说明真实用户为什么使用系统        说明 Judge 用什么质量轴评估 Live
             \                   /
              \                 /
                 MockDemandSpace
          同时满足业务真实性与评测有效性
                       ↓ Solidify
              具体、相关、可评估的 Mock 数据集
```

通用性约束的是生成机制不能写死已知 Case，不要求真实用户的问题保持抽象。Mock 可以模拟围绕自身目标、已有状态、业务对象、困难和约束提出具体需求的用户。

## 2. 强制调查产物

每个 `role=mock` 的调查包必须额外生成：

```text
impl/projects/<project>/draft/investigation/mock/
  manifest.json
  overview.md
  docs/
    mock-investigation-contract.json
```

`mock-investigation-contract.json` 必须登记到既有 `InvestigationManifest.artifacts`。缺失、无法解析或审查失败时，不得进入 Mock Solidify。

该文件是调查阶段的结构化交接产物，不是 MockCase、Persona 列表、Intent 枚举、固定场景表、Judge 评分实现或候选 Prompt。完整 JSON 不得直接注入 Mock 运行时。

## 3. Dataclass Schema

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MockInvestigationContract:
    business_values: tuple[BusinessValue, ...]
    evaluation_scope: EvaluationScope
    demand_spaces: tuple[MockDemandSpace, ...]


@dataclass(frozen=True)
class BusinessValue:
    value_id: str

    # 哪类业务参与者从中获益；描述人群范围，不是固定 Persona。
    beneficiary: str

    # 使用系统前，这类人面对的真实业务问题或需要推进的工作。
    business_need: str

    # 系统为解决问题提供的用户可见业务帮助，不描述内部实现。
    system_contribution: str

    # 用户借助系统最终希望取得的业务结果。
    desired_outcome: str

    # 引用当前 InvestigationManifest.evidence_refs 中的 ref_id。
    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationScope:
    # Judge 使用的业务质量维度集合。
    dimensions: tuple[EvaluationDimension, ...]


@dataclass(frozen=True)
class EvaluationDimension:
    dimension_id: str
    name: str

    # 该业务质量轴的准确含义。
    definition: str

    # Judge 在该质量轴上需要回答的问题。
    judgment_question: str

    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class MockDemandSpace:
    space_id: str
    name: str

    # 这类需求为什么属于真实业务需求。
    business_value_ids: tuple[str, ...]

    # 这类用户需求的整体定义，不是固定 Intent 或 Case。
    demand_definition: str

    # 逐项说明为检验某个评估维度，Mock 数据必须具备什么。
    evaluation_coverage: tuple[EvaluationDimensionCoverage, ...]

    # 具体用户事实可以沿哪些方向产生变化。
    variation_space: tuple[str, ...]

    # 保证生成数据真实、合法、内部一致的约束。
    validity_constraints: tuple[str, ...]

    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationDimensionCoverage:
    # 引用 EvaluationDimension.dimension_id。
    dimension_id: str

    # 为使该维度可被评估，当前需求空间生成的 Mock 数据必须具备什么。
    mock_data_requirement: str
```

## 4. Schema 语义

### 4.1 `BusinessValue`

`BusinessValue` 定义业务系统为什么值得真实用户使用。它必须形成完整关系：

```text
beneficiary
  → business_need
  → system_contribution
  → desired_outcome
```

它不得退化为产品功能列表、Intent 名称、页面操作、宣传文案或某个 Case 的目标答案。

### 4.2 `EvaluationDimension`

`EvaluationDimension` 是 Judge 评估 Live 时使用的业务质量轴，而不是具体业务场景。

例如：

- 用户目标达成度；
- 用户事实与上下文保持；
- 业务正确性；
- 结果可执行性；
- 信息不足时的交互合理性；
- 权限和业务边界遵守；
- 多轮状态连续性。

具体维度由项目真实业务验收材料和当前 Draft objective 决定，公共协议不预设枚举。

`EvaluationDimension` 只定义维度含义与判断问题，不直接绑定某条业务价值，也不包含具体 Case、Mock 生成规则、Judge Prompt、评分算法或判定结果。

### 4.3 `MockDemandSpace`

`MockDemandSpace` 是业务价值与评估维度共同约束出来的用户需求分布。它同时回答：

```text
这类需求为什么是业务系统真实用户可能提出的；
为了检验每个评估维度，Mock 数据必须具备什么；
同一类需求中的具体用户事实可以如何变化；
以及这些变化必须满足什么有效性约束。
```

各字段含义：

- `business_value_ids`：这类需求为什么具有真实业务意义；
- `demand_definition`：这类用户需求整体是什么；
- `evaluation_coverage`：为了评估每个维度，数据必须包含什么；
- `variation_space`：同一需求空间内的具体用户现实可以怎样变化；
- `validity_constraints`：怎样避免生成无效、虚假或内部冲突的数据。

每个 `EvaluationDimensionCoverage` 只表达一条明确关系：`dimension_id` 指向已声明的评估维度，`mock_data_requirement` 说明当前需求空间中的 Mock 数据必须具备什么，才能使该维度可被检验。它不是 Judge 结论，也不是目标答案。

一个 `MockDemandSpace` 可以关联多个业务价值和评估维度；一个业务价值或评估维度也可以由多个需求空间覆盖。因此三者形成多对多关系，而不是单向派生链。

## 5. 业务价值、评估维度与需求空间的关系

示意关系如下：

```text
monthly-planning 业务价值
  ├─ 已有工作基础上的继续调整需求空间
  └─ 从零开始形成规划的需求空间

user-fact-preservation 评估维度
  ├─ 已有工作基础上的继续调整需求空间
  ├─ 多轮补充信息需求空间
  └─ 用户纠正系统误解的需求空间
```

业务价值保证需求空间来自真实用户工作，评估维度保证需求空间具有评测意义。调查包不要求 BusinessValue、EvaluationDimension 与 MockDemandSpace 做笛卡尔积；只有与当前业务、objective 和 review 有真实关系且有证据支持的连接才应记录。

## 6. 具体性与泛化边界

Mock Solidify 应按以下关系产生数据：

```text
选择一个 MockDemandSpace
  → 读取关联 BusinessValue 与 EvaluationDimension
  → 满足各 EvaluationDimensionCoverage.mock_data_requirement
  → 在 variation_space 内构造当前模拟用户的具体事实
  → 校验 validity_constraints
  → 形成 user_context → user_intent → query
```

`variation_space` 可以要求数据沿以下方面产生变化，但公共协议不固定这些维度：

- 用户自己的业务目标；
- 用户已有的工作状态或成果；
- 当前处理的业务对象；
- 当前困难、冲突或异常；
- 时间、资源和权限约束；
- 已尝试的动作及其结果；
- 用户自己的偏好、取舍和未确定事项；
- 单轮缺失信息或多轮状态变化。

允许缺失、模糊、冲突和改变主意，只要这些状态对当前业务合法，且同一用户的多轮事实保持连续。

禁止：

- 写死 iteration case、promotion-only unseen case 或历史答案；
- 把一个用户的具体事实提升为所有用户的默认事实；
- 把调查示例当成生成词表；
- 为命中评估维度而把 Judge 标准直接写进用户问题；
- 在没有业务依据时补造项目规则。

## 7. 示例

以下只说明结构关系，不是固定项目模板或标准 Case。

本例使用两个项目内评估维度 ID。它们不是公共协议预设的固定枚举：

- `user-fact-preservation`（用户事实保持）：评估 Live 是否保留用户已经明确表达的目标、已有状态、业务对象和约束，避免遗漏、替换、冲突或无依据补充；
- `business-actionability`（业务可执行性）：评估 Live 的结果是否能帮助用户继续推进当前业务工作，而不只是给出相关但无法行动的信息。

`dimension_id` 只是调查合同内部的稳定引用。任何出现在 `MockDemandSpace.evaluation_coverage` 中的 ID，都必须先在同一份 `EvaluationScope.dimensions` 中以完整的 `EvaluationDimension` 声明其名称、定义、判断问题和证据。需求空间不得引用未声明或只有名称而没有定义的评估维度。

```python
BusinessValue(
    value_id="monthly-planning",
    beneficiary="承担机构经营规划职责的业务人员",
    business_need="需要把经营目标与当前状态之间的差距转化为可执行路径",
    system_contribution="连接目标、经营现状与可调整方案，支持用户分析和决策",
    desired_outcome="形成可理解、可执行、可调整的经营规划",
    evidence_ref_ids=("planning-contract",),
)

EvaluationDimension(
    dimension_id="user-fact-preservation",
    name="用户事实保持",
    definition=(
        "Live 的理解和结果不得删除、替换、冲突或无依据补充"
        "用户已经明确表达的目标、状态和约束"
    ),
    judgment_question="Live 是否正确承接用户事实，并避免无依据改写？",
    evidence_ref_ids=("judge-business-boundary",),
)

EvaluationDimension(
    dimension_id="business-actionability",
    name="业务可执行性",
    definition=(
        "Live 的结果应支持用户继续完成当前业务工作，"
        "而不只是提供相关但无法采取行动的信息"
    ),
    judgment_question="该结果是否让用户能够有效推进当前业务目标？",
    evidence_ref_ids=("planning-contract",),
)

MockDemandSpace(
    space_id="continue-existing-plan",
    name="基于已有规划继续分析或调整",
    business_value_ids=("monthly-planning",),
    demand_definition=(
        "用户已经具有一部分规划结果，并基于自己的目标、"
        "现状和约束请求 Live 继续分析或调整"
    ),
    evaluation_coverage=(
        EvaluationDimensionCoverage(
            dimension_id="user-fact-preservation",
            mock_data_requirement=(
                "Mock 输入需要包含用户明确给出的已有规划事实，"
                "使 Live 是否保留、遗漏或改写这些事实可以被观察"
            ),
        ),
        EvaluationDimensionCoverage(
            dimension_id="business-actionability",
            mock_data_requirement=(
                "Mock 输入需要包含用户希望继续推进的目标或具体调整诉求，"
                "使 Live 是否支持下一步业务行动可以被判断"
            ),
        ),
    ),
    variation_space=(
        "已有规划可以只完成一部分，也可以已经基本完整",
        "用户可以要求保留部分内容，只调整特定业务对象",
        "目标缺口、调整对象和现实约束应产生变化",
        "信息可以完整，也可以缺失、模糊或存在需要澄清的冲突",
        "用户可以在多轮中补充事实或改变自己的取舍",
    ),
    validity_constraints=(
        "同一个模拟用户的已有状态和目标必须前后一致",
        "具体事实必须符合项目业务规则",
        "不得复用已知 Case 的固定数值或对象组合",
        "不得把 Judge 的判断标准直接写进用户问题",
    ),
    evidence_ref_ids=("planning-contract",),
)
```

该需求空间可以生成具体问题，例如：

> 我已经按客户和产品拆过一版了，但现在还差一截，能不能看看队伍这边怎么补？

这句话只是一次实例，不进入调查合同。下一次可以实例化不同目标、已有状态、对象和约束，形成不同但同样可用于检验相关评估维度的用户问题。

## 8. 调查生成要求

执行 `/draft investigate` 且 `role=mock` 时，Harness AI 必须：

1. 读取 Mock ROLE 允许的业务材料、输入协议、用户可见能力和合法样例；
2. 读取 DraftConfig 的 objective、review，以及允许提供给 Mock Investigate 的业务评估范围来源；
3. 形成有真实 EvidenceRef 支撑的 `BusinessValue[]`；
4. 将评估范围拆成真正的 `EvaluationDimension[]`，不得把具体场景冒充评估维度；
5. 从 BusinessValue 调查真实用户可能产生的需求空间；
6. 从每个 objective 相关 EvaluationDimension 反推 Mock 数据必须具备的条件；
7. 将两侧约束汇合为 `MockDemandSpace[]`；
8. 检查每条关键业务价值和每个关键评估维度至少被一个需求空间覆盖；
9. 写入 `docs/mock-investigation-contract.json` 并登记到 Manifest artifacts；
10. 在 `overview.md` 中说明覆盖边界和 unresolved，但不复制整个 JSON。

若关键业务价值或评估维度缺少依据，或无法形成同时真实且可评估的需求空间，必须写入 `unresolved_reason`。不得用模型常识伪造完整合同。

## 9. 审查与落实机制

### 9.1 结构门禁

`validate_investigation.py` 对 `role=mock` 必须检查：

- 强制 artifact 存在并能反序列化为 `MockInvestigationContract`；
- `value_id`、`dimension_id` 和 `space_id` 各自唯一；
- `business_value_ids` 引用真实 `value_id`；
- 每个 `EvaluationDimensionCoverage.dimension_id` 引用真实 `dimension_id`；
- 每个被引用的 `dimension_id` 都有非空 name、definition、judgment question 和 EvidenceRef；
- 所有 `evidence_ref_ids` 引用当前 Manifest 的真实 EvidenceRef；
- 每个业务价值四段关系完整；
- 每个需求空间至少关联一条业务价值和一个评估维度；
- 每个需求空间都有 demand definition、variation space 和 validity constraint；
- objective 相关的每条业务价值和每个评估维度至少被一个需求空间覆盖；
- 文件不含已知 Case ID、promotion-only unseen case、目标答案或候选施工指令。

结构门禁失败时不得进入 Solidify。

### 9.2 Investigate → Solidify 语义交接审查

Harness AI 在 Solidify 前必须逐项确认：

- objective 与 review 关注的业务质量轴是否都进入 EvaluationDimension；
- EvaluationDimension 中是否混入具体场景、Intent 或实现机制；
- 每个需求空间是否由真实 BusinessValue 支撑；
- 每条 evaluation coverage requirement 是否真的能让对应维度被检验；
- variation space 是否允许形成具体用户现实，而不是只有抽象 Intent；
- 同一需求空间关联多个维度时，这些维度是否都能被该空间中的数据检验；
- 同一维度需要不同需求空间才能检验时，覆盖是否充分；
- 数据空间是否开放，且没有退化为已知 Case 枚举；
- validity constraints 是否能阻止无效输入、业务伪造和用户事实冲突。

关键维度或需求空间缺失时，路由回 Investigate 或标记本轮 unresolved，不得假装调查充分。

### 9.3 Solidify 落实审查

Mock Solidify 必须建立以下可复查映射：

```text
BusinessValue / EvaluationDimension / MockDemandSpace
  → 固化的 ContextUnit、Tool 或候选 Mock 逻辑
  → 实际生成记录或 runtime audit
```

并通过真实 project loader 完成：

- Context 注册与装载检查；
- Tool smoke（若声明验证 Tool）；
- 候选 Mock 实例化；
- 至少按 objective 相关 MockDemandSpace 生成代表性数据；
- 审查生成数据是否满足各 `mock_data_requirement`，而非只通过 schema；
- 审查用户需求是否具体、内部一致且满足 validity constraints；
- 检查候选确实消费固化资产，没有把 JSON 示例或固定 Case 写死。

未建立映射、候选未消费调查产物，或生成数据不能落实关键需求空间时，Solidify 失败。

### 9.4 Draft Loop 审查

Current/Draft 比较仍遵守现有冻结协议。Mock Review 在既有合法性、业务意义、覆盖和可执行性之外，还必须检查：

- Draft 是否更好地覆盖 objective 相关 MockDemandSpace；
- 生成数据是否能够真实检验关联的 EvaluationDimension；
- 用户需求是否具体且内部一致；
- 多次生成是否呈现真实变化，而非固定模板改写；
- 是否存在 Case、数值、对象组合或 Judge 标准硬编码；
- 改善是否伴随协议、业务边界或其他需求空间退化。

只有 Draft 被证明更好且无可见退化时，才可建议 Promotion。

## 10. 与现有公共协议的关系

- 本结构是 Mock 调查包的强制 artifact，不替代 `InvestigationManifest`；
- Evidence、artifact、ToolRequirement 和 unresolved 继续使用现有公共字段；
- 不增加 MockCase、JudgeResult 或 Draft Loop 顶层 schema；
- 完整调查 JSON 不直接进入 Prompt；
- Judge 不加载该 Mock 候选调查包；
- 跨 Role 共享仍需通过现有 `role_assets` 和正式 Context/Tool 权限完成；
- promotion-only unseen case 不得进入调查结构。

# 第二章：Changes

## 11. 当前状态与目标差异

当前长期协议已经要求 Mock 调查输入协议、业务实体、用户可见能力、合法场景空间和可执行性，但仍存在以下差异：

1. Mock 没有强制的结构化业务价值产物，业务价值容易退化为 overview 中的说明文字；
2. 业务价值与 Judge 评估维度没有在 Mock 需求空间中建立显式汇合关系；
3. 现有设计曾将具体业务情境误作 EvaluationDimension；
4. 现有设计曾以一一对应的 EvaluationCoverageTarget 和 MockCoverageRequirement 重复表达同一数据要求；
5. 现有 Mock artifact 文件名和内容形状由项目临场组织，无法统一门禁；
6. validator 不验证本 spec 的 ID、引用和维度覆盖关系；
7. Solidify 没有强制证明候选实际消费了业务价值、评估维度和需求空间；
8. 现有 DeerFlow Mock 调查文档尚未按本 schema 拆分；
9. 现有 Draft Loop 没有逐个关联 objective 相关 MockDemandSpace 和 EvaluationDimension。

## 12. 一次性改造任务

### Task 1：增加 schema 与 JSON 边界

- 新增 `MockInvestigationContract`、`BusinessValue`、`EvaluationScope`、`EvaluationDimension`、`MockDemandSpace` 和 `EvaluationDimensionCoverage`；
- 提供严格的 JSON serialize/deserialize；
- 保持现有 `InvestigationManifest` 公共字段不变。

### Task 2：更新 Mock ROLE 与模板

- 将 `docs/mock-investigation-contract.json` 加入 Mock 调查强制产物；
- 在 Mock ROLE 中写入调查生成步骤、材料边界和语义交接要求；
- 在 Draft reference 中提供空模板和最小示例；
- 更新 `MAP.md` 指向模板与门禁。

### Task 3：扩展调查 validator

- 对 `role=mock` 执行本 spec 的结构门禁；
- 校验 BusinessValue、EvaluationDimension 和 MockDemandSpace 的 ID 与引用；
- 校验 objective 相关业务价值与维度至少被一个需求空间覆盖；
- 保持其他 Role 的公共调查包行为不变。

### Task 4：增加 Solidify 落实审查

- 要求记录“调查合同 → 固化资产 → runtime observable”的映射；
- 在 Mock Solidify smoke 中按关键 MockDemandSpace 生成数据；
- 检查生成数据能检验关联维度，且候选没有写死示例或 Case；
- 关键需求空间未落实时阻断 Draft Loop。

### Task 5：更新 Draft Loop Review

- 在 Mock Review 中加入 MockDemandSpace 覆盖与 EvaluationDimension 可检验性检查；
- 不修改 Current/Draft 冻结、unseen 隔离或 Promotion 授权规则；
- 不把 dimension 或 demand space ID 写入 MockCase 公共 schema。

### Task 6：迁移 DeerFlow 调查包

- 从现有 `user-goal-and-scenario-contract.md` 和真实 EvidenceRef 提炼 `BusinessValue[]`；
- 从当前 objective、review 和允许的 Judge 业务验收材料提炼 `EvaluationDimension[]`；
- 从业务价值调查真实用户需求，从评估维度反推数据条件，并汇合为 `MockDemandSpace[]`；
- 合并原先一一对应且语义重复的 coverage target 与 coverage requirement；
- 原 Markdown 只保留必要的人类说明，避免与新 JSON 形成两套冲突真相源；
- 重新执行调查门禁、Solidify smoke 和冻结 Current/Draft Loop。

### Task 7：测试与文档同步

- 增加 dataclass round-trip、结构失败、引用失败和跨 Role 隔离测试；
- 增加缺失强制 artifact、维度未覆盖、未消费资产和 Case 硬编码的失败测试；
- 同步 `spec/alg/investigate.md`、Draft Skill、Mock ROLE、MAP 和参考模板。

## 13. 一次性改造验收

- 每个 Mock 调查包都生成并登记 `mock-investigation-contract.json`；
- validator 能阻止缺失、非法引用和关键维度未覆盖；
- 不再存在一一对应且语义重复的 CoverageTarget / CoverageRequirement；
- Mock Solidify 能证明关键 MockDemandSpace 已落实到生成能力；
- 代表性生成数据既覆盖评估需要，又允许具体用户现实自然变化；
- Judge、MockCase 和 Draft Loop 公共结果 schema 未被复制或污染；
- DeerFlow 迁移后不存在旧 Markdown 与新 JSON 的冲突真相源；
- Current/Draft 比较证明改进且无可见退化后，才提出 Promotion 建议。
