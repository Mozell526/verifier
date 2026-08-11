# Authority limitation: enum values

Scope：`client_search.authority.enum-values`

当前项目配置只能证明 parser 采用了某个枚举，不能单独证明它等于下游数据库的合法值全集。
缺少只读 ES 聚合或权威导出时，不得对依赖数据库真实枚举空间的判断给出肯定结论。

该限制只影响 `downstream-query-consumability` 中确实依赖下游实际值空间的 expectation；
actual 明确遗漏用户条件、字段格式明显错误等直接事实不受此限制。
