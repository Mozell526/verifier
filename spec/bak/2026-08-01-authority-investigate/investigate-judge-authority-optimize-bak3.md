# Judge Authority 调查优化协议

本文是 `spec/alg/investigate-judge-authority.md` 的优化提案。

本文不改变：

- `BusinessExpectation → EvaluationDimension → LiveBoundary` 的 Judge 主框架；
- 公共 `InvestigationManifest`、`EvidenceRef`、`ToolRequirement`；
- `Investigate → Solidify → Draft Loop → Promote` 流程；
- runtime `BusinessExpectation` 的既有业务语义：表示当前 Case 中一条可以单独
  判断的业务要求；
- `FulfillmentAssessment`、`JudgeResult` 和三态聚合协议；
- Production 和公共协议实现。

本文只在 Draft Judge 调查中新增资料轴心的 Authority Investigation 阶段，
并明确该阶段如何产出可供 Solidify 使用的 Authority 交付。

当前 Case 如何形成 runtime `BusinessExpectation`，仍由
`spec/alg/investigate-judge.md` 定义。本文只补充它与 Authority 的最小绑定和
`not_evaluable` Gate，不新增 `CaseEvaluationPoint`，也不要求新增一次
Planning LLM。大型资料如何建立索引和按需加载，统一由
`spec/alg/investigate-keyindex.md` 定义。

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

4. 候选 Authority 归纳
   输入：JudgeInvestigationContract 的 BusinessExpectation /
         EvaluationDimension，以及已经完成的 MaterialInvestigation[]
   输出：工作中的 AuthorityFinding[]
   回答：Judge 的有限 Authority 依赖，根据当前资料能否得到结论

5. unresolved 驱动的定向补证循环
   输入：工作中 status=unresolved 的 AuthorityFinding.required_evidence
   动作：沿现有资料的来源、审批、生效、替代、上下游和验证连接继续调查
   输出：新增 EvidenceRef，以及新增或更新的 MaterialInvestigation
   回到：步骤 3 和步骤 4

6. Report 冻结
   条件：Finding 已 resolved，或当前授权范围内已没有可继续取得的决定性证据
   输出：AuthorityInvestigationReport
   约束：每个 finding_id 只保留最后一次 AuthorityFinding
```

顺序不得颠倒。特别禁止先生成 Finding，再围绕 Finding 挑选资料。
Judge 调查合同只限定最终需要服务的业务判断范围，不得被用来预设答案或排除
与业务范围有关的资料。Finding 必须在逐份资料调查和连接分析完成后综合形成。

第一次得到 `status="unresolved"` 不是立即交付 Solidify 的信号，而是同一次
已授权 Investigate 内继续补证的起始点：

```text
初始 MaterialInvestigation[]
        ↓
第一次综合
        ↓
工作中的 AuthorityFinding(status="unresolved")
        │
        ├── unresolved_reason：为什么当前不能定夺
        └── required_evidence：接下来应补哪类决定性证据
        ↓
定向补证
        ↓
新增 EvidenceRef
        ↓
新增或更新 MaterialInvestigation
        ↓
使用相同 finding_id 重新综合
        ├── resolved
        └── 仍然 unresolved
```

不新增 `ProvisionalAuthorityFinding` 或 `provisional` 字段。工作状态和最终
状态由容器边界区分：

```text
尚未进入冻结 AuthorityInvestigationReport.findings
  → Investigate 内的工作结果，可以用同一 finding_id 重新生成

已进入冻结 AuthorityInvestigationReport.findings
  → 本次调查的最终结果，才允许进入 Solidify
```

同一轮 Investigate 内，补充资料后不得创建表示同一业务依赖的新 Finding ID。
问题本身没有拆分、合并或替换时，必须保留原 `finding_id`，只更新其资料依据、
状态和结论。

重新分析的起始输入固定为：

```text
上一轮 unresolved Finding 的
  finding_id + business_question + dimension_ids
        +
上一轮 required_evidence 指向的新 EvidenceRef / MaterialInvestigation
        +
该 Finding 原有 basis materials
```

Harness 只需重新调查新增资料、更新受影响的 MaterialConnection，并重新综合受
影响的 Finding；不要求每轮从零扫描整个项目。但重新综合时必须重新比较全部
适用 MaterialDecision，不能只在旧结论上把 `unresolved` 文本改成
`resolved`。

阶段内部的职责分工：

| 内部步骤 | Harness AI | 确定性代码 | 完成标准 |
|---|---|---|---|
| 资料登记 | 发现与业务范围有关的真实资料 | 固化 EvidenceRef、revision 和 hash | 本次资料范围可枚举、可复现 |
| 逐份资料调查 | 定义每份资料的唯一决定范围 | 校验 decisions 非空且定位有效 | 每份资料至少唯一决定一个业务事项 |
| 资料连接分析 | 说明上游、下游和同级资料的实质业务连接 | 校验资料路径和方向 | 每条连接都说明对方做什么和如何影响当前资料 |
| 候选 Finding 归纳 | 按业务事项、场景和条件匹配 Decision；用 unresolved_reason / required_evidence 提出下一轮补证方向 | 校验重叠范围已区分或候选 Finding 已标记 unresolved | 每个候选结果及冲突原因都能回溯 |
| 定向补证 | 沿具体缺口寻找来源、审批、生效、替代或验证资料 | 登记新 EvidenceRef、固化工具结果并拒绝虚构来源 | 新资料进入 Material 调查，或确认当前无法取得 |
| Report 冻结 | 确认所有 Finding 已 resolved 或满足停止条件 | 每个 finding_id 只接受最后一次结果并冻结最终 snapshot | 工作中的 provisional unresolved 不会进入 Solidify |

Harness AI 负责调查和业务解释；代码负责覆盖、引用和边界校验。代码不得替
Harness AI 生成业务结论，Harness AI 也不得绕过确定性校验。

定向补证只能由当前 unresolved 暴露出的决定性缺口驱动：

```text
当前冲突或缺失
    → unresolved_reason
    → required_evidence
    → 明确可能提供该证据的资料、Connection 或 Tool
```

不得把它解释为不受业务范围约束的全仓库、全网络或无限搜索。存在多个
unresolved Finding 时，Harness 可以按共同资料、相同 Tool 或相同责任方合并为
一轮补证，避免为每个 Finding 分别调用 LLM 或重复读取资料。

补证循环只允许在以下条件之一成立时停止：

1. 新资料已经使当前 Finding 可以 `resolved`；
2. 当前资料明确指向的来源、审批、生效、替代、上下游和验证资料已经调查；
3. 所需资料不存在、无法访问或超出本次用户授权的业务范围；
4. 所需事实只能由业务负责人、外部系统或当前不存在的确定性工具提供；
5. 继续搜索已经没有由 `required_evidence` 指向的新证据方向。

最终仍为 unresolved 时：

- `basis_source_ref_ids` 必须包含本次结论实际使用的现有资料；
- `resolution_reason` 必须说明已经跟进了哪些决定性方向，以及为什么仍不足；
- `unresolved_reason` 必须说明当前不能定夺的准确原因；
- `required_evidence` 必须说明未来什么证据可能解除 unresolved；
- 不能只写“存在冲突”“资料不足”或“建议人工确认”。

概念算法：

```python
materials = investigate_initial_materials()

