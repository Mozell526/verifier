# Client Search Planning 与 Authority 精确度设计

## 目标

修复 client_search Draft Judge 的三类准确性问题：

1. 业务适用性被关键词代码提前决定，导致“十里堡”“2023年生”等真实客户搜索请求被误判为不适用；
2. Planning 在未看到 actual 时提前激活 Query Form 等 Authority，导致确定性判断被过度约束为 `not_evaluable`；
3. Authority Gate 改写 assessment 状态后，`reasoning_summary` 仍保留 Gate 前结论。

不得增加 LLM 调用，不得为 badcase 写专用分支，不得改变未开启该能力的 Production 行为。

最终目标不是增加 `not_evaluable` 的数量，而是让三态落在正确证据边界上：

- 结论确实依赖尚未解决的 Authority 时判 `not_evaluable`；
- 当前用户输入与 actual 已有充分、直接证据时，必须在 `fulfilled` 与
  `not_fulfilled` 中作出判断；
- Authority 不得覆盖本可确定判断的字段、操作符、值、逻辑或边界事实。

## Draft 生命周期

本优化使用 Draft Skill 的标准生命周期，不直接围绕单个 badcase 修改 prompt：

```text
Investigate
  调查项目级 Authority 判断点、冲突源、因果链与可验证能力
    ↓ validate_investigation.py
Solidify
  将稳定事实固化为 ContextUnit/Tool，将 unresolved Authority 注册为 Gate
    ↓ solidify receipt + candidate smoke
Draft Loop
  冻结 Production、目标、review 和小批 cases，同输入运行 Current/Draft
    ↓ role review
Investigate / Solidify / 下一小批 / promotion-only checks
```

Investigate 只记录业务事实、证据来源和验证边界，不预选针对某条 case 的算法。
Solidify 必须证明每项 AuthorityAnalysis 从合同 source ID 到候选资产再到 runtime
observable 的映射。Loop 只保存原始两侧结果和异常，由 Harness 按本设计进行语义判优。
本目标不包含自动 Promote。

## 数据流

```text
RunTrace（pre-actual）
    ↓
Judge Planning（现有一次 LLM 调用）
    ├─ applicable_product_expectation_ids
    └─ CaseEvaluationPoint[]
           authority_analysis_ids = Point 本身天然依赖的 Authority
    ↓ 冻结
FrozenCaseEvaluationPlan
    ↓ + actual
Judge Assessment（现有一次 LLM 调用）
    └─ FulfillmentAssessment[]
           authority_analysis_ids = 本次 actual 比较实际触发的 Authority
    ↓
Core Authority Gate
    ├─ 校验 Assessment Authority 是否存在并覆盖当前 dimension
    ├─ resolved：保留 assessment
    └─ unresolved：该 assessment → not_evaluable
                         ↓
                  重建 Judge summary
```

## 最小 Schema 变化

不新增 dataclass，只扩展现有 LLM 输出结构：

- `JudgeLLMOutput.applicable_product_expectation_ids: list[str]`
  - 仅 Planning 使用；
  - 空列表明确表示 planning 判定当前请求不适用；
  - 非空 ID 必须属于项目提供的 ProductExpectation catalog。
- `JudgeFulfillmentAssessmentOutput.authority_analysis_ids: list[str]`
  - 仅 Assessment 使用；
  - 表示本次 actual 比较真正依赖的 Authority；
  - Core 校验其存在性、dimension 覆盖关系及状态。
- `FulfillmentAssessment.authority_analysis_ids: list[str]`
  - 保存同一显式业务关系，供 Gate、summary 与审计消费。

## 适用性规则

client_search Draft 不再使用词语重合结果提前返回 `not_applicable`。Planning 同时读取：

- 当前用户请求；
- `BusinessExpectation.expectation_id/use_scenario/desired_outcome`；
- EvaluationDimension catalog。

Planning 必须显式选择适用的 ProductExpectation。选择为空时，Core 使用 Planning 的中文 `reasoning_summary` 输出不适用原因。结构错误、未知 ID 或“适用但没有 Point”属于 planning failure，不能伪装成不适用。

该行为由项目 context 显式 opt-in，未开启的 Production 保持原行为。

## Authority 激活规则

Planning 的 Point Authority 与 Assessment Authority 含义不同：

