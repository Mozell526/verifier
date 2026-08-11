# Authority limitation: query equivalence

Scope：`client_search.authority.query-equivalence`

不同查询形式只有在封闭式等价规则成立，或同一数据快照上的客户身份集合证明确实相同，
才可以判定等价。缺少这两类证据时，不得用模型常识宣称两个查询形式等价。

该限制只影响需要证明查询形式等价的 expectation，不影响 actual 明确缺少或增加条件的直接判断。
