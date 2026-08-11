---
doc_type: api
schema_version: 1
---

# Policy Search API

- endpoint：`/api/v1/policy-search/parse`。
- method：`POST`，`Content-Type: application/json`，单轮非流式。
- 请求：AskBob 外层信封；核心输入位于 `extra_input_params.policySearchParseArgs`，包含 `query`、`currentTime`、`agentCode`，历史上下文位于 `extra_input_params.args.contexts`。
- 响应：外层为 `code/msg/data`；业务结果位于 `data.extra_output_params.policySearchParseResult`，包含 `status/query/filter/message`。
- 错误语义：`code != 0` 或 `data` 缺失是接口失败；`status=UNSUPPORTED` 且 `filter=null` 是合法安全失败，不应当作服务不可用。
