# Authority Agent 协议

> 状态：本文已完成第一轮设计裁决（2026-08-01）。裁决结论汇总见
> `spec/alg/authority-minimal-chain.md`（v0.1）。第二章中标注"已裁决"的条目以裁决
> 结论为准，后续新冲突追加为新条目；第一章与裁决结论冲突的表述已同步修正。

# 第一章：长期协议

## 1. 目标

Authority 是一项通用能力，不属于 Judge 私有流程。

当多份业务文档、上下游契约、配置、代码行为或人工说明对同一个业务问题给出不同
说法时，Authority Agent 回答：

> 在给定业务范围内，根据当前可取得的资料，能否确定应采用哪一种说法？

Authority Agent 只解决“标准是否确定”，不判断某个实际输出是否满足用户要求。

```text
多个可能冲突的资料
    + 一个明确的业务决定问题
    + 业务适用条件
    ↓
Authority Agent
    ↓
resolved：当前范围内可以确定采用什么说法
或
unresolved：当前资料不足以确定，并说明冲突和待补证内容
```

## 2. 职责边界

Authority Agent 负责：

- 根据调用方提出的一个明确业务问题，读取相关 Context 和 Evidence；
- 必要时调用检索、Key-index、业务 API、数据库观察或其他证据 Tool；
- 区分正式业务标准、外部上下游契约、当前系统行为和辅助资料；
- 分析来源的适用条件、上下游依赖、覆盖、替代和冲突关系；
- 返回 `resolved` 或 `unresolved`，并保留可追溯证据和原因。

Authority Agent 不负责：

- 生成当前 Case 的 `BusinessExpectation`；
- 判断 actual 是否 `fulfilled` 或 `not_fulfilled`；
- 输出 Judge verdict、score、confidence 或 overall；
- 为了得到确定答案而发明资料优先级；
- 把当前代码行为自动当作正式业务标准；
- 在没有实际证据时用模型常识补成业务结论。

不同调用方自行消费 Authority 结果：

| 调用方 | 依赖 Authority 且结果为 unresolved 时的业务义务 |
|---|---|
| Judge | 对应业务评价不得输出肯定结论，应为 `not_evaluable` 并说明原因 |
| Mock | 不得把未确认规则伪造成标准行为 |
| Attribute | 不得断言实现违反了尚未确定的正式规则 |

## 3. 调用形态

Authority 是 Agent 能力，对其他 Runtime LLM 暴露为按需调用的 Tool：

```text
主 LLM
    ↓ 发现当前判断确实需要确认业务标准
authority.resolve(decision_question)
    ↓
Authority Agent
    ├── 使用宿主绑定的 Authority 运行时契约（verifier 内为 AuthorityEnvironment）
    ├── 按需 Search/Load 资料、调用验证 Tool（EvidenceSpace / ToolGateway）
    └── 形成 AuthorityResolution
    ↓
主 LLM 继续原有任务
```

`authority.resolve` 是调用边界；Authority Agent 内部可以使用 LLM。它不是一个
“输入相同必然产生相同结论”的确定性函数。

现有 `VerifiableTool` 继续用于取得可复查的当前事实。Authority Agent 对多份事实和
资料作出的综合判断不得伪装成新的确定性事实。若使用现有 `ToolResult` 承载调用：

```text
ToolResult.status
    = Authority Agent 是否成功执行

ToolResult.outputs.resolution.status
    = 业务 Authority 是否 resolved / unresolved
```

`ToolResult.status=failed` 不能被改写为“业务 Authority unresolved”；前者表示工具或
Agent 没有完成工作，后者表示已经完成调查但当前资料不足以确定标准。

## 4. 最小输入输出与资料空间

对 LLM 的公开协议只新增一个通用请求和一个通用结果，不建立 Judge-specific Point、Plan
或 Binding。资料从哪里来不是由 LLM 请求决定，而是由 Core 在创建 Tool 时绑定的
`AuthorityEnvironment` 决定。

```python
from dataclasses import dataclass
from typing import Literal

# Existing runtime types; they are not new Authority schemas.
from impl.core.schema import EvidenceRef


@dataclass(frozen=True)
class AuthorityRequest:
    decision_question: str


@dataclass(frozen=True)
class AuthorityResolution:
    status: Literal["resolved", "unresolved"]
    statement: str
    reason: str
    basis_evidence_ref_ids: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()
```

`AuthorityEnvironment` 是 Core 私有的运行时组合对象，不属于公共协议；它组合
`ProjectSpec`、`ContextRun`、证据空间（`ContextRuntime.registry` 的授权子集）与授权
`VerifiableTool`，并持有 `environment_snapshot_sha256`。公共协议只暴露
`AuthorityRequest` 与 `AuthorityResolution`。

### 4.1 `AuthorityRequest`

| 字段 | 业务意义 |
|---|---|
| `decision_question` | 本次需要确定的一个完整业务规则、定义、契约或来源选择问题；必须包含所有可能改变答案、且未被 Environment 固定的业务条件，不能是“当前输出对不对”，也不能替代业务 API 查询当前事实 |

主 LLM 只传一个完整业务问题，不直接填写项目、Role、ContextUnit 或 EvidenceRef ID。
`authority.resolve` 的代码执行环境负责构造并绑定 `AuthorityEnvironment`。

`decision_question` 不承担资料空间或权限控制。有效资料空间始终是代码绑定的
`AuthorityEnvironment`；问题中的上下游、业务版本、渠道、产品或其他条件只限定结论的
业务适用性，不能切换项目、扩大权限或令其他项目的证据变得可见。

如果某个条件已经被 Environment 确定，例如项目身份、调用方 Role 或 Production/Draft
资产选择，问题不必重复它；如果同一 Environment 内不同条件可能得到不同答案，例如业务
渠道、下游协议版本或客户类型，`decision_question` 必须把该条件说清楚。若缺失条件导致
无法唯一作答，Authority 返回 unresolved，并在 `required_evidence` 中说明需要明确什么，
不再新增另一个字段或中间 schema 补救。

### 4.2 Authority 的运行时契约（宿主无关 Ports）与 verifier 适配

Authority Agent 的协议只依赖宿主无关的运行时契约（Ports）。公共协议只暴露
`AuthorityRequest` 与 `AuthorityResolution`；Agent 本体、prompt 与 Finalization 校验
不直接依赖任何 verifier 具体类型。曾提出 `EvidenceCatalog` 作为 EvidenceRef 的运行时
读取、登记和校验接口；**已裁决不新增该公共协议名**，引用校验属于 `EvidenceSpace` 的
职责（verifier 内由 Core 后处理基于 `ContextRuntime.registry` 与 `ContextRun` 的
loaded/hash 记录完成）。

