# client_search 真实业务系统 Authority 资料调查报告

> 本报告用于验证“以业务资料为轴心、以业务上下游为骨架”的 Authority 调查方式。
>
> 本报告调查的是 `CLIENT_SEARCH_REPO` 指向的真实业务系统，不以 verifier 的 Judge、Draft 或评测配置为 Authority 主证据。

## 1. 调查快照

```text
业务仓库：
/Users/xiaozijian/WorkSpace/projects/claude_code/llm_client_search_0513/llm_client_search

Git revision：
2859c55f71ec8a1e9687c73b40cc0987d81d379c

调查方式：
静态读取业务需求、业务配置、业务源码、测试和历史资料；
没有调用外部客户搜索服务；
没有访问下游数据库；
没有取得下游服务提供方的正式契约。
```

因此，本报告可以确认当前业务仓库中的资料内容和代码行为；不能把未实际取得的下游能力或客户结果写成已验证事实。

## 2. 业务目标

用户侧业务资料 `projects/client_search/readme.md` 声明：

```text
业务目标：
产出正确的数据库搜索结果，从数据库中搜索出正确的客户。

判断重点：
字段是否合理；
枚举值是否正确；
是否遗漏必要条件；
是否加入多余条件；
最终筛选出的客户是否属于用户想要的客户群体。
```

真实业务仓库中的 `src/main/python/docs_BAK/项目说明书.md` 将系统描述为：

```text
面向保险代理人的自然语言客户检索平台。
代理人输入中文查询意图，
系统将其转换为结构化查询条件，
再调用后端搜索 API 返回匹配客户。
```

从完整产品角度，业务链路应当是：

```text
保险代理人的客户搜索意图
        ↓
自然语言客户搜索 Parser
        ↓
结构化查询条件
        ↓
下游客户搜索服务
        ↓
客户数据库
        ↓
满足用户意图的客户集合
```

## 3. 当前真实可达业务链路

静态代码调查发现，当前对外 HTTP 主链实际上是：

```text
ParseApiRequest.user_text
        ↓
POST /api/v1/client_search_query_parse
或
POST /api/v1/client_search_query_parse_no_encipher
        ↓
QueryRouter.route_with_peeling()
        ↓
字段、操作符、值、query_logic
        ↓
AskBob ParseApiResponse
```

当前 FastAPI 没有注册 `/search/natural` 或 `/search/structured` 路由。解析接口的职责是返回结构化条件，不执行客户搜索。

业务仓库中确实存在另一条代码链：

```text
SearchService
        ↓
SearchAPIClient
        ↓
POST {SEARCH_API_BASE_URL}/api/v1/search/customer
```

但这条链当前没有接入已注册的 FastAPI 主路由，且 `SearchService.natural_language_search()` 调用 `QueryRouter.route_with_peeling()` 时缺少当前必需的 `trace_id` 参数。因此，它目前只能证明项目曾设计或保留了下游搜索调用能力，不能证明当前公开业务接口已经完成端到端客户搜索。

本报告必须区分：

```text
当前可验证能力：
自然语言 → 结构化查询条件

当前产品目标：
自然语言 → 正确客户集合

当前缺口：
结构化条件与真实客户集合之间缺少正式下游契约和运行证据。
```

## 4. 业务资料目录

### 4.1 用户侧业务要求

| 资料 | 作用 | 证据边界 |
|---|---|---|
| `projects/client_search/readme.md` | 描述业务目标和验收重点 | 是需求和评测口径，不是下游接口契约 |
| `projects/client_search/config.md` | 指向真实业务配置文件 | 证明应调查哪些资料，不证明配置与生产数据库一致 |
| `projects/client_search/prompt.md` | 描述 Parser 预期规则 | 是辅助资料，不能单独作为不可质疑标准 |
| `projects/client_search/judge_boundary-template.md` | 描述 Parser 与外部数据库责任边界 | 是用户侧边界声明，但没有附带下游 mapping 或结果集 |

### 4.2 真实业务配置

| 资料 | 当前业务作用 |
|---|---|
| `field_definitions_args.yaml` | 定义自然语言意图、字段、操作符、值类型、说明、示例和反例 |
| `field_enums_args.yaml` | 为字段提供当前配置中的枚举候选 |
| `value_mappings_args.yaml` | 将口语别名预归一化为配置中的标准值 |
| `enhanced_rules_args.yaml` | 驱动 Level 2 规则、模板、组合条件和枚举展开 |
| `field_mapping_args.yaml` | 将内部语义别名映射到查询字段 |
| `intent_summary_labels_args.yaml` | 为解析结果生成人类可读标签 |

### 4.3 真实业务实现

