# 评测轴任务化（axis loop）方案

> 状态：草案（2026-10-21），对着 `demand/axis_loop.md` 打磨，已经过两轮方案 grill（结论记在各节，标注"10-21 定"）。2026-10-22 按 dev 对比后的 grill 修订（标注"10-22 定"）：独立运行的轴、分发脚本、公共 loop 工具、去掉"轴自带子 loop"与带参数的内置材料、实施中的偏差回填。需求与本文冲突时以需求为准，回来修本文。
> 结论口径以 `demand/main_axis.md`、`expectations.md`、`claims.md`、`process_axes.md` 为准；本文只改"怎么组织、怎么执行"，不改"判什么"。
> 内核：`impl/core/tool_loop`（`spec/adapter/tool-loop-plan-20260922.md`），本文不改它的接口。
> 实施记录写在 `spec/implementation/axis_loop.md`（本文确认后再写）。
> 标 ⟡ 的条目待用户确认，或者需要试运行后再定。

# 第一章：方案

## 1. 总体

```text
轴定义存储（页面编辑）           材料注册表（代码里的字典）        信息源登记（MCP 实例）
  每个轴：配置 + 说明                case.* / scenario.* / axis.*       knowledge / trace
  轴自带子 loop：配置 + 说明         + result.<轴id>（由输出 schema 生成）
  可选上传：checks.py / synth.py
              │                              │                              │
              └──────────────┬───────────────┴──────────────────────────────┘
                             ▼
case ─► 加载：场景启用的轴 → 依赖、白名单、工具类别检查（fail fast）
                             ▼
        AxisLoop（一个 case 一个，搭在 ToolLoop 上）
          工具（从头到尾固定）：submit、mcp_call / mcp_read / mcp_find、recall、各启用轴的子 loop 工具
          hooks：
            start / post_batch  台账：谁出现、谁作废、跑程序任务 → 推送消息
            pre_tool            门禁（工具类别没解锁就拒）；submit 走验收流水线
            post_tool           给每个返回盖 call_id
            stop                所有已出现的任务都完成、没有作废待重交
                             ▼
        报告（与现有 build_report 同形）
```

- 任务机制与项目无关，放在 `impl/core/axis_loop/`。轴定义、材料注册表的项目部分、内置信息源由项目提供。
- 模型只做三件事：读推送来的任务；调工具（信息源、子 loop）；调 submit。顺序由模型自己定（需求 §3.2.6）。

## 2. 项目与代码落点（10-21 定）

### 2.1 新项目 `llm_probe_loop`

- 整体复制 `impl/projects/llm_probe/` 到 `impl/projects/llm_probe_loop/`。26 个文件里的 91 处 `impl.projects.llm_probe` 自引用、3 处写死的项目 id 批量改名。
- 原样保留，与 loop 无关的部分：跑业务（`live.py`、`live_schema.py`、`show_schema.py`、`adapter.py`、`mock.py`）、场景与资料（`capability.py`、`materials.yaml`、`schema/`）、trace 采集（`business_trace/` 的采集部分）、旧判官与归因（`need_judge.py`、`text_carrier.py`、`claims.py`、`attribute.py`、`tools.py`、`material_tools.py`）。
- 替换掉的部分：`eval_axes/`、`knowledge_loop/`、`process_loop/` 删除；`judge.py` 中调用评测的入口改为调用 axis loop。
- 数据：建项目时把 llm_probe 现有的场景预设、知识源登记拷一份快照到 `impl/data/llm_probe_loop/`。两边以后各自维护，不要求严格同源（10-21 用户定）。

### 2.2 不影响其他项目

- `service.py` 里 12 处 `project == "llm_probe"` 改成 `project in EVAL_AXES_PROJECTS`，其中 `EVAL_AXES_PROJECTS = {"llm_probe", "llm_probe_loop"}`。`from ..projects.llm_probe.xxx import` 改成按项目 id 取模块。
- 前端 13 处写死（`live.html` 3、`materials.html` 6、`summary.html` 2、`context.html` 1、`tool_loop_lab.html` 1）做同样的处理。
- `core/table_view.py` 里对 `llm_probe.eval_axes.registry` 的硬 import 改成按项目取。
- 不在集合里的项目，行为和现在完全一样。分出胜负后，集合缩回一个。