while True:
    candidate_findings = synthesize_findings(
        judge_contract=judge_contract,
        materials=materials,
    )

    unresolved_findings = [
        finding
        for finding in candidate_findings
        if finding.status == "unresolved"
    ]

    new_evidence_refs = investigate_required_evidence(
        unresolved_findings,
        within_current_authorized_scope=True,
    )

    if not new_evidence_refs:
        break

    materials = merge_materials(
        materials,
        investigate_materials(new_evidence_refs),
    )

report = freeze_report(
    materials=materials,
    findings=candidate_findings,
)
```

该伪代码表达职责，不要求按 Finding 单独调用模型。Harness 应优先批量合并
共同补证方向；Core 只负责 EvidenceRef、Material、引用、唯一性和冻结边界，
不得替 Harness 判断业务资料是否足以定夺。

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

`AuthorityInvestigationReport` 及其 `investigation_snapshot_id` 必须在补证循环
结束后一次性冻结。循环中新增资料属于同一次用户明确要求的 Investigate，不得
因为工作集 hash 变化而自动启动新的外部 Investigation。

人类在 Report 冻结后补充资料时，系统只负责登记新的 EvidenceRef。只有用户
再次明确要求 Investigate，才以原 Finding 的
`finding_id + unresolved_reason + required_evidence` 和新增 EvidenceRef 为
起点重新调查；不得由文件或 hash 变化自动重新调查或重新 Solidify。

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

    # 某个 EvaluationDimension 判断所需的有限 Authority 依赖。
    # 必须项目级可复用，不得包含 current Case actual/verdict。
    business_question: str

    # 需求侧：关联 EvaluationDimension.dimension_id。
    # BusinessExpectation 通过 EvaluationDimension.expectation_ids 获取，
    # 不在 Finding 中重复保存 expectation ID 或业务字段。
    dimension_ids: tuple[str, ...]

    # 资料侧：关联本次调查中支持、冲突或不足以支持本 Finding 的资料。
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

#### AuthorityFinding 的交叉定位

`AuthorityFinding` 不是自由生成的观点，也不是一份资料的摘要。它是 Judge
需求侧和资料调查侧之间唯一的综合对象：

```text
JudgeInvestigationContract
  ├── BusinessExpectation
  │     定义：真实业务用户为什么使用产品、最终希望得到什么
  │
  └── EvaluationDimension
        定义：Judge 具体需要判断 Live 的哪项业务贡献
        │
        │ 提出有限的 Authority 依赖
        ▼
AuthorityFinding  ◀──── MaterialInvestigation[]
  定义：该依赖根据当前资料是否已经解决
        │
        ▼ Solidify 忠实投影
SolidifiedAuthorityAnchor
        │
        ▼ 当前 Case 按需绑定 finding_id
RuntimeExpectationBinding
        │
        ▼ 引用既有 runtime BusinessExpectation.expectation_id
runtime BusinessExpectation
        │
        ▼ 既有一对一评价
FulfillmentAssessment
        │
        ▼ 确定性 Authority Gate
resolved   → 正常评价
unresolved → not_evaluable，并说明原因和来源
```

三侧信息的职责必须保持分离：

```text
BusinessExpectation
  回答：为什么需要这项产品能力

EvaluationDimension
  回答：Judge 对这项能力具体判断什么

MaterialInvestigation / MaterialDecision
  回答：每份资料在什么场景和条件下决定什么、具体怎么说

AuthorityFinding
  回答：该判断所依赖的业务事实，根据这些资料能否被定夺
```

Finding 不直接保存 `BusinessExpectation.expectation_id`。关联链固定为：

```text
AuthorityFinding.dimension_ids
    → EvaluationDimension.dimension_id
    → EvaluationDimension.expectation_ids
    → BusinessExpectation.expectation_id
```

这避免 Finding 再复制一套产品期望关联，也避免 Dimension 与 Finding 中的
Expectation 关系发生漂移。

只有满足以下条件才生成 Finding：

1. 至少一个 EvaluationDimension 的判断确实依赖项目资料提供业务标准或外部
   事实；
2. current Case 的 request/actual 直接比较、已有确定性 Comparator 或封闭规则
   不能独立完成判断；
3. 调查已经完成相关资料的 MaterialDecision、Connection 和限制分析；
4. Finding 问题是项目级可复用的有限依赖，不是某个词、字段或 badcase 的临时
   问答。

普通当前行为事实继续保留为 MaterialDecision；只有它确实被某个
EvaluationDimension 作为判断依赖时，才进一步形成
`finding_kind="current_behavior"` 的 Finding。与 Judge 判断无关的资料冲突也
不得生成 Finding。

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

Solidify 只允许读取已冻结 `AuthorityInvestigationReport.findings`。Investigate
工作区中尚未冻结的候选 Finding，即使其当前状态为 unresolved，也不得生成
Anchor、ContextUnit 或 Tool 交付。

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

Authority 调查和 Solidify 的公共交付到 `SolidifiedAuthorityAnchor` 为止。
为了避免下游重新发明 Authority 关联，本节同时固定 Draft Judge 消费 Anchor
时必须遵守的最小接口：

- Anchor 来自已经固化的 AuthorityFinding；
- Anchor 保留 Finding 的 `dimension_ids`，供 Judge Gate 确定性检查；
- `resolved / unresolved`、原因、待补资料和来源引用没有在 Solidify 中丢失；
- Judge 可以沿 `finding_id → basis_source_ref_ids → EvidenceRef` 回溯。

### 5.1 保留 runtime BusinessExpectation 的原有语义

现有 runtime `BusinessExpectation` 是当前 Case 的业务验收项：

> 当前 Case 中一条可以单独得到
> `fulfilled / not_fulfilled / not_evaluable` 的业务要求。

其既有字段继续承担原职责：

```text
user_intent
  当前用户为什么提出这项要求

expected_outcome
  当前 Case 应达到什么结果

acceptance_criteria
  当前要求如何被判断

blocking
  该要求失败是否阻断当前 Case 的整体业务结果
```

现有主链保持不变：

```text
runtime BusinessExpectation[]
        ↓ expectation_id 一对一引用
