# DeerFlow Mock Investigation

本调查包将 DeerFlow Mock 的业务价值、评估维度、开放需求空间和用户知识边界固化为唯一 JSON 合同：

- `docs/mock-investigation-contract.json`

候选 Mock 必须通过同一份合同生成具体用户处境，并保持：

- 开放用户群体，而不是历史 Case 或场景枚举；
- `user_context → user_intent → query` 的事实一致性；
- 固定 intent 存在时不补造月份、金额、机构、人物、视角或历史对话；
- 普通业务用户视角，不泄漏源码、Prompt、API、机器标识或评估术语；
- 对澄清、权限、领域和服务可见现象保持诚实边界。

`deerflow.mock_business_input_validate` 只验证请求形状和硬知识边界；开放性、自然度、事实保真及业务质量仍由 Draft Harness review 判断。
