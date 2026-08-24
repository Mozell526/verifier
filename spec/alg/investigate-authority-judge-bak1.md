# Investigate-Authority-Judge 调查协议

> 本协议是 **调查侧（输入侧）** 协议：定义 Judge 权威调查阶段如何以资料为轴心，
> 产出可供 Authority Agent 运行时复用或现场综合的调查产物。
>
> 运行时协议见 `spec/alg/authority.md`（`authority.resolve`、`AuthorityRequest` /
> `AuthorityResolution`、宿主无关 Ports、消费与 Gate 规则）。本协议不重复运行时内容，
> 只定义调查阶段怎么做、产物长什么样、如何与运行时交接。

---

# 第一章：调查方法论

## 1. 目标与位置

Judge 评估 Live 输出时，经常面对多份"官方项目材料"对同一业务判断点给出不同说法的
情况。调查阶段的目标不是建立一份静态的"权威优先级表"，而是回答：

> 基于当前已经调查的真实业务资料和上下游依赖，某个业务问题在当前条件下
> 是否有足够依据得到可靠结论？如果能，结论是什么、依据是什么；如果不能，
> 缺什么、冲突在哪、未来补充什么证据可以解除？

调查阶段通常没有具体 Runtime Case。它调查的是项目级、可复用的业务事实和规则，
例如：

- 客户搜索的业务词如何映射为正式查询条件；
- 多轮营销规划在什么条件下应结束澄清并进入执行；
- QA 的 gold/context 在什么 provenance 条件下可以作为判断依据。

具体 Case 只在 Runtime 判断是否依赖某项已经调查的结论，不进入调查报告。

本协议与 `spec/alg/authority.md` 的分工：

| | 调查侧（本协议） | 运行时（authority.md） |
|---|---|---|
| 时间 | Investigate 阶段，项目级 | 具体 Case 的 Judge 判断中 |
| 输入 | 真实业务资料 + 需求侧方向（可选） | `decision_question` + 绑定的 AuthorityEnvironment |
| 输出 | 调查报告（materials + findings） | `AuthorityResolution` |
| 职责 | 组织证据、确定每份资料能决定什么 | 针对具体问题综合出 resolved / unresolved |

## 2. 核心原则

### 2.1 权威不是标签，是因果分析的结论

不得给信息源贴静态优先级标签（如"Tier 1 > Tier 2"）替代因果分析。判断一份资料是否
有决定性，必须理解：

- **origin**：资料内容从哪里来；
- **producer**：谁/什么过程产生和维护它；
- **consumption path**：系统怎么加载和使用它；
- **failure modes**：它可能以什么方式出错。

追完因果链后，真正的标准往往自然浮现。资料之间的"覆盖、版本、消费链"关系必须落到
具体证据，而不是一句"这份资料优先级更高"。

### 2.2 唯一决定性：Authority 来自"资料在什么条件下唯一决定什么"

本协议最核心的概念是**唯一决定范围**：一份资料的 Authority 不来自它被贴上的标签，
而来自它在某个结论种类、场景和条件下，是某个业务事项的**唯一决定标准**。

```text
conclusion_kind（current_behavior / normative_rule / external_fact）
  + governs（决定哪个业务事项）
  + scenario（哪个项目级场景）
  + conditions（什么生效条件）
        ↓
一份资料在这个组合内唯一决定一个业务事项
```

由此得出：

- 每份进入报告的资料都必须能回答"它在什么条件下唯一决定什么"；找不到唯一决定范围
  的资料不进入报告的 `materials`（§8）；
- 资料之间是**分工关系，不是权威等级关系**：环境配置唯一决定"选哪个文件"、字段定义
  唯一决定"文件里写了什么"、注册表唯一决定"如何加载"，各司其职（§20）；
- 判断两份资料是否冲突，先看它们是否在相同的 `conclusion_kind + governs + scenario +
  conditions` 组合内重叠；不重叠不是冲突（§9）；
- 任何"决定性"都必须能回到具体资料的 `statement` 与 `locator`，不能只写"这份资料
  负责此事"。

### 2.3 资料轴心，不预设观点

调查以**资料**为主轴，不以判断观点、Case 或 badcase 为主轴：

- 报告的第一组织维度是 `materials`，每份资料说明它"能决定什么/不能决定什么/与谁
  冲突"；
- 禁止先生成结论、再围绕结论挑选资料；
- 只有相关性、找不到任何唯一决定范围的资料不进入报告的 `materials`；
- 与 Judge 判断无关的资料冲突不生成 Finding。

### 2.4 Schema 驱动调查，而非记录结论

Schema 的必填字段反向推动调查者完成因果分析。不能声明"X 是权威"就过关，必须给出
资料定位、决定范围、连接关系和理由。Validator 检查结构完整性与引用有效性，使跳过
分析或含糊其辞无法通过门禁。

## 3. 三种互补的确认方式

| 方式 | 适用场景 | 产出 |
|------|---------|------|
| 因果链追溯 | 能理解系统链路和数据流向时 | 从因果分析中自然得出哪个源反映了真实 |
| 事实验证 | 能通过实验/查询获得客观结果时 | 保存可复现的实验结果作为证据 |
| 业务方澄清 | 因果链追不到头、事实无法获取时 | 明确的澄清问题，等待业务方确认 |

