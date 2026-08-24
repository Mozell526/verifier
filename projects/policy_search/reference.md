---
doc_type: reference
schema_version: 1
---

# Policy Search 资料入口

- 资料来源：`${POLICY_SEARCH_REPO}` 中的接口文档、查询语法树协议、当前技术方案、生产配置、字段/场景注册表和人工审核 golden dataset。
- 用途：为 mock 场景设计、judge 语义判断和 attribute 根因定位提供当前业务证据。
- 适用范围：Policy Search verifier 接入与后续测评优化；资料是证据而非被测输出的自证。

关键位置：

- `docs/保单搜索算法解析接口文档（智能体对接稿）.md`
- `docs/保单搜索查询语法树协议（首期精简版）.md`
- `docs/保单搜索算法解析技术方案（当前实现版）.md`
- `src/main/python/policy_search/configs/insurance_search_business_config_prd.json`
- `src/main/python/policy_search/configs/insurance_search_runtime_config_prd.json`
- `src/main/python/policy_search/data/golden_dataset/`
