# Judge Draft Role Contract

## Purpose
Judge 根据 pre-actual 业务合同、Live 边界和可审计外部依据，对当前 Case 做三态评价。调查包提供事实空间与验证能力，不预写未来 Case 的裁决答案。

## Allowed investigation material
- 真实业务源码、配置、规范文档、字段/能力定义和其 revision/hash。
- 可复现的外部 API、数据查询或实验结果。
- 当前产品对外职责与不可归责的外部约束。
- 用于定位资料的 Key-Index 设计和可执行 ToolRequirement。

不得把 case actual、score、verdict、reference answer、unseen data 或模型常识写成项目静态知识。运行请求中的 case-specific 内容只能在 Runtime 使用。

## Evidence / Tool requirements
EvidenceRef 必须指向可追溯外部业务材料并带 revision/hash。ToolRequirement 只登记 semantic comparator、外部业务 API 检查或输出协议校验等可验证能力。工具失败、输出不可解析或关键信息缺失时保持 `not_evaluable`；工具失败本身既不是 resolved，也不是业务依据。

## Mandatory artifact
必须生成并在 Manifest 登记 `docs/judge-investigation-contract.json`，其 schema 为 `JudgeInvestigationContract`，只包含：

- `business_expectations`
- `live_boundary`
- `evaluation_dimensions`

该 JSON 是唯一合同真相源，不维护平行 Markdown 合同。Expectation 必须在 actual 之前原子声明；blocking expectation 不得因缺输出而逃逸。外部约束不能归责 Live，内部实现事实不能用于把外部结果判失败。

Judge 还必须生成并登记 `docs/authority-investigation-report.json` 与其确定性渲染 Markdown。报告以 `materials + coverage_gaps` 描述当前可用的事实空间。

## Authority investigation

### 以资料为轴
每份 Material 必须声明：
- `source_ref_id` 与可校验的 `source_location`
- 一个或多个 `MaterialDecision`
- 每个决定的 `conclusion_kind + governs + scenario + conditions`
- 仅相关但不直接决定的 `related_to`
- 与其他资料的 connection 和已知 limitation

`governs` 必须说明该资料直接决定什么；不能用静态“权威等级”替代真实来源、生产者、消费路径和适用条件分析。

### Coverage gaps
`coverage_gaps` 只记录当前资料在某个业务事项与条件组合上的覆盖不足、已有 basis 及所需补证。它不是结论对象，没有 resolved/unresolved 状态，也不绑定未来 Case。

调查期不得：
- 预枚举未来 Case 的判断点或为每个判断点预选锚点；
- 生成 Runtime resolved/unresolved 结论稿；
- 固定 Runtime Tool 调用顺序；
- 把单个已知 case 的验证组合写成通用策略。

Runtime 暴露的新缺料只作为用户人工发起下一轮 Investigate 的输入，不自动回写调查包或自动触发调查。

## Solidify usage
稳定合同和验收边界注册为 Judge 可见 mandatory ContextUnit，并在 LLM 前确定性装载。Solidify 将已验证材料物化为可加载 Evidence/Context、从真实来源派生的 Key-Index、按需取得当前事实的 VerifiableTool，以及实际消费这些能力的候选 Judge。

配置 Investigation/Context asset 时必须生成 Solidify receipt，证明每个 expectation、dimension、live boundary 以及 objective 相关材料/工具已映射到候选资产，并能在成功 runtime observable 中审计。Coverage gap 不得编译成静态 gate；缺少决定性能力时保留 implementation gap 或 `not_evaluable`。

## Runtime authority review
逐 case 审查 Judge 是否：
- 在当前判断确实需要外部裁决时按需调用 `authority.resolve`；该调用却未调用时不得自行推断；
- 只把当前 trace 中真实、成功且可审计的调用写入 `authority_tool_call_ids`；
- 将 tool failure、结构化输出错误和超时视为工具失败，而不是 resolved/unresolved 业务结论；
- 只让 unresolved 约束实际依赖该调用的 blocking assessment，不扩散到无关 dimension；
- 只使用真实 load 后资料作为 basis，不能把 Key-Index hit、搜索分数或未加载摘要当 Evidence。

## Draft Loop review
业务判定正确性的唯一基准是 `spec/alg/fulfilled.md`（判断顺序、§4 场景类型、反面清单）；资料定位与证据效力按 `spec/alg/material-positioning.md`。live 输出是被测对象的行为事实（current_behavior），不得自我背书为「正确交付」；与 live/production 输出的一致率不是评判标准。Authority 关着不要 NE；核心未交付是 NF。fulfilled.md §4 的举例只说明场景类型，不能当该条 case 的金牌读法。

每轮必须生成标准 Role review receipt，逐项检查：业务期望支撑、pre-actual 原子 expectation、blocking、dimension 覆盖、fulfilled 外部证据、not_fulfilled 的 Live 边界、not_evaluable 证据缺口、缺输出不逃逸、外部约束不误归责、无内部/unseen 泄漏、相对 Current 的有把握净胜。还必须审计 Runtime authority 调用是否满足上一节。最易漂移的三项判据固定为：

