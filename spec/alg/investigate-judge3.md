# Judge 调查协议

# 第一章：Spec 标准

## 1. 目标与定位

Judge Investigate 的目标，是为 Judge 提供一份稳定、可审查的业务判断依据，使其能够基于外部可观察证据判断 Live 是否满足业务期望。

Judge 调查通常从两类常见关系开始，但不限于这两类：

```text
用户输入 / 用户期望
  → Live 输出是否正确承接用户意图

Live 输出
  → 是否能被真实下游用户或系统有效使用
```

Live 系统自身的角色和职责不作为一个评估纬度。它属于所有评估纬度共享的责任边界，用于回答：哪些结果应归责给 Live，哪些限制来自外部系统。

因此，长期调查结构只保留三个核心概念：

```text
EvaluationDimension
  定义 Judge 具体评估什么，以及如何作出三态判断

LiveBoundary
  定义所有评估纬度共享的 Live 职责和外部限制

EvidencePolicy
  定义 Judge 采用什么证据，以及证据不足时如何保持保守
```

其中，Judge 调查包默认优先考虑：

1. 用户期望承接：Live 是否正确理解并满足用户真实意图；
2. 下游可用性：Live 输出是否能被真实下游用户或系统有效消费。

这两项只是常见默认方向，不是封闭类型，也不是每个项目都必须生成的固定纬度。调查应根据真实业务形成其他纬度；默认方向不适用时，应在 `overview.md` 说明理由。

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


@dataclass(frozen=True)
class JudgeInvestigationContract:
    evaluation_dimensions: tuple[EvaluationDimension, ...]
    live_boundary: LiveBoundary
    evidence_policy: EvidencePolicy


@dataclass(frozen=True)
class EvaluationDimension:
    dimension_id: str
    # 开放分类；协议仅推荐常见值，不限制项目定义其他稳定类型。
    dimension_type: str
    name: str

    # 本纬度评估的具体外部关系或业务结果。
    evaluation_target: str

    # 该关系成立时，业务上应得到什么结果。
    expected_result: str

    # 当前 Case 数据满足什么条件时，本纬度进入评估。
    # 描述数据侧的可观察特征，不是业务判断规则。
    applicable_when: tuple[str, ...]

    # 什么差异会阻断业务目标；必须在观察 actual 前确定。
    materiality_rule: str

    # 作出判断必须观察到哪些外部业务事实。
    required_evidence: tuple[str, ...]

    # 本纬度的三态判断条件。
    fulfilled_when: tuple[str, ...]
    not_fulfilled_when: tuple[str, ...]
    not_evaluable_when: tuple[str, ...]

    # 哪些可观察差异存在，但不影响本纬度的业务判断。
    # 不存在已确认允许差异时为空元组。
    non_material_variations: tuple[str, ...]

    # 需要 Comparator、外部业务 API 或协议检查时，引用既有 ToolRequirement。
    tool_requirement_ids: tuple[str, ...]

    # 引用当前 InvestigationManifest.evidence_refs 中的 ref_id。
    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class LiveBoundary:
    # Live 在真实业务链路中扮演什么角色。
    live_role: str

    # Live 必须对哪些用户可见或下游可消费结果负责。
    in_scope_responsibilities: tuple[str, ...]

    # 哪些事项明确不属于 Live 的职责。
    out_of_scope_conditions: tuple[str, ...]

    # 哪些上游、下游或环境限制不能自动归责为 Live 失败。
    external_system_constraints: tuple[str, ...]

    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvidencePolicy:
    # 哪些来源可作为业务判断的硬依据。
    authoritative_evidence: tuple[str, ...]

    # 哪些来源只能辅助理解，不能成为绝对标准。
    supporting_evidence: tuple[str, ...]

    # 不同来源发生冲突时如何确定证据优先级。
    conflict_resolution: tuple[str, ...]

    # 哪些全局证据缺失时，Judge 必须保持 not_evaluable。
    global_not_evaluable_conditions: tuple[str, ...]

    evidence_ref_ids: tuple[str, ...]
