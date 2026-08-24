# Judge 调查协议

# 第一章：Spec 标准

## 1. 目标与定位

Judge Investigate 的目标，是为 Judge 提供一份稳定、可审查的业务判断依据，使其能够基于外部可观察证据判断 Live 是否满足业务期望。

Judge 的核心判断可收敛为两类关系：

```text
用户输入 / 用户期望
  → Live 输出是否正确承接用户意图

Live 输出
  → 是否能被真实下游用户或系统有效使用
```

Live 系统自身的角色和职责不再作为第三个评估纬度。它属于所有评估纬度共享的责任边界，用于回答：哪些结果应归责给 Live，哪些限制来自外部系统，以及哪些证据可以作为判断依据。

因此，长期调查结构只保留两个核心概念：

```text
EvaluationDimension
  定义 Judge 具体评估什么，以及如何作出三态判断

JudgeBoundary
  定义所有评估纬度共享的 Live 职责、外部限制和证据边界
```

其中，Judge 调查包必须覆盖：

1. 用户期望承接：Live 是否正确理解并满足用户真实意图；
2. 下游可用性：Live 输出是否能被真实下游用户或系统有效消费；
3. 项目特有纬度：仅在业务确实存在额外独立关注点时补充，不能代替前两项。

证据充分性不是独立业务纬度，而是每个纬度进行 `fulfilled`、`not_fulfilled`、`not_evaluable` 三态判断的共同机制。

Solidify 将调查结构投影为现有 Judge mandatory ContextUnit、Comparator/外部检查 Tool 和候选 Judge 逻辑。它不新增或复制运行时 `BusinessExpectation`、`FulfillmentAssessment`、`JudgeResult` 和三态聚合协议。

## 2. 强制调查产物

每个 `role=judge` 的调查包必须额外生成：

```text
impl/projects/<project>/draft/investigation/judge/
  manifest.json
  overview.md
  docs/
    judge-investigation-contract.json
```

`judge-investigation-contract.json` 必须登记到既有 `InvestigationManifest.artifacts`。缺失、无法解析、EvidenceRef 无法解析或审查失败时，不得进入 Judge Solidify。

该文件是调查阶段的结构化业务验收合同，不是当前 Case 的 `JudgeResult`、目标答案、Judge Prompt 或候选实现指令。完整 JSON 不得无条件注入运行时 Prompt；Solidify 只装载当前 Judge 判断所需的最小稳定内容。

## 3. Dataclass Schema

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


EvaluationDimensionType = Literal[
    "user_expectation",
    "downstream_usability",
    "project_specific",
]


@dataclass(frozen=True)
class JudgeInvestigationContract:
    evaluation_dimensions: tuple[EvaluationDimension, ...]
    judge_boundary: JudgeBoundary


@dataclass(frozen=True)
class EvaluationDimension:
    dimension_id: str
    dimension_type: EvaluationDimensionType
    name: str

    # 本纬度评估的具体外部关系或业务结果。
    evaluation_target: str

    # 该关系成立时，业务上应得到什么结果。
    expected_result: str

    # 作出判断必须观察到哪些外部业务事实。
    required_evidence: tuple[str, ...]

    # 本纬度的三态判断条件。
    fulfilled_when: tuple[str, ...]
    not_fulfilled_when: tuple[str, ...]
    not_evaluable_when: tuple[str, ...]

    # 哪些表达、结构或执行形式差异仍属于业务等价。
    acceptable_equivalence: tuple[str, ...]

    # 需要 Comparator、外部业务 API 或协议检查时，引用既有 ToolRequirement。
    tool_requirement_ids: tuple[str, ...]

    # 引用当前 InvestigationManifest.evidence_refs 中的 ref_id。
    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class JudgeBoundary:
    # Live 在真实业务链路中扮演什么角色。
    live_role: str

    # Live 必须对哪些用户可见或下游可消费结果负责。
    in_scope_responsibilities: tuple[str, ...]

    # 哪些事项明确不属于 Live 的职责。
    out_of_scope_conditions: tuple[str, ...]

    # 哪些上游、下游或环境限制不能自动归责为 Live 失败。
    external_system_constraints: tuple[str, ...]

    # 哪些来源可作为业务判断的硬依据。
    authoritative_evidence: tuple[str, ...]

    # 哪些来源只能辅助理解，不能成为绝对标准。
    supporting_evidence: tuple[str, ...]

    # 哪些全局证据缺失时，Judge 必须保持 not_evaluable。
    global_not_evaluable_conditions: tuple[str, ...]

    evidence_ref_ids: tuple[str, ...]