FulfillmentAssessment[]
        ↓ 根据 BusinessExpectation.blocking 确定性聚合
overall_fulfillment
```

调查侧 `BusinessExpectation` 与 runtime `BusinessExpectation` 不能直接复制或
视为同一个对象：

- 调查侧对象描述项目级、长期稳定的业务目标；
- runtime 对象描述当前 Case 中具体、可单独判断的业务要求；
- 一个 `EvaluationDimension` 可以对应当前 Case 中零个、一个或多个 runtime
  `BusinessExpectation`，不得机械固定为“一维度一个验收项”；
- runtime expectation 的粒度不能因为引入 Authority 而被合并、拆分或改写。

`CaseEvaluationPoint` 不再作为独立业务对象。它与 runtime
`BusinessExpectation` 重复承载 `expected_outcome`、`acceptance_criteria` 和
`blocking`，再转回 runtime `BusinessExpectation` 只会增加一层语义绕行。

### 5.2 最小 Authority 绑定

runtime `BusinessExpectation` 当前没有调查侧 BusinessExpectation、
EvaluationDimension 和 AuthorityFinding 的显式来源字段。不得把这些关系塞进
`boundary`、`evidence_refs`、自由 metadata 或编码进 LLM 生成 ID。

Draft 使用一个最小只读关联记录：

```python
@dataclass(frozen=True)
class RuntimeExpectationBinding:
    # 引用当前 JudgeResult.business_expectations[*].expectation_id。
    runtime_expectation_id: str

    # 引用 JudgeInvestigationContract.business_expectations[*].expectation_id。
    project_expectation_id: str

    # 引用 JudgeInvestigationContract.evaluation_dimensions[*].dimension_id。
    evaluation_dimension_id: str

    # 当前 runtime expectation 的判断实际依赖的 AuthorityFinding。
    authority_finding_ids: tuple[str, ...] = ()
```

该对象只是关系，不是新的评价项：

- 不定义 `binding_id` 或 `point_id`；
- 不复制 `user_intent`、`expected_outcome`、`acceptance_criteria` 或
  `blocking`；
- 不保存 actual、status、score、confidence 或 verdict；
- 不进入公共 `JudgeResult`；
- 不修改 Production 或公共 runtime schema。
- 若当前兼容实现仍有 `authority_analysis_ids`，它只能是由
  `authority_finding_ids` 确定性投影出的旧字段；不能反过来作为 Authority
  绑定的真相源。

它在同一 `JudgeResult.trace_id` 范围内通过 `runtime_expectation_id` 唯一引用
现有 runtime `BusinessExpectation`。`project_expectation_id`、
`evaluation_dimension_id` 和 `authority_finding_ids` 只能从已固化目录中选择，
不得由 LLM 生成新 ID。

该绑定应在对应 runtime `BusinessExpectation` 冻结时一同确定，且不能根据
Assessment 的 status、score 或 actual 偏差事后改变。这个要求不等于必须增加
Planning LLM；绑定可以由确定性规则、既有 reference/expectation 构造步骤或
Draft 内受约束选择产生。

### 5.3 Authority Gate 数据流

完整串联为：

```text
AuthorityFinding.dimension_ids
        ↓ Solidify 忠实投影
SolidifiedAuthorityAnchor.finding_id
        ↑
RuntimeExpectationBinding.authority_finding_ids
        │
        ├── runtime_expectation_id
        │       → runtime BusinessExpectation.expectation_id
        │       → FulfillmentAssessment.expectation_id
        │
        ├── project_expectation_id
        │       → 调查侧 BusinessExpectation.expectation_id
        │
        └── evaluation_dimension_id
                → EvaluationDimension.dimension_id
                → 校验 Finding 是否覆盖该评价维度
```

Gate 按以下顺序执行：

1. 使用 `FulfillmentAssessment.expectation_id` 找到同 ID 的 runtime
   `BusinessExpectation`；
2. 使用该 ID 找到唯一 `RuntimeExpectationBinding`；
3. 校验项目级 expectation、dimension 和 finding 均存在，且 dimension 确实服务
   该项目级 expectation；
4. 校验每个 finding 的 `dimension_ids` 覆盖绑定的
   `evaluation_dimension_id`；
5. 读取当前 Solidify snapshot 中同 `finding_id` 的 Anchor；
6. 绑定为空时，按既有规则评价；
7. 所有绑定 Anchor 均 resolved 时，Judge 使用其固化结论、ContextUnit 或 Tool
   证据正常评价；
8. 任一绑定 Anchor unresolved 时，Core 必须把该 Assessment 约束为
   `not_evaluable`。

Assessment 可以保留现有兼容字段 `authority_analysis_ids` 作为“本次实际使用了
哪些 Authority”的审计回声，但该字段不能新增或解除 Binding 中的依赖，也不能
在 actual 可见后改变 Gate 的适用范围。Canonical Authority 依赖始终来自
`RuntimeExpectationBinding.authority_finding_ids`。

unresolved 的 Assessment 必须同时保留：

```text
runtime BusinessExpectation.expectation_id / expected_outcome
AuthorityFinding.finding_id / business_question
SolidifiedAuthorityAnchor.unresolved_reason
SolidifiedAuthorityAnchor.required_evidence
SolidifiedAuthorityAnchor.basis_source_ref_ids
```

Judge summary 必须明确回答：

```text
哪条当前 Case 业务要求不能评价？
它依赖哪个 Authority？
当前哪些资料产生冲突或不足？
为什么现有资料不能得出结论？
未来补充什么资料可能解除 not_evaluable？
```

缺少 Binding、引用不存在、维度关系不成立或 Anchor 不属于当前 Solidify
snapshot 时，不得静默跳过 Authority 校验，也不得输出没有 Authority 支撑的
肯定结论。Draft 应以结构化失败或有明确原因的 `not_evaluable` 结束当前评价。

### 5.4 语义回归案例

当前 30 条 client_search 对比结果显示，问题不在原 runtime
`BusinessExpectation`，而在新增 Planning/Point 改写了它的粒度和标准。

`badcase-003` 的原 runtime expectations 分别判断：

```text
1. “在职单”是否映射到 orphanType 字段；
2. orphanType 是否使用合法 MATCH 操作符；
3. 是否映射到正确枚举值；
4. 单条件逻辑是否引入额外约束。
```

当前 Draft Point 只保留“字段、枚举、无额外条件”三项，原独立操作符要求被
静默合并或遗漏。这证明把 Dimension 机械展开成 Point 会改变原 runtime
expectation 的语义和粒度。

`badcase-008` 中，原 runtime expectation 明确要求“孤儿单映射到在职有效
客户”，因此 actual 的“纯存续单客户”被判断为 `not_fulfilled`。当前 Draft
把要求改成“映射为代表孤儿单的枚举值”，但既未说明哪个值具有该语义，也未
绑定对应 Authority，最终错误输出 `fulfilled`。

这说明：

```text
Gate 只会约束已经显式绑定的 Authority；
漏掉 Binding 时，确定性 Gate 无法自行猜出业务依赖；
因此不能依靠 Point 改名、全维度默认绑定或 assessment 后处理掩盖依赖遗漏。
```

正确修复是保留原 runtime `BusinessExpectation`，并让
`RuntimeExpectationBinding` 显式串联调查维度和 Authority，而不是重新生成一套
Case 评价对象。

### 5.5 Authority Schema 的统一展示

Authority 不定义专属 `show_authority_*()`。人工审核统一遵从
`spec/alg/investigate-schemashow.md`：

```text
来源 Schema 的字段和值保持原样
    +
