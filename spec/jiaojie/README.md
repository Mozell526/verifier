# Verifier「Authority / Key-Index / Judge 三态」工作交接文档（详细版）

> 交接日期：2026-08-05
> 交接范围：verifier 评测系统中 **Judge 权威裁决（Authority）+ 调查索引（Key-Index）+ 判定三态（fulfilled / not_fulfilled / not_evaluable）** 这一系列设计、spec、实现与调查包现状。
> 一句话现状：**设计已收敛、核心协议已落地、client_search 调查包已按新口径重建（11 materials + 2 coverage_gaps + 2 key-indexes）；尚未跑通第一轮 30-case Draft Loop 验证**。
> 接手续读顺序：本文件 → `authority-design-issues.md`（分歧收敛记录）→ 各 spec 第一章 → 实现代码 → client_search 调查包 → 跑 loop。

---

## 0. 交接对象与阅读提示

本文件写给**接手 Authority / Key-Index / Judge 三态这条线的人**。它不是 spec 的摘要，而是：
1. 这一系列工作**在解决什么问题**（背景与历史分歧）；
2. 现在的**设计口径为什么是这样**（每个关键拍板的论证，不是只给结论）；
3. **spec 与实现、调查包三者的对应关系**（哪份 spec 落到哪段代码、哪个调查产物）；
4. 接手人**下一步具体做什么**（跑 loop → 看什么 → 改什么 → 怎么验证）；
5. 已知问题、硬约束、坑与过时文档清单。

注意：本文件里的 "spec 语义" 以 `spec/alg/*.md` 第一章为准；实现细节以代码为准；两者有出入的地方在 §13 单独列出，不要顺手改，先确认口径。

---

## 1. 背景：这一系列工作在解决什么问题

### 1.1 起点（为什么会有 "Authority" 这条线）

verifier 是业务测评系统：对被评测系统（Live）在真实业务 trace 上做 **Judge（办没办成）/ Mock（场景空间）/ Attribute（归因）** 三类判定。其中 Judge 遇到的最大问题是**"依据不足时怎么判"**：

- 有些判断点（如"某字段下游是否支持""某口语映射是否是业务认可口径""某查询形式与另一形式是否等价"）**不是 Judge 看一眼 actual 就能定的**，需要查项目的真实资料（字段定义、枚举、映射、边界文档、用户原文）。
- 早期做法是 Harness AI 在调查期直接把"结论"写出来（resolved/unresolved 的 finding），Runtime 直接消费。这套做法在 2026-07 底 ~ 08 初的模拟实验里暴露了根本问题：**调查期按"业务问题"查，但问题空间是开放的、每个 case 的问题更具体更组合，调查期根本没法穷举；且调查侧产的"结论形状"对象（findings）与运行时现场综合职责重复、互相打架**。

### 1.2 收敛过程（只保留最终结论，论证见 §12）

经过多轮讨论、模拟实验（两次大模拟：旧口径 0/6 resolved 全部 not_evaluable；正对照补证+正确分类后 6/6 resolved 且与业务期望一致），最终拍板了三条核心口径（§2），并围绕它重写了 7 份 spec、重建了 client_search 调查包、实现了 Core 侧 Authority 运行时。

### 1.3 这条线在 Draft 四阶段里的位置

```text
Investigate → Solidify → Draft Loop → Promote
Harness AI   Harness AI   Skill+协议    用户授权的协议代码
```

- **Investigate**：Harness AI 自由调查真实业务项目，交付标准调查包（manifest + overview + docs + key-index）。
- **Solidify**：把调查结果固化为 `draft/<role>.py`、ContextUnit 和 VerifiableTool。
- **Draft Loop**：在冻结条件下确定性运行 Current/Draft，Harness AI 判断是否更优、是否可 promotion。
- **Promote**：只在用户明确确认后由确定性代码搬运文件。

用户命令：`/draft start|investigate|continue|solidify|loop|test|stop|promote`。
协议入口：`spec/draft/draft.md` + `spec/alg/investigate.md`；Skill 文件 `.agents/skills/draft/SKILL.md` 与 `MAP.md`。

---

## 2. 三句核心口径（先读这个）

这三句是所有 spec 改动的锚点，任何新讨论都要先过这三句：

1. **调查层按资料调查，不按结论调查。** 交接物是"证据空间"（可物化、可检索、可追溯的原始资料），不是某个业务问题的答案。调查侧能定的只有：每份资料在什么 `conclusion_kind + scenario + conditions` 组合下直接决定什么（MaterialDecision），以及这些资料对象如何被可靠找到和加载（Key-Index）。
2. **结论整合是 Runtime Judge 的本职，不是调查层的职责。** 不存在任何"结论资产"：配对回写、结论块、缺料自动输入全部已否决。每次需要 Authority 裁决时，都由 Authority Agent 在绑定空间内现场综合；跨 case 复用只发生在两个层面——证据空间（资料物化后的 ContextUnit）和同一次 Runtime 任务内按 `decision_question` 去重。
3. **Runtime 不直接驱动调查层。** Runtime 顶多通过 `not_evaluable` + 缺料清单"提醒"（呈现 = per-case 记录缺料，评测报告汇总同类缺料）；调查层触发只能由用户手动发起。

**为什么这样收敛（一句话版）**：调查期按结论查查不完、还会伪造确定性；调查侧产结论形状对象会和 runtime 现场综合打架；runtime 回写配对是伪需求且污染调查层。详细论证见 §12。

---

## 3. 总体架构与数据流

### 3.1 一次 Judge 判定的完整链路（当前实现）

```text
case trace（用户输入 + actual + reference）
  ↓
draft/judge.py _build_core_context()
  ├─ 加载 judge 资产（boundary / business_contract / evaluation / standard / investigation）
  ├─ 压缩 capability_manifest / semantic_rules / value_mappings / enhanced_rules 进 user prompt
  ├─ build_authority_environment()   ← Core 私有组合 Authority 运行时
  │     ├─ ContextRuntime + ContextRun（证据空间：role assets + manifest evidence_refs 物化）
  │     ├─ navigation_tools（key-index：material-decisions 索引 + planfullname 枚举块索引）
  │     ├─ gateway_tools（client_search 字段认知工具）
  │     └─ environment_snapshot_sha256（项目/Role/资料 revision/工具指纹）
  └─ build_authority_resolve_tool(env)  → authority.resolve 作为 Judge 的一个 Tool
  ↓
DraftSinglePassJudgeExecution（单次 agentic LLM 会话）
  Judge LLM 遇到标准冲突 / 能力·职责边界判断点 → 调用 authority.resolve(decision_question)
  ↓
Authority Agent（authority_environment.resolve_authority）
  在绑定证据空间内 search_index → load_entry → EvidenceSpace Load → 现场综合
  → AuthorityResolution{status: resolved|unresolved, statement, reason,
                        basis_evidence_ref_ids, required_evidence}
  ↓
Judge 消费：resolved → 按 §8.3 分支；unresolved → not_evaluable（依据不充分）
  把 tool_call_id 写入 assessment.authority_tool_call_ids
  ↓
draft/judge_execution.py judge_trace() 尾部
  apply_authority_gate(result, authority_tool.audit)   ← Core 后处理硬校验
    · 引用不存在 → needs_human_review
    · unresolved → not_evaluable
    · not_evaluable 但成因缺"结论类型："标记 → needs_human_review
  ↓
JudgeResult（fulfilled / not_fulfilled / not_evaluable）
```

### 3.2 调查包 → 运行时的交接（资产流）

```text
/draft investigate 产物（client_search/judge）：
  manifest.json（evidence_refs ×11, tool_requirements ×3, key_indexes ×2, artifact_refs）
  docs/judge-investigation-contract.json（BusinessExpectation / LiveBoundary / EvaluationDimension）
  docs/authority-investigation-report.json（materials ×11, coverage_gaps ×2）  ← 真相源
  docs/authority-investigation-report.md（JSON 确定性渲染，不得手改）
  docs/evidence/authority-conflicts-scan.md
  ↓ Solidify
project.yaml role_assets 登记（judge_investigation 等 asset，production/candidate 双路径）
  ↓ build_authority_environment（运行时）
role_asset_context_records + _materialize_manifest_evidence_refs → ContextUnit registry
  ↓ build_authority_key_index_registry
manifest.key_indexes → navigation tools（search_index / load_entry），带 Target Resolver
  ↓ Judge LLM
authority.resolve 工具（内部再走 search/load/load_context_units）
```

