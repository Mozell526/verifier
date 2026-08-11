# Judge 权威分析协议

本文是 `spec/alg/investigate-judge.md` 的增量规范，增强 Judge 调查包中对"判断标准的权威来源"的调查能力。

本文不得修改或复制 Investigate 主流程。发生歧义时，以 `spec/alg/investigate.md` 和 `spec/alg/investigate-judge.md` 为准：仍然只有 InvestigationManifest 一个顶层调查产物 schema，仍然通过现有 `artifacts` 索引调查文件，仍然由 ROLE.md 区分 Role 语义，并沿用既有 Investigate → Solidify → Draft Loop → Promote 流程。

---

# 第一章：Spec 标准——最终长期协议

## 1.1 目标与问题

Judge 评估 Live 输出时，经常面对多个"官方项目材料"对同一判断点给出不同说法的情况。例如：

- `field_enums_args.yaml` 说 polStatus 的合法值是"减额交清"；
- `value_mappings_args.yaml` 把"减额缴清"映射到"减额交情"；
- `prompt.md` 中的示例可能使用另一种写法；
- 标准答案.xlsx 给出历史某个时间点的期望输出。

当这些材料冲突时，Judge 不能简单地按预设优先级表选择一方——因为**所有项目材料都可能是错的**。代码本身就是因为不可靠才需要被评估和改进的。

真正的权威不在项目材料内部的相互引用中，而在项目材料之外：行业标准、下游数据库现实、用户真实意图、端到端业务结果。调查阶段必须追溯每个信息源的因果链，理解它为什么说了它说的话，从而找到真正的权威锚点。

## 1.2 核心原则

### 权威不是标签，是因果分析的结论

不得给信息源贴静态优先级标签（如"Tier 1 > Tier 2"）来替代因果分析。权威来自于理解：

- 这个信息源的内容**从哪里来**（origin）；
- **谁/什么过程**产生和维护它（producer）；
- 系统**怎么加载和使用**它（consumption path）；
- 它**可能以什么方式出错**（failure modes）。

追完因果链后，真正的标准往往自然浮现。

> **举例**：旧模型（authority-registry.json）说 field_enums 和 value_mappings 都是 Tier 1，但 field_enums 优先级更高。这个标签无法解释**为什么** field_enums 更可信。
>
> 做因果链追溯后发现：field_enums 的 origin 是从生产数据库导出的实际存储值，producer 是系统化同步；value_mappings 的 origin 是开发者手写，producer 无自动校验，已知 failure mode 包括同音错别字。"减额交情"正是"减额交清"的同音错别字——不是因为 Tier 低所以错，而是因为人工手写所以容易打错字。
>
> 同理，"O2O"vs"O2O准客"的冲突不是因为优先级，而是因为 value_mappings 开发者只做了大小写归一化、漏掉了"准客"后缀，导致 normalize_field_value() 的归一化链断裂。

### 三种互补的权威确认方式

| 方式 | 适用场景 | 产出 |
|------|---------|------|
| 因果链追溯 | 能理解系统链路和数据流向时 | 从因果分析中自然得出哪个源反映了真实 |
| 事实验证 | 能通过实验/查询获得客观结果时 | 保存可复现的实验结果作为证据 |
| 业务方澄清 | 因果链追不到头、事实无法获取时 | 明确的澄清问题，等待业务方确认 |

三者是递进关系：优先追因果链，用事实验证结论，追不到时交给业务方。

> **举例（因果链追溯）**：追踪 value_mappings 的 origin → 人工手写；failure_mode → 同音错别字；"交情"vs"交清"正是该 failure mode 的实例 → 自然得出 field_enums 的"减额交清"正确。
>
> **举例（事实验证）**：跑 ES aggregation 查询 polStatus 字段的实际值分布，确认"减额交清"存在而"减额交情"不存在 → 用数据库事实验证因果链结论。
>
> **举例（业务方澄清）**：当因果链追不到头时，例如某个字段的枚举值来源不明（不知道 field_enums 最初是从哪个系统导出的），且无法通过 ES aggregation 验证（数据库不可访问），此时必须标 unresolved 并向业务方提出具体澄清问题。

### Schema 驱动调查，而非记录结论

Dataclass 的必填字段设计必须**反向推动**调查者完成因果分析。AI 不能声明"X 是权威"就过关——它必须填出因果链、给出证据、解释为什么。Validator 检查结构完整性和引用有效性，使得跳过分析或含糊其辞无法通过门禁。

> **举例**：AI 不能只写"field_enums 是权威"就过关。它必须填出：
> - `origin`: "从生产数据库导出的实际存储值"
> - `producer`: "开发团队手动维护 YAML，无自动化同步"
> - `consumption_path`: "field_registry.py → normalize_field_value() 先查 enum_vals，命中直接返回"
> - `failure_modes`: ["导出后新增值未同步", "手动维护可能拼写错误"]
>
> 填完这些后，调查者自然会发现：field_enums 的 failure mode 是"遗漏"，value_mappings 的 failure mode 是"写错"——当前冲突（"交情"vs"交清"）命中的是 value_mappings 的 failure mode，不是 field_enums 的。结论自然浮现。

### 防 AI Hack 设计

- 不允许仅凭文本声明建立权威；必须有 evidence_ref 指向可独立验证的材料。
- 不允许只列一个源就下结论；冲突判断点必须列出所有相关源并逐一分析因果。
- 不允许把"系统配置 A 比配置 B 优先级高"作为因果分析；必须解释 A 的内容为什么更可信。
- 标为 resolved 的锚点必须有因果推理和验证方法；标为 unresolved 的必须有明确澄清问题。

