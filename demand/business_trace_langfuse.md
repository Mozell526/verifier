# 业务 Trace：Langfuse provider 需求

## 1. 背景

llm_probe 现有两个业务 Trace provider：

| provider | 证据来源 | 评测路线 | 过程六轴 |
|---|---|---|---|
| agno | AgentOS `/sessions/*/runs`、`/traces`（+可选 SQLite） | 案卷（reader → dossier → 环节表 links） | 全部支持 |
| llmtracing | 模型中转 JSONL，按 `X-Eval-Execution-Id` 切片 | 对话稿（transcript） | 暂不支持 |

很多被测业务系统用 Langfuse 埋点，既不是 Agno，也不经过 llmtracing 中转。它们的过程证据已经在 Langfuse 里，
verifier 目前读不到，只能做无 Trace 的基础评测。

## 2. 目标

新增 `langfuse` provider：被测业务每处理一轮请求，verifier 就从 Langfuse 取回这一轮的 trace 和全部 observation，
冻结为快照，供 trace_analysis、过程六轴和主轴使用。效果上与 agno 对齐，六轴全部可用。

- 场景配置仍是 `{provider: "langfuse", config}` 信封，只在注册表里加一个 provider，不改 agno/llmtracing。
- 不要求业务系统改用 Agno 或接 llmtracing；业务已有的 Langfuse 埋点能给多少证据就用多少，缺的明确降级（同 evidence-tier 方向）。

## 3. 为什么走案卷路线

Langfuse 的数据是一棵树：trace → observations（`parentObservationId` 连接），每个 observation 有类型、输入输出、起止时间、
level/statusMessage；GENERATION 另有 model、modelParameters、usage。这和 Agno 的 run/span 是同一种形状，
可以映射到 reader 现有的记录类别，六轴和环节表直接复用：

| Langfuse | reader 类别 | 说明 |
|---|---|---|
| trace（本轮） | runs（scope=current） | input/output/metadata/tags/userId/sessionId |
| 同 session 更早的 trace | runs（scope=history） | 只纳入能确定早于本轮的 |
| GENERATION / EMBEDDING | model_calls | input 是 SDK 记录的请求，不一定等于真正发给模型的请求 |
| TOOL | tool_calls | 参数 = input，结果 = output |
| RETRIEVER | tool_calls（另登记 references） | 检索查询与召回结果 |
| AGENT / CHAIN / SPAN | steps | 编排步骤，保留父子关系 |
| EVENT | events | |
| GUARDRAIL / EVALUATOR | steps | 业务自带的护栏/评估，不当成 verifier 的结论 |
| session | sessions | 采集时观察 |

## 4. 关联：怎样确定"这一轮"是哪条 trace

只用业务自身支持的 ID 精确关联，不按时间窗、会话里最新一条或正文相似度猜；零条或多条都判失败，并写明原因。

做法：verifier 用 binding 从请求或响应里取出业务 ID，再声明这个 ID 对应 Langfuse trace 的哪个字段：

- `id`：业务 ID 就是 Langfuse 的 trace id，直接 `GET /api/public/traces/{id}`；
- `metadata.<key>`：业务把自己的 ID 写进了 trace metadata，用 `GET /api/public/traces?filter=[{type:stringObject, column:metadata, key, operator:"=", value}]`
  查出唯一一条 trace，再取详情。v3.184.1 的 API 定义里已核实支持这种过滤（fern `trace.yml`）。

当前 Insurance（2026-10-15 验证）将 `response.trace_id` 定义为调用方 ID 的回显，
不传时为 null；内部 `TR-…` ID 另存于 `metadata.business_trace_id`。
因此验收请求每轮生成唯一 `body.trace_id`，新增埋点写入 `metadata.request_trace_id`，
provider 使用 request `/body/trace_id` → `metadata.request_trace_id` 精确关联。
不改变响应协议，也不把内部 ID 冒充调用方 ID。
这处埋点只在 Insurance 评测工作树里，作为 `feat(observability)` 提交（0a138c24）放在 `local(eval)` 配置提交之下，
同步上游时随评测提交栈一起 rebase；改动前的分支备份为 `eval/current-backup-20261016-26387129`。

不做零改造的 sessionId 匹配：Insurance 写入 Langfuse 的 sessionId 是 HMAC 后的值，外部算不出来；硬算等于把业务私有规则写进 provider。
## 5. 采集要求

- 鉴权：Basic（public key : secret key），密钥写成 `${ENV}` 引用，不进场景存储。
- 入库是异步的：先轮询到 trace 出现，然后等 trace 和 observation 内容连续 quiet 秒不再变化、所有非 EVENT 的 observation 都有 endTime，
  才算采齐。超时就标 partial，并写明还有哪些没结束。
- 分页、条数上限、详情读取失败都要显式记录；记录失败不抹掉已经取到的数据。
- 快照写进 `RunTrace.project_fields.business_trace`。轴运行期间不再访问 Langfuse。

## 6. 必须声明的限制（limitations）