### 2.3 代码位置

| 位置 | 放什么 |
|---|---|
| `impl/core/axis_loop/` | 轴定义的加载与校验、材料表与白名单取值、台账、门禁、验收流水线、视图、标准校验库、子 loop 运行器、AxisLoop 组装、报告组装 |
| `impl/projects/llm_probe_loop/axis_loop.py` | 项目接入：从 RunTrace 构造 case；登记本项目的内置材料取值函数；出 `build_report` 同形报告 |
| `impl/data/llm_probe_loop/axis_definitions.json` | 轴定义存储（§3） |
| `impl/data/llm_probe_loop/axis_code/<轴id>/` | 上传的 `checks.py`、`synth.py`；子 loop 的放在 `axis_code/<轴id>/tools/<子loop id>/` |

## 3. 轴定义（全部是配置，10-21 定）

### 3.1 存储

- 所有轴的定义存成一个配置存储 `axis_definitions.json`，读写机制与 `capability_map.json` 相同（`capability_store` 那一套，保存时校验形状）。
- 说明正文（这个轴的"system prompt"）是其中一个文本字段，只写判法。
- 上传的代码放在 `axis_code/<轴>/` 下，三种固定插口（10-22 定）：`checks.py` 定义 `check(view)`，`synth.py` 定义 `synthesize(view)`，`dispatch.py` 定义 `dispatch(view)`；加载时检查名字与参数个数。公共 loop 工具的代码放在 `axis_code/shared/<工具>/`。

### 3.2 一个轴的字段

| 字段 | 意思 | 例（真实性） |
|---|---|---|
| `id`、`title` | 标识、显示名 | `truthfulness`、真实性 |
| `executor` | `model` 或 `program` | `model` |
| `run_mode` | `main`（缺省，主 loop 公共上下文里做）或 `isolated`（依赖满足时由程序启动独立子 loop，§6）（10-22 定） | `isolated` |
| `role` | `analysis`（中间产物，展示时不算评测结论）或 `evaluation`（缺省）（10-22 定） | `evaluation` |
| `depends` | `[{axis, hard}]` | `[{axis: claims, hard: true}]` |
| `trigger` | `{axis, verdict_in}`，只能引用硬依赖 | — |
| `instruction` | 说明正文：只写怎么判。`isolated` 时就是子 loop 的 system prompt 主体 | "判定回答里的每条说法是否属实……" |
| `materials` | 材料白名单（§4） | `["result.claims.claims[]"]` |
| `tool_categories` | 信息源类别 `[{category, required}]` | `[{category: knowledge, required: true}]` |
| `tools` | 选用的公共 loop 工具（§3.3），按名字 | `["search_knowledge"]` |
| `submit` | `once` 或 `per_item`；`per_item` 时写 `items_field` 与 `item_key` | `per_item` |
| `output` | 输出 JSON Schema，顶层字段用 `x-fill: model \| program` 标谁填 | 见 §12.1 |
| `checks` | 选用的标准校验，带参数（§7），可加 `on: item \| final` | `[{quote_in_call: {field: "basis[]", category: "subloop", on: "item"}}]` |

- `output` 必须包含 `verdict`、`reason` 两个字段，它们同样可以标程序填（需求 §3.3）。
- 存在程序填的字段就必须上传 `synth.py`；反过来没有就不能上传。上传了 `dispatch.py` 的轴必须是 `isolated`，并且必须有 `synth.py`（合并各份结果）。

### 3.3 公共 loop 工具的字段（10-22 定）

存放在存储的 `shared_tools` 里，任何轴（含独立运行的轴）在 `tools` 里按名字选用。它是 agentic 的：调用方的模型决定何时调、按 `params` 填参数。

