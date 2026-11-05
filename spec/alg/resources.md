# 资源与引用：试点算法（P1 离线复核）

> 状态：2026-11-04 起草，同日用户确认；同日两次修订（用户确认）：按 MCP 资源标准对齐数据结构；粒度改为"直接资源 + 模板资源"、去掉 `#` 块内位置与"只能对上一处"。需求：`demand/draft-20261104/resources-pilot.md`（同日确认）。
> 本文只写 P1 用到的部分：一种资源类型（记录集）、一个信息源（langfuse）、一类引用方（过程六轴实际）。现有代码、配置、提示词、校验都不改；新代码不被现有代码引用。

## 0. 角色分工与 MCP 对照

### 0.1 四个角色

| 角色 | 代码 | 管什么 |
|---|---|---|
| ① 信息源 | 登记 `eval_axes/sources/registry.py`；trace 类实现 `business_trace/providers/` | 数据从哪来；**挂载**：采回了哪些记录、每条挂成什么资源（地址、目录标签、类型参数） |
| ② 资源层 | `impl/core/resources/` | 规范（两种资源形式、资源表、类型接口）；**资源类型**（按数据长相定义）；通用工具（规范文本与区间、宽容比对、引用核对） |
| ③ 框架使用方 | `impl/core/axis_loop/` | 给模型看什么、模型看到过什么（含去重展示及其还原） |
| ④ 业务使用方 | `process_axes.py` 等各轴 | 能引哪些资源（白名单）；一条引用够不够支撑结论 |

资源类型按**数据长相**定义，不按数据从哪个信息源来：trace 信息源（langfuse、agno）建成案卷后的记录长相相同，共用记录集类型，各自只写挂载。以后有长相不同的数据再加类型。

### 0.2 与 MCP 的对照

数据结构照 MCP 2026-07-28 版（`server/resources`）；代码用已装的 `mcp` 1.12.4 的 `mcp.types`（协议版本 2025-06-18，这几个结构的字段与 2026-07-28 相同；不升级）。

| 照 MCP 标准 | 我们的扩展 / 自定（MCP 不管） |
|---|---|
| 地址 = `uri`（RFC 3986，自定义前缀） | 地址怎么起、粒度怎么分（MCP 交给提供方） |
| 两种资源：直接资源（`resources/list` 列出）、模板资源（`resources/templates/list` 声明 RFC 6570 地址形状，读时现取）；读法一样（`resources/read`） | 模板地址怎么拆回变量（RFC 6570 只定义"填变量 → 地址"）、读出什么内容；上下级关系（MCP 不认为子路径是上级的一部分） |
| 描述 `Resource{uri, name, title, description, mimeType, size, _meta}`；模板 `ResourceTemplate{uriTemplate, name, title, description, mimeType}`；内容 `TextResourceContents{uri, mimeType, text}` | 规范文本怎么生成（`render`）、模板资源的文本 = 所属那一块规范文本里的那一段（`slice`）、区间对照表 |
| `_meta` 放实现方附加信息，键名带前缀 | 类型名、类型参数（如记录集的角色表）放 `_meta`，前缀 `local.verifier/` |
| 资源不存在是错误，不返回空内容 | 引用核对、角色、"看到过"、引用范围（§5、§6） |

P1 不做：起 MCP 服务、订阅与变更通知、模板变量补全。真当 MCP 服务对外提供时，2026-07-28 版要求列表不随连接变，地址里须带 case / run 编号（现在一张资源表只装一个 case，地址里没有）。

## 1. 地址与两种资源

```
<前缀>://<路径>
```

- 地址就是 MCP 资源的 `uri`，不带 `#`。前缀是挂载点所属的数据类别，P1 只有 `trace`；路径是层级，`/` 分隔。挂载时校验地址合 RFC 3986（被 URI 解析改写的地址不收）。
- **直接资源**：信息源挂载时逐条登记，`resources/list` 列得到。langfuse 的一条记录 = 一个直接资源，路径就是案卷里的记录编号：`trace://turn1/records/observations/15`。直接资源之间不能互为上下级。
- **模板资源**：资源类型声明地址形状，不逐条登记，读时现取。记录集的模板是 `trace://{+record}/fields/{field}`：`trace://turn1/records/observations/15/fields/output` = 这条记录的 output 字段。P1 只做这一层；更深的（如 `{/path*}`）以后需要再加，其他层不动。
- **目录资源**：直接资源的每个上级路径（如 `trace://turn1/records/observations`）由资源表自动生成，`mimeType = inode/directory`，读它返回下一级各项的描述。不能引用。
- JSON Pointer（RFC 6901）只在内部用来记一块正文里节点的位置，不出现在地址里。

