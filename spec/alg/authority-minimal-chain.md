# Authority 最小链路讨论稿（v0.1）

> 状态：设计讨论稿，尚未裁决为长期协议。本文把 `spec/alg/authority.md` 第二章的冲突
> 收敛为一条可落地的最小链路，作为实施讨论的基础。裁决生效前，本文不作为实施清单。

## 1. 已确认的设计立场

1. **分工**：LLM 做语义综合（资料是否决定性），代码做一切可校验的事（物化、引用、
   hash、字段规则、权限、预算）。
2. **单条物化通道**：任何想被引用的内容（ToolResult、文件、人工澄清）必须先物化为
   可寻址、可重载、可 hash 的 ContextUnit；EvidenceRef 只引用已物化且 hash 未变的
   单元。废弃"ToolResult 直接变 EvidenceRef"的路线 A。
3. **触发**：Judge 在评估过程中发现标准冲突时调用 `authority.resolve(decision_question)`。
4. **消费方式**：去掉 Point/Binding 链路，assessment 直接引用 authority tool_call；
   Core 后处理保留"unresolved → not_evaluable"业务规则。
5. **assessment 引用方式**：LLM 在 assessment 写 `authority_tool_call_ids`，代码校验
   引用存在且属于当前 trace；引用不存在的调用 → 标 `needs_human_review`，不静默放行。
6. **执行形态（推荐，待实测确认）**：Production Judge 保持单次 agentic LLM 调用，
   `authority.resolve` 作为 Judge 的 Tool（方案 i）；若实测单次会话输出不稳定，升级为
   两段式（方案 ii，先 expectations 后 assessments）。
7. **单轮综合（推荐，待确认）**：Authority Agent 内部不做自主多轮调查迭代；多步
   tool-calling（search → load → 调工具 → 综合）是自然的。迭代调查是扩展。
8. **ID 空间（推荐，待确认）**：物化时 unit_id 由代码生成；manifest 的 ref_id 存入
   tags 作来源别名；运行时只认 unit_id。
9. **不新增 EvidenceCatalog**：引用校验用 `ContextRuntime.registry` + `ContextRun` 的
   loaded/hash 记录即可。

## 2. 业务需求（第一性原理）

verifier 链条：用户提要求 → Live 产出 actual → verifier 判断 actual 是否满足要求。
判断需要标准；标准来源（当轮要求、文档、配置、下游契约、数据库现实、历史答案、
代码行为）可能冲突。

- 标准冲突时 Judge 不得自行选择标准——选标准等于发明业务事实；
- Authority 回答：给定明确业务问题 + 当前可取得资料，标准是否唯一确定？
  → resolved / unresolved；
- 三个不可简化要素：**问题**（业务自包含）、**证据**（可寻址可重载可 hash）、
  **诚实性**（确定不了就说确定不了，并说明缺什么）。

Authority 不是事实查询（业务 Tool）、不是对错判断（Judge）、不是根因定位（Attribute）、
不是优先级背诵。

## 3. 对象分工（最小版）

| 业务需求 | 对象 | 职责 |
|---|---|---|
| 资料可寻址/搜索/加载/hash | `ContextUnit` + `ContextRuntime/ContextRun` | 唯一"资料载体"，静态与动态物化统一进 Registry |
| 动态事实获取 | `VerifiableTool` | 执行后 ToolResult 必须物化为 ContextUnit 才能被引用 |
| 结论可追溯 | `EvidenceRef` | 只指向已物化单元（location=unit_id, payload=None, metadata 带 source_hash/trace/case） |
| 权限/预算/边界 | Context policy + ContextRun | 直接复用，不新增 |

## 4. 最小链路

```text
Judge 发现标准冲突
  ↓
① 入口 authority.resolve(decision_question)
   Core 构造 Environment：project_id + role + trace/case
   → ContextRuntime（含 manifest 物化的静态 ContextUnit）
   → ContextRun（search/load/预算）
   → 授权 VerifiableTool（包装：ToolResult 自动物化）
  ↓
② 取料（静态）：ContextRun.search / load 静态资料
  ↓
③ 动态验证（可选）：VerifiableTool 执行 → ToolResult 自动物化为
   case-scoped ContextUnit → load 记录 hash
  ↓
④ LLM 综合（单轮）：输出 Resolution(status/statement/reason/
   basis_evidence_ref_ids/required_evidence)
  ↓
⑤ Finalization（确定性代码）：校验 basis refs 均为已加载 ContextUnit、
   hash 未变、字段规则 → 生成 EvidenceRef
  ↓
Judge 消费：assessment 引用 authority tool_call；
Core 后处理 unresolved + blocking → not_evaluable
```

### 每环校验规则

