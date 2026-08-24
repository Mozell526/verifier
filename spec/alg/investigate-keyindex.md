# Investigation Key-Index 协议

# 第一章：协议定义

## 1. 目标

Key-Index 是调查系统中的通用导航协议。它把一个无法直接完整装入上下文的对象集合，转换为可检索、可定位、可加载的入口层：

```text
对象集合
  ↓ build / project
Index + Index Catalog（entry 集合 + 可发现的索引登记）
  ↓ Runtime 按当前子问题选择零个、一个或多个 Index
  ↓ search_index
有限候选 entry
  ↓ load_entry
真实对象（或对象的一部分 / 子集合）
  ↓
Harness AI 调查 / Runtime 只读使用
```

它解决五类问题：

1. 大型资料无法在有限上下文中完整读取；
2. 调查产物数量增多后，调用方难以找到与当前事项相关的对象；
3. 不同项目各自实现私有搜索工具，无法复用统一的检索、加载与追溯合同；
4. 检索结果与真实资料、调查产物之间缺少稳定的导航关系。
5. Runtime 在调用 `search_index` 前，不知道当前有哪些 `index_key`、各自索引什么集合、
   返回什么类型和粒度的目标，只能猜测或把项目私有 key 写死在 Prompt / 代码中。

Key-Index 只负责**发现候选和定位目标**，不解释业务含义，不产生业务结论。

## 2. 基本概念

| 词 | 含义 |
|---|---|
| 对象（object） | 可被检索和加载的真实单元：一个 material、一个字段、一条规则、一个章节 |
| 集合（collection） | 一组对象的整体，可以被建立索引 |
| 包含（contain） | 一个对象内部还可以有子对象集合，是“下钻”的来源 |
| 索引（index） | 某个集合的导航层，由 entry 组成 |
| entry | 索引中的一个可检索入口，指向集合中的对象或对象的一部分 |
| Index Catalog | 当前权限空间内可用 Index 的结构化登记，只暴露索引身份、集合、目标类型与粒度，供 Runtime 在检索前选择 Index |

对象、集合、包含三者构成递归关系：

```text
material 是一个对象
  └─ 它包含一个字段集合（子集合）
       └─ 字段是子集合中的对象
```

“完整”和“部分”是相对的：一个对象在它所属的集合中是单元；它自己又可以包含子集合。集合可以是：

- 整个调查包的所有 material；
- 单个 material 内部的字段 / 章节 / 规则；
- 其他任意具有稳定对象的调查产物。

Index Catalog 解决的是 **Index Discovery**，不是索引执行链。多个 Index 可以位于不同
集合边界，但协议不推导默认父子关系、先后顺序或“命中后必须跳到哪个 Index”。Runtime
可以按当前问题选择零个、一个或多个 Index；不需要索引时继续普通 Search / Load。

## 3. 核心语义

### 3.1 索引是定位和提取，不是切碎

内容本体始终保持完整、原样。索引不持有内容副本，也不把内容物理切块。它只记录：

```text
哪些内容、在哪个位置、可以被什么检索词找到
```

`load_entry` 按位置从原始内容中提取所需部分，因此原始结构、相邻上下文和内容间关系都不会因索引而失真。

### 3.2 entry 与对象不是一一对应

同一个对象可以被多个 entry 引用，不同入口可以指向同一内容的不同粒度：

```text
字段 age
  ├─ entry “年龄”            （按业务名查）
  ├─ entry “age”             （按字段名查）
  └─ entry “出生日期等价条件”  （按主题查）
```

多入口是特性：不同查询意图需要不同入口，重复是允许的。

### 3.3 target 粒度任意

entry 的 target 可以是：

- 一个完整对象（整个 material / 整个字段定义）；
- 对象内部的一个部分（某一段、某条规则）；
- 一个容器（包含多个子对象的范围）。

`load_entry` 一个容器时，可以整体加载，也可以先返回容器结构再继续下钻。具体取多少由调用方决定。

### 3.4 索引不是结论

必须始终满足：

```text
索引命中 ≠ 事实成立
索引未命中 ≠ 事实不存在
索引条目 ≠ 原始证据
候选集合 ≠ 权限白名单
```

Search 未命中只能说明“本次索引没有召回候选”，不能自动推出资料不存在、unresolved 或 not_evaluable。命中 entry 后必须继续加载真实对象，由领域 Agent 验证与综合。

## 4. 设计边界

Key-Index 不负责：

- 判断资料是否权威；
- 判断业务问题是否 resolved / unresolved；
- 判断 fulfilled / not_fulfilled / not_evaluable；
- 生成 AuthorityResolution；
- 把索引条目当成事实或证据；
- 将未命中自动解释为资料不存在或证据不足；
- 让 Runtime 修改、晋升或回写调查层资产；
- 固化跨 case 的“问题 → 结论”复用资产。

## 5. 通用 Schema

```python
@dataclass(frozen=True)
class InvestigationKeyIndex:
    index_key: str
    collection_ref: str
    target_kind: str
    entry_granularity: str
    retrieval_channels: tuple[str, ...] = ()
    default_retrieval_channels: tuple[str, ...] = ()
    entries: tuple[InvestigationKeyEntry, ...] = ()


@dataclass(frozen=True)
class InvestigationKeyEntry:
    key: str
    name: str
    search_text: str
    target_ref: str
```

