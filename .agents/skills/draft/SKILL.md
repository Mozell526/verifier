---
name: draft
description: 围绕 objective 调查真实业务项目，固化为候选 Role/Context/Tool，在冻结数据上持续比较 current/draft，有把握的净胜才建议进入 promotion 检查。
---

# Draft Skill

长期协议以 `spec/alg/investigate.md` 为准；原有 Draft 思想见 `spec/draft/draft.md`。Draft 是统一控制面，不新增独立 Investigate Skill 或 Agent。

## 四个阶段

```text
Investigate → Solidify → Draft Loop → Promote
Harness AI   Harness AI   Skill+协议    用户授权的协议代码
```

- Investigate：Codex/Claude Code 等工程型 AI 自由调查真实业务项目，交付标准调查包；不修改候选 Role。
- Solidify：Harness AI 将已验证调查结果固化为 `draft/<role>.py`、ContextUnit 和 VerifiableTool。
- Draft Loop：协议在冻结条件下运行 Current/Draft，Skill 按 objective、review、真实实验和用户反馈持续判断并路由修订。
- Promote：只在用户明确确认后由确定性协议代码搬运已配置文件；不调用 LLM，不临场选文件。

## 用户命令语义

```text
/draft start --project <id> --role <role> --mode interactive|managed
/draft status
/draft investigate [补充方向]
/draft continue [补充方向]
/draft solidify
/draft loop
/draft test
/draft switch --mode interactive|managed
/draft stop
/draft promote
```

这些是 Skill 交互命令，不要求新增 HTTP API 或 CLI parser。`/draft test` 只运行一次协议测试，不修改候选；独立 `/draft review` 不是默认阶段。

## 启动与 Role 契约

读取 DraftConfig 的 `project_id/role/objective/material/mock_source/review/max_iterations/report_path`。`role` 必须存在对应 `.agents/skills/draft/<role>/ROLE.md`；先读 ROLE.md，再调查。ROLE.md 决定材料权限、EvidenceRef/ToolRequirement/artifact/unresolved 的有效性标准，公共 Manifest 不按 Role 派生。

半交互模式在调查收敛点和每轮 Loop 后暂停；全托管模式可在预算内连续 Investigate/Solidify/Loop。两种模式都不得自动 Promote、修改 frozen data 或降低 review 标准。

## Investigate

Harness AI 可以搜索源码、阅读文档、分析业务 trace、调用 API、写临时脚本和做实验，但必须遵守 ROLE.md 材料边界。输出固定在：

```text
impl/projects/<project>/draft/investigation/<role>/
  manifest.json
  overview.md
  docs/...
```

Manifest 使用 `InvestigationManifest`，只索引真实 `EvidenceRef`、`ToolRequirement`、artifacts 和 `unresolved_reason`。Judge 必须登记 `docs/judge-investigation-contract.json`，Mock 必须登记 `docs/mock-investigation-contract.json`；两者分别是该 Role 调查语义的唯一真相源。Judge 还必须登记 `docs/authority-investigation-report.json`（结构化真相源）与 `docs/authority-investigation-report.md`（由 JSON 确定性渲染），并分别以 `judge_authority_investigation_report_json` / `judge_authority_investigation_report_markdown` 逻辑路径登记到 `artifact_refs`。报告以 `materials` 为第一组织维度：每份资料声明它在哪个 `conclusion_kind + scenario + conditions` 组合内直接决定什么（`governs`），`related_to` 只列仅相关事项；`coverage_gaps` 只记录当前资料在“业务事项 × 条件”上的覆盖缺口及所需补证。调查期不得预枚举未来 Case 的 Authority 问题，也不得产出 Runtime 的 resolved/unresolved 结论稿；最终裁决由 Judge Runtime 针对当前 Case 按需调用 `authority.resolve`。报告是导航摘要，不复制文件内容、不含任何 case 的 actual/score/verdict；物化后的原始资料才可进入运行时 `basis_evidence_ref_ids`。模板与渲染脚本见 `MAP.md`；语义细节以 `spec/alg/investigate-authority-judge.md` §8-15 为准。大型内容留在文件或来源系统；Callable 不进入 JSON。Attribute 业务链使用同名 `.mmd + .md + .trace.json` 三件套，并全部登记到既有 `artifacts`；不得增加 Manifest 专属 trace 字段。`.trace.json` 用稳定 ID 记录节点责任、输入/输出、边上传递的数据以及 EvidenceRef/ToolRequirement 引用；`.mmd` 保存同一业务拓扑；`.md` 必须同时提供 `How to use this trace map`、`Operational index` 和 `Investigation procedure`。Operational index 列出每个节点的 input/output data IDs、当前 trace 信号、验证能力和证明边界。其他 Role 不被迫生成 Attribute 内部链路图。只有节点名称和关系线不算可消费的调查产物。