| 字段 | 意思 | 例（search_knowledge） |
|---|---|---|
| `id` | 工具名 | `search_knowledge` |
| `description` | 给调用方看的工具说明 | "到场景知识源取证（只取证不判对错）……" |
| `instruction` | 它自己的说明正文 | 原 knowledge_loop 的查证规则 |
| `materials` | 材料白名单：只能是内置材料 | `["scenario.knowledge"]` |
| `params` | 调用方可写的参数（JSON Schema，每个参数必须写 description） | `items: [{item_id, text, context}]` |
| `tool_categories` | 它能用的信息源类别 | `[{category: knowledge, required: true}]` |
| `submit` / `items_field` / `item_key` | 同轴 | `per_item`、`items`、`item_id` |
| `output` | 输出 schema，不要求 verdict、reason | 每条 `status`、`citations`、`search_calls`、`note`、`gap`；`evidence`（程序填） |
| `checks` | 选用的标准校验 | 同原 `Checklist`，全部用标准校验表达 |

### 3.4 加载期校验（fail fast）

以下情况在场景保存时，或者加载时报错：
- 依赖成环、硬依赖没开、trigger 引用的不是硬依赖或枚举值不存在；
- `output` 缺 `verdict` / `reason`（仅限轴）；
- `fill` 与 `synth.py` 对不上；
- 白名单里的名字不在注册表里，或者字段投影 / 元素筛选的路径不在 schema 里，或者超出读取范围（§4.3）；
- `checks` 的名字未知或参数不对，或者 `of` / `field` 的路径不存在；
- `per_item` 没写 `items_field`；
- 必需的工具类别在场景里一个实例都没有；
- 公共 loop 工具的参数没写 description；选用了未定义的公共 loop 工具；
- `dispatch.py` 用在非 `isolated` 的轴上，或者没有配 `synth.py`。

## 4. 材料（10-21 定）

### 4.1 注册表

代码里维护一张字典：标准名 → `{schema, description, load(case)}`。

| 标准名 | 是什么 | 值的形状 | 取自 |
|---|---|---|---|
| `case.user_turns` | 每一轮用户原话（含历史） | `[{turn, text}]` | RunTrace |
| `case.requests` | 每一轮请求体 | `[{turn, body}]` | RunTrace |
| `case.deliveries` | 每一轮被测系统的回答 | `[{turn, text}]` | RunTrace |
| `case.business_status` | 业务调用是否正常返回 | `{ok, http_status, error}` | RunTrace |
| `scenario.capability` | 被测系统的能力描述 | 文本 | 场景登记 `capability` |
| `scenario.criterion` | 场景判准 | 文本 | 场景登记 `criterion` |
| `scenario.description` | 业务描述（其中的资料引用会被展开） | 文本 | 场景登记 `description` |
| `scenario.downstream` | 下游要求 | `[文本]` | 场景登记 `downstream` |
| `scenario.boundary` | 责任范围 | 文本 | 场景登记 `boundary`（`expand_boundary`） |
| `scenario.process_obligations` | 过程职责 | 按现有结构 | 场景登记 `process_obligations` |
| `axis.note` | 场景对当前这个轴写的描述 | 文本 | 场景登记 `axes[]` 中该轴的 description |
| `result.<轴id>` | 某个轴被接受后的完整结果 | 该轴的输出 schema | 运行中写入材料表 |

- `case.*`、`scenario.*`、`axis.*` 由项目接入登记取值函数；`result.*` 根据轴定义自动生成。
- 第二期加入 `case.trace_snapshot`。

### 4.2 白名单写法

```
"<标准名>"                                  取整个值
"<标准名>.<路径>"                           取一部分；路径写法沿用现有的 item_path：列表[].字段
"<标准名>.<路径>.{字段1, 字段2}"            再投影出几个字段
"<标准名>.<列表>[字段=值1,值2]…"            只取这个字段等于这些值的元素（10-22 定；分发脚本按它给每份子 loop 列选择）
```

内置材料不带参数，一个 case 一个值（10-22 定，撤掉 10-21 加的"带参数的内置材料"）。

### 4.3 读取范围

