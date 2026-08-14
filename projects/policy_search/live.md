---
doc_type: api
schema_version: 1
---

# Policy Search API

- endpoint：`/api/v1/policy-search/parse`。
- method：`POST`，`Content-Type: application/json`。每一轮仍是一次非流式 POST；多轮由调用方把上一轮问答放进 `contexts` 再请求，服务端不按 `session_id` 记会话。
- 请求：AskBob 外层信封；核心输入位于 `extra_input_params.policySearchParseArgs`，包含 `query`、`currentTime`、`agentCode`，历史上下文位于 `extra_input_params.args.contexts`。当前 Query 只放在 `query`，不得在 `contexts` 中重复。
- 响应：外层为 `code/msg/data`；业务结果位于 `data.extra_output_params.policySearchParseResult`，包含 `status/query/filter/message`。
- 错误语义：`code != 0` 或 `data` 缺失是接口失败；`status=UNSUPPORTED` 且 `filter=null` 是合法安全失败，不应当作服务不可用。
