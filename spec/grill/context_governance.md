# Context Engineering 治理协议（Grilling 会话共识）

- 状态：设计共识已达成（2026-08-08，Q1–Q36），待按 §12 顺序实施。
- 范围：协议层保持项目无关；首个高压验证项目为 `client_search` Draft Judge。只有该项目形成真实、可复验闭环后，才允许抽取通用能力到 Core。例外：设计上项目无关、有独立设计审批、且首个落地 opt-in 的公共设施，可以直接建在 Core，不要求先等 `client_search` 闭环（首次适用：业务源漂移处理公共设施，见 `spec/grill/staleness_public_facility.md`）。
- 定位：本文规定 Investigation → Solidify → Compiler → Runtime Role → Draft Loop → Promotion 全链路的上下文治理职责、门禁和验证方式。
- 非目标：本文不要求一次性建设完整自动治理平台，不改变 Production 现有业务行为，也不允许以单 case patch 代替通用治理。
- 关联协议：Authority、Key-Index、Material Positioning、Structured Output 等协议继续各自独立生效；本文只规定它们作为上下文资产时如何被调查、固化、选择、隔离、追溯与审查。

---

## 1. 问题定义与治理目标

### 1.1 上下文污染

任何进入模型上下文、却不能安全参与当前任务决策的信息，都属于上下文污染。

“不能安全参与”至少包括：

1. 与当前 Role Objective 无关；
2. 属于其他角色、其他阶段或 Runtime-owned 对象；
3. 已被更强真相源取代；
4. 与当前有效协议互相冲突；
5. 重复注入并淹没更重要的信息；
6. 未标明来源、无法追溯或无法判断适用条件；
7. Investigation 施工建议被 Runtime 当成业务事实；
8. 冻结 Reference、Attribute 信息或其他禁止信息发生阶段泄漏；
9. 事实材料被临场 LLM 改写后以原始事实身份进入上下文。

### 1.2 优化目标

上下文治理不是单纯减少 token。目标是同时保证：

```text
较高的有效信息密度
+
围绕 Role Objective 的充分信息量
```

业务质量优先于上下文长度和调用速度。上下文缩短但准确率、召回率、证据完整性或可评价性下降，不属于成功优化。

### 1.3 已确认的首批实证问题

`client_search` Judge 已出现以下真实风险：

- `confidence` 同时被描述为标准字段和禁止字段；
- `overall_fulfillment` 在 Runtime final object 与 LLM-owned output contract 之间混用；
- `boundary` 被多个不相同的概念复用，导致模型输出形态错位；
- Structured Output Schema 被重复展开，降低有效信息密度；
- reprompt 附加错误列表和上次完整输出，放大污染；
- 项目 Markdown、Core Prompt、Draft Prompt 和解析 schema 之间存在协议漂移；
- Authority、Key-Index、Investigation/Solidify 资产的实际可用性和消费路径缺少统一可见性。

这些问题用于验证通用规则，但不得被实现成针对具体 case 或具体字符串的补丁。

---

## 2. 核心治理原则

### 2.1 每次 LLM 调用只有一个输出真相源

每次 LLM 调用必须只有一个 **LLM-owned output contract**。

- Structured Output Spec 及明确注册的 Project schema extension 是输出协议来源；
- Runtime final object、历史 Markdown、旧 Prompt 和下游派生字段不得指导模型生成额外字段；
- Project 层不得通过自由 Markdown 随意扩展输出字段；
- Runtime-owned 字段只能由 Runtime 生成或派生。

### 2.2 治理 LLM 不进入 Runtime

第一版禁止在 Runtime 中新增用于判断以下事项的治理型 LLM：

- 上下文是否充分；
- 材料是否过时；
- 材料价值与角色适用性；
- 上下文问题的责任归因；
- Context Compiler 是否应如何优化。

这些判断由 Harness AI 提前、按事件或周期性完成。

Authority、Judge、Attribute 等完成业务任务所必需的 LLM/Tool 不属于治理 LLM，不受此禁令影响。只有真实案例证明某项治理判断无法提前完成、具有强逐-case 动态性、且不能通过 Search→Load 或确定性规则解决时，才允许另行论证 Runtime 治理 LLM；不得默认加入。