```text
EvidenceSpace       ：search / load / ref 校验 / hash（可寻址资料集合）
Materializer        ：内容（ToolResult/文件/人工澄清）→ 可寻址、可重载、可 hash 单元
ToolGateway         ：执行动态获取能力，结果自动回填物化
PermissionBoundary  ：当前上下文可见范围与预算（宿主绑定，Agent 不能扩大）
EnvironmentSnapshot ：环境指纹（权限、资料 revision、工具指纹）
```

每个 Port 的宿主无关约束：

- `EvidenceSpace`：资料必须可寻址、可重载、可 hash；只有被实际 Load 的单元才可进入
  `basis_evidence_ref_ids`；ref 校验 = 引用能回到真实来源且 hash 未变；
- `Materializer`（物化通道，已裁决）：任何想被引用的内容（ToolResult、文件、人工澄清）
  必须先物化为可寻址、可重载、可 hash 单元；动态 ToolResult 物化为 case-scoped 单元，
  静态资料物化为 project_static 单元；EvidenceRef 只引用已物化且 hash 未变的单元；
  废弃"ToolResult 直接生成 EvidenceRef"的路线 A；Tool 定义本身不是证据，只有某次
  ToolCall 物化后的结果才可能成为证据；
- `ToolGateway`：执行结果自动回填物化；工具执行失败（能力不可用）与业务 unresolved
  必须分开；
- `PermissionBoundary`：权限与预算由宿主绑定，Agent 不能自行创建更宽空间；
- `EnvironmentSnapshot`：覆盖权限、资料 revision 与工具指纹，区分不同宿主、Role、
  Draft/Production 与资料版本，供审计与复用；只描述调用开始时绑定的静态环境，执行中
  新物化的单元不回写 snapshot，进入本次 Tool audit。

换场景（verifier 外部或内部新项目）复用同一 Agent 时，只需为这些 Ports 提供新的
Adapter 实现；协议、prompt 与校验逻辑不变。

**复用前提（诚实性边界）**：Authority 的"通用"不等于"无输入也能工作"。资料空间必须
可由至少一种来源充实，Authority 才有机会返回 resolved：

- Investigate/Solidify 物化产物（manifest evidence_refs → ContextUnit）；
- 运行时 Tool 执行结果（ToolResult → case-scoped ContextUnit）；
- 既有业务系统提供的可加载资料（经 Adapter 投影为 ContextUnit）。

如果宿主既没有调查产物、也没有授权工具、也没有可加载资料，Authority 只能返回
unresolved（诚实输出）。这不视为执行失败，也不通过修改协议补救——该场景要真正用上
Authority，必须先充实资料供应链（补调查、授权工具或接入资料），而不是改 Agent 本身。

#### verifier Adapter（verifier 内的实现层）

verifier 用下列既有对象实现五个 Ports：

```text
ContextRuntime + ContextRun             → EvidenceSpace
Attribute 物化通道公共化（§22.6）       → Materializer
VerifiableTool + 自动登记包装            → ToolGateway
Role policy + ContextRun 权限交集        → PermissionBoundary
逐资产来源 + registry hash + Tool 指纹  → EnvironmentSnapshot
```

Core 在 verifier 内按下列流程组合这些 Adapter，得到当前调用方绑定的运行时对象。该对象
内部称为 `AuthorityEnvironment`，是 Core 私有的组合对象，不属于公共协议：

```text
RunTrace.project_id + 调用方 role/operation/trace/run/case
    ↓ load_project / ProjectSpec
ProjectSpec
    + resolve_role_assets(spec, role, use_candidate)
    + 当前 Role 的 Context policy
    + 当前 Role 选中的 Investigation manifest（可以没有，也可以有多个）
    + 当前 Role 允许的 Tool
    ↓
ContextRuntime.start_run(...)
    ↓
AuthorityEnvironment(spec, context_run, evidence 空间, tools, environment_snapshot_sha256)
```

组合字段的业务意义：

| 组合字段 | 来源 | 业务意义 |
|---|---|---|
| `spec` | 当前 `RunTrace.project_id` 解析出的 `ProjectSpec` | 防止 Authority 跨业务项目取资料 |
| `context_run` | 当前调用方 Role 的 `ContextRuntime.start_run()` | 限定 Role、operation、trace/case、可见 Context 和访问预算 |
| `evidence 空间` | 当前选中 Investigation manifest 物化的 ContextUnit，加上本次 Tool 执行自动登记的 ContextUnit | 让结果中的 ref_id 能回到真实来源；没有登记就不能引用（由 Core 后处理校验） |
| `tools` | `resolve_role_assets()` 选出的当前 Role Tool，或项目 Tool fallback | 限定可以调用的动态验证能力 |
| `environment_snapshot_sha256` | 由项目、Role、Production/Draft 资产、Context 内容 revision、Evidence 来源 revision 和 Tool 实现指纹确定性计算 | 区分不同项目、不同 Role、不同 Draft/Production 和不同资料版本，供审计与复用 |

同一 Role 如果选中多个 Investigation manifest，Core 必须先分别验证其 `project_id`、
`role` 和 source revision，再合并物化的 ContextUnit；重复来源指向不同内容时 Environment
构造失败。没有 Investigation manifest 时证据空间可以从空集合开始，Authority 仍可使用
已授权 Context 或 Tool；最终拿不到决定性证据时返回 unresolved，而不是把"没有调查包"
本身当作执行错误。

跨 Run 复用必须同时匹配 Environment snapshot 和最终 basis Evidence revision，不能仅凭
Request 文本命中缓存。

`use_candidate` 必须由项目 Role 配置和当前执行策略决定，不能由 `decision_question` 或
LLM 选择。ContextRun 的权限还必须与项目、Role、trace 和 case 相交收窄；Authority Agent
不能自行创建一个更宽的 ContextRun。

不同调用方若需要共享同一正式业务资料，应在 Role assets 中明确授权给多个 Role；不允许
因为 Authority 是通用 Agent 就默认读取项目全部资料。

如果 `ProjectSpec`、ContextRun 权限、Role assets、manifest 或 Tool 装载失败，
`authority.resolve` 不得启动 Authority Agent，并返回 `ToolResult.status=failed`。只有
Environment 已成功构造、Agent 也完成调查，但当前资料仍不足时，才返回业务
`AuthorityResolution.status=unresolved`。

如果调用方已经发现某份直接证据，可以由 Tool wrapper 作为候选提示注入；模型不能
自行生成或跨 ContextRun 复制物理 ID。Authority Agent 仍需在结果中说明最终真正使用
了哪些 EvidenceRef。Agent 新调用的业务 Tool 结果必须先物化为当前 Authority 证据空间
可见的 ContextUnit，再允许进入 `basis_evidence_ref_ids`。

### 4.3 `AuthorityResolution`

