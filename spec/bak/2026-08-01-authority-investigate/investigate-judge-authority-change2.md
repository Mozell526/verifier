# Judge：actual-free Case 验收计划增量协议

本文是以下规范的 Planning 增量：

- `spec/alg/investigate-judge.md`
- `spec/alg/investigate-judge-authority.md`
- `spec/alg/investigate-judge-authority-change1.md`

发生歧义时，两份基线优先；Authority 状态、结果约束和人类澄清恢复以 change1 为准。
实施时先落地本文的 Case schema，再按 change1 第二章 §2.1 启用 Authority Gate；不得
长期保留旧 `judgment_kind` Authority 路由。

本文只解决一个问题：

> Judge 必须在 actual 可见前明确“当前 Case 到底要验收什么”，防止根据 actual 事后
> 增删或改写标准。

本文不调查 Authority、不改变 resolved/unresolved、不定义 Authority Gate，也不处理
人类澄清。它只提供 change1 可以消费的当前 Case 验收项、维度映射和精确
AuthorityAnalysis 依赖。

本文引入两个 Case 级内部 dataclass：

- `CaseEvaluationPoint`：当前 Case 中可以独立得到一个三态结果的业务验收点；
- `FrozenCaseEvaluationPlan`：actual 可见前冻结的全部验收点和 Authority 资产快照。

本文不引入：

- `judgment_kind`；
- `CaseAuthorityEvidence`；
- coverage registry；
- 产品期望/维度逐项审批协议；
- `not_applicable` 第四态；
- 额外 LLM semantic-review 阶段；
- 第二套 BusinessExpectation、EvaluationDimension 或 Authority schema。

---

# 1. 为什么需要 Case 验收计划

`investigate-judge.md` 已经区分：

- 产品级 `BusinessExpectation`：用户长期为什么使用产品、希望得到什么；
- 当前 Case 验收项：结合当前请求和评价维度，本次具体检查什么。

本文只为“当前 Case 验收项”提供 typed、actual-free 的运行时表示。

如果没有预先冻结，Judge 可能在看到 actual 后：

- 只生成 actual 容易满足的验收项；
- 遗漏 actual 表现较差的业务要求；
- 改写 acceptance criteria；
- 根据偏差程度事后调整 blocking；
- 切换到对 actual 更有利的 Authority 资产版本。

Plan 的业务价值是：

> 先定题，再看答案。

---

# 2. CaseEvaluationPoint

## 2.1 定义

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CaseEvaluationPoint:
    """当前 Case 中可以独立得到一个三态结果的业务验收点。"""

    point_id: str
    product_expectation_id: str
    evaluation_dimension_id: str
    authority_analysis_ids: tuple[str, ...]
    expected_outcome: str
    acceptance_criteria: tuple[Any, ...]
    blocking: bool
```

字段含义：

- `point_id`：当前 Case 内该验收点的唯一身份，由 Core 生成；
- `product_expectation_id`：该点服务于哪个项目级产品期望；
- `evaluation_dimension_id`：从哪个业务角度验收；
- `authority_analysis_ids`：承载 change1 定义的当前判断 Authority 依赖；字段语义、
  候选目录、选择边界和校验遵从 change1 §2.3，Gate 效果遵从 change1 §5；
- `expected_outcome`：当前请求下具体希望 Live 交付什么；
- `acceptance_criteria`：怎样的结果算满足；
- `blocking`：该点失败是否阻断关联产品期望的核心结果。

`CaseEvaluationPoint` 不是新的产品级 `BusinessExpectation`，因此不嵌套或复制完整
`BusinessExpectation`。产品角色、`use_scenario` 和长期 `desired_outcome` 通过
`product_expectation_id` 回到 Investigation 合同获取。

## 2.2 Point 的业务边界

Point 不是“最小语法条件”。一个 Point 的内部内容必须共享：

- 一个最终三态；
- 同一组决定性证据边界；
- 同一组 Authority 依赖；
- 同一种 blocking 业务影响。

这也是本文对基线“当前 Case 原子验收项”的具体解释：原子性指一个可独立聚合的业务
三态单位，不指把每个字段、条件或 acceptance criterion 都拆成单独对象。

只有满足以下任一条件时才拆成两个 Point：

1. 两部分可能合理地得到不同三态；
2. 两部分依赖不同证据或不同 Authority；
3. 两部分的 blocking 或下游业务影响不同。

以下内容不应机械拆分：

- 同一业务结果中的多个 AND 条件；
- 同一业务结果的 OR / 可替代实现；
- 使用相同证据、相同 Authority、相同三态和相同业务影响的多个细节。

例如：

```text
用户请求：
“找年龄大于 40 岁、居住在北京的高净值客户。”
```

可以形成：

```text
Point 1：明确条件得到完整保留
  - age > 40
  - city = 北京
  - 同一 comparator、同一三态、无业务术语 Authority