```

## 4. Schema 语义

### 4.1 `EvaluationDimension`

`EvaluationDimension` 是 Judge 调查包的主体。每个实例必须定义一个可独立判断的业务质量轴，并完整回答：

- 当前数据满足什么条件时本纬度适用；
- 评估什么外部关系或业务结果；
- 该关系成立时预期产生什么结果；
- 什么差异会阻断业务目标；
- 判断需要哪些证据；
- 什么情况下分别属于三态；
- 哪些差异存在但不影响业务判断；
- 是否需要 Comparator 或外部 Tool。

`evaluation_target` 不得只填写“正确性”“质量”或“可用性”等抽象词，而应明确被比较的两端。例如：

```text
用户表达的筛选意图 ↔ Live 生成的查询语义
Live 生成的结构化查询 ↔ Elasticsearch 的真实消费能力
```

`expected_result` 表达该纬度服务的具体业务结果，因此无需再建立一份与纬度平行且重复的 `BusinessOutcomeContract`。

`applicable_when` 描述当前 Case 的数据满足什么可观察特征时，本纬度才进入评估。它回答的是"该不该评"，不是"判不判得了"。例如：

```text
# client_search "ES 下游可用性"
applicable_when=("Live 输出了结构化查询条件",)

# QA "用户事实保持"
applicable_when=("用户在当前或历史轮次中表达了具体业务事实或目标",)
```

`applicable_when` 与 `not_evaluable_when` 的职责必须切清：

```text
applicable_when 不满足 → 纬度不适用（not_applicable），不进入三态判断
applicable_when 满足，但证据不足 → not_evaluable
applicable_when 满足，证据充分 → fulfilled / not_fulfilled
```

因此 `not_evaluable_when` 中不应再写适用性条件。"Live 没有产生可观察的查询输出"是适用性问题，属于 `applicable_when`；"用户意图存在决定性歧义且未获澄清"是证据不足问题，属于 `not_evaluable_when`。

`materiality_rule` 定义本纬度上的差异何时会阻断业务目标。它必须在观察当前 actual 前确定，用于指导当前 Case 生成 blocking expectation，而不是在调查包中写死每个 Case 的 `blocking=True/False`。

`non_material_variations` 记录可以被观察到、但不改变本纬度业务结论的差异。它比”等价”更通用，可以表达语义等价、顺序差异、数值容差、合法结构变体和非确定性措辞。对输出可形式化比较的项目（结构化查询、字段提取等），该字段价值较高；对纯自然语言输出项目，不存在已确认允许差异时保持空元组即可，不必强行枚举。不得用它豁免会改变业务结果的真实偏差。

#### 开放的纬度类型

`user_expectation` 评估输入侧关系：Live 输出是否正确承接用户的真实意图、限制和期望结果。

`downstream_usability` 评估输出侧关系：Live 输出是否满足真实下游用户或系统的消费方式、能力和约束，并能支持其继续完成业务任务。它不能只记录“下游是谁”，还必须体现“Live 输出为了被该下游有效使用，必须满足什么”。

上述值只是常见建议，不构成枚举。项目可以定义任意有真实业务证据支持的稳定 `dimension_type`，也可以为同一类型生成多个纬度。生成器必须主动考虑用户期望和下游可用性，但不得为了满足固定类型数量而制造不适用的纬度。

#### 三态要求

- `fulfilled`：现有证据足以证明该纬度的预期结果得到满足；
- `not_fulfilled`：现有证据足以证明 Live 职责范围内存在真实业务差异；
- `not_evaluable`：缺少决定性输入、actual、reference、外部合同或 Comparator 事实，无法可靠判断。

三态条件必须互斥且保守。文本更长、字段更多、confidence 更高，或内部实现更接近当前 Prompt，都不构成 `fulfilled` 证据。

### 4.2 `LiveBoundary`

`LiveBoundary` 不是一个评估纬度，也不重复各纬度的具体三态条件。它是所有纬度共享的 Live 责任边界。

它只回答以下问题：

- Live 在业务链路中承担什么角色；
- 哪些结果由 Live 控制并应对其负责；
- 哪些事项不属于 Live 职责；
- 哪些外部限制不能直接转化为 Live 失败。

`LiveBoundary` 不得包含“查询语义正确”“结果对用户有帮助”等具体纬度结论，也不得承担 Judge 的证据优先级；这些内容分别属于 `EvaluationDimension` 和 `EvidencePolicy`。

### 4.3 `EvidencePolicy`

`EvidencePolicy` 定义 Judge 的项目级证据规则，回答：

- 哪些来源可以作为业务判断的硬依据；
- 哪些来源只能辅助理解；
- 来源冲突时采用什么优先级；
- 缺少哪些全局事实时不得强判。

`EvaluationDimension.required_evidence` 描述某个纬度需要观察什么事实；`EvidencePolicy` 描述这些事实应从什么来源取得以及冲突时相信谁。二者不可互相替代。

内部源码、内部 trace 或 Attribute 根因默认不能作为 Judge 把外部结果判失败的依据。外部依赖不可用也不能自动转化为 Live 语义错误：若仍可从现有输出和权威业务合同判断某一纬度，应继续判断；否则该纬度保持 `not_evaluable`。

## 5. 调查结构到运行时的流转

```text
当前用户输入 / reference / 外部业务合同 / Live actual
  + 全部 EvaluationDimension
        ↓
  逐纬度检查 applicable_when
    ├── 不满足 → not_applicable（判断前分流，不参与三态聚合）
    └── 满足 → 进入三态判断
          ↓
        生成当前 Case 的 BusinessExpectation
        LiveBoundary → 约束 Live 归责范围
        EvidencePolicy → 约束证据优先级和全局不可评估边界
          ↓
        fulfilled / not_fulfilled / not_evaluable