| 字段 | 业务意义 |
|---|---|
| `status` | `resolved` 表示当前范围内可确定；`unresolved` 表示当前资料不足以确定 |
| `statement` | resolved 时采用的业务说法；unresolved 时必须为空 |
| `reason` | 无论 resolved 还是 unresolved，都解释为什么能够或不能确定；可说明来源决定性、资料不足、冲突或范围不明 |
| `basis_evidence_ref_ids` | 实际支撑结论或构成冲突的 EvidenceRef |
| `required_evidence` | unresolved 时说明还需要取得什么资料或人工澄清 |

`AuthorityRequest`、`AuthorityResolution` 和本次 `AuthorityEnvironment` 的
`environment_snapshot_sha256` 必须作为同一次 Tool audit 一并保存；不能单独保存一个
脱离问题和资料空间的 Resolution。不新增 `resolution_id`。一次调用由现有
trace、Tool call 和 Request/Resolution audit 定位；若某个结论需要长期复用，由 Solidify
按现有 ContextUnit 规则固化，而不是让 LLM 生成另一套永久 ID。

## 5. Authority Agent 的判断顺序

Authority Agent 按以下顺序工作：

1. 校验 `decision_question` 是否只包含一个业务决定问题，并识别其中会改变答案的业务条件；
2. 根据问题中明确的上下游、版本、渠道、产品或其他条件排除明显不适用的资料；
3. 通过 Core 已绑定的 `AuthorityEnvironment` 加载当前项目允许的 Context、Evidence 和调查快照；
4. 信息不足时按需调用检索、Key-index 或业务验证 Tool；
5. 对每份决定性资料识别其来源、业务定位、适用条件和上下游消费关系；
6. 判断是否存在能够在问题明确条件内唯一决定问题的证据；
7. 能确定时返回 resolved；仍冲突或缺少决定性证据时返回 unresolved。

resolved 的最低要求：

- `statement` 非空；
- `reason` 非空，并说明为什么当前资料对问题中的业务条件具有决定性；
- `basis_evidence_ref_ids` 非空；
- EvidenceRef 可以回到真实文件、artifact、物化后的 Tool 执行结果或人工澄清记录；
- 结论没有超出 `decision_question` 明确的业务条件；
- 如果存在冲突，必须说明为什么某份资料在当前条件下具有决定性，而不是只声明
  “优先级更高”。

unresolved 的最低要求：

- `statement` 为空；
- `reason` 具体说明冲突、证据不足或问题业务条件不明；
- `required_evidence` 非空；
- 如果已经发现资料或冲突，必须进入 `basis_evidence_ref_ids`；
- 不能只写“需要更多信息”，必须说明缺少哪类决定性证据。

## 6. 与 Investigate 的非硬依赖串联

Investigate 为 Authority Agent 准备可发现、可加载、可验证的环境，但不要求每次调查
都提前解决所有未来 Authority 问题。

```text
Investigate
    ├── EvidenceRef：登记真实资料和来源
    ├── ContextUnit：固化可复用的业务上下文
    ├── Key-index：为大资料提供按 key 检索和加载能力
    └── ToolRequirement / VerifiableTool：提供动态验证能力
              ↓ 可选输入，不是硬前置
Runtime 主 LLM
    ↓ 碰到明确标准问题时
authority.resolve(
    decision_question,
)
```

Investigate 的义务是：

- 让重要资料存在真实可引用的登记（manifest evidence_refs，进入 Runtime 后物化为
  ContextUnit），而不是只写一段结论摘要；
- 大资料需要检索时提供 Key-index，而不是把全量资料塞进 Prompt；
- 需要动态事实时提供可执行 Tool，而不是把 ToolRequirement 当作执行结果；
- 可以提前识别常见冲突并调用 Authority Agent，但这不是调查包通过的必需条件；
- 不按 badcase 或未来请求穷举所有 Authority 问题。

如果 Investigate 已经解决了一个稳定、可复用的问题，Solidify 可以把配对保存的
`AuthorityRequest + AuthorityResolution + basis EvidenceRef` 固化为 ContextUnit。Runtime
在完整 `decision_question`、Environment snapshot 和 Evidence revision 仍匹配时直接复用，
不再调用 Authority Agent。

资料 hash 或 revision 变化只会使旧结论不再可直接复用，不得自动启动外部调查或
Authority Agent；只有调用方显式发起新的调查或 Runtime 确实需要该结论时才运行。

## 7. Runtime 调用规则

主 LLM 只有在当前任务必须采用某个业务标准、且现有 Context 无法直接给出可靠结论
时才调用 `authority.resolve`。

不需要调用的情况：

- 用户已经明确给出可直接比较的条件；
- actual 与用户明确表达可以通过确定性 Comparator 直接判断；
- 当前问题与任何资料冲突无关；
- 已有完整 `decision_question`、Environment snapshot 和 Evidence revision 匹配的 resolved Authority Context。

需要调用的情况：

- 多份资料对当前必须使用的业务含义给出不同说法；
- 现有资料都相关，但无法判断谁在当前上下游中具有决定性；
- 当前任务需要一个正式规则，而 Context 只提供了当前行为或辅助说明；
- 已固化 Authority Context 与当前完整问题、Environment snapshot 或 Evidence revision 不匹配。

Authority Agent 的调用次数必须按业务问题控制：同一次 Runtime 任务中，相同
`decision_question + environment_snapshot_sha256 + Evidence revisions`
只解析一次；多个消费点复用同一结果，不允许按 expectation、字段或输出项重复调用。

## 8. 调用方消费规则

Authority Agent 不决定当前 Case 是否依赖该结论。主 LLM 在自身业务判断中决定是否
调用；一旦调用，返回结果必须保留在当前 trace 的 Tool audit 中，不能只被模型口头
转述。

Judge 的最小消费方式是：

```text
原有 Runtime Judge LLM
    ├── 生成 BusinessExpectation[]
    ├── 生成 FulfillmentAssessment[]
    └── 遇到标准冲突时调用 authority.resolve

authority.resolve = resolved
    → Judge 使用 statement 和 basis evidence 继续原有评价

authority.resolve = unresolved
    → 依赖该问题的 FulfillmentAssessment = not_evaluable
    → Judge summary 写明 reason、basis sources 和 required_evidence

Tool / Agent 执行失败
    → FulfillmentAssessment = not_evaluable
    → 原因必须写“Authority 能力不可用”，不能伪写成资料冲突
```

Authority 不单独参与 overall 聚合。它先影响对应的
`FulfillmentAssessment.status`，再由现有 blocking expectation 规则确定性聚合：

```text
blocking assessment 因 Authority unresolved 而 not_evaluable
    ↓
overall_fulfillment = not_evaluable
```

