# Judge 调查协议

# 第一章：Spec 标准

## 1. 目标与定位

Judge Investigate 的目标，是调查并固化一份稳定、可审查的业务判断合同，使 Judge 能够判断：**Live 是否在自己的责任范围内，为真实业务用户使用完整产品时的目标作出了正确贡献。**

调查必须先站在完整产品用户视角理解业务期望，再把业务期望投影到 Live 的责任范围，最后设计评估 Live 贡献的维度。不得直接从 Live 的输出格式、内部协议或当前 Judge 实现反推“用户期望”。

长期调查结构只保留三个核心对象：

```text
BusinessExpectation
  真实业务用户使用完整产品时希望得到什么

LiveBoundary
  完整产品实现该期望的链路中，Live 负责什么、不负责什么

EvaluationDimension
  从什么角度判断 Live 是否为关联业务期望作出了正确贡献
```

三者的关系是：

```text
业务用户使用完整产品
        ↓
BusinessExpectation
“用户最终想得到什么”
        ↓
EvaluationDimension
“需要从哪些角度检查 Live 对该期望的贡献”
        ↓
LiveBoundary
“哪些结果可以归责于 Live”
```

业务期望可以覆盖完整产品，因而可以大于 Live 的责任范围。Judge 不能因为最终产品结果未实现，就自动判定 Live 失败；也不能把 Live 的中间输出要求伪装成用户的业务期望。

证据来源、ToolRequirement、artifact、可选 `key_indexes` 和 unresolved 继续由公共 `InvestigationManifest` 管理，不在 Judge-specific contract 中重复建立第二套来源或能力登记。Solidify 负责把调查合同固化为 Judge Context、Comparator/外部检查 Tool 和候选 Judge 逻辑，但不修改现有 `FulfillmentAssessment`、`JudgeResult` 和三态聚合协议。

## 2. 调查产物（可选结构化契约 + 权威调查报告）

`judge-investigation-contract.json` 是 Judge 调查的**可选结构化契约（需求侧方向）**：
当 Judge 需要以 BusinessExpectation / LiveBoundary / EvaluationDimension 结构化表达
产品级判断合同，或需要为权威调查（`spec/alg/investigate-authority-judge.md`）提供
覆盖方向时使用；没有需求侧输入时，调查可以退化为纯资料侧调查
（`spec/alg/investigate-authority-judge.md` §4）。存在时：

```text
impl/projects/<project>/draft/investigation/judge/
  manifest.json
  overview.md
  docs/
    judge-investigation-contract.json      # 可选（需求侧方向）
    authority-investigation-report.json    # 权威调查结构化真相源（需要时）
    authority-investigation-report.md      # 由 JSON 确定性渲染，供人工审核
```

`judge-investigation-contract.json` 若存在，必须登记到既有 `InvestigationManifest.artifacts`；
缺失、无法解析、ID 引用无效或语义审查失败时，不得进入 Judge Solidify。权威调查产物
（`authority-investigation-report.json` / `.md`）按 `spec/alg/investigate-authority-judge.md`
§15 登记与渲染。

该文件是项目级、产品级的业务判断合同，不是当前 Case 的目标答案、`JudgeResult`、Judge
Prompt 或候选实现指令。完整 JSON 不得无条件注入运行时 Prompt；Solidify 只装载当前
判断所需的最小稳定内容。

## 3. Dataclass Schema

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JudgeInvestigationContract:
    business_expectations: tuple[BusinessExpectation, ...]
    live_boundary: LiveBoundary
    evaluation_dimensions: tuple[EvaluationDimension, ...]

    # 权威调查不在本契约内复制：判断点依赖权威资料时，按
    # spec/alg/investigate-authority-judge.md 单独产出权威调查报告；
    # 本契约只通过 EvaluationDimension 提供可选的需求侧方向。


@dataclass(frozen=True)
class BusinessExpectation:
    expectation_id: str

    # 谁在使用完整产品；必须是真实业务角色，而不是 Live 或下游模块。
    user_role: str

    # 用户在什么业务情景下使用产品。
    use_scenario: str

    # 用户最终希望从完整产品获得的业务结果。
    desired_outcome: str


@dataclass(frozen=True)
class LiveBoundary:
    # Live 在完整产品业务链路中的角色。
    live_role: str

    # 为实现业务期望，哪些结果由 Live 控制并应由其负责。
    in_scope_responsibilities: tuple[str, ...]

    # 完整产品中的哪些事项明确不属于 Live 职责。
    out_of_scope_responsibilities: tuple[str, ...]

    # 哪些上游、下游、数据或环境限制不能自动归责为 Live 失败。
    external_constraints: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationDimension:
    dimension_id: str

    # 本维度服务的产品级 BusinessExpectation。
    expectation_ids: tuple[str, ...]

    name: str

    # 在 LiveBoundary 约束下，本维度具体询问 Live 的哪项贡献是否正确。
    evaluation_question: str

    # 对本问题作出三态判断的业务条件。
    fulfilled_when: tuple[str, ...]
    not_fulfilled_when: tuple[str, ...]
    not_evaluable_when: tuple[str, ...]