字段含义：

- `index_key`：当前调查包内一个索引集合的稳定名称，由应用层声明；
- `collection_ref`：被索引集合的稳定逻辑引用，例如 EvidenceRef/source ref 或调查对象
  集合 ID；不是用途说明或自由文本；
- `target_kind`：entry 所指目标的稳定类型，例如 `material_decision`、
  `evidence_locator`；
- `entry_granularity`：entry 目标的稳定粒度，例如 `investigated_statement`、
  `yaml_list_range`；
- `retrieval_channels`：该 Index 可使用的召回通路集合，例如 `exact`、`lexical`、
  `embedding`；通路名是检索能力，不是业务路由或结论；
- `default_retrieval_channels`：调用方未指定通路时使用的默认子集；必须包含于
  `retrieval_channels`。为空表示由注册的搜索实现使用自身默认能力；
- `key`：entry 在同一 `index_key` 内唯一的稳定定位键；
- `name`：供工具结果和人工识别使用的短名称；
- `search_text`：资料派生的 **retrieval projection**，不是 Runtime query，也不是证据；
  它可以被 lexical、embedding 或其他文本通路共同物化使用，必须是 target 真实内容的
  确定性投影，禁止 AI 自由生成或补充同义词；字段名因兼容性暂保留，不能据此把协议理解成
  lexical-only 搜索；
- `target_ref`：命中后由所属应用解析的稳定逻辑目标引用，可以是对象 ID、对象内部 locator、或容器引用；它不要求等同于 Runtime ContextUnit ID。

约束：

- `(index_key, key)` 在当前调查包内唯一；
- `index_key` 在当前调查包的 Catalog 中唯一；
- `collection_ref` 必须指向当前调查包已登记的真实集合，且与 Builder 实际读取的集合一致；
- 同一 Index 内所有 entry 的目标必须符合其 `target_kind` 与 `entry_granularity`；不能用
  宽泛类型掩盖混合目标；确需不同类型或粒度时建立不同 Index；
- `name` 保持简短；
- `search_text` 可以比 `name` 丰富，但不得冒充原始资料正文或最终结论；
- `search_text` 的每个词必须能追溯到 target 自身内容或其来源资料，
  不得嵌入评测 case 问题、答案词或资料中不存在的同义词；
- `target_ref` 必须能解析到当前调查包中的真实对象或其确定性定位；
- 调查包只保存稳定逻辑地址，不得写入某次 Runtime 的 ContextUnit ID、selection_ref 或其他临时加载地址；
- Core 不解释 `target_ref` 的业务类型；绑定应用的 Target Resolver 负责在当前项目、Role、调查快照与权限范围内，将其确定性解析为零到多个可加载目标；
- entry 不携带 Authority status、Judge verdict、case expected answer 或运行时结论。
- `default_retrieval_channels` 不得声明 Index 未支持的通路；实际注册实现必须能够执行其
  声明的每条通路；
- Catalog 字段不得携带 `use_when`、`next_index`、priority、recommended query、case
  问题/答案词、自然语言同义词路由或业务结论。

`name` 与 `search_text` 分离的原因：短名称适合展示，但通常不足以召回自然语言问题。例如：

```text
name        = 下游可承载的字段空间与操作符空间
search_text = 下游可承载的字段空间与操作符空间 field_definitions_args.yaml 字段/操作符/
              值类型声明 意图定义总数=371 真实字段样例: searchClientName clientSex ...
              （全部来自 target 与其来源资料的确定性投影）
```

`search_text` 是调查层 Builder 从 target 真实内容确定性构建的投影，不是 AI 生成的
导航描述。调用方命中后必须先将 `target_ref` 解析为当前运行可加载的目标，再通过证据空间加载真实内容。投影未覆盖的查询词
由 runtime 重构 query 解决（§12.5），不得预埋。

### 5.1 Retrieval Channel 与 Index 的关系

Key-Index 定义 entry、`target_ref`、发现、加载与追溯合同；Retrieval Channel 定义“如何从
某个 Index 召回 entry”。二者不得混为一体：

```text
Index entries
  ├─ exact channel       正式 ID、完整枚举值、结构化 key
  ├─ lexical channel     字段名、操作符、专有名词和原文词项
  └─ embedding channel   自然语言改写和概念性相似召回
```

- 一个 Index 可以声明零个、一个或多个通路；协议不要求所有 Index 都使用 embedding；
- exact 命中、词法命中和向量相似均只产生导航候选，不自动取得证据资格；
- embedding 是补充召回能力，不得天然取得最终排序、资料适用性或业务裁决权；
- 大型枚举的成员判定应优先使用完整 item 边界上的 exact lookup；把多个枚举项合成一个
  chunk vector 不能证明某个具体值存在；
- 同一 `search_text` 可以派生倒排项和 embedding vector；调查包保存稳定投影，具体倒排
  结构、向量和模型版本由 Solidify / Runtime 物化；