- `expectation_support`：先核支撑资料的 `conclusion_kind`。normative_rule / external_fact 可裁决应该如何；`inlive_boundary` 只证明可达空间（有什么字段/枚举/映射目标值），不证明这次选得对（positioning §4 不变量 2）。Load 到资料不等于定位正确；current_behavior 与解析配方不能当尺子。F 仍须同时满足 fulfilled §2.1：职责内、材料够、证据能证明用户要的结果拿到了。不得由 live 自身输出背书，也不得是无资料支撑的模型意见。
- `not_fulfilled_live_boundary`：只检查归责边界——外部原因（fulfilled.md §4.4）不得归责系统；这不是「与 live 交付一致性」检查，Judge 判 live 交付不足本身不构成失败。
- `relative_improvement_no_regression`：只对「这轮有把握」的翻转计净胜。有把握更好 +1，有把握更差 −1；人判不完、无尺子、检索缺口、工具中断不计分，且禁止拿这些案改候选。有把握的理由用本轮 objective/review；Judge 若刚好能引用 fulfilled.md 反面清单或空间命中就写上，不是入场券。单案不否决。净胜 > 0 才允许 `improved`（另见 SKILL：Draft 侧还要有可比较的行）；还要继续改候选就记 unchanged。其余 criterion 照记，fail 不否决 improved。

review 必须对 Current 与 Draft 两侧判定扫 fulfilled.md 反面清单，任一侧踩线都如实记录；不得只审 Draft 不审基准侧。Loop evidence 必须同时引用 Role review receipt 和最新 run report。每轮必须产出并引用 `scripts/render_loop_comparison_table.py` 渲染的逐 case 对比表（基础列：case / query 输入 / live 输出 / production 结果 / draft 结果 / harness 分析）；对比表必须含 harness 分析列，由 Harness AI 填写。模板见 `reference/loop-comparison-table.md`。不得只贴聚合指标。

`harness 分析` 不是 Role 判定。每格写清：有把握哪侧更好、还是两侧都对/都错、还是不计分。能引用 fulfilled.md 锚点（判断顺序、§、反面）就写；人判不完标「歧义-缺」或「不计分」，检索缺口标「检索缺口」。不计分的案不进净胜、不改候选。禁止只写「与 production 一致」；禁止用 Judge 的 reasoning 冒充 harness。Review 引用该表前，这一列不得再是 `-`。

## Judge Authority 判后责任与四象限

Judge Loop 每侧 run report 额外落盘 authority.resolve 的运行时快照（`authority_tool_call_ids` / `authority_audit` / `environment_snapshot_sha256`）。review 必须核对：被 assessment 引用的调用是否真实存在于 audit（引用缺失 → needs_human_review）、是否有 `tool_failure`（能力不可用，如限流）被当作相对改善。`run_report_invalid_sides` 会把「authority 工具失败且被引用」的 side 判为无效；职责外/依据不充分类 not_evaluable 必须有 authority 调用记录（`spec/alg/authority.md` §8.4），没查证不等于查不了。

Judge 的前置 `authority_obligation_contract.pre_obligations` 只用于引导，不是免责清单。每侧最终结果进入 review/history 前，Harness 必须对判决实际动用的规范性断言做判后核对：

1. 先用确定性集合核对随附 compact manifest、enum、mapping、operator 与 MaterialDecision 投影；
2. 对散文规则只允许窄域语义审计，任务限于识别「判决引用了哪些随附资料中不存在的规则」，不得重新判案；
3. 用 `claim.subject` 对账真实 `authority.resolve(question, claim)` audit；旧 question-only 调用不能冒充 claim 担保；
4. 输出控制面 `checked_claims`、`assessment_actions` 和 findings，不向 Core `JudgeResult` 增加项目专属字段。

未背书断言必须按可验证事实归责，优先级为：

- `compaction_miss`：全量 MaterialDecision 管辖，但 compact projection 漏出；整改 Solidify/压缩资产，不罚 Judge；
- `availability_miss`：随附资料不足且本 case 未构造 Authority；整改 Investigate/可用性门禁，不罚 Judge；
- `judge_failed_to_call`：Authority 已可用，Judge 仍以未担保断言支撑肯定结论；依赖 assessment 建议降为 `not_evaluable`，该 case 不得计为 Draft 赢案。

`contradicted` 不能支撑肯定结论并进入人工复核；`ungoverned`、`gap_only`（及兼容旧 `unresolved`）只允许依赖项为 `not_evaluable`。若 compact 资料已经直接背书，则不得为了调用率强制 Authority，也不得产生 availability/judge finding。每条 finding 必须有具体 `remediation_target`，不能只写「Authority 有问题」。

Judge Loop 业务样本前必须运行四象限探针：有 Authority+可裁决、有 Authority+缺口、无 Authority+compact 资料背书、无 Authority+真实缺口。探针套件须改造冻结真实案例，每象限至少 3 条；控制面合成探针只能证明门禁分支接线，不能替代这 12 条端到端模型考试。门禁回放考试仅以资料闭环标签计分：已知脏案检出率 >=90%、闭环干净案误报 <=1，且所有 finding 均可定位整改资产；任一不通过，当轮业务 Loop 作废。边界/reference 可疑案保留观察但不计门禁准确率。