三者递进：优先追因果链，用事实验证结论，追不到时标记 unresolved 并给出需要业务方
澄清的具体问题。事实验证（数据库查询、API 调用、确定性 Tool 执行）的结果必须先固化
为可寻址 artifact 再引用（见 §7.2）。

## 4. 需求侧输入的定位（轻量依赖）

调查方向可以由需求侧提供，但调查产物不绑定需求侧：

- `JudgeInvestigationContract` 的 `EvaluationDimension` 可以指出"哪些评价维度依赖哪些
  业务事实"，作为候选 Finding 归纳的方向输入；
- 调查报告仍以资料为轴心组织，`dimension_ids` 只作为说明性标签（帮助聚焦与人工审核
  定位），**不改变调查与运行逻辑**（`authority.md` §14.3）；
- 没有需求侧输入时，调查也可以退化为纯资料侧的 capability 调查（每份资料能决定
  什么），Runtime 的 `decision_question` 再去命中。

需求侧方向的职责边界：

- 需求侧可以回答"这次调查应该覆盖哪些业务事项"；
- 需求侧不能预设 resolved/unresolved，不能用来排除与业务范围有关的资料。

## 5. 防 AI Hack 设计

- 不允许仅凭文本声明建立权威；每个决定性说法必须有 EvidenceRef 与 locator 可核验；
- 不允许只列一个源就下结论；冲突判断点必须列出所有相关源并逐一分析；
- 不允许把"配置 A 比配置 B 优先级高"作为论证；必须解释 A 的内容为什么在当前条件下
  具有决定性；
- 不允许虚构 origin、producer 或验证结果；无法证明时写入 limitations 并保持
  unresolved；
- 不允许用 current_behavior 代替 normative_rule 或 external_fact（§11.4）。

---

# 第二章：资料轴心调查协议

## 6. 四步主链

```text
EvidenceRef：已登记的真实业务资料
        ↓ Authority Investigation
AuthorityInvestigationReport：逐份资料调查 + 关系分析 + Finding 综合
        ↓ 冻结
最终 Report（materials + findings，唯一真相源）
        ↓ Solidify / 物化
① 已验证 (question, resolution, basis) 配对 → 固化为 ContextUnit（Runtime 命中即复用）
② 调查报告物化的原始资料 → 进入 EvidenceSpace（未命中配对时现场综合）
```

| 阶段 | 负责什么 | 不负责什么 |
|---|---|---|
| EvidenceRef 登记 | 资料位置、版本、hash；非文件资料先固化 artifact | 不解释资料内容 |
| Authority Investigation | 逐份调查资料、分析连接、综合 Finding | 不以预设观点筛选资料 |
| 报告冻结 | 一次性冻结 materials + findings | 不把工作状态当作最终结果 |
| Solidify / 物化 | 固化复用配对 + 物化原始资料 | 不重新调查、不重新解释结论 |

`AuthorityInvestigationReport` 是调查阶段的结构化交付，不是独立运行阶段；报告内部的
资料记录、连接与 Finding 不直接作为运行时对象（`authority.md` §14.2）。

## 7. EvidenceRef 登记与非文件资料固化

### 7.1 登记职责

`EvidenceRef` 只回答：

```text
资料是什么？
资料在哪里？
资料对应哪个 revision/hash？
```

它不回答"资料表达了什么业务规则""资料是不是最终权威""资料与谁冲突"。业务语义从
`MaterialInvestigation` 开始。`EvidenceRef` 不能只停留在 Manifest 总览：Report 中每一
份 `MaterialInvestigation` 都必须同时写出 `source_ref_id` 与可直接识别资料的
`source_location`，`source_location` 由 Core 从 EvidenceRef 复制和校验，不能由 Harness
AI 自由填写。

### 7.2 非文件资料必须先固化为 artifact

进入 Authority Report 的证据必须具有完整 `location_ref`。该要求不仅适用于源码和文档，
也适用于 API observation、Tool receipt、数据库查询与人工澄清：

```text
文件、文档、代码
  → business://、project:// 等原始 LogicalPathRef

API observation / Tool receipt / 数据库查询 / 人工澄清
  → 先确定性保存为不可变 JSON/Markdown artifact
  → artifact://evidence/<ref_id>.<ext>
  → EvidenceRef.location_ref
  → MaterialInvestigation.source_location
```

非文件资料不得只保存在 `EvidenceRef.payload` 或自由 metadata 中进入 Report。Core 必须
先将规范化内容、采集时间、采集方式、适用环境以及能取得的 revision/hash 固化为
artifact，再复制完整 LogicalPathRef，保证外部观察与人工补充可审计、可复现。这与运行时
Materializer 物化通道同构（`authority.md` §4.2）：调查侧先固化 artifact，运行时再物化
为 ContextUnit。

## 8. MaterialInvestigation：一份资料的完整调查记录

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

核心不变量：**`decisions` 不得为空**。进入 Authority Report 的资料不再分为
"决定性、辅助性、背景性"等权威等级；每份资料都必须明确：它在哪个结论种类、场景和
条件下，是哪个业务事项的**唯一决定标准**。

#### 8.1 直接决定与仅相关的二元对立

整体设计把资料对业务事项的关系切成两类，**没有中间等级**：

