# Judge Authority 调查优化协议

本文是 `spec/alg/investigate-judge-authority.md` 的优化提案。

本文不改变：

- `BusinessExpectation → EvaluationDimension → LiveBoundary` 的 Judge 主框架；
- 公共 `InvestigationManifest`、`EvidenceRef`、`ToolRequirement`；
- `Investigate → Solidify → Draft Loop → Promote` 流程；
- `FulfillmentAssessment`、`JudgeResult` 和三态聚合协议；
- Production 和公共协议实现。

本文只在 Draft Judge 调查中新增资料轴心的 Authority Investigation 阶段，
并明确该阶段如何产出可供 Solidify 使用的 Authority 交付。

当前 Case 如何选择评价点、如何引用 Authority、何时执行 `not_evaluable`
Gate，统一由 `spec/alg/investigate-judge.md` 定义。大型资料如何建立索引和按需
加载，统一由 `spec/alg/investigate-keyindex.md` 定义。

---

# 第一章：核心协议

## 1. Authority 的业务意义

Authority 回答：

> 基于当前已经调查的真实业务资料和上下游依赖，当前是否有足够依据得到
> 某一类可靠结论？

它不表示：

- 某份文件天然比另一份文件高级；
- 当前代码行为天然正确；
- 每个业务词都要建立一条静态规则；
- 调查阶段提前知道具体 Case；
- Judge 可以在 runtime 临时决定哪个来源更权威。

调查阶段通常不知道具体请求。它调查的是项目级可复用政策和业务规则，例如：

```text
客户搜索业务语义如何映射为正式查询条件；
多轮营销规划在什么条件下应结束澄清并进入执行；
QA 的 gold/context 在什么 provenance 条件下可以作为判断依据。
```

具体 Case 只在 runtime 判断是否依赖某项已经调查的 Authority。

## 2. 四步主链

业务人员和实现者只需要理解以下主链：

```text
EvidenceRef：已登记的真实业务资料
        ↓ Authority Investigation
AuthorityInvestigationReport：逐份资料调查后的报告
        ↓ Solidify
SolidifiedAuthorityAnchor
        ↓ 交给 Judge 运行时协议消费
```

对应职责：

| 阶段 | 负责什么 | 不负责什么 |
|---|---|---|
| EvidenceRef 登记 | 资料位置、版本、hash | 不解释资料内容 |
| Authority Investigation | 逐份调查资料、逐条取证，再形成 Finding | 不以预设观点筛选资料 |
| Solidify | 将 Finding 投影为最小运行时 Anchor | 不重新调查资料 |
| Judge 运行时 | 按 Judge 协议消费 Anchor | 不现场创造或解决 Authority |

`AuthorityInvestigationReport` 是 Authority Investigation 阶段的结构化交付，
不是一个独立运行阶段。报告内部的资料记录、证据和关系也不进入 runtime。

## 3. 三个核心概念

### 3.1 EvidenceRef：资料登记

`EvidenceRef` 是现有公共来源目录，只回答：

```text
资料是什么？
资料在哪里？
资料对应哪个 revision/hash？
```

它不回答：

```text
资料表达了什么业务规则？
资料是不是最终 Authority？
资料与谁冲突？
```

因此 EvidenceRef 不是 Authority 推理层。业务语义从
`AuthorityInvestigationReport` 开始。

EvidenceRef 不能只停留在 Manifest 总览。Authority Report 中每一个
`MaterialInvestigation` 都必须同时写出 `source_ref_id` 和可直接识别文件的
`source_location`。这样单独阅读一份资料分析时，不需要返回总览查 ID。
`source_location` 由 Core 从 EvidenceRef 复制和校验，不能由 Harness AI
自由填写。

### 3.2 AuthorityInvestigationReport：调查阶段的交付

Authority Investigation 必须按以下内部步骤执行：

```text
1. 资料登记
   输入：InvestigationManifest.evidence_refs
   输出：本次必须调查的资料清单

2. 逐份资料调查
   输出：MaterialInvestigation[]
   回答：每份资料在哪些维度、场景和条件下唯一决定什么

3. 资料连接分析
   输出：每份 MaterialInvestigation.connections[]
   回答：上下游和同级资料分别做什么、如何依赖和产生什么影响

4. Authority 归纳
   输出：AuthorityFinding[]
   回答：完成资料调查后，当前能够或不能够得到哪些结论
```