| 资料 | 当前业务作用 |
|---|---|
| `api/client_search_query_parse_post.py` | 当前公开解析 API 和最终输出包装 |
| `steps/query_router.py` | 组织输入归一化、Level 1/2/4 和最终条件校验 |
| `steps/field_registry.py` | 加载字段定义、枚举和别名映射，并供 RAG、归一化和校验使用 |
| `steps/level1_rule_engine.py` | 处理手机号、证件号、客户号、保单号、姓名等高确定性实体 |
| `steps/level2_enhanced_matcher.py` | 消费增强规则、枚举和值映射，生成确定性业务条件 |
| `steps/level4_llm_parser.py` | 在规则未得到正式条件时，使用字段检索和 LLM 生成条件 |
| `models/schemas.py` | 定义当前 Parser 的字段、操作符和值形状 |
| `services/search_service.py` | 保留自然语言/结构化查询到下游调用的封装，但未进入当前公开主链 |
| `services/search_api_client.py` | 描述当前调用方准备发送给下游的请求形状 |

### 4.4 历史与辅助资料

`docs_BAK` 中的项目说明、字段验证集、设计文档和测试问题，可以帮助理解系统历史目标和设计意图，但目录名称、内容与当前代码之间都表明它们可能是历史快照。

它们可以用于发现：

- 资料变迁；
- 历史业务说法；
- 当前配置可能遗漏的场景；
- 需要进一步确认的问题。

不能仅凭历史资料覆盖当前业务配置或下游现实。

## 5. 逐类资料调查

### 5.1 字段定义资料

```text
资料：
src/main/python/config/field_definitions_args.yaml

SHA256：
4916931df1cc8dbd596fe859e93d39e9b460dc22dc710c0c6800e4357cd51c26
```

它记录：

- 用户可能使用的自然语言；
- 对应查询字段；
- 操作符；
- 值类型和单位；
- 字段说明；
- 示例与反例；
- 对部分语义的补充说明。

业务消费关系：

```text
field_definitions_args.yaml
        ↓ FieldRegistry 加载
字段检索 / Trie / 枚举元数据 / query 归一化
        ↓
Level 4 Prompt 与 Router 最终字段校验
```

可以证明：

- 当前业务系统的字段知识库如何描述某个查询意图；
- 当前 Level 4 和部分运行时校验会看到哪些资料；
- 当前项目希望 Parser 输出什么字段和操作符。

不能证明：

- 所有字段都被下游客户搜索服务接受；
- 字段在下游数据库中一定存在；
- 字段说明已经通过业务方审批；
- 示例代表正式业务语义，而不是当前项目维护者的实现假设。

### 5.2 字段枚举资料

```text
资料：
src/main/python/config/field_enums_args.yaml

SHA256：
4923a5f449212d1da0b99db70123be4c18c4ee69bda3e816ba7ef4c478f47a92
```

业务消费关系：

```text
field_enums_args.yaml
        ↓
FieldRegistry / Level2 / QueryRouter
        ↓
枚举展开、值归一化、最终条件校验
```

可以证明：

- 当前 Parser 配置认为哪些值属于字段枚举；
- 当前 Router 会依据哪些值校验 Parser 输出；
- Level 2 规则会展开哪些候选值。

不能证明：

- 枚举来自生产数据库导出；
- 枚举覆盖下游当前实际值全集；
- 配置值的业务含义与下游数据含义完全一致；
- 配置没有过期或人工录入错误。

### 5.3 值映射资料

```text
资料：
src/main/python/config/value_mappings_args.yaml

SHA256：
883bca9da6445010cb239ca3a32205c7bc0c3308113fa3afda2f8d1b8a04c58f
```

业务消费关系：

```text
value_mappings_args.yaml
        ↓ FieldRegistry.normalize_query()
用户原始表达被预归一化
        ↓
Level 1 / Level 2 / Level 4 接收改写后的 query
```

`FieldRegistry` 会在 Parser 分层处理之前，把命中的别名替换成映射目标。因此该资料对当前运行行为有直接影响。

可以证明：

- 当前业务系统如何把某些口语别名改写为配置值；
- 某个输入在进入规则和模型之前可能被怎样重写；
- 当前实际 Parser 行为为什么采用某个值。

不能证明：

- 映射目标代表业务正式口径；
- 映射目标一定是下游真实合法值；
- 同一业务词发生冲突时，该文件天然高于字段定义或正式业务资料。

### 5.4 增强规则资料

```text
资料：
src/main/python/config/enhanced_rules_args.yaml

SHA256：
96f372ea329ead3bc9550f28e0916ac0bc684a4bdce9e20c1981bccebab69018
```

业务消费关系：

```text
enhanced_rules_args.yaml
        ↓ Level2EnhancedMatcher
正则、枚举模板、组合规则、优先级和字段条件
        ↓
结构化查询条件
```