---

## 4. Spec 地图与每份 spec 的详细要旨

### 4.1 总表

| Spec | 职责 | 章节结构 | 最近变化 |
|---|---|---|---|
| `spec/alg/investigate.md` | Draft 前置调查与固化的总协议：调查包目录、Manifest、ToolRequirement、EvidenceRef、Key-Index 策略探索与召回资产固化、ContextUnit 接入 | §1 协议主体（含 1.9 Schema 流与固化 / Key-Index 策略探索 / Key-index 目标固化）、§2 现有协议差异 | 加入 §1.9 Key-Index 策略探索与召回资产固化 |
| `spec/alg/investigate-judge.md` | Judge 调查协议：**BusinessExpectation / LiveBoundary / EvaluationDimension** 三对象；Planning 与 Authority Gate | §1-5（含 §5.2 Authority Gate 与 Task 8 约束引用 material-positioning） | 与 authority/positioning 口径对齐 |
| `spec/alg/investigate-authority-judge.md` | **调查侧**权威协议：资料轴心调查、MaterialInvestigation / MaterialDecision / MaterialConnection / CoverageGap、AuthorityInvestigationReport、缺口补证循环、运行时交接 | 第1章调查方法论 §1-5；第2章资料轴心 §6-15；第3章与运行时交接 §16-19；第4章案例 §20-21；第5章泛化 §22-23；第6章改造边界 §24-26 | `findings` 删除 → `CoverageGap`；报告以 `materials` 为第一组织维度 |
| `spec/alg/authority.md` | **运行时** Authority Agent 协议：`authority.resolve`、AuthorityRequest / AuthorityResolution、宿主无关 Ports、判断顺序、调用方消费规则、Core 后处理硬校验 | 第一章长期协议 §1-10；第二章设计矛盾/裁决记录 §11-20；第三章改造边界 §21-23 | §6 调查侧不产出配对；§8 后处理硬校验（tool_call_id 引用审计）；§8.5 Runtime 不主动补证 |
| `spec/alg/fulfilled.md` | 三态判定：`fulfilled / not_fulfilled / not_evaluable`；四成因（职责外/完全无关/依据不充分/输入坏） | 第一章 §1-9（三态定义、判断顺序、常见场景、核心原则）；第二章现状差异与改造任务 | 与 authority/positioning 口径对齐 |
| `spec/alg/material-positioning.md` | **资料定位**：conclusion_kind 四值（normative_rule / external_fact / current_behavior / inlive_boundary）+ Gate + 信任模型登记 | 第一章定位框架 §1-3；第二章四值与 Gate §4；第三章信任模型 §5；第四章区分 §6-7；第五章防滥用 §8 | 新起 spec（2026-08-04/05） |
| `spec/alg/investigate-keyindex.md` | **通用 Index 协议**：对象/集合/包含/索引/entry、Index Catalog、`search_index` / `load_entry` 工具合同、Target Resolution、构建方式、应用层 | 第一章协议定义 §1-6；第二章索引构建 §7-9；第三章应用层 §10-12 | 完全重写（2026-08-05） |

### 4.2 `investigate-authority-judge.md` 要点（调查侧）

- **§2 核心原则**：
  - 2.1 权威不是标签，是因果分析的结论（不许给源贴静态优先级）；
  - 2.2 唯一决定性：Authority 来自"资料在什么条件下唯一决定什么"；
  - 2.3 资料轴心，不预设观点；
  - 2.4 Schema 驱动调查，而非记录结论。
- **§6 四步主链**：登记 EvidenceRef → 逐个资料调查 → 形成 MaterialDecision/MaterialConnection → 记覆盖缺口。
- **§8 MaterialInvestigation**：一份资料的完整调查记录；8.1 "直接决定 vs 仅相关"二元对立（`decisions` vs `related_to`）。
- **§9 MaterialDecision**（见 §5 词典）：`conclusion_kind + governs + statement + locator + scenario + conditions`；唯一性只在 `conclusion_kind + governs + scenario + conditions` 组合内成立；governs/statement/locator 三者不得混淆；locator 可直接作为 keyindex entry 的 target_ref（entry.key 只是索引内编号）。
- **§10 MaterialConnection**：direction（upstream/downstream/peer）+ relation（dependency / derived_from / validated_by / supersedes / conflicts_with）+ effect；derived_from/validated_by 必须指向真实 EvidenceRef。
- **§11 CoverageGap**（覆盖缺口，替代 findings）：见 §5 词典；11.1 需求侧方向只作说明性标签（dimension_ids → EvaluationDimension → expectation_ids 关联链）；11.2 conclusion_kind 业务边界引用 material-positioning.md；11.3 判定规则（恰好一个 Decision → 覆盖成立；多 Decision 条件互斥 → 覆盖成立；重叠无法消解 → 记缺口；无适用 Decision → 记缺口）。
- **§12 AuthorityInvestigationReport**：以 `materials` 为第一组织维度；含 business_scope、materials、coverage_gaps；不含任何 case 的 actual/score/verdict。
- **§13 缺口补证循环**：Harness AI 产出缺口 + required_evidence → 校验层确定性校验 → 同轮定向补证；冻结条件 = 缺口被消解或所有方向已跟进并记录停止原因。
- **§14 Validator**、**§15 产物位置**（`draft/investigation/<role>/` 下，JSON 为真相源，MD 由 render 脚本生成）。
- **§16 运行时交接**：证据空间 + 现场综合；**§17 缺口反馈**：Runtime 只提醒，调查只由用户手动触发；**§18 调查报告的物化**；**§19 变更与重查边界**。

### 4.3 `authority.md` 要点（运行时）

- **§2 职责边界**：Authority 负责"确定一个明确业务问题的可靠结论"；不负责生成 BusinessExpectation、不判断 fulfilled/not_fulfilled、不输出 verdict/score/confidence/overall、不发明资料优先级、不把当前代码行为自动当正式标准、不用模型常识补结论。
- **§3 调用形态**：`authority.resolve(decision_question)` 是对其他 Runtime LLM 暴露的 Tool；`ToolResult.status`（是否成功执行）≠ `resolution.status`（业务 resolved/unresolved）；工具失败不能被改写成业务 unresolved。
- **§4.1 AuthorityRequest**：只一个字段 `decision_question`（自包含业务条件）。
- **§4.2 宿主无关 Ports**：EvidenceSpace / Materializer / ToolGateway / PermissionBoundary / EnvironmentSnapshot；verifier Adapter = `AuthorityEnvironment`（Core 私有组合对象，主 LLM 不能选择或扩大）。
- **§4.3 AuthorityResolution**：`status / statement / reason / basis_evidence_ref_ids / required_evidence`。
- **§5 判断顺序**：7 步；resolved 最低要求（statement/reason/basis 非空、可回真实文件/artifact/物化 ToolResult/人工澄清、不超条件、冲突要说明决定性）；unresolved 最低要求（statement 空、reason 具体、required_evidence 非空、已发现资料或冲突必须进 basis）。
- **§6 与 Investigate 的非硬依赖串联**：调查包为 Authority 准备可发现可加载可验证的环境；"可选"指调查层产出可选（不要求每次调查都产 Key-Index），不是 Authority 工作方式可忽略；调查侧不产出配对、Runtime 不沉淀结论资产；Index Catalog 暴露规则、检索通路规则、target_ref/load_targets 消费规则、navigation ≠ evidence。
- **§7 Runtime 调用规则**：相同 decision_question + snapshot 在单次任务内去重（cache）。
- **§8 调用方消费规则**：
  - 8.1 能力/职责边界裁决必须走 Authority（不得自行断定"职责外/职责内能力缺失"）；
  - 8.2 decision_question 构造模板（"<产品/模块> 是否支持 <能力>？/<事项> 是否属于 <产品> 职责？"；不得把 live 输出/reference/Judge 期望写进问题）；
  - 8.3 resolved 分支消费（职责外→not_evaluable；职责内能力缺失→结合实际交付；职责内正常→继续）；职责内能力缺失 + 期望未达成 → not_fulfilled 并注明长期优化点，不降级；
  - 8.4 Core 后处理硬校验（apply_authority_gate）：tool_call_id 引用审计、unresolved→not_evaluable、成因标记、needs_human_review；
  - 8.5 Runtime 不主动补证（不自动启动调查）。