顺序不得颠倒。特别禁止先生成 Finding，再围绕 Finding 挑选资料。

阶段内部的职责分工：

| 内部步骤 | Harness AI | 确定性代码 | 完成标准 |
|---|---|---|---|
| 资料登记 | 发现与业务范围有关的真实资料 | 固化 EvidenceRef、revision 和 hash | 本次资料范围可枚举、可复现 |
| 逐份资料调查 | 定义每份资料的唯一决定范围 | 校验 decisions 非空且引用合法 Dimension | 每份资料至少唯一决定一个业务事项 |
| 资料连接分析 | 说明上游、下游和同级资料的实质业务连接 | 校验引用文件和方向 | 每条连接都说明对方做什么和如何影响当前资料 |
| Finding 归纳 | 按维度、场景和条件匹配 Decision | 校验重叠范围已区分或已标记 unresolved | 结论及冲突原因都能回溯 |

Harness AI 负责调查和业务解释；代码负责覆盖、引用和边界校验。代码不得替
Harness AI 生成业务结论，Harness AI 也不得绕过确定性校验。

```python
@dataclass(frozen=True)
class AuthorityInvestigationReport:
    report_id: str
    investigation_snapshot_id: str

    # 项目级业务流程，不得写成具体 Case。
    business_scope: str

    materials: tuple[MaterialInvestigation, ...]
    findings: tuple[AuthorityFinding, ...]
```

报告的第一组织维度必须是 `materials`。Markdown 必须在每份资料下直接展示
decisions、related_to 和 connections，最后再展示 Finding；不得按 Finding
分章节后反向罗列资料。

### 3.3 AuthorityFinding：调查结果

`AuthorityFinding` 代替容易产生误解的 `AuthorityConclusion`。

```python
@dataclass(frozen=True)
class AuthorityFinding:
    finding_id: str

    finding_kind: Literal[
        "current_behavior",
        "normative_rule",
        "external_fact",
    ]

    # 项目级可复用问题，不得包含 current Case actual/verdict。
    business_question: str

    # 关联 EvaluationDimension.dimension_id。
    dimension_ids: tuple[str, ...]

    # 限制该 Finding 可以在哪些项目业务阶段使用。
    applicable_stage_ids: tuple[str, ...]

    # 只保留跨阶段需要的资料引用。
    basis_source_ref_ids: tuple[str, ...]

    status: Literal["resolved", "unresolved"]

    # resolved 时必填。
    result: str | None

    # unresolved 时必填。
    unresolved_reason: str | None
    required_evidence: tuple[str, ...]

    # 引用 InvestigationManifest.tool_requirements。
    tool_requirement_ids: tuple[str, ...] = ()
```

三种 Finding 的业务区别：

| kind | 回答的问题 | 能否解除正式规则 Gate |
|---|---|---|
| `current_behavior` | 当前系统现在如何做 | 不能 |
| `normative_rule` | 业务、产品、监管或契约要求应该如何做 | 可以 |
| `external_fact` | 外部系统或现实当前实际是什么 | 可以 |

最重要的不变量：

> `current_behavior=resolved` 只能解释系统现状，永远不能代替
> `normative_rule` 或 `external_fact`。

Finding 不对资料做权威强弱排序。它只检查当前业务问题是否命中某个
MaterialDecision：

```text
恰好一个适用 Decision
  → 使用该资料作为该范围内的唯一决定标准

多个 Decision，但场景或条件互斥
  → 选择当前适用 Decision

多个 Decision 在相同维度、场景和条件下重叠
  ├─ 存在明确 supersedes → 使用生效 Decision
  └─ 无法区分            → unresolved

没有适用 Decision
  → unresolved，required_evidence 说明缺少哪类唯一决定资料
```

## 4. SolidifiedAuthorityAnchor

Solidify 不把完整报告注入 Judge，只投影当前 Role 所需的最小 Anchor：

```python
@dataclass(frozen=True)
class SolidifiedAuthorityAnchor:
    report_id: str
    finding_id: str
    finding_kind: Literal[
        "current_behavior",
        "normative_rule",
        "external_fact",
    ]
    applicable_stage_ids: tuple[str, ...]
    status: Literal["resolved", "unresolved"]
    result: str | None
    unresolved_reason: str | None
    required_evidence: tuple[str, ...]
    basis_source_ref_ids: tuple[str, ...]
```