Point 2：“高净值”得到业务认可的解释
  - 依赖 semantic-mapping Authority

Point 3：最终查询能够被下游消费
  - 依赖下游协议或封闭式事实工具
```

Point 1 不必拆成“年龄 Point”和“城市 Point”。其中一个条件遗漏时，Point 1 为
`not_fulfilled`，具体差异写入 `missing` / `wrong`。

## 2.3 ID 责任

Planning LLM 只负责：

- 从 Core 给出的合法产品期望和评价维度目录中选择；
- 按 change1 §2.3 填充 Authority 承载字段；
- 描述当前 Case 的 `expected_outcome`；
- 给出 `acceptance_criteria` 和 `blocking`。

Core 负责：

- 校验所选 ID 存在；
- 校验维度确实服务对应产品期望；
- 按 change1 §2.3 校验和规范化 Authority 承载字段；
- 规范化 Point 内容；
- 生成当前 Case 内唯一 `point_id`。

LLM 不得生成：

- `point_id`；
- Authority 状态；
- asset ID；
- Authority snapshot；
- plan hash。

Authority ID 的选择与生成边界遵从 change1，本文不重复定义。

---

# 3. FrozenCaseEvaluationPlan

## 3.1 定义

```python
@dataclass(frozen=True)
class FrozenCaseEvaluationPlan:
    """actual 可见前冻结的当前 Case 验收计划。"""

    trace_id: str
    points: tuple[CaseEvaluationPoint, ...]
    authority_snapshot_sha256: str
    plan_sha256: str
```

字段含义：

- `trace_id`：计划属于哪个 Case；
- `points`：本 Case 必须逐项验收的问题；
- `authority_snapshot_sha256`：承载 change1 §2.4 定义的 Authority snapshot identity，
  失效处理遵从 change1 §5；
- `plan_sha256`：证明 actual 可见后计划内容没有被改写。

不增加 `plan_id`。`trace_id` 已确定 Case 范围，`plan_sha256` 已确定计划内容，第三个
身份没有独立业务意义。

`authority_snapshot_sha256` 不是新的 Authority 状态；其生成、空集合语义、匹配校验和
失效处理均遵从 change1。

## 3.2 真正冻结嵌套内容

`dataclass(frozen=True)` 只有浅层不可变性。Core 还必须：

- 将 `acceptance_criteria` 规范化为可稳定序列化的不可变值；
- 使用规范化序列化计算 `plan_sha256`；
- 在 Assessment 前复算并校验 hash；
- 拒绝任何嵌套对象被改写的 Plan。

## 3.3 actual-free 边界

Plan 只能读取：

- 当前用户请求；
- 项目级 BusinessExpectation；
- LiveBoundary；
- EvaluationDimension；
- 已 Solidify 的最小业务 Context；
- change1 §2.3 定义的 Authority 候选目录；
- 当前激活 Authority snapshot identity。

Plan 不得读取或包含：

- actual / final output；
- RunTrace 的 Live 输出部分；
- Comparator / ToolResult；
- FulfillmentAssessment；
- score / confidence；
- missing / wrong / extra；
- 任何后验 verdict。

actual 可见后不得新增、删除、合并、拆分或改写 Point，也不得切换 snapshot。

---

# 4. Planning 数据流

## 4.1 一次受约束的 LLM 调用

Planning 正常路径最多一次 LLM 调用：

```text
Core 提供：
  当前用户请求
  + BusinessExpectation 目录
  + EvaluationDimension 目录及 expectation_ids
  + LiveBoundary
  + 已固化的最小业务 Context
  + 当前维度可选的 AuthorityAnalysis ID / judgment_point 目录
        ↓
Planning LLM：
  选择本次相关的产品期望与维度
  + 选择每个 Point 实际依赖的 authority_analysis_ids
  + 描述 expected_outcome
  + acceptance_criteria
  + blocking
        ↓