Judge 不新增 `CaseEvaluationPoint`、`FrozenCaseEvaluationPlan` 或
`RuntimeExpectationBinding`。Authority 的使用记录复用当前 Tool audit、EvidenceRef
和 FulfillmentAssessment evidence 链。

**assessment 挂钩（已裁决）**：Judge LLM 在依赖某次 Authority 的
`FulfillmentAssessment` 中填写 `authority_tool_call_ids`，Core 后处理校验引用存在且
属于当前 trace；引用不存在的调用 → 该 assessment 标 `needs_human_review`，不静默放行。
引用的 resolution 为 unresolved 且 assessment 为 blocking → `not_evaluable`，并把
resolution 的 EvidenceRef 挂入 assessment 的 evidence 链。

**执行形态（已裁决）**：Production Judge 保持单次 agentic LLM 调用（一次
`complete_json` 会话），`authority.resolve` 作为 Judge 的 Tool（方案 i）；若实测单次
会话输出不稳定，升级为两段式（方案 ii：先生成 BusinessExpectation，再生成
FulfillmentAssessment）。

## 9. 中文案例：客户搜索中的业务词映射

当前请求：

```text
帮我找高净值且 30 岁以上的客户
```

Judge 可以直接比较“30 岁以上”是否被 actual 保留，不需要 Authority。对于“高净值”
的映射，如果已加载 Context 没有明确规则，Judge 按需调用：

```python
AuthorityRequest(
    decision_question=(
        "在当前线上业务版本中，向下游客户搜索接口构造目标客户筛选条件时，"
        "‘高净值客户’应采用哪一种正式定义？"
    ),
)
```

这次调用的资料空间不是由上面的问题文本决定，而是由 Core 根据当前运行绑定：

```text
project_id = client_search
caller_role = judge
asset_source = 当前 Judge 执行策略逐资产选择的 Production 或 Draft（snapshot 记录逐资产来源，§13.2）
trace/case = 当前 Judge RunTrace
证据空间 = 当前 Judge Investigation manifest 物化的 ContextUnit + 本次已登记 Tool 物化结果
```

因此同一个问题在 `deerflow/mock` 或 `client_search/attribute` 环境中不会自动读取
`client_search/judge` 的资料；只有项目配置明确把资料授权给这些 Role，才会进入它们的
AuthorityEnvironment。

如果 Authority Agent 发现业务资料、字段配置和下游契约给出相互不兼容的定义，且无法
确认哪份资料拥有当前范围的最终解释权：

```python
AuthorityResolution(
    status="unresolved",
    statement="",
    reason=(
        "当前 Judge standard、项目字段配置和 mapping/enum 冲突扫描对相关定义的表达不一致；"
        "这些资料没有给出适用于当前版本的正式审批、覆盖或最终解释关系。"
    ),
    basis_evidence_ref_ids=(
        "current-judge-standard",
        "current-project-config",
        "authority-conflicts-scan-20",
    ),
    required_evidence=(
        "取得明确适用当前版本的正式业务定义，或由业务责任人确认哪份下游契约具有最终解释权。",
    ),
)
```

> 注：案例中的 `current-judge-standard`、`current-project-config`、
> `authority-conflicts-scan-20` 是 manifest 的来源别名（ref_id）。运行时它们物化为代码
> 生成的 ContextUnit unit_id，`basis_evidence_ref_ids` 以物化后的 unit_id 为准，来源
> 别名保留在 tags 中（§4.2、§13.3）。

Judge 对两条要求分别处理：

```text
“年龄 30 岁以上被保留”
    → 直接比较，正常输出 fulfilled / not_fulfilled

“高净值被正确映射”
    → 依赖 unresolved Authority
    → not_evaluable，并展示具体冲突和待补证内容
```

不能因为“高净值” unresolved 就把与它无关的年龄条件也标成 not_evaluable。

## 10. Validator 与审计要求

- `decision_question` 必须非空，不得包含 Judge verdict、expected answer 或多个无关问题；
- 如果同一 Environment 内的上下游、版本、渠道、产品或其他条件会改变答案，
  `decision_question` 必须明确这些条件；条件不足时只能 unresolved；
- Tool wrapper 注入的 ContextUnit、EvidenceRef 和 Investigation snapshot 必须属于当前
  项目及调用方权限范围；
- `decision_question` 不能据此加载其他项目资料、切换 Production/Draft 或扩大权限；
- `basis_evidence_ref_ids` 中每个 ID 都必须能在当前证据空间（已物化 ContextUnit）中
  解析；模型不得生成未知 ID；动态 ToolResult 必须先物化为 ContextUnit 才能被引用；
- resolved 必须有 statement、reason 和 basis EvidenceRef；
- unresolved 必须没有 statement，有 reason 和 required_evidence；
- unresolved 可以没有 basis EvidenceRef，但如果已经发现资料或冲突，必须保留对应引用；
- Authority Agent 引用的 ToolResult 必须保留真实输入、输出和执行状态；
- Tool 执行失败与业务 unresolved 必须分开；
- 结论不得超出 `decision_question` 明确的业务条件或 `AuthorityEnvironment` 的项目与权限边界；
- 当前行为、Prompt、代码或模型输出不能仅凭“正在使用”自动成为正式标准；
- Authority Agent 不得输出 fulfilled、not_fulfilled、JudgeResult 或 overall；
- 主调用方必须保留 Authority Tool audit；
- 相同完整问题、Environment snapshot 和 Evidence revisions 在一次 Runtime 任务内不得重复调用；
- Authority unresolved 不能被未引用的新资料或模型常识静默覆盖。

---

# 第二章：设计矛盾、冲突与裁决记录

本章是设计审查账本，不是要求 LLM 或项目实现新增的 Schema。它把 Authority 设计中
已经暴露的业务疑问、对象边界冲突和当前代码不一致集中记录。2026-08-01 第一轮裁决已
关闭 §12～§17 的冲突条目（节内以"已裁决"标注）；§18 是当前代码事实清单；后续新冲突
追加为新条目并标注裁决状态。

如果本章与第一章存在表述差异，以第一章长期协议和节内裁决结论为准，不能选择其中一条
直接实施。实施前必须逐项确认：保留什么、删除什么、由哪个已有对象承担、以及是否需要
修改公共协议。

## 11. 已确认的业务底线

下面不是待讨论的实现细节，而是当前 Authority 设计必须满足的业务原则：

1. Authority 的意义是：当文档、代码、配置、上下游资料或人工说明对同一个业务问题
   给出相近但冲突的说法时，判断当前信息能否确定采用哪一种说法。
2. 调查包已经能够确定的，以调查结果和其真实来源为依据；不能把模型常识或当前代码
   “正在使用”自动升级为正式标准。
