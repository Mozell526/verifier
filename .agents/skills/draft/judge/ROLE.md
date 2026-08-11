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
每轮必须生成标准 Role review receipt，逐项检查：业务期望支撑、pre-actual 原子 expectation、blocking、dimension 覆盖、fulfilled 外部证据、not_fulfilled 的 Live 边界、not_evaluable 证据缺口、缺输出不逃逸、外部约束不误归责、无内部/unseen 泄漏、相对 Current 改善且无退化。还必须审计 Runtime authority 调用是否满足上一节。只有全部通过才允许 `improved/promotion_checks`；Loop evidence 必须同时引用 Role review receipt 和最新 run report。