Anchor 必须能沿以下关系回溯：

```text
SolidifiedAuthorityAnchor.finding_id
        ↓
AuthorityInvestigationReport.findings
        ↓
basis_source_ref_ids
        ↓
MaterialInvestigation.source_ref_id/source_location
        ↓
InvestigationManifest.evidence_refs
```

完整 Material 及其 connections 只在需要人工审核时从报告加载，不进入常规
Judge 上下文。

## 5. 与 Judge 运行时的交接边界

本协议到 `SolidifiedAuthorityAnchor` 为止。它只保证：

- Anchor 来自已经固化的 AuthorityFinding；
- `resolved / unresolved`、原因、待补资料和来源引用没有在 Solidify 中丢失；
- Judge 可以沿 `finding_id → basis_source_ref_ids → EvidenceRef` 回溯。

当前 Case 是否需要某个 Anchor、如何把 Anchor 关联到当前 Case 评价点，以及
何时将 unresolved 转换为有明确原因的 `not_evaluable`，由
`spec/alg/investigate-judge.md` 的 Planning 与 Judge Gate 定义。本协议不重复
这些运行时规则。

## 6. 资料轴心案例：client_search 当前字段知识链

该案例不从具体字段、枚举或 badcase 开始，而是调查当前字段知识如何从环境
配置进入 Parser 并约束最终输出。每份资料都展示 ref、具体文件以及它唯一决定
的业务范围。

业务链：

```text
dev_client_search_args.yaml
  唯一决定 dev 场景选择哪份字段定义
        ↓ selects
field_definitions_args.yaml
  唯一决定当前选中配置中写了哪些字段知识
        ├─ consumed_by
FieldRegistry
  唯一决定字段配置如何成为运行时检索知识
        │      ↓ consumed_by
        └──────────────┐
                       ↓
QueryRouter
  唯一决定最终条件如何执行字段合法性校验
```

### 资料一：dev 运行环境配置

具体文件：
`business://src/main/python/config/dev_client_search_args.yaml`

```python
MaterialInvestigation(
    source_ref_id="client-search-dev-runtime-config",
    source_location="business://src/main/python/config/dev_client_search_args.yaml",
    decisions=(
        MaterialDecision(
            dimension_id="active-business-configuration",
            conclusion_kind="current_behavior",
            governs="dev 部署默认选择哪一份字段定义文件",
            scenario="client_search Parser 在 dev 环境初始化",
            conditions=(
                "ENV=dev",
                "FIELD_DEFINITIONS_PATH 未被更高优先级配置覆盖",
            ),
            applicable_stage_ids=("parser_initialization",),
        ),
    ),
    related_to=("其他部署环境选择什么文件，由各自环境配置决定。",),
    connections=(
        MaterialConnection(
            direction="downstream",
            source_ref_id="client-search-field-definitions",
            source_location=(
                "business://src/main/python/config/field_definitions_args.yaml"
            ),
            relation="dependency",
            effect=(
                "通过 FIELD_DEFINITIONS_PATH 选择当前字段定义文件，"
                "使其成为 dev 场景的字段知识来源。"
            ),
        ),
    ),
    limitations=("结论只适用于上述 dev 条件，不自动扩张到其他部署环境。",),
)
```

### 资料二：字段定义配置

具体文件：
`business://src/main/python/config/field_definitions_args.yaml`