- **§9 中文案例**：客户搜索中的业务词映射。
- **§10 Validator 与审计要求**；**§11-20 设计矛盾与裁决记录**（§14.2 调查单位、§14.3 "特殊 Case" vs "通用问题类型"、§16 调用次数、§18 当前代码与协议已知不一致、§19 不得默认的结论、§20 实施前裁决顺序）。

### 4.4 `fulfilled.md` 要点（三态）

- **§2 三态定义**：fulfilled（办成了，职责内+材料够+证据能证明结果拿到）；not_fulfilled（职责内、期望明确没达成、责任在系统）；not_evaluable（该给说法但材料不够；四成因：职责外/完全无关/依据不充分/输入坏）。
- **§2.3 三个硬前提**（防垃圾桶）：1) 查证真的激活过（authority 机制真实跑过、有调用记录）；2) 必须写清"差在哪儿"和缺料清单；3) 临时态，挂限期关闭。
- **§3 判断顺序**：第一步用户要什么（结果/答复/处置/完全无关）；第二步职责与能力由 authority 裁决；第三步系统实际交付了什么。第二步的约定：authority 裁决依据是实际 Load 的原始资料；MaterialDecision 只是证据索引；reference/badcase 标注不可盲信。
- **§4 常见场景**：4.1 "查不了"类（职责外→说不清；依据不充分→说不清；职责内本可支持却没给→没办成）；4.2 漏了/做错了→没办成；4.3 等价替代→办成了；4.4 外部原因→不怪系统（必须有实据）；4.5 该回结果没回→没办成。
- **§5 核心原则**：用户要的是结果不是"被礼貌告知办不了"；不允许把没办成/说不清包装成办成了。
- 第二章：现状差异与一次性改造任务（反面情况 11 条、验收）。

### 4.5 `material-positioning.md` 要点（资料定位）

- **§2 唯一判定轴：独立性**（资料所陈述内容是否独立于被测系统，不由系统自身行为/配置决定）；打标依据是独立性不是出处。
- **§3 2×2 + 接缝格**：

```text
| 站位 \ 说法 | 说"应该"（规定性） | 说"是"（描述性） |
|---|---|---|
| 独立于被测系统 | normative_rule（独立尺子） | external_fact（独立现实） |
| 被测系统自己 | 故意留空（防循环不变量） | current_behavior（被量的东西） |
| 接缝：出处在系统内、内容指向外部边界 | 不适用 | inlive_boundary（边界代理） |
```

- **§4 四值与 Gate**：current_behavior 不能解除正式规则 Gate；normative_rule/external_fact 可以；inlive_boundary 有条件。信息关系唯一排序：`normative_rule / external_fact > inlive_boundary > current_behavior`。
- **§4.1 inlive_boundary 打标判据**：陈述对象是 Live↔外部边界上的可达空间（字段/枚举值/操作符/值映射目标值空间）；该空间由下游/外部决定；项目已登记信任模型且 conditions 可回指。反例：解析规则、时间换算、归一选择、prompt/路由配置 → 仍是 current_behavior。
- **§5 信任模型登记**：M0（默认：外部信息）与 M1（受控输出空间）；C1-C6 判定清单；登记形式（项目级边界文档 + 材料级 conditions 引用 + 校验层核对）；失效条件 R1-R3；**reference/参考答案不构成信任根**。
- **§6-7 与相关概念区分**：LiveBoundary（归责给谁）≠ inlive_boundary（这份资料能当什么证据）；Authority 能力/职责边界裁决消费 inlive_boundary 资料；locator/target_ref 是物理定位、positioning 是语义分类。
- **§8 防滥用禁令**：不得乱标 inlive_boundary 绕过 Gate；不得用它裁决 normative 问题或"本次选得对不对"；不得掩盖漂移；权威不来自行为自我背书。

### 4.6 `investigate-keyindex.md` 要点（通用 Index 协议）

- **§1 目标**：把一个无法直接完整装入上下文的对象集合转换为可检索、可定位、可加载的入口层；解决 5 类问题（大型资料读不动、产物多找不到、各项目私有搜索工具、检索结果与真实资料缺稳定导航、Runtime 不知道有哪些 index_key）。只负责发现候选和定位目标，不解释业务含义、不产生业务结论。
- **§2 基本概念**：对象/集合/包含/索引/entry/Index Catalog；递归关系（material 是对象，包含字段集合，字段是子集合对象）。
- **§3 核心语义**：3.1 索引是定位和提取不是切碎（内容本体完整原样，load_entry 按位置提取）；3.2 entry 与对象不一一对应（多入口是特性）；3.3 target 粒度任意（完整对象/内部部分/容器）；3.4 **索引不是结论**（命中≠事实成立、未命中≠不存在、索引条目≠原始证据、候选集合≠权限白名单）。
- **§4 设计边界**：不判断权威/resolved/三态、不生成 AuthorityResolution、不让 Runtime 修改调查层资产、不固化"问题→结论"复用资产。
- **§5 Schema**：`InvestigationKeyIndex{index_key, collection_ref, target_kind, entry_granularity, retrieval_channels, default_retrieval_channels, entries}`；`InvestigationKeyEntry{key, name, search_text, target_ref}`；字段约束（唯一性、search_text 必须是 target 真实内容的确定性投影、禁止 AI 补充同义词、target_ref 必须能解析到真实对象、不写 ContextUnit ID、entry 不携带 Authority status/verdict/expected answer、Catalog 不带 use_when/next_index/priority）。
- **§5.1 Retrieval Channel**：exact / lexical / embedding；命中只产生导航候选；embedding 是补充召回能力，不天然取得排序/适用性/裁决权；大型枚举成员判定优先 exact lookup；向量命中保留模型与投影版本运行记录但不要求写进 manifest。
- **§6 工具合同**：6.1 Index Catalog 暴露（V1 不要求新增 list_indexes Tool，通过 search_index 的 metadata/description 暴露）；6.2 `search_index`（输入 index_key/query/limit/channels；输出候选 entry；保留 matched_channels；不返回完整目标正文）；6.2.1 可选 Candidate Selection/Rerank（只决定加载优先级和预算裁剪）；6.3 `load_entry`（一次一个明确 entry；禁止空 key/通配符/超大 limit；resolved target 必须来自 target_ref 对应真实对象；`load_targets` 是协议级顶层字段）；6.4 Target Resolution（只做地址解析，不判断 resolved/三态；不得扩大权限；不得模糊搜索猜测；解析为空/无权限/locator 失效是导航/环境事实，不得自动解释为资料不存在）；6.5 Receipt（可追溯 index_key/key/target_ref/resolved locator/load target/实际 Load 的 unit）。
- **§7 构建职责分工**：探索边界（调查层+Builder+校验层）/ 生成 projection（确定性 Builder，禁止 AI）/ 选择召回通路（调查方案+校验层）/ 物化检索实现（Solidify/Core）/ 验证把关（校验层）。7.1 **Index 策略是调查结论**：selected / no_index / unresolved 三态。
- **§8 构建方式**：8.1 资料原生索引（结构已知，确定性构建）；8.2 大型资料探索构建（结构未知，Harness AI 探索边界但 search_text 仍由真实内容确定性投影）；8.3 调查投影索引（已有对象，如 MaterialDecision）；8.4 不适合建索引的集合（no_index 合法）。
- **§9 Validator**：通用 + 应用级。
- **§10 应用模式**：同一协议用于不同集合边界（Index A 全 material / Index B material 内部字段），不建立固定 A→B 父子链。
- **§11 应用一：大型资料内部检索**（planfullname 枚举块示例）。
- **§12 应用二：集合层 material 能力导航**：MaterialDecision 投影为 capability index → Runtime search_index → load_entry → Target Resolver → EvidenceSpace Load → 现场综合；约束：MaterialDecision 是可导航的资料能力描述不是跨 case 结论资产；CoverageGap 不自动进 index；Search 未命中不能直接 unresolved；候选集合不是权限白名单。

---

## 5. 关键概念词典（含"为什么这样设计"）

