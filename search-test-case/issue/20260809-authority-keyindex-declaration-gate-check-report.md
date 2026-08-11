# 20260809 Authority key-index 声明驱动 + 门禁 check report

## 审核背景

用户按 AGENTS.md 与 check 原则要求完整审查上一轮 CG-ENG-006/007/008 实施，发现多处"自己乱写"，确认修正方案后全部实施：
放开值级检索时序、P4（enhanced-rules 等大切片进 key-index）、调查产物门禁、description/search_text 口径清理、007 prompt 措辞清理。

## 审核发现（上一轮问题）

1. 值级召回链路回归：description 删全文后 `search_context_units`（embedding 投影=name+description）失去值级召回，而硬协议限制 `investigation_search_index` 只能在首次 Load 后使用 → 值级查询死锁为 unresolved。
2. P4 未落地：enhanced-rules 等字段级大切片没有 key-index，也没有"大切片必须进 key-index"的门禁。
3. description 泄漏实现细节：模型可见内容出现 `authority.evidence.<ref_id>` 与"不再把整字段内容复制进候选元数据"。
4. search_text 口径自造：纯值串联丢字段上下文，与协议 §12.2 / field_tools 不一致。
5. 007 prompt 混入"不是模型自述"审计语言。

## 修正实施

- `impl/core/authority_environment.py`
  - `_project_field_slice_evidence_indexes`：声明驱动（`metadata.key_index`），field / yaml_mapping_field 统一投影 `authority.evidence.<ref_id>`；search_text=字段名+值级确定性投影。
  - description 恢复摘要，不含实现细节。
  - `_resolve_system_prompt`：Search 无候选/无决定性候选时允许下一轮 `investigation_search_index` 值级/字段级检索；命中 load_targets 必须立即 Load；禁止并行导航/扩搜的治理边界保留。
  - `_claim_comparison_prompt` 措辞清理（去掉"不是模型自述"）。
- `impl/core/schema/investigation.py`：`_validate_sliced_evidence_key_index_support` 门禁——大切片资料（field / yaml_mapping_field / yaml_list_chunk）必须满足 manifest key_indexes 显式登记或 `metadata.key_index` 声明，否则校验拒绝。
- `impl/projects/client_search/draft/investigation/judge/manifest.json`：business-field-definitions / field-enums / value-mappings / enhanced-rules 声明 `metadata.key_index`。
- `spec/alg/investigate-keyindex.md` §8.3.1（运行时投影声明驱动）、`spec/alg/authority.md`（Investigate 义务）同步。

## 实测验证

- warn-policy 真实 env：catalog 含 `authority.evidence.business-{field-definitions,field-enums,value-mappings,enhanced-rules}`（106/120/59/33 个字段 entry）。
- 值级 probe：field-enums "在职有效客户"→orphanType；enhanced-rules "在职有效客户"→idValidDate；field-definitions "clientAge"→clientAge；value-mappings "annPremSegNum"→annPremSegNum。
- load_entry 闭环：field-locator 解析 load_targets，匹配唯一切片。
- 门禁反例：无支撑的 yaml_mapping_field 切片校验拒绝；有声明或 manifest 索引后通过。

## 验证清单

- [x] 170 passed 相关回归（investigation / keyindex / context / authority-tool / schema / draft-reference 等）
- [x] 门禁测试：`test_investigation_manifest_requires_key_index_support_for_sliced_evidence`
- [x] 投影闭环测试：`test_field_slice_projects_evidence_locator_index_closed_loop`（field + yaml_mapping_field + 无声明不投影）
- [x] description 摘要测试：`test_field_slice_description_stays_summary_without_implementation_details`
- [x] prompt 时序测试：`test_authority_prompt_allows_value_retrieval_via_key_index_after_empty_search`（warn-policy 实跑断言全过）
- [x] 已知环境失败未处理（业务源哈希/revision 漂移、embedding cache 漂移）：与本次改动无关
- [x] judge 报告 CG-ENG-006/007 更新；协议文档对齐

## 复查（check 二轮）发现与修复

1. field-locator 子串误配（高危）：`_build_evidence_load_target_resolver` 用 `field in locator_text` 子串匹配，精确字段名 `polNoInfo.applicantname` 被 `polNo` 污染 → 41/318 个投影 entry 的 load_targets 解析失败。修复：精确匹配优先，唯一子串匹配回退（strategy 区分 `field-locator` / `field-locator-substring`）；修复后真实数据冲突清零。
2. 门禁与投影能力不一致（中危）：`yaml_list_chunk` + `metadata.key_index` 声明会放行，但运行时投影只支持字段级切片 → 有声明无索引。修复：块级切片只接受 manifest key_indexes 显式登记，不接受声明绕过（schema/investigation.py + 协议同步）。
3. 投影与 manifest 显式索引重复注册（低危）：调查层显式登记同名 `authority.evidence.*` 且保留声明时 registry 会重复注册崩溃。修复：构建段按 index_key 去重，manifest 显式优先。
4. 复查确认无问题项：`_validate_authority_tool_sequence` 与新值级检索时序兼容（search_index 后必须 load_entry→load 由既有规则覆盖）；material decision 自然语言 locator 解析无回归（81 有 load_targets / 7 无 target 属预期）；投影 search_text 不进入模型上下文。

## 验证清单（二轮）

- [x] 真实数据 41 个 field-locator 冲突清零
- [x] yaml_list_chunk 声明绕过被门禁拒绝；manifest 显式登记放行
- [x] 投影索引去重：manifest 显式优先
- [x] 新增子串歧义回归测试 `test_field_locator_prefers_exact_field_name_over_substring_collision`
- [x] 181 passed 相关回归；4 failed + 23 errors 均为已知业务源哈希/revision 漂移

## 复查（check 三轮）发现与修复

1. 值级检索时序放口子过宽（中危）：prompt 允许"候选不决定性"时跳过 Load 直接导航，与"Search 有候选必须 Load"硬协议产生张力，模型可借"不决定性"规避必经 Load。修复：收紧为"Search 未返回任何候选"才可直接导航；有候选必须先 Load 确认，Load 后仍不足才可导航；并明确不得以"候选不决定性"跳过。
2. 确定性序列检查缺 search_index 链条（中危）：`_validate_authority_tool_sequence` 只覆盖 search→load、load_entry→load；search_index 返回候选后停在导航候选（未 load_entry）不会被拦，与 prompt"不得停留在导航结果"不一致。修复：中间序列要求 search_index 有候选必须紧跟 investigation_load_entry；结尾不允许停在有候选的 search_index。

## 验证清单（三轮）

- [x] prompt 收紧后 warn-policy 实跑断言全过（含"不得以候选不决定性跳过"）
- [x] 新序列测试：`test_authority_tool_sequence_accepts_value_retrieval_after_empty_search`（合法链）、`test_authority_tool_sequence_requires_loading_after_search_index_candidates`（两处拦截）
- [x] 183 passed 相关回归；4 failed + 23 errors 均为已知业务源哈希/revision 漂移
- [x] authority_gate.py / context_governance.py / context/tools.py 复查无新问题

## 复查（check 四轮）发现与修复

1. prompt 值级检索时序自相矛盾（中危）：第 4 条硬协议把 `investigation_load_entry` 一律限定在"完成第一次原始资料 Load 后"，而无候选场景的值级检索流程（search_index 命中 → load_entry → load）必须先于任何 Load 发生 → 该场景的 load_entry 被错误禁止。修复：`_resolve_system_prompt` 区分两种 load_entry 用途——MaterialDecision/coverage gap 的 load_entry 受首次 Load 时序限制；`authority.evidence.*` 内部对象索引的 load_entry 是值级检索流程的一部分，不受此限制；任何 load_entry 返回 load_targets 后下一轮必须立即 Load。
2. business-value-mappings 缺 consumption 登记（低危，一致性）：其余 3 个字段级切片 ref 均登记 `metadata.consumption`（key_live），唯独 value-mappings 未登记；而 judge 运行时按字段 key_live 消费它（judge.py 物化 `source_ref_id="business-value-mappings"` 并按 trace 字段投影 `_compact_value_mappings`）。未登记时 staleness 设施对其漂移 fail-closed（"no registered consumers"→needs_review），会造成本可自动吸收的 key_live 漂移被误判为需重审。修复：manifest 补 `consumption=[{consumer: "value-mappings-key-index", mode: "key_live"}]`，模拟漂移验证路由从 needs_review→absorb。
3. 确认无问题项：`enhanced_rules_key_index.py`（Judge 侧按 trace 字段 key_live 取规则列表的直接消费）与 authority 侧 `authority.evidence.*` 投影导航索引（search→load_entry→Load）用途不同、可共存，不需要合并；`business-time-knowledge` 无 key_live 消费（仅调查报告引用为冻结结论），fail-closed 路由属设施设计行为，不登记。

## 验证清单（四轮）

- [x] prompt 修复后 warn-policy 实跑断言全过（含"该用途的 load_entry 受此时序限制""用于内部对象索引（authority.evidence.*）的 load_entry 是值级检索流程的一部分"）
- [x] 序列校验：search_index 命中→load_entry→load 合法链通过；缺少 load_entry / 结尾停在 search_index 均被拦截
- [x] 34 passed（authority enforcement/gate/investigation_gates/tool/quadrants）
- [x] 17 passed（source_staleness）+ 4 passed（enhanced_rules_key_index）+ 4 passed（investigation manifest/key_index/sliced）
- [x] test_authority_runtime.py：13 passed + 3 failed + 23 errors，均为已知业务源哈希漂移（business-field-enums），与本次改动无关
- [x] 模拟漂移：value-mappings 登记 consumption 后路由 needs_review→absorb（key_live 自动吸收）

## 复查（check 五轮，持续循环）发现与修复

1. 死代码/缺失导入清理（低危，AGENTS.md 最简化原则）：`authority_environment.py` 删除未使用导入 `EvidenceRef`、未使用返回值 `stale_invalidations`、两个无调用死方法（`AuthorityEnvironment.ref_exists` / `content_hash`）；补齐缺失的 `Optional` 导入（`from __future__ import annotations` 掩盖了该 NameError 隐患）；`InvestigationKeyEntry/InvestigationKeyIndex` 由函数内局部导入上提为模块级。
2. 切片模式词汇三处硬编码重复（低危一致性）：`authority_environment.py` / `source_staleness.py` / `schema/investigation.py` 各自硬编码 `field` / `yaml_mapping_field` / `yaml_list_chunk`。统一为单一出处：`schema/investigation.py` 新增公共常量 `SLICE_MODE_FIELD/YAML_MAPPING_FIELD/YAML_LIST_CHUNK`，另两处改导入复用，删除本地定义。
3. 协议核对（无改动）：`investigate-keyindex.md` §8.3.1（运行时投影声明驱动、块级不接受声明绕过）、§6.3/§6.4（load_entry/load_targets 协议级顶层字段、Target Resolver 确定性）、§12.3/§12.4（search_index→load_entry→Load 使用流程）与实现一致；`authority.md` §4.2 Ports、§7 调用规则、§8 消费规则一致；§18 已知不一致清单第 5/8/9 条核对后仍准确，无需改动。
4. 消费-登记全口径核对（无改动）：manifest 11 个 evidence_ref 全部可消费（6 个被 judge 义务引用 + 全部被 material decisions 引用），judge 义务引用的 ref 全部在 manifest 登记；运行时实际物化 14 个 ref（11 manifest + 3 运行时产物）。
5. prompt 与运行时强制逐条核对（无改动）："最多 8 个 selection_ref / 不得 9+" 由 `AuthorityContextTools.load_context_units` 的 `Field(max_length=8)` 强制；"第一轮只能 search_context_units、候选必须紧跟 Load、search_index→load_entry→Load" 由 `_validate_authority_tool_sequence` 强制；值级检索时序（无候选才导航、MaterialDecision load_entry 受首次 Load 限制）prompt 内部自洽。

## 验证清单（五轮）