## 2. 资源：描述 + 正文

一个直接资源 = **描述**（MCP `Resource`）+ **正文**（body）。字段放哪里只看一条：

| 放在 | 放什么 | 能不能引 | langfuse |
|---|---|---|---|
| 正文 | 模型能读、能引的全部内容；读取时序列化成内容的 `text` | 能 | `record_body` 的结果：记录属性（`name`、`kind`、`observation_type`、`outcome`、`parent_ref`…）+ `fields` |
| 描述的标准字段 | 目录标签：`name`（程序用标识）、`title`、`description`、`mimeType`、`size`（规范文本字节数） | 不能 | `name` = 记录编号，`title` = 步骤名，`description` = 类型 · 观测类型 · 结果 |
| 描述的 `_meta` | 只给程序用的：资源类型名、类型参数 | 不能 | `local.verifier/type = record_set`、`local.verifier/roles`（§3） |

目录标签取自正文，只用来列目录，不作证据；证据只有正文一份。

**规范文本** = `dump(body)`（`impl/core/axis_loop/text.py` 的 `dump`：`json.dumps(ensure_ascii=False, sort_keys=True)`），即读直接资源返回的 `text`，`mimeType = application/json`。同一份 body 每次得到同一串文本；不另存，读时现算。

**区间对照表**：生成规范文本时同时记下每个 JSON 节点在文本里的 `[start, end)`。对象成员记"键 + 冒号 + 值"整段，值另记值本身的区间。序列化器与 `json.dumps(ensure_ascii=False, sort_keys=True)` 逐字一致（测试校验）。

**模板资源的文本** = 所属那一块规范文本里该节点（值）那一段，一字不差（`sort_keys` + 固定分隔符下，子节点单独序列化与它在整块里那段相同）。所以模型读整条记录还是读一个字段，引的是同一份原文。

字符串值本身是 JSON 文本时（如 MCP 返回、`output` 里的 JSON 串），P1 不展开内层结构。

## 3. 资源类型：记录集

框架通用类型（`impl/core/resources/types/record_set.py`），按长相定义：一条记录是一个 JSON 对象，`fields` 下是字段（`{名字: {status, value, …}}`），其余键是记录属性。

挂载参数（放 `_meta`）：

| 键 | 含义 | langfuse 取值 |
|---|---|---|
| `local.verifier/roles` | `{视角: {字段名: [input / output]}}`：这一块的哪些字段在该视角下是环节的输入端 / 输出端；可多值 | 案卷环节表 `links[].input / output` 里的 `{ref, field}`；视角 = 轴，环节类型 → 轴用 `links.TYPE_AXES` |

类型接口（每种类型都实现）：

| 方法 | 输出 |
|---|---|
| `text(body)` | 规范文本 |
| `templates(scheme)` | 本类型声明的模板（MCP `ResourceTemplate`）。记录集：`{scheme}://{+record}/fields/{field}` |
| `resolve(uri)` | 模板地址 → (所属那一块的地址, 块里的节点)；不是本类型的模板地址返回空。记录集：以最后一个 `/fields/` 为界拆，节点 = `/fields/<字段名>` |
| `slice(body, node)` | 该节点在规范文本里的那一段；没有该节点返回空 |
| `read(block, node?, uri?)` | MCP `TextResourceContents`：不给节点读整块，给了读该节点那一段；没有该节点报"资源不存在" |
| `locate(block, quote, seen?, node?)` | 摘句在资源里的全部命中：每条 `{start, end, node}`（node = 包含它的最小节点）；给了"模型实际看到的这一块"就在那份里找；给了节点只在该节点里找；按 §6 的宽容规则比对 |
| `extract(block, start, end)` | 规范文本上这段区间的原文 |
| `role(block, node, view?)` | 结构化角色 `{part: block / attribute / field, field, ends}`；给了视角按该视角的角色表判端点，不给则合并各视角。中文标签由使用方展示时转换 |

## 4. 挂载与读取

框架接口（`impl/core/resources/mount.py`）：