FulfillmentAssessment[]
  → 现有协议按预先确定的 blocking expectation 聚合 overall status
  → not_applicable 的 expectation 不参与 overall 聚合
```

`not_applicable` 是判断前的分流，不是第四态。运行时为每个不适用的纬度保留一条 `not_applicable` 标记记录，用于审计 Draft 是否正确识别了适用性，但不进入三态判断，也不影响 overall status 计算。三态词表和 overall 聚合继续由现有 Judge 协议代码负责，不因 `not_applicable` 修改 public schema。

调查结构不能预先保存某个 Case 的 `expectation_id`、expected 答案或 fulfillment 状态。运行时 expectation 由当前 Case 的用户意图、reference 和调查结构共同实例化。

## 6. 示例

以下只说明结构关系，不是固定项目模板或 Case 答案。

### 6.1 Client Search（结构化输出 + 明确下游）

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
            applicable_when=(
                "用户表达了客户搜索或筛选意图",
                "Live 产生了可观察的查询输出",
            ),
            materiality_rule=(
                "会改变目标客户集合的意图偏差属于 blocking；"
                "不影响搜索结果的表达差异不属于 blocking"
            ),
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
            ),
            non_material_variations=(
                "字段或操作符形式不同，但查询语义等价",
                "条件排列顺序不同，但不改变逻辑关系",
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
            applicable_when=(
                "Live 输出了结构化查询条件",
            ),
            materiality_rule="导致查询无法执行或结果集语义错误的问题属于 blocking",
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
            non_material_variations=(
                "查询 DSL 结构不同，但执行语义等价",
                "使用不同合法字段映射，但返回客户集合等价",
            ),
            tool_requirement_ids=("client_search.semantic_query_compare",),
            evidence_ref_ids=("es-schema", "search-contract"),
        ),
    ),
    live_boundary=LiveBoundary(
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
        evidence_ref_ids=("judge-boundary", "es-schema", "search-contract"),
    ),
    evidence_policy=EvidencePolicy(
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
        conflict_resolution=(
            "用户已确认的意图优先于 Prompt 中的默认假设",
            "ES 当前生效协议优先于代码中写死的字段假设",
            "真实执行结果优先于对查询结构的表面推断",
        ),
        global_not_evaluable_conditions=(
            "缺少用户输入或 Live 最终输出",
            "缺少判断所有核心纬度所必需的外部合同，且不存在替代权威证据",
        ),
        evidence_ref_ids=("judge-boundary", "es-schema", "search-contract"),
    ),
)
```