```text
decisions（governs）：直接决定，有强制性
    这份资料在这个结论种类、场景和条件下，直接决定某个业务事项是什么。
    命中该组合时，答案由它决定，不能绕过去说"我觉得另一个更合理"。

related_to：仅相关，不决定
    这份资料与某些业务事项相关，但明确"不由该资料决定"。
```

- `governs` 描述的是这份资料**直接决定的一些东西**（一份资料可以有多个
  MaterialDecision，各自直接决定不同的事项）；
- 强制性是**范围化**的：在这个 `conclusion_kind + scenario + conditions` 组合内它
  直接决定，换一个场景可能由另一份资料直接决定，不存在全局最高；
- 这正是禁止 `supporting`、`context_only` 等模糊等级的原因——要么直接决定，要么仅
  相关，没有"辅助性/背景性"中间态；
- **材料层自足**：`decisions` 是资料本身的能力声明，不依赖需求侧、不依赖 Finding
  是否存在；`AuthorityFinding` 依赖材料层（某个需求依赖命中 governs 时才形成），
  而不是反过来。只有完成调查并找到至少一个唯一决定范围的
资料才生成 `MaterialInvestigation` 并进入 Report 的 `materials`；只有相关性、无法读取
或找不到唯一决定范围的资料继续保留在普通 Investigation Evidence/overview 中，不得
伪装成 Authority Material。尚未取得、因而没有 EvidenceRef 的资料只能作为 unresolved
Finding 的 `required_evidence`。

文件引用固化链：

```text
InvestigationManifest.evidence_refs[n]
        ├── ref_id ────────→ MaterialInvestigation.source_ref_id
        └── location_ref ──→ MaterialInvestigation.source_location
```

Core 负责复制和一致性校验，Harness AI 不得自行拼写路径。报告不复制完整文件内容；
大型资料按 `spec/alg/investigate-keyindex.md` 建立索引并按需读取。

## 9. MaterialDecision：资料的唯一决定范围

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

**"唯一"只在以下组合内成立：**

```text
conclusion_kind + governs + scenario + conditions
```

`governs`、`statement` 与 `locator` 三者不得混淆：

```text
governs   这份资料决定的业务事项是什么（决定范围）
statement 这份资料对该事项具体说了什么（说法）
locator   人类到资料的哪个位置核验这句话（定位）
```

没有具体 `statement + locator`，不得仅凭"这份资料负责某事"形成 MaterialDecision。
大资料的 locator 可以使用 `spec/alg/investigate-keyindex.md` 定义的 key。

它不是宣称某份资料在整个项目中永远最高。决定相同业务事项的资料可以分别适用于不同
业务场景、产品或渠道、部署环境、生效时间或版本，或是一般规则与明确例外。如果两份
资料的决定范围不重叠，它们不是冲突；如果重叠，则必须存在明确的条件区分、场景区分
或 `MaterialConnection(relation="supersedes")`，否则对应 Finding 必须 unresolved。

## 10. MaterialConnection：资料之间的实质连接

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

`direction` 以当前 MaterialInvestigation 为中心。`effect` 不得只写"相关"或"被使用"，
必须说清传递或约束的内容以及结果。

Relation 的业务含义：

- `dependency`：一份资料如何选择、消费或约束另一份资料；
- `derived_from`：当前资料内容从哪个有证据的真实来源或生产过程产生；
- `validated_by`：当前资料的说法被哪个实际实验、查询或 Tool receipt 验证；
- `supersedes`：明确的版本、生效或审批关系使一份资料覆盖另一份资料；
- `conflicts_with`：两份资料在重叠的决定范围内给出不能同时成立的 statement。

`derived_from` 和 `validated_by` 都必须指向真实 EvidenceRef；无法证明 origin、producer
或验证结果时，不得根据文件名或模型常识补造 Connection，应写入 `limitations`，必要时
形成 unresolved Finding。Connection 必须携带完整 `source_location`；对非文件证据，该
路径指向先行固化的 `artifact://` 资产。不记录完整函数调用图，不生成
relation_id/evidence_id。

## 11. AuthorityFinding：调查综合对象

`AuthorityFinding` 是需求侧方向与资料调查结果之间的**调查侧综合对象**。它回答：

> 该业务依赖根据当前资料是否已经可以确定结论。

它**不是运行时对象**（`authority.md` §14.2）：运行时不再直接消费 Finding，而是通过
`decision_question` 触发 `authority.resolve`；调查侧 Finding 只作为"已解决的复用候选"
（§16-17）与人工审核的依据。

#### 11.0 交叉定位：需求侧依赖 × 资料侧能力

`AuthorityFinding` 不是自由生成的观点，也不是一份资料的摘要。它是需求侧（评价维度
提出的 Authority 依赖）与资料侧（材料层直接决定的能力）之间**唯一的综合对象**：

```text
需求侧
  BusinessExpectation      回答：为什么需要这项产品能力
      ↓
  EvaluationDimension      回答：Judge 对这项能力具体判断什么
      ↓ 提出有限的 Authority 依赖
AuthorityFinding ◀─────── MaterialInvestigation[]
  回答：该依赖根据当前资料能否被定夺      回答：每份资料在什么条件下唯一决定什么
      ↓
Solidify 只固化已验证的 (decision_question, resolution, basis) 配对（§17）
```

