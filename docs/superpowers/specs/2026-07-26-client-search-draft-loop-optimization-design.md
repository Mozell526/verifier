# client_search Judge Draft Loop 数据驱动优化设计

## 目标

只修改 `impl/projects/client_search/draft/` 下的 Judge candidate，在不改变
Production、四条冻结 iteration cases、objective 和 review 标准的前提下，修复上一轮
Draft Loop 暴露的两个问题：

1. 非客户搜索请求被错误套用 `find-target-customers`，并因空条件被判为
   `fulfilled`。
2. Planning 无差别装载过大的 capability context，造成高 token 消耗和 OR case
   长尾失败。

本轮不新增 dataclass schema，不修改公共 JudgeResult、ExpectationPlan、Authority
或 Draft Loop 协议。

## 冻结输入与成功标准

继续使用上一轮相同的四条输入和 case hash：
`93e964062f7986513c9762dafee7cdf6ee8014b0b564d0b39e25bbddd281d0ac`。

| Case | Draft 必须达到的业务结果 |
|---|---|
| `exact-reference-without-independent-authority` | `not_evaluable`，并保留具体 `authority_limitation` |
| `clear-wrong-condition` | `not_fulfilled`，明确指出年龄字段、操作符和值与用户要求相反 |
| `unrelated-weather-request` | 不得生成 `find-target-customers` 相关 expectation，不得判客户搜索 `fulfilled` |
| `or-logic-mismatch` | `not_fulfilled`，并且 Draft 侧正常完成、没有 terminal error |

Draft 只有同时满足以上四项、相对 frozen Production 有明确改善且没有可见退化时，
才可记录为 `improved`。结果相同、部分改善、超时、调用失败或缺少审计证据都不算成功。

## 方案

### 1. 复用现有适用性数据流

不引入新的 applicability schema。继续使用：

```text
RunTrace.request candidates
    → IntentFrame
    → applicable_product_expectation_ids
    → FrozenExpectationPlan
    → Assessment
    → Authority constraint
```

Draft candidate 在 `_applicable_product_expectations` 中只接受正向、pre-actual
的业务适用证据：

- `application_boundary` 明确当前请求属于客户搜索边界；或
- 用户请求本身表达目标客户/客户属性筛选语义，并能由当前项目的已配置能力或客户
  搜索任务语义支撑。

仅有“非空自然语言”不能证明 `find-target-customers` 适用。判断不得读取
`extracted_output`，避免 actual 反向污染 pre-actual planning；也不得针对“天气”
等单个反例写负向黑名单。

当没有正向适用证据时，
`applicable_product_expectation_ids=[]`。现有 plan contract 必须阻止 LLM 为当前
请求生成 `find-target-customers` expectation。该结果沿现有 plan audit 留痕，不增加
平行状态或结果 schema。

### 2. Planning context 最小化

Draft candidate 不再因 `planning=True` 而装载完整 capability manifest。它从
pre-actual request candidates 中提取当前请求可关联的字段/语义线索，只向 planning
阶段提供相关 capability、mapping、rule 片段。

如果请求没有任何客户搜索适用证据，则不加载字段能力全集。这个裁剪只减少上下文，
不改变 authority 结论，也不使用 actual output 选择材料。

### 3. Candidate 与 Production 基线同步

在上述两项修复前，先把 Production 已有、但 Draft 遗漏的通用 Judge 上下文约束同步
到 candidate，包括：

- 使用统一的 `user_intent` 上下文键；
- 保留 `fulfillment_assessments` 标准字段约束；
- 保持 condition comparator evidence 的公共输出形状。

同步只消除 candidate 的历史漂移，不把 Production 的业务结果复制到 Draft。

## 错误与审计

- LLM、schema validation 或超时失败必须保留为 terminal Role evidence，不得重试后
  伪装成成功。
- Authority unresolved 只约束依赖对应 authority 的 expectation；用户明确条件反向等
  直接失败仍应为 `not_fulfilled`。
- 非适用请求不得制造客户搜索成功，也不得通过空 `conditions` 逃逸。
- Current/Draft 必须使用同一 frozen case hash，Production 指纹变化时必须重新 start。

## 验证

1. 为适用性门禁和 planning context 裁剪增加离线单元测试，覆盖四条冻结输入的关键
   pre-actual 事实。
2. 重新执行 Investigation validation、Solidify probe 和 Solidify receipt。
3. 归档上一轮，使用相同四条 cases、objective 和 review 重新启动 Draft Loop。
4. 在用户已授权的外部 LLM 上运行 frozen Production/Draft。
5. 生成 Judge role review receipt，逐条检查状态、expectation、authority evidence、
   terminal error 和耗时。
6. 输出四条特定输入的 Production/Draft 并排对比；不自动 promotion。

## 非目标

- 不修改 Production Judge。
- 不新增公共 schema 或新的 RoleResult。
- 不把单个 case、城市、天气或特定字段写死成判断规则。
- 不改变冻结 case 或降低 review 标准。
- 不自动执行 promotion。