该示例中没有单独的 `BusinessOutcomeContract`：用户搜索意图和 ES 消费分别成为两个真实业务纬度；Live 的职责及 ES 外部限制由 `LiveBoundary` 约束；Schema、Prompt、代码和真实执行结果冲突时的采信规则由 `EvidencePolicy` 约束。三者共同形成完整判断链，但不存在两套重复描述。

### 6.2 QA 多轮咨询（自然语言输出、无结构化 reference）

```python
JudgeInvestigationContract(
    evaluation_dimensions=(
        EvaluationDimension(
            dimension_id="user-intent-fulfillment",
            dimension_type="user_expectation",
            name="用户意图满足",
            evaluation_target=(
                "用户在当前轮及历史轮次中表达的完整意图 "
                "↔ Live 当前轮回答对该意图的承接和满足程度"
            ),
            expected_result="回答直接回应用户当前问题，不遗漏历史轮已确认的关键约束",
            applicable_when=(
                "用户表达了具体的业务问题或信息需求",
            ),
            materiality_rule=(
                "答非所问、遗漏用户已明确表达的核心问题、"
                "或给出与用户意图无关的信息属于 blocking"
            ),
            required_evidence=(
                "用户当前轮输入及历史轮次上下文",
                "Live 当前轮完整回答",
            ),
            fulfilled_when=(
                "回答直接针对用户当前问题",
                "历史轮已确认的约束未被丢弃或篡改",
            ),
            not_fulfilled_when=(
                "回答偏离用户核心意图",
                "遗漏用户在历史轮明确给出的关键条件",
            ),
            not_evaluable_when=(
                "用户意图本身存在决定性歧义且未获澄清",
                "缺少历史轮上下文，无法判断当前回答是否承接",
            ),
            non_material_variations=(
                "措辞和表述方式不同但语义等价",
                "回答详细程度不同但核心信息完整",
            ),
            tool_requirement_ids=(),
            evidence_ref_ids=("qa-business-contract",),
        ),
        EvaluationDimension(
            dimension_id="factual-accuracy",
            dimension_type="downstream_usability",
            name="业务事实准确性",
            evaluation_target=(
                "Live 回答中涉及的业务事实 ↔ 权威业务知识库或条款中的真实规则"
            ),
            expected_result="回答中的业务规则、数值、流程与权威来源一致",
            applicable_when=(
                "Live 回答包含可验证的业务事实性陈述",
            ),
            materiality_rule="会导致用户做出错误业务决策的事实错误属于 blocking",
            required_evidence=(
                "Live 回答中的事实性陈述",
                "对应的权威业务条款或知识库内容",
            ),
            fulfilled_when=("事实性陈述与权威来源一致",),
            not_fulfilled_when=("存在与权威来源矛盾的事实性错误",),
            not_evaluable_when=(
                "缺少对应的权威来源进行比对",
            ),
            non_material_variations=(
                "数值精度差异但不影响业务判断",
            ),
            tool_requirement_ids=(),
            evidence_ref_ids=("qa-knowledge-base",),
        ),
    ),
    live_boundary=LiveBoundary(
        live_role="基于用户多轮对话提供业务咨询回答",
        in_scope_responsibilities=(
            "正确理解并回答用户当前轮问题",
            "保持多轮上下文一致性",
            "基于权威业务知识给出准确信息",
        ),
        out_of_scope_conditions=(
            "替用户做出业务决策",
            "处理超出知识库范围的问题",
        ),
        external_system_constraints=(
            "知识库本身内容缺失或过时",
            "用户提供的个人信息不真实",
        ),
        evidence_ref_ids=("qa-business-contract",),
    ),
    evidence_policy=EvidencePolicy(
        authoritative_evidence=(
            "用户原始输入及历史轮上下文",
            "权威业务条款和知识库",
        ),
        supporting_evidence=(
            "Prompt 中的回答风格要求",
            "项目配置",
        ),
        conflict_resolution=(
            "权威业务条款优先于模型常识",
            "用户已确认的意图优先于 Prompt 默认假设",
        ),
        global_not_evaluable_conditions=(
            "缺少用户输入或 Live 回答",
            "缺少历史轮上下文且当前轮依赖历史信息",
        ),
        evidence_ref_ids=("qa-business-contract", "qa-knowledge-base"),
    ),
)
```