执行者找模板和门禁脚本时读取 `MAP.md`。未执行 `validate_investigation.py`，或门禁失败时，不得进入 Solidify。

门禁失败后，Harness AI 必须读取 `draft/.state/<role>/investigation-gate-feedback.json`（Investigate）或 `draft/.state/<role>/solidify-gate-feedback.json`（Solidify）中的 `harness_prompt`。feedback 文件存在即代表该门禁未解决：`draft_loop.py run` 会确定性拒绝执行，直到对应门禁重跑通过（通过时自动清除 feedback）。当 `authority_problem=true` 时，不得把失败当作普通 JSON/测试格式问题：先按 `owner_stage` 返回对应阶段，依据 `diagnosis`、`missing_proof` 和 `improvement_options` 调查实现，再用 `pass_condition` 重跑验证。`prohibited_shortcuts` 是防止迎合门禁的硬约束；反馈给出的是调查方向，不是允许机械照抄的唯一补丁。Runtime 只提供 Tool audit、Search/Load、Environment snapshot 等观察事实，反馈和工程整改均属于 Draft Harness 控制面，不得写入 Production Judge 或业务三态。

结构门禁通过不等于调查足够。进入 Solidify 前，Harness AI 还必须按 objective 和 ROLE.md 做语义交接审查：关键业务链是否连到当前 gap、链路节点是否有真实 EvidenceRef、决定结论的当前事实是否有可执行 Tool 路径，操作索引能否从当前 trace 导航到最小决定性验证。Attribute 的通用架构图不能替代 case 所需的分支、匹配、捕获或后处理观察。若 objective 依赖的 ToolRequirement 仍有 `implementation_gap`，必须明确路由为“Solidify 补实现”或“本轮只能 unresolved”；不得一边承认关键验证缺失，一边围绕无关机制写候选 Role。

权威调查要覆盖**能力/职责边界**类裁决所需的资料（`spec/alg/authority.md` §8.2）：判“产品没有这个能力（职责外 / 职责内能力缺失）”必须落在能力清单、字段定义、规范规则（normative_rule）或外部事实（external_fact）等真实资料上，不能只靠产品介绍或模型常识。`authority-investigation-report.json` 的 `coverage_gaps.required_evidence` 记录调查时已知的补证需求。Runtime 因依据不足判 `not_evaluable` 时产生的缺料清单只作为用户人工发起下一轮 `investigate` 的输入；协议不得自动回写调查包、自动触发调查或把该次 Runtime 结果固化为永久结论。

调查包只交付业务事实、来源、观察边界和可用验证能力，不替 Solidify 预选候选算法、固定 Tool 调用顺序或给出针对某个 case/route 的施工指令。示例可以解释某项能力的适用边界，但不得被写成默认归因路径。若 `overview.md`、trace Markdown 或 Tool 描述把单个已知 case 的验证组合描述为普遍策略，Investigate 语义交接失败。

### Collection Index 实验闭环

当真实 Collection 存在上下文规模、内部对象定位或 Runtime 有限导航压力时，把 Key-Index
作为 **Draft 候选能力** 实验，而不是在调查阶段凭架构判断直接固化。执行顺序必须是：

```text
Collection pressure
→ candidate strategies
→ frozen simulation probes
→ deterministic Search→Load comparison
→ shortlisted candidate in Draft Role
→ provisional candidate implementation
→ frozen Loop comparison
→ selected / no_index / unresolved
→ final Manifest registration and Solidify refresh
```