三侧信息的职责必须保持分离：

```text
BusinessExpectation        回答：为什么需要这项产品能力
EvaluationDimension        回答：Judge 对这项能力具体判断什么
MaterialInvestigation      回答：每份资料在什么场景和条件下决定什么、具体怎么说
AuthorityFinding           回答：该判断所依赖的业务事实，根据这些资料能否被定夺
```

由此得出两条约束：

- Finding 不直接保存 `BusinessExpectation.expectation_id`。关联链固定为
  `dimension_ids → EvaluationDimension.dimension_id → expectation_ids →
  BusinessExpectation.expectation_id`，避免 Finding 复制一套产品期望关联，也避免
  Dimension 与 Finding 中的 Expectation 关系漂移；
- Finding 依赖材料层，材料层不依赖 Finding：先有"资料能直接决定什么"，才谈得上
  "某个需求依赖是否被定夺"。普通当前行为事实继续保留为 MaterialDecision；只有它
  确实被某个评价维度作为判断依赖时，才进一步形成 Finding（§11.1）。

```python
@dataclass(frozen=True)
class AuthorityFinding:
    finding_id: str

    finding_kind: Literal[
        "current_behavior",
        "normative_rule",
        "external_fact",
    ]

    # 项目级可复用的业务问题；运行时匹配时对应 decision_question。
    business_question: str

    # 只作说明性标签（服务哪些评价维度），不改变运行逻辑（§14.3）。
    # 关联链：finding.dimension_ids → EvaluationDimension.dimension_id
    #        → EvaluationDimension.expectation_ids → BusinessExpectation.expectation_id
    dimension_ids: tuple[str, ...] = ()

    # 资料侧：本次调查中支持、冲突或不足以支持本 Finding 的资料。
    basis_source_ref_ids: tuple[str, ...]

    status: Literal["resolved", "unresolved"]

    # resolved 时必填。
    result: str | None

    # 为什么 basis materials 足以或不足以支持本 Finding。
    resolution_reason: str

    # unresolved 时必填。
    unresolved_reason: str | None
    required_evidence: tuple[str, ...]

    # 引用 InvestigationManifest.tool_requirements。
    tool_requirement_ids: tuple[str, ...] = ()
```

### 11.1 生成条件

只有满足以下条件才生成 Finding：

1. 至少一个评价维度（或调查方向）确实依赖项目资料提供业务标准或外部事实；
2. 当前 Case 的 request/actual 直接比较、已有确定性 Comparator 或封闭规则不能独立
   完成判断；
3. 调查已经完成相关资料的 MaterialDecision、Connection 和限制分析；
4. Finding 问题是项目级可复用的有限依赖，不是某个词、字段或 badcase 的临时问答。

普通当前行为事实继续保留为 MaterialDecision；只有它确实被某个评价维度作为判断依赖
时，才进一步形成 `finding_kind="current_behavior"` 的 Finding。

### 11.2 finding_id 稳定性

`finding_id` 是项目内稳定关联键，不从 `business_question` 的自然语言 slug 推导。
修改措辞、翻译语言或调整标点不得改变 ID；只有业务问题本身被拆分、合并或替换时才
创建新 ID。同一轮补证循环内，问题没有拆分/合并/替换时必须保留原 `finding_id`，只
更新资料依据、状态和结论。

### 11.3 三种 Finding 的业务区别

| kind | 回答的问题 | 能否解除正式规则 Gate |
|---|---|---|
| `current_behavior` | 当前系统现在如何做 | 不能 |
| `normative_rule` | 业务、产品、监管或契约要求应该如何做 | 可以 |
| `external_fact` | 外部系统或现实当前实际是什么 | 可以 |

最重要的不变量：

> `current_behavior=resolved` 只能解释系统现状，永远不能代替 `normative_rule` 或
> `external_fact`。

### 11.4 Finding 不比较资料优先级

Finding 只检查当前业务问题是否命中某个 MaterialDecision：

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

`resolution_reason` 补足"资料引用"和"结论"之间的业务解释：`basis_source_ref_ids`
回答依据了哪些资料，`resolution_reason` 回答这些资料的具体说法、上下游关系或验证
结果为什么足以支持 result，或为什么仍不足以得出结论。不得写成"因为该资料优先级更
高"。其中出现"来自生产系统""经过正式审批""已由 API/数据库验证"等事实时，必须能回指
对应 `derived_from / validated_by` Connection 和 EvidenceRef。

## 12. AuthorityInvestigationReport：调查阶段的交付

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

Report 是本次调查的唯一真相源，必须在补证循环结束后一次性冻结。报告的第一组织维度
必须是 `materials`：Markdown 在每份资料下直接展示 decisions、related_to 和
connections，最后再展示 Finding；不得按 Finding 分章节后反向罗列资料。

进入 Report 的资料不再分为"决定性、辅助性、背景性"等权威等级。每份资料都必须明确：
它在哪个结论种类、场景和条件下，是哪个业务事项的唯一决定标准。

## 13. unresolved 驱动的补证循环

Authority Investigation 按以下内部步骤执行，顺序不得颠倒：

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