该示例体现自然语言输出项目的特点：`tool_requirement_ids` 为空元组，判断主要依赖 LLM 语义理解而非确定性 Comparator；`applicable_when` 按数据特征分流——用户未提出具体问题时"用户意图满足"不适用，回答未包含事实性陈述时"业务事实准确性"不适用。

## 7. 调查生成要求

执行 `/draft investigate` 且 `role=judge` 时，Harness AI 必须：

1. 读取 Judge ROLE 允许的用户输入、reference、可观察业务输出、外部业务合同、下游消费协议和合法 Comparator 材料；
2. 默认调查用户实际希望 Live 理解并交付什么，以及 Live 输出实际交给谁、怎样被消费、消费者具备什么能力和限制；
3. 根据真实业务形成开放的 `EvaluationDimension[]`，不得用固定类型列表代替调查；
4. 对每个纬度调查其数据侧适用条件（`applicable_when`），明确什么数据特征使该纬度进入评估；
5. 对每个纬度调查业务严重性和不影响结论的允许差异；
6. 从现有 `judge_boundary` 和权威业务资料中分别提炼 `LiveBoundary` 与 `EvidencePolicy`；
7. 为需要执行验证的纬度登记既有 `ToolRequirement`，不得在调查 JSON 中伪造 Callable；不需要 Comparator 的纬度保持 `tool_requirement_ids` 为空，不得视为缺陷；
8. 写入 `docs/judge-investigation-contract.json` 并登记到 Manifest artifacts；
9. 在 `overview.md` 中说明适用范围和 unresolved，但不复制整个 JSON。

不得根据当前实现、Prompt 或模型常识补造用户期望、下游能力或业务标准。无法确认时必须记录 `unresolved_reason`，并在相关纬度中保留相应的 `not_evaluable` 条件。

## 8. 审查与落实机制

### 8.1 结构门禁

`validate_investigation.py` 对 `role=judge` 必须检查：

- 强制 artifact 存在并能反序列化为 `JudgeInvestigationContract`；
- `evaluation_dimensions` 非空；
- `dimension_id` 唯一；
- `dimension_type` 非空且在同一项目内使用稳定命名，但不限制取值集合；
- 每个纬度都有具体 `evaluation_target`、`expected_result`、`applicable_when`、`materiality_rule`、required evidence 和三态条件；
- `applicable_when` 非空，且描述的是数据侧可观察特征而非业务判断规则；
- `not_evaluable_when` 中不含适用性条件（应属于 `applicable_when`）；
- `non_material_variations` 允许为空元组；
- 每个 `tool_requirement_ids` 引用当前 Manifest 的真实 ToolRequirement；
- 所有 `evidence_ref_ids` 引用当前 Manifest 的真实 EvidenceRef；
- `LiveBoundary` 的 Live 角色和职责范围非空；
- `EvidencePolicy` 的权威证据、冲突处理和全局不可评估条件非空；
- 文件不含 iteration case ID、promotion-only unseen case、目标答案、当前判定结果或候选施工指令。

结构门禁失败时不得进入 Solidify。

### 8.2 Investigate → Solidify 语义交接审查

Harness AI 在 Solidify 前必须逐项确认：

- 是否实际考虑了用户期望和下游可用性；若未形成对应纬度，是否有真实的不适用理由；
- `expected_result` 是否表达具体业务结果，而不是重复纬度名称；
- `applicable_when` 是否描述数据侧可观察特征，而非业务判断规则；是否覆盖该纬度真正进入评估的数据前提；
- `applicable_when` 与 `not_evaluable_when` 是否切清：适用性条件不在 `not_evaluable_when` 中重复；
- `materiality_rule` 是否能在观察 actual 前指导 blocking 判断；
- 三态条件是否互斥、保守且有相应证据要求；
- `non_material_variations` 是否覆盖已知的非实质差异，并避免豁免真实业务偏差；
- `LiveBoundary` 是否只定义共享责任边界，没有重复具体纬度结论；
- `EvidencePolicy` 是否明确权威来源、辅助来源、冲突优先级和全局证据不足；
- Live 职责和外部系统限制是否得到正确区分；
- 关键 ToolRequirement 是否已实现，或其 implementation gap 是否阻断本轮判断改善。