Harness AI 应：

1. profile Collection 的真实结构、稳定标识、可加载边界、规模和消费目标；
2. 提出多个合理的对象边界、entry 粒度、源派生 projection、召回通路和 `target_ref` 候选；
   若只有一个候选可实现，必须记录排除其他方案的真实约束；
3. 在比较前冻结模拟 probe set，按资料情况覆盖稳定标识、源术语、非原文改写、歧义/多对象、
   无关/不支持问题及 Search→Load；
4. 用确定性 Builder 从真实来源生成实验 Entry，先以低成本模拟测试比较 top-k target recall、
   可拒绝性、Target Resolution、Load 成功率、加载上下文质量、来源追溯和成本，淘汰明显不合格候选；
5. 把通过模拟测试的候选临时接入 Draft Role；每次可比较运行前冻结候选实现，在相同 Current、
   objective、review、cases 和业务环境下通过 Draft Loop 比较端到端业务结果、退化、Context/Tool
   audit、token 和 latency；
6. 通过模拟测试的 shortlist 可以在隔离 Draft 区域做临时候选实现并进入 Loop，但不得宣称正式
   `selected`；只有模拟测试与 Loop 都证明合格后，才能形成 `selected` 结论、登记到 Investigation
   Manifest，并刷新最终实现和 Solidify receipt。实验若证明 direct load 更合适则记录 `no_index`，
   证据不足则记录 `unresolved`。

模拟指标只负责筛选导航方案，最终选择以 Loop 的端到端效果为准。检索 recall 合格但业务结果、
成本或稳定性退化的候选不得选中。Loop case 只用于评价，不能直接生成或修补 Entry；应保留未参与
候选调整的 holdout probes 或 unseen cases 做最终复核。

Harness AI 可以探索 selector、粒度、projection 组成和 channel，但不得自由编写逐 Entry
`search_text`，不得把 badcase、reference answer、expected trace、答案词、推荐 query 或资料中
不存在的同义词注入索引；不得用 embedding top-k、rerank score 或 SearchHit 代替 Evidence；
不得用全文模糊 fallback、完整 Collection 注入或读取期望答案掩盖 Search miss / `target_ref`
解析失败。未被实验和 Loop 共同证明的候选不是正式资产，不得为通过结构门禁提前登记或 Solidify。
具体合同以 `spec/alg/investigate-keyindex.md` 为准。

#### Key-Index 门禁

执行者必须用 `MAP.md` 登记的 `validate_key_index_experiment.py` 依次执行三阶段门禁：

- **Investigation Readiness**（`--phase investigate`）：要求 Collection profile，并对 exact、lexical、
  embedding、rerank 分别记录 `experiment/deferred/rejected/not_applicable + reason`；至少保留 baseline 与
  一个有意义的 alternative，无法实验时可记录有证据的 `alternative_exclusions`。这是通路考虑门禁，
  不机械要求 embedding、rerank 或任一不适用通路必须实现；
- **Simulation Readiness**（`--phase simulation`）：要求冻结且分离的 development/holdout，holdout 必须
  `used_for_tuning=false`；探针套件整体覆盖 stable identifier、source term、source paraphrase、ambiguity/
  multi-object、unsupported、irrelevant 与 Search→Load。每个候选必须提供完整 Index/Builder/projection
  provenance/retrieval channels/Search/target_ref/Resolver/Load 套件；每个 SearchHit 记录真实
  `matched_channels`，声明 embedding 时还必须提供模型、模型版本和 projection 版本审计。shortlist 候选
  必须同时通过 development 与 holdout 的预冻结阈值；
- **Selection Readiness**（`--phase selection`；兼容别名 `--require-selected`）：在 Simulation Readiness
  之上必须提供 frozen Loop report，证明 objective 改善、业务无退化、没有完整 Collection fallback，
  记录 Draft prompt token 与 latency，并通过 Search/Load/Authority audit。没有 Loop 证据时只能保持
  `provisional`，不得登记为正式 `selected`。

