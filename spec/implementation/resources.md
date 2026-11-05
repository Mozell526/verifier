# 资源与引用：实现记录

需求 `demand/draft-20261104/resources-pilot.md`（2026-11-04 确认）；算法 `spec/alg/resources.md`（同日确认）。

## 1. P1 离线复核（2026-11-04）

### 1.1 新增（现有代码、配置、提示词、校验都没改；新代码只被测试与离线脚本引用）

| 位置 | 内容 |
|---|---|
| `impl/core/resources/spec.py` | 地址 `Address`（解析、上一级；不带 `#`）、JSON Pointer 拼接与拆分（内部记位置用）、`Block`（MCP `Resource` 描述 + 正文）、`_meta` 前缀 `local.verifier/` |
| `impl/core/resources/text.py` | `render`：与 `dump` 逐字一致的规范序列化 + 区间对照表；`normalize_map` / `find_all` / `closest`：带下标映射的宽容比对；`smallest`：包含区间的最小节点 |
| `impl/core/resources/types/record_set.py` | 记录集：`text`、`templates`（字段模板 `{+record}/fields/{field}`）、`resolve`、`slice`、`read`（返回 MCP `TextResourceContents`）、`locate`、`extract`、`role`（结构化 `Role`） |
| `impl/core/resources/mount.py` | `ResourceTable`：`mount` 建 MCP 描述（校验 RFC 3986、唯一、直接资源不互为上下级）、`get`、`part`（地址 → 块 + 节点）、`list`（= resources/list）、`templates`（= resources/templates/list）、`read`（= resources/read：直接 / 模板 / 自动生成的目录资源 `inode/directory`） |
| `impl/core/resources/cite.py` | 公共核对：资源存在 → 读过 → 在引用范围内 → 找得到即过；只收完整地址；返回各处命中（节点、规范文本上的区间）与角色；不过给原因与提示 |
| `impl/projects/llm_probe_loop/business_trace/providers/langfuse.py` | provider 约定加 `mount(dossier, table)`：目录标签取自正文，角色表按 `links.TYPE_AXES` 分轴，放 `_meta` |
| `tests/test_resources_text.py`、`test_resources_cite.py`、`test_langfuse_mount.py` | 20 个用例，全过 |
| `report/resources-pilot-20261104/recheck.py`、`README.md` | 复核脚本与结果 |

### 1.2 与 spec 的出入（已在 spec 里注明"实现时修订"）

- 挂载收的是按 case 建的案卷而不是单份快照，实现放在 provider 模块（案卷把多轮快照合起来建、编号带 `turnN/` 前缀，单份快照对不上）。
- 宽容规则加了中英文引号归一（16 条引用只差在弯引号）。

### 1.3 按 MCP 资源标准修订（2026-11-04，审查后，用户确认）

审查（check / Bussiness / aihacking）发现的标准问题，改法都以 MCP 资源标准为准（spec/alg §0）：

| # | 问题 | 改法 |
|---|---|---|
| C1 | 挂载直接拿 `link_type` 当轴名（现在两者恰好一对一同名） | 改查 `links.TYPE_AXES`，与过程轴核对同一张表 |
| C2 | `outline` 没被用、没测试，签名与 spec 不一致；列目录本不是类型能做的事（类型拿不到资源表） | 删 `RecordSet.outline` 与 `ResourceTable.children`；列目录改为读目录资源，`read` 返回 MCP 结构，均补测试 |
| C3 | `meta` 混了目录标签与记录属性，和正文重复——标准没定清 | 资源 = MCP 描述 + 正文：能引的全在正文；目录标签放描述标准字段；类型名、角色表放 `_meta`。原 `meta`、`params` 删掉 |
| O1 | 框架 `cite` 默认补 `trace://`、转裸编号，把项目约定写进了框架 | `cite` 只收完整地址，转换放调用方（P1 是复核脚本） |
| O2 | spec 的类型接口写"传地址"，类型却拿不到资源表 | 类型接口改为收一块资源；按地址取与列目录归资源表 |
| O3 | `role` 返回拼好的中文串，参数键叫"轴"（项目概念） | 返回结构化 `Role`；参数键改"视角"，中文标签由复核脚本转；"元信息"改称"属性" |

验证：改前改后各跑一遍复核，910 条 × 两种口径的判定、节点、区间、seen_only、命中各处逐条比对，**0 条不同**（只有角色标签"元信息"改名"属性"）。

### 1.4 结果（详见 `report/resources-pilot-20261104/README.md`）

910 条过程轴引用（§1.8 之后的口径）：误拒消掉 102 条（宽松口径；严格 81 条），真错误 2 条仍被拒；原来没拒的 806 条里只拦深层值没展开的 2 条，另有 166 条"跨字段多处"单列待使用方判（去重占位由复核脚本还原后 28 条全过，见 §1.7）。

