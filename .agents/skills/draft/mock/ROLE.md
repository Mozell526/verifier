---
name: draft-mock
description: Mock Draft 的业务价值、评估维度和需求空间调查、固化与逐轮审查契约。
---

# Draft · Mock

## Investigation objective
生成合法、有业务意义、能检验目标评估维度且不过拟合当前样本的具体用户输入。

## Material boundary
允许输入协议、业务实体与字段约束、用户可见产品能力、合法业务样例和可执行性结果。禁止 promotion-only unseen case、样本答案、Judge 结论、Attribute 根因和 case 专属修复信息。

## Evidence / Tool requirements
EvidenceRef 指向业务价值、输入协议、实体规则、字段约束、真实合法样例或执行结果，并带 revision/hash。需要稳定生成或验证时登记 generator、schema/constraint validator 或最小业务可执行性检查；生成样本本身不能反过来充当规则来源。

## Mandatory artifact
必须生成并在 Manifest 登记 `docs/mock-investigation-contract.json`，其 schema 为 `MockInvestigationContract`，完整定义 `BusinessValue[]`、`EvaluationScope.dimensions[]` 和 `MockDemandSpace[]`。该 JSON 是唯一真相源，不维护冲突的 Markdown/JSON 双合同。禁止 Case ID、unseen answer、固定对象/数值组合、把 Judge 标准直接写进用户问题，或把单个用户事实提升为所有用户默认事实。

## Solidify usage
候选生成路径按 `MockDemandSpace → BusinessValue/EvaluationDimension → coverage requirement → variation → validity constraints` 消费调查资产。稳定合同注册为 Mock 可见 mandatory ContextUnit；若项目没有配置 Investigation/Context asset，则等价于 `ContextUnit=[]`。配置了 Investigation asset时必须生成 Solidify receipt，证明合同 source IDs 已映射到候选资产并在成功 runtime observable 中被消费。

## Draft Loop review
每轮必须生成标准 Role review receipt，逐项检查：需求空间覆盖、维度可评估性、具体事实内部一致、variation、无 case/Judge hardcode、候选真实消费调查资产、相对 Current 的有把握净胜。`improved` 只看 `relative_improvement_no_regression` 净胜 > 0；人判不完的案不计分、不改候选。Draft Loop evidence 必须同时引用 Role review receipt 和最新 run report。
