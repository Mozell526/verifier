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
`MaterialInvestigation` 都必须同时写出 `source_ref_id` 和可直接识别资料的
`source_location`。这样单独阅读一份资料分析时，不需要返回总览查位置。
`source_location` 由 Core 从 EvidenceRef 复制和校验，不能由 Harness AI
自由填写。

进入 Authority Report 的 EvidenceRef 必须具有完整 `location_ref`。这个要求
不仅适用于源码和文档，也适用于 API observation、Tool receipt、数据库查询和
人工澄清：

```text
文件、文档、代码
  → business://、project:// 等原始 LogicalPathRef

API observation / Tool receipt / 数据库查询 / 人工澄清
  → 先确定性保存为不可变 JSON/Markdown artifact
  → artifact://evidence/<ref_id>.<ext>
  → EvidenceRef.location_ref
  → MaterialInvestigation.source_location
```

非文件资料不得只保存在 `EvidenceRef.payload` 或自由 metadata 中进入 Authority
Report。Core 必须先将规范化内容、采集时间、采集方式、适用环境以及能够取得的
revision/hash 固化为 artifact，再复制完整 LogicalPathRef。这样保留完整路径，
同时让外部观察和人工补充也可审计、可复现。

### 3.2 AuthorityInvestigationReport：调查阶段的交付

Authority Investigation 必须按以下内部步骤执行：

```text
1. 资料登记
   输入：InvestigationManifest.evidence_refs
   输出：本次必须调查的资料清单

2. 逐份资料调查
   输出：MaterialInvestigation[]
   回答：每份资料在哪些结论种类、场景和条件下唯一决定什么

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
| 逐份资料调查 | 定义每份资料的唯一决定范围 | 校验 decisions 非空且定位有效 | 每份资料至少唯一决定一个业务事项 |
| 资料连接分析 | 说明上游、下游和同级资料的实质业务连接 | 校验资料路径和方向 | 每条连接都说明对方做什么和如何影响当前资料 |
| Finding 归纳 | 按业务事项、场景和条件匹配 Decision | 校验重叠范围已区分或已标记 unresolved | 结论及冲突原因都能回溯 |

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

    # 只保留跨阶段需要的资料引用。
    basis_source_ref_ids: tuple[str, ...]

    status: Literal["resolved", "unresolved"]

    # resolved 时必填。
    result: str | None

    # 为什么 basis materials 足以或不足以支持本 Finding。
    # 必须基于这些资料的 Decision、Connection 和确定性验证结果。
    resolution_reason: str

    # unresolved 时必填。
    unresolved_reason: str | None
    required_evidence: tuple[str, ...]

    # 引用 InvestigationManifest.tool_requirements。
    tool_requirement_ids: tuple[str, ...] = ()
```

`finding_id` 是项目内稳定关联键，不从 `business_question` 的自然语言 slug
推导。修改措辞、翻译语言或调整标点不得改变 ID；只有业务问题本身被拆分、
合并或替换时才创建新 ID。Harness AI 可以提出 ID，Core 只校验格式、唯一性和
同一 Finding 跨 Report/Solidify 投影的一致性。

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

多个 Decision 在相同业务事项、场景和条件下重叠
  ├─ 存在明确 supersedes → 使用生效 Decision
  └─ 无法区分            → unresolved

没有适用 Decision
  → unresolved，required_evidence 说明缺少哪类唯一决定资料
```

`resolution_reason` 补足“资料引用”和“结论”之间的业务解释：

```text
basis_source_ref_ids
  回答：依据了哪些资料

resolution_reason
  回答：这些资料的具体说法、上下游关系或验证结果，
        为什么足以支持 result，或者为什么仍不足以得出结论
