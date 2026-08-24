# Mock 调查协议

# 第一章：Spec 标准

## 1. 目标与定位

Mock Investigate 必须调查并结构化记录：

1. 业务系统为什么对真实用户有价值；
2. Judge 使用哪些业务质量维度评估 Live；
3. 哪些业务情境需要覆盖哪些评估维度；
4. Mock 需要生成什么范围的数据，才能真实检验这些交叉点。

该结构只服务 Mock Investigate 与 Mock Solidify。它读取已声明的业务评估范围来指导 Mock 数据生成，但不优化 Judge、不修改 Judge 协议，也不作为 Judge 的运行时 Context。

长期关系为：

```text
BusinessValue
  说明业务系统为什么值得使用

EvaluationDimension
  说明 Judge 用什么质量轴评估 Live

EvaluationCoverageTarget
  说明哪些业务情境需要检验哪些质量轴

MockCoverageRequirement
  说明 Mock 必须生成什么数据才能完成检验
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
    # Judge 使用的真正评估维度。
    dimensions: tuple[EvaluationDimension, ...]

    # 业务情境与评估维度之间需要由 Mock 覆盖的交叉点。
    coverage_targets: tuple[EvaluationCoverageTarget, ...]


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
class EvaluationCoverageTarget:
    target_id: str
    name: str

    # 该业务情境来自哪些业务价值。
    related_value_ids: tuple[str, ...]

    # 该业务情境需要检验哪些 EvaluationDimension。
    dimension_ids: tuple[str, ...]

    # Mock 为覆盖这些交叉点必须生成的数据要求。
    mock_coverage: MockCoverageRequirement

    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class MockCoverageRequirement:
    # 哪些类型的真实用户需求属于该业务情境。
    relevant_user_needs: tuple[str, ...]

    # Mock 数据需要沿哪些用户事实、状态或约束产生变化。
    variation_requirements: tuple[str, ...]

    # 无论数据如何变化，都不能破坏的业务事实与用户知识边界。
    invariants: tuple[str, ...]
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

`EvaluationDimension` 只定义维度含义与判断问题，不包含业务情境、Mock 数据要求、Judge Prompt、评分算法或具体判定结果。

### 4.3 `EvaluationCoverageTarget`

`EvaluationCoverageTarget` 是一个需要被 Mock 数据覆盖的业务情境。它回答：

```text
在什么业务情境下
需要检验哪些 EvaluationDimension
```

例如“用户基于已有规划继续调整”是业务情境，不是评估维度。该情境可能同时检验：

- 用户事实保持；
- 业务正确性；
- 结果可执行性；
- 多轮状态连续性。

同一个评估维度可以出现在多个 CoverageTarget 中；同一个 CoverageTarget 也可以关联多个评估维度。二者形成项目所需的评估覆盖矩阵。

### 4.4 `MockCoverageRequirement`

`MockCoverageRequirement` 把一个业务情境转换为 Mock 可生成的数据空间：

- `relevant_user_needs`：该情境下可能出现的真实用户需求；
- `variation_requirements`：用户自己的目标、已有状态、业务对象、困难和约束如何变化；
- `invariants`：无论如何变化都不能破坏的业务事实。

字段值可以具体且发散，但不得被解释为封闭 Case 集合、固定词表或固定采样组合。

## 5. 评估覆盖矩阵

`EvaluationScope` 可以理解为一张矩阵：

| CoverageTarget / EvaluationDimension | 目标达成 | 用户事实保持 | 业务正确性 | 可执行性 |
|---|---:|---:|---:|---:|
| 新建业务任务 | ✓ | ✓ | ✓ | ✓ |
| 调整已有结果 | ✓ | ✓ | ✓ | ✓ |
| 信息不足 | ✓ | ✓ | ✓ | — |
| 越权业务请求 | ✓ | — | ✓ | — |

表中的行由 `coverage_targets` 表达，列由 `dimensions` 表达，交叉关系由每个 CoverageTarget 的 `dimension_ids` 表达。

矩阵不是要求所有行列做笛卡尔积。只有真实业务需要且有证据支持的交叉点才进入调查合同。

## 6. 具体性与泛化边界

Mock 应按以下关系产生用户数据：

```text
选择一个 EvaluationCoverageTarget
  → 读取其 dimension_ids 和 MockCoverageRequirement
  → 选择一种 relevant_user_need
  → 按 variation_requirements 构造当前模拟用户的具体事实
  → 校验 invariants
  → 形成 user_context → user_intent → query