### 2.3 治理判断必须固化后才能进入 Runtime

```text
Harness AI 决定“应该有什么”
→ Investigation/Solidify 将其固化为资产和消费计划
→ Runtime 确保固化要求被确定性执行
```

Harness AI 的临时分析、摘要和建议不得直接成为 Runtime 事实材料。

### 2.4 Runtime Compiler v1 不改写事实

Runtime Compiler v1 只允许：

1. 原文切片；
2. 确定性结构化投影；
3. 已登记资产的确定性选择、排序和排除；
4. 已固化 Tool/Index 计划的确定性暴露。

禁止 Runtime 临场调用 LLM 改写、概括或补全事实材料。

### 2.5 权威性属于具体 claim，不属于整份文件

不建立“代码永远高于 Spec”或“Spec 永远高于代码”的全局固定优先级。遇到冲突时必须：

1. 将冲突拆成具体 claim；
2. 识别 claim 所属裁决域；
3. 找到对该裁决域有裁决资格的来源；
4. 区分事实冲突与跨域材料误用；
5. 无法裁决时记录缺口，不强行选边。

裁决域至少包括：

| 裁决域 | 回答的问题 | 主要依据 |
|---|---|---|
| `business_obligation` | 业务上应该完成什么 | 当前有效业务 Spec、用户拍板、经 Solidify 固化的规则、必要的 Authority 裁决 |
| `live_behavior` | Production 当前实际做了什么 | 运行代码、live trace、实际 Tool/API 返回、可复现测试 |
| `llm_input_contract` | 本次模型应该看到什么 | Role 协议、Compiler 计划、隔离规则、实际 Snapshot |
| `llm_output_contract` | 本次模型必须输出什么 | 唯一 Structured Output Spec、注册的 schema extension、解析器契约 |
| `runtime_result_contract` | Runtime 最终给下游什么 | Runtime final schema、派生逻辑、下游契约 |
| `case_evaluation` | 某个 case 的合理判断是什么 | 业务义务、live 事实、Authority/Tool 证据、Reference 的形成依据 |

Reference 不是天然 Ground Truth；代码可以证明当前行为，但不能自动证明业务行为正确。

---

## 3. Harness AI 与 Runtime 的职责边界

### 3.1 Harness AI 的职责

Harness AI 属于控制面，负责目标驱动、跨样本、需要综合判断的治理。

#### A. 目标与信息义务审查

- 当前 Role 要作出哪些关键判断；
- 每个判断需要哪些信息；
- 信息来自直接上下文、Tool/Index，还是当前缺失；
- 缺失会影响哪个结论；
- 缺失是否允许进入 `unresolved/not_evaluable`；
- 模型是否承担了没有资料支撑的业务义务。

#### B. 材料适用性审查

- 材料是否仍然有效；
- 是否被更强真相源取代；
- 是否只适合 Investigation、Solidify 或其他 Role；
- 是否混合多个角色、阶段或裁决域；
- 是否需要提前切片；
- 是否应整体退出 Runtime；
- 是否与源码、schema、Spec 或 Tool 行为不一致。

#### C. Compiler 消费效果审查

- 决定性信息是否真正进入上下文；
- 条件性信息是否有可用 Search→Load 通道；
- 重要信息是否被低价值材料淹没；
- schema、协议或材料是否重复注入；
- 顺序和结构是否造成显著性偏移；
- 是否发生角色或阶段泄漏；
- 是否删掉完成任务所需的信息；
- 模型能否定位并消费依据。

#### D. 跨样本效果与责任归因

- Structured Output 失败和 reprompt 是否下降；
- Authority 是否被合理调用并产生裁决价值；
- Draft 相对 Production 的准确率、召回率和依据质量是否提升；
- 是否出现新的误报、漏报或不可评价案例；
- 问题最早出现于 Investigation、Solidify、Compiler、Candidate Role、Tool/Index 还是业务资料。

#### E. 固化与退出建议

Harness AI 可以推动：

- 新增调查方向；
- 修正或补充源材料；
- 切分混合文档并登记 segment；
- 将条件信息改为 Search→Load；
- 让被取代资产退出 Runtime；
- 修改 Project Compiler 选择规则；
- 修改 Candidate Role 的消费义务；
- 建立或修正确定性门禁。

