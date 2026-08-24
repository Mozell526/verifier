# Authority limitation: evaluation boundary

Scope：`client_search.authority.evaluation-boundary`

Parser 负责保留用户条件并交付可消费查询；外部数据库没有匹配记录不自动归责 Parser。
若一个判断依赖尚未确认的产品责任边界，则该 expectation 为 `not_evaluable`。

该限制不得扩散到可以直接从请求与 actual 判断的条件遗漏、额外限制或格式错误。