| 概念 | 定义 | 为什么这样设计 |
|---|---|---|
| **证据空间（EvidenceSpace）** | 调查资料物化后的可寻址、可追溯、可加载的 ContextUnit 集合（含 hash/版本校验） | 交接物必须是"可物化、可检索、可追溯"的原始资料，才能跨 case 复用且可审计 |
| **MaterialDecision** | 一份资料里"一句陈述"的能力声明 = 在 `conclusion_kind + scenario + conditions` 组合下，这份资料直接决定什么（`governs`）；statement 是该资料对事项的具体说法；locator 是核验位置 | 它是**证据索引/预判**，不是裁决依据；裁决依据永远是实际 Load 的原始资料。这样调查层可以提前产出（不依赖具体问题），又不会冒充结论 |
| **MaterialConnection** | 资料之间的实质连接（dependency/derived_from/validated_by/supersedes/conflicts_with + effect） | 冲突消解必须落在材料层的可核验关系上，不能靠"优先级更高"这种标签 |
| **CoverageGap** | 调查侧的确定性事实："某业务事项 × 条件没有唯一决定资料 / 重叠无法消解"，带 gap_reason 与 required_evidence | 它是材料层可核验的事实（"没有 MaterialDecision 管 X"），不是对某个业务问题的结论；是 findings 被删除后的替代物 |
| **conclusion_kind 四值** | normative_rule（独立尺子，规定性）/ external_fact（独立现实，描述性）/ current_behavior（系统自己，描述性）/ inlive_boundary（边界代理，有条件） | 唯一判定轴是"是否独立于被测系统"；inlive_boundary 解决"系统内配置描述外部边界空间"的接缝问题 |
| **inlive_boundary** | 真边界不可观测时的可达代理：字段空间/枚举值空间/操作符空间/值映射目标空间；须项目登记信任模型 M1 + conditions 可回指 | 没有它，系统内配置要么被误当 external_fact（在出处上说谎），要么被 Gate 卡死（current_behavior 不能裁决规范问题） |
| **信任模型** | M0（默认：外部信息）/ M1（受控输出空间：业务方声明"系统内空间=下游边界代理"）；C1-C6 判定；R1-R3 失效条件 | inlive_boundary 是条件定位，必须"用户同意"才启用；reference/伪参考答案不构成信任根 |
| **Key-Index** | 通用导航协议：对象集合 → Index + Index Catalog → search_index → 有限候选 entry → load_entry → 真实对象（或一部分/子集合） | 解决"找得到、读得动"；不解决"资料本身是不是 normative/external" |
| **entry / key / search_text / target_ref** | entry=索引中可检索入口；key=索引内唯一编号；search_text=target 真实内容的确定性投影（不是 runtime query、不是证据）；target_ref=稳定逻辑目标引用（对象 ID / 对象内部 locator / 容器引用） | entry.key 不是 locator；承担定位职责的是 target_ref。search_text 禁止 AI 生成/补充同义词，必须是确定性投影 |
| **load_targets** | Target Resolver 在当前运行环境内解析出的零到多个受权限约束的短期加载地址 | 把"稳定逻辑地址"与"运行时物化地址"分离；调查包不写 ContextUnit ID |
| **Index Catalog** | 当前权限空间内可用 Index 的结构化登记（index_key/collection_ref/target_kind/entry_granularity），不暴露 entry/search_text | 解决 Index Discovery；Runtime 不得猜测 Catalog 中不存在的 index_key |
| **AuthorityRequest** | `decision_question`：一个完整自包含业务条件的裁决问题 | 最小输入；资料空间由 Environment 绑定，不由请求决定 |
| **AuthorityResolution** | `status( resolved|unresolved ) + statement + reason + basis_evidence_ref_ids + required_evidence` | 通用输出；resolved 必须带可核验 basis；unresolved 必须带缺料清单 |
| **basis_evidence_ref_ids** | 只允许引用本会话实际 Load 过的物化 unit_id（authority-ref-* / authority-case-*），hash 未变 | 防止 LLM 凭记忆编造 unit_id；search/load_entry/导航内容都不是 basis |
| **authority_tool_call_ids** | Judge assessment 里对 authority.resolve 真实调用的 tool_call_id 引用 | Core 后处理只认真实调用记录；数字 id / resolution.N@hash 是伪造引用 → needs_human_review |
| **三态四成因** | fulfilled / not_fulfilled / not_evaluable；not_evaluable 成因=职责外/完全无关/依据不充分/输入坏 | authority 管②（能力/职责边界裁决），Judge 管①③（用户意图+实际交付）并消费② |
| **not_evaluable 缺料清单** | per-case 记录 AuthorityResolution.unresolved.required_evidence → Judge reason/required_evidence | 呈现载体；评测报告汇总同类缺料 → 人手动触发下一轮调查 |

---

## 6. 运行时链路：代码级走查

### 6.1 文件地图

| 文件 | 行数 | 职责 |
|---|---|---|
| `impl/core/schema/authority.py` | 60 | 公共协议：AuthorityRequest / AuthorityResolution |
| `impl/core/authority_environment.py` | 1144 | AuthorityEnvironment 组合对象、构造器、证据空间物化、系统 prompt、resolve_authority 主流程 |
| `impl/core/authority_tool.py` | 122 | AuthorityTool（authority.resolve 的 VerifiableTool 封装、cache、tool_failure） |
| `impl/core/authority_gate.py` | 210 | apply_authority_gate：Judge result 后处理硬校验 |
| `impl/core/authority_key_index.py` | 311 | MaterialDecision 能力索引 + evidence-navigation target + lexical 检索默认实现 |
| `impl/core/investigation_key_index.py` | 354 | 通用 Key-Index Registry / search / load / catalog / receipt / 工具构造 |
| `impl/tools/protocol.py` | 280 | VerifiableTool / ToolResult / build_agno_tools |
| `impl/projects/client_search/draft/judge.py` | 1299 | Draft Judge 实现：_build_core_context、system_extras、operator gate |
| `impl/projects/client_search/draft/judge_strategy.py` | ~45 | DraftSinglePassJudgeExecution（单次 agentic 会话） |
| `impl/projects/client_search/draft/judge_execution.py` | ~620 | judge_trace：LLM 调用、self-check、reprompt、authority gate 消费 |
| `impl/projects/client_search/draft/build_authority_key_index.py` | 130 | 确定性重建 manifest 的 key_indexes（material 索引 + planfullname 枚举块索引） |

### 6.2 `build_authority_environment()` 构造流程（authority_environment.py:795）

```text
1. _build_context_runtime(spec, role, use_candidate)   ← 需要 runtime_config.embedding.enabled=true
2. role_asset_context_records(spec, role, ...)          → 当前 role 的 assets（boundary/contract/evaluation/standard/investigation）
3. runtime.register_context_units(asset_records)
4. _materialize_manifest_evidence_refs(spec, runtime)   → 把 manifest evidence_refs 物化为 ContextUnitRecord
5. _invalidate_stale_evidence_refs(...)                 → hash 变化的旧证据失效
6. evidence_unit_ids = {ref_id: unit_id}（单映射的 ref）
7. role=="judge" 且恰好 1 个 investigation asset 时：
   load authority-investigation-report.json + manifest.json
   → create_authority_navigation_tools(report, evidence_unit_ids, indexes=manifest.key_indexes,
        load_target_resolver=_build_evidence_load_target_resolver(manifest_records, run))
8. _contextualize_gateway_tools(...)                    → 授权 VerifiableTool（Agno 化），结果可回填物化
9. permission_boundary = {project_id, caller_role, asset_source, context_unit_count, ...}
10. snapshot = _sha256({protocol_version, project_id, caller_role, use_candidate,
       asset_fingerprints, evidence_fingerprints, tool_fingerprints, registrations})
```

关键点：**主 LLM 不能选择或扩大这个空间**；snapshot 覆盖项目/Role/资料 revision/工具指纹，是 cache 与审计的依据。

### 6.3 `resolve_authority()` 主流程（authority_environment.py:1008）