Harness AI 不得直接改写业务事实、Reference、Production Prompt 或 Spec 并让其自动生效。

### 3.2 Runtime 的最小职责

Runtime 只做当前请求必须、能够确定性验证、每次执行均必要的约束：

- 唯一 LLM-owned output contract；
- Role/阶段隔离；
- ContextUnit/segment allowlist；
- source/segment 可追溯；
- 已固化 required asset/tool plan 的落实；
- 明确协议冲突检测；
- Context 预算与重复诊断；
- 未 Load 的材料不得被标为已获得证据；
- Structured Output 校验；
- Draft 阻断、Production 诊断。

Runtime 不自行判断业务材料是否充分，也不发明新的信息义务。

---

## 4. Context Compiler 分层协议

### 4.1 Core Compiler

Core 提供：

- 固定角色协议；
- 唯一输出协议；
- 角色/阶段隔离规则；
- 通用上下文预算和追溯协议；
- Snapshot 通用结构；
- 通用确定性扫描；
- Finding/Gate 最小协议。

### 4.2 Project Compiler

Project 提供：

- 项目业务材料选择；
- 当前 case 信号映射；
- 项目术语和边界；
- Tool/Index 可用与消费计划；
- 项目层信息义务；
- 项目特有的确定性扫描插件。

Project 可以扩展业务材料和 schema，但必须结构化注册，不得降低 Core 的隔离、证据和追溯门禁。

### 4.3 Runtime Role

Runtime Role 只对剩余未知按已固化计划执行 Search→Load。Runtime 不动态解析任意 Markdown，也不临场决定哪份历史材料更权威。

### 4.4 信息价值分类

第一版使用轻量四类，不引入复杂数值评分：

| 类别 | 含义 | 消费策略 |
|---|---|---|
| D1 | 对当前目标具有决定性作用 | 全量或确定性投影进入 |
| D2 | 条件触发后具有决定性作用 | 按触发进入，或通过 Search→Load 获取 |
| D3 | 支撑理解但非决定性 | 受预算控制 |
| D4 | 与目标无关、过时、越权或冲突 | 禁止进入 |

分类由 Harness AI 围绕目标判断，Solidify 固化稳定结果；Runtime 不逐 case 使用 LLM 重新分类。

---

## 5. 信息义务协议

### 5.1 定位

信息义务表达模型为了对自己的关键判断负责，必须能够获得哪些最低支撑。

它不是 Authority 专属协议，也不与 Key-Index 强绑定。Authority、Key-Index、直接 Context 和其他 Tool 都只是潜在的信息取得路径。

### 5.2 生命周期

```text
Harness AI 动态发现
→ 用真实案例验证
→ Solidify 轻量固化
→ Compiler/Runtime 确定性执行
```

不得一开始凭空为所有项目建立固定业务 taxonomy。

### 5.3 最小表达

每项稳定信息义务只需回答：

| 内容 | 说明 |
|---|---|
| `for_decision` | 模型准备对什么判断负责 |
| `need` | 该判断需要什么信息 |
| `obtain_via` | 可从哪个 Context segment、Tool、Index 或 channel 获得 |
| `when_missing` | 无法取得时进入 unresolved、not_evaluable 或其他已定义路径 |

示意：

```yaml
information_obligations:
  - id: result_validity_basis
    for_decision: 判断 live 返回项是否构成有效业务结果
    need: 有效结果的业务判定依据
    obtain_via:
      - context: valid_result_rules
      - tool: authority.resolve
    when_missing: unresolved
```

`obtain_via` 表达可用路径，不表示所有路径都必须调用。Authority 的触发条件必须经过案例验证后固化，不能由 Runtime 临场猜测。

### 5.4 消费约束

完整治理清单不直接塞给业务 LLM。Compiler 只投影当前 case 所需的简洁责任和取得路径。未固化的信息义务不得被 Runtime 擅自推断为必需项。

---

## 6. 材料治理与切片

### 6.1 材料审查分类

现有项目材料至少分为：