- [x] ruff 全绿（authority_environment / authority_tool / schema/authority / authority_key_index / schema/investigation / context/tools / source_staleness）
- [x] warn-policy 真实环境 E2E：14 个 evidence ref 物化；6 个 index_key 全可用；值级检索闭环（enhanced-rules 在职有效客户→idValidDate、value-mappings annPremSegNum→C8、field-definitions clientAge→C9、field-enums 在职→orphanType、planfullname 住院医疗保险→values-0000-0099、material-decisions→decision-1）
- [x] 131 passed 综合回归；4 failed + 23 errors 均为已知业务源哈希/revision 漂移（business-field-enums、source_revision），与本次改动无关

## 复查（check 五轮·续）发现与修复

6. `authority_tool.py` 无用签名探测（低危）：`_execute` 用 `inspect.signature(resolve_authority)` 探测是否接受 `authority_call_id`，但 `resolve_authority` 签名固定含该参数，探测纯属多余。删除 `inspect` 探测，直传 `llm=self._llm, authority_call_id=call_id`；对应测试桩签名补齐 `authority_call_id` 对齐真实函数。
7. `authority_key_index.py` 两个死函数（低危）：`load_material_decision_report`（`load_authority_investigation_report` 的薄包装）与 `create_material_decision_navigation_tools`（`build_material_decision_key_index_registry`+`create_key_index_tools` 的薄包装）全仓无调用。删除并清理未用导入（`Path`、`load_authority_investigation_report`）。

## 验证清单（五轮·续）

- [x] ruff 全绿；authority_tool / authority_key_index / schema/authority 导入通过
- [x] tests/test_authority_tool.py + test_investigation_key_index.py：16 passed
- [x] 综合回归 142 passed；4 failed + 23 errors 均为已知业务源哈希/revision 漂移

## 复查（check 六轮，持续循环）发现与修复

1. 业务源路径双真相（低危一致性）：`enhanced_rules_key_index.py` 硬编码 `src/main/python/data/.../enhanced_rules_args.yaml`，`build_authority_key_index.py` 硬编码 planfullname 路径，均与 project.yaml `resources.paths` 重复。修复：改走 `spec.source_path("enhanced_rules"/"planfullname_enums")` 单一出处。
2. PATH_WRITER_BYPASS 链（协议对齐，均改 registered/portable writer）：
   - `build_authority_key_index.py::main()` 裸写 manifest → 改用 `dump_investigation_manifest`（registered family writer）；顺带删除无调用兼容层 `build_entries`（AGENTS.md 禁兼容层）。
   - `simulate_field_key_index.py` 两处裸写（embedding cache + --output）→ 按 `project_artifact_repository_root` 可解析性分流：实验目录（owned）用 `write_active_artifact("key_index_experiment", ...)`，外部路径用 `write_portable_export`。
   - `source_staleness_cli.py` 三处裸写（drift-report/large-materials/audit ledger）→ 新增 `staleness_report` family（`*/draft/.state/*/staleness/*.json`）后改用 `write_active_artifact`。
   - `draft_gate_feedback.py::write_gate_feedback` 裸写 → `write_portable_export`。
3. active artifact family 补齐（一致性）：新增 `staleness_report` / `authority_claim_index`（`docs/authority-claims.json` 是 investigation 硬依赖却从未被分类）/ `key_index_experiment` 三个 family；`authority-claims.json`、`experiments/*.json`、staleness 报告从 PATH_ACTIVE_UNKNOWN/PATH_WRITER_BYPASS 清零。

## 验证清单（六轮）

- [x] test_config_contract PATH_WRITER_BYPASS 从 4 处清零；PATH_ACTIVE_UNKNOWN 从 10 处降至 8（均为 `.state` 审计/反馈/`.bak` 既有会话产物，非 authority 实现缺陷）
- [x] 189 passed 综合回归；4 failed + 23 errors 均为已知业务源哈希/revision 漂移（business-field-enums、source_revision、embedding cache 投影）
- [x] source_staleness 17 passed（含 embedding cache 按键刷新用例，修复了 write_active_artifact 缺 root 的回归）
- [x] test_active_artifacts 14 passed + test_config_path_portability 24 passed（新 family 无破坏）
- [x] warn-policy E2E：value-mappings 值级检索闭环正常，prompt 时序修复保持
- [x] 遗留（非本轮改动引入）：`.state/judge/context-governance/*.json` 等 8 个审计文件未分类；`loop.json.bak` 属备份垃圾可删；上游漂移 4 项（用户已指示不处理）

## 复查（check 七轮）发现与修复

1. `.state` 未分类文件清零（协议对齐）：`loop.json.bak`（备份垃圾，零引用）删除；新增 `gate_feedback` family（`*/draft/.state/*/*-gate-feedback.json`）与 `context_governance_review` family（`*/draft/.state/*/context-governance/*.json`），全部 8 个审计/反馈文件分类完成。
2. `context_governance_review` 两处 PATH_SCHEMA_BYPASS（既有违规，修 file 不改 validator）：`judge-authority-context-*` 记录的 `evidence[].path` 是裸相对路径字符串，不符合 derived_active 严格校验。修复：19 处证据 `path` 转为 `LogicalPathRef`（`location_scope: "verifier_repo"`）；`authority.py:79` 拆为 location+lines；`agno/models/base.py` 属外部 site-packages、无诚实域，并入 `detail` 文本引用。
3. 产出机制对齐：`.agents/skills/context-governance/SKILL.md` 补证据路径 portable 格式说明（repo 文件用 verifier_repo LogicalPathRef、外部依赖写进 detail），后续记录经同一门禁校验。

## 验证清单（七轮）

- [x] `_scan_active_path_artifacts`：PATH_SCHEMA_BYPASS ×2 → 0；PATH_ACTIVE_UNKNOWN ×8 → 0；仅剩 PATH_INTEGRITY_STALE ×4（business-field-enums/source_revision 上游漂移，用户指示不处理）
- [x] context_governance_review 4 个记录全部通过家族校验

## 复查（check 八轮）发现与修复

1. Authority 证据 run 会话级污染（中危，运行时隔离缺陷）：`build_authority_environment` 只创建一次 `ContextRun`，同一 judge 会话内多次 `authority.resolve`（不同问题）共享 candidate/loaded/hash 痕迹。后果：后续调用可把先前调用 Load 过的单元当作"本 run 已 Load"通过 basis 校验（authority.md §12.1 的 run 语义被破坏）；claim 比对阶段的 `context_coverage` 混入历史调用状态，`ungoverned`（无资料管辖）会被误判为 `gap_only`。修复：`ContextRun.reset_trace()`（保留 policy、重置 per-call Search/Load 痕迹），`AuthorityTool._execute` 每次调用开始处重置；直接 `resolve_authority` 调用方（测试/probe 先 Load 再 resolve 的 API 用法）保持自行管理 run 状态不变。
2. 深审 claim 比对/resolve 全流程（无改动项确认）：盲查阶段 user 载荷与 system prompt 均不含 claim（信息隔离成立）；比对阶段 `tools_override=[]` 模型边界强制无工具；`_derive_context_coverage` 与 `debug_snapshot()` 键名一致；`_validate_authority_tool_sequence` 覆盖 Search→Load、search_index→load_entry→Load、结尾不留候选；`apply_authority_gate` 的 unresolved/tool_failure/引用缺失/needs_human_review 语义与 authority.md §8.4 一致；claim 四值消费由 Draft 义务门禁（`analyze_judge_gate_obligations`：ungoverned/gap_only/unresolved→not_evaluable、contradicted→require_human_review）承接，spec/grill/authority.md §4.2 对齐。
3. ruff 清理（风格一致性）：`active_artifacts.py`/`solidify.py`/`draft_role_review.py` 的 `type(x) is not int` → 显式 bool 排除的 isinstance 检查（4 处）；`solidify.py` 死赋值 `normalized_mappings` 删除；`authority_gate.py` 未用导入 `Sequence`、`test_authority_runtime.py` 未用导入 `AuthorityResolution` 删除。

## 验证清单（八轮）

- [x] 新增 `test_authority_tool_call_isolates_evidence_run_between_resolves`：第二次调用引用第一次调用留下的 Load 记录被拒（demote unresolved），证明 run 隔离生效
- [x] test_authority_runtime 40 passed（fixture 与 3 个内联 env 测试按已定结论切 warn 策略绕开上游漂移）
- [x] 相关回归 109 passed（authority_tool/gate/enforcement/investigation_gates/quadrants/key_index/source_staleness/active_artifacts/config_path_portability/draft_gate_feedback）+ 92 passed（context_runtime/enhanced_rules_key_index/schema_validator/authority_runtime）+ 61 passed（investigation 协议/portable/trace/judge_investigation）
- [x] 剩余失败均为已知上游漂移：`business-field-enums` 哈希（investigation_protocol、judge_investigation solidify 投影）、`source_revision`（investigation_cli）、embedding cache 投影（key_index_experiment），与本次改动无关
- [x] ruff 全绿（本轮触及的 11 个文件）

## 复查（check 九轮）发现与修复

1. authority_gate 消费链核对（无改动，确认对齐）：
   - 时序正确：项目侧 `judge_execution.judge_trace` 先 `apply_authority_gate` 改写 assessment 状态，再经 Core `finalize_judge_result` 按 blocking expectations 确定性聚合——gate 的状态改写（not_evaluable）正确进入 overall 推导（任一 blocking 非 fulfilled → overall not_evaluable）。
   - Production 不暴露 `authority.resolve`（`impl/projects/client_search/judge.py::_build_core_context` 无 authority 工具）；gate 仅 Draft candidate 路径运行，与 spec/grill/authority.md"不改 Production Judge"一致。
   - `_judge_self_check` 校验 authority_tool_call_ids 非空、status 词表、expectation 拓扑；伪造 ID（数字/resolution.N@hash）由 gate `_looks_like_resolution_id` 命中并 needs_human_review。
   - claim 四值消费由 Draft 义务门禁 `analyze_judge_gate_obligations` 承接（ungoverned/gap_only/unresolved→downgrade_to_not_evaluable、contradicted→require_human_review），四象限探针 Q1-Q4 与 grill spec §Q 表对齐。

## 复查（check 十轮）发现与修复

1. `judge.py`（draft+production）intent_frame dict 字面量重复键（F601，真实缺陷）：`"downstream_consumer"` 出现两次，`spec.project_id` 被后写的字面量 `"downstream client search"` 静默覆盖。与其余项目惯例一致（intent_frame 用可读描述），删除前置死键。
2. `structured_output.py::render_output_constraint` 死赋值（F841）：`required = schema.get("required") or []` 未使用，删除。
3. 死导入清理（F401）：`draft/judge.py` 未用 `hashlib`；`judge.py`(production) 未用 `application_boundary`/`state_executors`/`trace_state_graph`；`authority_investigation_gates.py` 未用 `Sequence`；`investigation_key_index.py` 未用 `Callable`。
4. `simulate_field_key_index.py` E702 分号多语句（6 处）拆分单行。
5. `authority_investigation_gates.py` 深审无问题：claims/resolutions/gap_bindings 全量 fail-closed 校验、未知 EvidenceRef/CoverageGap 拒绝、冲突判定保守（条件集未知重叠标 potential_conflict 而非冒充确定性理解）、probe 派生确定性（subject hash 键控）。

## 验证清单（九~十轮）

- [x] 相关回归 63 passed（schema_validator/authority_investigation_gates/investigation_key_index/judge_execution_strategy/client_search_judge_investigation/authority_enforcement）；仅剩已知 business-field-enums 漂移 1 项
- [x] 综合回归（authority_runtime 40 + authority 相关 109 + context/schema 92 + investigation 61 + active/solidify/role-review 135）延续全绿
- [x] ruff 全绿（本轮触及的 authority/结构化输出/judge 相关文件）

## 复查（check 十一轮）E2E 实测与横向发现