| 使用方 | 内置材料 | `result.*` |
|---|---|---|
| 轴（`main` 或 `isolated`） | 可以 | 只能读自己 `depends` 里的轴 |
| 分发出来的每份子 loop | 只能读分发脚本给它的那份选择 | 同上（选择不能超出所属轴的范围，框架检查） |
| 公共 loop 工具 | 可以 | 不可以；另有调用方传的参数 |
| 校验、合成、分发代码 | 与所属方相同 | 与所属方相同 |

软依赖没开时，对应的 `result.*` 为空，放进上下文时写明"未启用"。

### 4.4 呈现与引用

```
【scenario.criterion】
查询类场景：给出所问字段的值
【result.expectations.expectations[].{expectation_id, statement}】
[{"expectation_id":"E1","statement":"给出这张保单当前的退保金额"}, ...]
```

- 文本原样放入；结构化的值用 `json.dumps(ensure_ascii=False, sort_keys=True)` 序列化，保证同一份值每次的文本一样，可逐字引用。
- 引用材料：`{ref: "<标准名>[#轮次]", quote}`，quote 必须逐字出现在那一段的文本里。引用工具返回：`{ref: "<call_id>", quote}`。
- 程序直接把材料放进上下文，不提供读材料的工具（10-21 定）。第二期 trace 这种大材料，先给目录，正文用工具读，到时再定。

## 5. loop 协议

### 5.1 消息布局

```text
system   通用评测协议（固定）：你会陆续收到任务；按说明做；用 submit 交；被拒就按原因改了再交；
         引用写成 {ref, quote}；工具返回要到下一次回复才能引用……
user     case 头 + 初始就出现的任务（没有依赖的），每个任务一段：
         【任务 expectations】说明 + 它的材料（按白名单）+ 可用工具（含子 loop）及其用法 + 提交格式（模型填的那部分 schema）
assistant / tool …
user     （post_batch 推送）【新任务 …】 / 【作废 …】 / 【撤下 …】
```

- 推送永远是追加一条新的 user 消息，不改写旧消息（中转站只有"新起一轮"才稳定命中前缀缓存，见 `report/process-axes-compare-20261009/CACHE-FINDINGS.md`）。
- **工具列表从头到尾固定**（10-21 定）：`submit`、`recall(call_id)`、场景选用的信息源的工具（按信息源暴露为 `<信息源>__<工具>`，加框架统一的 `mcp_read`、`mcp_find`），加上 `main` 轴选用的公共 loop 工具。`isolated` 的轴不进主 loop，它的工具只在它自己的子 loop 里。工具定义排在请求的最前面，中途增减会让整个前缀缓存失效。这和 Claude Code 的 skill、延迟加载工具是同一种做法：固定一组通用工具，具体用法写进追加的消息里。某个信息源实例有哪些工具、怎么用，写在任务推送里。
- 门禁：某个信息源类别还没被已出现的任务带进来，或者某个公共 loop 工具还没有已出现的任务选用，调用就直接拒绝，并说明原因。

### 5.2 submit

```json
{"task_id": "fulfillment", "item_id": "E2", "payload": {...}}
```

- `item_id` 只在 `per_item` 的任务上出现：带它是交一个分项，不带是收尾。`once` 的任务不能带。
- 交给一个已完成的任务，就是修改它：走同样的验收，通过后按 §5.4 让下游作废。

### 5.3 验收流水线（pre_tool 内依次执行；任一步不过就拒，并回告这一步的全部原因）

```text
1. 任务存在且已出现；提交形状与 submit 方式相符（分项 id 在清单里、同一分项不重复交）
2. 用"模型填的那部分 schema"做 JSON Schema 校验（jsonschema 4.26，环境已装）；条件字段用 if/then 表达
3. 依次执行选用的标准校验（§7）
4. checks.py 的 check(view)
5. 通过 → 记为接受 → 有 synth 就执行 synthesize(view) → 完整结果再过一次完整 schema → 写入材料表 result.<id>
```