1. 有效且必需；
2. 有效但不应进入当前角色；
3. 混合用途，需提前切片；
4. 被新协议取代；
5. 与源码或实际契约不一致；
6. 重复；
7. 无法确认。

### 6.2 混合材料处理

第一版只采用提前切片：

- Investigation/Solidify 阶段识别并登记可消费原文片段；
- Runtime 只加载已登记 segment；
- 暂不允许 Runtime 动态理解并拆分任意 Markdown；
- 暂不要求所有源文件立即物理拆分。

### 6.3 资产退出

如果某项资产的有效内容已由更强真相源完整承载，或其定位与 Runtime Role 不符，该资产可以整体退出 Runtime，不要求为了兼容历史而继续保留。

### 6.4 首批重点审查材料

`client_search Judge` 第一轮至少审查：

- Core Role Prompt；
- Project Judge Prompt；
- `judge_boundary_protocals.md`；
- Draft Judge 字段禁止协议；
- Structured Output Spec 与渲染逻辑；
- Runtime final JudgeResult 定义；
- Authority/Key-Index 描述和实际可用计划；
- reprompt 内容；
- Reference、Attribute、Investigation-only 材料的阶段隔离。

对 `judge_boundary_protocals.md` 不预设整份删除，必须逐段判断其裁决域、有效性和适用角色。

---

## 7. Snapshot、Scanner 与 Harness Review

### 7.1 不建设 Harness 调查包

Context Governance 不新增：

- Harness 调查包；
- Context Audit Evidence Bundle；
- 第二套材料汇编系统。

Harness AI 直接使用：

```text
审查目标
+ Compiler 实际产物
+ Trace / Snapshot
+ 确定性诊断
+ 现有 Search→Load / 项目材料查询能力
```

需要什么材料由 Harness AI 按需查询，并保留来源与定位。

Investigation 的职责是让项目材料“找得到、查得清、追得回”，而不是预先替 Harness AI 完成全部治理判断。

### 7.2 Compiled Context Snapshot

Draft 环境必须能够保存或重建模型实际收到的上下文，至少包括：

- project、role、stage、case；
- Compiler 版本；
- output contract identity/hash；
- section 顺序、来源、segment、大小；
- Tool/Index 可用计划；
- 被排除资产及确定性理由；
- 确定性诊断；
- reprompt 是否发生及其增量大小。

默认保存可重建快照：source/segment ID、asset hash、顺序、大小和 Compiler/schema hash。

以下情况按需保存完整最终文本：

- Draft 冻结样本；
- 阻断级错误；
- structured reprompt；
- Promotion 代表性验证样本；
- 资产可能变化且仅凭 hash 无法复现。

Production 只保存 compact hash、引用、上下文规模、reprompt 状态和高优先级诊断，不保存大份完整上下文副本。

### 7.3 Deterministic Context Scanner

Scanner 不调用 LLM，至少检查：

- 是否存在多个 output contract；
- Prompt 与 schema 字段要求是否冲突；
- Runtime-owned 字段是否进入 LLM contract；
- schema 或材料是否重复注入；
- 禁止角色/阶段资产是否进入；
- source/segment 是否存在并可追溯；
- required segment/tool plan 是否落实；
- Structured Output 声明与解析器是否一致；
- Context 是否超过预算；
- Draft/Production 是否静默混用不同协议版本；
- Investigation-only/Reference-only 资产是否进入 Runtime；
- Compiler 是否违反原文切片和确定性投影原则。

### 7.4 Harness Context Review

Harness Review 只处理 Scanner 无法回答的语义问题：

- 材料是否过时、相关和充分；
- 混合材料如何切片；
- 信息义务是否合理；
- 是否存在决定性业务资料缺口；
- Authority 是否产生实际裁决价值；
- 应删减、补充还是调整消费路径；
- 问题最早属于哪个阶段；
- 修复后是否改善最终准确率和召回率。

Harness AI 不被无边界地投入整个仓库。每次 Review 必须从明确 objective、实际 Snapshot/Trace 和 Scanner finding 开始，再通过现有查询能力按需扩展。

### 7.5 逻辑组件边界

治理逻辑分为四部分：