```text
1. 组装 tools = [load_context_units_tool, *navigation_tools, *gateway_tools]
2. llm = project_llm_client(...) 或传入的 llm；client._caller = "authority"
3. output_spec = StructuredOutputSpec.from_dataclass(AuthorityResolution,
       required_nonempty=["status","reason"])
4. user = {"decision_question": question, "environment_snapshot_sha256": snapshot}
5. data = client.complete_json(_resolve_system_prompt(env), user, ...)
6. data.get("error") → 显式抛 RuntimeError（执行失败，不许伪装成业务解析错误）
7. status ∈ {resolved, unresolved} 校验
8. basis 校验：对每个 ref，materialized_unit_id_for_selection_ref(ref) or ref
   → env.ref_loaded_unchanged(unit_id) 不过滤掉 → invalid_basis
9. resolved 且缺 statement/reason/basis → 归一化为 unresolved（依据不充分），不伪装成执行失败
10. unresolved 且 statement 非空 → 并入 reason、statement 置空
11. unresolved 且无 required → 默认 "补充可裁决该判断点的权威资料（当前依据不充分，无法定论）"
```

系统 prompt（`_resolve_system_prompt`）关键约束：
- 判断顺序 7 步；Context Load 预算（每次最多 8 个 selection_ref，优先 1-2 个）；
- resolved 最低要求（basis 只能引用本会话实际 Load 的物化 unit_id，逐字符原样复制）；
- 能力/职责边界类问题 statement 必须明确结论类型（职责外/职责内能力缺失/职责内正常）；
- unresolved 最低要求（statement 空、required_evidence 非空）；
- 导航工具提示：命中≠事实，未命中≠不存在；首次未命中必须至少改写一次 query 重试；load_entry 返回的 load_targets 必须优先执行 Context Load，不得对同一 locator 无理由退回模糊 Search；load_entry 的 decision 不能直接写进 basis。

### 6.4 `AuthorityTool._execute`（authority_tool.py）

```text
cache key = (question, environment_snapshot_sha256)   ← 同问题+同 snapshot 单次任务内去重
call_id = "authority.<project>.<hex12>"
异常 → audit[call_id] = {request, tool_failure: True, error, snapshot}
        result = {status: "tool_failure", statement: "", reason: "Authority 能力不可用（执行失败）...", ...}
正常 → audit[call_id] = {request, resolution, snapshot}
        result = {tool_call_id, status, statement, reason, basis_evidence_ref_ids, required_evidence}
```

### 6.5 `apply_authority_gate`（authority_gate.py:88）

```text
对每个 fulfillment_assessment：
  call_ids = assessment.authority_tool_call_ids
  ne_cause = _classify_not_evaluable_cause(assessment)   ← 只认"结论类型："显式标记
  - not_evaluable 且成因未识别 → 挂 needs_human_review（不静默放行）
  - 引用 audit 之外的 tool_call_id → needs_human_review
  - 引用存在且 resolution=unresolved → assessment 状态强制 not_evaluable，
    把 resolution 的 EvidenceRef 与原因挂入 evidence 链
  - 引用存在且 resolution=resolved → 不覆盖（Judge 已用 statement 与 basis 继续评价）
  - 伪造引用形态（纯数字 / resolution.N@hash12）→ 诊断提示 + needs_human_review
```

成因标记表：`结论类型：输入坏` / `结论类型：完全无关` 是豁免类（exempt，不需要 authority 引用）；`结论类型：职责外` / `结论类型：依据不充分` / `结论类型：Authority 能力不可用` 是触发类（requires_authority，必须有真实调用记录）。

### 6.6 Draft Judge 的 authority 消费（judge.py / judge_execution.py）

- `_build_core_context`（judge.py:972）：构造 authority_env + authority_tool，把 `authority.resolve` 加入 Judge 的 tools；system_extras 注入大量"Authority 使用规则"（§8.1/§8.2 模板、不得自行断定职责外、resolved 分支消费、unresolved→not_evaluable、tool_call_id 填写、工具失败不能伪写成 unresolved 等）。
- `_apply_operator_capability_check`（judge.py:837）：确定性 operator gate——actual 操作符与清单冲突时，有 authority 引用则由 Authority/Judge 结论决定；没有引用则 fail-closed 到 not_evaluable + 人审标记。
- `judge_execution.py:602`：`result = apply_authority_gate(result, tool_audit)`；随后把 `{source: "authority_runtime", environment_snapshot_sha256, tool_call_ids}` 追加进 result.evidence。

### 6.7 Key-Index 运行时（authority_key_index.py / investigation_key_index.py）

- `build_material_decision_key_index(report)`：把 report.materials 的每个 decision 投影为 entry（key=`<source_ref_id>.decision-<n>`，target_ref=`material-decision://<source_ref_id>/<n>`，search_text = conclusion_kind + governs + statement + scenario + conditions 的拼接）。
- `lexical_material_decision_search`：小型确定性默认检索（词项重叠 + phrase/name bonus），项目可替换。
- `_evidence_navigation_target`：解析 `evidence-navigation://<source_ref_id>/<locator>` → content（navigation_only）+ load_targets（通过 load_target_resolver）。
- `InvestigationKeyIndexRegistry.search/load`：search 返回 KeyIndexSearchHit + receipt；load 校验 entry 存在、调用 resolver、返回 content；load 禁止空 key/通配符。
- `create_key_index_tools`：把 search/load 包成 Agno tools（`search_index` / `load_entry`），receipt 记录 operation/index_key/key/query/target_refs/load_targets。

---

## 7. client_search 调查包现状（逐条）

### 7.1 manifest.json（`draft/investigation/judge/manifest.json`）

- `schema_version: 2`，`project_id: client_search`，`role: judge`，`source_revision: 0b65fad1...`（client_search 业务源库 revision）。
- **evidence_refs ×11**：
  1. `project-judge-boundary`（judge_boundary_protocals.md，AI 落地投影）
  2. `project-judge-boundary-source`（judge_boundary-template.md，**用户原文 + 信任模型登记**）← 关键：用户原文必须作为 normative 证据登记
  3. `project-evaluation-contract`（evaluation.md）
  4. `current-judge-standard`（judge.md，current 系统行为）
  5. `current-project-config`（project.yaml，current 系统行为）
  6. `business-field-definitions`（field_definitions_args.yaml）
  7. `business-field-enums`（field_enums_args.yaml）
  8. `business-value-mappings`（value_mappings_args.yaml）
  9. `business-enhanced-rules`（enhanced_rules_args.yaml）
  10. `business-time-knowledge`（time_knowledge_args.yaml）
  11. `business-planfullname-enums`（polNoInfo.plancodeinfo.planfullname_enums_args.yaml）
- **tool_requirements ×3**：
  - `client_search.condition_compare`（**已实现**：search_condition_compare.py，确定性比较 oracle conditions 与 actual conditions）
  - `client_search.es_enum_observation`（**implementation_gap**：没有只读 ES 聚合/DB 权限）
  - `client_search.query_result_equivalence`（**implementation_gap**：下游没有稳定快照比较接口）
- **key_indexes ×2**（由 `build_authority_key_index.py` 确定性重建）：
  - `authority.material-decisions`：collection=authority-investigation-report，target_kind=material_decision，entry_granularity=investigated_statement，**14 entries**（11 materials 的 14 条 decision）
  - `material.business-planfullname-enums.values`：collection=business-planfullname-enums，target_kind=evidence_locator，entry_granularity=yaml_list_range，**74 entries**（planfullname 枚举按 100 个一块切，locator 如 `values[7300:7342]`）
- `artifact_refs`：authority report JSON + MD、judge-investigation-contract 等。

### 7.2 authority-investigation-report.json（11 materials + 2 coverage_gaps）

**materials（每份资料含 1-2 条 MaterialDecision）：**