- 向量命中必须保留模型与投影版本的运行记录，但不要求把向量本身写入调查 manifest。

## 6. 通用工具合同

### 6.1 Index Catalog 暴露

Runtime 在构造 `search_index` 调用前，必须能看到当前权限空间内已注册 Index 的：

```text
index_key
collection_ref
target_kind
entry_granularity
```

V1 不要求新增 `list_indexes` Tool。Catalog 可以由 Core 根据当前项目、Role、调查快照和
权限确定性生成，并通过 `search_index` Tool 的注册 metadata / description，以及
`index_key` 参数说明暴露。无论采用何种载体，都必须满足：

- 只暴露当前调用方有权使用且实际已注册的 Index；
- 不暴露 entry、`search_text`、业务结论或建议查询；
- 不要求 Runtime 按固定父子链或固定顺序调用；
- Runtime 不得猜测 Catalog 中不存在的 `index_key`；
- Catalog 是导航元数据，不是 Evidence，也不能进入 Authority basis；
- Catalog 缺失、Index miss 或目标解析失败，只说明导航没有完成，不能直接推出
  unresolved / not_evaluable。

### 6.2 `search_index`

输入：

```text
index_key
query
limit
optional channels
```

输出（有限候选）：

```text
index_key
key
name
target_ref
matched_channels
optional channel_scores
optional fused_score
```

要求：

- 返回数量不超过 `limit`；
- 候选必须来自指定索引；
- 不返回完整目标正文；
- 不返回 Authority 或 Judge 的预判结论；
- `channels` 为空时使用 Index 的默认通路；调用方显式指定时只能选择该 Index 已登记支持的
  通路，不能借参数调用未注册能力；
- 各通路独立召回后可以去重、融合；结果必须保留 `matched_channels`，可选保留各通路分数，
  不能只返回一个无法解释来源的混合分数；
- 排序与融合实现可替换（exact、词法、语义、RRF 或其他策略），实现不属于协议业务语义；
- embedding、融合分数和多通路共同命中都不是 Evidence，也不证明 target 适用于当前问题；
- `search_text` 默认不直接返回，避免把导航文本误作证据；调试或审计模式可在 receipt 中记录匹配信息。

### 6.2.1 可选 Candidate Selection / Rerank

多通路去重后的候选超过当前加载预算时，可以增加可选的 Candidate Selection / Rerank：

```text
multi-channel candidates
  ↓ optional rerank / budget selection
limited SearchHit[]
```

- Rerank 只决定候选的加载优先级和预算裁剪，不判断资料权威性、适用性、`resolved` 或三态；
- 小集合或合并后候选已在预算内时，不应为形式完整强制增加 Rerank；
- 协议不固定 RRF 权重、embedding 阈值、Top-K、Cross-Encoder 或 LLM reranker；这些必须通过
  跨场景实验验证，不能围绕当前 case 调参；
- 被 Rerank 丢弃只表示未进入本轮有限候选，不能推导资料不存在；Runtime 必须保留继续检索、
  改写 query 或选择其他 Index 的能力。

### 6.3 `load_entry`

输入：

```text
index_key
key
```

输出至少包含：

```text
index_key
key
target_ref
resolved target（内联对象内容和/或导航信息）
locator / provenance
optional load_targets
optional target_resolution
```

要求：

- 一次加载一个明确 entry；
- 禁止用空 key、通配符或异常大的 limit 绕回全量上下文注入；
- resolved target 必须来自 `target_ref` 对应的真实对象，不得由模型补写；应用可以直接返回小型目标内容，也可以返回继续读取目标所需的导航信息；
- `load_targets` 是 Target Resolver 在当前运行环境内解析出的零到多个受权限约束的短期加载地址；它是 `load_entry` 的协议级顶层字段，不得藏入 `content`；没有可加载物化单元或该应用直接返回终端目标内容时可以为空；
- `target_resolution` 是可选的地址解析说明（例如状态、解析策略、命中单元数或失败原因），同样属于导航元数据而不是目标正文或业务结论；
- Key-index 本身不规定 resolved target 在下游业务中的证据资格；消费应用必须声明何时还需执行正式 Load。Authority 证据导航应用中，`load_entry` 返回的对象、导航信息与 `load_targets` 均不能直接进入 `basis_evidence_ref_ids`；
- Authority 必须继续使用 EvidenceSpace 的正式 Load 操作，只有实际 Load 返回的 ContextUnit 或物化 ToolResult 才能作为证据；
- 加载容器时，调用方可以选择整体加载、加载覆盖该 locator 的一个或多个资料单元，或继续下钻到子 entry；
- 应用可以在通用合同之上提供领域化 Tool 名称，但不得改变追溯语义。

### 6.4 Target Resolution

Target Resolver 将 `target_ref` 表示的稳定逻辑目标，解析为当前 Runtime 中零到多个
可加载目标：

```text
target_ref + 当前项目/Role/调查快照/权限
  ↓ Target Resolver
zero or more load_targets + resolved locator + resolution provenance
```

Target Resolver：

