# Draft Key-Index 实验闭环设计

## 背景

现有 Draft Skill 已要求调查大型 Collection 的 Key-Index 策略，并比较 recall、可拒绝性、Target Resolution、上下文质量和成本。但它把 `selected/no_index/unresolved` 结论放在 Investigate 内，容易让执行者先凭架构判断选中 Index，再在 Solidify 和 Runtime 中落实；同时也没有明确要求最终选择必须由 Draft Loop 的端到端业务效果证明。

本设计把 Key-Index 定位为 Draft 候选能力：调查只提出候选，先通过低成本模拟 Search→Load 测试筛选，再把胜出候选接入 Draft Role，用冻结 Loop 评价业务质量、退化、token 和 latency。只有通过 Loop 的候选才成为正式调查资产并进入 Solidify。

## 目标

1. 避免在调查阶段过早固化 Index 方案。
2. 用低成本模拟测试淘汰明显不合格方案，避免每个候选都运行完整 Judge。
3. 让 Loop 的端到端结果而非单一检索指标决定最终方案。
4. 禁止使用 frozen case 的答案、expected trace 或人工答案词反向污染 Index。
5. 选中后才登记 Manifest、物化 Builder/Search/Load/Resolver 并移除未经证明的全量 fallback。

## 生命周期

```text
Collection navigation pressure
  → Investigate profiles and candidate strategies
  → freeze simulation probes
  → deterministic candidate builders
  → Search→Load simulation comparison
  → shortlisted candidate in Draft Role
  → frozen Current/Draft Loop comparison
  → provisional candidate implementation
  → frozen Current/Draft Loop comparison
  → selected / no_index / unresolved
  → final Manifest registration and Solidify refresh
```

### Investigate

Investigate 记录 Collection 的真实结构、规模、稳定标识、加载边界和消费目标，并提出多个合理候选。它不提前把未经实验的候选登记为正式 Key-Index，也不规定 Runtime 固定调用顺序。

### 模拟测试

在比较候选前冻结 probe set。根据真实资料覆盖稳定标识、源术语、非原文改写、歧义或多对象、无关或不支持问题以及 Search→Load。Builder 和 projection 必须确定性地来自真实 Collection。

模拟阶段至少比较：

- top-k target recall；
- irrelevant rejectability；
- target resolution 和 load 成功率；
- 加载条目数及上下文体积；
- 来源追溯；
- 构建和查询成本。

模拟测试只负责筛选导航策略，不把 SearchHit、score 或模拟期望当作业务 Evidence。

### Draft Loop

通过模拟测试的候选可在隔离 Draft 区域形成 provisional candidate，再临时接入 Draft Role；这一步只为运行验证，不代表正式 `selected`。每次可比较运行必须冻结候选实现、Current、objective、review 和 cases，并保留 Search→Load、Context、Tool、token、latency 与最终 RoleResult 审计。

Loop 同时评价：

- 业务判定是否改善且无退化；
- Index 是否召回并加载了决定当前 Case 所需的最小对象；
- 无关或不支持问题是否可拒绝；
- 是否出现全量 Collection fallback；
- prompt/loaded token、Tool 调用和墙钟延迟是否改善。

检索指标合格但端到端业务结果、成本或稳定性不合格的候选不得选中。

### 选择与 Solidify

只有被模拟测试和 Loop 共同证明的候选才能形成 `selected` 结论、登记到 Investigation Manifest，并刷新最终 Catalog/Builder/Search/Load/Resolver 与 Solidify receipt。`no_index` 必须由实验说明 direct load 更合适；`unresolved` 保留缺口，不能被静默改写为全量 fallback 或勉强 Index。

## 防过拟合约束

- 不得把 badcase、reference answer、expected trace、答案词或资料中不存在的同义词写入 Entry 或 query rewrite。
- Loop case 只用于评价候选，不直接生成或修补 Entry。
- 每轮运行前冻结候选实现；运行中不得按单 case 修改策略。
- 保留未参与候选调整的 holdout probes 或 unseen cases 做最终复核。
- Search miss、target resolution failure 和超预算必须显式记录，不得用全文模糊搜索或完整 Collection 注入掩盖。

## client_search 首次落地边界

1. 冻结字段检索 probes。
2. 比较当前启发式策略和至少一个严格 source-derived 候选。
3. 先执行 Search→Load 模拟比较。
4. 将胜出候选临时接入 Draft Judge，定向运行 048、073、088、138。
5. 同时比较业务判定、Tool audit、token 和 latency。
6. 证明有效后才把 `client-search.field-definitions` 登记为正式 Manifest Key-Index、Solidify，并移除 trace fields 为空时的全量 capability manifest fallback。
7. 定向通过后再运行冻结的 30 条回归。

## 非目标

本阶段不引入统一 `collection_access` schema，不修改 Core 为全局强制拦截器，不使用 embedding/reranker，不修改 frozen cases、Current baseline 或 Promotion 规则。