3. 调查包发现冲突且无法确定的，Runtime 不得输出没有 Authority 支撑的肯定业务结论；
   对依赖该问题的评价返回 `not_evaluable`，并在 Judge summary 中说明具体冲突、来源和
   缺失的决定性证据。
4. `not_evaluable` 不是永久结论。人类补充资料、业务确认、可用的确定性 Tool 或新的
   调查结果进入同一证据链后，可以重新调查并解除它。
5. Investigate/Solidify 可以产生 ContextUnit、Tool 和来源信息；Runtime 代码负责引用、
   校验和审计这些信息。LLM 不得自由生成物理来源 ID。
6. Authority 是可被多个调用方复用的能力，不应为了 Judge 增加一套只能服务某类 Case 的
   Planning、Point 或 Binding 领域对象。

## 12. 对象职责是否被重复建模

### 12.1 `ContextUnit`、`Tool`、`EvidenceRef` 是否应该合并

> **已裁决（2026-08-01）**：三类对象不合并。`ContextUnit`=可寻址、可加载、可 hash 的
> 资料载体（唯一）；`VerifiableTool`=动态事实获取能力，ToolResult 必须先物化为
> ContextUnit 才能被引用；`EvidenceRef`=只指向已物化单元的引用（location=unit_id,
> payload=None）。Tool 定义本身不是证据，只有某次 ToolCall 物化后的结果才可能成为证据。

裁决结论：

- `EvidenceRef` 只承担最终引用（`ref_id`、来源定位、revision/hash），不存全文、不承担
  资料目录或加载；完整内容通过物化后的 ContextUnit 取得；
- Tool 定义本身不是证据，只有某次 ToolCall 物化后的结果才可能成为证据；
- 一个 ContextUnit 只有被实际 Load 后才可进入 `basis_evidence_ref_ids`；
- ToolResult 必须先物化为 ContextUnit 才能被引用（§4.2 物化通道），不允许直接由
  EvidenceRef 指向 ToolCall receipt。

### 12.2 `EvidenceCatalog` 是否是必要的新概念

> **已裁决（2026-08-01）**：不新增 `EvidenceCatalog`。引用校验由 Core 后处理基于
> `ContextRuntime.registry` + `ContextRun` 的 loaded/hash 记录完成；`EvidenceRef` 的
> 生成与校验是 Core 普通后处理职责，不引入独立公共协议名或新存储。

裁决依据：现有代码已具备 Context Registry（登记 ContextUnitRecord、来源和 source
hash）、`ContextRun`（Search/Load/权限/预算）、Trace/Tool audit（保存 Tool 调用和
执行结果）和 `EvidenceRef`（最终引用关系）。`get/register` 职责可由这些既有对象
承担，独立 `EvidenceCatalog` 只会形成第二套来源和 hash 账本。

### 12.3 `AuthorityEnvironment` 是否被过度拆分

> **已裁决（2026-08-01）**：`AuthorityEnvironment` 是 Core 私有的运行时组合对象，不是
> 公共 schema；公共协议只暴露 `AuthorityRequest` / `AuthorityResolution`。不保留 frozen
> 不可变承诺（内部 ContextRun / Tool audit 可变），不拆分 `context_access` /
> `evidence_recorder` 等平行名称。

裁决依据：`AuthorityEnvironment`、`AuthorityExecutionEnvironment`、`context_access`、
`evidence_recorder`、`EvidenceCatalog` 等名称描述的是同一件事——Core 绑定当前资料和
Tool，并在结束时生成可追溯引用。公共协议只需要 Request/Resolution 两个形状；
Environment 内部是否组合 `spec`/registry 引用是 Core 实现细节，不构成协议承诺。

## 13. 资料空间、适用范围与来源绑定的冲突

### 13.1 资料空间与业务适用范围是不是一回事

> **已裁决（2026-08-01）**：资料空间与业务适用性正交。资料空间=代码绑定的 ContextRun
> policy 交集；业务适用条件=全部放进 `decision_question`；不新增 `applicability_scope`
> 字段。`statement` 不重复适用条件，结论与 Request/Environment 绑定保存。
> `varying_conditions`（Environment 提供本环境已知会改变答案的业务维度清单，Agent 必须
> 覆盖，未覆盖 → unresolved）列为 V1 后扩展。

裁决依据：两个概念不能由同一个字段表达。`ContextRun` 的
project/role/operation/trace/case policy 已足以绑定资料空间；`decision_question`
足以表达业务适用条件。新增 `applicability_scope` 只会同时承担业务条件与权限边界两种
语义，且无法保证不扩大资料权限，故不引入。同一 Environment 内不同版本/渠道/产品得到
不同答案时，由问题文本表达条件；条件不足 → unresolved。

### 13.2 `ProjectSpec`、`Role assets`、`ContextRun` 谁是真正的空间边界

> **已裁决（2026-08-01）**：沿用调用方 Role 的权限交集，不新增独立 `authority` Role；
> Authority 不能自行创建更宽 ContextRun；资产选择按逐资产 Production/Draft 混合记录
> （§18.6），snapshot 覆盖逐资产来源；`ProjectSpec` 是配置入口兼授权依据。

裁决依据：`ProjectSpec` 是配置入口兼授权依据（`resolve_role_assets` 从中解析），仅保存
ProjectSpec 不能阻止越权，真正的授权边界是 `resolve_role_assets()` + Context policy 的
交集。资产选择按逐资产独立（Candidate/Production 可能混合，§18.6），Environment
snapshot 必须覆盖逐资产来源，不能只保存一个 `asset_source` 枚举。Authority 沿用调用方
Role 的权限交集，不新增独立 `authority` Role；跨 Role 共享资料必须通过 Role assets
显式授权；Authority 不能自行创建更宽的 ContextRun，Core 把现有句柄传入。

### 13.3 Investigate 产物如何进入 Runtime 可发现空间

> **已裁决（2026-08-01）**：Investigate 产物以"物化"方式进入 Runtime 可发现空间——
> manifest evidence_refs 物化为 ContextUnitRecord（content_ref 指向原文件，ref_id 存
> tags 作来源别名，unit_id 由代码生成）；找不到原始来源 → Environment 构造失败
> （fail-closed），不进业务层；Investigate 发现 unresolved 可以直接报告，不强制继续
> 调查。

调查包可能包含：

- Investigation manifest；
- manifest 中的 EvidenceRef；
- 文档和扫描报告；
- ToolRequirement；
- 已经 Solidify 的 Context 文件。

当前实现并不自动保证它们处于同一个运行空间：

- `_asset_records()` 会把调查目录中的文档转换为 ContextUnitRecord，但排除 `manifest.json`；
- `load_role_mandatory_context()` 在已有 Context 资产时会过滤 Investigation 资产；
- manifest 里的 EvidenceRef 不会自动变成可 Search/Load 的 ContextUnit；
- Judge/Mock loader 当前返回拼接内容和 debug，而不返回实际 `ContextRun` 句柄。