↳ [reference → 目标Schema.目标ID字段]
    只展示目标 Schema 的固定关键字段
```

本协议登记以下引用关系：

| 来源字段 | 目标 |
|---|---|
| `AuthorityFinding.dimension_ids` | `EvaluationDimension.dimension_id` |
| `EvaluationDimension.expectation_ids` | `BusinessExpectation.expectation_id` |
| `AuthorityFinding.basis_source_ref_ids` | `MaterialInvestigation.source_ref_id` |
| `SolidifiedAuthorityAnchor.finding_id` | `AuthorityFinding.finding_id` |
| `RuntimeExpectationBinding.project_expectation_id` | 调查侧 `BusinessExpectation.expectation_id` |
| `RuntimeExpectationBinding.evaluation_dimension_id` | `EvaluationDimension.dimension_id` |
| `RuntimeExpectationBinding.authority_finding_ids` | `SolidifiedAuthorityAnchor.finding_id` |
| `RuntimeExpectationBinding.runtime_expectation_id` | runtime `BusinessExpectation.expectation_id` |

用于 Authority 审核的最小展示字段：

| Schema | 固定展示字段 |
|---|---|
| `BusinessExpectation` | `user_role`、`use_scenario`、`desired_outcome` |
| `EvaluationDimension` | `name`、`evaluation_question`、`expectation_ids` |
| `MaterialInvestigation` | `source_location`、`decisions` |
| `AuthorityFinding` | `finding_kind`、`business_question`、`dimension_ids`、`basis_source_ref_ids`、`status`、`result`、`resolution_reason`、`unresolved_reason`、`required_evidence` |
| `RuntimeExpectationBinding` | `runtime_expectation_id`、`project_expectation_id`、`evaluation_dimension_id`、`authority_finding_ids` |

`MaterialInvestigation.decisions` 必须展示，因为只显示资料路径无法说明该资料
究竟决定什么，也无法审核 Finding 所称的资料冲突。该规则属于
MaterialInvestigation 的固定人工审阅需要，不是 AuthorityFinding 的 Case
特例。

例如，真实值：

```python
dimension_ids=("customer-segmentation-semantics",)
```

展示为：

```text
dimension_ids:
  - customer-segmentation-semantics
    ↳ [reference → EvaluationDimension.dimension_id]
      name:
        客户分层语义准确性
```

禁止用 `name` 替换原始 ID，也禁止把目标 Schema 字段伪装成
AuthorityFinding 自身的嵌套字段。

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

### Judge 需求侧与资料侧的交叉案例

以下是构造的 Client Search 项目级案例，用于证明 AuthorityFinding 的交叉
定位和 Schema Show 结果，不表示这些示例文件当前真实存在。

Judge 调查合同定义业务期望和评价维度：

```python
BusinessExpectation(
    expectation_id="find-target-customers",
    user_role="需要寻找目标客户的业务人员",
    use_scenario="使用客户搜索产品搜索正式业务分层中的客户",
    desired_outcome="获得符合当前正式客户分层定义的客户集合",
)

EvaluationDimension(
    dimension_id="customer-segmentation-semantics",
    expectation_ids=("find-target-customers",),
    name="客户分层语义准确性",
    evaluation_question=(
        "Live 是否按照当前正式客户分层定义解释客户分层术语？"
    ),
    fulfilled_when=("转换结果符合已经确认的正式定义",),
    not_fulfilled_when=("转换结果违反已经确认的正式定义",),
    not_evaluable_when=("正式定义存在无法解决的资料冲突",),
)
```

调查发现两份资料在同一决定范围内给出不同说法：

```python
MaterialInvestigation(
    source_ref_id="product-segmentation-standard",
    source_location="business://docs/product-segmentation-standard.md",
    decisions=(
        MaterialDecision(
            conclusion_kind="normative_rule",
            governs="客户搜索产品采用的正式客户分层定义",
            statement="重点客户指近十二个月贡献不低于一百万元的客户。",
            locator="客户分层/重点客户",
            scenario="客户搜索产品解释客户分层术语",
            conditions=("当前版本生效",),
        ),
    ),
    related_to=(),
    connections=(),
    limitations=("没有说明是否覆盖销售运营手册。",),
)

MaterialInvestigation(
    source_ref_id="sales-segmentation-handbook",
    source_location="business://docs/sales-segmentation-handbook.md",
    decisions=(
        MaterialDecision(
            conclusion_kind="normative_rule",
            governs="客户搜索产品采用的正式客户分层定义",
            statement="重点客户指近十二个月贡献不低于二百万元的客户。",
            locator="客户查询规则/重点客户",
            scenario="客户搜索产品解释客户分层术语",
            conditions=("当前版本生效",),
        ),
    ),
    related_to=(),
    connections=(),
    limitations=("没有说明是否只适用于特定销售渠道。",),
)
```

综合后的 Finding：

```python
AuthorityFinding(
    finding_id="customer-segmentation-definition",
    finding_kind="normative_rule",
    business_question=(
        "客户搜索产品解释客户分层术语时，"
        "应采用哪套当前生效的正式定义？"
    ),
    dimension_ids=("customer-segmentation-semantics",),
    basis_source_ref_ids=(
        "product-segmentation-standard",
        "sales-segmentation-handbook",
    ),
    status="unresolved",
    result=None,
    resolution_reason=(
        "两份资料在相同业务事项、场景和生效条件下给出了不同定义，"
        "且没有可验证的适用范围区分或版本替代关系。"
    ),
    unresolved_reason=(
        "无法确认产品分层规范和销售运营手册中哪一份当前生效。"
    ),
    required_evidence=(
        "当前生效版本、审批记录、替代关系或适用场景说明",
    ),
)
```

按统一 Schema Show 展示：

```text
AuthorityFinding [schema]

finding_id:
  customer-segmentation-definition