```

## 4. Schema 语义

### 4.1 `EvaluationDimension`

`EvaluationDimension` 是 Judge 调查包的主体。每个实例必须定义一个可独立判断的业务质量轴，并完整回答：

- 评估什么外部关系或业务结果；
- 该关系成立时预期产生什么结果；
- 判断需要哪些证据；
- 什么情况下分别属于三态；
- 哪些形式差异仍属于业务等价；
- 是否需要 Comparator 或外部 Tool。

`evaluation_target` 不得只填写“正确性”“质量”或“可用性”等抽象词，而应明确被比较的两端。例如：

```text
用户表达的筛选意图 ↔ Live 生成的查询语义
Live 生成的结构化查询 ↔ Elasticsearch 的真实消费能力
```

`expected_result` 表达该纬度服务的具体业务结果，因此无需再建立一份与纬度平行且重复的 `BusinessOutcomeContract`。

#### 必须覆盖的纬度类型

`user_expectation` 评估输入侧关系：Live 输出是否正确承接用户的真实意图、限制和期望结果。

`downstream_usability` 评估输出侧关系：Live 输出是否满足真实下游用户或系统的消费方式、能力和约束，并能支持其继续完成业务任务。它不能只记录“下游是谁”，还必须体现“Live 输出为了被该下游有效使用，必须满足什么”。

`project_specific` 只用于前两类无法清晰表达、且确有独立业务判断价值的项目特有纬度。调查不得为了罗列概念而默认生成此类纬度。

一个项目可以为同一类型生成多个纬度，但至少必须有一个 `user_expectation` 和一个 `downstream_usability`。如果 Live 没有独立下游系统，最终直接使用输出的用户本身就是下游消费者，仍需调查其可用性。

#### 三态要求

- `fulfilled`：现有证据足以证明该纬度的预期结果得到满足；
- `not_fulfilled`：现有证据足以证明 Live 职责范围内存在真实业务差异；
- `not_evaluable`：缺少决定性输入、actual、reference、外部合同或 Comparator 事实，无法可靠判断。

三态条件必须互斥且保守。文本更长、字段更多、confidence 更高，或内部实现更接近当前 Prompt，都不构成 `fulfilled` 证据。

### 4.2 `JudgeBoundary`

`JudgeBoundary` 不是一个评估纬度，也不重复各纬度的具体三态条件。它是所有纬度共享的归责和证据边界。

它只回答以下问题：

- Live 在业务链路中承担什么角色；
- 哪些结果由 Live 控制并应对其负责；
- 哪些事项不属于 Live 职责；
- 哪些外部限制不能直接转化为 Live 失败；
- 哪些材料是硬标准，哪些只能辅助理解；
- 哪些全局证据缺失会阻止 Judge 作出可靠判断。

内部源码、内部 trace 或 Attribute 根因默认不能作为 Judge 把外部结果判失败的依据。外部依赖不可用也不能自动转化为 Live 语义错误：若仍可从现有输出和权威业务合同判断某一纬度，应继续判断；否则该纬度保持 `not_evaluable`。

`JudgeBoundary` 不得包含“查询语义正确”“结果对用户有帮助”等具体纬度结论；这些内容必须进入对应的 `EvaluationDimension`。

## 5. 调查结构到运行时的流转

```text
当前用户输入 / reference / 外部业务合同
  + user_expectation 维度
  → 生成并判断输入侧 BusinessExpectation