1. warn-policy 真实环境 E2E 值级检索闭环 4/4（复跑确认）：
   - `authority.evidence.business-enhanced-rules`：query="在职有效客户" → key=idValidDate → 1 unit `authority-ref-19cbfc804287745a`
   - `authority.evidence.business-field-definitions`：query="clientAge" → key=clientAge → 1 unit `authority-ref-aa17ee78b2525ec3`
   - `authority.evidence.business-value-mappings`：query="annPremSegNum" → key=annPremSegNum → 1 unit `authority-ref-8c63552fc383d69d`
   - `authority.evidence.business-field-enums`：query="在职有效客户" → key=orphanType → 1 unit `authority-ref-e99be00e449b1f78`
   - 序列校验通过：search 无候选 → search_index → load_entry → load 合法链不触发 `AuthorityToolProtocolViolation`。
2. 横向问题已落地（judge 复用 Core 公共设施，协议零改动）：`impl/projects/client_search/draft/judge_execution.py` 原与 Core `impl/core/judge.py` 重复实现 19 个 helper，其中 11 个逐字节一致。已删除项目侧 11 个一致副本与 2 个随之失效的常量（`_FIELD_LIST_KEYS`/`_JUDGE_RAW_RESPONSE_MAX_CHARS`），改为从 `impl.core.judge` import（`_compact_raw_response_for_judge`/`_derive_overall_status`/`_dict_value`/`_has_input_reference`/`_judge_turn_view`/`_minimal_honest_judge_result`/`_trace_reference`/`load_judge_boundary_standard`；`_reference_ready_from_trace` 随 `_trace_reference` 一起消费）。其中 3 个在项目侧本就无调用（`ensure_business_expectation`/`finalize_judge_result`/`_extract_fields_from_trace`）直接删除不引入；`_judge_run_trace_view` 兼容别名（零调用，AGENTS.md 禁兼容层）Core 与项目侧一并删除。保留的 8 个为真实分叉（authority gate 消费、applicability 处理、capability_fields 校验、actual_state 投影）。对齐测试：`test_authority_enforcement.py`/`test_judge_blocking_aggregation.py` 的 `finalize_judge_result` 改从 Core import（draft 已无该定义）。与其余项目（QA/deerflow/marketting-planning 均从 Core import `ensure_business_expectation`）惯例一致。
3. staleness 设施留白（不属本轮改动）：`global-context-audit-*.json` 目前靠 Harness 手工写；`report-drift` 仍缺"自动合并进 `context-governance/` 目录"的步骤，属 spec §8 增量实施待办，本次不落地。

## 验证清单（十一轮）

- [x] warn-policy E2E 值级检索闭环 4/4 + 序列校验通过（复跑确认）
- [x] test_authority_runtime 40 passed
- [x] test_judge_blocking_aggregation + test_authority_enforcement + test_judge_execution_strategy + test_client_search_context_governance 18 passed；test_client_search_judge_investigation 23 passed（仅剩已知 business-field-enums 哈希漂移 1 项）；test_schema_validator 通过
- [x] 死导入清理（F401）：`judge_protocol.py` 未用 `core_judge_trace`、`core/judge_execution.py` 未用 `typing.Any`（judge 架构链一并清掉）
- [x] ruff 全绿（本轮触及全部文件）

## 复查（check 十二轮）draft/authority/key-index

1. material-decisions 索引双真相（P4 声明缺陷，已修复）：`impl/projects/client_search/draft/build_authority_key_index.py::_material_entries` 与 Core `impl/core/authority_key_index.py::build_material_decision_key_index` 重复实现同一索引，且已分叉：项目侧 search_text 更丰富（含 related_to/limitations），但**漏掉了 2 个 coverage-gap 条目**（report 有 semantic-mapping-authority / query-form-equivalence-authority 两个 gap，manifest 一个都没有）。后果：prompt 承诺"导航结果包含与 decision_question 匹配的 coverage_gap 必须加载检查"，但运行时（manifest 驱动）search_index 永远搜不到 gap。修复：Core 单一生来源补上 related_to/limitations；项目 writer 改复用 `build_material_decision_key_index`；重跑 builder 重生成 manifest（16 条 = 14 decisions + 2 gaps）。E2E 验证：`authority.material-decisions` 搜"多个合理映射且无法唯一选择"→ 命中 `coverage-gap.semantic-mapping-authority` → load_entry 返回 coverage_gap + basis_search_hints，闭环恢复。
2. draft/production `judge.py` 双真相（待用户决策，未改）：两个文件独立实现同一 ProjectJudge，13 个 helper 逐字节一致（76 行，condition-equivalence + protocol 面）。但 `build_context`/`build_intent_frame` 的传递依赖（`_build_core_context`/`build_judge_context`）已分叉，不能整体 import；安全可复用的是其余 10 个纯自包含 helper。方向有二：(a) draft 从 production import 这 10 个（production 零改动，延续 draft→live 依赖惯例）；(b) 保持现状（draft 允许分叉）。按"不改 Production Judge"的既有规则，倾向 (a)，等用户拍板。
3. draft `apply_condition_comparison` 分叉确认是设计而非缺陷：draft 不再用确定性 blocking `client_search:search_condition_contract` 判 not_fulfilled，改由 `_apply_operator_capability_check`（Authority 前置校验面，fail-closed 到 not_evaluable + 人审）+ `_apply_explicit_unsupported_boundary_gate` 承接，符合 authority.md"确定性强判前先完成能力/职责裁决"。不修改。

## 验证清单（十二轮）

- [x] warn-policy E2E：coverage-gap 经 `authority.material-decisions` search→load_entry 闭环恢复（修复前运行时搜不到 gap）
- [x] test_investigation_key_index + test_authority_tool 16 passed；test_authority_runtime 40 passed；test_client_search_judge_investigation 23 passed（仅剩已知 business-field-enums 哈希漂移 1 项）
- [x] authority-claims.json 经 `load_and_validate_authority_claim_index` 校验通过（5 claims / 3 subjects / 2 conflicts / 3 probes）
- [x] ruff 全绿（本轮触及全部文件）

## 复查（check 十三轮）draft/authority/key-index

1. 十二轮修复回归确认：warn-policy E2E 复跑——值级检索闭环 4/4（enhanced-rules→idValidDate、field-definitions→clientAge、value-mappings→annPremSegNum、field-enums→orphanType）+ coverage-gap 经 `authority.material-decisions` search→load_entry 闭环 + 序列校验，全部保持。
2. 声明↔运行时一致性逐项核对（无改动，确认对齐）：
   - manifest v2 evidence_refs（field/yaml_mapping_field 切片声明 `metadata.key_index`、planfullname yaml_list_chunk 声明 manifest 索引）与 `_validate_sliced_evidence_key_index_support` 门禁一致；`authority.evidence.<ref_id>` 运行时投影与声明 `entry_granularity=field` 一致；
   - tool_requirements 的 `implementation.module_ref`（`tools/search_condition_compare.py` project_package）解析正确，schema v2 校验通过；
   - `_validate_authority_tool_sequence` 检查的 `selection_ref`/`target_ref`/`load_targets` 与 `search_context_units_tool`/key-index search/load 实际输出字段逐一对齐；
   - `authority-claims.json` 经 `load_and_validate_authority_claim_index` 校验通过（5 claims/3 subjects/2 conflicts/3 probes）。
3. 新发现（待用户确认，未改）：`spec/alg/` 下 6 个零引用的 `*-bak*.md` 备份文件（`authority-bak1`/`investigate-bak1~3`/`investigate-authority-judge-bak1`/`attribution-schema-bak1`），全仓无引用。AGENTS.md"过时的直接删"，但属 spec 协议区，按 check 规则需用户拍板再删。
4. 遗留决策（上轮未定）：draft/production `judge.py` 13 个逐字节一致 helper（76 行），安全可复用子集 10 个（`build_context`/`build_intent_frame` 传递依赖已分叉不能整体 import）。建议 draft 从 production import 这 10 个、production 零改动。

## 验证清单（十三轮）

- [x] warn-policy E2E 复跑：值级闭环 4/4 + coverage-gap 导航 + 序列校验
- [x] test_investigation_key_index + test_authority_tool + test_authority_investigation_gates + test_authority_gate + test_enhanced_rules_key_index 42 passed
- [x] 声明↔运行时逐项核对无漂移；ruff 全绿（本轮触及文件）

## 复查（check 十四轮）draft/production judge.py 复用落地

用户拍板：spec/alg 下 `*-bak*.md` 属有意保留的备份，不动；同意 draft 复用 production helper。
1. `impl/projects/client_search/draft/judge.py` 与 `impl/projects/client_search/judge.py` 模块级逐字节一致函数共 9 个；其中 draft 实际消费的只有 3 个（`judge_governance`/`protocol_tools`/`semantic_equivalence_rules`），已改为从 production import（production 零改动，延续 draft→live 依赖惯例）。其余 6 个（`_hashable_value`/`_jsonable_value`/`_semantic_equivalence_config`/`_equivalent_condition_forms`/`canonical_condition`/`canonical_conditions`）在 draft 中只被这些已删副本互相引用，属死代码，直接删除不引入。类方法 `__init__`/`build_context`/`build_intent_frame`/`normalize_result` 与 `condition_comparison`/`apply_condition_comparison` 等已分叉函数保持项目侧不动。
2. 顺带清理：draft 侧 `ClientSearchConditionCompareTool`/`ToolRegistry` import 随 `protocol_tools` 本地副本删除而失效，已移除；`ToolContext`/`ToolResult` 保留。

## 验证清单（十四轮）

- [x] draft/judge.py 导入 production 三 helper 生效（同一函数对象），production 文件零改动
- [x] test_judge_evidence_view + test_judge_blocking_aggregation + test_authority_enforcement + test_judge_execution_strategy + test_client_search_context_governance 20 passed
- [x] test_client_search_judge_investigation 23 passed（仅剩已知 business-field-enums 哈希漂移 1 项）
- [x] ruff 全绿（draft/judge.py + production judge.py）

## 复查（check 十五轮）draft/authority/key-index

1. 真实缺陷修复——gate_feedback 写入路径被 `PATH_WRITER_BYPASS` 拦截：`validate_investigation.py`/`solidify.py` 失败路径调用 `write_gate_feedback()`，其内部原固定走 `write_portable_export`，但目标是已注册的 `gate_feedback` family（`*/draft/.state/*/*-gate-feedback.json`）→ CLI 诊断反馈写不出来、测试断言只见 traceback。修复 `impl/core/draft_gate_feedback.py::write_gate_feedback`：`project_artifact_repository_root` 可解析且 classify 为 `active`/`unknown_owned` 时改走 `write_active_artifact("gate_feedback", ...)`，否则保留 portable 分支（外部路径场景）。
2. 全量扫 `write_portable_export` 调用点（17 处）确认无同款不一致：
   - 已正确分流 active vs portable：`schema/investigation_trace.py::dump_trace_graph`、`schema/investigation_judge.py::dump_judge_contract`/`dump_authority_investigation_report`、`schema/investigation.py::dump_investigation_manifest`（v2 走 active、v1 拒绝 registered active 路径）、`simulate_field_key_index.py`（embedding cache 走 active `key_index_experiment`）、`solidify.py`/`pipeline.py`/`schema/investigation_mock.py`；
   - 写外部 `--output`/报告/tmp 路径属正常 portable：`draft_loop.py`、`run_iteration.py`、`probes/select_frozen_cases.py`、`probes/prepare_judge_badcase_cases.py`。
3. CLI 复跑（`validate_investigation.py --project client_search --role attribute --execute-tools`）：反馈文件正常落盘（1.7KB，含 `harness_prompt` 渲染），diagnosis 正确指向 source_revision 漂移；门禁仍失败仅因已知环境漂移（用户指示不处理）。

## 验证清单（十五轮）