finding_kind:
  normative_rule

business_question:
  客户搜索产品解释客户分层术语时，
  应采用哪套当前生效的正式定义？

dimension_ids:
  - customer-segmentation-semantics
    ↳ [reference → EvaluationDimension.dimension_id]
      name:
        客户分层语义准确性
      evaluation_question:
        Live 是否按照当前正式客户分层定义解释客户分层术语？
      expectation_ids:
        - find-target-customers
          ↳ [reference → BusinessExpectation.expectation_id]
            user_role:
              需要寻找目标客户的业务人员
            use_scenario:
              使用客户搜索产品搜索正式业务分层中的客户
            desired_outcome:
              获得符合当前正式客户分层定义的客户集合

basis_source_ref_ids:
  - product-segmentation-standard
    ↳ [reference → MaterialInvestigation.source_ref_id]
      source_location:
        business://docs/product-segmentation-standard.md
      decisions:
        - conclusion_kind: normative_rule
          governs:
            客户搜索产品采用的正式客户分层定义
          statement:
            重点客户指近十二个月贡献不低于一百万元的客户。
          locator:
            客户分层/重点客户
          scenario:
            客户搜索产品解释客户分层术语
          conditions:
            - 当前版本生效

  - sales-segmentation-handbook
    ↳ [reference → MaterialInvestigation.source_ref_id]
      source_location:
        business://docs/sales-segmentation-handbook.md
      decisions:
        - conclusion_kind: normative_rule
          governs:
            客户搜索产品采用的正式客户分层定义
          statement:
            重点客户指近十二个月贡献不低于二百万元的客户。
          locator:
            客户查询规则/重点客户
          scenario:
            客户搜索产品解释客户分层术语
          conditions:
            - 当前版本生效

status:
  unresolved

result:
  null

resolution_reason:
  两份资料在相同业务事项、场景和生效条件下给出了不同定义，
  且没有可验证的适用范围区分或版本替代关系。

unresolved_reason:
  无法确认产品分层规范和销售运营手册中哪一份当前生效。

required_evidence:
  - 当前生效版本、审批记录、替代关系或适用场景说明
```

该案例的业务含义是：

```text
BusinessExpectation
  要求结果符合正式客户分层定义
        ↓
EvaluationDimension
  需要判断 Live 是否正确解释客户分层术语
        ↓
AuthorityFinding
  需要确认当前正式定义
        ↑
MaterialInvestigation
  两份同范围资料给出冲突定义，无法确定哪份生效
        ↓
unresolved
        ↓