```

Judge-specific contract 不重复以下公共信息：

- EvidenceRef 的地址、类型和摘要；
- ToolRequirement 及其实现状态；
- artifact 路径；
- unresolved_reason。

这些信息继续通过 `InvestigationManifest` 和调查文档管理。调查合同只固化业务语义及判断边界。

### 3.1 权威调查对接（独立协议）

当多个官方项目材料对同一判断点给出不同说法，或外部验收标准能否唯一决定结论时，
Judge 的权威调查按 `spec/alg/investigate-authority-judge.md` 单独进行，不在本契约内
复制权威结论：

- 调查以**资料**为轴心：每份资料声明它在什么 `conclusion_kind + scenario + conditions`
  组合内直接决定什么（MaterialDecision），资料关系记录为 MaterialConnection；
- 需求侧方向（可选）用于识别"哪些业务事项 × 条件当前没有唯一决定资料"，以覆盖缺口
  （CoverageGap）记录缺什么料、为什么缺、未来什么证据可解除；
- 调查侧不产出任何"问题→结论"配对；最终 resolved/unresolved 由 Runtime 在证据空间
  内现场综合（`spec/alg/authority.md` §5、§14.2）。

## 4. Schema 语义

### 4.1 `BusinessExpectation`

`BusinessExpectation` 描述真实业务用户为什么使用完整产品，以及最终希望得到什么。它是产品级业务目标，不是 Live 的功能要求，也不是 Judge 的验收规则。

一个有效的业务期望必须完整回答：

```text
谁，在什么业务情景下使用产品，希望最终得到什么。
```

例如，Client Search 中有效的业务期望是：

```yaml
expectation_id: find-target-customers
user_role: 需要寻找目标客户的业务人员
use_scenario: 用户通过自然语言描述目标客户群体
desired_outcome: 用户能够得到符合其完整筛选要求的客户集合
```

以下内容不是业务期望：

```text
正确生成 age > 50 条件
生成符合 Elasticsearch 协议的 query_logic
使用正确字段、操作符和枚举
Comparator 应判断条件是否等价
```

它们分别属于当前 Case 验收项、Live 责任、评估维度或实现机制。

`BusinessExpectation` 中不得出现：

- Live 的内部步骤、Prompt、字段映射或输出 schema；
- 下游协议的具体字段、操作符或调用方式；
- Comparator、EvidenceRef、ToolRequirement；
- `blocking`、三态 verdict 或当前 Case 的 expected answer；
- 如何从当前输入实例化验收项的算法。

业务期望可以超出 Live 的能力极限。例如用户期望“得到符合要求的客户集合”，但数据库是否存在此类客户不由负责意图转换的 Live 控制。调查包应保留完整业务期望，再通过 `LiveBoundary` 限定归责范围；不得为了让期望完全落在 Live 范围内，将其缩写成“生成正确查询”。

`use_scenario` 描述该类业务期望何时存在。当前 Case 不属于该业务情景时，不为它生成运行时验收项；这属于“不适用”，不是 `not_evaluable`。

### 4.2 `LiveBoundary`

`LiveBoundary` 是完整产品业务期望到 Live 评估范围之间的共享投影边界。它只回答：

- Live 在完整业务链路中承担什么角色；
- 哪些结果由 Live 控制并应对其负责；
- 哪些完整产品能力由其他模块、用户或外部系统负责；
- 哪些外部限制不能直接转化为 Live 失败。

`LiveBoundary` 不描述具体 Case 的对错，也不重复各评估维度的三态条件。

例如，Client Search 的用户最终希望得到目标客户集合，但 Live 可能只负责把自然语言需求转换为结构化查询：

```yaml
live_role: 把自然语言客户搜索需求转换为下游搜索服务可消费的结构化查询
in_scope_responsibilities:
  - 正确承接用户已经表达或确认的搜索要求
  - 生成下游搜索服务可以消费的查询表达
out_of_scope_responsibilities:
  - 保证数据库中一定存在符合条件的客户
  - 保证客户数据完整且实时
  - 决定用户未表达且无法从上下文确认的业务条件
external_constraints:
  - 数据库中没有符合条件的客户
  - 搜索服务暂时不可用
  - 权威字段或业务数据尚未接入