- 只做地址解析，不判断 Authority `resolved/unresolved`，也不判断
  `fulfilled/not_fulfilled/not_evaluable`；
- 不产生业务结论；是否允许直接消费 resolved target 由应用合同决定，Authority 证据导航应用不得把 index entry、resolved target 或 `load_targets` 当成 Evidence；
- 不得扩大当前 Role 的资料权限，也不得跨 Production/Draft 或调查快照取资料；
- 必须根据已登记 target、locator 与资料物化关系确定性解析，不得在 resolver 内使用
  模糊搜索猜测目标；
- 允许一个逻辑目标覆盖零个、一个或多个可加载资料单元；Key-index 与 Evidence
  ContextUnit 的分块边界不要求一致；
- 解析为空、无权限、locator 失效或不支持该 target 类型属于导航/环境事实，不得自动解释为
  资料不存在或业务 unresolved。


检索召回与目标解析是两个独立质量门：

```text
retrieval quality       entry 是否被找到
resolution quality      entry 是否解析到与 locator 对应的真实可加载目标
```

搜索命中但 `load_targets` 为空，不能算完整链路通过。应用不得以静默全库模糊 Search fallback
掩盖无法解析的 `target_ref`；可以显式继续检索，但 receipt 必须保留原解析失败事实。

### 6.5 Receipt

每次调用至少应能追溯：

```text
使用了哪个 index_key
查询或加载了哪个 key
命中了哪个 target_ref
解析到了哪个真实对象、locator 与 load target；随后实际 Load 了哪个资料单元
```

如果目标最终落到 EvidenceRef，应通过 EvidenceRef 获取当前调查快照中的位置和版本信息。索引不重复复制 revision/hash，也不因普通资料 hash 变化自行作出业务失败判断。

---

# 第二章：索引构建

## 7. 构建职责分工

索引构建由三层职责组成，不交给单一主体：

| 职责 | 负责方 | 内容 |
|---|---|---|
| 探索边界与定位 | 调查层 + 确定性 Builder / 校验层 | 调查层提出候选对象、entry 粒度和 target；Builder 物化，校验层验证后形成调查结论 |
| 生成 retrieval projection / exact keys | 确定性 Builder | 从 target 真实内容与稳定结构投影，可追溯，禁止 AI 补充 case 表达 |
| 选择召回通路 | 调查方案 + 校验层 | 根据 Collection 结构声明 exact / lexical / embedding 等适合通路，不预测 Runtime 路由 |
| 物化检索实现 | Solidify / Core | 构建 exact map、倒排结构、embedding vectors 与版本记录 |
| 验证与把关 | 校验层（规则 + 审核） | 结构、目标可解析、覆盖完整、语义不越界 |

Harness AI 可以建议索引方案（索引哪些对象、用什么粒度），但不得单独决定：

- 集合中有哪些真实对象；
- 对象边界；
- key 和 target 的准确性；
- 是否把字段存在说成业务支持。

`name` 可以由 Harness AI 在探索构建中建议，并由校验层确认；`search_text` 必须是
target 真实内容的确定性投影，不得由 Harness AI 生成、改写或补充（§12.5）。

### 7.1 Index 策略是调查结论

本协议不预设“某类资料必然采用某种 Index”。字段、规则、枚举值、映射、章节、statement
等只是不具约束力的候选对象示例，不构成资料类型到 Index 策略的固定映射。调查层必须结合
当前 Collection 的真实结构、规模、稳定标识、Runtime 发现任务和可加载边界，探索：

- 是否需要 Index；
- 索引哪些真实对象以及 entry 粒度；
- 哪些源内容可形成 exact key 与 retrieval projection；
- 启用哪些召回通路；
- `target_ref` 如何确定性加载真实目标；
- 候选策略的覆盖限制、成本和风险。

探索结果只有三类：

```text
selected    至少一个候选通过冻结模拟与语义审查，可交给 Solidify
no_index    普通 Search / Load 更合适，不为满足结构要求强建 Index
unresolved  当前没有合格策略，记录缺少的资料、定位能力或验证条件
```

Core 只提供通用协议、检索通路、Target Resolver 与校验能力，不替项目调查层选择策略；
Solidify 只物化 `selected` 策略，不临场发明对象边界、projection 或路由。

## 8. 构建方式

以下构建方式用于提出候选策略，不是封闭分类，也不表示看到某种资料就必须采用对应方式。
同一 Collection 可以比较多个候选、并存多个相互独立的 Index，或最终选择 `no_index`。

### 8.1 资料原生索引（结构已知）

当对象集合来自已有稳定结构的资料时，应优先确定性构建：

```text
原始资料
  ↓ 解析稳定结构
entry key + name + search_text + target locator
```

候选示例包括：

- YAML 字段配置尝试 field、intent 或其他稳定节点粒度；
- API 定义尝试 endpoint、operation 或 schema 节点粒度；
- 规则资料尝试规则组、单条规则或其他可加载边界；
- 文档尝试章节、statement、表格行或其他稳定 locator。

示例不规定最终策略。调查仍须比较召回、拒绝、加载上下文与成本，禁止让 LLM 发明原始
资料中不存在的定位 key。