裁决结论：

- Authority 不直接读取 manifest 的 EvidenceRef；对应来源必须先物化为 ContextUnit 才能
  被 Search/Load 和引用（V1 改造项，§22.6）；
- 物化时 unit_id 由代码生成，manifest 的 `ref_id` 存入 tags 作来源别名；一个 EvidenceRef
  物化后对应一个 ContextUnit，不允许多对一或指向 ToolCall receipt；
- 调查包的 overview、报告是导航摘要，不是可引用证据；只有物化后的原始资料可进入
  `basis_evidence_ref_ids`；
- 已有 EvidenceRef 找不到原始来源 → Environment 构造失败（fail-closed），不进业务层；
- Investigate 发现 unresolved 可以直接在调查包阶段报告，不强制继续调查；重新调查的
  起始点由调用方显式发起，从原始资料或冲突 EvidenceRef 开始。

## 14. Authority 结论本身的边界冲突

### 14.1 Authority 是“资料优先级”还是“当前能否得出结论”

> **已裁决（2026-08-01）**：拒绝固定全局优先级。resolved 必须给出决定性论证：当前问题
> 条件下哪份/哪些资料成立、其他为何被排除（覆盖/版本/消费链），允许多份资料通过上下游
> 链共同唯一确定。当前行为=事实证据、契约=标准证据，契约适用版本不明 → unresolved。

裁决依据：Authority 判断的是"当前问题 + 当前资料 + 当前上下游关系是否已能确定一个业务
结论"，不是背诵优先级。不允许规定"下游外部契约永远高于项目配置"；下游当前行为与契约
冲突时，行为是事实证据、契约是标准证据，契约适用版本不明 → unresolved。业务文档、代码、
配置、人工说明各自只负责一个条件时，不比较全局优先级，而是判断它们是否在同一业务问题
上构成完整链路。`resolved` 不要求单一唯一权威资料，允许多份资料通过上下游关系共同唯一
确定。资料"相关"（source claim、summary、关键词命中）不等于"可决定结论"，后者必须由
决定性论证支撑。

### 14.2 Authority 的调查单位到底是什么

> **已裁决（2026-08-01）**：调查单位以资料侧为主——Investigate 产出资料 + 每份资料的
> decision capability（能决定什么/不能决定什么/与谁冲突），不提前输出
> resolved/unresolved；`AuthorityFinding`/`AuthorityAnalysis` 不作为运行时对象；Solidify
> 只固化已验证的 (question, resolution, basis) 配对。

裁决依据：调查阶段通常没有具体 Runtime Case，因此不以 Case/BusinessExpectation 为轴
（会过早特化），也不以 AuthorityFinding 为轴（会重新引入与 Judge 强绑定的业务观点
对象）。调查报告以"资料/证据"为主记录单位，每份资料通过上下游关系说明其可决定的业务
条件（decision capability：能决定什么、不能决定什么、与谁冲突），保留完整路径、前后
链路、上游依赖和下游消费关系。`AuthorityFinding`/`AuthorityAnalysis` 不作为运行时对象；
最终 resolved/unresolved 由通用 Authority Agent 在 Runtime 根据 `decision_question`
临时形成。Investigate 只负责搜集和组织证据，不要求在没有 Case 的前提下提前做出
AuthorityResolution；Solidify 只固化已验证的 (question, resolution, basis) 配对。

### 14.3 “特殊 Case”与“通用问题类型”的冲突

> **已裁决（2026-08-01）**：特殊 Case 的冲突通过 `decision_question + evidence + reason`
> 表达，不新增 case-specific schema；问题类型（定义/映射/契约/责任/等价/事实可见性）
> 只作说明性标签，不改变运行逻辑。

裁决依据："孤儿单""高净值""意外产品"等词本身不构成通用 Authority 枚举。问题类型
（定义、映射、契约、责任边界、执行等价性、当前事实可见性）只作说明性标签，不改变运行
逻辑；特殊 Case 的冲突一律通过 `decision_question + evidence + reason` 表达，不新增
case-specific schema。调查阶段不为"看起来完整"预写未来 Case 的结论。

### 14.4 Authority 与 Judge BusinessExpectation 的关系

当前第一章明确保留 Runtime `BusinessExpectation` 的原有语义：它表示当前 Case 中一条可单独
判断的业务要求。

裁决结论（2026-08-01）：Authority 不生成 expectation，也不生成 Point。Runtime Judge 在
   判断某条 BusinessExpectation 时按需调用 Authority，并把同一调用结果引用到对应
   Assessment（assessment 写 `authority_tool_call_ids`，Core 后处理校验引用存在，见 §8）；
   不引入 `CaseEvaluationPoint`/`RuntimeExpectationBinding`，Judge summary 通过
   assessment 引用的 authority tool_call 定位"哪条 not_evaluable 是因为哪个 Authority
   问题"。一个 Authority 结论可被多个 BusinessExpectation 复用（单任务内按
   question + snapshot 去重）。执行形态采用方案 i：Production Judge 保持单次 agentic
   LLM 调用，`authority.resolve` 作为 Judge 的 Tool；若实测不稳再升级方案 ii。

## 15. 动态 Tool、ContextUnit 与证据固化的冲突

### 15.1 ToolResult 直接生成 EvidenceRef，还是先生成 ContextUnit

> **已裁决（2026-08-01）**：强制路线 B（单条物化通道），废弃路线 A。Search 只发现候选、
> Load 才能引用，适用于所有资料与 Tool 结果；"所有 ToolResult 都必须先转 ContextUnit"
> 是长期协议结论。

裁决依据：路线 A 的 ToolCall receipt 无法独立重载、无法校验 hash，会退化为"只存在于
模型输出里的字符串列表"，故废弃。强制路线 B（单条物化通道）后，每个动态结果都会进入
Registry，这是证据可验证的必要代价；性能问题通过 Context 预算（load_limit、
content_char_budget）和 case-scoped 生命周期控制，而不是通过允许路线 A 绕过。
Source/file 检索 Tool 返回的片段不能直接成为证据，必须保存完整文件或完整 key 对应
内容。"Search 只发现候选、Load 才能引用"适用于所有资料与 Tool 结果。

### 15.2 ContextUnit 由谁生成、何时生成

> **已裁决（2026-08-01）**：静态 ContextUnit 由 Investigate/Solidify 从真实来源忠实
> 投影（不允许把 Authority 总结文字直接固化为 ContextUnit）；动态 ContextUnit 由
> ToolResult 物化，必须带 trace/case/run 隔离；source hash 变化 → 旧结论不可复用，
> 不自动触发重新调查。

裁决结论：