| # | source_ref_id | decision 数量 | conclusion_kind / governs 摘要 |
|---|---|---|---|
| 1 | current-project-config | 1 | current_behavior：parser 当前声明的字段/枚举/映射配置集合（current 行为基线） |
| 2 | project-judge-boundary | 1 | current_behavior：parser 与外部数据库/搜索服务的责任划分（AI 落地投影，upstream derived_from 用户原文） |
| 3 | project-judge-boundary-source | 2 | normative_rule：① 责任边界（可评价范围/不可评价范围/外部依赖责任/限制条款，用户原文）；② **信任模型登记 M1**（配置/枚举资料为下游能力空间代理） |
| 4 | project-evaluation-contract | 1 | current_behavior：Judge 判断的输入重建方式（按当前请求/actual/可用下游证据重建，不继承历史答案） |
| 5 | current-judge-standard | 1 | current_behavior：Judge 三态判断与证据要求标准（peer dependency: current-project-config） |
| 6 | business-field-definitions | 2 | ① **inlive_boundary**：下游可承载的字段空间与操作符空间（M1；含 familyclientbirthday MATCH/RANGE 冲突面）；② current_behavior：意图→查询条件的换算规则 |
| 7 | business-field-enums | 1 | **inlive_boundary**：字段的可枚举值空间（M1；onlyShareClientFlag 仅 Y） |
| 8 | business-value-mappings | 2 | ① **inlive_boundary**：口语映射的目标值空间（M1）；② current_behavior：口语别名→归一值的归一选择 |
| 9 | business-enhanced-rules | 1 | current_behavior：复杂口语模式的解析规则（正则 + merge_to_llm） |
| 10 | business-time-knowledge | 1 | current_behavior：相对时间口语→日期区间换算口径 |
| 11 | business-planfullname-enums | 1 | **inlive_boundary**：产品全称的可枚举值空间（M1） |

**coverage_gaps ×2：**

| gap_id | conclusion_kind | governs | gap_reason | required_evidence |
|---|---|---|---|---|
| semantic-mapping-authority | normative_rule | 口语表达多合理映射且无法唯一选择时，哪个映射是业务认可语义？ | 映射规则/历史案例/字段能力清单产生与生效流程不同；无受治理术语表或业务确认记录 | 业务方认可的澄清规则或标准术语表 |
| query-form-equivalence-authority | external_fact | 不同查询形式是否等价？ | 静态等价规则与真实查询结果由不同链路产生；缺少固定快照双查询比较 | 固定数据快照上的只读双查询比较能力；业务确认的封闭式等价规则 |

### 7.3 judge-investigation-contract.json

- `business_expectations`：`find-target-customers`（用户通过自然语言描述目标客户群体并搜索，获得符合筛选要求的客户集合）。
- `live_boundary`：live_role=将自然语言搜索要求转换为下游可消费结构化查询；in_scope=完整保留已表达/确认的筛选要求 + 以真实下游支持的字段/值/操作符/逻辑交付；out_of_scope=保证数据库有客户、保证外部数据完整实时、替用户决定未表达条件；external_constraints=下游无记录/服务不可用/字段未接入。
- `evaluation_dimensions` ×2：`search-intent-preservation`（搜索意图承接）与 `downstream-query-consumability`（下游查询可消费性），各带 fulfilled_when / not_fulfilled_when / not_evaluable_when。

### 7.4 现状结论

- 调查包已按"资料轴心"重建：11 份资料都登记了 MaterialDecision，用户原文（judge_boundary-template.md）已作为 normative_rule 登记并声明了信任模型 M1，8 份资料被正确分到 inlive_boundary/current_behavior 等定位。
- 两个 coverage_gap 都带 required_evidence，正好对应两个 tool_requirement 的 implementation_gap（es_enum_observation / query_result_equivalence）——即"缺口"与"验证能力缺失"是同一件事的两面。
- **当前 pack 的覆盖质量**：能力/职责边界类问题（如"某字段是否支持某操作符""某险种是否属于可查询范围"）理论上可由 inlive_boundary 资料 resolve；但 6 个经典判断点中 S3/S6（口语映射、查询等价）落在 gap 上，需要补业务确认或双查询能力才能 resolve。这正是下一轮调查的方向。

---

## 8. Draft Loop 状态与接手人操作手册

### 8.1 当前状态

- `.state/judge/loop.json`：`status=active`，`iterations=[]`（还没跑过第一轮新口径的迭代），`max_iterations=5`，`objective` 与 `review` 已写好（见 §8.3），`frozen_current_sha256=134d8339...`，`cases_sha256=bf9e77ee...`。
- `.state/judge/iteration-cases.json`：30 条冻结 badcase（source-badcase-xxx）。
- `.state/judge/solidify.json`：已生成，mapping judge-business-contract → runtime observable judge-business-contract-smoke **succeeded**。
- `.state/judge/investigation-validation.json`：已通过（manifest_sha256=8a6d93b3...，condition_compare 工具执行 succeeded）。
- `history/001~020`：**旧口径的历史尝试**。001 有 completed 的 run（30 cases，Protocol facts only）；020 的最新一次尝试 `iterations/001-run.json` 是 **failed**（`LLM endpoint unreachable during judge preflight ... api_transfer.wangshun.work/v1 DNS 失败）——旧 endpoint，已废弃。

### 8.2 当前 LLM endpoint（重要）

- 生效配置在 `impl/config.yaml`：`llm.provider=deepseek`、`model=deepseek-v4-pro`、`base_url=https://api.deepseek.com/v1`、`temperature=0`、`reasoning_effort=high`、`request_timeout_seconds=600`、`json_mode=true`、`tool_calls=true`。
- API key 从 `.env` 的 `DEEPSEEK_API_KEY` 绑定（`impl/config.yaml` env bindings）。
- **`.env` 里残留的 `LLM_BASE_URL=http://api_transfer.wangshun.work/v1` 已不被绑定使用**（bindings 里没有 LLM_BASE_URL），是历史遗留，可清理但无关紧要。
- 连通性验证：`/Users/xiaozijian/miniconda3/envs/agno/bin/python impl/checklist/test_deepseek_direct.py`（直连 HTTP + Agno 模型构建）。
- 用户已明确允许把本地 client_search 评测数据发送到该 DeepSeek endpoint。

### 8.3 loop 的 objective 与 review（冻结口径）

- objective：优化 Draft Judge——以 Authority 调查包为运行时材料（governs 直接决定、材料第一维度、unresolved 必须带原因与所需证据），让 Judge 在业务边界内输出可审计的 fulfillment/not_evaluable/not_fulfilled 判定，不越权、不劣于 Production。
- review：对照冻结 Current 30 条 badcase，Draft 必须在每条上保持或改善业务结果：Authority 绑定准确（不误绑、不遗漏）、not_evaluable 口径一致（材料缺失/边界外才用）、不输出无材料支撑的强验收条件；**equality 不是成功，整体必须优于 Production**。

### 8.4 怎么跑

```bash
PY=/Users/xiaozijian/miniconda3/envs/agno/bin/python
cd /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier

# 0) 前置：连通性 + 调查包校验 + solidify 已通过（已满足）
$PY impl/checklist/test_deepseek_direct.py
$PY .agents/skills/draft/scripts/validate_investigation.py --project client_search --role judge --execute-tools --tool-inputs '<JSON>'
$PY .agents/skills/draft/scripts/draft_loop.py status --project client_search --role judge

# 1) 第一轮迭代（health-check 会先探测 endpoint）
$PY .agents/skills/draft/scripts/draft_loop.py run --project client_search --role judge --workers 1 --retries 0

# 2) 查看本轮结果
$PY .agents/skills/draft/scripts/draft_loop.py status --project client_search --role judge
# 产出：draft/.state/judge/iterations/<NNN>-run.json（current/draft 逐 case 原始事实 + metrics）

# 3) Harness AI 审查每轮（不是自动判优）
$PY .agents/skills/draft/scripts/review_iteration.py --project client_search --role judge \
     --review '<role review JSON>' --iteration <NNN>
```

### 8.5 跑完一轮看什么（判断 Draft 是否更优）

1. **run report 结构**：`rows[].case_key / current / draft / current_metrics / draft_metrics / current_runtime / draft_runtime`；`decision` 字段留空——协议只落原始事实，**语义判优由 Harness AI 做**。
2. **逐 case 看三态分布**：Draft 是否把 Production 判错/漏判的 badcase 纠正；not_evaluable 是否只在"材料缺失/边界外"出现（不许滥用）；authority_tool_call_ids 是否真实、basis 是否可核验。
3. **authority 绑定准确率**：对每个依赖 authority 的 assessment，核对 decision_question 是否按 §8.2 模板、resolution 是否被正确分支消费、unresolved 是否带缺料清单。
4. **质量指标**：对比 current/draft 的 per-case metrics（accuracy / 三态一致性），注意 equality 不算成功。
5. **记录问题**：把发现的问题按 §10 的优先级挂到待办，不要边跑边大改；spec/实现改动需用户确认。