- [x] test_draft_gate_feedback 9 passed + test_active_artifacts/test_config_path_portability 38 passed（合计 47）
- [x] test_investigation_protocol 30 passed / 1 failed（唯一失败=已知 source_revision 漂移，消息已非 PATH_WRITER_BYPASS，反馈文件已正常落盘）
- [x] ruff 全绿（draft_gate_feedback.py + validate_investigation.py）

## 复查（check 十六轮）context-governance 按 AGENTS.md 查 authority 实现

目标与范围：authority 相关实现（environment/tool/gate/key-index/claim-index/schema）+ governance scanner；只读复查，沿用 review 记录 `judge-authority-context-2026-08-09` 的 CG-ENG-003。

1. 无新增阻断缺陷；全部 authority 测试 100 passed。静态扫描确认：
   - authority 文件无死函数/死导入（`_tool_result_contains_key` 等全部有真实消费）；broad except 均为 fail-loud 或文档化策略（`_materialize_tool_result` 失败不阻塞结果但不可引用为 basis，符合 authority.md §4.2）。
   - `write_portable_export` 17 处调用点分流复核无回归（十五轮 gate_feedback 修复完好）。
   - draft/production judge.py 逐字节一致模块级函数残留 0（十四轮复用闭环）。
   - B023 闭包捕获循环变量两处（`authority_key_index.py` validate_target、`context_governance.py` instruction_clause/mentions）：当前均在 register/调用点同步执行，非运行时 bug，属潜在隐患。
2. CG-ENG-003 复确认仍 open：2026-08-09 全库扫描 0 条带 governance 元数据的 ContextRecord；`impl.context audit --trace authority-resolve` 最新记录（de84106d）仅返回 `historical_provenance_unavailable`（mode=production 非阻断）。需要一次真实 governed Draft 跑才能 record-verified。
3. 低危观察（未改，等拍板）：
   - AUTH-R16-001：B023 潜在闭包隐患，建议默认参数绑定循环变量（行为零变化）。
   - AUTH-R16-002：core 内 4 个稳定 hash helper 重复且序列化细节不同；全量统一会改持久化 sha256（破坏冻结证据），只建议合并字节一致变体或注释说明差异。
   - AUTH-R16-003：scanner 无"LLM 输出契约字段为空"检查（CG-ENG-001 建议的纵深防御，根因已修）。
   - DRAFT-R16-004：staleness 大资料门禁遗留 2 个 open（abbrname_enums/claimplancodename_enums 未登记消费通道），属调查层待办（P4 类），非 authority 上下文缺陷。

## 验证清单（十六轮）

- [x] test_authority_runtime/tool/gate/investigation_gates/key_index/enhanced_rules + judge 聚合/证据视图/执行策略 100 passed
- [x] `impl.context audit --trace authority-resolve` 确定性 scanner 实跑（历史 provenance 诊断符合预期）
- [x] 全库 governed 记录扫描 0 条（CG-ENG-003 证据更新）
- [x] 新 review 记录落盘 `impl/projects/client_search/draft/.state/judge/context-governance/authority-recheck-2026-08-09.json`（active artifact 校验通过）

## 复查（check 十七轮）authority 实际上下文合理性审查

按 context-governance 语义维度审查 authority 实际拿到的上下文（当前代码编译 + 最新真实记录），发现 1 个中危角色/阶段泄漏：

1. **AUTH-R17-001（中危）authority 证据空间混入调用角色的 live role assets**：
   - `build_authority_environment`（`impl/core/authority_environment.py:1198`）把 `role_asset_context_records(role=judge)` 全部注册进 Authority 搜索空间：`judge_evaluation`(evaluation.md)、`judge_standard`(judge.md)、`judge_boundary`(judge_boundary_protocals.md)、`judge_business_contract` + 8 个 investigation 包文件。
   - 其中 3 个与 manifest 已冻结的 evidence refs（`project-evaluation-contract`/`current-judge-standard`/`project-judge-boundary`）指向同一文件 → 同一内容双重注册（冻结单元带 sha256 钉定 vs live 单元无钉定、漂移无保护）。
   - 实测：authority `search_context_units(["evaluation"])` 同时返回 `judge_evaluation: evaluation.md` 与 `Evidence project-evaluation-contract`（同文件两个候选），load 出 evaluation.md 全文（含"标准答案只能作为参考"）。
   - spec 违例：`spec/alg/authority.md` §4.2"证据空间 = 当前 Judge Investigation manifest 物化的 ContextUnit + 本次已登记 Tool 物化结果"；role assets 二者皆非。且 system prompt 明示"不做'当前输出对不对'的判断（那是 Judge 的职责）"——但 judge 评估材料可被检索。
   - 影响：expected-output 偏置通道（authority 可能按 judge 评估标准/标准答案调整结论）；重复候选浪费上下文；live 单元绕过冻结 hash 保护；`context_unit_count` 虚增（365 含 12 个非证据单元）。
2. 顺带确认合理的部分：index catalog 在完整上下文重复 4 次（system 提示 + 2 工具 description + index_key 参数描述，≈2319 chars 冗余）——低危；`top_k_per_query` 实际 3 与 policy 声明 5 不一致（authority 有意收窄）——信息性；工具名 `investigation_search_index` 与 prompt 一致；schema marker 仅 1 次、governance snapshot 与模型所见逐字节一致。

## 验证清单（十七轮）

- [x] 复现：authority search 可命中并 load judge_evaluation/judge_boundary（含全文）
- [x] spec/alg/authority.md §4.2 逐字核对（证据空间定义）
- [x] 无测试断言 authority env 依赖 judge assets（test_authority_runtime 等均用 mock 候选）
- [x] review 记录更新：`impl/projects/client_search/draft/.state/judge/context-governance/authority-recheck-2026-08-09.json` 新增 AUTH-R17-001

## 复查（check 十八轮）AUTH-R17-001 修复落地

1. `impl/core/authority_environment.py::build_authority_environment` 不再把 `role_asset_context_records` 注册进 Authority 运行时——证据空间回归 manifest 物化 + 本次 Tool 物化结果（spec/alg/authority.md §4.2）；同步移除 asset 指纹与 import。
2. `_invalidate_stale_evidence_refs` 扩展为证据空间级失效清理：除 manifest 旧 ref 外，历史 `role_asset`/`runtime_tool` 残留单元在 env 构建时确定性置 inactive——旧代码注册的 live judge 资产与旧 case 工具结果不会残留进当前搜索空间（修复对既有 DB 持久生效，非一次性改库）。
3. 实测：`judge_evaluation/judge_standard/judge_boundary` status=inactive；`search("evaluation")` 仅返回冻结 manifest 单元 `project-evaluation-contract`（不再出现 live 副本）；`context_unit_count` 365→353；值级检索（"在职有效客户"→value-mappings）不受影响。

## 验证清单（十八轮）

- [x] test_authority_runtime/tool/gate/investigation_gates/key_index/enhanced_rules 82 passed
- [x] judge 消费回归 43 passed（唯一失败为已知 business-field-enums 哈希漂移，非本轮改动）
- [x] ruff 全绿（authority_environment.py）
- [x] review 记录 AUTH-R17-001 closed（含验证证据）

## 模拟实测（check 十九轮）authority 实际可用性端到端验证

脚本化模型真实驱动工具链（search→load→search_index→load_entry→load→裁决），走当前代码（warn policy + 确定性 embedding）构建的真实 Environment：

1. **场景 A（能力/职责边界，提问模式）**："客户搜索产品是否支持按盘客搜索目标客户？"
   - 工具链：`search_context_units`(1576 chars) → `load_context_units`(10024 chars，含字段切片全文)
   - 裁决：`resolved`「职责内能力缺失（当前不支持）」，statement 符合 authority.md §5/§8.2 三类结论之一
   - basis=`authority-ref-e680951a0dde4509`，`ref_loaded_unchanged=True`（真实往返、hash 未变）
2. **场景 B（标准冲突，claim 担保模式 + coverage-gap 导航）**："多个合理映射且无法唯一选择应如何裁决？" + claim
   - 工具链：`search_context_units` → `load_context_units`（无决定性）→ `investigation_search_index`(authority.material-decisions) → `investigation_load_entry`（命中 coverage-gap）
   - 阶段2：`tools_override=[]` 强制无工具；user 仅 `claim`+`context_coverage`+`independent_resolution`；`context_coverage` 确定性派生（searched=true/candidate_count=10/loaded_count=1）
   - 裁决：`gap_only` + `required_evidence`（正式审批或覆盖声明），basis 可核验，governance mode=draft
3. **门禁实证**：脚本第一次让"搜到候选不立即 Load"直接跳导航 → 被 `_validate_authority_tool_sequence` 以 `AuthorityToolProtocolViolation` 拦截；改成合规顺序后通过——协议不只是提示，是运行时强制。

## 验证清单（十九轮）

- [x] 场景 A：resolved + 可核验 basis + statement 合规
- [x] 场景 B：unresolved/gap_only + required_evidence + 阶段2 无工具窄域 + context_coverage 信号
- [x] 序列门禁拦截非合规工具顺序（实证）
- [x] 两场景均基于真实 Environment（当前修复后代码），值级检索/导航/裁决全链路闭环

## 复查（check 十九轮）authority 全理论分支 mock 实测

用真实 env（warn policy + DeterministicHashEmbeddingProvider）+ 注入 mock LLM，31 项全分支模拟实测，**31/31 PASS**。覆盖：提问模式 10 项（resolved/unresolved/无 basis/编造 basis/未 Load/部分无效/缺 statement/statement 并入 reason/空问题/LLM 失败）、claim 担保 6 项（supported/contradicted/ungoverned/gap_only/状态不兼容/缺字段）、工具序列 5 项（合法链 2 + 拦截 3）、值级检索 runtime 闭环（key=orphanType→load→basis 可引用）、coverage-gap 导航闭环（load_entry 返回 coverage_gap+basis_search_hints）、证据空间边界（live judge 资产 inactive）、调用间 trace 隔离、同问题去重、gate 消费 3 项（unresolved→not_evaluable / 引用缺失→needs_human_review / tool_failure）、governance 快照 2 项。

实测暴露 2 个真实机制点（未改，等拍板）：

1. **AUTH-R17-002（低-中危）`context_coverage.has_candidate` 恒为 True**：构建期 `build_material_decision_key_index_registry` 预解析 material-decisions 的 load_targets 时经 `run.selection_refs_for_context_units` 把 6 个来源单元计入 `_debug["candidate_ids"]`（导航寻址被计入"搜索候选"）。后果：prompt 中"has_candidate 与 has_loaded 均 false → ungoverned"的信号条件在真实运行时不可达，CG-ENG-007"ungoverned/gap_only 分类可审计"信号失真（无任何检索/加载时 has_candidate 仍 true，模型只能靠语义区分）。修复方向：`selection_refs_for_context_units`（导航 load_targets 是精确定位地址，非搜索候选）不再计入 debug candidate_ids。
2. **AUTH-R17-003（低危）ungoverned/gap_only 专属缺料文案是死代码**：`_normalize_independent_resolution` 在 unresolved 时已兜底补默认 `required_evidence`，使 `resolve_authority` 里 `if not required:`（ungoverned→"补充能够管辖该主题的权威资料…"、gap_only→"补充当前管辖范围内缺失的决定性证据…"）恒不执行，实际返回通用文案"补充可裁决该判断点的权威资料"。语义略弱但非空、非阻断。修复方向：删除死分支或按分类覆盖文案。

模拟脚本：`/tmp/authority_sim_matrix.py`（31 项断言矩阵，可复跑）。

## 验证清单（十九轮）

- [x] 31/31 mock 实测 PASS（全理论分支）
- [x] 值级检索闭环（search_index→load_entry→load→basis 引用）与 coverage-gap 导航闭环复跑
- [x] AUTH-R17-001 修复在实测中确认（live judge 资产 inactive、搜索不再出现 live 副本）

## 复查（check 二十轮）draft vs production：authority 定位与效果实测对比