- ContextUnit 按来源分三类：Investigate/Solidify 生成的长期静态单元（Core 从真实来源
  忠实投影，内容或 content_ref 直接指向原始资料）；Runtime ToolResult 物化的 case 级
  动态单元（必须带 trace/case/run 隔离）；既有业务系统提供的可加载资料（经适配器投影）；
- 不允许把 Authority 的总结文字直接固化为 ContextUnit——固化内容必须能回到原始来源；
- source hash 变化 → 旧 EvidenceRef 禁止复用；不自动触发重新调查，等待调用方显式发起
  调查或 Runtime 确实需要该结论。

## 16. Runtime、Planning 与调用次数的冲突

> **已裁决（2026-08-01）**：不新增 Planning LLM；Runtime BusinessExpectation 由原有
> Judge LLM 生成；Authority 只能由主 Judge LLM 按需调用；三类结果明确且不重叠
> （failed=能力/配额/网络/非法结构；unresolved=资料冲突不足；resolved）；hash 变化
> 不自动调查；去重 key=(规范化 question + env snapshot + evidence revisions)；Key-index
> 定位为 Investigate/Solidify 构建产物（V1 后）。

裁决依据：过去把 Planning、Authority、Case Point 和 Gate 串成链路的方案废弃。Planning
只做确定性资料/能力整理，不设 Planning LLM；Runtime BusinessExpectation 由原有 Judge
LLM 生成，不被 Planning schema 替代；Authority 只能由主 Judge LLM 按需调用，不允许
Authority LLM 自主规划多次检索。同一 Runtime 任务内按 (规范化 question + env
snapshot + evidence revisions) 去重，多个 expectation 复用同一结论。Key-index 定位为
Investigate/Solidify 构建产物（V1 后），Runtime 只读使用。`environment_snapshot_sha256`
变化只使缓存失效，不自动触发调查。三类结果明确且不重叠：`failed`（能力/配额/网络/
非法结构）、`unresolved`（资料冲突不足）、`resolved`。

## 17. 通用 Agent 与框架类型的冲突

> **已裁决（2026-08-01）**：通用的是协议形状（Request/Resolution）与业务能力，不是
> verifier 具体对象；`ProjectSpec`/`ContextRun` 由项目适配层隐藏；不同调用方资料权限
> 显式取交集；不设独立 `authority` Role；Investigate/Solidify 是可选资料生产者；
> 宿主无关 Ports 与复用前提见 §4.2。

裁决依据：通用的是 Authority 的业务能力与协议形状（Request/Resolution），不是
`AuthorityEnvironment` 或 verifier 的具体 Python 对象。其他项目只需提供 Role assets、
Context 资料和 Tool，即可复用同一个 Authority Agent；`ProjectSpec`/`ContextRun` 由项目
适配层隐藏，不暴露为公共 Authority 协议。不同调用方的资料权限必须显式取交集，不能因为
Authority 通用就读取全项目资料；Judge/Mock/Attribute 通过 Role assets 显式授权共享
能力，保持各自权限与审计边界。Investigate/Solidify 是 Authority 的可选资料生产者，
不是硬前置 Role；不设独立 `authority` Role。

## 18. 当前代码与协议的已知不一致

以下是已核对的实现事实，不是理论问题：

1. `impl/core/context/project.py::load_role_mandatory_context()` 创建了 `ContextRun`，但返回
   的是拼接 content、unit IDs 和 debug，调用方拿不到可供 Authority 继续 Search/Load 的实际
   Run 句柄。
2. 该 loader 在已有 Context 资产时过滤 Investigation 资产，因而“Judge 已注入 Context”不等于
   “Judge 能读取调查包中的 EvidenceRef 或冲突扫描”。
3. `_asset_records()` 将调查目录里的文档转为 ContextUnitRecord，但排除 `manifest.json`；
   manifest 中的 EvidenceRef 因而不会自动进入 Context 搜索空间。
4. 当前代码没有通用 `EvidenceCatalog` 实现；已按裁决不新增该公共协议名（§12.2），
   引用校验由 Core 后处理基于 Context Registry + ContextRun 承担。
5. Attribute 已有 ToolResult → 动态 ContextUnit → Finalization → EvidenceRef 的实现，但这套
   机制尚未成为 Authority 可复用的公共调用路径。（V1 改造：抽取为公共物化通道）
6. `ProjectSpec` 的 Role assets 可以逐资产选择 Candidate 或 Production，一次选择结果可能混合
   两种来源；仅保存一个 Production/Draft 枚举不足以解释真实环境。
7. Authority 的 `ToolGateway` 期望统一工具接口（verifier 内为 `VerifiableTool`），但实际
   项目运行时还可能提供 Agno Function、Toolkit 或普通 callable，工具归一化规则尚未统一。
8. `client_search` 当前 Investigation manifest 声明了已实现的
   `client_search.condition_compare`，但对应 Judge Tool asset 仍是 disabled；实际调用
   `load_project_role_tools(spec, "judge")` 会因为实现未被 Role assets 授权而失败。
   （已裁决：工具未授权/装载失败 → Environment failed，不进业务层）
9. `client_search.es_enum_observation` 和 `client_search.query_result_equivalence` 在调查包中
   只有 ToolRequirement，当前没有可执行实现。
   （已裁决：未实现的 ToolRequirement 不进 Environment tools；缺失导致无法决定性验证 →
   业务 unresolved + required_evidence 说明；只有权限/装载/配置错误才是 Environment failed）
10. 当前 Judge Authority contract 已经有静态 `AuthorityAnalysis`、source claims 和
    `evidence_ref_ids`，而新 Authority Agent 又试图只保留 Request/Resolution。
    （已裁决：静态契约作为"已固化结论"保留复用，动态 resolve 负责补充其覆盖不到的新冲突；
    迁移与扩展顺序见 `authority-minimal-chain.md` §8）

## 19. 当前设计不得默认的结论

> 已按 2026-08-01 裁决更新：下列条目保留原文并标注裁决状态。标"已否定"的条目不得再作为
> 设计或实现前提；标"已确认"的条目已成为长期协议结论。

- “只要 EvidenceRef 管理正确，ContextUnit 和 Tool 就不再需要”——已否定（§12.1 三类对象不合并）；
- “所有 ToolResult 都必须先转 ContextUnit”——已确认（§15.1 单条物化通道）；
- “所有 ContextUnit 都必须来自 Investigation”——已否定（动态 ToolResult 物化也是来源，§15.2）；
- “Environment 必须包含 ProjectSpec、ContextRun、EvidenceCatalog 和完整 Tool 列表”——部分确认：
  Environment 是 Core 私有组合对象，`EvidenceCatalog` 不新增（§12.2/§12.3）；