只硬禁 expected answer/trace/verdict、AI 编写同义词等污染 Entry，SearchHit 冒充 Evidence，静默完整
Collection fallback，虚假 channel 声明和 case-specific route；不全局规定融合算法、Entry 粒度或必须使用
embedding/rerank。门禁阈值必须在实验运行前冻结并写入 report；若根据 holdout 失败调整候选或参数，
该 holdout 必须失效并转入 development，另备新的 unseen holdout。结构门禁通过只证明套件完整、实验可复查，
不替代 Harness AI 对失败 probe、query 构造边界和业务泛化性的语义审查。

## Solidify

Solidify 是 Harness AI 的工程判断，不是从 Manifest 机械生成代码：

- 静态项目知识按主题注册为有 Role 权限的 ContextUnit；
- Key-Index 只物化已通过冻结模拟测试的 shortlist：Loop 前只能作为隔离的 provisional candidate，
  不得宣称正式 `selected`；Loop 证明胜出后才登记最终 Manifest 并刷新 Solidify receipt。不得在
  Solidify 临场发明对象边界、projection、同义词、固定路由或 fallback；`no_index/unresolved` 不得
  被自动改写成一个勉强可用的 Index；
- 需要执行动作取得当前事实的 requirement 复用、包装或新建 VerifiableTool；
- 实现填入 `ToolImplementationRef`，未实现项保留 implementation gap；
- 候选 `draft/<role>.py` 必须实际消费已声明能力并遵循现有 Role 协议；
- Judge/Mock 必须用 `scripts/solidify.py` 写入并复核 `draft/.state/<role>/solidify.json`，逐项证明合同 source ID → 固化资产 → 成功 runtime observable 的映射；
- 在公共 `role_assets` 中预先声明 enabled、roles、production/candidate path 和 replace；
- 不复制 RoleResult、Context schema、Reviewer 或状态机。

Solidify 必须逐项回看 Manifest，而不是只参考 overview：

- 对 Attribute 的同名 `.mmd + .md + .trace.json` 作为一组 artifact 核对；sidecar 只提供结构化业务事实，不是候选施工说明；
- 对每个 objective 相关 ToolRequirement，确认已复用/实现，或确认其缺口会阻断本轮改善；
- 用真实 project loader 装配候选 Tool/Context，并做 Tool smoke、Context 注册/加载和候选 Role 实例化；
- 候选只能调用项目当前真实存在的公共函数、Tool 或协议扩展点。依赖不存在的 adapter 私有方法、静默退化为空字典，或把与 objective 无关的旧 probe 当主策略，均视为 Solidify 失败；
- 候选不得把调查包中的单个 route、case、字段、正则或固定 Tool 组合写成通用决策路径；必须从当前 Judge gap、当前业务输出和调查 artifact 的节点数据/观察边界动态选择验证能力；
- Solidify 消费源码、配置、文档或历史 probe/report 时必须优先取得支撑当前判断的最小充分片段；已有精确搜索、符号读取或专用 Tool 时，不得为了“看全”而加载整文件。若只能取得超预算的整份材料，应保留 unresolved，并把缺少的有界验证能力作为后续改造项；
- 列出“调查事实/requirement → 固化文件 → runtime 可观察调用”的对应关系；无需新增 schema，但每一项必须能由 validator、runtime audit 或真实测试复查。

Attribute 保留交互式 Search/Load、动态 ContextUnit、Finalization 和 Reviewer；Judge/Mock baseline 只确定性装载 mandatory ContextUnit，不继承 Attribute 的证据闭环。ContextUnit 是可选集合：未配置 Investigation/Context asset 的历史项目等价于 `ContextUnit=[]`，继续走同一流程，不写“旧框架”分支；一旦配置 Judge/Mock Investigation asset，Solidify receipt 和逐轮 Role review receipt 都成为强制门禁。

## Draft Loop

Loop 开始时冻结 production Current revision、objective、review 和 iteration cases，先运行 Current 确认真实 gap。每轮由协议在相同业务环境和数据上运行 frozen Current 与 Draft revision N，保留两侧原始 RoleResult、Context/Tool 使用和异常。

