# Authority / Key-index 优化检查报告（2026-08-05）

## 目标

修复调查包“资料能力导航”和“大资料内部具体值检索”混在同一个
MaterialDecision entry 中的问题，并检查 Authority / Judge 三态协议是否保持一致。

## 原问题

1. `authority.material-decisions` 为了召回具体产品名，把产品全称 YAML 的前 100 个值
   塞入集合层 `search_text`。当前 case 的“住院医疗保险”位于第 76 个，能够命中；
   尾部值“阖家团圆康”无法命中。这是 case 偏置，不是完整的大资料检索能力。
2. Authority 提示词只说“未命中不等于不存在”，没有要求首次 miss 后改写 query 并
   回退 Context Search/Load。
3. Judge 的 expectation 提示词只允许明确判 `fulfilled/not_fulfilled`，与协议允许
   `not_evaluable` 的三态口径冲突。
4. 调查报告的稳定 statement 混入“本次重查新增”等变更日志文字；EvidenceRef summary
   直接点名当前 case 值。

## 采用设计

```text
问题
  ↓
authority.material-decisions
  只定位“哪份资料决定什么”
  ↓
material.business-planfullname-enums.values
  在该大资料内部按完整分区定位具体值
  ↓
load_entry 返回 source_ref + locator（navigation_only）
  ↓
Context Search/Load 原始 Evidence
  ↓
Authority 现场综合 resolved / unresolved
```

两层均使用同一公共 Key-index 协议。索引结果仍不是 Evidence，也不能直接进入
`basis_evidence_ref_ids`。

## 修改检查清单

- [x] MaterialDecision 集合索引移除任意 first-N 源资料样本。
- [x] 新增产品全称大资料内部索引，74 个确定性分区覆盖 7343 个真实值。
- [x] `target_ref` 使用通用 `evidence-navigation://<source_ref>/<locator>` 导航引用。
- [x] Authority Environment 注册调查包中的多个 Authority 导航索引。
- [x] `load_entry` 只返回导航信息，保持 `navigation_only=true`。
- [x] Authority 首次 miss 后必须改写 query；仍 miss 时回退 Context Search/Load。
- [x] Judge expectation 提示词对齐三态协议。
- [x] 删除 EvidenceRef summary 中的当前 case 精确值。
- [x] 删除 MaterialDecision statement 中的“本次重查”变更日志口吻。
- [x] 更新 `investigate-keyindex.md`，明确集合层与单资料层两次应用。
- [x] 未修改、未冻结任何无关 source hash。

## 泛化 / AI hacking 检查

- 构建器不读取评测 case、reference answer 或 probe 结果。
- `search_text` 只来自 MaterialDecision 冻结字段或 YAML 中的真实值。
- 不添加人工同义词、case query、答案词或精确排名规则。
- 首段值“住院医疗保险”和尾段值“阖家团圆康”均通过同一机制召回。
- 集合层测试明确断言上述具体值没有被嵌入 MaterialDecision entry。
- Builder 连续重建 manifest 的 SHA-256 相同，说明投影可复现；该检查不是协议 hash 冻结。

## 测试结果

### 聚焦回归

```text
45 passed
```

覆盖：Authority runtime、调查 Key-index、client_search Judge 调查包。

### 扩大回归

```text
86 passed, 1 failed
```

唯一失败：

`test_validate_investigation_cli_fails_when_required_tool_inputs_are_missing`

该测试在到达“缺 smoke inputs”目标分支前，被既有 attribute 调查包 source hash drift
拦截。此问题在本次修改前已经存在，与 Authority / Key-index 优化无关。本次遵循用户
要求，没有通过重冻结 hash 绕过该问题。

### 静态检查

- `python -m py_compile`：通过。
- `git diff --check`：通过。
- Builder 重建一致性：通过。

## 尚未扩大的范围

当前只为已证明存在长尾召回问题的产品全称大资料建立内部索引。其他资料是否需要内部
索引，应以实际大小、召回失败和上下文成本为依据，不应预先给所有资料增加复杂度。