关键纬度、边界或证据缺失时，路由回 Investigate 或标记本轮 unresolved，不得假装调查充分。

### 8.3 Solidify 落实审查

Judge Solidify 必须建立以下可复查映射：

```text
EvaluationDimension / LiveBoundary / EvidencePolicy
  → 固化的 ContextUnit、Comparator Tool 或候选 Judge 逻辑
  → runtime BusinessExpectation / FulfillmentAssessment / audit
```

并通过真实 project loader 完成：

- mandatory Context 注册与确定性装载检查；
- Tool smoke（若声明 Comparator、外部 API 或协议检查）；
- 候选 Judge 实例化；
- 对当前项目的关键纬度执行满足、偏离和证据不足对照运行；
- 检查 blocking 在比较 actual 前确定；
- 检查候选真实消费固化资产，没有把 JSON 示例、Case 或固定答案写死；
- 检查基础设施失败、证据缺失和业务 `not_fulfilled` 没有混淆。

未建立映射、候选未消费调查产物或三态边界未落实时，Solidify 失败。

### 8.4 Draft Loop 审查

Current/Draft 比较仍遵守现有冻结协议。Judge Review 必须检查：

- expectation 是否原子、业务相关，并由当前用户意图、reference 和调查纬度支持；
- 当前 Case 适用的关键业务纬度是否得到实际判断；
- `not_applicable` 分流是否正确：是否把应当适用的纬度错误标记为不适用，或把不适用的纬度强行判断；
- blocking 是否在观察 actual 前确定；
- `fulfilled` 是否有足够外部证据；
- `not_fulfilled` 是否确认了 Live 职责内的真实业务差异；
- 证据不足是否保持 `not_evaluable`；
- 是否正确处理外部能力限制和非实质差异；
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
- Judge 与 Mock 调查包独立演进，是否共享相同 dataclass 留待后续独立决策；
- Judge 的 `applicable_when` 与 Mock 的 `EvaluationDimensionCoverage.mock_data_requirement` 是同一件事的两面：Judge 定义"数据满足什么条件时纬度适用"，Mock 定义"要检验该纬度数据必须具备什么"。现阶段不强制共享，但两侧调查应互相参照；长期 Judge 合同先于 Mock 生成时，Mock 可直接读取 `applicable_when` 作为输入。

# 第二章：Changes

## 10. 当前状态与目标差异

当前 Judge 已有 `BusinessExpectation`、`FulfillmentAssessment`、`JudgeResult`、三态聚合、Judge evidence view、项目 `judge_boundary` 文档和 mandatory Context 机制，但与本协议仍有以下差异：

1. Judge 没有强制的结构化调查合同，业务验收知识仍分散在 overview、evaluation、judge、judge_boundary、项目配置和代码中；
2. 用户期望承接和下游可用性等常见方向尚未被系统性考虑，也缺少形成开放项目纬度的统一方法；
3. 现有 `downstream_consumer` 多为简单字符串，不能表达 Live 输出为了被真实下游有效使用必须满足什么；
4. 现有 `judge_boundary` 混合了 Live 责任和 Judge 证据规则，尚未拆分为 `LiveBoundary` 与 `EvidencePolicy`；
5. 各纬度的三态条件、业务严重性、非实质差异与所需 Comparator 没有统一结构；
6. 纬度缺少数据侧适用条件（`applicable_when`），"不适用"和"证据不足"混在 `not_evaluable_when` 中无法区分；
7. validator 只验证公共 Manifest、EvidenceRef、ToolRequirement 和 artifact 路径，不验证本 spec 的开放类型和语义关系；
8. Solidify 没有强制证明候选实际消费评估纬度、`LiveBoundary` 和 `EvidencePolicy`；
9. Draft Loop 虽有正常、失败和信息不足要求，但没有逐项回到结构化调查合同审查，也不检查适用性分流正确性。

## 11. 一次性改造任务

### Task 1：增加 schema 与 JSON 边界