- “环境 hash 变化就自动重新调查”——已否定（只失效、不自动触发，§16）；
- “下游行为、项目配置、代码实现或文档存在固定全局优先级”——已否定（§14.1 决定性论证）；
- “Authority 必须由 Planning 预先为每个 expectation 绑定”——已否定（§16 不新增 Planning/Binding）；
- “调查阶段必须枚举未来所有 Case 的 Authority 问题”——已否定（§14.2 资料侧为主、按需 resolve）；
- “Authority unresolved 必然意味着整个 Case 所有 expectation 都 not_evaluable”——已否定
  （只影响依赖该问题的 blocking assessment，§8）；
- “已有 EvidenceRef 的存在本身就证明其内容具有决定性”——已否定（resolved 需决定性论证，§14.1）；
- “当前 Judge loader 已经把 ContextUnit、Tool 和 EvidenceRef 完整交给 Authority”——事实性修正：
  Judge loader 不返回 ContextRun 句柄（§18.1），V1 需先补该句柄。

## 20. 实施前的裁决顺序

> 已按 2026-08-01 裁决执行：第 1～6 步的结论见 §12～§17 与
> `spec/alg/authority-minimal-chain.md`；下一步进入 §22 的一次性改造任务。

为了避免继续反复，实施前必须按以下顺序确认：

1. 先确定 EvidenceRef、ContextUnit、Tool 的职责边界；
2. 再确定 EvidenceRef 的来源加载和最终物化方式；
3. 再确定 Environment 是内部组合对象还是公共协议；
4. 再确定 Investigate/Solidify 资料如何进入 Runtime Context；
5. 再确定 Runtime BusinessExpectation 如何按需调用 Authority；
6. 最后才确定 Judge/Mock/Attribute 的接入适配和一次性代码改造任务。

在第 1～4 项没有明确前，不应通过新增 Planning、Binding、Finding 或额外 catalog 来掩盖
资料来源和证据生命周期的不清晰。

---

# 第三章：当前项目改造边界

本章保留现阶段拟议的一次性改造项，仅用于记录现状与长期协议之间的差异。它受第二章
裁决结果约束：第二章确认删除或替换的对象，必须从本章任务中同步删除或改写，不能把本章
当前文字直接当作实施清单。

## 21. 与现有 Authority 设计的关系

现有 Judge Authority 方案把 AuthorityAnalysis、Planning、Point、Binding 和 Gate
串成 Judge 内部专属链路，容易产生以下问题：

- 调查阶段试图提前穷举 Runtime 问题；
- Runtime applicability 被包装成大量中间 Schema；
- Authority 只能被 Judge 使用；
- 为每个 Case 增加固定 Planning LLM；
- 即使 Binding 存在，也不能证明 LLM 绑定正确。

本协议将职责收缩为：

```text
通用 Authority Agent
    = 按需解决一个明确的业务标准问题

Investigate
    = 可选地准备 Context / Evidence / Key-index / Tool

Judge
    = 按原有 Runtime 逻辑生成 BusinessExpectation 和 Assessment，
      只在需要时调用 Authority Agent

Core
    = 保留 Tool audit，并执行调用方已有的状态约束和 overall 聚合
```

## 22. 一次性改造任务

1. 将 Authority Agent 的通用输入输出移出 Judge-specific Schema；公开
   `AuthorityRequest` 只保留自包含业务条件的 `decision_question`，不再增加独立适用范围字段；
2. 提供 `authority.resolve` 的 tool-callable Agent 入口；
3. 实现宿主无关五个 Ports 的 verifier Adapter（§4.2），并新增 Core-owned
   `AuthorityEnvironment` 构造器：从当前 `ProjectSpec`、调用方 Role、ContextRun、
   Production/Draft asset selection、Investigation manifest 和 Role Tool 确定性组合
   这些 Adapter；主 LLM 不能选择或扩大该空间；（已确认：Environment 是 Core 私有组合
   对象，公共协议只暴露 Request/Resolution）
4. 为 Environment 计算 `environment_snapshot_sha256`，至少覆盖项目、Role、当前资产来源
   （含逐资产 Production/Draft，§18.6）、Context/Evidence revision 和 Tool 实现指纹，
   并保存到 Authority Tool audit；
5. 复用 Context Loader、EvidenceRef、Key-index 和现有 VerifiableTool；不让主 LLM 自由
   传递物理 Context/Evidence ID；
6. 建立公共物化通道：任何被引用的内容（ToolResult、manifest evidence_refs）先物化为
   ContextUnit，`EvidenceRef` 只指向已物化且 hash 未变的单元；引用校验由 Core 后处理基于
   `ContextRuntime.registry` + `ContextRun` 完成，不新增 `EvidenceCatalog` 公共协议名；
   不能把 `EvidenceRef` 退化为只存在于模型输出里的字符串列表；
7. Authority Agent 的 Agent 执行状态和业务 resolution 状态分开；
8. 为 Agent-as-Tool 建立调用方权限、当前 ContextRun 绑定、递归调用
   防护和 Tool/LLM 预算；
9. 支持 Investigate 可选准备 Context/Evidence，但不把 Authority Resolution 设为调查包硬门禁；
10. 支持已 Solidify 的匹配结论直接复用，避免 Runtime 重复调用；（V1 后）
11. Production Judge 保留原有单次 Runtime BusinessExpectation / Assessment 逻辑；
    （方案 i：一次 agentic 会话，`authority.resolve` 作为 Judge Tool）
12. 删除 Authority 对 Planning、CaseEvaluationPoint 和 RuntimeExpectationBinding 的硬依赖；
13. Judge 只在确有标准冲突时调用 Authority Agent；依赖 assessment 写
    `authority_tool_call_ids`，Core 后处理把 unresolved 且 blocking 的评价转为
    `not_evaluable`，引用不存在的调用标 `needs_human_review`；
14. 增加 resolved、unresolved、Agent 失败、已有 Context 复用、无关 expectation 不受阻断、
    assessment 引用不存在 tool_call → needs_human_review、单任务内按 question 去重、
    跨项目拒绝、跨 Role 拒绝、Production/Draft 隔离和 trace/case 隔离测试。

## 23. 实施边界

本协议不要求：

- 所有 Runtime Case 都调用 Authority Agent；
- Investigate 提前生成所有 Authority 结论；
- 修改原有 runtime `BusinessExpectation` 语义；
- 新增独立 Planning LLM；
- 为 V1 新增拥有全项目资料权限的独立 `authority` Role；
- 把整个 Investigation Package 塞入 Authority Prompt；
- 为每个项目复制一套 Authority Agent；
- 用 Authority Agent 替代业务 API、Comparator 或其他确定性 Tool。

Authority Agent 是通用能力，但它的证据空间必须由具体业务项目绑定，结论适用条件必须在
完整业务问题中表达；通用不等于脱离项目资料进行常识判断。