可以证明当前 Level 2 的确定性匹配规则。它不能单独证明这些规则符合下游搜索语义或产品正式要求。

### 5.5 Parser 输出协议

`models/schemas.py` 定义当前项目内部接受和输出的：

```text
QueryLogic：
AND / OR

Operator：
MATCH / GT / GTE / LT / LTE / RANGE /
CONTAINS / NOT_CONTAINS /
EXISTS / NOT_EXISTS /
GEO_RADIUS / NOT_GEO_RADIUS

Condition：
field + operator + optional value
```

它能证明当前 Parser 的本地数据形状，不能证明下游 `/api/v1/search/customer` 正式支持完全相同的 operator 和 value 语义。

### 5.6 下游搜索调用资料

`services/search_api_client.py` 表明当前调用方准备：

```text
POST {SEARCH_API_BASE_URL}/api/v1/search/customer

body：
header.agent_id
header.page
header.size
query_logic
conditions
sort（可选）
```

这只能证明消费者侧代码如何构造请求。

当前没有取得：

- 下游服务提供方维护的 OpenAPI/IDL；
- 下游搜索服务源码；
- provider-owned contract test；
- 下游字段和枚举契约；
- operator 到 ES DSL 的正式映射；
- 下游响应 schema；
- 当前部署版本信息；
- 固定数据快照和真实客户结果。

因此，不能把 `SearchAPIClient` 的实现和注释当作下游正式 Authority。

## 6. 当前 Parser 业务数据流

```text
用户输入
        ↓
去空格、句号
        ↓
FieldRegistry.normalize_query()
使用 value_mappings 预归一化口语
        ↓
Level 1 提取高确定性实体
        ↓
Level 2 使用 enhanced rules + enums
        ↓
如果 Level 2 有正式结果，当前 Router 丢弃 Level 1 条件
        ↓
如果仍无条件，进入 Level 4
字段检索 + LLM
        ↓
Router 校验字段和枚举值
        ↓
日期、年龄、摘要等后处理
        ↓
ParseApiResponse.extra_output_params
```

补充事实：

- Level 3 语义缓存代码存在，但当前 Router 的初始化和调用被注释，当前主链并未使用；
- 当前非 Level 4 结果默认使用 `AND`；
- `field_definitions` 既参与 Level 4 知识检索，也参与 Router 字段校验；
- `value_mappings` 在分层处理前直接改写用户 query，因此其冲突会影响所有后续层。

## 7. 资料冲突实例：`orphanType`

这个实例来自真实业务仓库，不是 verifier Prompt 中临时推断的冲突。

### 7.1 字段枚举

`field_enums_args.yaml:114-118`：

```text
orphanType:
  - 在职有效客户
  - 纯存续单客户
  - 非纯存续单客户
```

它证明当前 Parser 配置允许这三个候选值，但不能说明“孤儿单”应该对应其中哪一个。

### 7.2 字段定义

`field_definitions_args.yaml:578-596`：

```text
当前口径：
孤儿单 = 在职有效客户
有存续单 = 纯存续单客户
非存续单 = 非纯存续单客户

示例：
“孤儿单客户”
→ orphanType MATCH 在职有效客户
```

该资料明确声明“孤儿单”对应“在职有效客户”。

### 7.3 值映射

`value_mappings_args.yaml:75-83`：

```text
孤儿单客户 → 纯存续单客户
孤儿单     → 纯存续单客户
```

该资料明确声明“孤儿单”对应“纯存续单客户”。

### 7.4 当前实现如何消费

`FieldRegistry.normalize_query()` 在 `QueryRouter` 进入 Level 1/2/4 前执行。它读取 `value_mappings_args.yaml` 并对 query 做别名替换。

所以当前实现链路是：

```text
用户输入“孤儿单客户”
        ↓ value_mappings 预归一化
“纯存续单客户”
        ↓ Level 2 枚举规则
orphanType = 纯存续单客户
```

这可以证明：

> 当前实现行为倾向于输出 `纯存续单客户`。

这不能证明：

> 业务正式口径一定是 `纯存续单客户`。

### 7.5 Authority 结论

```text
问题一：
当前 Parser 实际如何处理“孤儿单”？

状态：
resolved

结论：
当前 value_mappings 在分层解析前将其改写为“纯存续单客户”，
后续 Level 2 使用该值生成 orphanType 条件。

依据：
value_mappings_args.yaml
field_registry.py
query_router.py
enhanced_rules_args.yaml
```