通过 RuntimeExpectationBinding 依赖该 finding_id 的
runtime BusinessExpectation 必须得到 not_evaluable Assessment
```

这里的 “重点客户” 只是展示 MaterialDecision 实际内容的例子。
`business_question` 和 Finding 的适用范围仍是项目级“客户分层正式定义”，
不得为每个客户词语或 runtime Case 新建 Finding。

### 同一 Finding 的补证迭代

上述 `customer-segmentation-definition` 第一次综合为工作中的 unresolved 后，
其 `required_evidence` 指向“生效版本、审批记录、替代关系或适用场景说明”。
Harness 不立即冻结 Report，而是继续调查这些方向。

如果随后取得：

```python
MaterialInvestigation(
    source_ref_id="customer-segmentation-v3-release",
    source_location="business://releases/customer-segmentation-v3.md",
    decisions=(
        MaterialDecision(
            conclusion_kind="normative_rule",
            governs="客户搜索产品当前采用的客户分层正式定义",
            statement=(
                "经批准的客户分层规范 v3 自 2026-06-01 生效，"
                "并替代销售运营手册中的旧版客户分层定义。"
            ),
            locator="发布结论",
            scenario="客户搜索产品解释客户分层术语",
            conditions=("2026-06-01 及以后",),
        ),
    ),
    related_to=(),
    connections=(
        MaterialConnection(
            direction="peer",
            source_ref_id="sales-segmentation-handbook",
            source_location=(
                "business://docs/sales-segmentation-handbook.md"
            ),
            relation="supersedes",
            effect="正式发布结论明确声明 v3 替代销售运营手册中的旧版分层定义。",
        ),
    ),
    limitations=("只决定发布结论声明的产品、场景和生效时间。",),
)
```

则重新使用同一 `finding_id` 综合：

```python
AuthorityFinding(
    finding_id="customer-segmentation-definition",
    finding_kind="normative_rule",
    business_question=(
        "客户搜索产品解释客户分层术语时，"
        "应采用哪套当前生效的正式定义？"
    ),
    dimension_ids=("customer-segmentation-semantics",),
    basis_source_ref_ids=(
        "product-segmentation-standard",
        "sales-segmentation-handbook",
        "customer-segmentation-v3-release",
    ),
    status="resolved",
    result="采用已获批准并生效的客户分层规范 v3。",
    resolution_reason=(
        "新增正式发布资料明确给出生效时间，并声明 v3 替代销售运营手册中的"
        "旧版定义，因此原重叠冲突已经被可验证的 supersedes 关系解除。"
    ),
    unresolved_reason=None,
    required_evidence=(),
)
```

如果审批、版本或场景资料均无法取得，则保留同一 Finding 的最终 unresolved，
并在 `resolution_reason` 中记录已经跟进但仍无法取得的决定性方向。无论最终
状态如何，冻结 Report 中都只保留最后一次结果；中间工作结果不进入
Solidify。

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
- `AuthorityFinding.dimension_ids` 必须能通过
  `EvaluationDimension.expectation_ids` 回到至少一个存在的
  `BusinessExpectation`；
- Finding ID 必须在项目内稳定且唯一，不得从 `business_question` 文案临时
  生成；
- resolved 必须有 `result` 和 `resolution_reason`，不得有
  `unresolved_reason`；
- unresolved 必须有 `unresolved_reason` 和 `required_evidence`；
- unresolved 也必须有 `resolution_reason`，说明现有资料为什么不足。
- 冻结 Report 中每个 `finding_id` 只能存在最后一次 AuthorityFinding；
- 工作中的候选 Finding 不得写入已冻结 Report 或 Solidify 输入。

业务边界校验：

- 每份 Authority Material 必须至少唯一决定一个明确业务事项；
- Decision 的 scenario 和 conditions 必须是项目级范围，不得包含单个 badcase；
- Finding 的 kind 必须与适用 Decision 一致，Dimension 引用必须存在；
- Finding 必须对应至少一个 EvaluationDimension 确实需要的有限 Authority
  依赖；与 Judge 判断无关的资料事实或冲突不得生成 Finding；
- Finding 只通过 `dimension_ids` 关联 Judge 评价范围，不得为资料内部步骤
  虚构 EvaluationDimension；
- Finding 不得重复保存 `BusinessExpectation` 的 ID 或业务字段；
- `current_behavior=resolved` 必须命中 current_behavior Decision；
- `normative_rule=resolved` 必须命中 normative_rule Decision；
- `external_fact=resolved` 必须命中 external_fact Decision；
- 不得用其他 conclusion_kind 的 Decision 替代缺失 Decision；
- 相同决定范围只允许一个当前生效 Decision；
- 重叠 Decision 只有存在互斥条件、场景区分或 peer
  `connection.relation="supersedes"` 时才能 resolved；
- 无适用 Decision 或重叠 Decision 无法消解时，必须 unresolved；
- 现有 MaterialConnection、ToolRequirement 或 required_evidence 仍明确指向
  当前授权范围内可取得的新证据时，不得把候选 unresolved 提前冻结；
- 最终 unresolved 的 resolution_reason 必须说明已跟进的决定性补证方向和停止
  原因，不能只复述 unresolved_reason；
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
“是否还存在值得跟进的新业务资料”主要由 Harness AI 负责；Core 只能对已经
登记的 EvidenceRef、Connection、Tool receipt、required_evidence 和冻结状态做
确定性一致性检查。

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
14. 跨阶段 Authority ID 缺少稳定性约束，不能从可改写的自然语言问题推导；
15. AuthorityFinding 尚未稳定表达为 EvaluationDimension 的有限 Authority
    依赖与 MaterialInvestigation 调查结果之间的交叉对象；
16. 当前人工展示混合裸 ID 和自由说明，无法稳定看到关联的
    BusinessExpectation、EvaluationDimension 和 MaterialDecision 实际值；
17. `basis_source_ref_ids` 只能定位整份 MaterialInvestigation；当一份资料包含
    多个 MaterialDecision 时，尚不能结构化指出 Finding 具体使用或冲突的是哪
    一条 Decision；
18. 当前流程容易把第一次分析得到的 unresolved 直接冻结，尚未形成
    `unresolved → required_evidence → 定向补证 → 重新综合` 的 Investigate
    内部循环。
19. Draft Planning 引入 `CaseEvaluationPoint` 后又把 Point 转回 runtime
    `BusinessExpectation`，造成重复建模和语义绕行；
20. Draft 将 `EvaluationDimension` 机械映射为 Point，已经改变部分旧
    runtime `BusinessExpectation` 的粒度，出现原有操作符、值或逻辑要求被合并
    或遗漏；
21. 当前 Authority Gate 依赖 Planning/Assessment 输出的
    `authority_analysis_ids`，缺少 runtime expectation 到调查 Dimension 和
    Authority 的稳定绑定；绑定遗漏时 Gate 无法主动发现缺失的业务依赖；
22. 当前 runtime `BusinessExpectation`、调查侧 `BusinessExpectation` 和
    EvaluationDimension 的层级关系没有在运行时交接处明确区分，容易把项目级目标
    当成当前 Case 验收项，或反过来用 Case 结果改写项目级标准。

### 18.1 概念引入时间、业务职责与本次处置

本表中的“引入阶段”表示概念相对于本次 Authority 优化的来源，不表示代码提交
日期。实现和迁移时必须按“本次处置”理解，不能因为一个旧概念仍出现在兼容代码中，
就把它继续当作长期协议的一部分。

| 概念 | 引入阶段 | 所属业务阶段 | 业务职责 | 本次处置 |
|---|---|---|---|---|
| `RunTrace` | 原有 Judge 主链 | Runtime 输入 | 保存当前 Case 的请求、实际输出和可引用运行证据 | 保留，不改变语义 |
| `EvidenceRef` | 原有证据基础设施 | Investigate / Solidify / Runtime 共用 | 为文件、artifact、Tool receipt 等证据提供可追溯引用 | 保留；Authority 资料必须落到真实 EvidenceRef |
| runtime `BusinessExpectation`（`impl/core/schema/judge.py`） | 原有 Judge 主链 | Runtime Judge | 表示当前 Case 中一条可以单独判断的业务要求；保存 `blocking`、`expected_outcome` 和 `acceptance_criteria` | 原样保留，仍是当前 Case 唯一业务验收项 |
| `FulfillmentAssessment` | 原有 Judge 主链 | Runtime Judge | 对一条 runtime `BusinessExpectation` 给出三态评价和证据 | 原样保留；Authority Gate 只允许约束其结果，不替代它 |
| `JudgeResult` | 原有 Judge 主链 | Runtime 输出 | 汇总当前 Case 的业务要求、逐项评价、差异和摘要 | 原样保留；不加入 Authority 调查内部对象 |
| `overall_fulfillment` | 原有 Judge 主链 | Runtime 聚合 | 从 blocking assessments 确定性聚合整体结果 | 原样保留；Authority 只通过改变对应 assessment 间接影响它 |
| `ContextUnit` / `ContextUnitRecord` | Authority 之前已有的上下文基础设施 | Solidify 交付 / Runtime 加载 | 承载已固化、可在 Judge 中消费的上下文资产 | 复用，不作为 Authority 的第二套真相 |
| `ToolRequirement` | Authority 之前已有的调查基础设施 | Investigate | 描述为了补足证据还需要什么 Tool 能力；不代表 Tool 已经执行 | 复用；执行结果必须另存 EvidenceRef |
| `InvestigationManifest` | Authority 之前已有的调查基础设施 | Investigate 输入 | 登记调查范围内的资料、Tool 和逻辑路径 | 复用，作为资料轴心调查的入口 |
| investigation `BusinessExpectation`（`impl/core/schema/investigation_judge.py`） | Judge 调查合同阶段引入 | 项目级 Investigate | 定义该业务项目长期需要守住的用户目标 | 保留；与同名 runtime Schema 是两个层级，不能互相替代 |
| `EvaluationDimension` | Judge 调查合同阶段引入 | 项目级 Investigate | 把项目级业务目标拆成有限、稳定的评价角度，并定义三态边界 | 保留；它约束 runtime expectation 的评价来源，但不机械生成 runtime expectation |
| `LiveBoundary` | Judge 调查合同阶段引入 | 项目级 Investigate | 划定被测系统在业务链中的责任边界 | 保留，避免把外部责任错误归因给当前系统 |
| `AuthorityAnalysis` / `SourceClaim` / `CausalChain` / `AuthorityAnchor` | 第一轮 Authority 方案引入 | Investigate | 以“判断观点”为轴心收集来源并给出 resolved/unresolved | 不再作为长期主模型；迁移期可作为 `AuthorityFinding` 的兼容投影 |
| Authority constraints / deterministic Gate | 第一轮 Authority 实现引入 | Runtime Judge | 当当前评价明确依赖 unresolved Authority 时，禁止输出无权威支撑的肯定结论 | 保留确定性 Gate 思想；改用稳定 Binding 和 Solidified Anchor 驱动 |
| `CaseEvaluationPoint` | 最近 Draft Planning 实验引入 | Draft Runtime Planning | 尝试在看到 actual 前生成当前 Case 的验收点 | 删除长期协议定位；它复制了 runtime `BusinessExpectation` 的核心字段和职责 |
| `FrozenCaseEvaluationPlan` | 最近 Draft Planning 实验引入 | Draft Runtime Planning | 冻结 Planning LLM 生成的 Points 和 Authority 快照 | 不作为本协议必需对象；本次优化不要求额外 Planning LLM |
| `ProductExpectation` | 最近 Planning 文案/实现中使用 | Draft Runtime Planning | 实际上指向项目级业务期望，但形成了第三种相近期望命名 | 统一回 investigation `BusinessExpectation`，不再建立别名层 |
| `AuthorityInvestigationReport` | 本次 Authority 优化新增 | Investigate 输出 | 汇总本次资料调查、资料关系和最终 Finding | 新增长期调查报告；它是阶段交付，不是 Runtime Judge 对象 |
| `MaterialInvestigation` | 本次 Authority 优化新增 | Investigate | 以一份真实业务资料为主轴，记录其来源、定位、决定范围、相关范围和局限 | 新增长期核心 Schema |
| `MaterialDecision` | 本次 Authority 优化新增 | Investigate | 表示一份资料在特定条件和场景下唯一决定的业务事项 | 新增长期核心 Schema；resolved 结论必须能回到具体 Decision |
| `MaterialConnection` | 本次 Authority 优化新增 | Investigate | 说明资料之间的上下游消费、来源、验证、覆盖、替代或冲突关系 | 新增长期核心 Schema；只记录影响 Authority 判断的实质连接 |
| `AuthorityFinding` | 本次 Authority 优化新增 | Investigate 综合 | 作为 `EvaluationDimension` 的有限 Authority 依赖与资料调查结果的交叉结论，回答“根据当前资料能否得出结论” | 新增长期权威结论；替代观点轴心的 `AuthorityAnalysis` |
| `SolidifiedAuthorityAnchor` | 本次 Authority 优化新增 | Solidify | 忠实冻结 Finding 的状态、理由、来源和待补证项，供 Runtime 使用 | 新增长期交付 Schema；不得在 Solidify 中重新解释调查结论 |
| `RuntimeExpectationBinding` | 本次 Authority 优化新增 | Draft Runtime 交接 | 只建立一条 runtime expectation 到项目级 expectation、dimension 和 finding 的 ID 关系 | 最小新增关系 Schema；不复制业务内容，不进入公共 `JudgeResult` |

两个同名 `BusinessExpectation` 必须明确区分：

```text
investigation BusinessExpectation
    = 项目级长期业务目标