同一批冻结真实 case（judge-badcase-final-30）+ 同一套 mock judge LLM 行为，
对比 production（无 authority）与 draft（authority 可用/消费/忽略/伪造）的最终判定。
脚本：`/tmp/authority_draft_vs_production.py`（可复跑，离线，确定性 embedding）。

### 实测结论（9/9 PASS）

| case | production（无 authority） | draft D1（消费 authority） | draft D2（忽略 authority，确定性门禁） |
|---|---|---|---|
| 003 在职单（normal） | fulfilled | 无 authority 工具（无候选信号，不暴露） | fulfilled（与 production 一致，无回归） |
| 008 孤儿单（资料冲突） | fulfilled（零审计） | authority supported → fulfilled + 真实 basis | 无确定性门禁（资料冲突类靠 LLM 自觉调用） |
| 023 少儿万能险（操作符冲突） | fulfilled（零审计） | authority gap_only → not_evaluable | operator fail-closed → not_evaluable + 人审 |
| 088 7月盘客（能力边界） | not_fulfilled（零审计） | authority resolved 职责外 → not_evaluable | boundary gate → not_evaluable |
| 113 东莞何叶（空语义载体） | fulfilled（零审计） | authority unresolved → not_evaluable | 无确定性门禁（依赖 LLM 自觉） |

- resolved/supported → Judge 保留判定，basis 为真实物化单元（可核验）；
- unresolved 类 → 依赖项 not_evaluable，不输出肯定结论（spec §2 消费义务成立）；
- 伪造 authority_tool_call_ids → authority_reference_missing + needs_human_review 拦截；
- 无候选信号（normal case）→ authority.resolve 工具不暴露，draft 与 production 判定一致。

### 新发现 AUTH-R17-004（medium，已记录）

**gate 未消费 claim 担保模式的 ungoverned/gap_only/contradicted**：
`apply_authority_gate` 只对 `resolution.status == "unresolved"`（提问模式）强制降级。
实测（直接 gate 单测）：

| resolution.status | assessment=fulfilled → gate 后 |
|---|---|
| unresolved | not_evaluable + authority_unresolved |
| ungoverned / gap_only | **fulfilled（未降级，零 marker）** |
| contradicted | **fulfilled（未拦截，零 marker）** |

spec/grill/authority.md §2.2 要求 ungoverned/gap_only 必须强制降 not_evaluable；
§4.2-2 要求 contradicted 的肯定性 verdict 不得成立 + needs_human_review。
claim 模式是标准断言担保的主通道，该缺口使"真查证过仍不足"的硬校验只对提问模式生效，
Judge LLM 失误（拿到 gap_only 仍判 fulfilled）时过度自信结论直接穿透。

修复方向：gate 的 status 判定扩展为
`{'unresolved','ungoverned','gap_only'} → not_evaluable + authority_unresolved`；
`{'contradicted'} → 肯定性 verdict 拦截 + needs_human_review`；supported/resolved 不覆盖。

## 复查（check 二十一轮）authority 结论正确性 2×2 mock 实测

脚本：`/tmp/authority_correctness_2x2.py`（离线、确定性 embedding，可复跑）。
目的：不只验证"有没有用 authority"，而是验证 **authority 出的结论对不对**（使用 × 判断对错）。

| 象限 | 构造 | 最终 overall | 机制行为 |
|---|---|---|---|
| A 使用+对 | 008 资料冲突，authority 正确 unresolved | not_evaluable | gate 强制降级 + authority_unresolved 证据 |
| B 使用+错 | 008 资料冲突被错判 resolved（basis 真实可核验） | fulfilled | 机制信任 authority，错误结论被消费（模型/资料质量边界，gate 无法兜底） |
| B1 使用+无据 resolved | resolved + 编造 basis | not_evaluable | basis 校验自动降级 unresolved → 拦截（诚实性防线生效） |
| C 没用+对 | 003 normal，judge 自己判 fulfilled | fulfilled | 无 authority 也正确，与 production 一致 |
| D1 没用+错 | 023 操作符冲突 judge 误判 fulfilled | not_evaluable | operator 门禁 fail-closed + 人审 |
| D2 没用+错 | 008 资料冲突 judge 误判 fulfilled | fulfilled | 无确定性门禁，错误结论与 production 一样穿透 |

结论：authority 正确性有两道防线——无据 resolved 会被 basis 校验拦截（B1）；但"真实 basis + 结论错"无法被机制发现（B，信任边界），只能靠调查/固化资料供应链与模型质量；不调用时确定性门禁只覆盖 operator/boundary 类（D1），资料冲突/空载体类穿透（D2），依赖 judge 自觉调用 authority（AUTH-R17-004 修复后至少"调用了"的 case 会被 gate 兜底）。

## Draft Loop 对比表规范（已落地）

- 新增 `verifier/.agents/skills/draft/scripts/render_loop_comparison_table.py`：从冻结 iteration-cases + run report 确定性渲染 Current/Draft 逐 case 对比表。
- `SKILL.md` Draft Loop 节：每轮 review 必出对比表，基础列固定 `case / query 输入 / live 输出 / production <role> 结果 / draft <role> 结果`，场景列按被测场景扩展（judge 权威场景自动追加 authority 列，其他场景 `--scenario-columns` 注入）。
- `MAP.md` 文件映射已登记；已用 history/024 真实 run 验证渲染（30 行 + 自动 authority 列）。
- 注：`.agents/` 目录未被 git 跟踪（既有状态），改动在运行时生效。

## 复查（check 二十二轮）authority 效果问题修复（上下文工程重点）

修复 3 项（均已验证、findings 转 closed）：

1. **AUTH-R17-004（effect 核心）** `impl/core/authority_gate.py`：gate 新增
   `_UNRESOLVED_RESOLUTION_STATUSES={unresolved, ungoverned, gap_only}`，claim 担保模式
   的 `ungoverned/gap_only` 与提问模式 `unresolved` 同口径强制降 `not_evaluable` +
   `authority_unresolved`（evidence 带 `resolution_status`）；`contradicted` + 肯定性
   verdict → 降 `not_evaluable` + `authority_contradicted` + `needs_human_review`；
   否定性 verdict 不受罚；`resolved/supported` 不覆盖。此前 judge 拿到 `gap_only` 仍误判
   `fulfilled` 会直接穿透，现在被 gate 兜底。
2. **AUTH-R17-002（上下文工程信号）** `impl/core/context/runtime.py`：
   `selection_refs_for_context_units`（导航寻址）不再计入 `_debug["candidate_ids"]`；
   `candidate_ids` 只记录真实 `search_context_units` 命中。fresh env 实测
   `has_candidate` 从恒 True 恢复为 False，phase-2 prompt 中
   "has_candidate 与 has_loaded 均 false → ungoverned" 的分类信号重新可达
   （CG-ENG-007 审计信号失真修复）。
3. **AUTH-R17-003（上下文文案）** `impl/core/authority_environment.py`：
   删除 `resolve_authority` claim 分支的 `if not required:` 死代码；`ungoverned/gap_only`
   仅清空 statement，`required_evidence` 继承独立裁决兜底默认。

验证：test_authority_gate/context_runtime 52 passed；test_authority_runtime/tool 45 passed；
authority+key_index+judge 消费 75 passed（3 失败均为已知 business-field-enums 漂移，
用户已拍板不处理）；31 分支模拟矩阵 31/31 PASS；ruff 全绿。
新增测试：`test_claim_mode_gap_only/ungoverned/contradicted/supported_*`（gate 4 项）、
`test_navigation_refs_do_not_pollute_search_candidates`（runtime 1 项）。

## 复查（check 二十三轮）fulfilled.md 三态消费落地（authority 效果问题根修复）

用户核对口径：nf/ne 边界已在 `spec/alg/fulfilled.md` 定死（§3 第二步：resolved=职责外→说不清；resolved=职责内能力缺失+期望未达成→没办成；unresolved→说不清；authority.md §8.3 同口径）。真实 039 run 中 4 个 authority 参与 case 有 2 个消费反（50% 错误率）：

| case | authority 裁决 | fulfilled.md 应判 | 039 draft 实际 | 修复后 |
|---|---|---|---|---|
| 088 7月盘客 | 职责内能力缺失 | nf | ne（逃逸归责） | **nf**（authority_capability_gap） |
| 113 东莞何叶 | 职责外 | ne | nf（过度归责） | **ne**（authority_boundary_outside） |
| 133 中银保信 | 职责外 | ne | ne | ne（不人审） |
| 023 少儿万能 | 依据不充分（gap_only） | ne | ne | ne |

落地 3 项（AUTH-R19-001/002/003，均 closed）：

1. **AUTH-R19-001（消费根修复）** `impl/core/authority_gate.py`：按 resolution statement 结论类型前缀确定性三态消费——职责外→not_evaluable（无论 judge 判定，append authority_boundary_outside）；职责内能力缺失→judge 判 not_evaluable 时修正 not_fulfilled（无 unresolved/tool_failure/引用错误时，append authority_capability_gap）；职责内正常→不覆盖。
2. **AUTH-R19-002（explicit_unsupported 冲突修复）** `impl/projects/client_search/draft/judge.py`：`_apply_explicit_unsupported_boundary_gate` 从「is_supported=false→强制 not_evaluable」改为「is_supported=false=职责内能力缺失=功能未实现→not_fulfilled」：judge 判 fulfilled（如实拒绝=办成）→修正 not_fulfilled；判 not_fulfilled→保持；已消费 authority→交 gate §8.3。
3. **AUTH-R19-003（上下文工程对齐）**：authority prompt 硬约束 statement 以「职责外：」「职责内能力缺失：」「职责内正常：」开头（gate 确定性解析前提）；judge prompt 补三态消费规则（039 判反的上下文根因）；修正 `_enrich_unsupported_boundary_evidence` decision_rule 残留旧语义文案。

验证：tests 122 passed（含 6 个新增三态消费单测）；31 分支矩阵全 PASS；ruff 全绿；端到端 `/tmp/verify_fulfilled_consumption.py` 四 case 全 PASS。记录已更新 `authority-recheck-2026-08-09.json`（15 findings，R19 三项 closed）。

## 复查（check 二十四轮）nf/ne 分界：authority 触发面漏洞修复（093/073 静默逃逸关闭）

用户核对口径：nf/ne 边界 fulfilled.md 已定死（§2.3 硬前提 1：职责外/依据不充分类"说不清"必须有 authority 调用记录，"没查证 ≠ 查不了"；§10 验收同口径）。逐项核对实现后确认一处真实漏洞并修复。

**漏洞（AUTH-R20-001，已 closed）**：`capability_or_responsibility_boundary:all_conditions_unsupported` 触发依赖 `request_notice_overlap` 词法重叠。请求是具体值、提示是字段标签时重叠为空（093 车牌：请求「贵C826N1」vs 提示「车牌号」）→ 不触发 → authority 未装配 → §8.3 三态消费 gate 不运行 → 职责外类 not_evaluable 无调用记录、无 `authority_required_not_consulted` 人审标记静默通过。同语义 088（「盘客」重叠命中）→ 职责内能力缺失 → nf；093 → 静默 ne——**同一 is_supported=false 语义，nf/ne 落位取决于词法重叠**。073（投保日期部分拒绝、保留 isBuyInsurance）同样因非 all_conditions_unsupported 不触发。

修复：`_authority_candidate_reasons` 新增两个确定性触发面（`impl/projects/client_search/draft/judge.py`）：

1. `explicit_unsupported_capability`（Key-Index Search→Load 已解析到 is_supported=false 字段）→ `capability_or_responsibility_boundary:explicit_unsupported_field`（覆盖 093，不依赖词法重叠）；
2. `acknowledges_requested_constraint`（系统拒绝/降级了请求自身约束，含部分保留）→ `capability_or_responsibility_boundary:unsupported_constraint_acknowledged`（覆盖 073，全拒为特例）。

验证：

