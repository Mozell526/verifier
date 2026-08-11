# Schema Show 通用协议

## 1. 目的

Dataclass Schema 之间通常使用稳定 ID 串联。ID 适合代码关联和确定性校验，
但不能单独承担人工阅读：

```python
AuthorityFinding(
    dimension_ids=("downstream-query-consumability",),
)
```

只看到上述内容的人无法知道该维度实际评价什么，也无法继续理解它关联的业务
期望。

Schema Show 的目标是提供一套通用、确定性的人类可读投影：

> Schema 的原始字段和值保持原样；展示器根据显式 Schema 引用关系找到目标
> 对象，并且只在明确的引用展示边界内展示目标 Schema 预先声明的关键字段。

该协议不是 Authority 专属协议，也不限定数据必须来自 Investigate。任何使用
Dataclass Schema 和稳定 ID 串联的业务都可以使用同一机制。

## 2. 非目标

Schema Show 不负责：

- 新增、修改或推断业务结论；
- 让 LLM 根据相似名称猜测 ID 指向；
- 自动推导未在 Schema 中表达的业务链；
- 展开全部关联对象或输出完整对象转储；
- 代替 Schema 引用完整性校验；
- 新增 `InvestigationPackage`、展示专用业务 Schema 或字段副本。

展示结果只能来自当前 Schema、被显式引用的 Schema 及其实际字段值。

## 3. 核心概念

### 3.1 Schema 引用关系

单独的字符串 ID 不包含目标类型。每个跨 Schema ID 字段必须显式声明：

```text
来源 Schema.引用字段
    → 目标 Schema.ID 字段
```

引用关系是数据协议，不是展示器私有配置。Validator、Solidify 投影和
Schema Presenter 必须共用同一份关系定义。

概念形状：

```python
SCHEMA_REFERENCES = {
    (SourceSchema, "reference_field"):
        (TargetSchema, "target_id_field"),
}
```

例如：

```python
SCHEMA_REFERENCES = {
    (AuthorityFinding, "dimension_ids"):
        (EvaluationDimension, "dimension_id"),

    (EvaluationDimension, "expectation_ids"):
        (BusinessExpectation, "expectation_id"),

    (AuthorityFinding, "basis_source_ref_ids"):
        (MaterialInvestigation, "source_ref_id"),

    (SolidifiedAuthorityAnchor, "finding_id"):
        (AuthorityFinding, "finding_id"),
}
```

目标对象的查找键不是裸 ID，而是：

```text
(目标 Schema 类型, 目标 ID 字段, ID 实际值)
```

因此，不同 Schema 出现相同字符串 ID 时不会互相串联。

### 3.2 Schema 展示字段

每种需要展示的 Schema 必须声明最小展示字段：

```python
SCHEMA_DISPLAY_FIELDS = {
    SchemaType: (
        "field_a",
        "field_b",
    ),
}
```

展示字段只控制“展示多少”，不能改变 Schema 引用关系。

示例：

```python
SCHEMA_DISPLAY_FIELDS = {
    BusinessExpectation: (
        "user_role",
        "use_scenario",
        "desired_outcome",
    ),
    EvaluationDimension: (
        "name",
        "evaluation_question",
        "expectation_ids",
    ),
    MaterialInvestigation: (
        "source_location",
    ),
    AuthorityFinding: (
        "finding_id",
        "finding_kind",
        "business_question",
        "dimension_ids",
        "basis_source_ref_ids",
        "status",
        "result",
        "resolution_reason",
        "unresolved_reason",
        "required_evidence",
    ),
}
```

这份配置不得为了某个 Case 临时变化。只有 Schema 的长期人工审阅需求变化
时，才修改其展示字段。

### 3.3 原始值与引用展开边界

Schema Show 必须先按来源 Schema 的真实字段形状展示原始值，再在该值下使用
固定标记展开目标 Schema：

```text
来源字段:
  - 原始 ID
    ↳ [reference → 目标Schema.目标ID字段]
      目标 Schema 的展示字段
```

例如，真实字段是：

```python
AuthorityFinding(
    dimension_ids=("downstream-query-consumability",),
)
```

必须展示为：

```text
dimension_ids:
  - downstream-query-consumability
    ↳ [reference → EvaluationDimension.dimension_id]
      name:
        下游查询可消费性
      evaluation_question:
        Live 是否以真实下游支持的形式交付查询？
```

其中：

- `downstream-query-consumability` 是
  `AuthorityFinding.dimension_ids` 中真实保存的值；