> **举例（会被拒绝的 causal_reasoning）**：
> - ❌ "field_enums 是 Tier 1，value_mappings 优先级更低，所以 field_enums 赢。" → 优先级声明，不是因果分析。
> - ❌ "field_enums 是权威。" → 无因果链，无证据。
> - ❌ 只列了 field_enums 一个源就下结论。 → 冲突判断点必须列全所有相关源。
>
> **举例（合格的 causal_reasoning）**：
> - ✅ "field_enums 的 origin 是生产数据库导出（因果链完整），value_mappings 的 origin 是人工手写且无校验（已知 failure mode 为错别字）。本次冲突'交情'vs'交清'正是同音错别字的实例。normalize_field_value() 的代码逻辑也佐证：先查 enum 命中即返回，value_mappings 只是 fallback。"

## 1.3 在现有 Judge 调查合同中的位置

`AuthorityAnalysis` 是 `JudgeInvestigationContract` 的独立顶层对象，与 `BusinessExpectation`、`LiveBoundary`、`EvaluationDimension` 平级，通过 `dimension_ids` 被多个评估维度引用。

```text
JudgeInvestigationContract
  ├── business_expectations[]
  ├── live_boundary
  ├── evaluation_dimensions[]
  │     └── dimension_id ←──────────────────┐
  └── authority_analyses[]                   │
        ├── analysis_id                      │
        ├── dimension_ids ──────────────────→┘
        ├── judgment_point
        ├── source_claims[]
        │     └── causal_chain
        ├── anchor
        └── evidence_ref_ids → InvestigationManifest.evidence_refs
```

一个 AuthorityAnalysis 回答一个判断点的权威问题，可以服务多个维度。一个维度可以依赖多个 AuthorityAnalysis。

## 1.4 Dataclass Schema

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorityAnalysis:
    """对一个关键判断点的权威来源分析。"""

    analysis_id: str

    # 本分析回答的判断问题。
    # 例如："polNoInfo.polStatus 字段的合法枚举值是什么？"
    judgment_point: str

    # 本分析服务的评估维度 ID 列表。
    # 引用 EvaluationDimension.dimension_id。
    dimension_ids: tuple[str, ...]

    # 所有对该判断点给出说法的信息源及其因果链。
    # 冲突时必须列全所有相关源，不得只选一方。
    source_claims: tuple[SourceClaim, ...]

    # 因果分析后得出的权威锚点。
    anchor: AuthorityAnchor

    # 支撑锚点结论的 EvidenceRef ID 列表。
    # 引用 InvestigationManifest.evidence_refs 中的 ref_id。
    # status=resolved 时不得为空。
    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class SourceClaim:
    """一个信息源对判断点的说法及其因果链。"""

    source_id: str

    # 该信息源的身份标识。
    # 例如："field_enums_args.yaml"、"ES 数据库 polStatus 字段"、"保险行业标准术语"。
    source_label: str

    # 该源对判断点的具体说法。
    # 例如："polStatus 合法值包含'减额交清'"。
    claim: str

    # 该源内容的因果链：它为什么这么说？
    causal_chain: CausalChain


@dataclass(frozen=True)
class CausalChain:
    """追溯一个信息源内容的因果来源。"""

    # 内容的原始来源。
    # 例如："从保险公司核心系统数据库 schema 导出"、"开发人员手工编写"。
    origin: str

    # 系统中谁/什么过程产生和维护该源。
    # 例如："配置团队手动维护"、"自动化脚本从核心系统同步"。
    producer: str

    # 系统代码如何加载和使用该源。
    # 例如："validator.py 第 42 行加载，用于校验查询条件枚举值合法性"。
    consumption_path: str

    # 该源可能以什么方式出错。
    # 例如：("手工录入可能打错字", "导出脚本可能未同步最新变更")。
    failure_modes: tuple[str, ...]


@dataclass(frozen=True)
class AuthorityAnchor:
    """因果分析后得出的权威锚点。"""

    # 分析状态。
    # "resolved"：已确定权威锚点。
    # "unresolved"：因果链追不到头，需要业务方澄清。
    status: str

    # 权威锚点的描述：真正的标准是什么。
    # resolved 时必填。
    # 例如："保险行业标准术语'减额交清'是正确值，来源于行业规范。"
    description: str

    # 权威锚点的类型。
    # "industry_standard"：行业/领域标准
    # "database_reality"：下游数据库实际存储
    # "user_intent"：用户真实意图
    # "business_rule"：业务方明确确认的规则
    # "end_to_end_outcome"：端到端业务结果
    # "unresolved"：无法确定
    anchor_type: str

    # 如何验证该锚点。
    # 例如："ES aggregation 查询返回的实际值集合"、"行业标准文档 GB/T XXXX"。
    verification_method: str

    # 为什么该锚点是权威而其他源不是。
    # 必须基于因果链分析，不得仅凭优先级声明。
    # 例如："field_enums 的内容由自动化脚本从核心系统同步，因果链完整；
    #        value_mappings 由人工手写，存在错别字的已知 failure mode，
    #        本次冲突正是该 failure mode 的实例。"
    causal_reasoning: str

    # unresolved 时：需要业务方回答的具体问题。
    # resolved 时为空。
    unresolved_question: str