runtime BusinessExpectation
    = 当前 Case 中一条可独立判断的业务要求
```

二者不是一对一复制关系。一个项目级业务目标可以在不同 Case 中形成不同数量和粒度
的 runtime requirements；一个 `EvaluationDimension` 也可以对应零条、一条或多条
runtime requirements。迁移不得为了方便绑定而强迫拆分或合并原有 runtime
`BusinessExpectation`。

### 18.2 当前 Draft 链路与目标链路

当前 Draft 的实际绕行是：

```text
项目级 BusinessExpectation / EvaluationDimension / AuthorityAnalysis
    ↓ Planning LLM
CaseEvaluationPoint[]
    ↓ as_business_expectation()
runtime BusinessExpectation[]
    ↓ Assessment LLM
FulfillmentAssessment[]
    ↓ authority_analysis_ids + Gate
JudgeResult
```

问题不只是多一次 LLM 调用，而是 `CaseEvaluationPoint` 重新定义了本应由 runtime
`BusinessExpectation` 承担的业务验收语义。Planning 一旦合并、遗漏或泛化 Point，
后续 Assessment 和 Authority Gate 都只能判断这套已经被改写的标准。

本次改造后的目标链路是：

```text
InvestigationManifest + EvidenceRef
    ↓ Investigate：以资料为轴心调查
MaterialInvestigation
    ├── MaterialDecision
    └── MaterialConnection
    ↓ 与 BusinessExpectation / EvaluationDimension 综合
AuthorityFinding
    ↓ Solidify 忠实投影
SolidifiedAuthorityAnchor

RunTrace
    ↓ 按原有语义形成
runtime BusinessExpectation[]
    + RuntimeExpectationBinding[]
    ↓ 对原有 requirements 做评价
FulfillmentAssessment[]
    ↓ 确定性 Authority Gate
JudgeResult
    ↓ 原有 blocking 聚合
