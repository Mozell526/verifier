# Judge Production/Draft 执行策略隔离设计

## 目标

恢复 Production 原有的单次 Judge 行为，并把 Planning、Frozen Plan、
Authority 依赖绑定和 Assessment 两阶段执行限制在 Draft 候选实现中。

本次设计只解决执行策略隔离，不改变 JudgeResult 公共输出协议，也不把
client_search 业务语义加入共享 Core。

## 长期边界

### Production

```text
RunTrace
→ Production build_context
→ SinglePassJudgeExecution
→ 一次 LLM Judge
→ normalize / reconcile / finalize
→ JudgeResult
```

Production 必须严格保持 Git HEAD 的单次 Judge 行为：

- 不构造 PlanningTrace；
- 不调用 Planning LLM；
- 不依赖 ProductExpectation registry；
- 不校验 product_expectation_id；
- 不构造 FrozenCaseEvaluationPlan；
- 不产生 judge_planning_failed；
- 不读取 Draft Authority 或 Draft Context 资产。

### Draft

```text
RunTrace
→ Actual-free PlanningInput
→ PlanningJudgeExecution
→ FrozenCaseEvaluationPlan
→ Actual + Authority + Tool Evidence
→ Assessment
→ normalize / reconcile / finalize
→ JudgeResult
```

Draft 的 Planning、Authority、字段 key 索引和按 key 读取定义均属于
`impl/projects/client_search/draft/` 内部实现。Draft 可以增加 LLM 阶段，
但不得改变 Production 的执行次数、输入上下文或错误语义。

## 组件职责

### JudgeExecution

共享 Core 只提供不包含业务语义的执行策略边界。策略接收 Judge Role、
RunTrace 和 user_intent，返回 JudgeResult。

它不得声明 Planning、Authority、ProductExpectation 或 client_search 字段。

### SinglePassJudgeExecution

Production 的默认策略，忠实封装 Git HEAD 的既有单次 Judge 调用。

所有没有显式候选执行策略的项目和 Role 都必须使用该策略。

### PlanningJudgeExecution

client_search Draft 的候选策略，只存在于 Draft 目录。它负责：

1. 构造不含 actual 的 PlanningInput；
2. 生成并校验 FrozenCaseEvaluationPlan；
3. 冻结 Authority 依赖；
4. 构造包含 actual、工具证据和 Authority Context 的 AssessmentInput；
5. 生成 JudgeResult。

### Role Loader

Role Loader 通过已加载的 Production 或 Draft Role 选择执行策略：

- Production Role 未声明候选策略时，固定选择 SinglePassJudgeExecution；
- Draft Role 显式提供 PlanningJudgeExecution；
- 禁止用全局 `planning_enabled` 或项目运行时布尔开关切换策略。

## 公共汇合点

两种策略只能在 JudgeResult 汇合：

```text
SinglePassJudgeExecution ─┐
                          ├→ JudgeResult → normalize/reconcile/finalize
PlanningJudgeExecution ───┘
```

Production 不需要理解 Frozen Plan。Draft 不得修改 JudgeResult 的公共含义。

## 错误边界

- Production 保持既有 LLM 请求和输出校验错误，不出现 Planning 错误。
- Draft Planning 失败只能产生 Draft 侧错误记录。
- LLM 空响应、配额失败和连接失败属于基础设施失败，不是业务
  `not_evaluable`。
- Authority unresolved 属于有效业务结果，必须是 `not_evaluable`，并在
  Judge Summary 中说明冲突来源、缺失证据、待澄清问题和受影响判断点。

## 一次性恢复范围

1. 从共享 `impl/core/judge.py` 移除当前未提交的强制两阶段 Planning 行为，
   恢复 Git HEAD 单次 Judge。
2. 从共享 `impl/core/judge_protocol.py` 移除默认 PlanningTrace、
   build_planning_context 和 build_assessment_context 调用。
3. 保留或新增的共享能力只能是无业务语义的 JudgeExecution 策略插槽，
   且默认行为必须与 Git HEAD 完全一致。
4. 将 client_search 两阶段执行和相关调用迁入
   `impl/projects/client_search/draft/`。
5. 不修改 `impl/projects/client_search/judge.py` 的 Production 行为。

## 验证

### Production 回归

- 同一 case 只发生一次 Judge LLM 调用；
- 不出现 `judge-planning` stage；
- 不要求 ProductExpectation registry；
- Production 输出与 Git HEAD 基线一致；
- Draft 开关和 Draft 资产不能改变 Production 指纹。

### Draft 回归

- Planning 输入不含 actual；
- Frozen Plan 在 Assessment 前冻结；
- Planning 字段候选最多 8 个，只含 key 和短名称；
- 字段定义只能按精确 key 按需读取；
- Authority unresolved 必须产生带原因的 `not_evaluable`；
- Production/Draft Loop 在同一冻结 cases 上分别加载对应执行策略。

### 防回归

测试必须显式断言：

- Production Role 选择 SinglePassJudgeExecution；
- Draft Role 选择 PlanningJudgeExecution；
- Production 调用链中无法观察到 Draft Planning Schema；
- 删除或禁用 Draft 目录后，Production 仍可独立运行。

## 非目标

- 本次不把 Draft Planning promotion 到 Production；
- 本次不修正具体 badcase 的业务期望；
- 本次不调整 Authority 调查内容；
- 本次不通过配置开关兼容两套流程；
- 本次不修改其他项目的 Production Judge。