4. 候选 Finding 归纳
   输入：需求侧方向（可选）与已完成的 MaterialInvestigation[]
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

特别禁止先生成 Finding、再围绕 Finding 挑选资料。需求侧方向只限定最终需要服务的业务
判断范围，不得被用来预设答案或排除与业务范围有关的资料。Finding 必须在逐份资料调查
和连接分析完成后综合形成。

阶段内部的职责分工：

| 内部步骤 | Harness AI | 确定性代码 | 完成标准 |
|---|---|---|---|
| 资料登记 | 发现与业务范围有关的真实资料 | 固化 EvidenceRef、revision 和 hash | 本次资料范围可枚举、可复现 |
| 逐份资料调查 | 定义每份资料直接决定的唯一范围 | 校验 decisions 非空且定位有效 | 每份资料至少直接决定一个业务事项 |
| 资料连接分析 | 说明上游、下游和同级资料的实质业务连接 | 校验资料路径和方向 | 每条连接都说明对方做什么和如何影响当前资料 |
| 候选 Finding 归纳 | 按业务事项、场景和条件匹配 Decision；用 unresolved_reason / required_evidence 提出下一轮补证方向 | 校验重叠范围已区分或候选 Finding 已标记 unresolved | 每个候选结果及冲突原因都能回溯 |
| 定向补证 | 沿具体缺口寻找来源、审批、生效、替代或验证资料 | 登记新 EvidenceRef、固化工具结果并拒绝虚构来源 | 新资料进入 Material 调查，或确认当前无法取得 |
| Report 冻结 | 确认所有 Finding 已 resolved 或满足停止条件 | 每个 finding_id 只接受最后一次结果并冻结最终 snapshot | 工作中的 provisional unresolved 不会进入下游 |

Harness AI 负责调查和业务解释；代码负责覆盖、引用和边界校验。代码不得替 Harness AI
生成业务结论，Harness AI 也不得绕过确定性校验。

第一次得到 `status="unresolved"` 不是立即交付的信号，而是同一次已授权调查内继续补证
的起始点。补证循环只允许在以下条件之一成立时停止：

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
- 不能只写"存在冲突""资料不足"或"建议人工确认"。

概念算法（表达职责，不要求按 Finding 单独调用模型）：

```python
materials = investigate_initial_materials()

while True:
    candidate_findings = synthesize_findings(
        direction=direction,   # 需求侧方向，可空
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

Harness 应优先批量合并共同补证方向（相同资料、相同 Tool 或相同责任方），避免为每个
Finding 分别调用 LLM 或重复读取资料；Core 只负责 EvidenceRef、Material、引用、唯一性
和冻结边界，不得替 Harness 判断业务资料是否足以定夺。

补证循环中新增资料属于同一次用户明确要求的调查，不得因为工作集 hash 变化自动启动新
的外部调查。人类在 Report 冻结后补充资料时，系统只负责登记新的 EvidenceRef；只有用户
再次明确要求调查，才以原 Finding 的 `finding_id + unresolved_reason + required_evidence`
和新增 EvidenceRef 为起点重新调查，不得由文件或 hash 变化自动重新调查或重新固化
（`authority.md` §6）。

## 14. Validator

Validator 只能检查引用、边界和禁止项，不能代替业务语义审查。"是否还存在值得跟进的
新业务资料"主要由 Harness AI 负责；Core 只能对已经登记的 EvidenceRef、Connection、
Tool receipt、required_evidence 和冻结状态做确定性一致性检查。

结构校验：

- `materials` 非空，每份资料 `decisions` 非空且定位有效；
- 每条 `source_ref_id` 都能回到 `InvestigationManifest.evidence_refs`，且
  `source_location` 等于该 EvidenceRef 的 `location_ref`；
- Core 必须按 `source_location.revision + sha256` 校验实际读取的资料；
- Decision 的 `governs`、`statement` 和 `locator` 必须非空；
- `connections` 的引用、方向与 relation 合法：Connection 的 `source_ref_id` 必须存在
  于 Manifest，`source_location` 必须与对应 EvidenceRef 一致，`effect` 不得为空或只写
  "相关""被使用"；
- `derived_from` / `validated_by` 必须指向真实 EvidenceRef（Tool receipt 等）；
- `AuthorityFinding.dimension_ids` 必须能通过 `EvaluationDimension.expectation_ids`
  回到至少一个存在的 `BusinessExpectation`（有需求侧输入时）；
- Finding ID 项目内稳定且唯一，不得从 `business_question` 文案临时生成；
- resolved 必须有 `result` 和 `resolution_reason`，不得有 `unresolved_reason`；
- unresolved 必须有 `unresolved_reason`、`required_evidence` 和 `resolution_reason`
  （说明现有资料为什么不足）；
- 冻结 Report 中每个 `finding_id` 只能存在最后一次 Finding；工作状态不得进入冻结
  Report。

业务边界校验：

- 每份资料必须至少直接决定一个明确业务事项；Decision 的 scenario 和 conditions 必须
  是项目级范围，不得包含单个 badcase；
- Finding 的 kind 必须与适用 Decision 一致；
- Finding 必须对应至少一个评价维度确实需要的有限 Authority 依赖；与 Judge 判断无关
  的资料事实或冲突不得生成 Finding；
- Finding 只通过 `dimension_ids` 关联评价范围，不得为资料内部步骤虚构
  EvaluationDimension；不得重复保存 `BusinessExpectation` 的 ID 或业务字段；
- `current_behavior=resolved` 必须命中 current_behavior Decision，`normative_rule` 与
  `external_fact` 同理；不得用其他 conclusion_kind 的 Decision 替代缺失 Decision；
- 相同决定范围只允许一个当前生效 Decision；重叠 Decision 只有存在互斥条件、场景区分
  或 `peer connection.relation="supersedes"` 时才能 resolved；无适用 Decision 或重叠
  无法消解时必须 unresolved；
- 现有 MaterialConnection、ToolRequirement 或 required_evidence 仍明确指向当前授权
  范围内可取得的新证据时，不得把候选 unresolved 提前冻结；
- 最终 unresolved 的 `resolution_reason` 必须说明已跟进的决定性补证方向和停止原因，
  不能只复述 `unresolved_reason`；
- 禁止 `supporting`、`context_only` 等模糊权威等级；`related_to` 不能单独解除 Gate；
- 只写"资料有歧义"但没有具体资料和 Connection，校验失败；
- `resolution_reason` 只能引用 `basis_source_ref_ids` 对应资料已有的 Decision、
  Connection 和确定性验证结果；
- 声称资料"派生自生产系统""经过正式审批"时，必须有 `relation="derived_from"` 的
  Connection 和 EvidenceRef；
- 声称结论已经由数据库、API 或其他工具验证时，必须有 `relation="validated_by"` 的
  Connection，并指向实际 Tool receipt EvidenceRef；只有 ToolRequirement 不代表已经
  验证；
- 报告不得包含 current Case actual、Comparator、score、confidence 或 verdict；
- 不得为单个 badcase 新增专属 Finding 或 relation kind。

## 15. 产物位置

```text
impl/projects/<project>/draft/investigation/judge/
  manifest.json
  overview.md
  docs/
    judge-investigation-contract.json      # 可选（需求侧方向）
    authority-investigation-report.json    # 结构化真相源
    authority-investigation-report.md      # 由 JSON 确定性渲染，供人工审核