- 只能看到业务埋点覆盖的部分。没埋点的工具、HTTP 调用、内部分支不可见，而不可见不等于没发生。
- GENERATION 的 input 是 SDK/集成记录下来的内容。可能被截断，也可能经过 mask，不保证就是发给模型的原始请求。
- 业务开了采样（sampleRate）、或者用后台任务另起 trace 时，本轮的部分调用可能不在这条 trace 里。
- Langfuse 的 scores 是业务方自己的评估，只登记为资料，不作为 verifier 结论。

## 7. 不做

- 不为证据补业务埋点。改业务只限「关联」：让 verifier 找到本轮 trace 所需的那一个 ID（一次性、固定、不随 case 增加）。
  业务没记录的内容（例如工具内部解析出的查询条件）按缺证处理并在结论中写明缺哪一步，可作为可观测性发现报告给业务方，由业务方决定是否补；verifier 不代改。

- 不把评测结果写回 Langfuse（scores）。
- 不读 Langfuse 的 prompt 管理、datasets、experiments。
- 不为 Langfuse 另建对话稿路线。

## 8. 通用化：agno 只是一个 provider

现状：provider 产出标准记录（reader 的 KINDS 加元数据键）；案卷 dossier、环节表 links、材料 materials、design_rules 读这些记录。
大部分逻辑已经只依赖记录契约，剩下的 Agno 假设集中在：

| 位置 | Agno 假设 | 处理 |
|---|---|---|
| `links.py` | `representation == "span"`（同一执行在 API 与 span 两种表示）、`agent_run_id` 桥接、`reconstructed_input.message_refs`、`_agent_definitions` | 这些都是"同一事实有两种表示或需要重建"时的回退。改成读 reader 声明的记录契约；Langfuse 只有一种表示，SDK 输入声明为 recorded_request（不保证 exact_request），回退分支自然不触发 |
| `links.py` `LIMITS`、`trace_analysis.py` 提示词 | 写死"从 Agno 结构枚举" | 文案由 reader 提供（同 `kind_notes` 的做法），Agno 保留原文 |
| `dossier.py` `_RENDER_KEYS` 等 | 键名源自 Agno，但语义是通用的 | 保留不改 |

约束：不影响现有效果。通用化是纯重构，验收标准与 llmtracing 第 1 期相同——
用 `report/business-trace-agno-20260913/snapshots/*.json` 等现有 Agno 快照，在重构前后各跑一遍 overview / dossier / links / 材料，输出逐字节一致；现有测试全部通过。
重构先单独落地、验收，再接 Langfuse。

## 9. 验收

- **测试对象：** Insurance（eval 工作树）开启 Langfuse：在 dev 配置里填 host/key，并打开 `capture_content: true`（同 `tracing_capture_io`，作为本地 eval 提交）。
- **跑通：** 「采集 → trace_analysis → 六轴 → 主轴」，至少覆盖单轮、多轮追问两种 case；同一批 case 与 agno 路线对照，看六轴结论是否一致。
- **降级：** 关联失败、入库未完成、字段被 mask 时，各轴分别输出缺证或降级，不能当成通过。
- **不回归：** agno、llmtracing 现有测试与快照的产出不变。

### Insurance 侧已知限制（会写进 limitations）

- 内容默认不上报（`capture_content: false`），关着时只有结构、模型名、token、耗时，没有输入输出。
- 打开后内容会经过 Insurance 自己的 `clean_content`（同事 2026-09-22 提交 405f02c3，依据见其 `docs/langfuse.md`「内容边界」，不是 verifier 的要求）：单字段最多 4000 字（上限 20000），保单号、手机号、姓名等键值和长数字被替换成 `[REDACTED]`。
  这会影响对"对象对不对"的判断（如保单号是否传对），这类检查只能判缺证。
- 截断不留标记：`clean_content` 最后一步是 `text[:max_content_chars]`，只截不标。provider 必须自己识别——字段长度等于上限的一律标 `truncated`，相关检查判缺证，不当成完整原文。截掉的是尾部；模型输入按 system → 历史 → 本轮 → 工具结果排列，最先丢的正是本轮问题和工具结果。
- 实测（5 个 Agno 快照，按 JSON 序列化后计长度）：模型输入 12/12 次超过 4000 字（13.9k–25.1k），调到 20000 仍有 3/12 超；工具结果 6/30 超 4000，均不超 20000。所以默认配置下模型轴基本只能判缺证；`max_content_chars: 20000` 只是配置项，不改业务代码，测试时建议调高。
- Agno 框架自带的 span 输入输出被隐藏（`hide_inputs/hide_outputs`），模型调用的输入输出靠 Insurance 自己的 sidecar 补；工具输入输出只有走 `backend.py` 的才有。

## 10. 当前实施状态

本机已部署 OSS 3.184.1，地址 http://127.0.0.1:3300，部署目录为
`/Users/xiaozijian/WorkSpace/package/langfuse-deploy`。沿用业务脱敏策略，验收配置长度上限为 20000。
provider、冻结 reader、通用案卷/环节材料已接入。合成 OTLP 验证与回归记录见
`report/business-trace-langfuse-20261015/validation.json`；真实保险业务对照单独记录，
不得把合成数据测试作为第 9 节真实模型评判验收通过的证据。