| 验证项 | 结果 |
|---|---|
| 30 条冻结集触发面重扫 | 激活 5/30 → **7/30**（008/023/073/088/093/113/133） |
| 新增单测（2 项） | `test_candidate_triggers_on_explicit_unsupported_without_lexical_overlap` / `test_candidate_triggers_on_partial_acknowledged_unsupported` 全 PASS |
| 093 集成模拟 | 判 not_evaluable（结论类型：职责外）但不调用 authority → `authority_required_not_consulted` + needs_human_review，不再静默 |
| 相关测试集 | test_authority_gate / judge_investigation / blocking_aggregation / authority_quadrants：63 passed（1 失败为已知 business-field-enums 哈希漂移，已拍板不处理） |

**遗留（AUTH-R20-002，open，调查层）**：138（业务员归属维度）无确定性 runtime 信号（系统静默丢维度、无 notice/manifest 字段/reference）→ 仍不触发 authority；冻结 `authority-investigation-report.json` 仅 2 个覆盖缺口，未按 fulfilled.md §9.2 记录职责内外类问题（093/113/133/138/148）的覆盖缺口与 required_evidence。需调查层补职责边界 normative_rule 覆盖后，runtime 再评估是否需要「请求维度缺失」信号（依赖调查层缺口索引，不靠启发式）。§10 验收的 30 条冻结集全量重跑在修复后仍需以真实 LLM（或全量 stub）重出。

### 二十四轮补充：显式不支持 gate 补齐 093 类零条件兜底 + 073/093/138 重放验证

1. **gate 兜底补齐** `impl/projects/client_search/draft/judge.py` `_apply_explicit_unsupported_boundary_gate`：触发条件从「all_conditions_unsupported」放宽为「Key-Index 确认 explicit_unsupported_capability 且 supported_condition_count==0」——覆盖请求值/字段标签无词法重叠的零条件拒绝（093 车牌）。judge 判 fulfilled（如实拒绝=办成）→ 修正 not_fulfilled；部分保留条件（073）不兜底，留给 authority 现场裁决。
2. **新增单测** `probes/test_judge_authority_signals.py::test_explicit_unsupported_gate_covers_zero_condition_no_overlap`（验证 093 类 fulfilled→nf 修正）。

当前管线重放（stub 复现 039 judge 判定，跑 2026-08-09 代码）：

| case | authority_mode（修复后） | 039 judge 判定 | 当前管线最终 | 说明 |
|---|---|---|---|---|
| 073 投保日期 | on_demand（unsupported_constraint_acknowledged + enum_authority_space） | 核心 ne | ne + needs_human_review（not_evaluable_cause_missing） | 不再静默；生产环境 LLM 会现场调 authority 定职责外/能力缺失 |
| 093 车牌 | on_demand（explicit_unsupported_field） | 核心 ne | ne + needs_human_review | 不再静默；same |
| 138 业务员归属 | not_required（无确定性信号） | 业务员归属核心 ne | ne 无标记（静默） | 仍缺口，AUTH-R20-002 调查层待办 |

结论：nf/ne 分界的 authority 触发面漏洞已修复（093/073 不再静默逃逸），138 类「系统静默丢维度」需要调查层职责边界覆盖缺口（normative_rule）支撑后，runtime 再评估是否需要「请求维度缺失」信号。

### 二十四轮补充：30 条冻结集当前代码重放（039 记录判定 + 修复后 pipeline）

用 039 run 记录的 judge 判定与 authority 审计，按生产一致条件（gate 仅 on_demand 装配时执行）重放 30 条：

| case | mode | production | draft(039) | draft(重放) | human_review | 说明 |
|---|---|---|---|---|---|---|
| 088 7月盘客 | on_demand | fulfilled | ne | **nf** | - | 职责内能力缺失→没办成（三态消费修正） |
| 113 公司名 | on_demand | ne | nf | **ne** | - | 职责外→说不清（三态消费修正） |
| 073 投保日期 | on_demand | nf | ne | ne | 投保日期筛选条件交付 | 修复后不再静默（旧 run 无调用记录） |
| 093 车牌 | on_demand | fulfilled | ne | ne | 车牌号条件搜索客户核心交付 | 修复后不再静默（旧 run 无调用记录） |
| 133 中银保信 | on_demand | fulfilled | ne | ne | 按公司名称检索中银保信目标客户 | 旧 run resolution statement 前缀不在句首（pre-R19 格式）→ fail-closed 人审；新 run 前缀约束下干净消费（E2E 已验证） |
| 138 业务员归属 | not_required | fulfilled | ne | ne | - | 仍静默：AUTH-R20-002 调查层待办 |
| 其余 24 条 | - | - | - | 与 draft(039) 一致 | - | 无 gate 修正 |

结论：§10 程序化断言（职责外/依据不充分 ne 均有调用记录或人审标记）在重放中成立（除 138 调查层缺口外）；30 条全量以真实 LLM 重跑仍待网络环境。

## 复查（check 二十五轮）nf/ne 上下文工程契约缺口修复（ne 成因标签 + not_applicable 词表对齐）

审计发现：`authority_gate` §8.4 只消费 judge 在 `actual_evidence` 显式输出的「结论类型：」标签，但 judge prompt 从未指示该契约 → LLM 不会写 → 所有非 authority 消费的 not_evaluable（含应豁免的输入坏/完全无关）都被标 `not_evaluable_cause_missing` + needs_human_review，豁免设计失效、差在哪儿依赖 LLM 自发书写。

验证（`apply_authority_gate` 直接模拟）：

| judge 输出 | gate 结果 |
|---|---|
| ne，无标签（当前 prompt 下 LLM 实际输出） | `not_evaluable_cause_missing` + needs_human_review（错误噪音） |
| ne，actual_evidence 含「结论类型：输入坏」 | 豁免，无人审标记（正确） |

落地 2 项（AUTH-R21-001，closed）：

1. **prompt 成因契约** `impl/projects/client_search/draft/judge.py`：`_build_core_context` system_prompt_extras 新增「not_evaluable 成因契约」段——五种标签（职责外/完全无关/依据不充分/输入坏/Authority 能力不可用）；职责外/职责内能力缺失/依据不充分必须真实调用 authority.resolve（无 authority 可用时不得自行判定）；依据不充分同时给缺料清单；完全无关/输入坏豁免。
2. **not_applicable 词表对齐** `impl/projects/client_search/draft/judge_execution.py`：`_not_applicable_judge_result` evidence 补 `cause=完全无关`（§10：完全无关→说不清（完全无关），不用"不评"绕过；verdict 本就是 not_evaluable，现在成因也进三态词表）。

验证：新增 `test_judge_prompt_contract_requires_not_evaluable_cause_markers`（断言 prompt 含五种标签 + 缺料清单）；更新 `test_candidate_reports_unrelated_request_as_not_applicable`（evidence 含 cause=完全无关）；相关测试集 73 passed（1 项为已知 business-field-enums 哈希漂移，已拍板不处理）；ruff 全绿。

剩余（持续）：AUTH-R20-002 调查层职责内外类覆盖缺口（138 静默丢维度，需调查流程补 normative_rule 后 runtime 再评估信号）；§10 30 条真实 LLM 全量重跑（网络环境）；CG-ENG-003 真实受治理 run 记录（网络环境）。

## 复查（check 二十六轮）AUTH-R20-002 关闭：调查层覆盖缺口 + runtime 缺口索引触发面

按 fulfilled.md §9 任务 2（补齐职责/能力权威依据；职责内外类问题以覆盖缺口记录，补齐前查不了一律按说不清）落地并验证：

**调查层（冻结产物）**
- `docs/authority-investigation-report.json`：覆盖缺口 2 → 6，新增 4 个职责内外类缺口（`responsibility-boundary-unsupported-field` / `responsibility-boundary-entity-name-query` / `silently-dropped-request-dimension` / `enum-space-search-consumption-boundary`），`required_evidence` 均指向业务方确认的职责边界声明/下游接口声明；
- `docs/authority-investigation-report.md` 按 `render_authority_report_markdown` 确定性重渲染；`manifest.json` key-indexes 经既有 `build_authority_key_index.py` 重生成（20 entries）；
- `validate_investigation_package` 通过（warn 策略，仅既有 3 条 evidence_content_drift）。

**runtime 触发面（公共机制，非启发式）**
- `impl/core/authority_key_index.py` 新增 `coverage_gap_trigger_hit`：请求文本在完整 material-decisions 索引中的唯一最高命中是 coverage-gap 时返回 gap_id（缺口内容由调查层固化，匹配与字段导航同一词法索引机制）；
- `impl/projects/client_search/draft/judge.py` `_authority_candidate_reasons` 消费为 `capability_or_responsibility_boundary:coverage_gap:<gap_id>`；judge prompt 补缺口消费规则（命中缺口且无新决定性证据 → unresolved → 依据不充分 ne + 缺料清单）。

**30 条冻结集精确触发面审计**（剥离 embedding 兜底标记，warn 策略；全量 context 构建无异常）：

| case | 触发信号 |
|---|---|
| 008 孤儿单映射 | conflicting_materials:value_mapping |
| 023 生日操作符 | operator_standard_conflict |
| 073 投保日期 | unsupported_constraint_acknowledged |
| 088 7月盘客 | all_conditions_unsupported + explicit_unsupported_field + coverage_gap |
| 093 车牌 | explicit_unsupported_field |
| 113 公司名 | coverage_gap(entity-name) + missing_semantic_carrier |
| 133 中银保信 | missing_semantic_carrier |
| 138 业务员归属 | **coverage_gap(silently-dropped)（原 not_required → 现 on_demand）** |
| 148 住院医疗保险 | **coverage_gap(silently-dropped)（原静默 → 现 on_demand）** |
| 其余 21 条 | not_required，无噪音触发 |

验证：新增 `test_coverage_gap_trigger_hit_requires_top_hit_gap`、`test_candidate_triggers_on_coverage_gap_for_silently_dropped_dimension`；相关集合 116 passed（仅剩既有 business-field-enums 哈希漂移失败，已拍板不修不回退）；138 authority 环境实测：authority_tool 装配、缺口可达（`coverage-gap://silently-dropped-request-dimension`）、snapshot 生成。138 真实 LLM 端到端（authority 现场 unresolved→ne(依据不充分)）待 30 条全量重跑确认。

剩余（持续）：§10 30 条真实 LLM 全量重跑（网络环境）；CG-ENG-003 真实受治理 run 记录（网络环境）；AUTH-R16-001/002/003、DRAFT-R16-004（低危，待用户决策）；fulfilled.md §2.3 093 示例 vs authority.md §8.3 规格张力协解（待 grill）。

## 复查（check 二十七轮）fulfilled.md §10 验收完成度审计

逐项核对 §10 验收与 §8 D1-D8 差距、§9 改造任务：

| 验收项 | 证据 |
|---|---|
| 三态 + 说不清带差在哪儿 | judge prompt 决策顺序 + not_evaluable 成因契约（五种标签）；gate 消费标签，缺标签 fail-closed |
| 职责内+期望未达成→没办成 | 三态 gate（`authority_gate.py`）+ `/tmp/verify_fulfilled_consumption.py` 四 case PASS |
| 职责外/依据不充分 ne 有 authority 调用记录 | §8.4 无调用记录→needs_human_review；138 E2E 实测：unresolved→ne(依据不充分) 带调用记录、无人审标记 |
| 完全无关→说不清（完全无关） | `test_candidate_reports_unrelated_request_as_not_applicable`（cause=完全无关，不用不评绕过） |
| 依据未定论判断点全部走 authority | 30 条精确触发面审计：9 on_demand（008/023/073/088/093/113/133/138/148），21 not_required 无噪音；0 静默 |
| 无逃逸路径 | 无必办项→不得办成（`impl/core/judge.py:148` + `test_judge_blocking_aggregation`）；如实拒绝≠办成（judge.py:648/681/690/1320） |
| 其他项目不回归 | deerflow/marketing/live smoke 33 passed |
| D7 旧词表统一 | `judge_boundary_protocals.md` 无"对/错/不确定"残留，全为三态词 |
| D8 调查合同三态 | `judge-investigation-contract.json` 每维度 fulfilled/not_fulfilled/not_evaluable 边界 + validator 互斥检查（重叠即报错） |