```python
MaterialInvestigation(
    source_ref_id="client-search-field-definitions",
    source_location=(
        "business://src/main/python/config/field_definitions_args.yaml"
    ),
    decisions=(
        MaterialDecision(
            dimension_id="configured-field-knowledge",
            conclusion_kind="current_behavior",
            governs=(
                "当前被选中字段配置中包含哪些检索文本、字段、"
                "操作符、值类型、说明、示例和反例"
            ),
            scenario="Parser 使用字段知识进行检索和字段校验",
            conditions=(
                "当前环境配置指向该文件",
                "文件 revision/hash 与调查快照一致",
            ),
            applicable_stage_ids=("field_retrieval", "output_validation"),
        ),
    ),
    related_to=(
        "正式业务应该允许哪些字段，但应由正式业务规范决定。",
        "下游实际接受哪些字段，但应由 provider-owned 契约决定。",
    ),
    connections=(
        MaterialConnection(
            direction="upstream",
            source_ref_id="client-search-dev-runtime-config",
            source_location=(
                "business://src/main/python/config/dev_client_search_args.yaml"
            ),
            locator="$.FIELD_DEFINITIONS_PATH",
            relation="dependency",
            effect=(
                "通过 FIELD_DEFINITIONS_PATH 选择本文件；只有被当前环境"
                "选中时，它才决定当前字段知识。"
            ),
        ),
        MaterialConnection(
            direction="downstream",
            source_ref_id="client-search-field-registry",
            source_location="business://src/main/python/steps/field_registry.py",
            locator="FieldRegistry._load_yaml",
            relation="dependency",
            effect="读取 intents，并转化为运行时字段检索知识。",
        ),
        MaterialConnection(
            direction="downstream",
            source_ref_id="client-search-query-router",
            source_location="business://src/main/python/steps/query_router.py",
            locator="QueryRouter._load_validation_data",
            relation="dependency",
            effect="读取 field 集合，作为最终结构化条件的合法字段边界。",
        ),
    ),
    limitations=(
        "它唯一决定当前选中配置的内容，不决定正式业务本来应该有哪些字段。",
        "它不决定下游客户搜索服务实际接受哪些字段。",
    ),
)
```

### 资料三：FieldRegistry

具体文件：`business://src/main/python/steps/field_registry.py`

```python
MaterialInvestigation(
    source_ref_id="client-search-field-registry",
    source_location="business://src/main/python/steps/field_registry.py",
    decisions=(
        MaterialDecision(
            dimension_id="field-knowledge-materialization",
            conclusion_kind="current_behavior",
            governs="字段定义如何被加载、展开并转化为运行时检索知识",
            scenario="Parser 初始化字段注册表并执行字段意图检索",
            conditions=("当前部署执行该 FieldRegistry revision",),
            applicable_stage_ids=("parser_initialization", "field_retrieval"),
        ),
    ),
    related_to=("字段知识内容由字段定义配置决定。",),
    connections=(
        MaterialConnection(
            direction="upstream",
            source_ref_id="client-search-field-definitions",
            source_location=(
                "business://src/main/python/config/field_definitions_args.yaml"
            ),
            relation="dependency",
            effect="读取 intents、展开 enum_ref，并建立运行时字段检索知识。",
        ),
        MaterialConnection(
            direction="downstream",
            source_ref_id="client-search-query-router",
            source_location="business://src/main/python/steps/query_router.py",
            locator="QueryRouter.__init__",
            relation="dependency",
            effect="QueryRouter 使用该注册表执行字段知识检索和输入归一化。",
        ),
    ),
    limitations=("它决定加载和检索机制，不决定字段配置内容。",),
)
```

### 资料四：QueryRouter

具体文件：`business://src/main/python/steps/query_router.py`

```python
MaterialInvestigation(
    source_ref_id="client-search-query-router",
    source_location="business://src/main/python/steps/query_router.py",
    decisions=(
        MaterialDecision(
            dimension_id="parsed-condition-validation",
            conclusion_kind="current_behavior",
            governs="最终结构化条件如何执行字段合法性校验",
            scenario="Parser 汇总各解析层结果并生成最终条件",
            conditions=("当前部署执行该 QueryRouter revision",),
            applicable_stage_ids=("output_validation",),
        ),
    ),
    related_to=("下游正式接口契约由 provider-owned 资料决定。",),
    connections=(
        MaterialConnection(
            direction="upstream",
            source_ref_id="client-search-field-definitions",
            source_location=(
                "business://src/main/python/config/field_definitions_args.yaml"
            ),
            locator="$.intents[*].field",
            relation="dependency",
            effect="读取 field 集合，建立最终条件的合法字段边界。",
        ),
        MaterialConnection(
            direction="upstream",
            source_ref_id="client-search-field-registry",
            source_location="business://src/main/python/steps/field_registry.py",
            locator="FieldRegistry",
            relation="dependency",
            effect="使用运行时字段知识执行查询归一化和字段检索。",
        ),
    ),
    limitations=("它决定当前校验行为，不决定下游正式接口契约。",),
)
```

这个案例表达的是资料分工，不是权威等级：

```text
环境配置唯一决定“选哪个文件”；
字段定义唯一决定“选中文件里写了什么”；
FieldRegistry 唯一决定“如何加载和检索”；
QueryRouter 唯一决定“如何执行最终字段校验”。
```