- `↳ [reference → EvaluationDimension.dimension_id]` 是纯展示标记；
- `name` 和 `evaluation_question` 属于目标
  `EvaluationDimension`，不属于 `AuthorityFinding`；
- 展示标记和展开内容都不得写回、序列化进或伪装成来源 Schema 字段。

禁止把目标对象字段直接合并进来源字段：

```text
# 禁止：无法分辨哪些值来自原 Schema。
dimension_ids:
  - 下游查询可消费性
    id: downstream-query-consumability
    evaluation_question: ...
```

### 3.4 相关 Schema

一次展示需要两类动态数据：

- 当前要展示的 Schema 对象；
- 当前对象可能引用的相关 Schema 对象。

相关 Schema 只是本次查找范围，不是新的 Package Schema：

```python
presenter.show(
    finding,
    related_schemas=(contract, report, manifest),
)
```

`contract`、`report` 和 `manifest` 保持各自原有业务含义。Presenter 只遍历其中
已有的 Dataclass 对象并按目标类型和 ID 建立内部查找表。内部查找表不持久化、
不进入报告，也不是长期协议字段。

## 4. 通用接口

引用关系和展示字段在 Presenter 初始化时绑定一次，不要求业务调用方每次
重复传入：

```python
presenter = SchemaPresenter(
    references=SCHEMA_REFERENCES,
    display_fields=SCHEMA_DISPLAY_FIELDS,
)
```

通用展示接口：

```python
text = presenter.show(
    value,
    related_schemas=(...),
)
```

参数语义：

```text
value
    当前要展示的 Schema 对象

related_schemas
    本次可以解析引用的其他 Schema 对象或包含这些对象的 Dataclass 根对象
```

接口中不出现 `investigation_package`，也不提供 AuthorityFinding 专属
`show_authority_finding()`。

## 5. 确定性数据流

```text
当前 Schema 对象
    ↓ 读取 SCHEMA_DISPLAY_FIELDS
按声明顺序展示字段
    ↓
普通字段
    → 直接展示实际值

已登记的 ID 引用字段
    ↓ 查询 SCHEMA_REFERENCES
得到目标 Schema 类型和目标 ID 字段
    ↓ 在 related_schemas 中确定性查找
得到目标 Schema 对象
    ↓ 读取目标 Schema 的 SCHEMA_DISPLAY_FIELDS
先原样展示来源 ID
    ↓
输出 ↳ [reference → 目标Schema.目标ID字段]
    ↓
在该展示边界内展示目标对象的关键实际值
    ↓
目标展示字段仍是已登记引用时，继续使用相同规则
```

Presenter 不调用 LLM，也不根据字段名、自然语言或 ID 格式推断关系。
Presenter 不得用目标对象的名称替换来源 Schema 中真实保存的 ID。

### 5.1 递归边界

为避免展示无限扩张：

- 只遍历 `SCHEMA_DISPLAY_FIELDS` 中明确列出的字段；
- 只跟随 `SCHEMA_REFERENCES` 中明确登记的引用；
- 每次引用展开都必须保留来源字段中的原始 ID；
- 每次引用展开都必须带有
  `↳ [reference → 目标Schema.目标ID字段]` 边界；
- 同一目标对象在当前展示路径中第二次出现时，只显示其 ID，不再次展开；
- 不展示未被当前对象引用的其他 Schema；
- 不因为资料“相关”而自动追加资料、结论或解释。

## 6. 通用错误语义

### 6.1 引用关系未声明

字段没有登记在 `SCHEMA_REFERENCES` 时，Presenter 将其作为普通字段展示，
不得猜测目标 Schema。

### 6.2 引用目标不存在

已声明的 ID 引用找不到目标对象时：

- Validator 必须判定引用完整性失败；
- Presenter 必须显示明确的 unresolved reference；
- Presenter 不得隐藏、补写或选择相似 ID。

示例：

```text
dimension_ids:
  - downstream-query-consumability
    ↳ [unresolved reference → EvaluationDimension.dimension_id]
```

### 6.3 引用目标不唯一

同一目标 Schema 的同一 ID 出现多个对象时，Validator 必须判定唯一性失败，
Presenter 不得自行选择其中一个。

### 6.4 缺少展示字段定义

被要求展开的目标 Schema 没有登记 `SCHEMA_DISPLAY_FIELDS` 时，Presenter
必须报告展示协议缺失，不得退化为完整对象转储。

## 7. Client Search 示例

以下对象均为既有业务 Schema 的简化实例。

