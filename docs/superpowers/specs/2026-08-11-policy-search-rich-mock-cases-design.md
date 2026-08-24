# Policy Search 高丰富度 Mock Case 设计

## 目标

为 `policy_search` 构建一批独立于业务 golden query 的高丰富度 MockCase，用保险代理人的真实检索表达主动撞击解析边界。数据用于发现字段识别、操作符、取值、逻辑作用域、时间边界、上下文承接和安全失败问题，不把当前 parser 输出固化成正确答案。

首批目标约 400 条；数量服从覆盖与差异性，不用重复或机械改写凑数。

## 事实源与隔离边界

- 允许读取业务配置中的启用字段、别名、枚举、操作符、场景定义和 unsupported 边界。
- 不读取业务 golden query 作为生成 seed、模板或改写输入。
- golden query 只在生成完成后用于精确重复和高相似表达检查，不向生成器提供文本。
- `mock_cases.json` 保持唯一受支持的 MockCase 存储形状；`output` 与 `reference` 保持 `null`，因为当前项目 `ready=[]`。
- 当前 Judge evidence view 不包含 `trace.mock_intent.user_context`，但实现不能依赖这一点泄露答案。

## 生成架构

采用“覆盖矩阵约束 + Mock Agent 独立表达 + 确定性质量门禁”。

1. 项目内覆盖规划器从业务配置提取能力清单，只产生成任务，不读取 golden case 文本。
2. 每个任务描述代理人目标、可见业务概念、表达风格、逻辑复杂度、时间表达和上下文形态。
3. Policy Search Mock Agent 根据任务生成 `MockIntentOutput`，其中：
   - `user_intent` 是用户自然语言目标，不包含字段 ID、标准操作符或预期状态。
   - `query` 是代理人实际会输入的原话。
   - `user_context` 只含中性代理人背景，或业务请求确实需要的历史 `contexts`。
4. `build_initial_request` 构造完整 AskBob envelope，显式包含 `args.contexts`。
5. 质量门禁校验 schema、重复、语言差异和覆盖配额，合格用例写入 `impl/data/policy_search/mock_cases.json`。
6. 覆盖标签、生成维度和统计单独写入 `impl/data/policy_search/mock_coverage.json`，不进入 MockCase、RunTrace 或 Judge 输入。

## 覆盖矩阵

首批数据至少覆盖：

- 全部 41 个启用字段，以及字段允许的主要操作符族。
- 全部 85 个启用业务场景和 11 个明确 unsupported 场景。
- 原子条件、同字段多值、跨字段 AND/OR、括号优先级、混合逻辑、条件重复与冲突。
- 绝对日期、相对日期、日/月/季度/年度、跨年、月末和包含边界。
- 投保人、被保人、当前代理人等角色差异。
- 保单号、手机号、证件号的完整值、片段、前缀、尾号表达。
- 金额、年龄、次数等数字的阿拉伯数字、中文数字、单位缩写和范围表达。
- 简短搜索词、完整陈述、命令式、询问式、反问式、工作口语、礼貌冗余、标点缺失、口头修正和轻微错别字。
- 有历史承接、指代、省略、追加条件、撤销或纠正上一轮条件。
- 字段缺失、条件缺失、歧义、否定范围不清、协议不支持，以及支持条件与不支持条件混合。

## 防 Judge 污染

- `user_context` 禁止出现：业务字段 ID、标准操作符、期望 filter、期望状态、正确/错误标签、Judge 结论。
- `user_intent` 只能比 query 更清晰地表达同一个用户目标，不得补充 query 和对话 contexts 中不存在的业务条件。
- 覆盖标签仅存在于 `mock_coverage.json`，Judge 链路不读取该文件。
- 增加回归测试，构建真实 Judge evidence view 并断言其中不存在覆盖标签、生成任务、期望字段、期望操作符或期望状态。
- 对上下文用例，Judge 可以看到业务请求中的对话 `contexts`，因为它们是用户需求证据；这些 contexts 同样不得包含标准答案或实现提示。

## 数据质量门禁

- MockCase 请求 schema 通过率 100%。
- query 精确重复率 0；规范化后重复率 0。
- 不与 golden query 精确重复；高相似项单独报告并剔除或人工确认。
- 每个启用字段、启用场景、unsupported 场景均有覆盖。
- 各表达风格、逻辑复杂度和上下文形态达到最低配额。
- query、user_intent 和 contexts 不含字段 ID、标准答案、实现类名或 prompt 指令。
- 固定随机种子和稳定 case ID，使同一输入配置可以重建同一批任务；Mock Agent 失败、输出空文本或重复时有限重试，最终不足配额则失败退出，不静默降级为重复模板。

## 修改范围

- `impl/projects/policy_search/mock.py`：让项目 Mock Agent 消费覆盖任务并生成独立表达。
- `impl/projects/policy_search/scripts/`：覆盖规划、生成、去重和统计脚本。
- `impl/projects/policy_search/` 下的项目级测试辅助代码（仅在必要时）。
- `tests/`：Mock schema、覆盖、golden 隔离与 Judge 污染回归。
- `impl/data/policy_search/mock_cases.json`：固化 MockCase。
- `impl/data/policy_search/mock_coverage.json`：不进入运行链路的覆盖报告。

不修改 core/protocol、其他项目、业务 parser 或 golden dataset。

## 验证

1. Policy Search 项目级生成器测试。
2. `mock-check --project policy_search`。
3. adapter 与 protocol compliance。
4. 覆盖报告门禁和 golden 重复检查。
5. 抽样运行 atomic、compound、time、context、clarification、unsupported 的 Live 链路。
6. 构造 Judge evidence view，验证覆盖元数据与预期答案未进入 Judge。

外部 Judge 服务不稳定时，Live 与本地结构门禁必须独立完成；Judge 网络失败不得被误判为 Mock 数据失败。