### 8.6 改什么、怎么验证（一般路径）

- 判断点查不到资料 → 回调查层补料/补 MaterialDecision/补 coverage_gap（用户手动触发 `/draft investigate` 或 continue），改 report JSON 后必须 `render_authority_report.py` 重新渲染 MD；
- 检索召回差 → 调 `build_authority_key_index.py`（entry 粒度/search_text 投影）或调查层选新 Index 策略；
- Authority prompt 约束/后处理问题 → 改 `authority_environment.py` / `authority_gate.py`（Core 通用，不许加 client_search 专用逻辑）；
- Judge 消费问题 → 改 `draft/judge.py` 的 system_extras / gate；
- 每次改动后：跑对应测试（§9）+ 一轮 loop 复跑对比。

---

## 9. 测试基线

### 9.1 全量（2026-08-05 实测）

```text
633 passed, 25 failed (147s)
```

### 9.2 本轮工作直接覆盖的测试（全部通过）

```text
test_authority_runtime.py / test_authority_tool.py / test_authority_gate.py /
test_authority_enforcement.py / test_investigation_key_index.py / test_source_retrieval.py
→ 61 passed（上述 6 个文件合计）
另有 test_llm_runtime_config_contract.py / test_judge_execution_strategy.py /
test_solidify_receipt.py 等通过
```

### 9.3 25 个失败分类（都已有结论，非本轮回归）

| 类别 | 数量 | 失败原因 | 性质 |
|---|---|---|---|
| hooks/api-check | 20 | 本地 8023 端口没有起服务（`curl: Failed to connect to 127.0.0.1 port 8023`） | 环境夹具未起服务，非代码问题 |
| test_config_contract | 1 | `build_authority_key_index.py:122` 直接 `write_text` 写 manifest → `PATH_WRITER_BYPASS` | **需改**：改用 registered family writer（如 write_portable_export） |
| test_context_embedding | 1 | sandbox 无网络，`dashscope.aliyuncs.com` DNS 解析失败 | 环境相关 |
| test_investigation_protocol | 1 | 期望错误信息 "requires smoke inputs"，实际先撞到 hash 断言（expected hash 过时） | **需更新断言**（不要乱冻结 hash） |
| test_llm_client_json_extract | 2 | monkeypatch 无法承载 `logical_tool_aliases` | 需修测试或改健壮性 |

---

## 10. 已知问题 / 待办（按优先级）

| # | 事项 | 现状 | 建议 |
|---|---|---|---|
| 1 | **跑通第一轮 30-case Draft Loop** | loop.json active/0 iter；endpoint 已是 DeepSeek 且用户已授权 | 按 §8.4 跑；跑完按 §8.5 审查 |
| 2 | `build_authority_key_index.py:122` PATH_WRITER_BYPASS | test_config_contract 失败 | 改用 registered family writer（Core 通用机制） |
| 3 | test_llm_client_json_extract 2 个失败 | monkeypatch 与 `logical_tool_aliases` 不兼容 | 修测试或改健壮性 |
| 4 | test_investigation_protocol hash 断言过时 | expected hash 与实际不符 | 更新断言（不冻结新 hash 到别处） |
| 5 | hooks/api-check 20 个失败 | 8023 无服务 | 起服务后复跑确认，非代码问题 |
| 6 | Draft Loop revision 机制过严 | 用户已指出不合理 | 不是当前最紧迫，不要顺手重构，先记录 |
| 7 | **Skill 文档过时**：`.agents/skills/draft/SKILL.md` / `MAP.md` / `judge/ROLE.md` / `reference/investigation/judge/docs/authority-investigation-report.json` 模板仍写 `findings`（resolved/unresolved）、`authority_analyses` 旧形状 | 与新的 `materials + coverage_gaps` schema 不符 | 低优先，先确认口径再统一更新 |
| 8 | **legacy context units**：`draft/context/judge_authority_*.md`（enum_values/evaluation_boundary/query_equivalence/semantic_mapping）仍在 project.yaml 的 role_assets 里登记 | 属旧 Authority-limitation 设计 | 核对新 draft judge 是否还消费；若不再消费可清理或改登记 |
| 9 | `.env` 残留 `LLM_BASE_URL=http://api_transfer.wangshun.work/v1` | 已不被绑定使用 | 可清理，无关紧要 |
| 10 | deerflow / marketting-planning 的 attribute loop 状态 | `.state/attribute/` 有历史运行 | 确认是否受本轮改动影响（本轮只动了 judge 线，大概率无影响，但要确认） |
| 11 | 大量未提交改动 | git status 显示 160 个 M/??（含新增核心模块、spec、调查包） | 交接前明确提交策略（用户偏好：不要乱冻结 hash；spec 多为 untracked 新增） |

---

## 11. 用户硬约束（务必遵守，接手人逐条读）

1. **不要乱冻结 hash**：无关紧要的 hash 不要动；test_investigation_protocol 的过时断言更新即可。
2. **Runtime 不直接左右调查层**：顶多通过 `not_evaluable` + 缺料清单"提醒"；调查层触发必须用户手动；不存在 runtime 回写配对、结论资产、自动补证。
3. **不伪造成功、不吞异常、不 fallback**：不把 dispatch 失败转成 `not_evaluable`，不把完整失败结果包装成成功（tool_failure ≠ unresolved，代码里已显式区分）。
4. **Search hit ≠ Evidence**：必须继续 `search → load`，拿到真实资料内容（物化 unit_id）才算证据；index entry / navigation / load_targets 都不是 basis。
5. **结论整合是 Judge 本职**：调查侧不产出结论形状对象（无 resolved/unresolved 参考稿、无配对、无 findings）。
6. **修复必须是 Core 通用机制**：不得加 client_search 专用工具名 alias 或专用旁路。
7. **安全**：外部 endpoint 须用户明确允许才可发送本地评测数据；不得绕过审批。
8. **先调研讨论、别急着改**：改动前用户会明确说"去改/去实现"；spec 与实现的调整要先对齐口径。
9. **验证**：模拟实验优先（`/aihacking` 相关），确认效果与问题后再落 spec/实现；调查包改 JSON 后必须重新渲染 MD，不得手改 MD。
10. **不自动 promotion**：Draft 被证明更优后先报告，promotion 只由用户确认后由确定性代码执行。

---

## 12. 决策论证回顾（为什么是现在这套设计）

这部分回答"为什么绕了这么多弯"，接手人讨论新问题时先看这里，避免重复踩坑。

### 12.1 为什么否掉"调查期按业务问题出结论"

- 模拟实验（旧口径：10 material 全 current_behavior + 4 缺口）→ **0/6 resolved，全部 not_evaluable**；问题空间开放，调查期无法穷举每个 case 的组合问题；
- 调查期能稳定产出的是"资料能力声明"（不依赖具体问题）："这份资料在什么条件下决定什么"——提前定得了；
- 结论整合是组合推理，发生在具体 case 上，天然属于 runtime。

### 12.2 为什么删掉 findings

- 可行性试跑：result 文本与 `MaterialDecision.statement` 冗余；kind 语义已由 `conclusion_kind` 承载；"提示 runtime"的职能与"runtime 现场综合"冲突；人工审核可直接审材料层；
- 唯一"真损失"（调查侧的结论整合对象）本就是伪需求；
- 替代物 = **CoverageGap**（材料层确定性事实 + required_evidence），由 Harness AI 调查中自然产出、校验层确定性校验。

### 12.3 为什么否掉"问题→结论"跨 case 复用资产（配对回写）

- 用户明确指出这是伪需求：怎么定义"问题"？not_fulfilled 不是问题（业务侧事实），唯一算问题的信号是 `not_evaluable`；
- 回写会让 runtime 左右调查层/全局，污染证据空间；
- 复用只保留两层：证据空间（ContextUnit）跨 case 复用 + 同任务内 decision_question 去重。

### 12.4 为什么 Runtime 不驱动调查层

- 调查触发必须用户手动（`/draft investigate` 等）；
- runtime 顶多通过 not_evaluable + 缺料清单记录影响；评测报告汇总同类缺料，人看到共性后手动发起下一轮；
- 缺料清单载体 = `AuthorityResolution.unresolved.required_evidence` → Judge `not_evaluable` 的 reason / required_evidence。