```

具体事实可以包括：

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

EvaluationCoverageTarget(
    target_id="existing-plan-adjustment",
    name="用户基于已有规划继续调整",
    related_value_ids=("monthly-planning",),
    dimension_ids=(
        "user-fact-preservation",
        "business-actionability",
    ),
    mock_coverage=MockCoverageRequirement(
        relevant_user_needs=(
            "用户已有部分规划，希望补足仍存在的目标缺口",
            "用户希望修改已有方案中的某个业务对象或约束",
        ),
        variation_requirements=(
            "变化已有规划的完成程度和当前缺口",
            "变化已处理和待处理的业务对象",
            "覆盖信息完整、信息缺失和需要澄清的情况",
            "变化用户自己的目标、限制和调整偏好",
        ),
        invariants=(
            "同一用户在多轮中的已有状态、目标和约束保持连续",
            "不能替用户补造未提供或未确认的业务事实",
        ),
    ),
    evidence_ref_ids=("planning-contract",),
)
```

该 CoverageTarget 可以生成具体问题，例如：

> 我已经按客户和产品拆过一版了，但现在还差一截，能不能看看队伍这边怎么补？

这句话只是一次实例，不进入调查合同。下一次可以实例化不同目标、已有状态、对象和约束，形成不同但同样可用于检验相关评估维度的用户问题。

## 8. 调查生成要求

执行 `/draft investigate` 且 `role=mock` 时，Harness AI 必须：

1. 读取 Mock ROLE 允许的业务材料、输入协议、用户可见能力和合法样例；
2. 读取 DraftConfig 的 objective、review，以及允许提供给 Mock Investigate 的业务评估范围来源；
3. 形成有真实 EvidenceRef 支撑的 `BusinessValue[]`；
4. 将评估范围拆成真正的 `EvaluationDimension[]`，不得把具体场景冒充评估维度；
5. 识别需要覆盖的 `EvaluationCoverageTarget[]`；
6. 为每个与 objective 相关的 CoverageTarget 形成 `MockCoverageRequirement`；
7. 写入 `docs/mock-investigation-contract.json` 并登记到 Manifest artifacts；
8. 在 `overview.md` 中说明覆盖边界和 unresolved，但不复制整个 JSON。

若关键评估维度缺少业务依据、无法建立 CoverageTarget，或无法形成相关 Mock 数据要求，必须写入 `unresolved_reason`。不得用模型常识伪造完整合同。

## 9. 审查与落实机制

### 9.1 结构门禁

`validate_investigation.py` 对 `role=mock` 必须检查：

- 强制 artifact 存在并能反序列化为 `MockInvestigationContract`；
- `value_id`、`dimension_id` 和 `target_id` 各自唯一；
- `related_value_ids` 引用真实 `value_id`；
- `dimension_ids` 引用真实 `dimension_id`；
- 所有 `evidence_ref_ids` 引用当前 Manifest 的真实 EvidenceRef；
- 每个业务价值四段关系完整；
- 每个 CoverageTarget 都有关联维度和 `MockCoverageRequirement`；
- 每个覆盖要求至少声明 relevant user need、variation requirement 和 invariant；
- 文件不含已知 Case ID、promotion-only unseen case、目标答案或候选施工指令。

结构门禁失败时不得进入 Solidify。

### 9.2 Investigate → Solidify 语义交接审查

Harness AI 在 Solidify 前必须逐项确认：

- objective 与 review 关注的业务质量轴是否都进入 `dimensions`；
- `dimensions` 中是否混入了具体场景、Intent 或实现机制；
- 每个维度是否能回到真实业务价值或业务验收边界；
- CoverageTarget 是否覆盖 objective 相关的必要业务情境；
- 每个行列交叉点是否有真实业务意义，而非机械笛卡尔积；
- Mock 数据要求是否真的能触发并区分关联维度；
- 数据要求是否允许形成具体用户现实，而不是只有抽象 Intent；
- 变化要求是否开放，且没有退化为已知 Case 枚举。

关键维度或 CoverageTarget 缺失时，路由回 Investigate 或标记本轮 unresolved，不得假装调查充分。

### 9.3 Solidify 落实审查

Mock Solidify 必须建立以下可复查映射：

```text
BusinessValue / EvaluationDimension / EvaluationCoverageTarget
  → 固化的 ContextUnit、Tool 或候选 Mock 逻辑
  → 实际生成记录或 runtime audit
```

并通过真实 project loader 完成：

- Context 注册与装载检查；
- Tool smoke（若声明验证 Tool）；
- 候选 Mock 实例化；
- 至少按 objective 相关 CoverageTarget 生成代表性数据；
- 审查生成数据是否能检验其 `dimension_ids`，而非只通过 schema；
- 审查用户需求是否具体、内部一致且满足 invariants；
- 检查候选确实消费固化资产，没有把 JSON 示例或固定 Case 写死。

未建立映射、候选未消费调查产物，或生成数据不能落实关键 CoverageTarget 时，Solidify 失败。