```python
class ResourceTable:                                   # 一个 case 一张
    def mount(uri, type, body, *, name, title=None, description=None, meta=None) -> Block   # 直接资源
    def get(uri) -> Block | None                       # 直接资源
    def part(uri) -> (Block, node) | None              # 地址所指的资源：直接资源 → (块, "")；模板资源 → (所属块, 节点)
    def list() -> list[Resource]                       # = resources/list
    def templates() -> list[ResourceTemplate]          # = resources/templates/list：表里用到的类型各自声明的模板
    def read(uri) -> ReadResourceResult                # = resources/read：直接资源、模板资源、目录资源
```

- `mount`：信息源给地址、类型、正文与目录标签；`mimeType`、`size` 由类型算，类型名写进 `_meta`。同一地址只能挂一次；直接资源不能互为上下级。
- `read` / `part` 遇到不是直接资源的地址，交给各类型 `resolve`，拆出的所属块须是已挂的、且类型就是它。读不存在的地址报"资源不存在"，不返回空内容。

**信息源实现挂载**：provider 约定加一个函数，与 `collect`、`open_reader` 并列：

```python
def mount(dossier, table) -> None         # 对冻结的数据做，不连外部
```

langfuse：`providers/langfuse.py` 的 `mount` 收与内置材料 `case.trace` 同一份按 case 建的案卷（`build_dossier`），只挂 Langfuse 采回的那几轮（`sources[].recorder`），每条记录挂一个记录集直接资源（§2 的描述、§3 的参数，输入端 / 输出端取自同一份 `build_links`）。字段级资源不用挂，由记录集的模板负责。不改 reader、dossier 现有方法。

（2026-11-04 实现时修订：原写 `mount(snapshot, table)`、由 `LangfuseReader` 实现；案卷是按 case 把多轮快照合起来建的、记录编号带 `turnN/` 前缀，单份快照对不上编号与正文，故改为收案卷、实现放 provider 模块。）

P1 挂载时机只有一个：离线脚本对每个 case 的快照调一次。运行时的挂载时机 P1 不接；到时工具返回里的资源按 MCP 写成 `resource_link`（只给地址）或嵌入资源（带内容），推送里内联的材料即嵌入资源。

## 5. 使用方各管什么

- **③ 框架使用方**：给 `cite` 传"模型看到过什么"（`seen`）。去重等展示处理由它在算 `seen` 时还原（§7.2），资源层不知道去重。
- **④ 业务使用方**：引用范围（白名单），P1 两种口径各算一次（需求 §5 ⟡）：
  - **严格**：只能引本轴材料里的记录 = trace_analysis 结果里 `views[axis=本轴].full.records` 的编号（即现有核对的范围）。
  - **宽松**：只能引这次提交所在上下文里此前读回过的记录（不论来自哪个轴的材料）。
- **④ 业务使用方**：一条引用够不够支撑结论（例如"返回的对"要求引用落在输出端；引用写在整条记录这一级、命中输入端与输出端时够不够）。资源层只如实报出命中各处与角色，不判。P1 不判，复核结果里单列（§7.4）。

## 6. 引用核对（公共入口，`impl/core/resources/cite.py`）

输入：`table`、`seen`（这次提交之前模型实际看到的各块文本，§7.2）、`scope`（引用范围）、`view`（视角）、一条引用 `{uri, quote}`。

**资源是最小引用单位**：原文在地址所指的资源里出现即过，出现几处都算过。依次判，第一个不过即返回原因：

1. **资源存在**：只收完整地址，引用方自己把写法转成地址（过程轴现写法 `turn1/records/observations/15` → `trace://turn1/records/observations/15`，P1 由复核脚本转）；`table.part` 能取到，模板资源的节点在这一块正文里存在。否则 `no_address`。
2. **读过**：`seen` 里有所属那一块。否则 `not_seen`。
3. **在引用范围内**：否则 `out_of_scope`。
4. **找得到**：在 `seen` 里这一块的各份文本中、地址所指的范围内 `locate`。找不到 → `not_found`，附提示：这一块里与摘句最接近的一段（`difflib` 找最长公共片段所在节点），只提示、不放行。
5. 通过：返回各处命中 `regions`（每处 `{node, start, end, seen_only}`）与各处的角色 `roles`（去重、排序）。同一位置在几份看到的文本里重复出现算一处（按 node + 节点内偏移去重）。`start / end` 换算到这一块规范文本（§2）上：同一 node 在看到的文本与规范文本里内容相同时，用 node 起点 + 节点内偏移；不同（看到的是预览）时保留看到的文本里的区间，并标 `seen_only`。