```text
问题二：
“孤儿单”的正式业务含义应当是“在职有效客户”
还是“纯存续单客户”？

状态：
unresolved

原因：
真实业务仓库中的两份当前运行资料直接冲突；
两个目标值都存在于当前枚举配置；
当前没有受治理业务术语表、配置生成来源或业务审批记录；
当前也没有下游客户集合证据证明哪种映射符合正式业务含义。

需要补充：
1. `orphanType` 的正式业务定义；
2. 字段定义和值映射的产生及维护关系；
3. 哪份资料由业务方批准并处于生效状态；
4. 必要时提供可区分两种客户集合的下游查询结果。
```

这里代码链只能证明当前行为，不能替代业务 Authority。外部业务定义或下游客户集合才有能力解除该 unresolved。

## 8. 跨资料结论

### 8.1 已经能够确认

| 结论 | 状态 | 主要依据 |
|---|---|---|
| 当前公开 API 的主职责是自然语言解析，不直接搜索客户 | resolved | 当前 FastAPI 路由与 API 实现 |
| 当前 Parser 的本地 Condition 数据形状 | resolved | `models/schemas.py` |
| 字段定义、枚举、值映射和增强规则被哪些运行模块消费 | resolved | 配置加载与运行代码 |
| Level 3 当前未进入运行主链 | resolved | `query_router.py` |
| `orphanType` 的两份当前业务配置存在直接冲突 | resolved | 字段定义与值映射 |
| 当前实现会优先受到 value mapping 预归一化影响 | resolved | `field_registry.py` 与 `query_router.py` |

### 8.2 当前不能确认

| 结论 | 状态 | 缺失证据 |
|---|---|---|
| 下游实际支持的字段全集 | unresolved | 下游正式字段契约或 mapping |
| 下游实际支持的枚举全集 | unresolved | 下游正式枚举或数据聚合 |
| 每个 operator 的真实搜索语义 | unresolved | provider-owned 接口/查询规则 |
| Parser 条件能否搜出正确客户集合 | unresolved | 固定数据快照和客户结果证据 |
| 两种查询形式是否业务等价 | unresolved | 同一快照上的双查询结果或正式规则 |
| `orphanType` 的正式业务语义 | unresolved | 业务术语表、审批或下游结果 |
| SearchService 是否仍属于计划启用的正式链路 | unresolved | 产品/架构确认和可达接口 |

## 9. 资料可靠性边界

### 外部业务依赖

下游服务正式契约、客户数据库 mapping、受治理字段/枚举和真实客户集合，是最有能力约束最终业务结果的证据。

当前尚未取得这些资料，因此不能假装端到端正确性已经可评。

### 业务配置

当前业务配置对 Parser 实际行为有直接影响，能够证明“当前系统如何做”。如果能进一步证明配置来自下游导出或业务审批，它才可能成为正式 Authority。

### 内部实现

内部实现用于还原：

- 哪份配置被消费；
- 输入如何转换；
- 哪一步导致当前输出；
- 资料冲突最终如何影响当前行为。

内部实现不能单独证明业务含义正确。

### 历史文档和测试

历史文档和测试可以发现设计意图和退化，但不能覆盖当前代码、当前配置或下游正式事实。

## 10. 下一步补证

### P0：下游正式契约

取得 `/api/v1/search/customer` 的：

- provider-owned OpenAPI、IDL、接口文档或源码；
- 当前部署 revision；
- 请求、响应和错误 schema；
- operator 的正式语义；
- 字段、枚举和嵌套对象定义。

### P0：客户结果验证

取得以下至少一种能力：

- 脱敏固定数据快照；
- 由业务方维护的 query → expected customer IDs；
- 同一快照的双查询结果比较；
- 只读 ES mapping、aggregation 和查询工具。

### P0：业务资料治理

对字段定义、枚举和值映射分别确认：

- 原始来源；
- 维护主体；
- 生成方式；
- 审批和生效方式；
- 更新频率；
- 覆盖和废弃关系。

### P1：确定现行产品边界

确认：

- 当前产品是否只交付 Parser；
- 下游客户搜索由调用方完成，还是应该由本服务完成；
- `SearchService` 和 `SearchAPIClient` 是待启用能力、历史遗留，还是正式但未接路由的模块。

## 11. 报告最终结论

当前真实业务系统调查已经能够回答：

```text
Parser 当前读取哪些业务资料；
资料如何进入 Level 1/2/4；
输入如何转成结构化条件；
当前实现实际会选择什么；
哪些当前业务配置彼此冲突。
```

当前调查仍然不能回答：

```text
下游数据库的正式字段和值域是什么；
某个业务词的正式业务定义是什么；
Parser 输出能否在真实数据上搜出正确客户；
不同查询形式是否得到相同客户集合。
```

所以 Authority 的合理边界是：

> 当前业务源码和配置可以确定当前 Parser 行为；  
> 外部业务定义和下游结果证据缺失时，不能把当前实现行为提升为正式业务正确性。