### 8.2 大型资料探索构建（结构未知）

当资料本身很大、没有现成稳定结构时，需要先理解资料、划分边界，再建立索引：

```text
大型资料
  ↓ Harness AI 探索主题 / 边界 / 层级
候选单元（每个单元可对应一个或多个原始 locator）
  ↓ 策略校验边界与回溯规则
entry
  ↓ 校验层验证
可消费索引
```

Harness AI 在探索构建中负责：

- 发现主题与单元边界；
- 建议层级（主题 → 子主题 → 具体条目）；
- 建议 `name`（短展示名）；`search_text` 仍由单元真实内容确定性投影，
  禁止 AI 改写或补充同义词；
- 建立单元到原始 locator 的对应关系。

策略负责约束探索：

- 单个 entry 必须能在有限上下文内加载；
- 每个 entry 至少引用一个原始 locator；
- 一个 entry 可以引用多个 locator（跨文件 / 跨章节主题）；
- 不允许只保存 AI 摘要而没有原文定位；
- 无法确定边界时退回普通资料读取；
- 跨段推理结论不得直接写入 entry；
- 大资料优先建粗粒度目录，再按需细分。

注意：探索构建产生的层级是**导航组织关系**，不是业务关系。例如“查询规则 → 年龄查询”只表示导航归属，不表示“年龄查询支持出生日期等价转换”，后者必须由领域 Agent 加载原始内容后判断。

### 8.3 调查投影索引（已有对象）

当对象集合是调查阶段已形成的产物时，可以把已有稳定对象投影为 entry：

```text
调查产物（如 MaterialDecision）
  ↓ projector
entry key + 导航文本 + target_ref
```

投影的检索表示必须是调查产物原文的确定性投影，不得由 Harness AI 生成或补充；
同时必须满足：

- `target_ref` 指向已存在的调查对象；
- 不新增伪事实；
- 不把推测写成已确认结论；
- 不通过索引绕过原调查产物的 schema 和 validator。

### 8.3.1 运行时投影（声明驱动）

当对象集合的成员枚举来自业务源、调查时无法写死（如字段级 YAML 映射/规则切片的
字段名）时，调查层只需声明索引策略，不写死 entry：

```text
EvidenceRef.metadata.key_index = {"entry_granularity": "field"}
  ↓ Runtime materializer 已物化字段级切片
authority.evidence.<ref_id>（entry key=字段名，search_text=字段名+值级确定性投影）
```

- entry 的 `search_text` 必须来自已物化切片真实内容的确定性投影，禁止 AI 生成；
- 运行时每次构造 Environment 时从当前已物化内容重新投影，因此业务源内容变化后
  按 key 消费自动拿到新值（对应"资产刷新/确定性重建"，不是业务重调查）；
- 没有声明的切片资料不投影（Index 策略是调查项，Core 不做隐式决策）；
- 运行时投影只支持字段级切片（field / yaml_mapping_field）；块级切片
  （yaml_list_chunk）的 chunk 边界由 slice 声明固定，必须由调查层在 manifest
  key_indexes 显式登记，不接受 metadata.key_index 声明绕过；
- 大切片资料（field / yaml_mapping_field / yaml_list_chunk）无任何 key-index
  支撑时，调查产物校验拒绝（authority.md Investigate 义务）。

### 8.4 不适合建索引的集合

以下情况可以继续使用普通 Search / Load，不强行生成 Key-Index：

- 没有可稳定解析的目标；
- 条目无法回到真实对象；
- 集合很小，索引不会改善上下文使用；
- 检索文本必须依赖未验证的业务推断才能成立；
- 构建成本明显高于直接读取成本。

## 9. Validator

通用 Validator 至少检查：

- `index_key` 非空，并在当前调查包内唯一；
- `collection_ref`、`target_kind`、`entry_granularity` 非空；
- `collection_ref` 能回到当前调查包已登记的真实集合；
- Index 的声明元数据与 Builder 实际输出一致，entry 目标类型和粒度在 Index 内统一；
- `(index_key, key)` 唯一且非空；
- `name`、`search_text`、`target_ref` 非空；
- `target_ref` 能被所属应用解析；
- Search 结果来自指定索引且不超过 `limit`；
- Load 命中明确 entry，并返回相同 `index_key + key + target_ref`；
- Receipt 能回溯到真实目标；
- entry 和工具结果不携带 Authority status、Judge verdict 或 case expected answer；
- 索引内容未被当作原始证据或最终结论。

应用 Validator 负责进一步验证领域目标，例如：

- 资料内部 locator 是否真实存在；
- MaterialDecision target 是否存在于当前 Authority 调查报告；
- 投影是否保留原对象的引用关系；
- `search_text` 词项是否可追溯到 target 自身内容或其来源资料。

---

# 第三章：应用层

## 10. 应用模式

同一套通用协议可用于不同集合边界，不需要为每个边界发明新机制：

```text
Index A：整个调查包的所有 material
  entry = material（或其 MaterialDecision）

Index B：某个 material 内部的字段 / 章节 / 规则
  entry = 字段 / 章节 / 规则
```