1. Snapshot/Trace：陈述模型实际看到和做了什么；
2. Deterministic Scanner：发现可证明的协议、隔离和追溯问题；
3. Harness Context Reviewer：完成目标驱动语义审查；
4. Finding/Gate Coordinator：路由、阻断、追踪和复验。

这是职责划分，不要求建设四个独立服务。

---

## 8. Finding、责任路由与生命周期

### 8.1 Finding 最小协议

Finding 必须足以推动 Harness AI 知道哪里有问题、归谁负责、下一步改什么。最少表达：

```text
问题类型
严重级别
目标 Role/资产/组件
可追溯证据
实际影响
主要责任
协同责任（可选）
要求的改进方向
阻断阶段
当前状态
```

第一版严重级别只使用：

| 级别 | 含义 |
|---|---|
| `blocking` | 相应 Draft 阶段必须处理后才能继续 |
| `high` | 可以有限探索，但 Promotion 前必须处理或明确豁免 |
| `diagnostic` | 用于探索和趋势观察，不自动阻断 |

不引入 0–100 置信度、冗长思维过程或复杂责任权重。

### 8.2 责任路由原则

问题在哪里暴露，不等于责任在哪里。主要责任必须定位到：

> 最早一个本应阻止问题、却没有阻止问题的阶段。

允许：

```yaml
owner:
  primary: solidify
  contributing:
    - project_compiler
```

典型路由：

| 问题 | 优先责任 |
|---|---|
| 业务材料未发现 | Investigation |
| 已发现但未形成可消费资产 | Solidify |
| 混合材料未切片 | Solidify |
| 已登记但未被正确选择、排序或隔离 | Project Compiler |
| 通用 contract/schema 渲染冲突 | Core Compiler |
| Tool 调用条件未固化 | Solidify |
| Tool 和义务均正确但模型未消费 | Candidate Role |
| Tool 无法提供所需信息 | Tool/Index 或 Business Material |
| 现有资料无法闭环 | unresolved/not_evaluable，并记录所缺证据 |
| Reference 与业务证据冲突 | 复核 Reference 形成依据，不默认归错给 Draft |

确定性 Scanner 只提供事实；Harness AI 负责语义归因。

### 8.3 Unresolved 约束

证据不足时允许 `primary: unresolved`，但必须同时记录：

1. 已检查什么；
2. 为什么当前证据不能闭环；
3. 还缺什么；
4. 缺口影响哪些 case 或判断；
5. 是否允许标记 `not_evaluable`；
6. Promotion 前是否必须补足。

### 8.4 Finding 生命周期

```text
open
→ remediation_ready
→ verified
→ closed
```

必要时允许 `open → waived`，但 `waived` 不等于 `closed`。

- `remediation_ready`：修改已完成，但尚未证明有效；
- `verified`：新 Snapshot、Scanner 和代表性案例已证明修复有效；
- `closed`：验证证据归档，退出阻断集合。

最低复验证据包括：

- before/after Snapshot；
- 对应确定性扫描结果；
- 原失败案例；
- 至少一个相邻正常案例；
- 是否出现新退化；
- 是否属于通用规则而非 case patch。

---

## 9. 门禁行为

### 9.1 Draft 立即阻断

以下确定性问题直接阻断相应 Draft 阶段：

- 互斥输出协议；
- LLM contract 与 schema 不一致；
- Runtime-owned 字段要求 LLM 输出；
- 明确角色/阶段泄漏；
- required source/segment 不存在或不可追溯；
- Runtime Compiler 临场 LLM 改写事实；
- 冻结 Reference 或其他禁止信息泄漏给待测 Draft；
- Snapshot 无法重建；
- 静默混用不兼容协议版本。

### 9.2 有限探索

以下语义风险可以允许少量代表性 case 探索，但不得直接运行正式完整冻结集或进入 Promotion：

- 材料可能过时但尚无充分裁决依据；
- ContextUnit 可能造成信息淹没；
- 某项信息义务可能缺失；
- Authority 触发条件可能不合理；
- 材料可能应改为 Search→Load；
- 混合文档切片方式尚待验证。

探索必须有明确假设、保存完整 Snapshot，并限定 case 范围。

### 9.3 Unresolved 与 Not Evaluable