如果需要判断“正式业务应该有哪些字段”或“下游实际接受哪些字段”，当前四份
资料没有任何一个 MaterialDecision 覆盖该问题。此时不是把它们降级为
supporting，
而是直接生成 unresolved Finding，并要求补充相应正式规范或 provider-owned
契约。

## 7. 核心 Validator

结构校验：

- `source_ref_id` 必须引用当前 Manifest 中存在的 EvidenceRef；
- `source_location` 必须等于该 EvidenceRef 的 `location_ref`；
- Core 必须按 `source_location.revision + sha256` 校验实际读取的资料；
- 每个 MaterialInvestigation 的 `decisions` 必须非空；
- Decision 的 Dimension 和 Stage 引用必须存在；
- Connection 的 source_ref_id 必须存在于 Manifest；
- Connection 的 source_location 必须与对应 EvidenceRef 一致；
- Connection.effect 不得为空或只写“相关”“被使用”；
- Finding 的 basis_source_ref_ids、Dimension 和 ToolRequirement 必须存在；
- Finding ID 由 Harness 使用 `project_id + business_question slug` 生成；
- `applicable_stage_ids` 不得为空；
- resolved 必须有 `result`，不得有 `unresolved_reason`；
- unresolved 必须有 `unresolved_reason` 和 `required_evidence`。

业务边界校验：

- 每份 Authority Material 必须至少唯一决定一个明确业务事项；
- Decision 的 scenario 和 conditions 必须是项目级范围，不得包含单个 badcase；
- Finding 的 kind、Dimension、Stage、场景和条件必须与适用 Decision 一致；
- `current_behavior=resolved` 必须命中 current_behavior Decision；
- `normative_rule=resolved` 必须命中 normative_rule Decision；
- `external_fact=resolved` 必须命中 external_fact Decision；
- 不得用其他 conclusion_kind 的 Decision 替代缺失 Decision；
- 相同决定范围只允许一个当前生效 Decision；
- 重叠 Decision 只有存在互斥条件、场景区分或 peer
  `connection.relation="supersedes"` 时才能 resolved；
- 无适用 Decision 或重叠 Decision 无法消解时，必须 unresolved；
- 禁止 `supporting`、`context_only` 等模糊 Authority 等级；
- `related_to` 不能单独解除 Gate；
- 只写“资料有歧义”但没有具体资料和 Connection，校验失败；
- 报告不得包含 current Case actual、Comparator、score、confidence 或 verdict；
- 不得为单个 badcase 新增专属 Finding 或 relation kind。

Validator 只能检查引用、边界和禁止项，不能代替业务语义审查。

## 8. 调查产物位置

```text
impl/projects/<project>/draft/investigation/judge/
  manifest.json
  overview.md
  docs/
    judge-investigation-contract.json
    authority-investigation-report.json
    authority-investigation-report.md
```

规则：

- JSON 是结构化真相源；
- Markdown 由 JSON 确定性渲染，供人工审核；
- 两者使用固定逻辑路径和 purpose 登记到
  `InvestigationManifest.artifact_refs`；
- Judge contract 不复制完整报告；
- 完整报告不得无条件注入 runtime Prompt。

```text
artifact://docs/authority-investigation-report.json
purpose = judge_authority_investigation_report_json

artifact://docs/authority-investigation-report.md
purpose = judge_authority_investigation_report_markdown
```

## 9. 现有 AuthorityAnalysis 的迁移

现有 `AuthorityAnalysis` 降为兼容视图，不再是调查真相源。

确定性投影：

```text
AuthorityFinding.finding_id
  → AuthorityAnalysis.analysis_id

AuthorityFinding.business_question
  → AuthorityAnalysis.judgment_point

AuthorityFinding.dimension_ids
  → AuthorityAnalysis.dimension_ids

AuthorityFinding.status/result/unresolved_reason
  → AuthorityAnalysis.anchor

AuthorityFinding.basis_source_ref_ids
  → AuthorityAnalysis.source_claims 的最小引用摘要

AuthorityFinding.tool_requirement_ids
  → AuthorityAnalysis.tool_requirement_ids
```

不得从旧 AuthorityAnalysis 反向生成 Authority Report。

---

# 第二章：报告内部结构

## 10. MaterialInvestigation：一份资料的完整调查记录