### 1.5 推广前必做

- **C4 宽容规则收成一套**：现在有四份——`axis_loop/text.py` 的 `_normalize`、过程轴核对（另加弯引号）、说法轴 `claims/checks.py`（`_plain` + 引号表）、`resources/text.py`（`_normalize` 的带下标版 + 说法轴引号表）。P1 不动现有三份；推广时只留 `resources/text.py` 一份，其余改为引用它。
- 地址里加 case / run 编号：真当 MCP 服务对外提供时需要（2026-07-28 版要求列表不随连接变）；离线一张表一个 case 不需要。

### 1.6 待定

- "一条引用够不够支撑结论"（④ 业务使用方）：引用写在整条记录这一级、命中好几个字段时够不够，P2 定。
- 现有展示的两个问题（与试点无关）：深层值没展开成原文（约 5% 读回的记录）；同一条记录两种渲染（本轴材料与 `case.trace`）。

### 1.7 地址写到字段；去重归调用方（2026-11-04，用户确认；"写到字段"的做法已被 §1.8 取代）

| 位置 | 改动 |
|---|---|
| `types/record_set.py` `locate` | 加 `pointer`：只在该节点里找（对象成员连键名算），这份看到的文本里没有该节点返回 None |
| `cite.py` | 地址带块内位置时按节点找；各份看到的文本里都没有该节点 → `no_node`；`not_found` / `ambiguous` 回带完整地址 |
| `tests/test_resources_cite.py` | 加 3 个：写到字段收窄、`no_node` 与找不到时提示原文所在节点、同节点重复仍对上多处；共 20 个，全过 |
| `report/…/recheck.py` | 去重是上游展示层的事、资源层不管：复核脚本算"看到过"时把"〔同 X 里已给过的那段，N 字〕"还原——取这一块正文同一位置的原文、且该原文在 X 看到的某份里出现过才还原 |

复核重跑：原 28 条去重占位"找不到"全过（角色按被引这一块：输出端 24、输入端 4）；1 条原通过的因还原多出一处变对上多处；其余判定不变。过程轴现在的提交写不了块内位置，所以这批数据里没有写到字段的引用；P2 要改提交格式与提示词，动之前另报。

### 1.8 直接资源 + 模板资源；去掉 `#` 与"只能对上一处"（2026-11-04，用户确认）

起因：MCP 里能单独读、单独引的最小单位是一个 URI。`#` 后面不是资源（RFC 6901 明说 `application/json` 的片段不是 JSON Pointer），按 MCP 读到的仍是整条记录。MCP 的标准做法是两种资源：基本单位逐条列出（直接资源），更细的按地址形状声明、读时现取（模板资源，RFC 6570），官方示例服务、文件类服务都这么做。

分工（spec/alg §0.1）：资源类型按数据长相定义、放在资源层，langfuse 与 agno 建成案卷后记录长相相同，共用记录集；信息源只写挂载。

| 位置 | 改动 |
|---|---|
| `spec.py` | `Address` 去掉块内位置，带 `#` 的地址不收 |
| `types/record_set.py` | 加 `templates`（`{scheme}://{+record}/fields/{field}`）、`resolve`（以最后一个 `/fields/` 为界拆）、`slice`（该节点在整条记录规范文本里那一段）；`read` 可读字段；`locate` 的范围改为地址所指的资源；`Role` 可排序 |
| `mount.py` | 加 `part`、`templates`；`read` 认模板地址（交给类型 `resolve`，所属块须已挂且类型一致）；不存在报"资源不存在" |
| `cite.py` | 资源是最小引用单位：找到即过，不再判"对上多处"（`ambiguous`、`no_node` 删掉）；结果改为各处命中 `regions` + 角色 `roles` |
| `tests/test_resources_cite.py` | 改为：模板声明、读字段资源（文本与整条记录里那段一致）、读不存在的字段报错、记录级命中两端照过并报两种角色、字段级只落一端、同一资源里重复全过；共 20 个，全过 |
| `report/…/recheck.py` | 通过的分三档：一处 / 同一字段多处 / 跨字段多处（需使用方判） |
| `providers/langfuse.py` | 不改 |

复核重跑与改前逐条比对：原来通过的 643 条（宽松；严格 629）节点、角色、区间全部不变；原来"对上多处"的 263 条（宽松）全部变成通过，命中节点集合与原来一致——同一字段多处 90、跨字段多处 173（其中原来没拒的 166）；拒的不变。过程轴现在的引用都写在记录级，没有字段级引用；字段级的效果要 P2 改提交格式后才看得到。
