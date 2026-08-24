# Policy Search 暂不修复问题

## PS-OPEN-001：UNSUPPORTED 的前端序列化结果未显式展示 `filter: null`

- 状态：开放，不修复
- 修复方案确定性：70%
- 浏览器复现：Live 页提交“投诉超过3次的保单”，查看结构化输出与 Raw JSON。
- 预期候选：`PolicySearchExtractOutput.filter` 是可空字段，UNSUPPORTED 时可能应显式序列化为 `filter: null`。
- 实际：浏览器返回的 `extracted_output` 中完全省略 `filter`，但 live schema 校验仍通过，业务安全失败语义也正确。
- 暂不修复原因：尚未确认 verifier 公共序列化协议是保留 null 还是统一省略 null；直接改 policy_search 或公共 `to_dict` 都可能改变其他项目合同，确定性低于 80%。

## PS-OPEN-002：外部 Judge 模型端点间歇性 502/503

- 状态：外部依赖观察项，不修复
- 修复方案确定性：20%
- 浏览器复现：Summary 页并发运行 atomic_condition 与 time_boundary，查看 verifier 服务日志。
- 预期：Judge 端点稳定返回结构化结果。
- 实际：首次请求分别出现 502 与 503，内部重试后两条最终均成功。
- 暂不修复原因：错误来自外部模型网关；当前重试最终生效，没有证据证明 verifier 本地实现存在可确定修复点。
# PS-BROWSER-009：公开 Trace 省略请求中的空集合字段

- 状态：已确认，暂不修复
- 严重度：中
- 修复方案确定性：75%
- 浏览器复现：Live 页使用合法 `policy_search` 请求，显式传入 `args:{"contexts":[]}` 并成功执行；展开 Raw JSON。
- 预期：`trace.input`、`normalized_request`、turn request 与 LiveExchange request 应保留实际线上的 `contexts:[]`，以便证据回放能区分“必填空数组”和“字段缺失”。
- 实际：页面公开 Trace 中四处都显示成 `args:{}`，但同一请求已通过必填 schema 并成功调用业务服务，说明公开序列化阶段丢掉了空数组。
- 根因：`impl/core/schema/occam.py` 的公共 dict 序列化统一过滤 `None`、`[]`、`{}`，对一般摘要有效，但会改变请求/交换证据语义。
- 暂不修复原因：需要明确哪些证据字段必须 lossless、哪些展示字段仍应压缩；直接全局保留空集合会扩大所有 API 输出，局部特判也需先统一证据序列化边界。

## OPEN-BUG-20260811-003：Policy Search 将多类有效边界请求统一降为 1001 解析失败

- 状态：未修复
- 严重度：高
- 修复方案确定性：60%
- 不修复原因：问题位于独立的 `policy-search` 业务仓库，现有浏览器证据能确定外部行为不符合协议，但 `code=1001` 抹掉了内部失败阶段；在没有服务异常日志和完整模型可用性证据前，无法以 80% 以上确定性区分模板召回、LLM fallback、上下文消歧和 unsupported guard 的根因。
- 浏览器复现路径：打开 Live，选择 `policy_search`，逐条填写完整 AskBob envelope（`args.contexts` 必填），点击“请求业务服务”。
- 预期：支持字段和复合条件返回 `SUCCESS + filter`；不支持/需澄清请求返回 `UNSUPPORTED + filter:null + message`；上下文省略请求应消费 `contexts` 后解析或明确澄清。
- 实际：下列 5 类均返回 `policy-search API failed: code=1001, msg=保单搜索解析失败`：
  - 原子字段：`合同号码里带4826的`
  - 复合条件：`陈晓华投保的，保额至少30万`
  - 上下文承接：历史为“查陈晓华作为投保人的保单”/“已按上一轮条件完成查询。”，当前问“那今年生效的呢”
  - 澄清请求：`帮我按年龄找一下`
  - 不支持场景：`麻烦帮我筛一下，即将领取生存金的保单`
- 对照证据：同一浏览器、同一 schema、同一 8050 服务下，`9月生效的康宁险种保单` 正常返回 `SUCCESS`，包含 `pol_effective_date_term BETWEEN [2026-09-01, 2026-10-01)` 与 `plan_full_name CONTAINS 康宁`，因此不是服务整体不可用或 verifier transport 故障。
- 本次 Summary 批量浏览器对照：`policy-search-rich-0001`（`合同号码里带4826的`）完成 `1/1` 后 Output 列为 `-`，Trace/Judge 均记录 8050 返回 `code=1001`、`data=null`、`final_output 为空对象`；同页随后运行 `policy-search-rich-0002`（`合同号码尾号4826的保单`），Output 正常显示 `SUCCESS + filter`。因此 Output 缺失是业务解析失败的真实结果，不是前端二次序列化删除字段。
- 建议定位范围：业务仓库 `parser_service.py` 的 deterministic/template → unsupported guard → LLM fallback 分支、`api/routes.py` 捕获异常前的结构化日志，以及 `context_ellipsis_resolver.py`；先保留五条独立回归用例，禁止用宽泛异常兜底伪装成 UNSUPPORTED。
