---
doc_type: startup
schema_version: 1
---

# Policy Search 启动说明

- 前置条件：`${POLICY_SEARCH_REPO}` 指向业务仓库，仓库内 `.venv` 和依赖已准备完成；需要完整 LLM 兜底时提供业务仓库要求的模型密钥。
- 启动方式：verifier 执行 `impl/projects/policy_search/scripts/start.sh`，从业务仓库启动 `main:main_app`，监听 `127.0.0.1:8050`。
- 健康检查：请求 `GET http://127.0.0.1:8050/api/v1/policy-search/health/ready`。
- 成功信号：HTTP 请求成功且返回可解析 readiness；未注入 LLM 时可能为 `NOT_READY`，确定性解析仍可用于最小链路验证。
- 常见失败：8050 端口冲突、业务虚拟环境缺失、配置文件不可读、模型密钥缺失或服务启动超时。
