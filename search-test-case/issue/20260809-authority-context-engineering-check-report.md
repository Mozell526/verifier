# 20260809 authority context engineering check report

## 审核背景

用户要求用 check / aihacking / bussiness 三视角审核本次 Authority 上下文工程优化：
CG-ENG-001（PEP604 结构化输出契约）、CG-ENG-002（工具结果 JSON 化）、CG-ENG-004（claim 比对载荷投影）、CG-ENG-005（audit caller 标注）。

## 审核范围

- `impl/core/structured_output.py`（`_resolve_annotation` / `_dataclass_to_schema` fail-loud）
- `impl/tools/protocol.py`（`_serialize_tool_result` / `json_tool`）
- `impl/core/llm_client.py`（`_json_context_tools` + `complete_json` 接线）
- `impl/core/authority_environment.py`（`_compare_claim` 投影 / `_caller` 调用点）
- 新增测试：`tests/test_tool_json_context.py`、`tests/test_schema_validator.py`、`tests/test_authority_runtime.py`
- 审查记录：`impl/projects/client_search/draft/.state/judge/context-governance/judge-authority-context-2026-08-09.json`

## 实测结果

- 回归 130 passed（tool_json_context / schema_validator / authority / attribute / llm / context 相关）。
- 裸 callable 经 `json_tool -> agno from_callable -> process_entrypoint` 全链参数 schema 保留。
- `Toolkit` 实例透传，无误包装。
- 实跑 `resolve_authority`：第一阶段 `caller=authority`、第二阶段 `caller=authority-claim-compare`，tool 消息为 JSON，claim 比对载荷只含结论字段。

## aihacking 审核（投机取巧）

- 无 fallback 注入绕业务失败：`_serialize_tool_result` 的 `default=str` 与旧 agno `str()` 行为等价，非为过测试加的兜底。
- 无改标准：`ToolResult` / `VerifiableTool` / `build_agno_tools` 契约未变。
- 无越界：序列化只在 `_json_context_tools` 消费处生效；`AgnoToolCall.run`、attribute 直接调 `entrypoint()` 仍拿结构化结果。

## bussiness 审核（业务期望）

- 实跑业务结论不变（`supported`、basis 为物化 unit_id）。
- 信息隔离符合预期：第一阶段无 claim、第二阶段无证据地址。
- 最小单元格核对：PEP604 只影响 schema 渲染、JSON 化只影响工具结果进上下文、caller 修复只影响 audit 标注。

## check 发现的问题与处理

- P1（冗余）：`json_tool` 显式 `logical_tool_id` 搬运与 `functools.wraps` 的 `__dict__` 拷贝重复 → 已删除，`wraps` 自动携带。
- P2（可读性）：fail-loud 消息原始注解带引号重复显示（`x: "'MissingTypeXYZ'"`）→ 已去引号展示。
- P3（测试缺口）：缺 agno `from_callable -> process_entrypoint` 全链 schema 断言 → 已补 `test_json_tool_survives_agno_from_callable_schema_inference`。
- P4（协议文档对齐）：`spec/struct_output.md` 未提及 PEP604 支持 → 已补说明（Python 3.9 支持 `X | None`，无法解析 fail-loud）。

## 验证清单

- [x] 150/130 相关回归通过
- [x] P1 删除后 `logical_tool_id` 仍保留（单测断言）
- [x] P2 fail-loud 消息可读
- [x] P3 全链 schema 测试通过
- [x] P4 文档与实现对齐