剩余（网络/决策阻塞）：§9 任务 8 的 30 条真实 LLM 全量重跑（需网络 + API 额度）；CG-ENG-003 真实受治理 run 记录（需网络）；AUTH-R16-001/002/003、DRAFT-R16-004（低危，待用户决策）；fulfilled.md §2.3 093 示例与 authority.md §8.3 的规格张力协解（待 grill，当前 interim 行为已与 §2.3 一致：边界类补齐前按依据不充分→说不清）。

## 复查（check 二十八轮）R16 实施 + fulfilled 落地复核

- [x] **AUTH-R16-001 闭包绑定（closed）**：`authority_key_index.py` loop 内 `validate_target` 改默认参数绑定 `_index=index`；`context_governance.py` `instruction_clause` 改 `_line=line`。消除 B023 类循环变量闭包隐患，行为零变化。
- [x] **AUTH-R16-002 hash 助手统一（closed）**：新增 `impl/core/hashing.py` 单一 `stable_sha256`（紧凑分隔符+sort_keys+default=str）；`context_governance`/`authority_investigation_gates`/`investigation_validation` 删除本地副本改复用；`authority_environment._sha256`（默认分隔符、持久化于 snapshot）按要求未动。字节一致，持久化 hash 全部保持有效。
- [x] **AUTH-R16-003 空合同扫描（closed）**：`scan_compiled_context` 新增 `output_contract_empty` blocking finding（注册输出合同零字段即 fail-closed）；历史记录路径未加（`field_names=[]` 表示未知而非空，已有 `output_contract_count` 兜底）。
- [x] **30 条触发面复算**：剥离 embedding 标记后与存档审计 0 diff（9 on_demand / 21 not_required），改动后运行时触发面无回归。
- [x] **138 E2E 离线重建重跑（`/tmp/verify_138_gap_e2e.py`）**：真实 138 trace + stub LLM 走真实管线：coverage_gap(silently-dropped) → authority unresolved → 核心交付 ne(依据不充分) 带调用记录、无人审标记，全 PASS。
- [x] **其他项目回归**：deerflow/marketing/live smoke/protocol 57 passed。
- [x] 测试：authority runtime/tool/gate/enforcement/investigation_key_index/draft_gate_feedback/judge_blocking 105 + context_governance/investigation_gates/investigation_key_index/solidify 90 + client_search_judge_investigation/context_governance 52 passed；仅剩已知 source_revision 与 business-field-enums 漂移失败（均与本次改动无关）。
- [x] ruff 全绿（hashing/context_governance/authority_investigation_gates/investigation_validation/authority_key_index）。

剩余（网络/决策阻塞，未变化）：§9 任务 8 的 30 条真实 LLM 全量重跑（需网络 + API 额度）；CG-ENG-003 真实受治理 run 记录（需网络）；DRAFT-R16-004 枚举源登记（改冻结 manifest，待用户决策）；fulfilled.md §2.3 093/113/148 示例与调查层未确认状态的张力（待用户拍板）；gate 信任边界疑问（职责内能力缺失+judge fulfilled 不兜底、resolved 无三前缀不 fail-closed、混合消费优先级）。

## 复查（check 二十九轮）真实全量重跑 + 过期 resume 污染根因与门禁修复

### 前置结论修正：原 093 env=missing 是"过期数据"不是运行时 bug
- **根因**：当前 `iterations/001-run.json`（上一版）30 行里 24 行是从 8-08 旧 `001-run.partial.json`（旧代码 `_runtime_snapshot` 早于 context_governance 快照）**字节级 resume 复用**，仅 6 行（113/128/133/138/143/148）为新代码重跑。093/008/048/083/123/073 等"env=missing / 无 authority"分歧全部来自这 24 行过期数据，不是当前实现的问题。
- **证明**：旧 partial 与上一版 24 行逐字节一致；直连 `instance.judge_trace(093)` 单跑（当前代码）env/tool 均正常并带 authority_runtime evidence；本版全量重跑后 093 等全部按当前触发面装配 authority。

### 修复：Draft resume 公共指纹门禁（统一机制）
- 新增 `.agents/skills/draft/scripts/fingerprints.py` 共享三档指纹：`current_fingerprint`（production 资产+impl/core）、`draft_fingerprint`（draft 资产/代码，不含 .state）、`runner_fingerprint`（runner 脚本，覆盖 `_runtime_snapshot` 等比较语义）。
- `run_iteration._load_resume_rows` 除 `frozen_cases_sha256` 外，新增三档指纹强校验：任一不符即 raise（`delete the partial and restart`）。直接 `--resume` 不再能复用过期行。
- `draft_loop._resume_candidate` 同步补 `runner_fingerprint` 校验；`persist_progress` 落盘 `runner_fingerprint`。旧函数从 draft_loop 删除，统一复用 fingerprints 模块（消除重复实现）。
- 门禁实测：`_load_resume_rows` 对旧 partial 正确拒绝（`different current_fingerprint`）；新增 2 项单测（accept/reject）全 PASS。

### 真实全量重跑（当前代码，30 条，workers=2，elapsed 2396.9s）
- resume 6 条有效行（113/128/133/138/143/148，带 context_governance 快照）+ 重跑 24 过期行。全 30 行均带 `context_governance`，无 error、无 human_review 标记。
- **触发面自洽**：draft 侧 `environment=ok` 恰好 9 个 case，与离线触发面审计"9 on_demand / 21 not_required"一致。
- **调用面修正（round 三十一补充核实）**：9 个 on_demand 中 8 个真实调用 authority.resolve；**023 例外**——触发 on_demand（`operator_standard_conflict:familyInfo.familyclientbirthday`）但主 LLM 0 调用。023 的 blocking 结论（产品条件缺失+多余约束）不依赖该运算符冲突（value_mappings 有 abbrname 依据），`not_called` 契约条款（blocking 结论依赖 trigger 时禁肯定性结论）不触发；属"触发但结论不依赖、未显式声明无关"的模型侧噪音，非可靠性缺陷，列为观察项。
- 分布：current {fulfilled 17, not_fulfilled 12, ne 1}；draft {fulfilled 11, not_fulfilled 13, ne 6}。

### 对比表（query / live / current / draft / authority）
| case | live（robot_text） | current | draft | draft authority | 分歧 |
|---|---|---|---|---|---|
| 008 孤儿单→纯存续单客户 | 纯存续单客户 | nf | ne | 2 次 tool_failure | draft 想用 authority 裁枚举冲突但工具失败→ne |
| 068 张和奎 45岁 | （生产 LLM 输出非法被阻断） | ne | nf | 0 | current ne 系 production 结构化输出校验失败；draft 给真值 nf |
| 073 投保日期暂不支持 | 提示投保日期不支持+按可支持字段搜 | fulfilled | nf | 2（真实裁决） | authority 定"职责内能力缺失"→draft 翻为 nf（本次 authority 真实改变边界判定） |
| 088 7月盘客/准客来源 | 提示盘客不支持 | fulfilled | ne | 2 tool_failure | 需 authority 裁 盘客 范围，工具失败→ne |
| 093 车牌号 C826N1 | 提示车牌号不支持 | fulfilled | ne | 2 tool_failure | reasoning 写"职责内能力缺失→nf"，assessment 因工具失败降 ne |
| 113 何叶 | 客户姓名何叶 | fulfilled | ne | 2 tool_failure | 需裁产品名边界，工具失败→ne |
| 133 中银保信 | 未识别到条件 | fulfilled | ne | 3 tool_failure | 机构名边界需 authority，工具失败→ne |
| 138 陈金秀在别业务员投保 | 客户姓名陈金秀 | nf | ne | 2 tool_failure | 业务员归属/产品维度需裁边界，工具失败→ne |
| 148 徐晓燕+住院医疗险 | 客户姓名徐晓燕 | fulfilled | nf | 1（真实） | authority 用字段定义确认 planfullname 应承载 住院医疗保险→被丢弃→nf（authority 证据驱动纠正，倾向更正确） |

### 结论与下一优先项
- authority 在当前代码下**可装配、会真实被调用、触发面与离线审计一致**；"env=missing"已彻底排除。
- 遗留最大问题不再是"是否装配/是否使用"，而是 **authority.resolve 工具可用性**：083/093/113/133/138/088 等多次 `AuthorityToolProtocolViolation: investigation_search_index candidates not immediately followed by investigation_load_entry`，模型未能按 Search→Load 顺序导航，导致 draft 诚实降级为 ne（Authority 能力不可用）——authority 的判定力被工具协议约束弱化。属上下文/工具工程问题，需作为下一轮优先修。
- 其它待用户拍板：draft loop 冻结 current 已漂移（state.frozen_current_sha256 仍为 d49b2a，当前实现 35ffbe，直接 CLI 重跑不受影响）；`decision` 仍为空；DRAFT-R16-004 枚举源登记；fulfilled.md §2.3 093/113/148 示例与调查层未确认状态张力。

## 复查（check 三十轮）authority.resolve 工具协议违例修复（导航校验放宽）

### 根因（真实工具日志证据）
- 093/008/088/113/133/138 的 ne 不是"环境缺失"，而是 authority.resolve 内部 agent 会话的 `AuthorityToolProtocolViolation`。dump 093 实际工具日志（`/tmp/093_tool_call_log.json`）：
  - `[0] search_context_units → [1] load_context_units`（正确）；
  - `[2] investigation_search_index`（material-decisions 命中 coverage-gap）→ `[3] investigation_search_index`（business-field-definitions，冗余）——**连续两次 search_index** 触发旧校验"must be immediately followed by load_entry"；
  - `[4] investigation_load_entry`（coverage-gap 条目，**内容自包含** `navigation_only: true`、无 load_targets）后停止。
- 模型导航意图合理：coverage-gap 条目本身就是"该边界无唯一决定资料"的裁定（gap_reason 明确点名 093/088 场景），内容即答案，无需再 Load。旧校验把"批量检索 + 自包含终态"误判为协议违例，整次 resolve 判废 → judge 诚实降 ne（Authority 能力不可用），拿不到 coverage-gap 的 required_evidence 缺料清单。

### 修复（`impl/core/authority_environment.py` `_validate_authority_tool_sequence`）
- 允许连续 `investigation_search_index` 批量检索；改为会话结束时不得有未消费的 key-index 候选（`outstanding_index_candidates` 兜底，`investigation_load_entry` 即消费）。
- `investigation_load_entry` 返回 load_targets 时仍需紧跟 `load_context_units`，**除非**条目 `navigation_only`（决策/gap 内容自包含）——此时可合法作为终态调用。
- 保留：首调用必须 search_context_units；search_context_units 候选必须立即 Load；非自包含 load_entry 终态仍拒绝。

### 验证
- 093 实际工具日志重放：新校验 PASS（旧校验 FAIL）。
- 单测：`test_authority_runtime.py` 44 passed（新增 4 项：批量 search_index 合法 / 批量未消费仍拒绝 / navigation-only 终态合法 / 非自包含终态仍拒绝）；`test_authority_gate` + `test_authority_tool` 合计 74 passed。
- ruff 待跑；真实 LLM 复验（093 单 case + 6 个受影响 case 重跑）待审批（审批网关 502 拦截一次，未绕过）。

## 复查（check 三十一轮）修复后全量 30 条真实重跑终验（AGENTS.md 复核）

### 运行事实
- 当前代码全量重跑（无 resume，指纹门禁强制全量）：30 rows，elapsed 4615.3s，workers=2，无 error、无 human_review 标记。
- draft 侧 `environment=ok` = 9，与触发面审计"9 on_demand / 21 not_required"一致；其中 8 个真实调用 authority.resolve（023 触发 on_demand 但 0 调用，其 blocking 结论不依赖该 trigger，见观察项）。
- 分布：current {fulfilled 16, nf 14, ne 0}；draft {fulfilled 11, nf 13, ne 6}。