```

如果 Live 查询语义正确，但数据库中没有匹配客户，完整产品的最终用户结果可能为空；Judge 仍不能将数据库数据缺失归责为 Live 的意图转换失败。

### 4.3 `EvaluationDimension`

`EvaluationDimension` 定义从哪个角度评价 Live 对一个或多个产品级业务期望的贡献。它不是另一份业务期望。

每个维度必须：

- 通过 `expectation_ids` 明确服务哪些业务期望；
- 通过 `evaluation_question` 形成一个可独立回答的问题；
- 在 `LiveBoundary` 内判断，不把完整产品其他环节的失败归责给 Live；
- 明确 `fulfilled`、`not_fulfilled`、`not_evaluable` 三个端点。

一个业务期望可以关联多个评估维度。例如“得到符合完整筛选要求的客户集合”可以同时关联：

```text
意图承接
  Live 是否完整、准确地保留了用户的目标客户范围？

下游交付可用性
  Live 是否以真实下游能够消费的方式交付了转换结果？
```

一个评估维度也可以服务多个业务期望，但只有确实采用同一判断问题和同一三态边界时才能复用；不得为了减少数量而合并语义不同的判断。

#### 三态端点

- `fulfilled_when`：现有外部证据足以证明 Live 在本维度作出了正确贡献；
- `not_fulfilled_when`：现有外部证据足以证明 Live 职责范围内存在真实业务偏差；
- `not_evaluable_when`：该业务期望和维度本应接受判断，但缺少决定性输入、actual、外部合同或可验证事实，无法可靠判断。

三态条件必须互斥、保守，并防止 Live 通过不输出结果逃逸评估。例如 Live 应产生查询却没有产生输出，通常属于 `not_fulfilled`；只有无法取得或确认 Live 的实际输出时，才属于 `not_evaluable`。

“不适用”和“不可评估”必须分开：

```text
当前 Case 不属于 BusinessExpectation.use_scenario
  → 不生成该期望对应的当前 Case 验收项

当前 Case 属于该业务情景，但缺少决定性证据
  → 对已生成的验收项判断 not_evaluable
```

调查合同不增加 `not_applicable` 第四态，也不要求修改现有 runtime public schema。

## 5. 调查结构到运行时的流转

```text
项目级调查合同
  ├── BusinessExpectation：完整产品用户希望得到什么
  ├── LiveBoundary：其中哪些部分应归责于 Live
  └── EvaluationDimension：如何评价 Live 的贡献
                ↓
当前 Case 的用户输入 / reference / 外部业务事实
                ↓
根据 use_scenario 识别当前 Case 涉及的产品级业务期望
                ↓
选择关联 EvaluationDimension，并应用 LiveBoundary
                ↓
在观察 actual 前生成当前 Case 的原子验收项及 blocking 属性
                ↓
观察 Live actual 和合法外部证据
                ↓
fulfilled / not_fulfilled / not_evaluable
                ↓
FulfillmentAssessment[] → 现有 overall 聚合协议
```

调查侧 `BusinessExpectation` 与当前 runtime 中同名对象的抽象层级不同：

- 调查侧表达稳定的产品级用户目标；
- runtime 对象当前承载从用户目标、当前 Case 和评估维度投影出的原子验收项。

为避免概念混淆，本文将后者称为“当前 Case 验收项”。本轮规范不要求修改 runtime class 名称，但 Solidify 必须保留从产品级 `expectation_id` 到当前 Case 验收项的可审查映射，不能把两者视为同一个对象直接复制。

当前 Case 验收项必须在观察 actual 前生成。是否 `blocking` 应根据该验收项失败是否会阻断关联 `desired_outcome` 确定，不得根据 actual 的偏差程度事后改变标准。

### 5.1 Planning：在观察 actual 前形成评价计划

Planning 是从项目级调查合同到当前 Case 验收项的选择步骤，不是另一次调查。
它只使用当前请求和已经固化的项目级知识：

```text
当前 Case
  ↓ 按 use_scenario 选择适用 BusinessExpectation
适用的产品级业务期望
  ↓ 展开其关联的全部 EvaluationDimension，并应用 LiveBoundary
当前 Case 原子验收项
  ↓ 若该评价点依赖权威事实（能力/职责边界、资料冲突、外部标准）
