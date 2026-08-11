# Draft 协议收敛与 client_search Judge 优化设计

## 1. 目标

分两个阶段收敛 Draft：

1. 先统一 Draft 通用协议、Skill、Role、模板和门禁，移除静态 AuthorityAnalysis 链路对新调查包的误导。
2. 在统一口径上优化 client_search Judge，修复字段支持边界、Key-Index、Authority 工具失败和旧 Context 资产问题，并重新运行冻结 Draft Loop。

本工作不自动提交 Git、不修改冻结数据、不自动 Promotion。

## 2. 长期 Authority 模型

当前唯一正式链路为：

```text
Investigate
  → materials + coverage_gaps
  → EvidenceRef / Key-Index / ToolRequirement

Judge Runtime
  → 遇到具体权威问题时按需调用 authority.resolve

Core
  → 校验 authority_tool_call_ids
  → unresolved 只约束依赖该调用的 blocking assessment
```

以下链路不再作为新调查包或新运行逻辑的设计前提：

```text
authority_analyses
→ AuthorityAnalysis
→ Planning / CaseEvaluationPoint / Binding
→ authority_analysis_ids
→ authority-gate:<analysis_id>
```

历史产物可以保留；新模板、文档和活跃调查包不得继续生成该形状。

## 3. 阶段一：Draft 通用方案收敛

### 3.1 文档与 Role

更新以下文件：

- `.agents/skills/draft/SKILL.md`
- `.agents/skills/draft/MAP.md`
- `.agents/skills/draft/judge/ROLE.md`

收敛内容：

- Authority 调查报告固定为 `materials + coverage_gaps`。
- 调查阶段组织资料能力和覆盖缺口，不预枚举未来 Runtime Case 的 resolved/unresolved 问题。
- Solidify 物化 Evidence、Context、Key-Index 和可执行 Tool，不编译静态 Authority Gate。
- Judge Runtime 按需调用 `authority.resolve`。
- Core 通过 `authority_tool_call_ids` 执行审计和状态约束。
- Runtime 缺料只作为人工下一轮调查的输入，不自动回写或触发 Investigate。
- 当前 Draft 执行器支持 `attribute`、`judge`、`mock`；Live 仅为协议扩展点，直至实现对应 Role 和执行入口。
- 明确 active loop 的继续与 `--restart` 重开语义；restart 归档旧状态并从 iteration 1 开始。
- 明确 Promotion 的计划、检查、用户确认和确定性执行入口。

### 3.2 参考模板

更新：

- Judge investigation contract 模板删除 `authority_analyses`。
- Authority report 模板使用 `materials + coverage_gaps`，删除顶层 `findings`。
- Authority Markdown 由更新后的 JSON 通过确定性 renderer 生成，不手工维护平行内容。

### 3.3 门禁与测试

新增或更新确定性检查：

- Judge contract 模板能够被当前 `JudgeInvestigationContract` Schema 加载。
- Authority report 模板能够被当前 `AuthorityInvestigationReport` Schema 加载。
- 新模板不得出现顶层 `authority_analyses` 或 `findings`。
- JSON/Markdown 渲染结果一致。
- restart 行为归档旧 loop，并清理活跃 iteration 文件后从 1 开始。
- 新文档不再把静态 AuthorityAnalysis 链路描述为当前协议。

门禁只约束新模板、新调查包和当前活跃产物，不扫描或重写历史 `.state/history`。

### 3.4 兼容策略

- `JudgeBusinessExpectationOutput.authority_analysis_ids` 暂时保留为 deprecated compatibility projection。
- 它不是真相源，当前实现不得依赖它做 Gate。
- 在确认外部序列化消费者和历史回放要求后，再单独决定删除。
- 不删除历史 receipt、run report 或旧 investigation 归档。

### 3.5 阶段一完成标准

- 文档、Role、MAP 和模板只描述当前 Authority 模型。
- 参考模板通过当前 Schema 和 renderer。
- Draft 现有通用测试与针对性门禁通过。
- client_search 运行逻辑、当前 loop 和调查包尚未被修改。

## 4. 阶段二：client_search Judge 优化

### 4.1 `is_supported` 全链路