同一 project/role 已有 active loop 时，默认继续该 loop。若 frozen Current、objective、review、cases 或 Draft fingerprint 已改变，必须显式使用 `--restart`：确定性归档旧 loop 的完整状态与迭代证据，创建新的 active loop，并从 iteration 1 重新开始；不得覆盖或删除历史归档。

Skill 只在以下条件成立时停止为成功：

```text
Draft 相对冻结 Current，在 objective/config.review 下有把握的净胜 > 0
```

有把握：能一句话说清 Draft 更好或更差，依据是本轮 objective/review，不要求每个 Role 先订一本规范。人判不完、两边都像对、资料不够、这轮没判完 → 不计分，且禁止拿这些案改候选。单案不否决整轮。净胜 = 有把握更好的条数 − 有把握更差的条数。字段更多、文本更长、confidence 更高、跟 production 打分更像，都不算更好。

Role-specific 填写规则见该 Role 的 `ROLE.md`；不要在 SKILL 正文展开 Role 判定口径，也不为每个 Role 补规范文件。长期再优化决策函数；短期按净胜拍。

Review 将问题路由为：

- 调查材料/关键未知不足 → Investigate；其中 Runtime 侧“职责外/依据不充分”类
  not_evaluable 暴露的缺料清单（`spec/alg/authority.md` §8.5）必须路由回 Investigate
  补证，不能留在判定层反复 not_evaluable；
- Context/Tool/候选 Role 使用方式不足 → Solidify；
- loader、数据、协议或环境失败 → blocker；
- 净胜 > 0 允许记 improved → promotion-only checks（仍须人工确认 Promote；unseen 只在这一步跑）。还要继续改候选就记 unchanged，不要进 promotion_checks。

unseen cases 只在 promotion-only checks 使用，不逐轮暴露给 Harness AI。达到 max_iterations、预算、连续无新信息或环境阻塞时诚实停止。

Judge/Mock 每轮先用 `scripts/review_iteration.py` 生成 `draft/.state/<role>/iterations/<NNN>-role-review.json`，覆盖合同 source IDs 和全部 Role 专属 criterion。`improved` 只要求 `relative_improvement_no_regression` 为 pass，以及 Draft 侧还有可比较的行（不能整侧执行失败）；其余 criterion 照记，fail 不否决 improved。Draft Loop review 必须同时引用该 receipt 与最新 Current/Draft run report。

`/draft loop` 使用 `scripts/draft_loop.py start/run/review/status` 保存冻结事实和每轮判断。
`run` 在存在未解决的 `investigation-gate-feedback.json` / `solidify-gate-feedback.json` 时拒绝执行；
对应门禁（`validate_investigation.py` / `solidify.py`）重跑通过会自动清除反馈文件。
`review` 确定性校验对比表：文件必须存在、cases 对齐、harness 分析已填；各 Role 的填写规则只在该 Role 的 `ROLE.md`。evidence 必须引用该表；不满足则 review 不落盘。
每轮 review 必须随 role-review receipt 产出 Current/Draft 逐 case 对比表：用 `scripts/render_loop_comparison_table.py` 从冻结 iteration-cases 与 run report 确定性渲染，表文件与 run report 同目录落盘（`<NNN>-comparison-table.md`）并在 review 中引用。基础列固定为 `case / query 输入 / live 输出 / production <role> 结果 / draft <role> 结果 / harness 分析`（`harness 分析` 为必出最后一列，排在场景列之后），逐 case 保留两侧原始判定，禁止只贴聚合指标；场景列按被测场景扩展——judge 权威场景自动追加 `authority(production) / authority(draft)`（调用数 + resolution 状态），其他场景用 `--scenario-columns` 注入对应列。渲染后 Harness AI 必须逐 case 填写 `harness 分析`；Python 渲染器对该列只填 `-`，不得撰写分析。Python 脚本只负责：预校验全部 case、冻结身份、环境依赖预检、执行两侧 Role、逐 case 原子落盘、保存异常和阻止非法状态；它不解释业务结果，也不决定 Draft 是否更好。协议 `run` 只产原始 Current/Draft 事实；Harness AI 必须按 ROLE.md/config.review 审查，并通过 `review` 明确记录 decision、route、reason 和真实报告指针后才能进入下一轮。修改 frozen Current 或 iteration cases 时必须重新 start，不得继续旧比较。业务源码 revision 变化只记录 drift，不自动触发 Draft 更新；是否更新 Investigation/Solidify/Candidate Role 由用户启动 Draft 后决定。