### 12.5 为什么需要 Key-Index（且"索引不是切碎"）

- 大资料（planfullname_enums 371KB / abbrname_enums 313KB）flat 整读不可持续；nav 集合层 top-4 ≈ 1-2KB；
- 模拟实验证明 key-index 解决"找得到、读得动"，**不解决"资料本身不是 normative/external"**（那是定位/信任模型的事）；
- 索引只记录"哪些内容、在哪个位置、可以被什么检索词找到"；load_entry 按位置提取，内容本体完整原样，因此原始结构、相邻上下文和关系不因索引失真。

### 12.6 为什么 entry.key ≠ locator，定位由 target_ref 承担

- 概念"key（能定位到真实内容的那把钥匙）"在 schema 里由 `target_ref` 承担；字段 `entry.key` 只是索引内编号，与概念撞名是歧义根源；
- 已拍板：`MaterialDecision.locator` 本质就是 keyindex entry 的 `target_ref` 的一种（对象内部 locator，如 YAML path）；`entry.key` 只是索引内编号。

### 12.7 为什么需要 inlive_boundary（第 4 个 conclusion_kind）

- 系统内配置（字段/枚举/值映射）描述的空间由下游决定（parser 造不出空间外的东西）：标 external_fact 在出处上说谎、标 current_behavior 会被 Gate 卡死（不能裁决规范问题）；
- 单列 inlive_boundary + 信任模型登记（业务方声明 = 用户同意）+ C1-C6 + R1-R3，既让"能力/职责边界"类问题可裁决，又防滥用（不自我背书、不掩盖漂移、不裁决"选得对不对"）。

### 12.8 为什么 MaterialDecision 是"证据索引"不是"裁决依据"

- 现场综合必须发生在真实资料 Load 之后；MaterialDecision 只是告诉你"这份资料可能决定什么、去哪找"；
- 命中索引 ≠ 事实成立；索引命中后必须 load_entry → Target Resolver → EvidenceSpace Load 真实 ContextUnit，才可能进 basis。

### 12.9 为什么 authority 是"现场综合"而不是查表

- 每个 case 的问题通常比调查时的问题更具体、更组合；
- authority 在绑定空间内拆解问题 → 匹配 MaterialDecision → 候选 source_ref_ids → 内部 Search/Load → 现场综合 → resolved/unresolved；
- 同任务内相同 decision_question + snapshot 去重（cache），但不跨 case 沉淀。

---

## 13. 风险与未决问题（接手人注意）

1. **Skill 文档与 spec 脱节**（§10 #7）：SKILL.md / MAP.md / ROLE.md / reference 模板仍引用旧 `findings`/`authority_analyses` 形状。新调查包的真相源是 `materials + coverage_gaps`。跑 loop 前如果 Skill 调度依赖旧模板字段，可能在校验处失败——先核对 validate_investigation.py 实际校验的是哪个 schema（当前 manifest 已过门禁，说明校验器认新 schema）。
2. **`authority_analyses` 在 judge-investigation-contract.json 中不存在**：当前 contract 只有 business_expectations/live_boundary/evaluation_dimensions。ROLE.md 说"Judge 契约含 authority_analyses 时必须生成 report"——当前走的是"生成 report"路径，字段名是 report 里的 materials/coverage_gaps。
3. **两个 coverage_gap 的 required_evidence 需要外部能力（只读 ES 聚合 / 双查询快照比较）**：这是客户端环境拿不到的；下一轮调查要么找业务确认（术语表/封闭等价规则），要么明确记录为不可解除缺口。
4. **30 条 badcase 的参考口径**：review 里写"equality 不是成功，整体必须优于 Production"——判优标准依赖 Harness AI 人工判断，接手人要在第一轮 review 时把"优于"的操作定义写清楚（按哪些维度、多大规模差异算优）。
5. **Draft Loop revision 机制过严**（用户已指出）：当前设计在 revision 门槛上可能过于严格，但不要顺手改。
6. **deerflow / marketting-planning**：`.state/attribute/` 有历史运行；本轮只动了 judge 线与 Core authority 模块，理论上不影响，但要确认。
7. **160 个未提交改动**：交接前必须确定提交策略（哪些 spec/实现/调查包该提交、哪些历史 context_store 删除是预期）。不要乱冻结 hash。

---

## 14. 常用命令速查

```bash
PY=/Users/xiaozijian/miniconda3/envs/agno/bin/python
cd /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier

# 环境 / endpoint
$PY impl/checklist/test_deepseek_direct.py          # DeepSeek 直连 + Agno 链路验证

# 调查 / 固化 / 循环
$PY .agents/skills/draft/scripts/validate_investigation.py --project client_search --role judge --execute-tools --tool-inputs '<JSON>'
$PY .agents/skills/draft/scripts/draft_loop.py status --project client_search --role judge
$PY .agents/skills/draft/scripts/draft_loop.py run --project client_search --role judge --workers 1 --retries 0
$PY .agents/skills/draft/scripts/review_iteration.py --project client_search --role judge --review '<JSON>' --iteration <NNN>
$PY .agents/skills/draft/scripts/check_draft.py --project client_search --role judge

# 重建 key-index（改 report 或源资料后）
$PY impl/projects/client_search/draft/build_authority_key_index.py

# 渲染权威报告（改 JSON 后必须重新渲染，不得手改 MD）
$PY .agents/skills/draft/scripts/render_authority_report.py --project client_search --role judge

# 测试
$PY -m pytest tests/test_authority_runtime.py tests/test_authority_tool.py tests/test_authority_gate.py tests/test_authority_enforcement.py tests/test_investigation_key_index.py tests/test_source_retrieval.py -q
$PY -m pytest -q    # 全量（当前 633 passed / 25 failed，见 §9）
```

---

## 15. 文件索引

### spec（`spec/alg/`）
- `authority.md`（运行时 Authority 协议，§1-10 长期协议为当前口径）
- `fulfilled.md`（三态判定）
- `investigate.md`（Draft 调查/固化总协议；§1.9 Key-Index 策略探索与固化）
- `investigate-judge.md`（Judge 调查协议：BE/LB/ED 三对象 + Authority Gate）
- `investigate-authority-judge.md`（调查侧权威协议：MaterialDecision/Connection/CoverageGap）
- `investigate-keyindex.md`（通用 Index 协议）
- `material-positioning.md`（资料定位 + 信任模型）
- 备份：`spec/bak/2026-08-04-authority-design/`、`spec/bak/2026-08-01-authority-investigate/`、`spec/alg/*-bak1.md`

### 收敛记录
- `authority-design-issues.md`（repo 根；分歧收敛记录，写新 spec/讨论前先读）

### 实现（`impl/core/`）
- `authority_environment.py` / `authority_tool.py` / `authority_gate.py`
- `authority_key_index.py` / `investigation_key_index.py`
- `schema/authority.py` / `schema/investigation_judge.py` / `schema/investigation_key_index.py`
- `impl/tools/protocol.py`

### client_search draft（`impl/projects/client_search/draft/`）
- `judge.py` / `judge_strategy.py` / `judge_execution.py` / `build_authority_key_index.py`
- `investigation/judge/manifest.json` + `docs/*`（report JSON/MD、contract、evidence/authority-conflicts-scan.md）
- `.state/judge/`（loop.json、iteration-cases.json、solidify.json、investigation-validation.json、history/）

### Skill（`.agents/skills/draft/`）
- `SKILL.md` / `MAP.md` / `judge/ROLE.md` / `judge/knowledge.md`
- `scripts/`（validate_investigation / solidify / review_iteration / run_iteration / draft_loop / render_authority_report / check_draft ...）
- `reference/investigation/judge/docs/authority-investigation-report.json`（模板；**注意仍是旧 findings 形状**，见 §10 #7）

### 历史
- `search-test-case/issue/`（历次 authority/draft-judge 检查报告 2026-07-26 ~ 08-05）
- `docs/superpowers/specs/2026-08-05-investigation-index-strategy-exploration-design.md`（key-index 策略探索设计）
- `docs/superpowers/specs/2026-07-29-judge-execution-strategy-isolation-design.md`（Judge 执行策略隔离设计）
