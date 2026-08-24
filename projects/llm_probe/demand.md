---
doc_type: requirements
schema_version: 1
---

# llm_probe 测评需求

- 业务目标：把任意非流式 HTTP JSON 接口当成带 LLM 的能力片段来评。Case 给出 curl 形状的请求（url/header/json body）以及对该能力的描述；输出统一收成字符串，再交给 judge。
- 范围：单轮、非流式 POST/PUT/PATCH；现有业务项目只作为默认 URL 和能力口径来源，不在本项目里复制它们的 adapter。
- 非目标：不评流式/SSE；不把各业务项目的字段协议写进本项目 live_schema；不做归因优化；不替被测服务生成 gold output。
- 核心场景：http_probe。一条 case 就是一次探针调用。