运行时按 decision_question 调用 authority.resolve 现场裁决
```

Planning 必须在读取 Live actual 前完成，且不得：

- 比较原始 Authority 资料；
- 触发新一轮调查或回写任何结论；
- 把 `unresolved` 改成 `resolved`；
- 因为预见 actual 的表现而增删维度、验收项或改变 `blocking`。

评价点是否依赖权威事实、依赖哪些资料，由运行时按 `spec/alg/authority.md` §5、§7
处理：Judge 遇到需要裁决的能力/职责边界、资料冲突或外部标准时，构造
`decision_question` 调用 `authority.resolve`；同一任务内相同 `decision_question`
只裁决一次。Planning 不复制资料正文、调查推理或调查报告，也不直接读取完整
Authority Report（`spec/alg/authority.md` §13.3）。权威调查产物与运行时综合见
`spec/alg/investigate-authority-judge.md` 与 `spec/alg/authority.md`。

### 5.2 Authority Gate：根据当前信息决定能否评价

评价点是否依赖权威事实、当前依据是否足以支持判断，由 `authority.resolve` 现场裁决
（`spec/alg/authority.md` §5、§7）；确定性 Gate 把裁决结果映射为三态：

```text
评价点不依赖权威事实
  → 按现有三态规则评价

评价点只命中 current_behavior 类资料
  → 可解释当前实现，但不能据此证明正式业务正确

评价点依赖 normative_rule / external_fact / inlive_boundary
  ├─ 依据充分   → Judge 结合依据评价
  └─ 证据不足   → unresolved → 该评价点必须 not_evaluable
