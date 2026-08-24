# Authority 可选模式下的 Judge 三态设计

## 背景

当前 client_search Draft Judge 在发现能力或职责边界候选、但
`verifier.authority.enabled=false` 时，会把相关 blocking assessment 确定性改成
`not_evaluable`。该行为使 Authority 关闭模式无法直接评价 Live 是否满足用户意图，
也把“没有启用 Authority”错误等同于“Authority 已查证但无法确定”。

现有协议同时明确：

- Judge 评价用户想办成的事是否实际交付；
- Authority 是通用业务标准裁决能力，不负责直接输出 Judge verdict；
- Authority 不只裁决职责内外，也裁决语义映射、查询等价、能力范围和资料冲突；
- 职责外或依据不充分类 `not_evaluable` 必须有真实 Authority 查证记录；
- 如实拒绝只能证明透明说明，不能替代用户核心结果。

因此不能采用“Judge 先输出 `not_fulfilled`，Authority 再把它机械转换为
`not_evaluable`”的单向后处理模型。

## 目标

1. Authority 关闭时，Judge 根据用户意图与 Live 实际交付，尽量输出
   `fulfilled` 或 `not_fulfilled`。
2. Authority 开启时，Judge 在最终状态依赖业务标准时调用 Authority，并允许裁决改变
   对交付事实的业务解释。
3. 只有合法协议成因才能产生 `not_evaluable`，不能把 Authority 未启用当作业务 NE。
4. 保留 Authority 对语义映射、查询等价、枚举范围、能力和职责等多类问题的通用能力。
5. 不增加兼容层、迁移逻辑、case ID 特判或新的状态类型。

## 核心模型

Judge 采用三个逻辑阶段。它们是职责分层，不要求拆成三个独立运行组件。

### 1. 意图与交付事实层

Judge 先形成不依赖最终三态的事实：

- 用户的核心业务意图和各个阻断维度；
- Live 实际交付的结果、条件、说明和错误；
- 明确满足、明确缺失、明确错误和可能等价的维度；
- 最终判断依赖的业务标准问题。

这一层不能因为 Live 如实拒绝就把核心交付标为已满足，也不对职责归属作无依据的
权威声明。

### 2. 可选 Authority 治理层

当 Authority 开启，且某个 blocking assessment 的最终判断依赖业务标准时，Judge 使用
`authority.resolve` 裁决该标准问题。问题仍必须是自包含的业务问题，不能询问“本次
Live 输出是否正确”。

Authority 可能裁决：

- 业务词与字段、枚举值之间的语义映射；
- 两种查询表达是否业务等价；
- 某字段、值、操作符或组合是否处于可表达范围；
- 某能力是否属于产品职责；
- 多份规则或事实冲突时当前范围内采用哪一种说法。

Authority 返回的 resolved statement 作为最终评价的业务标准输入，而不是直接作为
Judge verdict。Authority 返回 unresolved 时，只有依赖该问题的 assessment 进入
`not_evaluable`。

### 3. 最终三态裁决层

最终状态按 blocking 用户意图聚合：

- 证据证明核心意图已达成：`fulfilled`；
- 核心意图明确未达成：`not_fulfilled`；
- 存在协议允许且阻断最终判断的不可评价原因：`not_evaluable`。

Authority 可以改变事实的业务解释，因此 resolved 后可能得到 F、NF 或 NE，不能只实现
NF→NE 的单向转换。

## Authority 关闭模式

Authority 关闭时：

1. Judge 使用当前 trace、普通业务上下文和确定性工具结果直接评价用户意图。
2. 核心结果缺失、错误或漏掉阻断维度时，输出 `not_fulfilled`。
3. Live 明确表示“不支持”但没有交付核心结果时，核心交付仍为 `not_fulfilled`；透明说明
   可以作为单独的 non-blocking expectation 评价。
4. 不得仅因存在 capability/responsibility candidate、coverage gap、空 conditions 或拒绝
   提示，把 assessment 改成 `not_evaluable`。
5. 不得声称 Authority 已确认职责内、职责外、正式语义或资料优先级。
6. 输入坏、完全无关、实际输出或必要 trace 无法取得等不依赖 Authority 的合法原因，仍可
   输出 `not_evaluable`。

该模式是非治理的效果评价模式：它回答“从用户意图和当前可见交付看，办成没有”，不回答
“该产品在权威标准下是否应当具备此能力”。