**宽容规则**：沿用 `text.py` 的 `_normalize`（去空白、反斜杠、转义的换行制表），再把中英文各式引号归一（同说法轴 `claims/checks.py` 的引号表），实现成"带下标映射"的版本，比对在规范化文本上做，命中区间映射回原文下标。推广时要收成全系统一套（P1 期间与现有几套并存，见 `spec/implementation/resources.md` §1.5）。（2026-11-04 实现时修订：加引号归一。现过程轴核对本就把弯引号当直引号，P1 里 16 条引用只差在弯引号（原收下 10、原拒 6）。）

## 7. P1 复核方法

### 7.1 数据（只读拷贝到 scratchpad）

- 8037（`inst-5ac0245dc11a4220`）`latest_runs.sqlite3`：22 条 run，trace 快照在 `run.trace.turn_records[i].project_fields.business_trace`，trace_analysis 结果在 `run.eval_axes.results`。
- 8037 context_store 里这 22 条 run 的调用记录（每次模型请求的 messages 与回复）。

### 7.2 "模型实际看到的文本"

对每次过程轴 submit：取产生这次 submit 的那次请求的输入 messages（即此前全部上下文），收集其中 `read_material` / `recall` 返回里的每条记录 `{id, content}`；同一记录多次读回的各份都算看到过，每份的文本 = `dump(content)`。工具返回里的"〔预览…〕"照原样算进看到的文本（预览之外的不算看到）。"〔同 X 里已给过的那段，N 字〕"是上游展示层的去重，资源层不管：由调用方（P1 是复核脚本）还原——占位处取这一块正文同一位置的原文，且该原文在 X 看到的某份里出现过，才算看到过（2026-11-04 用户定）。

### 7.3 逐条复核

范围：22 条里过程六轴（实际）的全部 submit（被收下的与被拒的）里 `actual[].quotes`、`unexpected[].quotes` 的每条引用。

每条记：现规则结果（收下的 submit 里的引用 = 过；被拒的按拒绝原因对上具体那条）、新规则在严格 / 宽松两种口径下的结果与原因、命中各处的节点与角色。

### 7.4 结果表（`report/resources-pilot-20261104/README.md`）

1. 现规则 × 新规则（两种口径）的交叉表：误拒消掉多少、新拒多少、两边都拒多少。
2. 新规则拒的按原因分布；通过的分三档：一处 / 同一字段多处 / 跨字段多处——跨字段多处单列为"一条引用够不够需使用方判"，不直接算作该过。
3. 原来该拒的约 12 处真错误（`demand` 草稿 §1）是否全部仍被拒。
4. 抽查：新规则新拒的随机 20 条，逐条写人工结论（确实该拦 / 误伤）。
5. 那 3 处"原文在本轴字段里也被拒"的原因。

## 8. 文件

| 位置 | 内容 |
|---|---|
| `impl/core/resources/spec.py` | 地址解析（不带 `#`）、`Block`（MCP 描述 + 正文）、`_meta` 前缀 |
| `impl/core/resources/text.py` | 带区间对照表的规范序列化、带下标映射的规范化比对 |
| `impl/core/resources/types/record_set.py` | 记录集类型：直接资源 + 字段模板 |
| `impl/core/resources/mount.py` | ResourceTable：挂载、读（直接 / 模板 / 目录资源）、列表、模板列表 |
| `impl/core/resources/cite.py` | 公共核对 |
| `impl/projects/llm_probe_loop/business_trace/providers/langfuse.py` | provider 约定加 `mount`（实现也在这里） |
| `tests/test_resources_text.py`、`test_resources_cite.py`（含记录集的找原文与角色）、`test_langfuse_mount.py` | 单元测试 |
| `report/resources-pilot-20261104/recheck.py`、`README.md` | P1 复核脚本与结果 |

## 9. P1 不做

运行时挂载时机、给模型用的资源工具、带地址的展示方式、其他类型与信息源（agno 的挂载）、字段以下更深的模板、提交格式与提示词的改动、内层 JSON 串的展开、"一条引用够不够支撑结论"的判断。