从真实字段定义向下传递：

```text
field_definitions_args.yaml
→ capability_manifest
→ compact capability manifest
→ field Key-Index
→ field definition Tool
→ Judge runtime context
```

实现要求：

- 保留明确的 `is_supported: true/false`。
- 对未声明 `is_supported` 的条目使用可解释的兼容语义，不把缺失自动等同于 false。
- 同一字段存在多个定义条目时，合并规则必须确定性处理支持状态冲突，并暴露冲突而非静默覆盖。
- 适用于全部字段，不为 073/088 写 Case 特例。

### 4.2 调查包材料能力

更新 `business-field-definitions` 的 MaterialDecision，明确区分：

- 字段是否存在；
- 字段是否允许作为客户搜索条件；
- 字段支持的操作符和值类型；
- 字段仅用于解析并返回“不支持提示”的情况。

报告只声明资料的决定范围，不预写具体 Case 结论。更新 JSON 后确定性重渲染 Markdown并重新运行调查门禁。

### 4.3 Key-Index

- 将字段定义索引正式登记到调查包 Index Catalog。
- 搜索投影只包含资料派生信息，如字段名、描述和支持状态。
- `load_entry` 返回真实字段定义内容及定位 receipt。
- Index hit、projection 和检索分数均不得直接作为 basis evidence。

### 4.4 Authority Runtime

- 能由当前已装载、无冲突的能力资料直接确定的事实不强制调用 Authority。
- 资料冲突、能力边界不清或查询等价无法静态确定时调用 `authority.resolve`。
- Authority 工具调用失败保持 `tool_failure`，不得包装成 resolved 或业务 unresolved。
- 修复结构化输出失败时采用通用 Schema 约束、有限重试或明确失败路径，不为“业务员”等个别问题增加旁路。

### 4.5 旧 Context 资产

追踪以下资产的真实加载和消费：

- `judge_authority_enum_values.md`
- `judge_authority_evaluation_boundary.md`
- `judge_authority_query_equivalence.md`
- `judge_authority_semantic_mapping.md`

处理规则：

- 未消费：从当前候选 role assets 中停止登记，不删除历史归档。
- 内容仍是稳定业务事实：转为普通 ContextUnit，并通过 Solidify observable 证明消费。
- 仅服务旧静态 Gate：不迁移到新候选。

### 4.6 验证顺序

1. 运行 capability manifest、field tool、Key-Index 和调查包门禁测试。
2. 定向运行 073、088、138。
3. 复核 048，避免掩码条件再次退化。
4. 重开 Draft Loop并运行冻结的 30 条。
5. 生成新的 Role review receipt。
6. 只有整体明确优于 Current 且无退化才记录 `improved/promotion_checks`。
7. 不自动 Promotion。

## 5. 非目标

本轮不做：

- 自动从 Runtime 触发 Investigate；
- 跨 run Authority 结论缓存；
- 为具体 badcase 写硬编码；
- 修改 frozen cases 或 Current baseline；
- 删除历史状态和历史报告；
- 自动提交或 Promotion；
- 在尚未实现前宣称 Live Draft 已受支持。

## 6. 风险控制

- 当前工作区存在大量未提交改动，修改前后按文件记录差异，不进行 reset、clean 或批量格式化。
- 第一阶段不碰 client_search 活跃 loop，以避免 Draft fingerprint 再次失配。
- 第二阶段修改调查包或候选资产后必须显式 restart，保留旧 loop 归档。
- 所有 LLM/Authority 网络验证使用用户已允许的 endpoint；基础设施失败独立记录。
- 所有优化以通用数据语义实现，不依据 Case ID、oracle verdict 或 unseen answer 分支。

## 7. 交付物

### 阶段一

- 收敛后的 Draft Skill、MAP、Judge ROLE。
- 与当前 Schema 一致的 Judge/Authority 模板。
- 对应门禁与测试结果。
- 变更清单和仍保留的兼容项说明。

### 阶段二

- `is_supported` 全链路实现。
- 更新后的 client_search 调查包和索引。
- Authority 工具失败通用修复。
- 旧 Context 消费审计结果。
- 定向用例和 30 条 Draft Loop 对比报告。