```

规则：

- JSON 是结构化真相源，Markdown 由 JSON 确定性渲染；
- 两者使用固定逻辑路径和 purpose 登记到 `InvestigationManifest.artifact_refs`
  （`judge_authority_investigation_report_json` / `_markdown`）；
- Judge contract 不复制完整报告；完整报告不得无条件注入 Runtime Prompt。

---

# 第三章：与 Authority 运行时的交接

## 16. 双层复用

运行时消费调查产物采用双层策略（`authority.md` §6、§22-10）：

```text
第一层：已固化配对直接复用
    Solidify 把已验证的 (decision_question, resolution, basis) 固化为 ContextUnit；
    Runtime 在完整 decision_question + Environment snapshot + Evidence revision
    仍匹配时直接复用该结论，不再调用 Authority Agent。

第二层：现场综合
    未命中已固化配对时，调查报告物化后的原始资料已进入 EvidenceSpace；
    Authority Agent 按 authority.md §5 的判断顺序现场综合，输出 AuthorityResolution。
```

双层的关系：

- 第一层是优化：避免重复计算稳定结论，但只适用于"问题、环境、证据"三者完全匹配的
  场景；匹配不完整必须落到第二层，不能降级匹配；
- 第二层是兜底：任何 `decision_question` 都可以现场综合，但证据不足时只能返回
  unresolved；
- 调查报告本身是导航摘要，不是可引用证据；只有物化后的原始资料可进入
  `basis_evidence_ref_ids`（`authority.md` §13.3）。

## 17. Finding 到复用配对的映射

调查侧 Finding 是"已解决的复用候选"。Solidify 把冻结 Report 中 `status="resolved"` 的
Finding 投影为运行时配对；`status="unresolved"` 的 Finding 不生成配对，只作为资料空间
的背景与人工审核依据。

```text
AuthorityFinding.business_question  → AuthorityRequest.decision_question
AuthorityFinding.result             → AuthorityResolution.statement
AuthorityFinding.resolution_reason  → AuthorityResolution.reason
AuthorityFinding.basis_source_ref_ids → AuthorityResolution.basis_evidence_ref_ids
AuthorityFinding.unresolved_reason  → AuthorityResolution.reason（unresolved 场景）
AuthorityFinding.required_evidence  → AuthorityResolution.required_evidence
```

固化配对时的约束：

- `decision_question` 必须自包含业务条件（版本、渠道、场景等），不依赖运行时额外
  补充适用范围字段；
- `basis_evidence_ref_ids` 引用**物化后的 ContextUnit unit_id**（`authority.md` §13.3）；
  来源别名（`ref_id`）保留在 tags 中，不直接作为运行时引用；
- 配对的 Environment snapshot（权限、资料 revision、工具指纹）必须随配对保存；Runtime
  复用前必须校验 snapshot 与 revision 仍匹配；
- 同一 Finding 固化后，资料 hash 或 revision 变化只使旧配对不再可直接复用，不得自动
  启动重新调查或重新固化（`authority.md` §6）。

`status="unresolved"` 的 Finding 仍有两个用途：作为 `required_evidence` 的待补清单，
以及在未命中配对时提示 Runtime 该问题已知证据不足、需要先补证而非重复综合。

## 18. 调查报告的物化

调查产物进入运行时可发现空间遵循 `authority.md` §13.3 的物化规则：

- manifest 中的 evidence_refs 物化为 `ContextUnitRecord`：`content_ref` 指向原文件，
  `ref_id` 存 tags 作来源别名，`unit_id` 由代码生成；
- 一个 EvidenceRef 物化后对应一个 ContextUnit，不允许多对一或指向 ToolCall receipt；
- 已有 EvidenceRef 找不到原始来源 → Environment 构造失败（fail-closed），不进业务层；
- 调查报告的 overview、报告本身是导航摘要，不进入 `basis_evidence_ref_ids`；
- Tool 动态执行结果在运行时物化为 case-scoped ContextUnit，静态资料物化为
  project_static ContextUnit（`authority.md` §4.2 Materializer）。

## 19. 变更与重查边界

- 只有用户显式发起的新一轮调查，才以原 unresolved Finding 的
  `finding_id + unresolved_reason + required_evidence` 与新增 EvidenceRef 为起点重新
  调查；
- 文件或 hash 变化不得自动重新调查或重新固化；
- 人类补充资料后，系统只登记新 EvidenceRef；结论更新必须经过新一轮调查；
- 同一轮调查内，补充资料后不得创建表示同一业务依赖的新 Finding ID。

---

# 第四章：案例

## 20. client_search 字段知识链（资料轴心）

业务链：

```text
dev_client_search_args.yaml
  唯一决定 dev 场景选择哪份字段定义文件
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

