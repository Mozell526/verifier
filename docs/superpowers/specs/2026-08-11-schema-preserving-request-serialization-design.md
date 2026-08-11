# Schema-Preserving Request Serialization 设计

## 目标

公共序列化不得改变已经进入 `RunTrace` 的请求事实。通过项目 `live_schema.REQUEST_SCHEMA` 校验的请求，在公开 Trace 中必须与实际请求严格相等；请求之外的展示数据继续使用现有公开字段白名单和空值压缩。

## 问题

`to_public_dict` 当前对所有 dataclass 和 dict 递归删除 `None`、`[]`、`{}`。Policy Search 的 `extra_input_params.args.contexts` 是必填列表，因此合法的 `contexts: []` 在运行后被删除，导致：

- `RunTrace.input` 和 `normalized_request` 不再符合项目 live schema；
- Summary 从 `MockCase.live_request` 切换到 `trace.input` 后，页面上的 contexts 消失；
- Live 页面把当前输入与被改写的 Trace 比较时产生错误的不匹配判断；
- `turn_records` 和 `live_exchanges` 中的请求事实也会被同一递归规则改写。

400 条 Policy Search rich mock 的只读模拟结果是：原始请求 400/400 合法；当前公共序列化后仅 16/400 合法且 0/400 与原请求严格相等。

## 设计原则

`live_schema` 是请求边界的校验器，不是序列化投影器。

1. 请求进入执行链路时继续由 `live_schema.check.request()` 严格校验。
2. 请求一旦作为执行事实进入 Trace，序列化时视为不透明 JSON 载荷，保留显式的 `None`、`[]`、`{}` 以及全部键。
3. 不根据 schema 删除额外字段，不自动补 `contexts: []`，不把非法请求改写成合法请求。
4. 请求之外的公开对象继续使用 `PUBLIC_SCHEMA_FIELDS`、`PUBLIC_DROP_KEYS` 和现有空值压缩。
5. 不增加兼容层、配置开关或项目专属字段表。

## 范围

以下请求事实必须原样序列化：

- `RunTrace.input`
- `RunTrace.normalized_request`
- `turn_records[].request`
- `live_exchanges[].request`
- 已经原样处理的 `MockCase.live_request`

`LiveExchange.request` 也必须保真，因为辅助物理请求不一定符合项目 `REQUEST_SCHEMA`，但仍是实际传输事实。

范围外：

- 不放宽 Policy Search live schema；
- 不修改 mock case 构造规则；
- 不修改 8050 业务服务；
- 不全局关闭公开序列化的空值压缩；
- 不修改 Judge 或 Attribute 的业务语义。

## 实现

在 `impl/core/schema/occam.py` 中增加一个只负责把协议事实转换为 JSON-safe 结构的内部函数。该函数递归处理 dataclass、dict 和 list，但不执行公开字段投影、`PUBLIC_DROP_KEYS` 删除或空值删除。

`RunTrace` 公共序列化继续由现有字段白名单控制；仅在处理 `input`、`normalized_request` 和 `turn_records` 中的请求节点时调用保真函数。`LiveExchange` 的 `request` 字段同样调用保真函数。其他字段沿用当前 `_to_public_dict`。

这个实现把“哪些 Trace 字段公开”和“公开请求内部是否可被改写”分开：前者仍由 Occam 白名单负责，后者由协议事实保真规则负责。

## 错误处理

- 序列化器不负责修复或再次解释请求。
- 缺失 `contexts` 的 `args: {}` 仍在现有 live schema 前置校验处失败。
- 循环引用继续产生现有 `recursive_ref` 标记，避免无限递归。
- 对协议请求中的非 JSON 标量沿用当前基础值处理；不新增字符串化或降级路径。

## 验证

单元回归必须覆盖：

1. Policy Search `contexts: []` 在 `input`、`normalized_request`、`turn_records[].request` 和 `live_exchanges[].request` 中均保留。
2. 四处请求序列化后与原请求严格相等，并继续通过 `check.request()`。
3. 非空 contexts 同样保真。
4. 显式可选空值，例如 `history: []`、`application_setting: null`，不被删除。
5. 非法 `args: {}` 不被自动补齐；带 schema 外空字段的非法请求也不被“洗成”合法请求。
6. 请求之外的空 Trace 展示字段仍被压缩，`PUBLIC_DROP_KEYS` 仍生效。
7. 400 条 `data/policy_search/mock_cases.json` 在模拟 Trace 序列化后保持 400/400 schema-valid 和 400/400 请求严格相等。

实现后通过浏览器按原路径回归：

- Live 页面请求 8050 后，Trace 中仍显示 `contexts: []`；继续请求 Judge 时不重复触发 Live。
- Summary 从 rich mock 运行单链路后，运行前后的 Input 不变，不出现当前结果与输入不匹配。

## 验收标准

- 请求事实序列化前后严格相等；
- Policy Search 400 条 rich mock 序列化后全部通过 live schema；
- 非法请求保持非法；
- 协议外公开输出仍保持当前压缩行为；
- 不引入项目专属兼容逻辑或 schema 放宽。