```python
@dataclass(frozen=True)
class MaterialInvestigation:
    source_ref_id: str

    # 正式 JSON 保存 LogicalPathRef；案例和 Markdown 渲染为 business:// 等缩写。
    source_location: LogicalPathRef

    # 至少一项：该资料在哪些边界内唯一决定什么。
    decisions: tuple[MaterialDecision, ...]

    # 可以相关，但这些事项不由该资料决定。
    related_to: tuple[str, ...]

    # 直接说明上下游或同级资料做什么、怎么依赖和产生什么影响。
    connections: tuple[MaterialConnection, ...]

    limitations: tuple[str, ...]
```

核心不变量：

```text
MaterialInvestigation.decisions 不得为空
```

进入 Authority Report 的资料不再分为“决定性、辅助性、背景性”等权威等级。
每份资料都必须明确：它在哪个维度、场景和条件下，是哪个业务事项的唯一决定
标准。只有相关性、但找不到任何唯一决定范围的资料，继续保留在普通
Investigation Evidence 中，不进入 Authority Report 的 `materials`。

Manifest 可以登记 Authority 调查过程中发现的全部资料；只有完成调查并找到
至少一个唯一决定范围的资料，才生成 `MaterialInvestigation` 并进入
Authority Report 的 `materials`。只有相关性、无法读取或找不到唯一决定范围的
资料继续保留在普通 Investigation Evidence/overview 中，不得伪装成 Authority
Material。尚未取得、因而没有 EvidenceRef 的资料只能作为 unresolved Finding
的 `required_evidence`。

文件引用固化链：

```text
InvestigationManifest.evidence_refs[n]
        ├── ref_id ────────→ MaterialInvestigation.source_ref_id
        └── location_ref ──→ MaterialInvestigation.source_location
```

Core 负责复制和一致性校验，Harness AI 不得自行拼写文件路径。报告不复制
完整文件内容；大型资料按 `spec/alg/investigate-keyindex.md` 建立索引并按需
读取。正式 JSON 继续保存完整 `LogicalPathRef`，案例和 Markdown 只显示：

```text
business://src/main/python/config/field_definitions_args.yaml
```

定位代码 symbol 时单独显示 `locator`。revision 和 sha256 由 EvidenceRef 与
InvestigationSnapshot 固化，不在每条业务说明中重复展开。

Markdown 必须以该结构逐份展开：

```text
资料名称
├── source_ref_id
├── source_location：business:// 等逻辑路径缩写
├── decisions：唯一决定什么
├── related_to：相关但不决定什么
├── connections：上下游和同级资料怎么连接
└── 资料边界
```

## 11. MaterialDecision：资料的唯一决定范围

```python
@dataclass(frozen=True)
class MaterialDecision:
    dimension_id: str

    conclusion_kind: Literal[
        "current_behavior",
        "normative_rule",
        "external_fact",
    ]

    # 该资料在本范围内唯一决定的业务事项。
    governs: str

    # 项目级场景类型，不得包含单个 runtime Case。
    scenario: str

    # 资料成为唯一决定标准所必需的生效条件。
    conditions: tuple[str, ...]

    applicable_stage_ids: tuple[str, ...]
```

“唯一”只在以下组合内成立：

```text
dimension_id + conclusion_kind + scenario + conditions + applicable_stage_ids
```

它不是宣称某份资料在整个项目中永远最高。相同维度的资料可以分别适用于：

- 不同业务场景；
- 不同产品或渠道；
- 不同部署环境；
- 不同生效时间或版本；
- 一般规则与明确例外条件。

如果两份资料的决定范围不重叠，它们不是冲突。如果决定范围重叠，则必须存在
明确的条件区分、场景区分或
`MaterialConnection(relation="supersedes")`；否则对应 AuthorityFinding
必须 `unresolved`。

`related_to` 只说明资料与其他业务事项的关系和决定边界，例如：

```text
正式业务应该允许哪些字段，但应由正式业务规范决定。
下游实际接受哪些字段，但应由 provider-owned 契约决定。
```

它不是低等级 Authority，不能单独解除 Gate。

## 12. MaterialConnection：资料之间的实质连接

```python
@dataclass(frozen=True)
class MaterialConnection:
    direction: Literal["upstream", "downstream", "peer"]

    source_ref_id: str
    source_location: LogicalPathRef
    locator: str = ""

    relation: Literal[
        "dependency",
        "supersedes",
        "conflicts_with",
    ]

    # 一句话同时说明对方做什么、如何依赖当前资料以及业务影响。
    effect: str
```