```

Gate 必须校验：

- `inlive_boundary` 类资料只用于回答能力/可表达性问题，且项目已登记信任模型
  （`spec/alg/material-positioning.md` §4、§5）；
- 裁决基于绑定空间内实际 Load 的原始资料，`basis_evidence_ref_ids` 可回溯
  （`spec/alg/authority.md` §6、§13.3）；
- `current_behavior` 不得替代缺失的 `normative_rule`、`external_fact` 或
  `inlive_boundary`（`spec/alg/material-positioning.md` §4）；
- 同一任务内相同 `decision_question` 只裁决一次（`spec/alg/authority.md` §7）。

Authority 导致的 `not_evaluable` 不是静默跳过。Judge Summary 最少保留：

```text
status = not_evaluable
reason = authority_unresolved
unresolved_reason
required_evidence
basis_source_ref_ids
```

Judge 把 `AuthorityResolution.unresolved.required_evidence` 作为本 case 的缺料记录
（reason / required_evidence，`spec/alg/authority.md` §8.4）。调查层触发只能由用户
手动发起：人看到评测报告汇总的同类缺料后，才触发新一轮调查
（`spec/alg/investigate-authority-judge.md` §17）。Planning 和 Judge 本身不能用临时
提示绕过 unresolved。

## 6. 示例

以下示例用于说明三个对象如何组装，不是固定项目模板或特定 Case 的目标答案。

### 6.1 Client Search

```python
JudgeInvestigationContract(
    business_expectations=(
        BusinessExpectation(
            expectation_id="find-target-customers",
            user_role="需要寻找目标客户的业务人员",
            use_scenario="用户通过自然语言描述目标客户群体",
            desired_outcome="用户能够得到符合其完整筛选要求的客户集合",
        ),
    ),
    live_boundary=LiveBoundary(
        live_role="把自然语言客户搜索需求转换为下游搜索服务可消费的结构化查询",
        in_scope_responsibilities=(
            "正确承接用户已经表达或确认的搜索要求",
            "以真实下游可以消费的形式交付查询表达",
        ),
        out_of_scope_responsibilities=(
            "保证数据库中一定存在符合条件的客户",
            "保证客户数据完整且实时",
            "替用户决定未表达且无法确认的业务条件",
        ),
        external_constraints=(
            "数据库中不存在目标客户数据",
            "下游搜索服务不可用",
            "业务所需字段尚未接入数据源",
        ),
    ),
    evaluation_dimensions=(
        EvaluationDimension(
            dimension_id="search-intent-preservation",
            expectation_ids=("find-target-customers",),
            name="搜索意图承接",
            evaluation_question=(
                "Live 产生的查询语义是否完整、准确地保留了用户描述的目标客户范围、限制和关系？"
            ),
            fulfilled_when=(
                "Live 输出保留了所有会改变目标客户集合的用户要求",
                "条件之间的组合、排除和范围关系与用户意图一致",
                "没有增加用户未表达且会改变目标客户集合的强约束",
            ),
            not_fulfilled_when=(
                "遗漏、增加或改变了会影响目标客户集合的条件",
                "错误表达了条件之间的组合、排除或范围关系",
                "Live 在应交付查询时没有提供可用的查询表达",
            ),
            not_evaluable_when=(
                "用户要求存在决定性歧义，且没有产品约定或有效澄清结果",
                "无法取得或确认 Live 的实际输出",
            ),
        ),
        EvaluationDimension(
            dimension_id="downstream-query-consumability",
            expectation_ids=("find-target-customers",),
            name="下游查询可消费性",
            evaluation_question=(
                "Live 是否以真实下游支持的形式交付查询，使其能够继续执行用户要求的搜索？"
            ),
            fulfilled_when=(
                "查询使用下游支持的字段、值、操作符和组合结构",
                "下游能够消费该查询，且其执行语义未改变用户目标客户范围",
            ),
            not_fulfilled_when=(
                "查询包含下游不支持或语义不适用的字段、值、操作符或结构",
                "查询虽然可解析，但执行语义会改变用户目标客户范围",
                "Live 在应交付下游输入时没有提供可消费结果",
            ),
            not_evaluable_when=(
                "缺少决定性的下游协议或能力事实，且无法执行等价验证",
                "无法取得或确认 Live 交付给下游的实际结果",
            ),
        ),
    ),
)
```

#### Case A：Live 查询正确，但数据库没有匹配客户

用户输入：

```text
搜索年龄大于 50 岁的女性客户
```

Live 正确保留 `年龄 > 50`、`性别 = 女` 和二者的 AND 关系，但数据库返回空集合：

```text
搜索意图承接 = fulfilled
下游查询可消费性 = fulfilled
```

“数据库中没有匹配客户”可能使用户没有得到目标客户，但它属于 `LiveBoundary.external_constraints`，不能自动转化为 Live 失败。

#### Case B：Live 遗漏年龄条件

Live 只生成“性别 = 女”：

```text
搜索意图承接 = not_fulfilled
```

因为遗漏年龄条件改变了用户要求的目标客户集合。即使该查询结构能够被下游执行，也不能用“下游可消费性 fulfilled”覆盖真实的意图偏差。

#### Case C：缺少下游协议

Live 的查询语义可从外部输出确认正确，但调查和运行环境都没有提供决定性的下游字段或操作符协议：

```text
搜索意图承接 = fulfilled
下游查询可消费性 = not_evaluable
```

不同维度可以独立得到不同结果；证据不足只影响依赖该证据的维度。

### 6.2 多轮业务咨询

```python
JudgeInvestigationContract(
    business_expectations=(
        BusinessExpectation(
            expectation_id="obtain-reliable-business-guidance",
            user_role="需要处理业务问题的一线工作人员",
            use_scenario="用户通过多轮对话咨询具体业务规则或处理方式",
            desired_outcome="用户获得与自身问题相关、可信且可用于后续行动的业务指导",
        ),
    ),
    live_boundary=LiveBoundary(
        live_role="结合当前问题、历史上下文和权威业务知识提供咨询回答",
        in_scope_responsibilities=(
            "正确承接用户当前问题及已确认的历史约束",
            "对回答中涉及的业务事实保持准确",
        ),
        out_of_scope_responsibilities=(
            "替用户作出最终业务决策",
            "保证用户提供的事实或身份信息真实",
        ),
        external_constraints=(
            "权威知识库缺失、冲突或过时",
            "当前请求依赖但未提供的用户侧事实",
        ),
    ),
    evaluation_dimensions=(
        EvaluationDimension(
            dimension_id="question-alignment",
            expectation_ids=("obtain-reliable-business-guidance",),
            name="问题承接",
            evaluation_question="Live 回答是否直接回应用户当前问题，并保留已确认的历史约束？",
            fulfilled_when=(
                "回答直接处理用户当前的核心问题",
                "没有遗漏或篡改历史轮已确认且仍然有效的关键约束",
            ),
            not_fulfilled_when=(
                "回答偏离用户当前核心问题",
                "遗漏或改变了会影响处理结论的已确认约束",
            ),
            not_evaluable_when=(
                "当前问题依赖历史上下文，但无法取得相关历史轮次",
                "用户问题存在决定性歧义且没有有效澄清",
            ),
        ),
        EvaluationDimension(
            dimension_id="business-factual-accuracy",
            expectation_ids=("obtain-reliable-business-guidance",),
            name="业务事实准确性",
            evaluation_question="Live 回答中的业务事实是否与当前有效的权威业务规则一致？",
            fulfilled_when=(
                "回答中的关键业务规则、数值和流程与权威来源一致",
            ),
            not_fulfilled_when=(
                "回答包含会影响用户行动的错误业务事实",
            ),
            not_evaluable_when=(
                "回答涉及的关键事实缺少权威来源",
                "多个权威来源相互冲突且无法确定当前有效版本",
            ),
        ),
    ),
)
```

该示例中的产品级业务期望是“获得可靠、可行动的业务指导”，而不是“回答必须包含某条知识库文本”。问题承接和事实准确性只是评价 Live 对该业务期望贡献的两个维度。

## 7. 调查生成要求

执行 `/draft investigate` 且 `role=judge` 时，Harness AI 必须按以下顺序调查：

1. 识别完整产品的真实业务用户，而不是把 Live、开发者、测试框架或下游模块当作用户；
2. 调查用户在什么业务情景下使用产品，以及最终希望得到什么产品结果；
3. 形成稳定的产品级 `BusinessExpectation[]`，不得把 Live 输出、内部协议或评估规则写成业务期望；
4. 调查 Live 在完整产品链路中的角色、可控结果、非职责事项和外部限制，形成一个共享 `LiveBoundary`；
5. 针对每个业务期望，设计实际需要的 `EvaluationDimension[]`，明确每个维度评价 Live 的哪项贡献；
6. 为每个维度给出互斥、保守的三态端点，尤其说明何时证据不足而不能可靠评估；
7. 将证据来源、ToolRequirement、artifact 和 unresolved 登记到公共 `InvestigationManifest`，不在 Judge-specific contract 中复制；
8. 写入 `docs/judge-investigation-contract.json` 并登记到 Manifest artifacts；
9. 在 `overview.md` 中说明调查覆盖范围、关键来源和 unresolved，但不复制整个 JSON。

调查必须基于 Judge ROLE 允许的用户输入、reference、可观察业务输出、外部业务合同、下游消费协议和合法 Comparator 材料。不得根据当前 Prompt、实现习惯或模型常识补造用户角色、业务目标、下游能力或判断标准。

无法确认某项产品期望或 Live 边界时，应记录公共 `unresolved_reason`；无法确认某个已适用维度的决定性判断事实时，应在该维度中保留对应的 `not_evaluable_when`。

## 8. 审查与落实机制

### 8.1 结构门禁

`validate_investigation.py` 对 `role=judge` 必须检查：

- 强制 artifact 存在并能反序列化为 `JudgeInvestigationContract`；
- `business_expectations` 非空，且 `expectation_id` 唯一；
- 每个业务期望都有非空的 `user_role`、`use_scenario` 和 `desired_outcome`；
- `LiveBoundary.live_role` 和 `in_scope_responsibilities` 非空；
- `out_of_scope_responsibilities` 与 `external_constraints` 字段存在；
- `evaluation_dimensions` 非空，且 `dimension_id` 唯一；
- 每个维度至少引用一个存在的 `expectation_id`；
- 每个维度都有具体的 `evaluation_question` 和非空的三态条件；
- 文件不含 iteration case ID、promotion-only unseen case、目标答案、当前 verdict 或候选施工指令。

结构门禁只验证可确定的结构和引用关系。对“是否是真实产品期望”“是否错误混入实现细节”等问题，必须继续执行语义交接审查，不能用字符串规则假装完成业务判断。

### 8.2 Investigate → Solidify 语义交接审查

Harness AI 在 Solidify 前必须逐项确认：

#### BusinessExpectation

- `user_role` 是否为真实业务用户，而不是系统组件或抽象的“请求方”；
- `desired_outcome` 是否描述完整产品给用户带来的业务结果；
- 是否错误写成“Live 正确输出某结构”“字段映射正确”或“通过 Comparator”；
- 是否为了适配 Live 边界而人为缩小了用户真实期望；
- 不同业务期望是否代表不同用户结果，而不是同一实现流程的多个步骤。

#### LiveBoundary

- 是否准确描述 Live 在完整产品链路中的实际角色；
- 是否区分 Live 可控责任、其他模块责任和外部约束；
- 是否既没有把完整产品结果全部压给 Live，也没有把 Live 应负责的失败推出范围；
- 是否没有混入具体 Case verdict 或某个评估维度的三态规则。

#### EvaluationDimension

- 每个维度是否明确服务至少一个真实业务期望；
- `evaluation_question` 是否评价 Live 对业务期望的贡献，而不是再次描述用户想要什么；
- 多个维度是否真的提供不同判断角度，而不是字段换名后的重复；
- 三态条件是否互斥、保守，并能处理满足、明确偏离和证据不足；
- Live 未输出应交付结果时，是否被错误包装成 `not_evaluable` 从而逃逸失败；
- 外部系统失败是否被错误写成 Live 的 `not_fulfilled`。

关键业务期望、Live 边界或评估维度缺失时，应路由回 Investigate 或标记本轮 unresolved，不得假装调查充分。

### 8.3 Solidify 落实审查

Judge Solidify 必须建立以下可复查映射：

```text
产品级 BusinessExpectation
  + 当前 Case 用户输入 / reference
        ↓