Core：
  校验产品期望与维度引用
  + 按 change1 校验 Authority 引用
  + 生成 point_id
  + 规范化其余字段
  + 冻结 FrozenCaseEvaluationPlan
```

本文不要求 LLM 对所有配置项逐项输出 `applicable / not_applicable`，也不把适用性决定
塞入 `GateDecision`。

原因是 Core 只能确定性证明 ID 和引用是否合法，不能证明自然语言场景选择一定正确。
强制生成完整审批矩阵会增加 token、ID 和误判入口，不会把语义选择变成确定性事实。

## 4.2 Core 可以校验什么

Core 必须拒绝：

- 未知 `product_expectation_id`；
- 未知 `evaluation_dimension_id`；
- 维度没有引用对应产品期望；
- Authority 引用不满足 change1 §2.3；
- 空 `expected_outcome`；
- 空 `acceptance_criteria`；
- 重复 `point_id`；
- 同一 Point 引入互相矛盾的验收条件；
- Plan 泄露 actual 或后验结果；
- `plan_sha256` 无法复算；
- Authority snapshot 不满足 change1 §2.4。

Core 不得声称可以确定性证明：

- LLM 是否遗漏了语义上必要的 Point；
- LLM 是否遗漏了某个 Point 语义上必需的 Authority 依赖；
- 自然语言 `use_scenario` 选择一定正确；
- acceptance criteria 的业务描述一定完整；
- blocking 一定符合真实业务影响。

这些属于 Planning 准确性问题，必须通过中文冻结 cases、Draft Loop、遗漏率和人工审查
验证。

## 4.3 不适用不是第四态

当前请求不属于某个 `BusinessExpectation.use_scenario` 时，不生成对应 Point。

```text
不属于产品场景
  → 不生成 Point

属于产品场景，但证据不足
  → 已生成 Point 的 assessment 为 not_evaluable
```

Plan 不增加 `not_applicable` fulfillment 状态。

---

# 5. Assessment 与 Authority 串联

## 5.1 Assessment 映射

继续复用现有 `FulfillmentAssessment`。在不修改公共 schema 的前提下：

```text
FulfillmentAssessment.expectation_id
    → CaseEvaluationPoint.point_id