两个 Index 是同一协议在不同集合边界上的应用。一个 material 在 Index A 中是对象，
在 Index B 中又是一个包含子集合的容器。但协议不因此建立固定的 A → B 父子链：Runtime
通过 Catalog 识别二者，可以只用其中一个，也可以按当前子问题使用二者。

新增应用只需定义：

```text
index_key
collection_ref
target_kind
entry_granularity
entry key 生成规则
name 生成规则与 search_text 投影规则
target_ref 格式
load resolver
应用 validator
```

不应为每个项目重新发明搜索和 receipt 协议。

## 11. 应用一：大型资料内部检索

对大型字段配置：

```text
business://src/main/python/config/field_definitions_args.yaml
```

建立：

```python
InvestigationKeyIndex(
    index_key="client-search.field-definitions",
    collection_ref="business-field-definitions",
    target_kind="evidence_locator",
    entry_granularity="yaml_field_definition",
    entries=(
        InvestigationKeyEntry(
            key="customer_type",
            name="客户类型",
            search_text="customer_type 客户类型字段定义 操作符 MATCH 值类型 enum（YAML 原文确定性投影）",
            target_ref="evidence://business-field-definitions#customer_type",
        ),
        InvestigationKeyEntry(
            key="age",
            name="年龄",
            search_text="age 年龄字段定义 操作符 GTE LTE RANGE 值类型 数值（YAML 原文确定性投影）",
            target_ref="evidence://business-field-definitions#age",
        ),
    ),
)
```

调用：

```text
search_index("client-search.field-definitions", "17、18周岁的客户", 5)
  → age / 年龄 / evidence://...#age

load_entry("client-search.field-definitions", "age")
  → 该字段的原始定义、必要相邻上下文和 locator
```

## 12. 应用二：集合层 material 能力导航

### 12.1 目标

Authority 接到 `decision_question` 后，不应只能对所有原始资料做无方向搜索。调查层可以把 `MaterialDecision` 投影为 material 能力索引：

```text
MaterialDecision
  ↓ project
KeyIndexEntry
  ↓ Runtime Authority search_index
候选 MaterialDecision
  ↓ load_entry
完整 MaterialDecision
  ↓ target 指向原始 Evidence
读取原始资料
  ↓
Authority 现场综合
```

### 12.2 投影示例

```python
InvestigationKeyEntry(
    key="field-definitions.field-semantics",
    name="字段定义与支持范围",
    search_text="字段定义与支持范围 field_definitions_args.yaml 字段/操作符/值类型声明（确定性投影，词项可追溯）",
    target_ref="material-decision://field-definitions.field-semantics",
)
```

命中只说明该 MaterialDecision 可能与当前问题相关。Authority 必须加载完整对象，并根据其引用阅读原始资料。

加载后的 MaterialDecision 自带 `conclusion_kind` 定位。Authority 按
`spec/alg/material-positioning.md` §4 的信息关系
（normative_rule / external_fact > inlive_boundary > current_behavior）筛选候选；
索引命中本身不等于业务证据，也不能提升资料的定位。

大资料内部 locator 与 Evidence ContextUnit 的分块不要求一致。例如：

```text
search_index("阖家团圆康")
  ↓
target_ref = evidence-navigation://business-planfullname-enums/
             polNoInfo.plancodeinfo.planfullname.values[7300:7342]
  ↓ Target Resolver
load_targets = [覆盖 values[7300:7342] 的一个或多个 Evidence ContextUnit]
  ↓ load_context_units
加载真实枚举块后，由 Authority 核实该值是否存在及是否适用于当前问题
```

Target Resolver 可以返回多个覆盖该 locator 的资料单元，但不得为了统一分块而复制资料、
改写索引或扩大加载范围。

### 12.3 Authority 使用流程

```text
decision_question
  ↓ 必要时拆成若干检索意图
search_index(material capability index)
  ↓
有限候选 MaterialDecision（top-k，不只看 top-1）
  ↓
对候选做验证（load_entry 读取导航对象）
  ↓ Target Resolver
解析为当前运行中的精确 load target
  ↓ EvidenceSpace Load
读取对应原始 Evidence 和必要关联资料
  ↓
处理适用条件、限制、连接与冲突
  ↓
AuthorityResolution(resolved / unresolved)
```

约束：

- MaterialDecision 是可导航的资料能力描述，不是跨 case 结论资产；
- Capability entry 不是业务证据；
- CoverageGap 不自动进入 capability index，也不自动等于 unresolved；
- Search 未命中不能直接产生 unresolved；
- 候选集合不是 Authority 的硬权限白名单；
- Authority 的现场结论不回写或修改调查索引；
- Runtime 仅只读消费生产调查资产。

### 12.4 Collection 能力导航与内部对象导航

资料能力 Index 与资料内部对象 Index 解决不同层次的问题：

```text
decision_question
  ↓ MaterialDecision / collection-capability Index
找到“哪些 Collection 能决定该事项”
  ↓ Runtime 结合 Catalog 与当前子问题选择后续 Index
字段 / 枚举值 / 规则 / 章节等内部对象 Index
  ↓ load_entry
精准真实资料
```