- 第 5 步合成出错，或结果不合 schema，属于评测器自己的 bug：直接中止整个 loop，记运行失败，不打回给模型（需求 §3.2.8）。
- 同一批里的多个 submit 各自独立验收（ToolLoop 的既有语义：同一批调用彼此看不见）。所以同一批里同时交上游和依赖它的下游，下游这一次会因为"任务未出现"被拒。这是对的。

### 5.4 台账（start / post_batch，全部由程序完成）

1. **作废**：本批被修改的任务，它所有已完成的传递下游都作废，回到"已出现、待重交"。
2. **出现**：依赖全部完成或不出现（软依赖没开视为满足），并且触发条件满足，就出现。
3. **撤下**：已出现但触发条件不再满足的，撤下，它交过的东西作废。
4. **程序任务**：依赖满足就当场合成；上游一变就重算。不推送给模型。
5. **独立运行的轴**（10-22 定）：依赖满足、触发成立就由程序启动它的子 loop（有 `dispatch.py` 就按分发起多份），被接受的结果直接记为这个轴的结果；上游一变就作废重跑。不推送给模型。
6. **推送**：`main` 轴里新出现、被作废、被撤下的，合成一条 user 消息。

"不出现"是确定的状态：对下游来说算作已完成，`result.<id>` 为空。

### 5.5 完成与失败

- completion_hook：所有已出现的任务都完成，并且没有作废待重交，返回 Done，否则返回 Continue 并列出还差什么。`ready_to_finish` 用同一个判断。
- 失败（整个 case 记运行失败，不出部分结论）：预算耗尽；`max_blocked` 用尽；合成 / 分发出错；独立运行的轴或公共 loop 工具失败（§6.3）；上下文压缩后仍然超限（§9）。失败时各轴不保留做了一半的输出，过程只留在 loop 记录里（10-22 定）。

## 6. 独立运行与公共 loop 工具（10-22 定，取代 10-21 的"子 loop"）

### 6.1 独立运行的轴

- 由台账启动（§5.4.5）：一个新的 ToolLoop，system = 通用子任务协议 + 这个轴的 `instruction`，第一条 user 消息 = 按白名单取出的材料 + 提交格式。主 loop 的模型不参与，不需要任何参数。
- 子 loop 里用同一套 submit、验收流水线、视图和标准校验；`task_id` 就是轴 id。被接受的收尾就是这个轴的结果，写进材料表 `result.<轴>`。
- 工具：`submit`、`recall`、它 `tool_categories` 对应的信息源工具、它 `tools` 选用的公共 loop 工具。
- 台账不在主 loop 的工具调用里，所以直接调 `ToolLoop.run(input, LoopContext(trace_id, stage=<主 stage>/<轴>))`，不用 `as_tool()`。

### 6.2 分发

```python
def dispatch(view) -> list[dict]:
    """view：这个轴白名单里的材料。返回每份子 loop 的材料选择，写法同 §4.2 白名单。"""
    return [{"id": "t1", "materials": ["case.requirements.sources[id=t1.user]"]}, ...]
```

- 不上传就只起一份，材料 = 这个轴的白名单。
- 每份子 loop 只看到它那份选择取出的材料；框架检查每个选择合法且不超出这个轴的读取范围，不合法算评测器出错（这个轴失败）。
- 各份按这个轴的输出 schema 提交、验收；框架把被接受的结果收成 `[{id, result}]`，作为 `view.parts` 交给这个轴的 `synth.py` 合并成最终结果。
- 第一期各份串行执行。

### 6.3 公共 loop 工具

- 选用它的轴（不论 `main` 还是 `isolated`）的模型调用它：`<工具名>(参数)`；框架新开一个 ToolLoop（每次调用一个，提交状态各自独立），system = 通用子任务协议 + 它的 `instruction`，材料按它的白名单取，加上参数。通过 `as_tool()` 嵌入调用方，继承 trace_id 与 stage。
- 被接受的结果作为这次工具调用的返回：`text` 加 `structured`；调用方用 `{ref: call_id}` 引用，代码从 `view.calls[].structured` 读。
- **嵌套只有一层**：独立运行的轴可以调公共 loop 工具；公共 loop 工具里不能再调公共 loop 工具。
- 失败（预算耗尽、一直过不了验收）：整个 case 记运行失败。调用次数与 token 计入全局预算。
- 子 loop（独立运行的轴、公共 loop 工具）同样开上下文归档（§9）。