这四份资料各自"唯一决定"一个不同的业务事项，形成**分工而不是等级**：

| 资料 | governs（唯一决定什么） | conclusion_kind |
|---|---|---|
| dev_client_search_args.yaml | dev 场景选择哪一份字段定义文件 | current_behavior |
| field_definitions_args.yaml | 当前选中配置中写了哪些字段知识 | current_behavior |
| FieldRegistry | 字段配置如何成为运行时检索知识 | current_behavior |
| QueryRouter | 最终条件如何执行字段合法性校验 | current_behavior |

逐份展开：

### 资料一：dev 运行环境配置

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
        "它唯一决定当前配置里写了什么，不决定正式业务规范，"
        "也不决定下游契约实际接受什么。",
    ),
)
```

### 资料三：FieldRegistry

```python
MaterialInvestigation(
    source_ref_id="client-search-field-registry",
    source_location="business://src/main/python/steps/field_registry.py",
    decisions=(
        MaterialDecision(
            conclusion_kind="current_behavior",
            governs="字段配置如何成为运行时检索知识",
            statement=(
                "FieldRegistry 加载字段定义，并提供字段知识检索与输入归一化"
            ),
            locator="FieldRegistry.__init__",
            scenario="Parser 运行时初始化并检索字段知识",
            conditions=("当前部署执行该 FieldRegistry revision",),
        ),
    ),
    related_to=("字段配置的具体内容由字段定义资料决定。",),
    connections=(
        MaterialConnection(
            direction="upstream",
            source_ref_id="client-search-field-definitions",
            source_location=(
                "business://src/main/python/config/field_definitions_args.yaml"
            ),
            locator="FieldRegistry._load_yaml",
            relation="dependency",
            effect="读取 intents，建立运行时字段检索知识。",
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

```python
MaterialInvestigation(
    source_ref_id="client-search-query-router",
    source_location="business://src/main/python/steps/query_router.py",
    decisions=(
        MaterialDecision(
            conclusion_kind="current_behavior",
            governs="最终结构化条件如何执行字段合法性校验",
            statement="QueryRouter 使用加载后的字段集合校验最终结构化条件",
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

这个案例表达资料分工，不是权威等级：

```text
环境配置唯一决定"选哪个文件"；
字段定义唯一决定"选中文件里写了什么"；
FieldRegistry 唯一决定"如何加载和检索"；
QueryRouter 唯一决定"如何执行最终字段校验"。
```

如果需要判断"正式业务应该有哪些字段"或"下游实际接受哪些字段"，当前四份资料没有任何
一个 MaterialDecision 覆盖该问题。此时不是把它们降级为 supporting，而是直接生成
unresolved Finding，并要求补充正式规范或 provider-owned 契约：

```python
AuthorityFinding(
    finding_id="client-search-normative-field-contract",
    finding_kind="normative_rule",
    business_question="下游正式接口允许哪些字段？",
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

这个差异保证"当前代码确实这样做"不会被偷换成"正式业务就应该这样做"。

## 21. 客户分层定义冲突（决定性论证）

两份资料在同一决定范围内给出不同说法：

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
    unresolved_reason="无法确认产品分层规范和销售运营手册中哪一份当前生效。",
    required_evidence=(
        "当前生效版本、审批记录、替代关系或适用场景说明",
    ),
)
```

该 Finding 冻结后：不生成复用配对（unresolved）；物化后的两份资料进入 EvidenceSpace。
Runtime 收到 `decision_question`（"高净值客户应采用哪一种正式定义？"）时未命中配对，
Agent 现场综合后返回 unresolved，并携带 `basis_evidence_ref_ids`（两份资料的物化
unit_id）与 `required_evidence`。Judge 侧按 `authority.md` §8 消费：相关 assessment 写
`authority_tool_call_ids`，Core 把 unresolved 且 blocking 的评价转为 `not_evaluable`；
与它无关的业务条件不受阻断。

#### 21.1 同一 Finding 的补证迭代

上述 Finding 第一次综合为工作中的 unresolved 后，其 `required_evidence` 指向"生效
版本、审批记录、替代关系或适用场景说明"。Harness 不立即冻结 Report，而是继续调查
这些方向。如果随后取得：

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

则重新使用**同一 `finding_id`** 综合：

```python
AuthorityFinding(
    finding_id="customer-segmentation-definition",
    finding_kind="normative_rule",
    business_question=(
        "客户搜索产品解释客户分层术语时，"
        "应采用哪套当前生效的正式定义？"
    ),
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

如果审批、版本或场景资料均无法取得，则保留同一 Finding 的最终 unresolved，并在
`resolution_reason` 中记录已经跟进但仍无法取得的决定性方向。无论最终状态如何，冻结
Report 中都只保留最后一次结果；中间工作结果不进入 Solidify 与运行时。

---

# 第五章：泛化验证

## 22. 跨项目不变量

Schema 不假设业务一定存在：字段或枚举、Parser、数据库、唯一标准答案、内部代码、
下游搜索结果。跨项目稳定抽象只有：

```text
有版本的真实资料
  ↓
资料在某个结论种类、场景和条件下唯一决定一个业务事项
  ↓
资料之间的选择、消费、约束、覆盖或冲突关系
  ↓
resolved / unresolved Finding
```

## 23. QA / DeerFlow / Marketing Planning

**QA**：当前 Judge boundary 政策可以唯一决定"当前系统在什么场景使用 gold"，形成
current_behavior Decision；只有正式 provenance policy 才能唯一决定"什么条件下 gold
可以作为业务标准"，缺失时对应 normative Finding unresolved。具体 Case 的 question、
actual、gold、context 不进入静态报告。

**DeerFlow**：当前 clarification policy 可以唯一决定"当前流程在什么条件下继续澄清"，
形成 current_behavior Decision；只有领域充分性规范才能唯一决定"业务上何时信息已经
足够"，缺少该资料、部署 revision 或 skill receipt 时，对应 normative Finding
unresolved。

**Marketing Planning**：当前代码枚举可以唯一决定"当前实现允许哪些意图标签"，形成
current_behavior Decision；只有受治理的正式意图分类资料才能唯一决定"对外产品允许
哪些意图"，缺少审批、生效版本和覆盖关系时，对应 normative Finding unresolved。
API/Tool 调查结果必须先固化 artifact 再进入 Report。

三个项目均不需要 client_search 专属概念。

---

# 第六章：改造边界与实施顺序

## 24. 改造边界

只允许修改：

```text
impl/projects/<project>/draft/**
impl/projects/<project>/draft/investigation/**
Draft 测试
```

不得修改 Production 和公共协议实现（`authority.md` §20、§23）。

## 25. 实施顺序

1. 产出 Report JSON 与确定性 Markdown 渲染，登记 artifact_refs；
2. 将 manifest evidence_refs 物化为 ContextUnit，未物化资料不进业务层（fail-closed）；
3. 对真实业务资料逐份完成 MaterialInvestigation（decisions 非空、locator 可核验）；
4. 建立 MaterialConnection（dependency/derived_from/validated_by/supersedes/
   conflicts_with），非文件证据先固化 artifact；
5. 按需求侧方向（可选）综合 AuthorityFinding，实现 unresolved 驱动的补证循环与报告
   冻结；
6. Solidify 将 resolved Finding 投影为 (decision_question, resolution, basis) 配对并
   固化 ContextUnit（V1 后启用复用）；
7. 与 `authority.md` §22 的运行时改造联调：resolve 入口、物化通道、assessment 写
   `authority_tool_call_ids`、Core 后处理。

## 26. 验收要求

- 调查阶段不依赖具体 Case；报告以真实业务资料为轴心；
- 文件和非文件资料都具有完整 LogicalPathRef；每个决定性说法都能通过 locator 回到
  真实资料；
- current_behavior 与 normative_rule 可以得到不同状态；
- 第一次候选 unresolved 会在同一次调查内驱动定向补证，而不是立即冻结；
- 冻结的 unresolved 能说明已跟进哪些决定性方向、为什么停止、未来缺什么证据；
- 同一业务依赖在补证迭代中保持 finding_id 稳定，冻结 Report 只保留最后一次结果；
- resolved Finding 生成的复用配对满足"完整 decision_question + snapshot + revision
  匹配"才可复用，匹配不完整必须现场综合；
- 资料 hash 或 revision 变化不会自动重新调查或重新固化；
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
  保存资料引用及其直接决定范围
        ↓
MaterialDecision
  明确资料在哪个结论种类、场景和条件下直接决定什么
        ↓
MaterialConnection
  直接说明上下游和同级资料怎么依赖及产生什么影响
        ↓
AuthorityFinding
  在完成资料调查后表达当前可以或不可以得到的结论
```

不得把业务角色、冲突关系和 Authority 结论塞进 `EvidenceRef.metadata`。