当前 Case 原子验收项及预先确定的 blocking

EvaluationDimension
  + LiveBoundary
  + Manifest 中登记的证据和 ToolRequirement
        ↓
固化的 ContextUnit、Comparator Tool 或候选 Judge 逻辑
        ↓
runtime FulfillmentAssessment / JudgeResult / audit
```

并通过真实 project loader 完成：

- mandatory Context 注册与确定性装载检查；
- Tool smoke（若判断依赖 Comparator、外部 API 或协议检查）；
- 候选 Judge 实例化；
- 对关键维度执行满足、明确偏离和证据不足对照运行；
- 检查当前 Case 验收项和 blocking 在观察 actual 前确定；
- 检查候选真实消费固化资产，没有把 JSON 示例、Case 或固定答案写死；
- 检查完整产品失败、外部约束、Live 失败和证据不足没有混淆；
- 保留产品级 `expectation_id` 到当前 Case 验收项的审计映射，但不要求修改 runtime public schema。

未建立映射、候选未消费调查产物或三态边界未落实时，Solidify 失败。

### 8.4 Draft Loop 审查

Current/Draft 比较仍遵守现有冻结协议。Judge Review 必须检查：

- 当前 Case 验收项是否由真实产品级业务期望、当前用户需求和关联评估维度共同支持；
- 验收项是否原子、业务相关，并在观察 actual 前生成；
- blocking 是否在观察 actual 前确定；
- 当前 Case 涉及的关键评估维度是否得到实际判断；
- `fulfilled` 是否有足够外部证据；
- `not_fulfilled` 是否确认了 Live 职责范围内的真实业务差异；
- 证据不足是否保持 `not_evaluable`；
- Live 未交付应有结果时是否错误逃逸为 `not_evaluable`；
- 完整产品其他环节或外部约束是否被错误归责给 Live；
- 是否泄露或依赖内部实现、Attribute 根因或 promotion-only unseen case；
- Draft 是否相对 Current 提高判断准确性且无可见退化。

只有 Draft 被证明更好且无退化时，才可建议 Promotion。

## 9. 与现有公共协议的关系

- 本结构是 Judge 调查包的强制 artifact，不替代 `InvestigationManifest`；
- EvidenceRef、artifact、ToolRequirement 和 unresolved 继续使用现有公共字段；
- 调查侧 `BusinessExpectation` 是产品级定义，不直接复制 runtime 的当前 Case 验收项；
- 本轮不修改现有 `FulfillmentAssessment`、`JudgeResult`、三态词表和 overall 聚合 schema；
- 当前 Case 输入、actual 和 reference 继续通过 Judge 请求显式传入；
- 完整调查 JSON 不直接进入 Prompt；
- Judge 默认不读取内部源码、内部 trace 或 Attribute 候选调查包；
- promotion-only unseen case 不得进入调查结构；
- Judge 与 Mock 调查包独立演进，是否共享 dataclass 留待后续独立决策。

# 第二章：Changes

## 10. 当前状态与目标差异

当前 Judge 已有 runtime `BusinessExpectation`、`FulfillmentAssessment`、`JudgeResult`、三态聚合、Judge evidence view、项目 `judge_boundary` 文档和 mandatory Context 机制，但与本协议仍有以下差异：

1. Judge 没有强制的结构化调查合同，业务判断知识仍分散在 overview、evaluation、judge、judge_boundary、项目配置和代码中；
2. 当前材料容易直接把 Live 输出要求当成“用户期望”，缺少真实业务用户和完整产品目标的独立表达；
3. 产品级业务期望、Live 责任边界和 Judge 评估方法容易互相混合；
4. 现有 runtime `BusinessExpectation` 实际承载当前 Case 原子验收项，与产品级业务期望的抽象层级不同，但尚未建立明确映射；
5. 现有 `judge_boundary` 可能混合 Live 责任、证据规则和具体判断标准；
6. 各评估维度的三态端点及其与业务期望的关联没有统一结构；
7. validator 只验证公共 Manifest、EvidenceRef、ToolRequirement 和 artifact 路径，不验证本 spec 的三个核心对象及其引用关系；
8. Solidify 没有强制证明候选实际消费产品期望、LiveBoundary 和 EvaluationDimension；
9. Draft Loop 没有逐项检查完整产品失败与 Live 可归责失败是否得到正确区分；
10. Planning 对 BusinessExpectation、EvaluationDimension、LiveBoundary 的选择
    边界尚未形成稳定合同；
11. Authority unresolved 仍可能只影响提示语，不能确定性阻断无依据的肯定结论
    （需按 `spec/alg/authority.md` §8 接入 not_evaluable）。

## 11. 一次性改造任务

### Task 1：增加调查 schema 与 JSON 边界

- 新增调查侧 `JudgeInvestigationContract`、`BusinessExpectation`、`LiveBoundary` 和 `EvaluationDimension`；
- 提供严格的 JSON serialize/deserialize；
- 不在 Judge-specific contract 中复制 EvidenceRef、ToolRequirement、artifact 和 unresolved；
- 保持现有 Judge runtime public schema 不变。

### Task 2：更新 Judge ROLE 与模板

- 提供 `docs/judge-investigation-contract.json` 的可选结构化契约模板与门禁（按 §2 口径，非强制）；
- 在 Judge ROLE 中写入“产品级业务期望 → Live 责任边界 → 评估维度”的调查顺序；
- 增加业务期望正例、实现视角反例和最小完整模板；
- 更新 `MAP.md` 指向模板与门禁。

### Task 3：扩展调查 validator

- 对 `role=judge` 执行本 spec 的结构门禁；
- 校验业务期望和维度 ID、维度到期望的引用、LiveBoundary 必需字段和三态完整性；
- 保持其他 Role 的公共调查包行为不变；
- 不使用脆弱的关键词匹配替代语义交接审查。

### Task 4：迁移项目 Judge 调查材料

- 从真实用户、产品场景、业务合同、下游协议、application、evaluation、judge 和 judge_boundary 中提炼三个核心对象；
- 优先迁移 `client_search`，验证“完整产品用户希望找到目标客户”与“Live 只负责查询转换”的责任区分；
- 原 Markdown 只保留必要的人类说明或明确成为 JSON 的来源材料，避免形成两套冲突真相源。

### Task 5：增加 Solidify 落实审查

- 要求记录“产品级业务期望 → 当前 Case 验收项”的映射；
- 要求记录“评估维度 + LiveBoundary + 公共证据/Tool → 固化资产 → runtime observable”的映射；
- 在 Judge Solidify smoke 中对关键维度执行满足、明确偏离和证据不足对照；
- 检查候选真实消费资产且没有写死 Case、expected 或 verdict；
- 关键业务期望、Live 边界或评估维度未落实时阻断 Draft Loop。

### Task 6：更新 Draft Loop Review

- 检查当前 Case 验收项是否有产品级业务期望来源；
- 检查 Judge 是否只评价 Live 在其责任范围内的贡献；
- 检查三态判断、blocking 预确定和外部约束处理；
- 保持 Current/Draft 冻结、unseen 隔离和 Promotion 授权规则不变。

### Task 7：测试与文档同步

- 增加 dataclass round-trip、结构失败、非法 expectation 引用和跨 Role 隔离测试；
- 增加空业务期望、空维度、三态缺失和 LiveBoundary 缺失的失败测试；
- 增加“Live 无输出不得逃逸为 not_evaluable”的代表测试；
- 增加 Client Search 查询正确但数据库无数据、遗漏用户条件、缺少下游协议等代表测试；
- 增加自然语言 QA 多轮上下文完整、事实错误和权威知识缺失的代表测试；
- 同步 `spec/alg/investigate.md`、Draft Skill、Judge ROLE、MAP 和参考模板。

### Task 8：固化 Planning 与 Authority Gate

- 在 Draft 内实现 actual-free Planning：按 use_scenario 选择业务期望，展开关联
  维度，并应用 LiveBoundary 形成当前 Case 原子验收项；
- 评价点依赖权威事实时，按 `spec/alg/authority.md` §5、§7 接入 `authority.resolve`
  （`decision_question` + 绑定空间），同一任务内按 `decision_question` 去重；
- unresolved 的 normative_rule、external_fact 或 inlive_boundary 必须把对应评价点约束为
  `not_evaluable`，并把 `required_evidence` 写入 reason / required_evidence；
- Judge Summary 必须输出 unresolved 原因、待补资料和依据来源；
- 增加“无权威依赖”“current_behavior 仅解释现状”“依据充分可评价”
  和“unresolved 强制 not_evaluable”四类测试；
- 保持上述结构为 Draft 内部执行合同，不修改 Production 执行策略或公共
  runtime schema。

## 12. 一次性改造验收

- Judge 调查包使用 `judge-investigation-contract.json` 时，正确登记到 Manifest artifacts 并通过结构门禁；
- 每份合同都明确真实业务用户、使用场景和完整产品层面的期望结果；
- 业务期望中不包含 Live 内部输出、协议字段、Comparator 或 Judge verdict；
- `LiveBoundary` 能把完整产品结果正确投影到 Live 可归责范围；
- 每个评估维度都通过稳定 ID 关联至少一个产品级业务期望；
- 每个维度都具有可执行理解的 `evaluation_question` 和互斥、保守的三态端点；
- validator 能阻止缺失对象、非法 ID 引用和三态不完整；
- Solidify 能证明产品级业务期望已自然引出当前 Case 原子验收项，而不是机械复制；
- Judge 能区分完整产品未达成、Live 职责内失败、外部约束和证据不足；
- 当前 Judge runtime public schema 未被复制或污染；
- Planning 在观察 actual 前完成，且不重新调查资料、不回写任何结论；
- unresolved Authority 能确定性约束对应评价点，并在 Judge Summary 中显示
  具体原因、待补资料和依据来源；
- Current/Draft 比较证明判断准确性改善且无可见退化后，才提出 Promotion 建议。