### 9.4 Draft Loop 审查

Current/Draft 比较仍遵守现有冻结协议。Mock Review 在既有合法性、业务意义、覆盖和可执行性之外，还必须检查：

- Draft 是否更好地覆盖 objective 相关 CoverageTarget；
- 生成数据是否能够真实检验关联的 EvaluationDimension；
- 用户需求是否具体且内部一致；
- 多次生成是否呈现真实变化，而非固定模板改写；
- 是否存在 Case、数值、对象组合或 Judge 标准硬编码；
- 改善是否伴随协议、业务边界或其他覆盖目标退化。

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
2. Judge 的评估维度没有与 Mock 需要覆盖的业务情境建立显式映射；
3. 具体业务情境与评估维度当前容易被混为同一概念；
4. 现有 Mock artifact 文件名和内容形状由项目临场组织，无法统一门禁；
5. validator 不验证本 spec 的 ID、矩阵与覆盖关系；
6. Solidify 没有强制证明候选实际消费了业务价值、评估维度和 CoverageTarget；
7. 现有 DeerFlow Mock 调查文档包含用户目标、业务事实、场景示意和生成边界，但尚未按本 schema 拆分；
8. 现有 Draft Loop 没有逐个关联 objective 相关 CoverageTarget 和 EvaluationDimension。

## 12. 一次性改造任务

### Task 1：增加 schema 与 JSON 边界

- 新增 `MockInvestigationContract`、`BusinessValue`、`EvaluationScope`、`EvaluationDimension`、`EvaluationCoverageTarget` 和 `MockCoverageRequirement`；
- 提供严格的 JSON serialize/deserialize；
- 保持现有 `InvestigationManifest` 公共字段不变。

### Task 2：更新 Mock ROLE 与模板

- 将 `docs/mock-investigation-contract.json` 加入 Mock 调查强制产物；
- 在 Mock ROLE 中写入调查生成步骤、材料边界和语义交接要求；
- 在 Draft reference 中提供空模板和最小示例；
- 更新 `MAP.md` 指向模板与门禁。

### Task 3：扩展调查 validator

- 对 `role=mock` 执行本 spec 的结构门禁；
- 校验 ID、EvidenceRef、CoverageTarget 与 EvaluationDimension 的关联；
- 保持其他 Role 的公共调查包行为不变。

### Task 4：增加 Solidify 落实审查

- 要求记录“调查合同 → 固化资产 → runtime observable”的映射；
- 在 Mock Solidify smoke 中按关键 CoverageTarget 生成数据；
- 检查生成数据能检验关联维度，且候选没有写死示例或 Case；
- 关键 CoverageTarget 未落实时阻断 Draft Loop。

### Task 5：更新 Draft Loop Review

- 在 Mock Review 中加入 CoverageTarget 覆盖与 EvaluationDimension 可检验性检查；
- 不修改 Current/Draft 冻结、unseen 隔离或 Promotion 授权规则；
- 不把 dimension 或 target ID 写入 MockCase 公共 schema。

### Task 6：迁移 DeerFlow 调查包

- 从现有 `user-goal-and-scenario-contract.md` 和真实 EvidenceRef 提炼 `BusinessValue[]`；
- 从当前 objective、review 和允许的 Judge 业务验收材料提炼 `EvaluationDimension[]`；
- 将现有业务场景重构为 `EvaluationCoverageTarget[]`，不得冒充评估维度；
- 为每个关键 CoverageTarget 形成 `MockCoverageRequirement`；
- 原 Markdown 保留必要的人类说明，避免与新 JSON 形成两套冲突真相源；
- 重新执行调查门禁、Solidify smoke 和冻结 Current/Draft Loop。

### Task 7：测试与文档同步

- 增加 dataclass round-trip、结构失败、引用失败和跨 Role 隔离测试；
- 增加缺失强制 artifact、非法矩阵关联、未消费资产和 Case 硬编码的失败测试；
- 同步 `spec/alg/investigate.md`、Draft Skill、Mock ROLE、MAP 和参考模板。

## 13. 一次性改造验收

- 每个 Mock 调查包都生成并登记 `mock-investigation-contract.json`；
- validator 能阻止缺失、非法引用和不完整覆盖关系；
- EvaluationDimension 与 EvaluationCoverageTarget 不再混用；
- Mock Solidify 能证明关键 CoverageTarget 已落实到生成能力；
- 代表性生成数据既覆盖评估需要，又允许具体用户现实自然变化；
- Judge、MockCase 和 Draft Loop 公共结果 schema 未被复制或污染；
- DeerFlow 迁移后不存在旧 Markdown 与新 JSON 的冲突真相源；
- Current/Draft 比较证明改进且无可见退化后，才提出 Promotion 建议。