`direction` 以当前 MaterialInvestigation 为中心。`effect` 不得只写“相关”或
“被使用”，必须说清传递或约束的内容以及结果。例如：

```text
读取 intents，并转化为运行时字段检索知识。
读取 field 集合，作为最终结构化条件的合法字段边界。
```

不记录完整函数调用图，也不再生成 relation_id/evidence_id。

# 第三章：当前项目泛化验证

## 13. 泛化不变量

Schema 不假设业务一定存在：

- 字段或枚举；
- Parser；
- 数据库；
- 唯一标准答案；
- 内部代码；
- 下游搜索结果。

跨项目稳定抽象只有：

```text
有版本的真实资料
  ↓
资料在某个维度、场景和条件下唯一决定一个业务事项
  ↓
资料之间的选择、消费、约束、覆盖或冲突关系
  ↓
resolved / unresolved Finding
```

不能找到非空 decisions 的资料不进入 Authority materials。这个要求不依赖
资料是文档、配置、代码、契约、工具结果还是外部观察。

## 14. QA

QA 业务链：

```text
上传 question + actual + optional gold/context
        ↓
归一化
        ↓
按 scenario 使用 gold、context 或弱参考策略
        ↓
质量判断
```

静态 Authority Report 只调查项目级政策：

```text
什么 provenance 条件下 gold 可以作为依据？
gold 与可信 context 冲突时如何处理？
弱参考场景需要什么 runtime evidence？
```

具体 Case 的 question、actual、gold 和 context 不进入静态报告，继续作为
runtime evidence。

例如当前 Judge policy/实现可以唯一决定“当前系统在什么场景使用 gold”，形成
current_behavior Decision；只有正式 provenance policy 才能唯一决定“什么条件下
gold 可以作为业务标准”。后者缺失时，normative Finding unresolved。

## 15. DeerFlow

DeerFlow 业务链：

```text
用户多轮目标
  ↓ Gateway thread/run
clarification policy
  ↓ skill selection
planning execution
  ↓ reply / tool_calls / message history
```

当前 clarification policy/实现可以唯一决定“当前流程在什么条件下继续澄清”，
形成 current_behavior Decision。只有领域充分性规范才能唯一决定“业务上何时信息
已经足够”；缺少该资料、部署 revision 或 skill receipt 时，对应 normative
Finding unresolved。

这证明 Schema 不依赖 client_search 的字段和数据库。

## 16. Marketing Planning

两个项目共享业务资料，但边界不同：

```text
marketting-planning-intent
  用户表达 → intent/nlu_info

marketting-planning
  intent → clarification/session → planning → SSE cards
```

真实资料中，正式文档、代码枚举、Prompt 和用户侧 intent 文档分别给出
4、7、7、5 类意图。

当前代码枚举可以唯一决定“当前实现允许哪些意图标签”，形成
current_behavior Decision。只有受治理的正式意图分类资料才能唯一决定“对外产品
允许哪些意图”；缺少审批、生效版本和覆盖关系时，对应 normative Finding
unresolved。

在 intent 项目中，该 Finding 可以约束意图标签；在完整 planning 项目中只能
约束入口阶段。因此必须使用 `applicable_stage_ids`，不能把意图 Authority
扩张到后续规划结果。

## 17. 当前验证状态

| 项目 | 状态 |
|---|---|
| `client_search` | 已基于真实业务资料生成报告案例 |
| `QA` | 已验证 Schema 表达力，尚无 Judge Authority Report |
| `deerflow` | 已验证 Schema 表达力，当前只有 Attribute investigation |
| `marketting-planning` | 已验证 Schema 表达力，当前只有 Attribute investigation |
| `marketting-planning-intent` | 已验证 Schema 表达力，当前只有 Attribute investigation |

因此当前只能确认跨项目表达能力；除 client_search 示例外，不能宣称
Manifest、Solidify 和 runtime 已经实测通过。

---

# 第四章：Changes

## 18. 当前差异

1. AuthorityAnalysis 仍是观点轴心，可能先提观点再找资料；
2. 当前缺少结构化 Authority Report；
3. 当前没有明确每份 Authority 资料唯一决定的维度、场景和条件；
4. 当前行为、正式规则和外部事实没有稳定分离；
5. unresolved Finding 无法稳定回指具体资料声明和待补证项；
6. 跨项目、跨业务阶段引用缺少确定性门禁；
7. 单份资料调查只保存 source ID，阅读时无法直接知道对应哪个文件。