① 入口
- question：非空、长度受限、业务自包含；
- Environment 构造失败 → `ToolResult.status=failed`，不进业务层；
- `env_snapshot_sha256` = hash(project_id, role, 资产选择, 授权 unit 的
  source_hash 集合, 工具指纹)。

② 取料
- search ≤ query_limit 条；load ≤ load_limit 个，完整 content；
- 只有 policy 允许的可见；load 即记录 content hash。

③ 动态验证
- 工具执行失败（能力不可用）→ 业务 unresolved + reason 说明缺什么；
- 工具未授权/不存在/装载失败 → Environment failed（与业务 unresolved 分开）。

④ LLM 综合
- resolved ⇒ statement + reason + ≥1 basis；unresolved ⇒ 无 statement，
  reason + required_evidence；
- reason 须给出决定性论证或不足原因，不得只写"优先级更高"。

⑤ Finalization
- 每个 basis ref ∈ 已加载 ContextUnit；重载核对 hash 未变；
- 产出 `EvidenceRef(location=unit_id, payload=None, metadata={source_hash,
  trace_id, case_id, authority_call_id, question_sha256, env_snapshot_sha256})`。

## 5. Judge 接入（方案 i）

```text
Judge LLM（single-pass agentic，一次 complete_json 会话，tools 含 authority.resolve）
  ├── 生成 business_expectations
  ├── 发现标准冲突 → 调用 authority.resolve(question)（Agent-as-Tool）
  │      返回 ToolResult{outputs: {resolution, evidence_refs, env_snapshot}}
  ├── 继续生成 fulfillment_assessments
  │      依赖某次 authority 的 assessment 写 authority_tool_call_ids
  └── Core 后处理（替代 apply_authority_constraints 的 Point/Binding 链路）：
        - 校验 authority_tool_call_ids 存在且属于当前 trace；不存在 → needs_human_review
        - 引用的 resolution 为 unresolved 且 assessment 为 blocking → not_evaluable
        - 把 resolution 的 EvidenceRef 挂进 assessment 的 evidence 链
```

与现有代码的关系：
- 现有 `apply_authority_constraints` 的"Point 绑定 → 维度匹配 → 快照校验"链路退役，
  只保留"unresolved → not_evaluable"这一业务规则；
- 现有静态 `authority_analyses` 契约保留（作为扩展点），动态 resolve 处理其覆盖不到
  的新冲突。

## 6. 组件与改造清单（最小版）

1. 新增 `impl/core/authority/`：
   - `protocol.py`：AuthorityRequest、AuthorityResolution（schema）；
   - `environment.py`：`build_authority_environment(spec, role, trace, ...)`，复用
     attribute_environment 的 context 构建模式；
   - `agent.py`：resolve 入口（LLM 综合 + Finalization + ToolResult 包装）。
2. 抽取公共物化通道：把 attribute_environment 的 `_register_dynamic_materials` +
   Finalization 校验抽为公共模块（如 `impl/core/evidence.py`），Attribute 与 Authority
   共用。
3. manifest evidence_refs 物化：调查 manifest 的 evidence_refs → ContextUnitRecord
   （content_ref 指向原文件，tags 保留 ref_id/source_revision），进入可搜索空间。
4. Judge 接入：
   - Judge tools 注册 authority.resolve；
   - FulfillmentAssessment schema 增加 `authority_tool_call_ids`（可选字段）；
   - Core 后处理函数（校验 + unresolved→not_evaluable + evidence 挂链）。
5. 测试：
   - 最小闭环验收：client_search"高净值映射"（静态资料 + unresolved 路径）；
   - resolved 路径（资料足以确定）；
   - 引用不存在 tool_call → needs_human_review；
   - 无关 assessment 不受阻断（§9 的"年龄条件"案例）。

## 7. V1 明确不做

- 跨 run 缓存/复用（Solidify 固化）；
- Authority 自主迭代调查；
- `varying_conditions` 校验；
- Key-index；
- 多 manifest 合并；
- 跨 Role 资产共享；
- 静态 `authority_analyses` 的自动化复用（保留现有 Gate 行为，动态 resolve 先行）。

## 8. 扩展顺序（V1 之后）

1. 静态契约复用优先（现有 Gate 作为"已固化结论"）；
2. 单任务去重：(规范化 question + env snapshot) 一次解析；
3. `varying_conditions` 校验；
4. 跨 run 复用 via Solidify；
5. 高 stakes 二次自审（resolved 无工具重审）；
6. 跨 Role 资产共享、多 manifest 合并、Key-index。

## 9. 遗留问题

- 方案 i 单次会话输出稳定性需实测；不稳则升级方案 ii；
- Authority 内部 LLM 与工具预算的具体数值（复用现有 tool_call_limit 机制）；
- Judge prompt 需要明确"何时该调 authority、何时不该"（spec §7 的规则翻译成
  prompt 指引）。
