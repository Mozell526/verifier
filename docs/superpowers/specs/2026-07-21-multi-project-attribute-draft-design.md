# 非 QA 项目 Attribute Draft 逐项目优化设计

## 目标与范围

除 QA 外，逐项目执行 Attribute 的 Investigate、Solidify 和 Draft Loop，并用 `/Check` 审查候选是否因少量 case 产生过度规则化。`client_search` 保留已经完成且处于 `ready_for_promotion_checks` 的 Draft，只进行泛化审查和必要修正；新闭环按以下顺序推进：

1. `marketting-planning-intent`
2. `marketting-planning`
3. `deerflow`

本轮不自动 Promote，不修改外部业务源码仓库，不增加公共 schema。

## 每项目闭环

### Investigate

- 从 Judge 已确认的 not-fulfilled gap 出发，调查真实业务输入、输出、业务 API、执行分支、关键串联函数、配置和后处理。
- 生成 Attribute 调查包：`manifest.json`、`overview.md`、业务链 Mermaid 和带操作索引的同名 Markdown。
- 操作索引必须把 trace 观察连接到业务节点、验证 Tool/EvidenceRef、结果分支与 unresolved 边界。
- 对决定结论但当前不可执行的验证能力保留 implementation gap，不用静态源码或评测 trace 冒充运行证据。

### Solidify

- 将静态业务知识注册为 Attribute 可见 ContextUnit。
- 将 API、replay、probe 或局部函数验证实现为参数化 VerifiableTool。
- 候选 `draft/attribute.py` 通过现有 Attribute Search/Load、动态 ContextUnit、Finalization 和 Reviewer 使用这些能力。
- 不复制 client_search 的 L2 专属路径；每个项目按自身业务链选择验证节点。

### Draft Loop

- 冻结 Current、objective、review、业务源码 revision 和 iteration cases。
- iteration cases 至少包含一条真实失败、一条 fulfilled 对照，以及一条不共享字面输入但可检查同类机制边界的邻近变化 case。
- 协议保存 Current/Draft 的原始 AttributeResult、Tool/Context 使用、Reviewer、异常和耗时；Harness AI 判断是否更优。
- 只有 Draft 的定位准确性和修复可行动性有证据地优于 Current，且没有可见退化，才标记 `ready_for_promotion_checks`。
- promotion-only unseen case 不用于候选修订。

## `/Check` 泛化门禁

逐项目以及最终横向审查以下风险：

- prompt、Tool 或候选代码写死 case ID、完整 query、历史 finding 或期望答案；
- 将单一字段、单一路由或 client_search 的 L2 方法误写成所有项目的归因路径；
- Tool 只能接受某个冻结 case 的固定参数，或内部返回预制结论；
- 无关项目资料、字段或历史 attribution 泄漏到当前 finding；
- 仅增加更长文本、更多字段或 confidence，而未增加有效证据；
- 服务不可用、外部依赖失败或 verifier 基础设施错误被伪装为业务算法根因；
- fulfilled case 被强行制造归因。

发现过度规则化时，优先把候选改为“根据 trace 信号选择业务节点和参数化验证”，必要时返回 Investigate 补链路/Tool；不得通过降低 Reviewer 或 Loop 标准放行。

## 验证与交付

每项目执行调查包结构校验、真实 Tool smoke、Context 注册/装载、候选 Role 装配、冻结 Current/Draft Loop、相关单元/API 测试。最终交付：

- 每项目核心输入、Current/Draft 输出和证据链；
- Context/Tool/Reviewer 运行审计与基础设施异常；
- `/Check` 发现的过度规则化及修正；
- 尚未验证的边界和是否进入 promotion-only checks；
- 不执行 Promote。
