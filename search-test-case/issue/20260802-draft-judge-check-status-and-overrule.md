# 2026-08-02 Draft Judge Check：现状对比 + 过度规则化审查（check skill）

> 本文档回答两个问题：(1) 当前现状与 draft/production 对比；(2) draft 实现是否过度规则化。
> not_evaluable 口径拆分（用户第 3 项）不在本文档范围，待单独讨论。
> 后台 30 条全量重跑仍在进行（见 §1.3），本文对比基于最近已完成的全量轮 007-run 与 148/088/133 定向实测。

## 一、现状

### 1.1 代码与资产状态（未提交改动，main @1f8de95）
- Draft Judge：`impl/projects/client_search/draft/judge.py`（1046 行，本轮 +807 行）、
  `judge_execution.py`（854 行）、`judge_strategy.py`。
- Authority 运行时：`impl/core/authority_environment.py`（522 行）、`authority_tool.py`、`authority_gate.py`。
- 共享层改动：`capability_manifest.py`（lean/full 分离 + 5 个枚举源）、`live.py`（full 开关）、
  `search_condition_compare.py`（语义 comparator 重构）；production `judge.py` 未动，但共享层改动会影响 production 行为。
- 资产：4 个 authority ContextUnit + business contract；investigation 包含 authority-conflicts-scan（20 处 value_mappings/enums 冲突观测）。
- 测试：12:07 全量回归 610 passed。

### 1.2 最近完成的全量对比（007-run，07:44，30 条冻结 badcase）
| 结果 | current | draft | case |
|---|---|---|---|
| 一致 | fulfilled/fulfilled ×14、not_fulfilled/not_fulfilled ×10、not_evaluable/not_evaluable ×3 | 27 条 |
| 差异 | not_evaluable → not_fulfilled | 038、148 |
| 差异 | fulfilled → not_evaluable | 093 |

差异明细：
- 038「一年内客户」：current NE → draft NF（isBuyInsurance 实际已解析，draft 可判）。
- 093「贵C826N1」（车牌号，空条件）：current fulfilled → draft NE（核心交付不可确认，边界处理 fulfilled）。
- 148「徐晓燕住院医疗保险」：current NE → draft NF（draft 命中 planfullname 枚举，定位缺保险条件）。

### 1.3 148/088/133 定向实测（新代码，issue 20260801-*，12:07）
| case | production | draft | 评价 |
|---|---|---|---|
| 148 | NF（reasoning 错误："清单无保险字段"，与 manifest 矛盾） | NF（证据正确：planfullname 命中"住院医疗保险"，定位缺条件+AND 组合） | draft 更好 |
| 088「7月盘客」 | fulfilled（对无权威的核心检索目标给肯定结论） | not_evaluable（核心 NE 0.96 + 边界 fulfilled 0.99） | draft 符合 spec §11-3 |
| 133「中银保信」 | not_fulfilled（要求把机构名虚构为 searchClientName 条件） | not_evaluable（核心 NE 0.90 + 边界 fulfilled 0.99） | draft 符合字段语义 |

三个 case `authority_tool_call_ids` 均空，同一环境快照（a702ae60…）。

### 1.4 后台 30 条重跑（11:49 启动，进行中）
- 集合：28 badcase + 2 session（非 007-run 的纯 30 badcase）。
- 进度：12:23 已处理 10/30（148/088/133/session×2/003/008/013/018/023），预计 ~13:00 完成。
- 完成后应产出 `iterations/008-run.json` 提供当前代码状态下的 definitive 对比。

## 二、check：过度规则化审查

### 审查结论
**存在过度规则化的风险，且 authority 机制被规则架空（未激活）；但规则以 prompt prose 而非
case_id 分支实现，机制层（枚举反查、fragment 语义命中、compact manifest、操作符校验）本身可泛化。**

### 证据