```

它不得写成“因为该资料优先级更高”。其中出现“来自生产系统”“经过正式
审批”“已由 API/数据库验证”等事实时，必须能回指对应
`derived_from / validated_by` Connection 和 EvidenceRef。不能取得证据时，应
写入资料边界并保持 Finding unresolved。

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
    dimension_ids: tuple[str, ...]
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
Judge 上下文。`resolution_reason` 也保留在 Authority Report 中用于调查审计，
不复制到最小 Anchor；unresolved 的运行时原因继续由 Anchor 中的
`unresolved_reason + required_evidence + basis_source_ref_ids` 表达。

## 5. 与 Judge 运行时的交接边界

本协议到 `SolidifiedAuthorityAnchor` 为止。它只保证：

- Anchor 来自已经固化的 AuthorityFinding；
- Anchor 保留 Finding 的 `dimension_ids`，供 Judge Gate 确定性检查；
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
            conclusion_kind="current_behavior",
            governs="dev 部署默认选择哪一份字段定义文件",
            statement=(
                "FIELD_DEFINITIONS_PATH 指向 "
                "config/field_definitions_args.yaml"
            ),
            locator="$.FIELD_DEFINITIONS_PATH",
            scenario="client_search Parser 在 dev 环境初始化",
            conditions=(
                "ENV=dev",
                "FIELD_DEFINITIONS_PATH 未被更高优先级配置覆盖",
            ),
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
            conclusion_kind="current_behavior",
            governs=(
                "当前被选中字段配置中包含哪些检索文本、字段、"
                "操作符、值类型、说明、示例和反例"
            ),
            statement=(
                "intents 条目分别声明当前配置提供的检索文本、字段、"
                "操作符、值类型和说明"
            ),
            locator="$.intents[*]",
            scenario="Parser 使用字段知识进行检索和字段校验",
            conditions=(
                "当前环境配置指向该文件",
                "文件 revision/hash 与调查快照一致",
            ),
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
            conclusion_kind="current_behavior",
            governs="字段定义如何被加载、展开并转化为运行时检索知识",
            statement=(
                "FieldRegistry 加载字段配置、展开引用，并建立运行时字段索引"
            ),
            locator="FieldRegistry",
            scenario="Parser 初始化字段注册表并执行字段意图检索",
            conditions=("当前部署执行该 FieldRegistry revision",),
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
            conclusion_kind="current_behavior",
            governs="最终结构化条件如何执行字段合法性校验",
            statement=(
                "QueryRouter 使用加载后的字段集合校验最终结构化条件"
            ),
            locator="QueryRouter._load_validation_data",
            scenario="Parser 汇总各解析层结果并生成最终条件",
            conditions=("当前部署执行该 QueryRouter revision",),
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

### 资料调查后的两个 Finding

现有资料能够支持“当前系统如何做”：

```python
AuthorityFinding(
    finding_id="client-search-current-field-validation",
    finding_kind="current_behavior",
    business_question="当前部署使用什么字段知识校验结构化条件？",
    dimension_ids=("downstream-query-consumability",),
    basis_source_ref_ids=(
        "client-search-dev-runtime-config",
        "client-search-field-definitions",
        "client-search-field-registry",
        "client-search-query-router",
    ),
    status="resolved",
    result="使用当前环境选中的字段配置形成运行时字段集合并执行校验。",
    resolution_reason=(
        "环境配置选择字段定义文件；字段定义声明字段知识；"
        "FieldRegistry 将其转化为运行时索引；QueryRouter 使用该集合校验输出。"
        "四份资料的 statement 和 dependency 连接形成完整当前行为链。"
    ),
    unresolved_reason=None,
    required_evidence=(),
)
```

相同资料不能支持“正式业务应该如何做”：

```python
AuthorityFinding(
    finding_id="client-search-normative-field-contract",
    finding_kind="normative_rule",
    business_question="下游正式接口允许哪些字段？",
    dimension_ids=("downstream-query-consumability",),
    basis_source_ref_ids=(
        "client-search-field-definitions",
        "client-search-query-router",
    ),
    status="unresolved",
    result=None,
    resolution_reason=(
        "字段配置和 QueryRouter 只能证明当前实现加载、校验了什么；"
        "两份资料都明确不决定下游正式接口契约，也没有 provider 验证结果。"
    ),
    unresolved_reason="缺少能够决定下游正式字段范围的资料。",
    required_evidence=(
        "带版本的下游正式接口字段契约，或可复现的 provider 字段能力查询结果",
    ),
)
```

这个差异保证“当前代码确实这样做”不会被偷换成“正式业务就应该这样做”。

## 7. 核心 Validator

结构校验：

- `source_ref_id` 必须引用当前 Manifest 中存在的 EvidenceRef；
- `source_location` 必须等于该 EvidenceRef 的 `location_ref`；
- Core 必须按 `source_location.revision + sha256` 校验实际读取的资料；
- 每个 MaterialInvestigation 的 `decisions` 必须非空；
- Decision 的 `governs`、`statement` 和 `locator` 必须非空；
- Connection 的 source_ref_id 必须存在于 Manifest；
- Connection 的 source_location 必须与对应 EvidenceRef 一致；
- Connection.effect 不得为空或只写“相关”“被使用”；
- Finding 的 basis_source_ref_ids、Dimension 和 ToolRequirement 必须存在；
- Finding ID 必须在项目内稳定且唯一，不得从 `business_question` 文案临时
  生成；
- resolved 必须有 `result` 和 `resolution_reason`，不得有
  `unresolved_reason`；
- unresolved 必须有 `unresolved_reason` 和 `required_evidence`；
- unresolved 也必须有 `resolution_reason`，说明现有资料为什么不足。

业务边界校验：

- 每份 Authority Material 必须至少唯一决定一个明确业务事项；
- Decision 的 scenario 和 conditions 必须是项目级范围，不得包含单个 badcase；
- Finding 的 kind 必须与适用 Decision 一致，Dimension 引用必须存在；
- Finding 只通过 `dimension_ids` 关联 Judge 评价范围，不得为资料内部步骤
  虚构 EvaluationDimension；
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
- `resolution_reason` 只能引用 `basis_source_ref_ids` 对应资料已有的
  Decision、Connection 和确定性验证结果；
- 声称资料“派生自生产系统”“经过正式审批”时，必须有
  `relation="derived_from"` 的 Connection 和 EvidenceRef；
- 声称结论已经由数据库、API 或其他工具验证时，必须有
  `relation="validated_by"` 的 Connection，并指向实际 Tool receipt
  EvidenceRef；只有 ToolRequirement 不代表已经验证；
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

AuthorityFinding.resolution_reason
  → AuthorityAnalysis.anchor.causal_reasoning

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

    # 正式 JSON 保存完整 LogicalPathRef；案例和 Markdown 渲染为前缀路径。
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
每份资料都必须明确：它在哪个结论种类、场景和条件下，是哪个业务事项的唯一决定
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

Core 负责复制和一致性校验，Harness AI 不得自行拼写路径。报告不复制
完整文件内容；大型资料按 `spec/alg/investigate-keyindex.md` 建立索引并按需
读取。正式 JSON 继续保存完整 `LogicalPathRef`，案例和 Markdown 只显示：

```text
business://src/main/python/config/field_definitions_args.yaml
artifact://evidence/marketing-intent-provider-capability.json
```

定位代码 symbol 时单独显示 `locator`。revision 和 sha256 由 EvidenceRef 与
InvestigationSnapshot 固化，不在每条业务说明中重复展开。

Markdown 必须以该结构逐份展开：

```text
资料名称
├── source_ref_id
├── source_location：business:// 等逻辑路径缩写
├── decisions：唯一决定什么、资料具体怎么说、在哪里核验
├── related_to：相关但不决定什么
├── connections：上下游和同级资料怎么连接
└── 资料边界
```

## 11. MaterialDecision：资料的唯一决定范围

```python
@dataclass(frozen=True)
class MaterialDecision:
    conclusion_kind: Literal[
        "current_behavior",
        "normative_rule",
        "external_fact",
    ]

    # 该资料在本范围内唯一决定的业务事项。
    governs: str

    # 该资料对该事项具体给出的说法。
    statement: str

    # statement 在资料中的稳定定位：JSON/YAML path、章节、symbol 或 key。
    locator: str

    # 项目级场景类型，不得包含单个 runtime Case。
    scenario: str

    # 资料成为唯一决定标准所必需的生效条件。
    conditions: tuple[str, ...]