```

## 1.5 Schema 语义

### 1.5.1 `AuthorityAnalysis`

一个 AuthorityAnalysis 对应一个**关键判断点**——Judge 在评估时必须知道"什么是对的"才能作出判断的具体问题。

判断点不是评估维度本身，而是维度内部的具体事实问题。例如：

- 维度 "intent-completeness" 可能依赖判断点 "用户说的'减额缴清'对应系统的哪个字段和值？"
- 维度 "value-correctness" 可能依赖判断点 "polStatus 字段的合法枚举值集合是什么？"
- 维度 "operator-correctness" 可能依赖判断点 "CONTAINS 和 MATCH 对 polStatus 是否等价？"

同一个判断点可以被多个维度引用。

### 1.5.2 `SourceClaim` 与 `CausalChain`

`SourceClaim` 要求调查者列出**所有**对判断点有说法的信息源，不能只选对自己结论有利的一方。

`CausalChain` 是防 AI Hack 的核心：它要求对每个源回答"你为什么这么说"。四个字段分别追溯：

- `origin`：内容的源头（不是"谁写的文件"，而是"内容最初从哪来"）
- `producer`：产生和维护机制（自动化 vs 人工，决定了出错概率）
- `consumption_path`：系统怎么用它（决定了它的影响范围）
- `failure_modes`：已知或可推断的出错方式（决定了它的可信度）

当两个源冲突时，比较它们的因果链：哪个源的 origin 更接近真实、producer 更可靠、failure_modes 更少命中当前冲突，哪个就更可信。

### 1.5.3 `AuthorityAnchor`

`AuthorityAnchor` 是因果分析的结论，不是预设的优先级。

- `status=resolved` 时：`description`、`anchor_type`、`verification_method`、`causal_reasoning` 全部必填，`evidence_ref_ids` 不得为空。
- `status=unresolved` 时：`unresolved_question` 必填，描述需要业务方回答什么。`evidence_ref_ids` 可以为空（因为还没有确认的答案），但 `source_claims` 仍然必须列出已知的源和因果链。

`causal_reasoning` 必须解释"为什么这个锚点是权威"，而不是"因为它的优先级高"。有效的因果推理形如：

> "field_enums 的内容由自动化脚本每周从核心系统数据库同步（origin 可靠、producer 自动化），
> 而 value_mappings 由开发人员手工维护（producer 人工），其 failure_modes 包含'手工录入错别字'。
> 本次冲突中 value_mappings 的'减额交情'正是该 failure mode 的实例（'情'与'清'形近）。
> 因此 field_enums 的'减额交清'反映了真实，value_mappings 的'减额交情'是配置 bug。"

无效的因果推理：

> "field_enums 是 Tier 1，value_mappings 也是 Tier 1 但优先级更低，所以 field_enums 赢。"

### 1.5.4 与 `EvaluationDimension` 的关系

`EvaluationDimension` 通过 `dimension_id` 被 `AuthorityAnalysis.dimension_ids` 引用。

评估维度的三态端点（`fulfilled_when`、`not_fulfilled_when`、`not_evaluable_when`）可以引用权威分析的结论。例如，维度 `downstream-usability` 的端点条件可以这样写：

```yaml
fulfilled_when:
  - "输出字段值均在 AuthorityAnalysis[enum-value-authority] 认定的合法枚举空间内"
not_evaluable_when:
  - "涉及的判断点尚无 AuthorityAnalysis 覆盖，或对应分析状态为 unresolved"