## 7. 视图与标准校验

### 7.1 视图（check / synthesize / dispatch 的唯一输入，只读）

```python
@dataclass(frozen=True)
class TaskView:
    task_id: str
    own: Mapping            # 本次提交里模型填的部分；分条交收尾时含全部已接受分项
    materials: Mapping      # {标准名: 完整值}，只含白名单里出现的名字（10-21 实施时定：投影只决定给模型看多少，代码拿完整值）
    params: Mapping         # 仅公共 loop 工具：本次调用的参数
    calls: Sequence[CallView]  # 此前批次的调用：call_id, tool, category, args, batch, text, structured, is_error
    stage: str              # item（校验一个分项）/ final（收尾）
    parts: Sequence[Mapping]   # 仅有分发的轴的 synth：[{id, result}]，各份被接受的结果（10-22 定）
```

- 视图只包含白名单里的材料，代码拿不到白名单以外的东西（需求 §3.4.3）。
- 自定义代码的确定性靠测试保证：同一个视图连续跑两次，结果必须相同，不做沙箱（10-21 定）。

### 7.2 标准校验库

| 名字 | 种类 | 参数 | 说明 |
|---|---|---|---|
| （schema） | V1/V2 | — | 来自 output 定义，自动执行 |
| `covers` | V3 | `field`、`of` | `field` 取出的 id 集合与 `of` 指向的集合相等 |
| `refs_in` | V4 | `field`、`of` | `field` 取出的每个 id 都在 `of` 指向的集合里 |
| `quote_in_material` | V5 | `field`、`material` | 引文逐字出现在指定材料里 |
| `quote_in_call` | V5+V6 | `field`、`category?` | ref 是此前批次中没报错的调用（可限定类别），quote 逐字出现在它的 text 里 |
| `searched` | V6 | `field`、`category` | 列出的调用都是此前批次中没报错、属于该类别的调用，至少一个 |
| `from_call` | V4+V6 | `field`、`tool` | ref 指向一次已被接受的、指定子 loop 工具的调用 |

- `of` 用路径指向视图：`own.<路径>`、`params.<路径>`、或 `<标准名>.<路径>`（白名单里的材料）。
- 需要先算出来的集合（比如"没给到的期望"），由上游的合成程序算成一个程序填字段，下游直接引用。校验库里不加计算语言。
- 遇到新的通用形式，就往这张表里加一行（需求 §3.4.1）。

## 8. 信息源（MCP）

| 层 | 落在哪 | 内容 |
|---|---|---|
| 类型 | 代码：知识源 `es`、`mcp`；trace 源 `agno`、`langfuse`、`llmtracing`（第二期） | 怎么连、怎么读；外部一律经 MCP（ES 由评测器自动拉起本地 ES MCP server） |
| 全局登记 | 资料管理页：知识源登记（`knowledge_sources.json`）；trace 源登记（第二期新增，同一种页面） | 选类型、按类型填连接配置；凭据写成 `${VAR}`。一条登记拿来做什么由它的类型决定（10-22 定） |
| 场景选用 | 轴框描述里的 `{es://名/索引}`、`{mcp://名}`、`{material://项目/资料}` 引用（沿用现有写法）；trace 第二期按同样方式选用并填字段绑定 | 一个轴框里引用的就是这个轴挑的；场景选用 = 各轴框引用的并集 |