- 新增 `JudgeInvestigationContract`、`EvaluationDimension`、`LiveBoundary` 和 `EvidencePolicy`；
- `EvaluationDimension` 包含 `applicable_when`；
- 提供严格的 JSON serialize/deserialize；
- 保持现有 `InvestigationManifest` 和 Judge runtime schema 不变。

### Task 2：更新 Judge ROLE 与模板

- 将 `docs/judge-investigation-contract.json` 加入 Judge 调查强制产物；
- 在 Judge ROLE 中写入开放纬度、业务严重性、非实质差异、`LiveBoundary` 和 `EvidencePolicy` 调查要求；
- 在 Draft reference 中提供空模板和最小示例；
- 更新 `MAP.md` 指向模板与门禁。

### Task 3：扩展调查 validator

- 对 `role=judge` 执行本 spec 的结构门禁；
- 校验 dimension ID、开放 type、`applicable_when` 非空、materiality、EvidenceRef 和 ToolRequirement，不维护封闭类型枚举；
- 保持其他 Role 的公共调查包行为不变。

### Task 4：迁移项目 Judge 调查材料

- 从现有 application、evaluation、judge、judge_boundary、外部业务合同和下游协议提炼结构化纬度与边界；
- 优先迁移 `client_search`，验证用户搜索意图、ES 消费能力、查询等价语义和外部数据边界；
- 原 Markdown 只保留必要的人类说明或明确成为 JSON 的来源材料，避免形成两套冲突真相源。

### Task 5：增加 Solidify 落实审查

- 要求记录“调查纬度/Live 边界/证据策略 → 固化资产 → runtime observable”的映射；
- 在 Judge Solidify smoke 中对项目关键纬度执行满足、偏离和证据不足对照；
- 检查候选真实消费资产且没有写死 Case、expected 或 verdict；
- 关键纬度、Live 边界或证据策略未落实时阻断 Draft Loop。

### Task 6：更新 Draft Loop Review

- 在 Judge Review 中加入开放纬度、`LiveBoundary` 和 `EvidencePolicy` 的落实检查；
- 保持 Current/Draft 冻结、unseen 隔离和 Promotion 授权规则不变；
- 不把调查纬度 ID 写入 `JudgeResult` 公共 schema。

### Task 7：测试与文档同步

- 增加 dataclass round-trip、结构失败、引用失败和跨 Role 隔离测试；
- 增加缺失强制 artifact、空纬度、`applicable_when` 缺失或为空、materiality 缺失、三态缺失、未实现关键 Tool 和未消费资产的失败测试；
- 增加 `not_applicable` 分流正确性测试：适用数据进入三态判断、不适用数据标记 `not_applicable` 且不参与聚合；
- 增加 client_search 用户意图承接、下游可执行、语义等价、ES 不可用和证据不足代表测试；
- 增加 QA 多轮项目自然语言输出、无 Comparator、`non_material_variations` 为空的代表测试；
- 同步 `spec/alg/investigate.md`、Draft Skill、Judge ROLE、MAP 和参考模板。

## 12. 一次性改造验收

- 每个 Judge 调查包都生成并登记 `judge-investigation-contract.json`；
- validator 能阻止缺失、非法引用、空纬度、`applicable_when` 缺失、materiality 缺失和三态不完整，同时允许项目扩展纬度类型；
- 调查会默认考虑用户期望和下游可用性，但不强制生成不适用的固定纬度；
- 每个纬度的 `applicable_when` 描述数据侧适用条件，与 `not_evaluable_when` 不重叠；运行时 `not_applicable` 正确分流且不参与三态聚合；
- `non_material_variations` 能稳定承接 client_search 的语义或结果集等价；对纯自然语言输出项目允许为空；
- `LiveBoundary` 只承接 Live 职责和外部限制，不混入证据策略；
- `EvidencePolicy` 明确证据层级、冲突处理和全局不可评估条件；
- Judge Solidify 能证明纬度、Live 边界和证据策略已落实到实际判断；
- 关键纬度的满足、偏离和证据不足对照分别得到有依据的三态结果；
- Judge runtime public schema 未被复制或污染；
- Current/Draft 比较证明判断准确性改善且无可见退化后，才提出 Promotion 建议。