当前 Live actual / 下游协议 / 外部可观察结果
  + downstream_usability 维度
  → 生成并判断输出侧 BusinessExpectation

JudgeBoundary
  → 约束上述所有 expectation 的归责范围、证据优先级和不可评估边界

FulfillmentAssessment[]
  → 现有协议按预先确定的 blocking expectation 聚合 overall status
```

调查结构不能预先保存某个 Case 的 `expectation_id`、expected 答案或 fulfillment 状态。运行时 expectation 由当前 Case 的用户意图、reference 和调查结构共同实例化；public schema、三态词表和 overall 聚合继续由现有 Judge 协议代码负责。

## 6. Client Search 示例

以下只说明结构关系，不是固定项目模板或 Case 答案。

```python
JudgeInvestigationContract(
    evaluation_dimensions=(
        EvaluationDimension(
            dimension_id="user-search-intent-alignment",
            dimension_type="user_expectation",
            name="用户搜索意图承接",
            evaluation_target=(
                "用户表达的客户筛选目标、条件和组合关系，与 Live 生成的查询语义之间的对应关系"
            ),
            expected_result="查询完整且准确地表达用户希望筛选的客户集合",
            required_evidence=(
                "用户原始搜索需求及已确认的上下文",
                "Live 输出的结构化查询条件",
            ),
            fulfilled_when=(
                "查询保留用户的核心筛选条件和组合语义",
                "查询没有增加用户未表达的强约束",
            ),
            not_fulfilled_when=(
                "遗漏或错误解释会改变目标客户集合的核心条件",
                "增加用户未表达且会改变结果集的强约束",
            ),
            not_evaluable_when=(
                "用户意图本身存在决定性歧义且未获得澄清",
                "Live 没有产生可观察的查询输出",
            ),
            acceptable_equivalence=(
                "不同字段或操作符形式在查询语义或结果集等价时可以接受",
            ),
            tool_requirement_ids=("client_search.semantic_query_compare",),
            evidence_ref_ids=("search-contract", "judge-boundary"),
        ),
        EvaluationDimension(
            dimension_id="elasticsearch-downstream-usability",
            dimension_type="downstream_usability",
            name="Elasticsearch 下游可用性",
            evaluation_target=(
                "Live 生成的结构化查询，与 Elasticsearch 字段、枚举、操作符和查询结构能力之间的兼容关系"
            ),
            expected_result="ES 能够合法执行该查询，并用它搜索符合用户意图的客户集合",
            required_evidence=(
                "Live 输出的结构化查询条件",
                "ES 字段、枚举、操作符和查询结构定义",
                "可用时的真实执行结果或等价查询结果",
            ),
            fulfilled_when=(
                "查询使用 ES 支持的字段、枚举和操作符",
                "查询结构能被 ES 合法消费和执行",
            ),
            not_fulfilled_when=(
                "使用不存在或不适用的字段、枚举或操作符",
                "生成 ES 无法消费的查询结构",
            ),
            not_evaluable_when=(
                "缺少决定性的 ES schema 或查询能力信息",
                "既无法执行查询，也无法可靠判断其协议兼容性",
            ),
            acceptable_equivalence=(
                "能够产生等价查询语义或结果集的结构差异可以接受",
            ),
            tool_requirement_ids=("client_search.semantic_query_compare",),
            evidence_ref_ids=("es-schema", "search-contract"),
        ),
    ),
    judge_boundary=JudgeBoundary(
        live_role="把用户的自然语言客户搜索需求转换为下游搜索服务可消费的结构化查询",
        in_scope_responsibilities=(
            "正确承接用户已经表达或确认的搜索意图",
            "生成符合 ES 已知能力的字段、值、操作符和查询逻辑",
            "避免遗漏核心条件或增加错误强约束",
        ),
        out_of_scope_conditions=(
            "替用户决定未表达且无法从上下文确认的业务条件",
            "创建 ES 当前不存在的业务数据",
        ),
        external_system_constraints=(
            "ES 不存在用户希望搜索的字段",
            "ES 数据源中不存在目标客户数据",
            "系统无法控制的服务上线和数据限制",
        ),
        authoritative_evidence=(
            "用户原始需求和已确认上下文",
            "ES 字段、枚举和查询协议",
            "真实搜索结果或可执行的等价查询结果",
        ),
        supporting_evidence=(
            "Prompt",
            "项目配置",
            "当前实现和后处理规则",
        ),
        global_not_evaluable_conditions=(
            "缺少用户输入或 Live 最终输出",
            "缺少判断所有核心纬度所必需的外部合同，且不存在替代权威证据",
        ),
        evidence_ref_ids=("judge-boundary", "es-schema", "search-contract"),
    ),
)
```

该示例中没有单独的 `BusinessOutcomeContract`：用户搜索意图对应输入侧纬度，ES 消费对应输出侧纬度；Live 的职责及 ES 外部限制由共享的 `JudgeBoundary` 约束。三者共同形成完整判断链，但不存在两套重复描述。

## 7. 调查生成要求

执行 `/draft investigate` 且 `role=judge` 时，Harness AI 必须：

1. 读取 Judge ROLE 允许的用户输入、reference、可观察业务输出、外部业务合同、下游消费协议和合法 Comparator 材料；
2. 调查用户实际希望 Live 理解并交付什么，形成至少一个 `user_expectation` 纬度；
3. 调查 Live 输出实际交给谁、怎样被消费、消费者具备什么能力和限制，形成至少一个 `downstream_usability` 纬度；
4. 只有在真实业务证据表明存在独立质量轴时，才生成 `project_specific` 纬度；
5. 从现有 `judge_boundary` 和权威业务资料中提炼 Live 角色、职责、外部限制、证据优先级和全局不可评估条件；
6. 为需要执行验证的纬度登记既有 `ToolRequirement`，不得在调查 JSON 中伪造 Callable；
7. 写入 `docs/judge-investigation-contract.json` 并登记到 Manifest artifacts；
8. 在 `overview.md` 中说明适用范围和 unresolved，但不复制整个 JSON。

不得根据当前实现、Prompt 或模型常识补造用户期望、下游能力或业务标准。无法确认时必须记录 `unresolved_reason`，并在相关纬度中保留相应的 `not_evaluable` 条件。

## 8. 审查与落实机制

### 8.1 结构门禁

`validate_investigation.py` 对 `role=judge` 必须检查：

- 强制 artifact 存在并能反序列化为 `JudgeInvestigationContract`；
- `dimension_id` 唯一；
- `dimension_type` 只能取协议允许值；
- 至少存在一个 `user_expectation` 和一个 `downstream_usability` 纬度；
- 每个纬度都有具体 `evaluation_target`、`expected_result`、required evidence 和三态条件；
- 每个 `tool_requirement_ids` 引用当前 Manifest 的真实 ToolRequirement；
- 所有 `evidence_ref_ids` 引用当前 Manifest 的真实 EvidenceRef；
- `JudgeBoundary` 的 Live 角色、职责范围、证据层级和全局不可评估条件非空；
- 文件不含 iteration case ID、promotion-only unseen case、目标答案、当前判定结果或候选施工指令。

结构门禁失败时不得进入 Solidify。

### 8.2 Investigate → Solidify 语义交接审查

Harness AI 在 Solidify 前必须逐项确认：

- `user_expectation` 是否明确连接用户输入与 Live 输出，而不是泛泛描述“理解正确”；
- `downstream_usability` 是否明确连接 Live 输出与真实消费能力，而不是只写下游名称；
- `expected_result` 是否表达具体业务结果，而不是重复纬度名称；
- 三态条件是否互斥、保守且有相应证据要求；
- `acceptable_equivalence` 是否避免把无业务影响的形式差异误判为失败；
- `JudgeBoundary` 是否只定义共享归责与证据边界，没有重复具体纬度结论；
- Live 职责和外部系统限制是否得到正确区分；
- 关键 ToolRequirement 是否已实现，或其 implementation gap 是否阻断本轮判断改善。

关键纬度、边界或证据缺失时，路由回 Investigate 或标记本轮 unresolved，不得假装调查充分。

### 8.3 Solidify 落实审查

Judge Solidify 必须建立以下可复查映射：

```text
EvaluationDimension / JudgeBoundary
  → 固化的 ContextUnit、Comparator Tool 或候选 Judge 逻辑
  → runtime BusinessExpectation / FulfillmentAssessment / audit