- 信息源工具按信息源暴露（`<信息源>__<工具>`，名字、说明、参数取自 MCP 服务本身）。一个信息源要加查询工具，加在它自己的 MCP 服务里（10-22 定）。
- 返回形状按 MCP：`content`、`structuredContent?`、`isError`。是否报错看 `isError`。
- ES：现有 `es_tools` 包成本地 stdio MCP server（`impl/projects/llm_probe_loop/mcp_servers/es/`），检索语义不变；直连与 `verify_quote` 回读删除（10-21 定）。
- 校验场景选没选某类信息源：按引用找到登记，按登记的类型判断，不搜描述文字（10-22 定）。

## 9. 上下文与成本

1. 上限：`axis_loop.context_limit_tokens`，可配置。每次请求前估算。
2. 到上限的 80% 时（可配置），把已完成任务的旧工具返回替换成 `"[已归档] call_id=c12，需要时用 recall(call_id) 重看"`。这和 Anthropic API 的 context editing（clear tool uses）是同一种做法。原文仍在调用记录里，校验和引用不受影响；`recall` 本身是一次新调用，返回的原文可以被引用。
3. 归档之后仍然超限：记运行失败，原因写明上下文超限（需求 §5.3）。
4. 归档会让缓存失效一次，所以只在接近上限时触发。

## 10. 预算

全局一份，进全局运行配置（10-22 定）：放在现有的可选节 `eval_axes` 下，`eval_axes.loop_llm_calls`、`loop_tool_calls`、`loop_seconds`、`loop_context_limit_tokens`、`loop_archive_ratio`，都有缺省值，现有 config.yaml 不用改。主 loop、独立运行的轴、公共 loop 工具共用一份计数。

## 11. 记录与报告

### 11.1 报告（与现有 `build_report` 同形）

```text
{ main_verdict, run_id, scenario_id, trace_id, case_id, axes, warnings,
  results: [ {type_id, status, output, summary, ...} ],     ← 每个轴一条，output = 完整结果
  route: "loop",
  loop: { status, reason, llm_calls, tool_calls, seconds, tokens, events: [...] } }
```

- 主轴结论：程序任务 `main_verdict` 的 synth 调用现有的 `main_verdict(results)`，函数不改。
- status 沿用 `succeeded` / `not_applicable`。没出现的写明"触发条件未满足"。loop 失败时全部记 `failed`，`main_verdict` 为 None。
- 前端 summary、live 不用改。`events` 第一期只放进报告 JSON，按任务的时间线视图放到第二期（10-21 定）。

### 11.2 事件记录

```text
{batch, kind: appear | submit | accept | reject | invalidate | withdraw | program | subloop | archive,
 task_id, item_id?, call_id?, reasons?}
```

- 每一步的模型请求已经由 LlmClient 写成 ContextRecord，挂在同一个 trace_id 下。子 loop 的请求用 `<父 stage>/<子loop id>` 作前缀（ToolLoop 嵌套的既有行为）。
- 判错时的定位路径：在 events 里找到那个轴最后一次 accept → 找到对应 batch 的模型请求 → 看当时的上下文。

## 12. 现有轴映射与分期

### 12.1 第一期：主轴（无 trace 场景，也就是评测集的范围）

| 轴 | 执行者 | run_mode | 依赖 | 材料 | 工具 | 代码 | verdict |
|---|---|---|---|---|---|---|---|
| `expectations` | 模型 | isolated | — | `case.requirements`（全部需求侧材料，每条标轮次） | — | `dispatch.py` 按轮切（每轮只选本轮及之前的原话、业务背景；最后一轮加判准）；`checks.py`（期望必须引本轮用户原话等）；`synth.py` 合并各轮、编号加轮次前缀 | 程序（complete / partial） |
| `blocking` | 模型 | isolated | expectations（硬） | `result.expectations.expectations[].{expectation_id, turn, about, statement, condition, ambiguity_group}` | — | `checks.py`（同一歧义组 blocking 一致） | 程序 |
| `claims` | 模型 | main | expectations（硬） | `case.final_output`、`case.user_turns` | — | `checks.py`（逐字与隔离规则） | 程序 |
| `truthfulness` | 模型 | isolated | claims（硬） | `result.claims.claims[]` | 信息源 knowledge；公共 loop 工具 `search_knowledge` | `checks.py`（依据的那次取证里有这一条；取证没找到只能判 unverifiable）；`synth.py` | 程序 |
| `fulfillment` | 模型 | main | expectations（硬）、blocking（硬）、truthfulness（软） | `case.deliveries`、`result.expectations`、`result.blocking`、`result.truthfulness.claims[].{…}` | — | `checks.py`（check_assessments）；`synth.py`（blocking 取自 `result.blocking`，整体状态派生） | 程序 |
| `main_verdict` | 程序 | — | fulfillment（硬）、truthfulness（软） | 二者的 `result.*` | — | `synth.py` 调现有 `main_verdict()` | 程序 |