- 影响输出协议真实性：阻断；
- 影响关键业务裁决且无法评价：标记 `not_evaluable`，不得计入 Draft 晋升优势；
- 仅影响非关键支撑材料：允许继续并记录诊断；
- 影响少量边界案例：单列并在 Promotion 前复核；
- 大范围无法形成闭环：回流 Investigation，阻断正式 Draft Loop。

### 9.4 Waiver

允许显式、有限范围的 waiver，但不得静默删除 Finding。至少记录：

- 继续执行的理由；
- 适用范围；
- 证据；
- 失效事件；
- 是否允许 Promotion。

阻断级协议冲突原则上不得永久豁免。

### 9.5 Production

Production：

- 不改变现有业务行为；
- 不运行治理 LLM；
- 不因 Context Audit 新 Finding 中断当前线上业务；
- 只记录 compact、高优先级诊断与趋势数据；
- 将异常聚类留给后续 Harness AI 审查。

---

## 10. 运行时机

Context Governance 采用事件触发为主、Promotion 强制、日常按需的策略。

### 10.1 资产或协议变化后

以下变化触发确定性扫描，并按风险触发 Harness Review：

- ContextUnit/segment 增删改；
- 项目 Spec、业务材料或 Tool 描述变化；
- Role Prompt 或 Structured Output Schema 变化；
- Project Compiler 选择、切片或排序规则变化；
- 信息义务变化；
- Search→Load、Key-Index 或 Authority 接入方式变化。

可以使用内容 hash 避免无实质变化时重复审查。

### 10.2 Draft Loop 前

运行协议一致性、角色隔离、追溯和 required path 检查。确定性冲突先修复，避免无效跑批。

### 10.3 新错误簇出现后

Runtime 先记录 trace；当出现以下聚类时由 Harness AI 审查：

- structured reprompt 重复发生；
- Authority miss 重复出现；
- 输入尺寸显著增加；
- 某类准确率或召回率退化；
- Draft/Production 差异无法由现有证据闭环；
- 模型反复引用未提供或不存在的依据。

不逐 case 在线运行治理 LLM。

### 10.4 Promotion 前

强制完成：

- 协议一致性；
- 材料适用性；
- 信息义务覆盖；
- 跨样本业务质量；
- 未解决 Finding 汇总；
- Draft 相对 Production 的退化检查。

### 10.5 人工或周期性巡检

允许通过独立组件手动或偶尔运行：

- 怀疑上下文污染时；
- 项目长期未审查时；
- Core 协议升级后；
- 批量扫描多个项目时。

第一版不设置机械的每小时/每日 LLM 审查。

---

## 11. 验证与晋升要求

### 11.1 四层验收

1. 协议一致性；
2. 结构可靠性；
3. 业务质量；
4. 证据完整性。

业务质量优先于 token 和速度优化。

### 11.2 代表性小样本

完整 30 条冻结集之前，先覆盖：

- Authority 应调用；
- Authority 不应调用；
- Authority resolved；
- Authority unresolved；
- 首轮 Structured Output 成功；
- 历史 structured reprompt；
- Draft/Production 有差异；
- Reference 可能存在边界问题；
- 相邻正常案例不退化。

样本可重叠，不要求每种情况独占一条。

### 11.3 修复有效性的最低要求

每项修复必须证明：

```text
原错误改善
+
相邻正常行为保持
+
属于通用规则
+
未引入新的上下文污染
```

### 11.4 冻结 30 条 Draft Loop

小样本闭环成立后，才运行完整冻结集，比较：

- Draft/Production 差异；
- 差异案例中 Draft 对与 Production 对的比例；
- Draft 新增误报；
- 召回变化；
- Authority 是否提供真实裁决价值；
- unresolved/not_evaluable 是否合理；
- structured reprompt 是否下降；
- 上下文长度和耗时；
- Reference 是否存在需复核边界。

晋升遵循 Pareto 原则：最好不允许任何关键指标掉点。若 Draft 比 Production 多判错正常案例，除非召回提升足够大且该案例经证据复核确认属于 Reference/GT 边界争议，否则不得晋升。

---

## 12. 第一版实施顺序

### 阶段 1：建立实际上下文可见性