- Point Authority：即使还没看到 actual，该验收问题本身也无法绕开某项 unresolved Authority；
- Assessment Authority：看到 actual 后，这次比较确实出现了需要该 Authority 裁决的冲突。

Core Gate 使用两者并集，但 Assessment 新增的 Authority 必须覆盖 Point 所属 dimension。仅仅“属于同一维度”不构成 LLM 选择理由；prompt 要求先写出当前比较中的两个冲突说法，再选择对应 Authority。

client_search 的证据触发顺序固定为：

1. 先使用当前请求、actual、字段定义、封闭值域规则和确定性 comparator 尝试直接裁决；
2. 直接证据足够时，`authority_analysis_ids` 必须为空；
3. 只有存在两个相互冲突的业务说法，且现有证据不能确定哪一个代表真实业务语义时，
   才能选择覆盖当前 Point 的 Authority；
4. 选择 Authority 时必须在 assessment evidence 中记录冲突双方、已经检查的直接证据、
   缺少的决定性依据；缺一项即视为 Authority 误激活；
5. unresolved Authority 只能将明确依赖它的 Point 改成 `not_evaluable`，不得扩散到
   同 dimension 的其他 Point。

示例：

- `17、18周岁` 对 `RANGE [17,18]`：整数闭区间可直接判断，不激活 Query Form Authority；
- “高净值”对某个字段和值：若业务映射资料冲突，激活 Semantic Mapping Authority；
- 姓名或产品名称完全相同：不激活 Authority；
- 不支持投保日期是否属于可接受产品边界：只有本次结论依赖责任边界冲突时，激活 Evaluation Boundary Authority。

## Gate 后摘要

只要 Gate 将任一 assessment 改成 `not_evaluable`，Core 必须重新生成面向人类的中文 `reasoning_summary`，至少包含：

- 哪个业务判断点不可评价；
- 哪个 Authority 未解决；
- 当前缺少的决定性证据或冲突原因；
- `unresolved_question`，即人类补充什么信息后可以重新调查。

不得保留“所有期望均 fulfilled”等与最终状态矛盾的结论。

## 验证

1. 单元测试覆盖 planning 适用性、未知 ProductExpectation、Authority dimension 校验、Gate 后 summary。
2. 使用已暴露的 badcase 子集进行 Current/Draft Loop，验证已知退化被修复。
3. 数据源固定为
   `/Users/xiaozijian/WorkSpace/projects/claude_code/verifier-branch/verifier/data/client_search/badcase.json`，
   当前 SHA-256 为
   `7513a0767900df78cfe073a18fc22dcdba2c05e4e15a52afa88c43461b13c0b7`，
   共 168 个唯一 case。
4. 历史状态或 probe 已暴露的真实 badcase 不得进入 promotion-only 数据：
   `001/012/033/041/061/081/126/167`。
5. 阶段 Loop 每轮只引入 3-5 条新 case，并回放固定回归哨兵。修改 candidate 或
   iteration cases 后必须重新冻结 Loop；不得沿用旧 fingerprint。
6. 同一 case 只生成一份冻结 Live `RunTrace`，Production 与 Draft 必须消费完全相同的
   input、actual、reference、模型配置和运行环境。
7. 实现冻结前，以稳定哈希从未暴露 case 中预留 40 条 promotion-only cases；优化期间
   不读取其请求、注释、actual 或 Judge 结果。实现冻结后才生成 RunTrace，并在打开
   Current/Draft 结果前根据用户输入、actual 和人工注释登记预期三态与 Authority。
8. 终验至少取得 36 条双方均有效的结果；基础设施失败保留原始事实但不冒充业务三态，
   必要时从预留补充池补样本。
9. 每条有效结果分别审查：
   - overall fulfillment 与逐 Point 三态；
   - Authority 过激活、漏激活和类型误选；
   - Authority 是否只约束真实依赖的 Point；
   - Gate 后 `reasoning_summary` 是否与最终状态一致。
10. 只有 Draft 的 Authority/三态错误数严格少于 frozen Production，且不存在
    “Production 正确、Draft 错误”的可见业务退化，才可判定 Draft 更优。结果相同、
    confidence 更高、文本更长或局部改善伴随退化均不算成功。
11. 只有 Draft 相对 Current 更准确、没有可见退化、且运行侧不存在未解释的 LLM
    基础设施失败时，才允许进入 promotion-only checks；是否 Promote 仍需用户明确确认。