```

并通过真实 project loader 完成：

- mandatory Context 注册与确定性装载检查；
- Tool smoke（若声明 Comparator、外部 API 或协议检查）；
- 候选 Judge 实例化；
- 用户期望满足、用户期望偏离、下游可用、下游不可用和证据不足对照运行；
- 检查 blocking 在比较 actual 前确定；
- 检查候选真实消费固化资产，没有把 JSON 示例、Case 或固定答案写死；
- 检查基础设施失败、证据缺失和业务 `not_fulfilled` 没有混淆。

未建立映射、候选未消费调查产物或三态边界未落实时，Solidify 失败。

### 8.4 Draft Loop 审查

Current/Draft 比较仍遵守现有冻结协议。Judge Review 必须检查：

- expectation 是否原子、业务相关，并由当前用户意图、reference 和调查纬度支持；
- 用户期望承接和下游可用性是否都得到实际判断；
- blocking 是否在观察 actual 前确定；
- `fulfilled` 是否有足够外部证据；
- `not_fulfilled` 是否确认了 Live 职责内的真实业务差异；
- 证据不足是否保持 `not_evaluable`；
- 是否正确处理外部能力限制和业务等价；
- 是否泄露或依赖内部实现、Attribute 根因或 promotion-only unseen case；
- Draft 是否相对 Current 提高判断准确性且无可见退化。

只有 Draft 被证明更好且无退化时，才可建议 Promotion。

## 9. 与现有公共协议的关系

- 本结构是 Judge 调查包的强制 artifact，不替代 `InvestigationManifest`；
- Evidence、artifact、ToolRequirement 和 unresolved 继续使用现有公共字段；
- 不增加或复制 `BusinessExpectation`、`FulfillmentAssessment`、`JudgeResult` 和 overall 聚合 schema；
- 当前 Case 输入、actual 和 reference 继续通过 Judge 请求显式传入；
- 完整调查 JSON 不直接进入 Prompt；
- Judge 默认不读取内部源码、内部 trace 或 Attribute 候选调查包；
- promotion-only unseen case 不得进入调查结构；
- Judge 与 Mock 调查包独立演进，是否共享相同 dataclass 留待后续独立决策。

# 第二章：Changes

## 10. 当前状态与目标差异

当前 Judge 已有 `BusinessExpectation`、`FulfillmentAssessment`、`JudgeResult`、三态聚合、Judge evidence view、项目 `judge_boundary` 文档和 mandatory Context 机制，但与本协议仍有以下差异：

1. Judge 没有强制的结构化调查合同，业务验收知识仍分散在 overview、evaluation、judge、judge_boundary、项目配置和代码中；
2. 用户期望承接和下游可用性尚未作为强制调查纬度统一生成；
3. 现有 `downstream_consumer` 多为简单字符串，不能表达 Live 输出为了被真实下游有效使用必须满足什么；
4. 现有 `judge_boundary` 主要是 Markdown 或项目配置，未统一为带 EvidenceRef 的职责与证据边界；
5. 各纬度的三态条件、业务等价与所需 Comparator 没有统一结构；
6. validator 只验证公共 Manifest、EvidenceRef、ToolRequirement 和 artifact 路径，不验证本 spec 的类型覆盖和语义关系；
7. Solidify 没有强制证明候选实际消费评估纬度和 JudgeBoundary；
8. Draft Loop 虽有正常、失败和信息不足要求，但没有逐项回到结构化调查合同审查。

## 11. 一次性改造任务

### Task 1：增加 schema 与 JSON 边界

- 新增 `JudgeInvestigationContract`、`EvaluationDimension` 和 `JudgeBoundary`；
- 提供严格的 JSON serialize/deserialize；
- 保持现有 `InvestigationManifest` 和 Judge runtime schema 不变。

### Task 2：更新 Judge ROLE 与模板

- 将 `docs/judge-investigation-contract.json` 加入 Judge 调查强制产物；
- 在 Judge ROLE 中写入用户期望承接、下游可用性、三态边界和 JudgeBoundary 调查要求；
- 在 Draft reference 中提供空模板和最小示例；
- 更新 `MAP.md` 指向模板与门禁。

### Task 3：扩展调查 validator

- 对 `role=judge` 执行本 spec 的结构门禁；
- 校验 dimension ID/type、两类强制纬度、EvidenceRef 和 ToolRequirement；
- 保持其他 Role 的公共调查包行为不变。

### Task 4：迁移项目 Judge 调查材料

- 从现有 application、evaluation、judge、judge_boundary、外部业务合同和下游协议提炼结构化纬度与边界；
- 优先迁移 `client_search`，验证用户搜索意图、ES 消费能力、查询等价语义和外部数据边界；
- 原 Markdown 只保留必要的人类说明或明确成为 JSON 的来源材料，避免形成两套冲突真相源。

### Task 5：增加 Solidify 落实审查

- 要求记录“调查纬度/边界 → 固化资产 → runtime observable”的映射；
- 在 Judge Solidify smoke 中执行输入侧、输出侧和证据不足对照；
- 检查候选真实消费资产且没有写死 Case、expected 或 verdict；
- 关键纬度或边界未落实时阻断 Draft Loop。

### Task 6：更新 Draft Loop Review

- 在 Judge Review 中加入两类强制纬度和 JudgeBoundary 的落实检查；
- 保持 Current/Draft 冻结、unseen 隔离和 Promotion 授权规则不变；
- 不把调查纬度 ID 写入 `JudgeResult` 公共 schema。

### Task 7：测试与文档同步

- 增加 dataclass round-trip、结构失败、引用失败和跨 Role 隔离测试；
- 增加缺失强制 artifact、缺失强制纬度、三态缺失、未实现关键 Tool 和未消费资产的失败测试；
- 增加 client_search 用户意图承接、下游可执行、语义等价、ES 不可用和证据不足代表测试；
- 同步 `spec/alg/investigate.md`、Draft Skill、Judge ROLE、MAP 和参考模板。

## 12. 一次性改造验收

- 每个 Judge 调查包都生成并登记 `judge-investigation-contract.json`；
- validator 能阻止缺失、非法引用、强制纬度缺失和三态不完整；
- `user_expectation` 纬度明确连接用户输入与 Live 输出；
- `downstream_usability` 纬度明确连接 Live 输出与真实下游消费约束；
- `JudgeBoundary` 只承接 Live 职责、外部限制和证据优先级，不重复具体纬度结论；
- Judge Solidify 能证明纬度和边界已落实到实际判断；
- 输入侧、输出侧和证据不足对照分别得到有依据的三态结果；
- Judge runtime public schema 未被复制或污染；
- Current/Draft 比较证明判断准确性改善且无可见退化后，才提出 Promotion 建议。