| # | 发现 | 严重度 | 说明 |
|---|---|---|---|
| R1 | prompt 变成 case-law 规则书 | P1 | `_build_core_context` 的 system_extras 约 6.6KB 手写决策 prose，其中多处是单 case 逐字特判：013「居家临界客户→jujiaClientGrade/居家潜客；actual 用 pajjmemberstatus CONTAINS [潜客,意向]」、148「住院医疗保险→planfullname」、088「盘客」、133「中银保信」、053/083「权益/年华→searchClientName」、048「掩码手机号 158****5078」、028「成交→poleffdate」、023「familyclientbirthday 仅 MATCH」。docstring 直接引用 case 号（013/148）。judge.py 本轮净增 807 行 |
| R2 | 规则预判掉 authority 该裁决的歧义 → authority 从未激活 | P1 | 30 条冻结集 authority_tool_call_ids 全空。设计意图（authority.md §8、ROLE.md）是"真实冲突→authority.resolve"，规则现在把已知冲突形状（unsupported、清单外、多字段命中）全部枚举结果，authority 变成 dead path；未见过的新冲突形状泛化依赖 prompt 覆盖而非 authority 机制（check 风险 a 的形态） |
| R3 | 半确定性混合：同一政策两个执行通道 | P2 | enum_completeness/unsupported_boundary 把静态 `decision_rule` prose 注入 prompt 让 LLM 照章执行；另一侧 `_apply_operator_capability_check`/`apply_authority_gate` 在代码层强制翻转 status。两条通道漂移即出矛盾（F1 unsupported 规则自相矛盾已实际发生一次） |
| R4 | 通用规则 + 例外打补丁 | P2 | `_operator_justified` 硬编码 MATCH≡CONTAINS（enum/list/extract）与范围族互容 blanket 政策，prompt 再为具体字段写例外（023 等）；规则与例外都在增长 |
| R5 | 泛化验证不足 | P3 | unseen 集仅 3 条（041/061/081）且无落盘结果；knowledge.md 的"被否决假设/泛化边界"为空；30 条冻结集同源（badcase 序列），无 valid/unseen 对照进本轮优化；ROLE.md 的 promotion 门槛要求 unseen 无退化，当前未满足 |

### 缓和因素（不构成完全过度规则化）
- 代码无 `case_id` 硬编码分支；规则是给 LLM 的 prose，机制函数（`_request_enum_hits`/`_semantic_field_hits`/
  `_compact_capability_manifest`/`_operator_justified`）对任意字段/枚举可复用。
- 确定性覆盖（操作符校验、authority gate）是代码层、可单测的，属用户认可的"LLM 综合 + 代码校验"。
- 规则 prose 中的 case 大多作为"机制示例"出现，底层反查机制本身是泛化设计。

### 改进方向（待与用户确认后实施）
1. 把 case 专属决策从 prompt prose 下沉到数据：字段归属（planfullname/abbrname/pCategorys 等）、
   语义等价（成交→poleffdate）、掩码格式等应来自 field_definitions notes / value_mappings / ContextUnit，而不是 judge prompt 手写。
2. 让 authority.resolve 真正承载"多源冲突"裁决：authority 材料当前 4 个 ContextUnit 全是"不能肯定结论"的
   限制说明，scan 记录了 20 处 value_mappings/enums 冲突却不裁决；应把 resolved 锚点（governs 唯一决定性）补进
   调查包，规则只定义"何时必须调 authority"，而不是把结果枚举完。
3. 规则收敛：把 enum_completeness/unsupported/operator 三类 decision_rule 收敛为单一确定性 gate +
   少量机制说明，消除 prompt 与代码双通道漂移。
4. 补 unseen/valid 回归集并纳入 loop：以 3 条 unseen + valid 对照做每轮无退化验证（promotion 门槛）。

## 三、check list 结论
| 检查项 | 结果 |
|---|---|
| 代码可编译/可加载/测试通过 | ✅（610 passed） |
| 产物与数据一致（solidify receipt 重建） | ✅ |
| 无 case_id 硬编码分支 | ✅ |
| 过度规则化（风险 a） | ⚠️ R1/R2 存在，需按 §改进方向收敛 |
| 局部样本修改（风险 b） | ✅ 未见（规则均为通用函数 + prompt） |
| 源头逻辑 vs 只改结果（风险 c） | ⚠️ 148/088/133 改的是机制与证据注入，但规则下沉位置（prompt vs 数据 vs authority）尚未定论 |
| 数据同步一致性（风险 d） | ✅（重跑中，008-run 待产出） |
| 冗余/失效代码（风险 e） | ⚠️ authority 运行时当前 0 激活，存在"未激活通道"风险，需 unseen 验证或收敛 |