## Authority 开启模式

Authority 开启时：

1. 不依赖业务标准的明确交付事实直接评价，不为调用而调用 Authority。
2. 影响 blocking 结论的语义、等价、能力或职责问题必须调用 Authority。
3. resolved 后，Judge 使用 statement 重新完成相关 assessment：
   - 标准确认实际交付等价满足用户意图：`fulfilled`；
   - 标准确认职责内且核心交付缺失或错误：`not_fulfilled`；
   - 标准确认职责外：`not_evaluable`，原因标记为职责外；
   - 标准确认职责内能力缺失：结合交付判断，未达成仍为 `not_fulfilled`。
4. Authority 真正完成查证但返回 unresolved：依赖项为 `not_evaluable`，并附带缺料清单。
5. Authority Tool 或 Agent 执行失败不能伪写成资料冲突或职责外；依赖项为
   `not_evaluable`，原因明确标记为 Authority 能力不可用。

## 状态矩阵

| 场景 | Authority 关闭 | Authority 开启 |
|---|---|---|
| Live 明确完整满足用户意图 | F | F；若等价性是决定性问题，先经 Authority 确认 |
| Live 明确漏掉或做错核心维度 | NF | 职责内为 NF；业务解释可能经 resolved statement 修正 |
| Live 如实回复暂不支持但未交付结果 | NF | 职责内能力缺失为 NF；职责外为 NE |
| 当前表达疑似是合法等价表达 | 按普通上下文作最佳 F/NF 判断 | Authority 确认等价后可为 F，不等价则 NF |
| 能力或职责边界资料不足 | 不因 Authority 关闭自动 NE，按交付作 F/NF | 真查证后 unresolved 为 NE |
| 用户输入损坏 | NE | NE |
| 请求与产品完全无关 | NE | NE，不要求 Authority |
| Authority 调用执行失败 | 不适用 | NE，明确为工具能力不可用，不冒充业务结论 |

## 实现边界

### 协议

- 更新 `spec/alg/fulfilled.md`，增加 Authority enabled/disabled 两种模式，并明确事实层与
  最终状态分离。
- 更新 `spec/alg/authority.md`，明确 Authority 关闭时调用方可以做非治理的 F/NF 效果
  评价，但不得伪造 Authority 结论。
- `spec/alg/material-positioning.md` 不改变四类资料定位和 Gate，只在必要时补充交叉引用。

### Draft Judge

- 删除 Authority 关闭时强制 NE 的 `_apply_unresolved_boundary_gate` 分支。
- Authority 开启时保留并收紧已有 Authority resolution 消费和审计校验。
- 调整 Judge prompt contract，使关闭模式要求 intent-based F/NF，开启模式要求只对决定性
  标准问题调用 Authority。
- 不新增第二套 Judge、兼容 gate 或配置项。

### 测试

Authority 关闭模式至少覆盖：

- 完整交付 → F；
- 核心条件缺失 → NF；
- 空结果并声明不支持 → NF；
- 部分维度满足、部分维度缺失 → 整体 NF；
- 输入坏和完全无关仍为 NE；
- capability/responsibility candidate 本身不能触发 NE。

Authority 开启模式至少覆盖：

- 语义等价 resolved → F；
- 职责内正常但交付缺失 → NF；
- 职责内能力缺失且未交付 → NF；
- 职责外 resolved → NE；
- 查证完成但 unresolved → NE；
- Tool failure → NE，且原因不是业务 unresolved；
- Authority 只影响依赖该问题的 assessment，不污染独立维度。

## 验收标准

1. Authority 关闭时，073、088、093、113、133、148 等核心结果未交付场景不再仅因边界候选
   自动变成 NE，而是按各自用户意图与 Live 交付得到 NF。
2. Authority 开启的 mock 矩阵能分别稳定得到 F、NF、职责外 NE、unresolved NE 和工具失败
   NE。
3. Authority 的语义映射、等价、能力、职责和冲突裁决能力均未被删除或降格。
4. 每个 NE 都能指出合法成因；职责外和依据不充分 NE 均存在真实 Authority 调用记录。
5. 如实拒绝不能替代核心交付；non-blocking 透明说明不能覆盖 blocking NF。
6. 不增加 case-specific 规则、兼容层、migration、fallback verdict 或新配置。
7. 聚焦测试通过后，仅重跑相关冻结 case，不执行无必要的全量 30 条循环。