- MaterialDecision 可以指向一个资料 Collection，而不必假装总能直接定位到单个字段或规则；
- 当 Collection 已被切成细粒度 ContextUnit，且 MaterialDecision locator 只描述整个资料类别时，
  调查层应为该 Collection 建立适当的内部对象 Index，或提供同等精度的确定性 resolver；
- 多层导航是 Runtime 对 Catalog 的现场使用，不建立固定 `next_index_key`、默认父子链或自动
  业务路由；同一个 Collection 可以有多个不同粒度和检索方式的 Index；
- 最终 Authority basis 必须来自实际加载的真实 Evidence，不能停留在 Collection 能力声明。

### 12.5 构建要求（实验依据）

当前真实调查包模拟表明：

1. lexical 对正式字段、操作符和项目术语稳定，但用户问法与资料词汇不一致时会漏召回；
2. embedding 能补充责任边界和自然语言改写，却会对无关问题强制产生候选，并可能把正确的
   项目术语结果排后；它适合作为一条通路，不适合独占最终排序；
3. 简单 RRF 能保持部分召回，但不能识别无关候选；当前小型 MaterialDecision 集合合并后
   通常只有有限候选，尚未证明必须增加独立 Reranker；
4. “医保类型”等概念与具体字段/资料之间的关系若不在真实资料投影或内部对象 Index 中，
   不能指望 Runtime 改写 query 或 embedding 凭空稳定补全；
5. 搜到 MaterialDecision 但其 locator 只指整份资料类别时，字段/规则切片仍可能
   `load_targets=0`。召回成功不能代替内部对象导航和 Target Resolution。

因此：

- `search_text` 始终是 target 真实内容的 retrieval projection，每个部分可追溯到来源资料；
- 调查层可以根据资料结构声明 lexical、embedding、exact 等多通路，但不得让 Harness AI
  把评测问题、答案词、推荐 query 或臆造同义词预埋进 projection；
- 概念、正式名称、字段、枚举值、映射关系等若真实存在，应按其原始结构进入对应内部对象
  Index；若资料本身没有该关系，检索层不得伪造；
- 大型值空间不得把任意 first-N 样本塞入 Collection 能力 entry。具体值应在资料内部建立
  覆盖完整对象边界的 Index，成员判定优先 exact；
- Runtime 可以改写 query、选择其他通路或 Index，但这是补充检索行为，不是调查资产缺失
  概念关系的默认补丁；
- Search 未命中、embedding 低分或 Rerank 裁剪都只表示本轮导航结果，不产生 unresolved 或
  not_evaluable；
- 若确需人工词汇资产，应由用户可见、单独审阅并回指正式资料，不混入不可审计的
  `search_text`。

## 13. 应用三：其他对象集合

后续可以按同一协议接入：

- 规范章节和条款目录；
- API / 事件 / 字段契约目录；
- 配置项或规则目录；
- 调查报告中的其他稳定对象集合；
- 项目自定义但能解析到真实目标的导航集合。

---

# 第四章：与调查和运行时的关系

## 14. Draft 调查阶段

Index 策略探索是 Draft 调查项，不是每个 Collection 的强制产物。发现上下文规模、内部对象
定位或 Runtime 有限导航压力后，Harness AI 应按以下闭环推进：

```text
Collection profiling
  → 提出多个候选对象边界 / projection / channel / target_ref
  → 从真实来源确定性构建实验 Entry
  → 冻结测试集并比较候选
  → 校验 retrieval、rejectability、target resolution、loaded context、source derivation
  → selected | no_index | unresolved
```

冻结测试集应在候选比较前确定，并按实际资料情况覆盖：稳定标识、源术语、未复制源 example
的改写、歧义或多对象问题、无关/不支持问题，以及 Search 后的真实 Load。Harness AI 可以提出
策略与做语义审查，但不得同时按未冻结 badcase 补 projection 再用同一 badcase 自证成功。

调查报告应呈现候选、测试类别、结果、取舍、最终状态和覆盖限制；指标不自动选出业务正确
策略。`selected` 的 Index 随调查包作为候选资产交给 Solidify；`no_index` 保留普通 Search /
Load；`unresolved` 记录缺少的资料、定位能力或验证条件，不得注入 fallback 或 AI 自写检索词。

调查包只有在用户触发 promotion 后才进入 Production。Runtime 不自动触发 Draft 调查或 promotion。

## 15. Production / Runtime

Production Runtime 可以只读使用已晋升索引：

```text
Runtime query
  ↓ 从 Index Catalog 选择零个、一个或多个 Index
  ↓ search_index
候选
  ↓ load_entry
真实调查资产或 Evidence
  ↓
领域 Agent 继续判断
```

Runtime 可以在 per-case 结果中记录：

- 调用了哪个 index；
- 读取了哪些目标；
- Authority unresolved 时的 `required_evidence`；
- Judge not_evaluable 时的原因。

这些记录用于结果呈现和后续人工调查参考，不会自动改变全局调查包。

---

# 第五章：现状、实施顺序与验收

## 16. 当前实现状态

`client_search` 已落实：