## 19. 一次性改造任务

### P0：调查产物

- 新增 Report JSON 和确定性 Markdown 渲染；
- 使用固定 logical path/purpose 登记 artifact_refs；
- 调查 Manifest 中的真实业务资料，只将具有非空 decisions 的资料固化为
  MaterialInvestigation；
- Core 将 EvidenceRef.location_ref 固化到每个
  MaterialInvestigation.source_location；
- 为每份 Authority 资料生成至少一个 MaterialDecision；
- 使用 related_to 表达相关但不决定的事项；
- 使用 MaterialConnection 直接表达上下游、同级冲突和覆盖关系；
- Finding 只保留 basis_source_ref_ids；
- 将旧 AuthorityAnalysis 改为相同 ID 的兼容投影；
- 删除没有真实调查证据的具体 Case Authority 声明。

### P0：Validator

- 校验 EvidenceRef、Material、Connection、Finding、Dimension 和 Tool 引用；
- 拒绝 `decisions` 为空的 Authority Material；
- 拒绝用 `supporting/context_only` 等模糊等级代替唯一决定范围；
- 对重叠 Decision 要求互斥条件、场景区分、supersedes 或 unresolved；
- 拒绝缺少依据的 resolved；
- 拒绝缺少具体原因和 required_evidence 的 unresolved；
- 拒绝 current_behavior 解除正式规则 Gate；
- 拒绝跨 project、snapshot 和 business stage 引用；
- 拒绝把 QA 逐样本 reference 固化为项目级 Finding。

### P0：Solidify 交付

- 将 Finding 投影为 SolidifiedAuthorityAnchor；
- 保证 Anchor 保留 Finding 状态、原因、资料声明和待补证项；
- 完整报告按需审核，不进入常规 Prompt。

### P1：真实业务补证

- 调查资料 origin、owner、审批、生效和废弃关系；
- 优先取得外部正式契约和可复现业务事实；
- client_search 补充下游接口、字段、枚举和客户结果证据；
- DeerFlow 补充领域信息充分性规则和部署 receipt；
- Marketing Planning 补充正式 intent 集合审批和版本关系；
- QA 补充 gold/context 的 provenance policy。

## 20. 改造边界

只允许修改：

```text
impl/projects/<project>/draft/**
impl/projects/<project>/draft/investigation/**
Draft 测试
```

不得修改 Production 和公共协议实现。

验收要求：

- 调查阶段不依赖具体 Case；
- 报告以真实业务资料为轴心；
- current behavior 和正式规则可以得到不同状态；
- unresolved 原因、待补资料和来源可以完整保留到
  SolidifiedAuthorityAnchor；
- 人类补充信息后，通过新 EvidenceRef、报告和 snapshot 解除 unresolved；
- QA、DeerFlow、Marketing Planning 不需要 client_search 专属概念。

---

# 附录 A：EvidenceRef 原始定义

当前公共定义位于 `impl/core/schema/evidence.py`：

```python
from dataclasses import dataclass, field
from typing import Any, Dict

from ..path_contract import LogicalPathRef


@dataclass
class EvidenceRef:
    ref_id: str
    source: str = ""
    kind: str = ""
    stage: str = ""
    summary: str = ""
    location: str = ""
    location_ref: LogicalPathRef | None = None
    payload: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

schema v2 中，文件、文档、函数、trace、test 和 dataset 使用：

```python
@dataclass(frozen=True)
class LogicalPathRef:
    location_scope: PathScope
    location: str
    symbol: str = ""
    revision: str = ""
    sha256: str = ""
```

职责关系：

```text
EvidenceRef
  定位资料和版本
        ↓
MaterialInvestigation
  保存资料引用及其唯一决定范围
        ↓
MaterialDecision
  明确资料在哪个维度、场景和条件下唯一决定什么
        ↓
MaterialConnection
  直接说明上下游和同级资料怎么依赖及产生什么影响
        ↓
AuthorityFinding
  在完成资料调查后表达当前可以或不可以得到的结论
```

不得把业务角色、冲突关系和 Authority 结论塞进
`EvidenceRef.metadata`。