```

这是兼容映射。是否将公共字段重命名为 `point_id`，属于基线 Judge schema 的独立变化，
不在本文扩展。

Assessment LLM：

- 必须逐个输出 Plan 中 Point 的三态；
- 不得新增或删除 Point；
- 不得修改 acceptance criteria 或 blocking；
- 不得更换 product expectation、dimension 或 Authority snapshot。

`FulfillmentAssessment.evidence_refs` 由 Core 从当前 trace、Comparator 和已验证 Tool
结果中附加；LLM 不得自己构造可信 `EvidenceRef`。

## 5.2 与 change1 的唯一接口

change2 只承载：

```text
CaseEvaluationPoint.authority_analysis_ids
FrozenCaseEvaluationPlan.authority_snapshot_sha256
```

这两个字段的来源、选择、规范化、校验、snapshot 失效、Gate、summary 和人类恢复全部
由 change1 定义。change2 不复述、不覆盖，也不建立第二套 Authority 规则。

---

# 6. 中文案例

## 6.1 “高净值客户”

actual 不可见时，Planning 得到：

```python
FrozenCaseEvaluationPlan(
    trace_id="trace-high-value",
    points=(
        CaseEvaluationPoint(
            point_id="由 Core 生成",
            product_expectation_id="find-target-customers",
            evaluation_dimension_id="search-intent-preservation",
            authority_analysis_ids=("semantic-mapping-authority",),
            expected_outcome="“高净值客户”得到业务认可的查询表达",
            acceptance_criteria=(
                "映射遵从当前已 Solidify 的业务语义规则",
            ),
            blocking=True,
        ),
        CaseEvaluationPoint(
            point_id="由 Core 生成",
            product_expectation_id="find-target-customers",
            evaluation_dimension_id="downstream-query-consumability",
            authority_analysis_ids=(),
            expected_outcome="生成的查询能被当前客户搜索服务消费",
            acceptance_criteria=(
                "字段、操作符、值和组合结构符合当前下游协议",
            ),
            blocking=True,
        ),
    ),
    authority_snapshot_sha256="Core 按 change1 规范计算",
    plan_sha256="Core 根据规范化 actual-free 内容计算",
)
```

这个 Plan 表达本次要验收的两个问题及其 AuthorityAnalysis 引用，但不包含：

- “高净值”最终应该映射成什么；
- actual 使用了哪个字段；
- Authority 是 resolved 还是 unresolved；
- 最终三态。

两个 Point 的 Authority Gate 结果不在本文定义，统一按 change1 处理。

## 6.2 多个明确条件不机械拆分

```text
用户请求：
“找年龄大于 40 岁、居住在北京的女性客户。”
```

若年龄、城市、性别：

- 都来自当前用户原文；
- 都由同一 comparator 判断；
- 都不依赖不同 Authority；
- 都具有相同 blocking 影响；

则可以形成一个 Point：

```text
“用户明确表达的筛选条件被完整保留。”
```

具体缺失或错误条件进入 `missing` / `wrong`，无需生成三个 Point。

## 6.3 OR 替代方案不制造假失败

```text
业务允许：
clientGroupLabel = 创业新贵
或
clientGroupLabel = 创富一代
均可满足同一个高净值目标。
```

两者是同一业务结果的替代实现，应保留在一个 Point 的 acceptance criteria 中，不得拆成
两个 blocking Point，导致只满足其中一个时出现一个虚假的 failure。

---

# 7. 失败与版本边界

Planning 失败：

- 合法 ID 或关系无法建立；
- 无法生成非空验收标准；
- actual-free 边界被污染；
- Plan 无法规范化或 hash 无法复算；
- Authority 承载字段不满足 change1。

Planning 准确性退化：

- 漏掉必要 Point；
- 生成无业务意义的 Point；
- 错误拆分 AND / OR；
- 把不同 Authority 依赖的问题错误合并；
- blocking 与真实业务影响不符。

前一类由 Core 拒绝；后一类通过 Draft Loop 和冻结 cases 发现。不得用脆弱关键词规则
假装确定性修复语义准确性。

源码或 Authority hash 变化只使旧 Plan 失效，不授权自动 Investigation、Solidify 或
Role 重写。

---

# 8. 实施与验收

## 8.1 实施任务

1. 新增 `CaseEvaluationPoint`；
2. 新增 `FrozenCaseEvaluationPlan`；
3. 用 Point 替代 runtime 对产品级 `BusinessExpectation` 的机械复制；
4. 由 Core 生成 `point_id`、规范化嵌套内容并计算 plan hash；
5. Planning 隔离 actual，正常路径只进行一次 Planning LLM 调用；
6. 删除 `judgment_kind`、`plan_id`、applicability 决策矩阵和额外语义复核调用；
7. Planning 按 change1 填充每个 Point 的 `authority_analysis_ids`；
8. Authority 引用和 snapshot 统一交给 change1 校验；
9. Assessment 严格复用冻结 Point；
10. 将 Authority 承载字段交给 change1，不在 change2 实现第二套 Gate；
11. 保存 Planning 和 Assessment 原始产物，支持不调用外部 LLM 的离线 replay。

## 8.2 最低验收

至少覆盖：

1. actual 在 Planning 阶段不可见；
2. actual 后不能新增、删除或改写 Point；
3. `point_id` 由 Core 生成且当前 Case 内唯一；
4. 未知产品期望和未知维度被拒绝，Authority 非法关系按 change1 被拒绝；
5. criteria 嵌套内容变更会导致 hash 校验失败；
6. Plan 不包含 actual、assessment、score、confidence 或 verdict；
7. 同一证据/Authority/三态/业务影响的多个条件不会被机械拆分；
8. 不同 Authority 或不同三态的问题被拆成不同 Point；
9. OR / 可替代实现不会生成多个 blocking failure；
10. Assessment 不能增加或遗漏 Point；
11. change2 只承载 Authority 引用和 snapshot，其余行为完全遵从 change1；
12. snapshot 变化按 change1 处理；
13. 正常路径最多一次 Planning LLM 和一次 Assessment LLM；
14. 离线 replay 不调用外部 LLM；
15. Point 遗漏率和 `not_evaluable` 率作为 Draft 退化指标。

完成后必须满足：

- 继续遵从两份基线 spec 和 change1；
- Case 层只新增两个职责单一的 dataclass；
- Plan 不保存 Authority 状态或规则；
- change2 不重新定义 Authority Gate、summary 或澄清恢复；
- Authority 字段的 LLM/Core 责任边界遵从 change1；
- Current / Draft 只有在相同冻结数据上证明 Draft 更准确且无退化后，才允许提出
  Promotion。
