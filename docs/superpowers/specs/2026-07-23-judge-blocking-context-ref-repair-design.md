# Judge Blocking 与 ContextUnit 引用修复设计

## 目标

修复两项已由 `api-check` 暴露的测评系统问题，同时保持 `20260721`
已有的 fail-closed 审核边界：

1. `marketting-planning-intent` 不得把 LLM 产生的任意 `missing`
   二次升级为新的 blocking contract。
2. Attribute 模型不得因为长 ContextUnit 物理 ID 被压缩而请求不存在的
   缩写 ID。

## Judge 设计

- 公共 `BusinessExpectation.blocking`、`FulfillmentAssessment` 和
  `finalize_judge_result()` 聚合协议保持不变。
- 项目 normalize 分离“已有 LLM gap”和“本轮确定性 contract gap”。
- `intent_contract` 只由 intent、required slots/entities、fallback 和
  min confidence 的确定性检查驱动。
- `intent_contract` expectation 与 assessment 按 ID upsert，确保重复
  normalize 幂等。
- assessment 使用协议字段 `expected_evidence`、`actual_evidence` 和
  `downstream_impact`，不再写会被丢弃的私有 `evidence`。
- LLM 调用或结构输出失败属于公共终态，必须在进入任何项目 normalize
  前返回；项目扩展不得把该结果升级为 fulfilled。

## ContextUnit 设计

- Registry 继续只接受精确物理 ID；禁止前缀、唯一匹配或模糊补全。
- Search 和 Load 的模型可见结果只暴露 run-scoped `selection_ref`、名称、
  描述以及各自需要的摘要或完整内容，不暴露长物理 ID。
- 动态 VerifiableTool 的完整结果注册后仍自动进入 investigated 集合；
  模型从 `runtime_metadata.attribute_context_evidence` 看到注册状态和可选短引用，不改写
  业务 `actual`，也不暴露长物理 ID。
- `load_context_units` 仅在 Registry 中不存在完全同名 ID 时，将含
  `...` 或 `…` 的输入判作疑似缩写并提示使用 Search 返回的
  `selection_ref`；不尝试猜测。
- debug、Finalization、EvidenceRef 继续保存精确 ID，并保留 policy
  鉴权、run 隔离和 source hash 校验。

## 兼容性

- 真正的 blocking expectation 仍会使 overall 失败。
- 非 blocking gap 仍保留在 Judge 展示与 Attribute 输入中，但不会被
  项目硬门重新升级。
- 动态证据的最终 EvidenceRef.location 仍是精确物理 ID；只改变模型调查
  阶段的可见句柄。
- 工具结果压缩继续启用，避免恢复长上下文膨胀。

## 验证

- Judge：非 blocking missing、真实 contract failure、已有 blocking
  failure、重复 normalize、terminal failure。
- Context：Search 只暴露短引用、短引用可加载、稳定 ID 不冲突、缩写拒绝、
  动态证据自动 investigated、Finalization 精确重载、跨 run 隔离。
- 运行现有 blocking、context runtime、attribute baseline 和项目分发测试。