- **交付第一次进主上下文**是 `claims` 出现时，此时期望已定（硬依赖）；`blocking`、`expectations` 是独立运行，材料里没有交付。
- **真实性**（10-22 定）：独立运行。子 loop 里的模型调 `search_knowledge` 取证（可以针对证据不够的几条再调，补查），拿证据逐条判；检索过程在最里层，判定看不到。证据原文只在真实性子 loop 的上下文里，主 loop 只经兑现的材料读到每条说法的结论。每条提交：`verdict`、`reason`、`basis`（`{ref: 那次 search_knowledge 调用, quote}`）、`evidence_call`、`gap`。
- **错误码归为运行失败**（10-22 定，需求 `main_axis.md` §3.6）：场景配置里事先维护错误码 `business_failure: {http_status: [...], body: {pointer, values: [...]}}`；返回命中即记运行失败、不出结论、不启动 loop；没命中（含没登记的非 2xx）照常进 loop。没配就不判失败。现有"非 2xx 即失败"的写死规则在 llm_probe_loop 里不再用。这段判断在项目入口统一一处手写，不进任何轴。
- **兑现不自推期望**（10-21 用户定）：`fulfillment` 硬依赖 `expectations`。
- 承载性第一期仍未迁：迁时同真实性，独立运行 + 选用 `search_knowledge`。

### 12.2 第二期：trace 与过程六轴

- trace 平台改为 MCP，读取 `case.trace_snapshot` 存档（需求 §4.4）；`trace_analysis` 作为一个轴，硬依赖 expectations。
- 六轴各是一个轴，硬依赖 expectations 和 trace_analysis；"本应清单"做成各轴自带的子 loop，材料只给输入端（对应现在 `process_expected.py` 的第一次调用），实际清单在主 loop 里交，per_item 提交；轴级值按 `process_axes.md` §4.1 由程序派生。
- 第一期跑通并通过对比后，再展开这一节。

## 13. 对比与验收

- 数据：`report/eval-main-axis`，dev 43 条，holdout 19 条。
- 流程：只在 dev 上调。dev 满足需求 §9 的硬门槛后，跑一次 holdout。holdout 不用来调规则。
- 重跑一致性：每条 case 两条路线各跑 3 次（10-21 定）。
- 加轴成本：逐个对比第一期每个轴的"配置字段数 + checks / synth 行数"，和现有对应 adapter 及其校验的行数。
- 防污染：写成测试，检查 events 与消息：`claims` 出现之前，主上下文里没有出现交付；`blocking`、`expectations` 子 loop 的消息里从头到尾不出现交付；`expectations` 每轮子 loop 里不出现后面轮次的原话。

## 14. 不做

- 不改 `impl/core/tool_loop` 的接口；缺能力先和你确认。
- 第一期不做：trace、过程六轴、代码工具、events 的前端视图、超过一层的嵌套、分发子 loop 并发。
- 不在框架机制之外加自定义代码（10-22 定）：轴只用配置与三个代码插口（checks / synth / dispatch），新增内置材料走注册表；框架不够用就先和用户讨论改框架。
- 不做兼容层：分出胜负后删掉输的项目和 `EVAL_AXES_PROJECTS` 里的那一项。

## 15. 待确认 ⟡

1. 承载性迁入时的配置（独立运行 + `search_knowledge`）：迁时再定细节。
2. 分发子 loop 并发执行：第一期串行，耗时数据出来后再定。