```

“唯一”只在以下组合内成立：

```text
conclusion_kind + governs + scenario + conditions
```

MaterialDecision 不直接引用 `EvaluationDimension`。资料调查首先忠实表达资料
自身决定的事项，不能为了通过引用校验而把配置加载、内部函数或执行步骤包装成
Judge 业务维度。只有综合后的 `AuthorityFinding.dimension_ids` 负责把资料结论
连接到 Judge EvaluationDimension。

`governs` 与 `statement` 不得混淆：

```text
governs
  这份资料决定的业务事项是什么

statement
  这份资料对该事项具体说了什么

locator
  人类到资料的哪个位置核验这句话
```

没有具体 `statement + locator`，不得仅凭“这份资料负责某事”形成
MaterialDecision。大资料的 locator 可以使用
`spec/alg/investigate-keyindex.md` 定义的 key。

它不是宣称某份资料在整个项目中永远最高。决定相同业务事项的资料可以分别
适用于：

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
        "derived_from",
        "validated_by",
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

Relation 的业务含义：

- `dependency`：一份资料如何选择、消费或约束另一份资料；
- `derived_from`：当前资料内容从哪个有证据的真实来源或生产过程产生；
- `validated_by`：当前资料的说法被哪个实际实验、查询或 Tool receipt 验证；
- `supersedes`：明确的版本、生效或审批关系使一份资料覆盖另一份资料；
- `conflicts_with`：两份资料在重叠的决定范围内给出不能同时成立的 statement。

`derived_from` 和 `validated_by` 都必须指向真实 EvidenceRef。无法证明 origin、
producer 或验证结果时，不得根据文件名或模型常识补造 Connection；应写入
`limitations`，必要时形成 unresolved Finding。

Connection 仍必须携带完整 `source_location`。对非文件证据，该路径指向先行
固化的 `artifact://` 资产；禁止用 URL、请求描述或 payload 摘要冒充路径。

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
资料在某个结论种类、场景和条件下唯一决定一个业务事项
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

