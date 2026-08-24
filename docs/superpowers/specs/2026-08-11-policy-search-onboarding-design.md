# Policy Search Verifier 接入设计

## 目标

把现有 `policy-search` 单轮 HTTP 解析服务接入 verifier，使用真实服务响应完成 mock、live、judge、attribute 和回归链路。服务默认监听 `127.0.0.1:8050`。

## 边界

- 只新增 `projects/policy_search/`、`impl/projects/policy_search/`、`impl/data/policy_search/`，并在 `impl/checklist/check1.py` 注册项目。
- 不修改 `policy-search` 业务仓库，不修改 verifier core/protocol/frontend，不复制业务解析逻辑。
- 业务仓库通过 `POLICY_SEARCH_REPO` 注册，服务地址通过 `POLICY_SEARCH_BASE_URL` 覆盖。

## 运行合同

- 交互：单轮。
- 服务：`POST /api/v1/policy-search/parse`。
- 健康检查：`GET /api/v1/policy-search/health/ready`。
- 请求保持 AskBob 外层协议；mock 负责填充 query、currentTime、agentCode、contexts 和追踪字段。
- live 输出归一为接口 code/msg 与业务 status/query/filter/message。合法 `UNSUPPORTED` 是业务结果，非接口故障。

## 组件

- `live_schema.py`：冻结真实请求和归一输出 dataclass。
- `live.py`：使用 verifier `LiveTransport` 调用 8050 服务并提取响应。
- `mock.py`：生成单轮真实用户意图和合法请求，覆盖原子条件、组合逻辑、时间边界、枚举别名、身份、澄清、不支持与上下文场景。
- `judge.py`：向通用 judge 提供业务协议、当前配置、golden manifest 和责任边界，不把被测实现本身当绝对标准。
- `attribute.py`：只提供首版归因上下文，复杂优化留给 draft 流程。
- `adapter.py`：只实现四个 `_load_*`。
- `scripts/start.sh`：从业务仓库现有虚拟环境启动 uvicorn，固定 8050。

## 数据与验证

- verifier 固化少量代表性 mock cases，不复制业务仓库全部 780 条 golden cases。
- 必须通过项目识别、adapter 合规、协议符合、live schema、mock-check、run-chain，以及全项目 adapter/protocol 副作用检查。
- `run-chain` 前启动真实服务；readiness 的 `NOT_READY` 允许服务存活，但依赖 LLM 的 case 可能 fail-closed，因此验收选用可确定性解析的最小请求。