- 通用 Index / Entry schema、Index Catalog、`investigation.search_index`、
  `investigation.load_entry` 和 Target Resolver 扩展点；
- `authority.material-decisions` Collection 能力导航 Index；
- 产品全称大型枚举的资料内部 Index，可将首段、中段、尾段完整值解析并加载到真实
  YAML list chunk；
- 导航 Tool 与 Authority gateway Tool 分离，entry、projection、locator、score 和
  `load_targets` 均不物化为 Evidence。

尚未落实或未完整落实：

- 正式多通路执行目前仍以确定性 lexical 策略为主，embedding / exact 通路尚未作为统一
  channel 合同接入；
- `business-field-definitions`、`business-enhanced-rules` 等资料已经按字段物化 ContextUnit，
  但对应 MaterialDecision locator 仍停留在整份资料类别，多个 entry 的
  `target_resolution=no-deterministic-match`、`load_targets=0`；
- 除产品全称枚举外，字段、规则、映射等 Collection 内部对象 Index 尚未普遍形成；
- 当前 14 条 MaterialDecision 的多通路模拟通常形成 3～6 条候选，尚未证明必须增加
  独立 Reranker；embedding-only 无关查询仍会产生假候选。

因此当前状态是“Collection 能力导航已形成，部分内部对象导航已打通”，不能表述成整个
Authority 资料链已经完整解决。

## 17. 建议实施顺序

### P0：协议对齐与真实链路验收

- 将 retrieval channel 作为 Index 可声明、Core 可执行的检索能力；
- SearchHit 保留命中通路，召回与 Target Resolution 分别验收；
- 不改变 Authority、Judge 或 fulfilled 三态合同。

### P1：Collection 内部对象导航

- 优先为已按细粒度物化但无法由 MaterialDecision 精准加载的资料建立内部 Index：字段定义、
  enhanced rules、value mappings 等；
- Entry 的 `target_ref` 必须能够确定性加载对应 ContextUnit；
- 产品枚举成员判定继续以 item 边界上的 exact lookup 为主，不以 chunk embedding 证明存在性。

### P2：多通路召回

- MaterialDecision 可使用 lexical + embedding；
- 字段定义可使用 exact + lexical + embedding；
- 枚举和映射优先 exact + lexical，embedding 仅在资料用途确需模糊发现时启用；
- projection 必须来自真实资料，禁止 Harness AI 补 query 同义词、case 词或推荐路由。

### P3：按规模验证可选 Rerank

- 只有多路合并候选持续超过加载预算时才引入 Rerank；
- 对召回率、无关查询、模型漂移和跨项目泛化做冻结实验；
- Rerank 只裁剪加载优先级，不取得 Authority 裁决权。

## 18. 验收标准

### 通用层

- 同一套 Tool 能检索不同应用定义的索引集合和召回通路；
- Runtime 能看到有权使用的 Catalog，并理解集合、目标类型、粒度和支持通路；
- Runtime 不猜测未登记 `index_key`，也不被迫遵循父子链；
- Core 不包含 client_search、字段、Authority 等项目或领域硬编码；
- Search 返回有限候选，并保留 `matched_channels`；
- Entry、score、projection 和融合结果不被当作 Evidence 或业务结论；
- 无命中或低相似度不会被自动解释成 unresolved / not_evaluable。

### 构建与校验

- spec 不固定资料类型到 Index 策略的映射，调查层对具体 Collection 形成 `selected | no_index |
  unresolved` 结论；
- 候选比较使用预先冻结的稳定标识、源术语、held-out 改写、歧义/多对象、无关/不支持及
  Search→Load 测试，不用临场 badcase 自证；
- 策略决定对象边界、Collection、Entry 粒度与 locator；
- `search_text` 是 target 真实内容的 retrieval projection，可用于多种通路，禁止嵌入
  评测 case、答案词或资料中不存在的同义词；
- exact key 必须来自真实对象边界或稳定结构标识；
- 每个 `target_ref` 均可解析，或者明确报告未解析，不能以模糊 fallback 隐藏；
- 校验层分别报告 retrieval recall 与 target resolution；
- 索引随调查包呈现，由用户控制是否 promotion；没有索引的集合仍可使用原有调查方式。

### 大型资料与内部对象应用

- 常规搜索不把整份大型资料注入上下文；
- Search 候选有上限，Load 读取明确对象或范围；
- 枚举成员查询能够精确命中真实 item 所在目标，并拒绝把语义相似当作成员证明；
- 字段、规则、章节等内部对象可按同一合同接入；
- 搜索命中后能够加载与 locator 对应的真实 ContextUnit。

### Authority 应用

- `decision_question` 可先导航到相关 MaterialDecision / Collection，再按需下钻到具体对象；
- Authority 在实际加载真实 Evidence 后排除假阳性、组合资料、识别冲突并裁决；
- 多路召回、Rerank、MaterialDecision 均不替代 Authority 现场综合；
- Runtime 不回写调查层，也不生成跨 case 问题结论资产；
- 首次未命中时可以重构 query、选择其他 Index 或显式退回 Context Search，但不得隐藏原
  Index miss 或 Target Resolution 失败。