最小结构化案例。这里假设 QA Judge Contract 已将
`business-factual-accuracy` 登记为 EvaluationDimension：

```python
MaterialInvestigation(
    source_ref_id="qa-judge-boundary-policy",
    source_location="project://judge_boundary.md",
    decisions=(
        MaterialDecision(
            conclusion_kind="current_behavior",
            governs="当前 QA Judge 在不同证据场景下允许使用什么依据",
            statement=(
                "qa_gold_answer 使用 gold；qa_context_faithfulness 只按 contexts；"
                "qa_weak_quality 不得宣称事实准确性"
            ),
            locator="## Evidence boundaries",
            scenario="QA 评估已经产生的回答",
            conditions=("使用当前项目 Judge boundary revision",),
        ),
    ),
    related_to=("gold 是否经过正式业务治理，需要独立 provenance policy。",),
    connections=(),
    limitations=("它决定当前 Judge 政策，不自动证明 gold 是正式业务真相。",),
)

AuthorityFinding(
    finding_id="qa-current-evidence-policy",
    finding_kind="current_behavior",
    business_question="当前 QA Judge 在各 scenario 下允许依据什么进行判断？",
    dimension_ids=("business-factual-accuracy",),
    basis_source_ref_ids=("qa-judge-boundary-policy",),
    status="resolved",
    result="按 gold、context、weak-quality 三类场景使用不同证据边界。",
    resolution_reason="项目 Judge boundary 对三类场景分别给出明确规则。",
    unresolved_reason=None,
    required_evidence=(),
)
```

当前样本的 question、gold、context 和 actual 仍是 runtime evidence，不进入
上述静态 Authority Report。

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

API 或 Tool 调查结果必须先获得完整 artifact 路径：

```python
provider_capability_location = LogicalPathRef(
    location_scope=PathScope.ARTIFACT_PACKAGE,
    location="evidence/marketing-intent-provider-capability.json",
    revision="本次 InvestigationSnapshot ID",
    sha256="规范化 artifact 的实际 sha256",
)

MaterialInvestigation(
    source_ref_id="marketing-intent-provider-capability",
    source_location=provider_capability_location,
    decisions=(
        MaterialDecision(
            conclusion_kind="external_fact",
            governs="本次调查快照中 provider 实际暴露的意图标签集合",
            statement="provider capability probe 返回 7 个意图标签",
            locator="$.result.intent_labels",
            scenario="单轮 intent-recognition 接口能力调查",
            conditions=("artifact 中记录的环境、接口和采集时间保持适用",),
        ),
    ),
    related_to=("正式产品应该开放哪些意图，仍由受治理业务分类资料决定。",),
    connections=(),
    limitations=("这是带环境和时间边界的外部事实，不是永久业务规范。",),
)
```

原始 API 响应、采集参数和 hash 都保存在上述 artifact；不能只把响应塞进
EvidenceRef.payload 后声称完成验证。

在 intent 项目中，该 Finding 只能关联意图正确性维度；在完整 planning 项目中
也不能关联澄清、规划结果或 SSE 完整性维度。Authority 的适用范围由
`project_id + AuthorityFinding.dimension_ids` 确定，不再建立一套没有统一
注册表的 stage ID。

## 17. 当前验证状态

| 项目 | 状态 |
|---|---|
| `client_search` | 已基于真实业务资料生成报告案例 |
| `QA` | 已用项目政策资料完成结构化表达验证，尚无 Judge Authority Report |
| `deerflow` | 已完成业务链语义推演，尚缺结构化案例和 Judge Authority Report |
| `marketting-planning` | 已用 artifact 化外部观察完成结构化表达验证，尚无 Judge Authority Report |
| `marketting-planning-intent` | 与 Marketing Planning 共享上述表达验证，尚无 Judge Authority Report |

因此当前只能确认 client_search、QA 和 Marketing Planning 三类资料形状可由
Schema 表达；DeerFlow 仍只是语义推演。所有非 client_search 项目都不能宣称
Manifest、Solidify 和 runtime 已经实测通过。

---

# 第四章：Changes

## 18. 当前差异

