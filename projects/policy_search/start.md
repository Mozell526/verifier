---
doc_type: startup
schema_version: 1
---

# Policy Search 启动说明

- 前置条件：`${POLICY_SEARCH_REPO}` 指向业务仓库，仓库内 `.venv` 和依赖已准备完成；完整 LLM 兜底复用 verifier 根目录 `.env` 中的 `BAILIAN_API_KEY`，手动启动脚本会将它注入为业务服务需要的 `DASHSCOPE_API_KEY`。
- 生命周期：Policy Search 由用户手动管理。verifier 只连接 `127.0.0.1:8050`，不会启动或重启服务。
- 手动启动：在 verifier 根目录执行 `impl/projects/policy_search/scripts/start.sh`。
- 手动停止：结束该脚本启动的 uvicorn 进程；verifier 不会重新拉起。
- 健康检查：请求 `GET http://127.0.0.1:8050/api/v1/policy-search/health/ready`。
- 成功信号：readiness 返回 `ready=true` 且 `llm_client_configured=true`。
- 常见失败：服务未手动启动、8050 端口冲突、业务虚拟环境缺失、配置文件不可读或模型密钥缺失。
