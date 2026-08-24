# Judge 结构化输出与上游失败处理设计

## 目标

解决两条已经通过真实运行复现的错误路径：

1. 模型返回含未转义正文双引号的近似 JSON 时，Verifier 在 `json_repair` 前主动跳过修复，导致本可通过 schema 校验的 Judge 输出被阻断。
2. DeepSeek 402 等上游失败被 Agno 表现为空 `RunOutput.content` 后，Verifier 将其误报为 JSON 错误；项目 `reconcile_result()` 随后又可能把失败结果升级为 `fulfilled`。

## 设计

### JSON 提取

保持处理顺序：标准 JSON、代码块 JSON、裸 JSON、`json_repair`。删除 `_has_ambiguous_inline_quotes()` 前置拦截；正文中汉字或文字之间出现未转义英文双引号，正是 `json_repair` 应处理的典型语法缺陷。

`json_repair` 只负责得到候选对象，不负责决定候选是否可信。修复结果仍必须通过调用方现有的 `StructuredOutputSpec` 严格校验，包括顶层 object、必填非空字段、字段类型、嵌套结构和 `additionalProperties: false`。不合规结果继续阻断或进入现有的一次 reprompt，不增加重试次数。

### Provider 失败

`LlmClient.complete_json()` 在解析内容前检查 Agno `RunOutput.status` 和最终内容。运行状态失败或最终内容为空时，将其分类为 LLM 请求失败，而不是 JSON 语法失败。原始 RunOutput 应通过其 `to_dict()` 能力保留状态、provider data 和错误事件，供 ContextStore 与日志诊断。

上游失败直接返回带 `error` 和诊断摘要的结果。Judge 收到该结果后生成现有的最小诚实结果：无业务 expectations/assessments，`overall_fulfillment.status = not_evaluable`，并记录 `llm_call_failed`。永久性 provider 失败不触发结构化输出 reprompt。

### Judge 终态

公共 `ProjectJudge.judge_trace()` 将 `llm_call_failed` 和 `llm_output_validation_failed` 视为终态。可以执行通用 normalize/finalize，但不得再调用项目 `reconcile_result()`。因此项目确定性比较只能补充有效 Judge 结果，不能为失败结果创造 expectations/assessments，也不能把 `not_evaluable` 升级成 `fulfilled`。

批量任务可继续执行其他 case；单 case 状态必须保持 `not_evaluable`。现有前端从 Judge summary 和 fulfillment status 展示结果，不新增前端模式或 schema。若验证发现文案仍错误，只修复现有投影，不新增平行状态字段。

## 验证

- 未转义正文双引号能够经过 `json_repair`，并在严格 Judge schema 合规时被接受。
- repair 后结构不符合 schema 时仍被阻断。
- Agno error/空 content 被分类为 LLM 请求失败，不显示为 JSON repair 错误。
- Judge 失败结果不调用项目 reconcile，最终保持 `not_evaluable`。
- `client_search` condition comparison 不得把失败结果升级为 `fulfilled`。
- 批量 case 失败不阻断全批次，但事件文案不得同时出现 `fulfilled` 和 Judge 失败原因。
- 充值后的正常 Judge 输出仍按原流程生成完整 expectations/assessments，不发生退化。

## 非目标

- 不放宽 Judge schema。
- 不接受任意字符串或非 object 结果。
- 不增加 LLM 重试次数。
- 不改变 Draft/Production 选择机制。
- 不修改业务项目的判定规则。