`draft_loop.py run --workers <N>`：`--workers 0`（默认）按
`execution.batch_concurrency_default/max` 自动并行；case 之间相互独立，允许并发执行
Current/Draft。每行 run report 记录实际 `workers` 与墙钟 `elapsed_seconds`，review 时
必须核对；退避只针对 LLM 端点/限流/超时类瞬时故障（含 authority 工具端点失败：
连接错误、Cloudflare 5xx/524、Unknown model error 等），且按 worker 独立退避（含抖动），
单个 case 的端点故障不得冻结整批并行。业务/校验类错误按 Role 行为事实记录，不驱动
退避；端点故障退避重试仍失败时按工具失败落盘，review 依据 audit 判 side 有效性。

Judge Loop 额外核对 authority audit：被引用的调用必须真实存在，工具失败不得当成相对改善。判后责任、四象限探针与消费规则见 `judge/ROLE.md`。

正式 Attribute Loop 在调用 LLM 前必须验证 Context/证据注册依赖可用，并在每侧 Role 返回后检查本次运行审计。预检只能减少无效消耗，不能证明长运行期间依赖持续可用；任何 Context Search/Load 基础设施异常、证据注册失败或 runtime Reviewer 基础设施异常都使本轮报告失败并保留已完成事实。无效 ID、权限、预算等请求错误作为 Role 行为事实留给 Harness review，不得和基础设施失败混为一类。不得靠重试把失败伪装为有效比较。

调查 Tool 的真实 smoke validation 使用：

```bash
<config.python.executable> .agents/skills/draft/scripts/validate_investigation.py \
  --project <id> --role <role> --execute-tools --tool-inputs <JSON或文件>
```

`--tool-inputs` 只提供本次执行 kwargs，不进入 Manifest。已实现 Tool 缺少必需输入、没有真实执行或未返回成功 `ToolResult` 时，检查必须失败。

## 当前执行支持边界

- Draft Loop 的确定性执行入口当前支持 `attribute`、`judge`、`mock`。
- Solidify receipt 与逐轮 Role review receipt 当前支持 `judge`、`mock`。
- Live 仅是协议扩展点；当前没有 `live/ROLE.md`，也没有可宣称已支持的 Draft 执行入口。
- reference template 是 Harness/Skill 构造输入的骨架，不是 `draft_loop.py` 直接加载的统一 DraftConfig loader。

## Promote

用户确认后运行：

```bash
<config.python.executable> -m impl.cli draft-promote --project <id> --role <role> --check
<config.python.executable> -m impl.cli draft-promote --project <id> --role <role> --apply
```

`--check` 零写入；`--apply` 只按 `<role>_draft` 和 `role_assets` 的固定映射校验、move/copy、关闭 switch 并做最小回归。候选仍被其他启用 Draft Role 使用时 copy，否则 move。搬运过程不得生成、合并或改写候选内容。

## Production / Draft 切换

继续使用项目 `project.yaml` 的 `<role>_draft.enabled + module`；修改后启动或重启服务即可观察 Draft/Production。该开关只切 Role 文件。Tool、Context 和调查资料使用同一个 `role_assets.enabled + roles`，不再维护第二套 Draft 能力开关。

## 不变量

- evidence 必须可追溯；prompt 声明不是证据；
- 不写死 case，不吞异常，不伪造成功，不把 fulfilled 强判失败；
- Draft 只写隔离的 `draft/` 区域；
- Current 在一轮 Loop 内冻结；
- promotion 必须人工确认，完成后关闭对应 `<role>_draft.enabled`；
- 实施、模板、脚本和 Role 资源位置统一从 `MAP.md` 查找。