1. AuthorityAnalysis 仍是观点轴心，可能先提观点再找资料；
2. 当前缺少结构化 Authority Report；
3. 当前没有明确每份 Authority 资料唯一决定的事项、场景和条件；
4. 当前行为、正式规则和外部事实没有稳定分离；
5. unresolved Finding 无法稳定回指具体资料声明和待补证项；
6. 跨项目、跨 EvaluationDimension 引用缺少确定性门禁；
7. 单份资料调查只保存 source ID，阅读时无法直接知道对应哪个文件；
8. MaterialDecision 只写“决定什么”，没有固化资料的具体说法和定位；
9. Finding 只有 result 和来源 ID，没有解释这些资料为什么足以或不足以支持
   结论；
10. 资料来源和动态验证可能停留在自由文本，无法确认是否有真实 EvidenceRef；
11. 非文件证据可能只保存在 payload 中，没有完整、可复查的逻辑路径；
12. 当前没有明确分开“资料内部决定范围”和“Judge 业务评价维度”，迁移时容易
    为内部资料步骤虚构业务维度；
13. 项目间没有统一 business-stage registry，不能把 stage ID 作为强制合同；
14. 跨阶段 Authority ID 缺少稳定性约束，不能从可改写的自然语言问题推导。

## 19. 一次性改造任务

### P0：调查产物

- 新增 Report JSON 和确定性 Markdown 渲染；
- 使用固定 logical path/purpose 登记 artifact_refs；
- 调查 Manifest 中的真实业务资料，只将具有非空 decisions 的资料固化为
  MaterialInvestigation；
- Core 将 EvidenceRef.location_ref 固化到每个
  MaterialInvestigation.source_location；
- API observation、Tool receipt、数据库查询和人工澄清必须先保存为
  `artifact://` 资产，再进入 Authority Report；
- 为每份 Authority 资料生成至少一个 MaterialDecision，且不让 Decision
  虚构 Judge EvaluationDimension；
- 每个 MaterialDecision 固化 `governs + statement + locator`；
- 使用 related_to 表达相关但不决定的事项；
- 使用 MaterialConnection 直接表达上下游、来源、验证、同级冲突和覆盖关系；
- Finding 的来源引用只保留 basis_source_ref_ids；
- Finding 使用 `resolution_reason` 解释资料如何支持或不足以支持结论；
- Finding 只通过真实 EvaluationDimension ID 连接 Judge，不再复制 stage ID；
- Finding ID 使用稳定项目键，不从自然语言文案生成；
- 将旧 AuthorityAnalysis 改为相同 ID 的兼容投影；
- 删除没有真实调查证据的具体 Case Authority 声明。

### P0：Validator

- 校验 EvidenceRef、Material、Connection、Finding、Dimension 和 Tool 引用；
- 拒绝 `decisions` 为空的 Authority Material；
- 拒绝用 `supporting/context_only` 等模糊等级代替唯一决定范围；
- 对重叠 Decision 要求互斥条件、场景区分、supersedes 或 unresolved；
- 拒绝缺少依据的 resolved；
- 拒绝缺少具体原因和 required_evidence 的 unresolved；
- 拒绝缺少 statement、locator 或 resolution_reason 的对象；
- 拒绝缺少完整 source_location 的文件或非文件 Authority Evidence；
- 拒绝只存在 payload、没有 artifact LogicalPathRef 的非文件 Authority
  Evidence；
- 拒绝没有 EvidenceRef 的 derived_from/validated_by 声明；
- 拒绝把 ToolRequirement 当成已执行的验证结果；
- 拒绝 current_behavior 解除正式规则 Gate；
- 拒绝跨 project、snapshot 和 EvaluationDimension 引用；
- 拒绝把 QA 逐样本 reference 固化为项目级 Finding。

### P0：Solidify 交付

- 将 Finding 投影为 SolidifiedAuthorityAnchor；
- 保证 Anchor 保留 Finding 的 Dimension、状态、原因、资料声明和待补证项；
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
- 文件和非文件 Authority 资料都具有完整 LogicalPathRef；
- 每个决定性说法都能通过 locator 回到真实资料；
- resolved 和 unresolved Finding 都能说明资料为什么足够或不足；
- 来源、审批或动态验证声明都有 EvidenceRef，而不是 Harness AI 推测；
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
  明确资料在哪个结论种类、场景和条件下唯一决定什么
        ↓
MaterialConnection
  直接说明上下游和同级资料怎么依赖及产生什么影响
        ↓
AuthorityFinding
  在完成资料调查后表达当前可以或不可以得到的结论
```

不得把业务角色、冲突关系和 Authority 结论塞进
`EvidenceRef.metadata`。