1. 盘点 `client_search Judge` 当前材料；
2. 找到实际 Compiler/Prompt 拼接链路；
3. 展示最终 section、来源、角色、阶段、顺序和大小；
4. 展示唯一 output contract；
5. 展示 Tool/Authority/Index 实际可用状态；
6. 展示 reprompt 增量；
7. 固化少量现有 trace 作为 before 基线。

此阶段先看清现状，不急于优化 Prompt，也不运行完整 30 条。

### 阶段 2：确定性扫描

优先覆盖：

- `confidence` 冲突；
- `overall_fulfillment` 所有权冲突；
- LLM output 与 Runtime result 混用；
- schema 重复注入；
- `boundary` 概念错位；
- 角色/阶段泄漏；
- source/segment 追溯；
- reprompt 放大；
- Project Markdown 非结构化扩展输出；
- Compiler 事实改写风险。

### 阶段 3：Harness AI 审查

Harness AI 从具体 objective、真实 Snapshot/Trace 和 Scanner finding 出发，按需查看当前 Spec、源码、业务材料、Authority/Key-Index、Investigation/Solidify 资产与历史 trace，形成：

- 信息义务候选；
- 材料保留/切片/修正/退出建议；
- 责任归因；
- Finding；
- 代表性验证计划。

不建立 Harness 调查包。

### 阶段 4：回到最早责任阶段修复

按 Finding 分别进入 Investigation、Solidify、Core/Project Compiler、Candidate Role、Tool/Index 或业务资料补充，不把所有问题都改成 Draft Prompt 禁止语句。

### 阶段 5：少量端到端复验

使用 §11.2 的多象限样本，检查最终 Judge 效果，而不只检查实现或 Authority 流程。

### 阶段 6：冻结 30 条验证

小样本闭环成立后运行完整 Draft Loop，并按 §11.4 比较 Draft/Production。

### 阶段 7：沉淀 Core

只有 `client_search` 证明有效后，才允许从该项目抽取通用能力到 Core：

- Snapshot 通用协议；
- Deterministic Scanner；
- Finding/Gate；
- Compiler 通用约束；
- 其他项目扫描能力。

例外（§1 范围声明）：设计上项目无关、有独立设计审批、且首个落地 opt-in 的公共设施，可直接建在 Core，不要求先等 `client_search` 闭环。已适用：业务源漂移处理公共设施（`spec/grill/staleness_public_facility.md`，2026-08-09 协解）。

---

## 13. v1 完成标准与非目标

### 13.1 完成标准

v1 成功必须证明：

1. 能重建 `client_search Judge` 的实际上下文；
2. 能确定性发现当前已知协议问题；
3. Harness AI 能围绕目标审查材料充分性与适用性；
4. 能生成证据驱动、可行动、可路由的 Finding；
5. 能用少量真实案例完成“发现 → 归因 → 修复 → 重建 → 复验”闭环；
6. 治理机制自身没有成为新的 Runtime 污染源；
7. Production 现有业务行为不被改变；
8. Context Audit 可以关闭而不影响正常 Runtime 业务执行。

### 13.2 v1 暂不要求

- 全仓库自动语义审查；
- 所有项目一次性清理完成；
- 自动修复所有 Finding；
- 自动判定 Reference 真伪；
- 每次调用实时治理；
- 复杂置信度或数值评分；
- 完整可视化平台；
- 一次性解决所有 Authority 或 Key-Index 问题；
- 为 Context Governance 新建大型调查包或材料汇编系统。

---

## 14. 最终设计摘要

```text
Harness AI：
  目标驱动地判断够不够、该怎么用、哪里有问题

Investigation：
  保证材料找得到、查得清、追得回

Solidify：
  把验证后的材料切片、信息义务和消费计划固化

Core / Project Compiler：
  确定性选择、隔离、投影、追溯和输出协议组装

Runtime：
  执行固化结果，不使用治理 LLM，不临场改写事实

Snapshot / Scanner / Finding Gate：
  让实际上下文可见、问题可证明、责任可路由、修复可复验
```

Context Governance v1 的最终判定标准是：

> 能针对真实案例形成可追溯、可归因、可修复、可复验的上下文治理闭环，并且治理机制自身没有成为新的 Runtime 污染源。