overall_fulfillment
```

其中：

1. Investigate 回答项目级“哪些资料在什么条件下能够决定什么”；
2. Solidify 只冻结调查结论及其证据链；
3. Runtime 仍按原有方式形成当前 Case 的业务要求；
4. Binding 只回答“这条当前要求依赖哪个项目目标、评价维度和 Authority
   Finding”，不回答 fulfilled 与否；
5. Assessment 判断 actual 是否满足要求；
6. Gate 只在对应 Finding unresolved 时把该 assessment 约束为
   `not_evaluable`，并把具体原因、来源和待补证项写入 Judge summary；
7. 后续人类补充资料后，必须由显式的新一轮 Investigate 更新 Finding；Runtime
   不能自行把 unresolved 改成 resolved。

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
- 第一次综合得到 unresolved 时，不立即冻结 Report；使用
  `unresolved_reason + required_evidence` 驱动同一次 Investigate 内的定向
  补证；
- 新 EvidenceRef 进入 Material 调查后，使用相同 finding_id 重新综合；只有
  最后一次结果进入冻结 Report；
- 多个 unresolved Finding 的共同资料和 Tool 需求应合并调查，避免按 Finding
  重复调用模型；
- Report 和 investigation_snapshot_id 在补证循环结束后一次性冻结；工作集
  hash 变化不得自动启动新的外部 Investigation；
- 在完成 MaterialInvestigation 后，结合 JudgeInvestigationContract 中真实的
  BusinessExpectation / EvaluationDimension 归纳 Finding；禁止先有 Finding
  再挑资料；
- Finding 只表达 EvaluationDimension 判断所需的项目级有限 Authority 依赖；
  不按具体词语、字段或 badcase 建 Finding；
- Finding 通过 `dimension_ids` 连接 EvaluationDimension，并通过
  `EvaluationDimension.expectation_ids` 间接连接 BusinessExpectation，不重复
  保存 Expectation ID 或业务字段；
- Finding 当前使用 `basis_source_ref_ids` 关联资料；在实现前必须用多 Decision
  资料案例确定最小的 Decision 精确引用方式，禁止为此引入不稳定的 LLM 生成
  ID；
- Finding 使用 `resolution_reason` 解释资料如何支持或不足以支持结论；
- Finding 只通过真实 EvaluationDimension ID 连接 Judge，不再复制 stage ID；
- Finding ID 使用稳定项目键，不从自然语言文案生成；
- 按 `spec/alg/investigate-schemashow.md` 登记统一引用关系和最小展示字段；
- Authority Markdown 必须保留来源 Schema 原始 ID，并在
  `↳ [reference → ...]` 边界内展示关联 Schema 的关键实际值；
- MaterialInvestigation 的 Authority 审核视图固定展示
  `source_location + decisions`，不得只展示来源 ID 或路径；
- 保留 runtime `BusinessExpectation` 作为当前 Case 的唯一业务验收项，不新增
  `CaseEvaluationPoint` 作为平行业务对象；
- 删除 Draft 中 Point → runtime `BusinessExpectation` 的往返转换；
- 为每条参与 Draft Judge 的 runtime `BusinessExpectation` 生成一条
  `RuntimeExpectationBinding`，只保存 runtime expectation、项目级 expectation、
  evaluation dimension 和 AuthorityFinding 的 ID 关系；
- `RuntimeExpectationBinding` 不进入公共 `JudgeResult`，不复制
  `expected_outcome`、`acceptance_criteria`、`blocking` 或 actual；
- Binding 必须在对应 runtime expectation 冻结时确定，不能由 Assessment 根据
  actual 事后增加、删除或改写；
- Authority Gate 改为通过 `FulfillmentAssessment.expectation_id`
  → `RuntimeExpectationBinding` → `SolidifiedAuthorityAnchor` 串联；
- Authority unresolved 时，只改写对应既有 `FulfillmentAssessment` 的状态和
  原因，不新建 Point、不新建 runtime BusinessExpectation；
- 旧 runtime expectation 的粒度、blocking、acceptance criteria 和一对一
  Assessment 映射必须通过 badcase-003、badcase-008 等回归案例保持；
- 将旧 AuthorityAnalysis 改为相同 ID 的兼容投影；
- 删除没有真实调查证据的具体 Case Authority 声明。

### P0：Validator

- 校验 EvidenceRef、Material、Connection、Finding、Dimension 和 Tool 引用；
- 校验 Finding 的每个 Dimension 都能通过 expectation_ids 回到存在的
  BusinessExpectation；
- 拒绝与任何 EvaluationDimension 判断无关的 Finding；
- 拒绝 Finding 重复保存 BusinessExpectation ID 或业务字段；
- 拒绝 `decisions` 为空的 Authority Material；
- 拒绝用 `supporting/context_only` 等模糊等级代替唯一决定范围；
- 对重叠 Decision 要求互斥条件、场景区分、supersedes 或 unresolved；
- 拒绝缺少依据的 resolved；
- 拒绝缺少具体原因和 required_evidence 的 unresolved；
- 拒绝把工作中的候选 Finding 投影到 Solidify；
- 拒绝冻结同一 finding_id 的多个迭代结果；
- 当已登记 Connection 或可用 Tool receipt 路径仍表明存在当前范围内可取得的
  决定性证据时，拒绝提前冻结 unresolved；
- 拒绝缺少 statement、locator 或 resolution_reason 的对象；
- 拒绝缺少完整 source_location 的文件或非文件 Authority Evidence；
- 拒绝只存在 payload、没有 artifact LogicalPathRef 的非文件 Authority
  Evidence；
- 拒绝没有 EvidenceRef 的 derived_from/validated_by 声明；
- 拒绝把 ToolRequirement 当成已执行的验证结果；
- 拒绝 current_behavior 解除正式规则 Gate；
- 拒绝跨 project、snapshot 和 EvaluationDimension 引用；
- 拒绝把 QA 逐样本 reference 固化为项目级 Finding。
- 校验每条 runtime expectation 都有且只有一条
  `RuntimeExpectationBinding`；
- 校验 Binding 的 runtime expectation ID 在当前 Case 中存在且唯一；
- 校验 Binding 的 project expectation、evaluation dimension 和 finding ID 均来自
  当前固化目录；
- 校验 evaluation dimension 确实服务 Binding 所引用的项目级 expectation；
- 校验 Binding 引用的 Finding 覆盖其 evaluation dimension；
- Binding 缺失或非法时不得静默跳过 Authority，当前结果必须结构化失败或
  `not_evaluable` 并说明原因；
- 禁止通过 Point、metadata、boundary 或随机生成 ID 绕过 Binding。

### P0：Solidify 交付

- 将 Finding 投影为 SolidifiedAuthorityAnchor；
- 只接受来自已冻结 AuthorityInvestigationReport 的最终 Finding；
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
- 每个 Finding 都能通过 dimension_ids 回到 EvaluationDimension 和
  BusinessExpectation，并能通过资料引用回到 MaterialInvestigation；
- resolved 和 unresolved Finding 都能说明资料为什么足够或不足；
- Authority 人工视图保留原始 ID，并只在明确的 reference 展示边界中展开
  BusinessExpectation、EvaluationDimension 和 MaterialInvestigation 的实际
  字段；
- 来源、审批或动态验证声明都有 EvidenceRef，而不是 Harness AI 推测；
- current behavior 和正式规则可以得到不同状态；
- 第一次候选 unresolved 会在同一次 Investigate 内驱动定向补证，而不是立即
  进入 Solidify；
- 冻结的 unresolved 能说明已经跟进哪些决定性方向、为什么停止以及未来缺少
  什么证据；
- 同一业务依赖在补证迭代中保持 finding_id 稳定，冻结 Report 只保留最后一次
  结果；
- unresolved 原因、待补资料和来源可以完整保留到
  SolidifiedAuthorityAnchor；
- runtime `BusinessExpectation` 的原有 Case 级语义、粒度、blocking 和
  Assessment 一对一关系不因 Authority 接入而改变；
- 每条 runtime `BusinessExpectation` 都能通过唯一 Binding 回溯到调查侧
  `BusinessExpectation`、`EvaluationDimension` 和 `AuthorityFinding`；
- Authority Gate 只改写绑定了 unresolved Authority 的既有 Assessment；
- Authority 绑定遗漏不会被当作 `fulfilled` 静默放过；
- 人类补充信息后，通过新 EvidenceRef、报告和 snapshot 解除 unresolved；
- 人类补充或 hash 变化不会自动重新调查；只有用户明确要求的新 Investigate
  才重新打开已冻结 unresolved；
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
