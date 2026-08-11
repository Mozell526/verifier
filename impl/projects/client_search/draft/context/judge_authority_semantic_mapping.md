# Authority limitation: semantic mapping

Scope：`client_search.authority.semantic-mapping`

当前规则配置描述 parser 会采用的映射，但不能替代用户真实意图。口语表达存在多个合理映射、
当前请求又无法唯一确定且没有有效澄清规则或标准术语表时，对依赖该映射的 expectation
返回 `not_evaluable`。

用户已经明确表达、无需外部语义裁决的条件不得因此变成不可评估。