### 修复效果（对比修复前）
- **093/113**：authority.resolve 由 tool_failure 变为真实裁决（unresolved/gap_only），draft ne 成因从"Authority 能力不可用"升级为"依据不充分 + 缺料清单"（evidence_refs.kind=authority_unresolved，含 required_evidence）。
- **073**：authority 裁决"职责内能力缺失"→ draft nf（current 同 nf）。
- **148**：authority 裁决"职责内正常"→ 险种条件被静默丢弃属核心未达成 → draft nf。
- **088/133**：虽有 1 次残留 tool_failure，但有成功裁决（unresolved/gap_only）可消费，ne 成因"依据不充分"。
- **008/138**：仍 2 次 tool_failure（008 模型 search 后未立即 Load；138 复杂三维度导航 10 次撞预算 8）→ ne"Authority 能力不可用"，诚实 fail-closed，非上下文工程缺陷。

### 残留项（诚实标注，不追 LLM 合规性）
- 008/138 的 authority 内部导航仍存在模型合规性失败；已评估：加提示/加预算属追模型行为，收益不确定且增加成本，按 AGENTS.md"最简单实现"不再追加，留作模型侧观察项。
- 023 触发 on_demand（operator_standard_conflict）但 authority.resolve 0 调用；blocking 结论不依赖该 trigger，`not_called` 条款不触发，最终判定合理。模型未显式声明"该 trigger 与结论无关"，属合规性噪音，留作观察项。
- draft loop 冻结 current 已漂移（state.frozen_current_sha256=d49b2a vs 当前 35ffbe）；direct CLI 不受影响，loop 正式迭代需用户拍板重冻结。
- `decision` 仍为空；DRAFT-R16-004 枚举源登记、fulfilled.md §2.3 示例张力待用户拍板。

### 测试与质量（本轮改动）
- `test_authority_runtime` 44 passed（含 4 项新导航 case）；`test_authority_gate`+`test_authority_tool` 合计 74 passed；ruff 绿。
- 新增公共设施 `fingerprints.py`（current/draft/runner 三档指纹）+ resume 门禁：`test_draft_loop` 23 passed（含 2 项新门禁 case）。

## 复查（check 三十二轮）§10 程序化验收审计 + 治理快照键名核实

### governance_enabled=None 误读澄清
- 早前初审把 `context_governance` 快照读成 `governance_enabled=None`，系键名误读。该报告键不在 `context_governance_report` 顶层；正确字段为 `gate.mode` / `gate.blocking`（`build_context_governance_report` 定义，`impl/core/context_governance.py`）。
- 核实：当前 30 行每行 current/draft 两侧均落 `context_governance` 快照（共 60 份），全部 `gate.mode=draft`、`gate.blocking=False`，且 `snapshot.compiled_prompt_sha256` 每份完整（60/60）。治理快照 30/30 行生效，无遗漏。

### 30 条 ne 全量口径复核（正确键名重扫）
- 取 `summary.fulfillment_status` 判分，draft 分布：fulfilled 11 / not_fulfilled 13 / not_evaluable 6（非简写 ne），与 round 三十一 一致。
- `not_evaluable` 6 条 = 008/088/093/113/133/138，全部有 authority 真实调用记录（`authority_tool_call_ids` 非空，`draft from zero without authority`）：无游离 ne。
- ne 成因信号逐案复核（用真实字段 `resolution`/`independent_resolution`/`tool_failure`，非旧 `outcome` 猜测键）：
  - 088（2 调 / 1 tf）：1 次真实裁决 unresolved + 1 次残留 tf，有成功决议可消费 → 依据不充分。
  - 093（1 调 / 0 tf）：真实独立裁决 unresolved/gap + 缺料清单（`required_evidence`=业务方职责边界声明）。
  - 113（1 调 / 0 tf）：真实裁决 unresolved，缺业务方职责边界声明。
  - 133（3 调 / 1 tf）：1 次真实 unresolved + 缺料清单；1 次 tf 残留，有成功决议可消费。
  - 008（2 调 / 2 tf）：fail-closed"Authority 能力不可用"，无实决议。
  - 138（2 调 / 2 tf）：fail-closed（含 `tool_budget_exceeded`），无实决议。
- 结论：ne 不再全部归罪"能力不可用"；093/113/133/088 已升级为"依据不充分 + 缺料清单"，与 round 三十一叙述一致。008/138 为诚实 fail-closed，非上下文工程缺陷。

### §10 验收（对齐 fulfilled.md §10 散文条目，程序化断言）
- [x] 三态全覆盖：30 条全部落到 fulfilled / not_fulfilled / not_evaluable 之一；每案带 `summary.reason`（"差在哪儿"）。
- [x] ne 必带差异成因：6 条 not_evaluable 的 `summary.reason` 均可归到"依据不充分 / 职责边界未决"；无职责外/完全无关误收（客户搜索无天气类无关案）。
- [x] 职责内+期望未达成 → not_fulfilled 且理由可归因：nf 13 条 `summary.reason` 均点明核心交付未达成并指出缺口（如 048 遮码前缀被遗漏、结果集过宽），供列入长期优化点。
- [x] 依据未定论判断点全走 authority：9 个 on_demand 中 8 个有 `authority_tool_call_ids` 且非空；023 触发但 0 调用（blocking 结论不依赖该 trigger，`not_called` 条款不触发，观察项）；`_formal_runtime_failures` 无异常（无 error / 无 human_review），非 0 激活。
- [x] authority 依据链可回溯：authority 调用对应 audit 存在 `resolution`/`independent_resolution`（真实裁决，含 basis_evidence_ref_ids）或 `tool_failure`（fail-closed）；`authority_resolve` 证据带 coverage_gap + required_evidence。
- [x] 无逃逸路径：ne 不落 fulfilled，nf 全部职责内未达成；30 条冻结集全量重跑、draft 无退化（draft 相较 current 增加 6 条诚实 not_evaluable / 修正若干）。

### 遗留（仍待用户拍板/观察）
- 保持 round 三十一残留：draft loop 冻结 current 漂移、`decision=null`、DRAFT-R16-004 枚举源登记、fulfilled.md §2.3 示例张力。
- 008/138 内部导航模型合规性噪声作观察项，不追预算/提示改造。
## 最终移交要点
- 代码侧 authority 工具协议违例、resume 过期污染、指纹门禁均已修复并经真实 30 条重跑终验。
- 上下文工程目标达成：ne 成因从"能力不可用"收敛为"依据不充分+fail-closed"，authority 真实发挥作用。

## 复查（check 三十三轮）新冻结仓 30 条全量重跑（08-10，source=b4ffbb62）§10 复扫

### 数据源
- `impl/projects/client_search/draft/.state/judge/iterations/001-run.json`（frozen `bf9e77ee`，current_fingerprint `72722705`，workers=2，0 error/0 human_review）。
- 与 round 三十二 的旧 run 差异：新 run 修了 088（authority=supported → 职责内能力缺失 → not_fulfilled），ne 由 6 条收敛为 5 条。

### 新 run 判定分布
- current：fulfilled 17 / not_fulfilled 13。
- draft：fulfilled 12 / not_fulfilled 13 / not_evaluable 5（008/093/113/133/138）。
- 翻转：123 (nf→fulfilled，修复误判)；088/148 (fulfilled→nf，authority 证明可支持被拒)；093/113/133/138 (fulfilled→ne)；008 (nf→ne)。无反向退化。

### §10 机械断言（新 run 复扫）
- [x] 三态全覆盖：30/30；每案 `summary.reason` 带"差在哪儿"。
- [x] 5 条 ne 均有 `authority_tool_call_ids` 非空、`environment=ok`、gate 不阻断、findings=0：无游离 ne、无 0 激活。
- [x] nf 13 条 reason 均可归因职责内未达成（048/068/143 等，供列长期优化点）。
- [ ] **113/133/138 依据链可回溯性未达**：113=2×tool_failure、138=2×tool_failure、133=gap_only+1×tool_failure、148=1×tool_failure（tool_budget_exceeded）。除 133 的 gap_only 外，tool_failure 无 required_evidence 缺料清单、证据链回不到实际 Load，不满足 §10"依据链可回溯 + 缺料清单"的严格栏。

### 与 round 三十二 的关键 delta（必须记录）
- **113 从"1 调 0 tf 真实 unresolved + 缺料清单"退化为"2 调 2 tf"**；133 从"3 调 1 tf 有真实 unresolved"退化为"gap_only + 1 tf"。同代码、同冻结集，差异来自模型导航行为漂移（search 后未紧跟 load / key-index 候选悬空）。
- 008/138 维持 fail-closed（nav 噪声观察项，按既有决策不追）。
- 含义：§10 严格栏能否通过取决于"tool_failure 是否计入可审计依据"。按 authority.md §8.4 tool_failure→ne 是设计行为；按 fulfilled.md §10 则缺缺料清单。此为待用户拍板的规格张力（见 001-review-recommendation.draft.md），不做单方面放宽。

### 结论
- 上下文工程目标继续成立：ne 全部带 authority 调用记录、无逃逸、无 0 激活；draft 相对 current 无业务退化且有 3 例方向性修复。
- 但 iteration 001 不足以判"可证明改善"建议选中：3/5 ne 为 tool_failure，依据链未达 §10 严格栏。review 建议 decision=insufficient_evidence、route=investigate。

## 复查（check 三十四轮）非端点型 authority 执行失败 → unresolved+缺料清单（已落地）

### 修复
- `impl/core/authority_tool.py`：`AuthorityTool._execute` 现在把**确定性查证失败**
  （`AuthorityToolProtocolViolation` 导航违例、`tool_budget_exceeded` 工具预算耗尽）
  归一为 `unresolved`（提问模式）/ `gap_only`（claim 模式）的 resolution，并带
  material-positioning 口径的缺料清单（需业务方确认的 normative_rule/external_fact/
  已登记 inlive_boundary 声明 + 完整 Search→Load 查证记录）。
- 端点/瞬时故障（5xx/限流/超时）与未知错误仍保持 `tool_failure` fail-closed，不归一。

### 动机
- 原实现把这类"模型没完成查证"硬拒成 `tool_failure` + 空 `required_evidence`，
  使 113/133/138/148 的 ne 缺缺料清单、证据链回不到 Load，过不了 fulfilled.md §10。
- 既符 authority-minimal-chain.md §8（工具执行失败→业务 unresolved+reason 说明缺什么），
  也符 material-positioning.md（缺料标定位类别）；不改 prompt、不追模型导航噪声。

### 效果（确定性测试证明）
- `test_authority_runtime.py` 新增 3 用例：协议违例→unresolved+缺料、预算耗尽+claim→gap_only、
  瞬时 5xx→仍 tool_failure。权威三层测试 76 + draft_loop/context_governance 40 = 116 全绿，ruff 干净。

### 待办
- 001-run.json 仍是修复前的数据（113/133/138/148 为 tool_failure）。需以真实 LLM 重跑
  冻结集，确认这 4 条 authority 变为 resolved 类 `unresolved/gap_only`（带缺料清单）后，
  §10 依据可回溯栏通过。重跑需放行 LLM 网络审批。

### 离线回放（无 LLM，基于 001-run.json 既有 6 条 tool_failure）
- 对新分类逻辑重放 6 条既有 tool_failure：**全部** → `unresolved/gap_only + 缺料清单`。
- 明细：113×2（协议违例）、138×2（协议违例）、133×1（key-index 候选悬空）、148×1（tool_budget_exceeded，claim→gap_only）。
- 重跑预期：113/133/138 的 ne 从"authority 不可用"变"依据不充分 + 缺料清单"，§10 依据可回溯栏可过；148 的 authority 调用不再 dead-end。最终裁决受 judge 业务消费影响，仍以真实重跑为准。