```python
BusinessExpectation(
    expectation_id="find-target-customers",
    user_role="需要寻找目标客户的业务人员",
    use_scenario="用户通过自然语言描述目标客户群体并使用客户搜索产品",
    desired_outcome="获得符合其已表达筛选要求的客户集合",
)

EvaluationDimension(
    dimension_id="downstream-query-consumability",
    expectation_ids=("find-target-customers",),
    name="下游查询可消费性",
    evaluation_question=(
        "Live 是否以真实下游支持的形式交付查询并保持用户目标客户范围？"
    ),
    # 其他字段仍存在，但不在本次引用展示范围内。
)

AuthorityFinding(
    finding_id="client-search-current-field-validation",
    finding_kind="current_behavior",
    business_question="当前部署使用什么字段知识校验结构化条件？",
    dimension_ids=("downstream-query-consumability",),
    basis_source_ref_ids=("client-search-field-definitions",),
    status="resolved",
    result="使用当前环境选中的字段配置形成运行时字段集合并执行校验。",
    resolution_reason="当前环境配置选择该字段定义，运行时加载并用于查询校验。",
    unresolved_reason=None,
    required_evidence=(),
)

MaterialInvestigation(
    source_ref_id="client-search-field-definitions",
    source_location=(
        "business://src/main/python/config/field_definitions_args.yaml"
    ),
    # 其他调查字段仍存在，但引用展示只需要 source_location。
)
```

调用：

```python
presenter.show(
    finding,
    related_schemas=(contract, report),
)
```

标准展示：

```text
AuthorityFinding [schema]

finding_id:
  client-search-current-field-validation

finding_kind:
  current_behavior

business_question:
  当前部署使用什么字段知识校验结构化条件？

dimension_ids:
  - downstream-query-consumability
    ↳ [reference → EvaluationDimension.dimension_id]
      name:
        下游查询可消费性
      evaluation_question:
        Live 是否以真实下游支持的形式交付查询并保持用户目标客户范围？
      expectation_ids:
        - find-target-customers
          ↳ [reference → BusinessExpectation.expectation_id]
            user_role:
              需要寻找目标客户的业务人员
            use_scenario:
              用户通过自然语言描述目标客户群体并使用客户搜索产品
            desired_outcome:
              获得符合其已表达筛选要求的客户集合

basis_source_ref_ids:
  - client-search-field-definitions
    ↳ [reference → MaterialInvestigation.source_ref_id]
      source_location:
        business://src/main/python/config/field_definitions_args.yaml

status:
  resolved

result:
  使用当前环境选中的字段配置形成运行时字段集合并执行校验。

resolution_reason:
  当前环境配置选择该字段定义，运行时加载并用于查询校验。

unresolved_reason:
  null

required_evidence:
  []
```

该输出首先保留 Schema 本身的字段和值，再把显式引用对象的关键实际值放在
`reference` 展示边界内。它没有新增“业务意义”“业务链路”或其他解释章节。

## 8. 协议不变量

1. ID 仍是 Schema 间唯一的持久化关联方式，展示不得复制业务字段回源
   Schema。
2. 引用关系必须显式声明，禁止根据字段名或自然语言猜测。
3. Validator、Solidify 和 Presenter 必须共用同一份引用关系定义。
4. 展示字段必须按 Schema 类型固定，禁止按 Case 临时增删。
5. Presenter 只负责读取、解析引用和格式化，不产生业务结论。
6. 引用对象的实际值必须来自本次传入的相关 Schema，不得来自模型记忆或
   历史缓存。
7. 展示必须保留 ID 供追踪，但应同时展示目标 Schema 的关键业务字段。
8. 未声明或无法解析的关系必须明确暴露，禁止静默跳过。
9. 引用展开必须使用统一的 `reference` 展示边界，禁止把目标 Schema 字段
   合并成来源 Schema 的嵌套字段。
10. Presenter 不得用目标对象的名称、描述或其他人类可读值替换来源 Schema
    中真实保存的 ID。

## 9. 实施边界

本协议落地时只需要通用基础设施：

- 一份由 Schema 协议维护的引用关系 Registry；
- 一份按 Schema 类型维护的最小展示字段 Registry；
- 一个确定性的 `SchemaPresenter`；
- Validator 与 Presenter 共享引用关系的测试；
- Authority、Planning 或其他业务 Schema 按需登记自身关系和展示字段。

不需要：

- 修改现有业务 Schema 以复制展示内容；
- 为 AuthorityFinding 新建专属 View Schema；
- 为每种 Schema 单独编写 `show_*()`；
- 增加 LLM 调用；
- 引入调查阶段专属 Package。