```

但评估维度不内嵌权威分析——权威分析是独立调查产出，被引用而非被包含。

### 1.5.5 完整 Schema Case（client_search）

以下四个 AuthorityAnalysis 是 client_search 项目级调查合同中的实际条目，展示不同权威判断点的完整分析。

#### Case 1：枚举值合法空间的权威来源（resolved / database_reality）

```json
{
  "analysis_id": "enum-value-authority",
  "judgment_point": "Live 输出的字段值是否合法，以什么为权威标准？当 field_enums、value_mappings、prompt.md、标准答案对同一个值给出不同说法时，Judge 依据什么判断？",
  "dimension_ids": ["downstream-usability", "intent-completeness"],
  "source_claims": [
    {
      "source_id": "field_enums",
      "source_label": "field_enums_args.yaml（全量枚举配置）",
      "claim": "定义每个枚举字段的合法值集合，是系统运行时校验值合法性的依据",
      "causal_chain": {
        "origin": "从下游客户数据库（ES 索引）的字段实际存储值导出，反映数据库中真实存在的值",
        "producer": "开发团队从生产数据库导出并手动维护 YAML；无自动化同步机制",
        "consumption_path": "field_registry.py _load_enum_values() 加载 → normalize_field_value() 第一步检查 value 是否在 enum_vals 中（命中直接返回）→ 同时注入 L4 prompt 的枚举列表供 LLM 参考",
        "failure_modes": [
          "导出后数据库新增值未同步到 YAML",
          "手动维护可能引入拼写错误（但概率远低于 value_mappings）",
          "某些字段的枚举可能不完整"
        ]
      }
    },
    {
      "source_id": "value_mappings",
      "source_label": "value_mappings_args.yaml（全量别名映射配置）",
      "claim": "定义用户口语别名到标准值的映射，用于归一化用户输入和 LLM 输出",
      "causal_chain": {
        "origin": "开发人员手工编写，目的是将用户口语化表达归一化为系统标准值",
        "producer": "人工维护，无自动化校验（没有 CI 检查映射目标是否在 field_enums 中）",
        "consumption_path": "field_registry.py 加载 → 两处使用：(1) normalize_query() 在 LLM 解析前用正则替换 query 文本中的别名；(2) normalize_field_value() 在 LLM 输出后，当值不在 field_enums 中时作为 fallback 映射",
        "failure_modes": [
          "手工录入错别字（同音字：清→情、失→时、力→率）",
          "映射目标缺少后缀（O2O→应为 O2O准客）",
          "identity 映射完全无效（alias=target，未做归一化）",
          "无自动化校验，上述错误不会被发现"
        ]
      }
    },
    {
      "source_id": "standard_answers",
      "source_label": "标准答案.xlsx（历史期望输出快照）",
      "claim": "记录某些 case 在某个历史时间点的期望输出",
      "causal_chain": {
        "origin": "评估团队在某个时间点根据当时系统行为和业务理解编制",
        "producer": "评估人员手动编制",
        "consumption_path": "Judge 调查包 → 作为 reference 与 actual 对比",
        "failure_modes": [
          "编制时的配置版本可能已过时",
          "编制者可能基于旧版 field_enums 或 value_mappings",
          "不反映当前系统的合法值空间"
        ]
      }
    }
  ],
  "anchor": {
    "status": "resolved",
    "description": "field_enums 反映下游数据库实际存储值，是合法值空间的首要权威。value_mappings 是归一化辅助工具，其 target 必须指向 field_enums 中的值才有效（用于 normalize_field_value 的 fallback 路径）；target 与 field_enums 不一致时，冲突本身说明 value_mappings 有 bug。标准答案只反映历史意图，不能覆盖当前合法空间。但 field_enums 可能不完整——当有理由怀疑枚举缺失时，需通过 ES aggregation 验证。",
    "anchor_type": "database_reality",
    "verification_method": "1. 对 20 个已知冲突逐一分类验证：错别字类（5 个，如'减额交情'→'减额交清'）通过语义分析确认；缺后缀类（5 个，如'O2O'→'O2O准客'）通过运行时链路追踪确认归一化链断裂；identity 类（4 个，如 zxjyEquityGrade 的 alias=target）通过代码逻辑确认映射无效；query 文本归一化类（3 个，如 newValueLabel 的'价值a'→'价值A'）确认 target 不是枚举值而是 LLM 输入文本，见 Case 3。2. 可通过 ES aggregation 查询各字段实际值分布验证 field_enums 完整性（待执行）。",
    "causal_reasoning": "field_enums 的因果链更可靠：origin 是生产数据库导出，producer 是系统化同步（虽然手动触发），failure_modes 主要是遗漏而非错误。value_mappings 的因果链：origin 是人工手写，producer 无校验，已知 failure modes 在 20 个冲突中得到实例化。normalize_field_value() 的运行时逻辑也佐证：先查 enum（命中即返回），再查 value_mappings（fallback）——代码设计本身就把 field_enums 当作首要权威。",
    "unresolved_question": ""
  },
  "evidence_ref_ids": [
    "authority-conflicts-scan-20",
    "field-enums-source",
    "value-mappings-source",
    "normalize-field-value-code-analysis"
  ]
}
```

#### Case 2：评估边界的权威来源（resolved / business_rule）

```json
{
  "analysis_id": "evaluation-boundary-authority",
  "judgment_point": "Judge 的评估边界（什么差异算错、什么差异可以忽略）以什么为权威标准？当系统配置声明、用户侧约定、评估团队理解三者不一致时，以谁为准？",
  "dimension_ids": ["downstream-usability", "intent-completeness"],
  "source_claims": [
    {
      "source_id": "judge_boundary_template",
      "source_label": "judge_boundary-template.md（用户侧边界标准源头）",
      "claim": "用户（评估需求方）直接给出的评估边界规则，如'不要纠结 CONTAINS 和 MATCH'",
      "causal_chain": {
        "origin": "用户（评估需求方）根据业务目标和评估成本协商确定",
        "producer": "用户直接编写或口头约定后由评估团队记录",
        "consumption_path": "评估团队编写 → 纳入 Judge 调查包 docs/ → Solidify 时固化为边界 ContextUnit",
        "failure_modes": [
          "约定可能过时（如下游系统升级后行为分化）",
          "口头约定可能未被完整记录"
        ]
      }
    },
    {
      "source_id": "judge_boundary_protocols",
      "source_label": "judge_boundary_protocals.md（AI 落地的边界协议）",
      "claim": "评估团队将用户约定落地为可执行的边界协议文档",
      "causal_chain": {
        "origin": "基于 judge_boundary_template 的用户约定，由 AI/评估团队落地",
        "producer": "评估团队或 AI 解读用户约定后编写",
        "consumption_path": "Judge 调查包 → judge prompt 的边界规则",
        "failure_modes": [
          "落地时可能误解用户意图",
          "可能添加了用户未明确约定的规则",
          "与 template 不一致时应以 template 为准"
        ]
      }
    },
    {
      "source_id": "field_definitions",
      "source_label": "field_definitions_args.yaml（系统字段能力声明）",
      "claim": "声明每个字段支持的操作符列表，如 polStatus 只声明 CONTAINS 和 NOT_CONTAINS",
      "causal_chain": {
        "origin": "开发团队根据 ES 查询能力配置",
        "producer": "开发团队手动配置",
        "consumption_path": "field_registry.py 加载 → 注入 L4 prompt 的操作符列表 → LLM 据此选择操作符",
        "failure_modes": [
          "声明可能不完整（ES 实际支持但未声明）",
          "声明的是'系统配置了什么'而非'什么差异对业务有影响'"
        ]
      }
    }
  ],
  "anchor": {
    "status": "resolved",
    "description": "用户侧明确约定是评估边界的最终权威。judge_boundary_template 的因果链最短最可靠——直接来自评估需求方。当用户明确说'不要纠结 CONTAINS 和 MATCH'时，这就是 Judge 的边界标准。judge_boundary_protocols 与 template 冲突时以 template 为准。field_definitions 的操作符声明定义系统能力，但不定义评估边界。",
    "anchor_type": "business_rule",
    "verification_method": "1. judge_boundary_template 中明确列出用户约定的等价规则和忽略规则；2. project.yaml 的 semantic_equivalence_rules 将部分约定固化为可执行规则；3. 对比 template 和 protocols 确认落地未偏离用户意图。",
    "causal_reasoning": "评估边界回答的是'什么差异对业务有影响'，是业务判断而非技术判断。judge_boundary_template 的 origin 是用户（评估需求方），因果链最短且不存在'技术实现错误'的 failure mode。field_definitions 回答的是'系统配置了什么'，是技术事实而非业务判断。两者不在同一问题上竞争——但如果冲突，评估边界以用户约定为准。",
    "unresolved_question": ""
  },
  "evidence_ref_ids": [
    "judge-boundary-template",
    "judge-boundary-protocols",
    "project-yaml-semantic-rules"
  ]
}
```

#### Case 3：口语表达的语义映射权威（resolved / system_semantic_definition）

```json
{
  "analysis_id": "semantic-mapping-authority",
  "judgment_point": "当用户口语表达（如'价值A'、'A类客户'）需要映射到枚举值时，映射关系的权威定义在哪里？value_mappings 的 target 不在 field_enums 中时，是 value_mappings 错了还是有其他解释？",
  "dimension_ids": ["intent-completeness", "downstream-usability"],
  "source_claims": [
    {
      "source_id": "field_definitions",
      "source_label": "field_definitions_args.yaml → newValueLabel (customer_value_group)",
      "claim": "notes 明确定义'A类=A1/A2/A3/A4，B类=B，AB类=A1/A2/A3/A4/B'；examples 给出精确输出格式：'A类客户' → { operator: CONTAINS, value: ['A1','A2','A3','A4'] }；retrieval_text 包含'价值a或b'",
      "causal_chain": {
        "origin": "产品/开发定义的字段语义说明和示例，是 LLM 理解字段含义的直接依据",
        "producer": "开发团队编写，经业务确认后纳入配置",
        "consumption_path": "field_registry.py → ES 索引 retrieval_text 用于字段检索 → notes/examples/description 注入 L4 prompt → LLM 据此生成查询条件",
        "failure_modes": [
          "notes/examples 可能与 field_enums 不同步（但本例中一致）",
          "LLM 可能不遵守 examples 的格式（概率性问题）"
        ]
      }
    },
    {
      "source_id": "value_mappings",
      "source_label": "value_mappings_args.yaml → newValueLabel",
      "claim": "'价值a'→'价值A'，'价值b'→'价值B'，'价值a或b'→'价值A或B'。target 均不在 field_enums 中",
      "causal_chain": {
        "origin": "开发者手动编写。注意：这些映射用于 normalize_query()（LLM 解析前的 query 文本替换），不是用于 normalize_field_value()（LLM 输出后的值映射）",
        "producer": "开发者手写。注释中还有被注释掉的 'A1类→A1' 等条目，说明开发者考虑过更细粒度的映射但最终选择让 LLM 通过 field_definitions 处理",
        "consumption_path": "normalize_query() 把 query 中'价值a'替换为'价值A' → LLM 看到'价值A' → ES 检索匹配 customer_value_group intent → LLM 看到 notes 'A类=A1/A2/A3/A4' 和 examples → 输出 CONTAINS ['A1','A2','A3','A4']（数组）→ normalize_field_value() 收到数组直接跳过",
        "failure_modes": [
          "target '价值A'不是枚举值——但这是设计意图，不是 bug：它是 query 文本归一化的中间形态，不是最终输出值",
          "如果 LLM 不遵守 examples 而输出 value:'价值A'（字符串），normalize_field_value 无法修正"
        ]
      }
    },
    {
      "source_id": "field_enums",
      "source_label": "field_enums_args.yaml → newValueLabel",
      "claim": "合法枚举为 [F,E,D,C,B,A4,A3,A2,A1]，ordered=true",
      "causal_chain": {
        "origin": "从下游客户数据库导出，是精确的离散等级值",
        "producer": "开发团队从生产数据库导出",
        "consumption_path": "field_registry.py → normalize_field_value() → LLM prompt 枚举列表",
        "failure_modes": [
          "枚举值本身无歧义，但不包含'价值A'这样的集合概念——集合语义由 field_definitions 的 notes/examples 定义"
        ]
      }
    }
  ],
  "anchor": {
    "status": "resolved",
    "description": "口语表达到枚举值的语义映射权威定义在 field_definitions 的 notes 和 examples 中。'价值A'='A类'=CONTAINS ['A1','A2','A3','A4']，'价值B'='B类'=CONTAINS ['B']，'价值A或B'='AB类'=CONTAINS ['A1','A2','A3','A4','B']。value_mappings 的'价值a'→'价值A'是 query 文本归一化（normalize_query 阶段），不是值映射（normalize_field_value 阶段）；target 不在枚举中是设计意图，不是 bug。扫描报的'value_mapping_target_not_in_enums'对此类映射是误报。",
    "anchor_type": "database_reality",
    "verification_method": "1. field_definitions notes 明确写出'A类=A1/A2/A3/A4'；2. field_definitions examples 给出精确输出：'A类客户'→CONTAINS ['A1','A2','A3','A4']；3. retrieval_text 包含'价值a或b'，ES 检索能匹配；4. normalize_query 代码确认'价值a'→'价值A'是文本替换；5. normalize_field_value 代码确认数组输入直接跳过。",
    "causal_reasoning": "field_definitions 的 notes 和 examples 是 LLM 理解字段语义的直接依据，因果链最短：开发团队编写 → 注入 LLM prompt → LLM 据此生成输出。value_mappings 的'价值a'→'价值A'只是 query 文本归一化的中间步骤，不是最终值映射。field_enums 定义精确枚举值，集合语义（'A类'='A1/A2/A3/A4'）由 field_definitions 定义。三者不冲突：field_enums 定义原子值，field_definitions 定义组合语义，value_mappings 做文本预处理。",
    "unresolved_question": ""
  },
  "evidence_ref_ids": [
    "field-defs-newValueLabel-notes-examples",
    "value-mappings-newValueLabel",
    "field-enums-newValueLabel",
    "normalize-query-code-analysis"
  ]
}
```

#### Case 4：查询形式等价性的裁决（resolved / business_rule）

```json
{
  "analysis_id": "query-form-equivalence-authority",
  "judgment_point": "Live 输出的查询条件在字段/操作符/值的形式上与 reference 不同，但可能语义等价时，Judge 依据什么判断是否等价？形式差异在什么条件下可以忽略？",
  "dimension_ids": ["downstream-usability", "intent-completeness"],
  "source_claims": [
    {
      "source_id": "reference_answers",
      "source_label": "标准答案 / reference 输出",
      "claim": "给出某个 case 的期望输出形式（特定字段、操作符、值的组合）",
      "causal_chain": {
        "origin": "评估团队在某个时间点编制的期望输出",
        "producer": "评估人员根据当时理解编制",
        "consumption_path": "Judge 调查包 → 作为 reference 与 actual 逐字段对比",
        "failure_modes": [
          "reference 的形式可能不是唯一正确形式",
          "reference 可能基于旧版配置",
          "形式不同不等于语义不同"
        ]
      }
    },
    {
      "source_id": "judge_boundary_equivalence_rules",
      "source_label": "judge_boundary_template + project.yaml semantic_equivalence_rules",
      "claim": "用户侧明确约定的等价规则（如 CONTAINS≈MATCH、字段别名等价）",
      "causal_chain": {
        "origin": "用户（评估需求方）根据业务目标约定的等价规则",
        "producer": "用户协商 + 评估团队固化到 project.yaml",
        "consumption_path": "用户协商 → 评估团队固化到 project.yaml → Solidify 时加载为等价规则配置",
        "failure_modes": [
          "等价规则可能不完整（未覆盖所有合理的等价情况）",
          "等价规则可能过时（下游系统升级后行为分化）"
        ]
      }
    },
    {
      "source_id": "downstream_query_semantics",
      "source_label": "下游 ES 查询引擎的实际查询语义",
      "claim": "不同形式的查询条件可能在下游产出相同的结果集",
      "causal_chain": {
        "origin": "ES 引擎的查询语义（keyword 字段的 term 查询、CONTAINS/MATCH 行为等）",
        "producer": "ES 引擎实现",
        "consumption_path": "下游搜索服务将 conditions 转换为 ES DSL 执行 → 返回结果集",
        "failure_modes": [
          "对 text 类型字段，CONTAINS 和 MATCH 行为可能不同",
          "自定义 analyzer 可能影响结果",
          "调查阶段可能无法直接执行下游查询验证（需要下游服务可用）"
        ]
      }
    }
  ],
  "anchor": {
    "status": "resolved",
    "description": "等价性判断分两个层面：(1) 用户侧明确约定的等价规则（如 CONTAINS≈MATCH）直接生效；(2) 未被约定覆盖的等价性争议，原则上需要下游查询结果集验证，但在 Judge 无法执行下游查询时，应保守处理——已知等价规则覆盖的差异视为等价，超出已知规则的形式差异不能自动视为等价。reference 的形式只是'一种正确形式'，不是'唯一正确形式'。",
    "anchor_type": "business_rule",
    "verification_method": "1. judge_boundary_template 和 project.yaml semantic_equivalence_rules 中明确列出的等价规则；2. 对已知等价规则可通过对比 ES 查询结果验证（待执行）；3. 对未覆盖的等价性争议，标记为需要下游验证或业务方确认。",
    "causal_reasoning": "等价性判断的权威来自两个层面。第一层：用户侧约定（judge_boundary_template）的因果链最短——直接来自评估需求方。第二层：下游查询语义是客观事实，但 Judge 通常无法在运行时执行下游查询。因此实操中：已知等价规则覆盖的差异→视为等价；未知差异→保守处理。",
    "unresolved_question": ""
  },
  "evidence_ref_ids": [
    "judge-boundary-template",
    "project-yaml-semantic-rules",
    "es-query-semantics-analysis"
  ]
}
```

## 1.6 调查过程要求

### 1.6.1 识别判断点

调查者必须从 `EvaluationDimension` 的 `evaluation_question` 和三态端点中，识别出所有需要权威标准才能判断的项目级判断点。

不是所有判断都需要 AuthorityAnalysis。只有存在多个信息源可能给出不同说法的判断点才需要。如果某个判断点的权威来源显而易见且无争议（例如"用户说了什么"直接来自 trace input），不需要单独建立 AuthorityAnalysis。

> **举例（client_search 的判断点识别）**：
> 从 `downstream-usability` 维度的 evaluation_question "actual 是否满足当前客户搜索字段、操作符和值协议并可交给下游执行？" 中，可以识别出：
> - 判断点 1：枚举值合法空间的权威来源 → 需要 AuthorityAnalysis（field_enums vs value_mappings vs 标准答案有冲突）
> - 判断点 2：查询形式等价性的裁决 → 需要 AuthorityAnalysis（reference 形式 vs actual 形式可能不同）
> - "字段是否在 field_definitions 中注册" → 不需要 AuthorityAnalysis（只有一个源，无冲突）

### 1.6.2 追溯因果链

对每个判断点的每个相关源类别，调查者必须：

1. 找到源文件/源数据的实际位置；
2. 追溯内容的原始来源（不是"文件在哪"，而是"内容从哪来"）；
3. 确认产生和维护机制（读代码、读文档、读 git history）；
4. 确认系统如何加载和使用（读代码中的 import/load 路径）；
5. 推断可能的出错方式。

调查者可以使用任何手段：读源码、调用 API、查询数据库、分析 git log、阅读业务文档。本协议不约束调查手段，只约束产出格式。

> **举例（追溯 value_mappings 的因果链）**：
> 1. 位置：`config/value_mappings_args.yaml`
> 2. origin：读文件内容发现是人工编写的别名→标准值映射表
> 3. producer：读 git log 发现由开发者手动提交，无 CI 校验
> 4. consumption_path：读 `field_registry.py` 发现两处使用——`normalize_query()` 在 LLM 前替换 query 文本，`normalize_field_value()` 在 LLM 输出后作为 fallback
> 5. failure_modes：对比 field_enums 发现 20 个 target 不在枚举中，按模式分为错别字、缺后缀、语义概念、identity 四类

### 1.6.3 事实验证

当因果链分析得出初步结论后，应尽可能用事实验证：

- 如果锚点是"ES 数据库实际存储的值"→ 跑一次 aggregation query，保存原始结果作为 evidence artifact；
- 如果锚点是"两个操作符等价"→ 跑对比查询，保存结果；
- 如果锚点是"行业术语"→ 引用具体文档或标准编号。

事实验证的原始结果必须作为 `evidence_refs` 登记到 InvestigationManifest，不得只在 AuthorityAnalysis 文本中描述。

> **举例**：因果链分析得出"field_enums 反映数据库实际值"→ 跑 ES aggregation：
> ```
> GET /customer_index/_search
> { "aggs": { "polStatus_values": { "terms": { "field": "polNoInfo.polStatus", "size": 50 } } } }
> ```
> 保存原始返回结果到 `docs/evidence/es-polstatus-aggregation.json`，登记为 evidence_ref。

### 1.6.4 标记 unresolved

当因果链追不到头，且无法通过事实验证确认时，必须标为 unresolved 并提出明确的澄清问题。

不得在证据不足时强行给出 resolved 结论。

> **举例**：某字段的 field_enums 来源不明（不知道从哪个系统导出），数据库不可访问无法跑 aggregation，value_mappings 的 target 也不在枚举中。因果链追不到头，事实验证做不了。标 unresolved，提问："请确认该字段的枚举值列表是否完整？"
>
> 注意：不是所有"target 不在枚举中"都是 unresolved。newValueLabel 的"价值a"→"价值A"看起来 target 不在枚举中，但 field_definitions 的 notes 明确写了"A类=A1/A2/A3/A4"，examples 给出了精确输出 `CONTAINS ["A1","A2","A3","A4"]`。这个 case 的权威来源是 field_definitions 的语义定义，是 resolved 的。扫描报的 "value_mapping_target_not_in_enums" 是误报——该 mapping 是 query 文本归一化，不是值映射。

## 1.7 Solidify 接口

调查包为 Solidify 提供以下可消费内容：

1. **resolved 锚点 + verification_method** → Solidify 可据此构建 VerifiableTool 或 ContextUnit；
2. **resolved 锚点 + evidence_ref_ids** → Solidify 可从 evidence artifact 取得原始材料固化；
3. **unresolved 锚点 + unresolved_question** → Solidify 知道该判断点尚无权威结论，对应的维度能力需要保守处理。

> **举例（client_search）**：
>
> 1. `enum-value-authority` 锚点 resolved，verification_method 包含"查 field_enums"→ Solidify 可构建一个枚举校验 Tool。
>
> 2. `evaluation-boundary-authority` 锚点 resolved，evidence_ref_ids 指向 judge_boundary_template 原文 → Solidify 可将原文固化为 ContextUnit。
>
> 3. 若某锚点 unresolved → Solidify 知道该判断点无权威结论，不应基于猜测构建判断能力。

Solidify 不得：
- 把 AuthorityAnalysis 的完整 JSON 直接注入 prompt；
- 用 AI 生成的摘要替代 evidence artifact 的原始内容；
- 忽略 unresolved 状态，把未确认的锚点当作已确认使用。

## 1.8 Validator 门禁

对 `role=judge` 的调查包，validator 在现有 investigate-judge.md 门禁基础上增加：

- 每个 `AuthorityAnalysis` 的 `dimension_ids` 必须引用有效的 `EvaluationDimension.dimension_id`；
- 每个 `SourceClaim` 的 `causal_chain` 四个字段均不得为空；
- `source_claims` 至少包含 2 个源（单源无冲突不需要 AuthorityAnalysis）；
- `anchor.status` 为 "resolved" 时：`description`、`anchor_type`、`verification_method`、`causal_reasoning` 不得为空，`evidence_ref_ids` 不得为空；
- `anchor.status` 为 "unresolved" 时：`unresolved_question` 不得为空；
- `evidence_ref_ids` 必须引用 InvestigationManifest.evidence_refs 中有效的 ref_id；
- `anchor_type` 必须在允许的枚举值内；
- `causal_reasoning` 不得仅包含优先级声明（validator 可做基本语义检查，但不做脆弱的关键词匹配）。

## 1.9 与现有公共协议的关系

- 本结构是 Judge 调查合同的组成部分，不替代 `InvestigationManifest`；
- Evidence、artifact、ToolRequirement 和 unresolved 继续使用现有公共字段；
- 不增加 JudgeResult、FulfillmentAssessment 或 Draft Loop 顶层 schema；
- 不修改 Judge runtime 的三态聚合协议；
- 完整 AuthorityAnalysis JSON 不直接注入运行时 Prompt；
- Mock 和 Attribute 不加载该结构；
- 跨 Role 共享仍需通过现有 `role_assets` 和正式 Context/Tool 权限完成。

---

# 第二章：Changes——现状差异与一次性改造

## 2.1 当前状态与目标差异

1. 当前 Judge 调查合同（`JudgeInvestigationContract`）只有 `business_expectations`、`live_boundary`、`evaluation_dimensions` 三个顶层对象，没有权威分析能力；
2. 当前存在一份 `authority-registry.json`（位于 client_search 调查包），采用静态 5 层优先级模型（Tier 0-4），给信息源贴标签排座次，不做因果分析；
3. 该静态模型把系统内部配置（field_enums、value_mappings）当作权威源，但系统本身就是被评估对象，其配置可能有 bug；
4. 调查包中没有结构化的权威分析产物，Solidify 无法从中取得可验证的权威结论；
5. `capability_manifest` 只读 field_definitions，不解析 enum_ref，导致 31 个枚举字段的合法值在 Judge context 中为空；
6. 当前 `value_mappings_args.yaml` 与 `field_enums_args.yaml` 存在 20 个已知冲突（映射目标不在合法枚举中），但没有因果分析说明为什么冲突、哪个反映了真实；
7. 调查阶段没有强制步骤要求追溯信息源的因果链；
8. Validator 不验证权威分析的结构完整性。

## 2.2 一次性改造任务

### Task 1：增加 schema 与 JSON 边界

- 新增 `AuthorityAnalysis`、`SourceClaim`、`CausalChain`、`AuthorityAnchor` dataclass；
- 提供严格的 JSON serialize/deserialize；
- 将 `authority_analyses` 加入 `JudgeInvestigationContract` 顶层；
- 保持现有 `BusinessExpectation`、`LiveBoundary`、`EvaluationDimension` 不变；
- 保持现有 `InvestigationManifest` 公共字段不变。

### Task 2：更新 Judge ROLE 与模板

- 在 Judge ROLE 中增加"权威分析"调查步骤，位于 evaluation_dimensions 之后；
- 说明调查顺序：识别判断点 → 列出所有源 → 追溯因果链 → 事实验证 → 确定锚点或标记 unresolved；
- 提供最小完整示例（以 client_search polStatus 冲突为例）；
- 提供反例：仅凭优先级声明、只列一个源、无证据的 resolved；
- 更新 `MAP.md` 指向模板与门禁。

### Task 3：扩展调查 validator

- 对 `role=judge` 执行本 spec 1.8 节的结构门禁；
- 校验 AuthorityAnalysis 的 ID 引用、因果链完整性、锚点状态一致性；
- 保持其他 Role 的公共调查包行为不变；
- 不使用脆弱的关键词匹配替代语义审查。

### Task 4：迁移 client_search 权威分析

- 废弃现有 `authority-registry.json` 的静态 5 层优先级模型；
- 建立项目级 AuthorityAnalysis，覆盖以下判断点：
  - 枚举值合法空间的权威来源（field_enums vs value_mappings vs 标准答案）；
  - 评估边界的权威来源（用户侧约定 vs 系统配置声明）；
  - 口语表达的语义映射权威（field_definitions notes/examples 如何定义集合语义）；
  - 查询形式等价性的裁决（形式不同但语义等价时的判断标准）；
- 每个 AuthorityAnalysis 追溯相关源类别的因果链（origin/producer/consumption_path/failure_modes）；
- 将 20 个已知 value_mappings vs field_enums 冲突按失败模式分类（错别字、缺后缀、语义概念、identity 映射），作为项目级结论的证据；
- 对无法从因果链推断的判断点标记 unresolved 并提出澄清问题；
- 将验证实验的原始结果登记为 evidence_refs；
- 更新 `judge-investigation-contract.json` 加入 `authority_analyses`。

### Task 5：修复 capability_manifest 枚举缺失

- `build_capability_manifest` 增加 `enums_path` 参数，解析 `enum_ref` 从 field_enums 获取实际枚举值；
- `live.py` 的 `capability_manifest()` 传入 field_enums 路径；
- 验证 31 个枚举字段的合法值在 Judge context 中可见；
- 此修复使枚举值在调查包中完整可见，但枚举值本身不是权威——权威来自 AuthorityAnalysis 的因果分析结论。

### Task 6：更新 Solidify 消费

- 要求 Solidify 记录"AuthorityAnalysis → 固化资产 → runtime observable"的映射；
- resolved 且有动态验证方式的锚点 → 构建 VerifiableTool；
- resolved 且稳定的锚点 → 固化为 ContextUnit（内容来自 evidence artifact）；
- unresolved 的锚点 → 映射到评估维度的 not_evaluable_when 条件；
- 在 Judge Solidify smoke 中验证：有锚点的维度能正确判断，无锚点的维度正确标记 not_evaluable。

### Task 7：更新 Draft Loop Review

- 检查 Judge 是否正确引用 AuthorityAnalysis 的锚点作为判断依据；
- 检查 unresolved 的锚点在调查包中有明确的 unresolved_question；
- 检查 Judge 是否在没有 AuthorityAnalysis 覆盖的判断点上自行推断权威（应标记为证据不足）；
- 保持 Current/Draft 冻结、unseen 隔离和 Promotion 授权规则不变。

### Task 8：测试与文档同步

- 增加 dataclass round-trip、结构失败、非法引用测试；
- 增加单源 AuthorityAnalysis 拒绝测试（至少 2 源）；
- 增加 resolved 无 evidence 拒绝测试；
- 增加 unresolved 无 question 拒绝测试；
- 增加 causal_chain 字段为空拒绝测试；
- 增加"仅凭优先级声明"的 causal_reasoning 语义检查测试；
- 增加 client_search 代表测试：
  - 一个 resolved 锚点（polStatus 错别字，因果链完整）；
  - 一个需要事实验证的锚点（操作符等价性）；
  - 一个 unresolved 锚点（无法确认的业务规则）；
- 同步 `spec/alg/investigate-judge.md`、Draft Skill、Judge ROLE、MAP 和参考模板。

## 2.3 一次性改造验收

- `JudgeInvestigationContract` 包含 `authority_analyses` 顶层对象；
- 每个 AuthorityAnalysis 都有完整的因果链分析，不是优先级标签；
- client_search 的项目级权威判断点（枚举合法空间、评估边界、口语语义映射、查询等价性）都有对应的 AuthorityAnalysis，20 个已知冲突作为证据支撑项目级结论；
- resolved 锚点都有 evidence_ref 支撑，可独立验证；
- unresolved 锚点都有明确的澄清问题；
- Validator 能阻止结构不完整、引用无效和单源结论；
- Solidify 能从调查包中正确解析和消费锚点；
- 调查包中不再包含静态优先级表，权威结论基于因果分析；
- 现有 `authority-registry.json` 的静态模型被废弃或降级为历史参考；
- 现有 Judge runtime public schema 未被复制或污染；
- Current/Draft 比较证明判断准确性改善且无可见退化后，才提出 Promotion 建议。
