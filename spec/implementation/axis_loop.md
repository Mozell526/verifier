# 评测轴任务化（axis loop）实施记录

> 更新：2026-10-21。本文持续维护实施步骤、状态、验证证据和未决事项。
> 当前阶段：§8 重构 R1–R8 完成。准确率、误放行、重跑一致持平；耗时（中位 300s vs 169s）与 token（输入中位 2.4 倍）两条门槛没过，见 `report/axis-loop-20261021/RESULT.md` R8 节。待用户定下一步。

## 1. 三类文档的分工

| 文档 | 回答的问题 | 入口 |
|---|---|---|
| 需求 | 要解决什么、要什么、不做什么、怎么验收 | [评测轴任务化需求](../../demand/axis_loop.md) |
| 方案 | 怎么分工、结构与规则 | [评测轴任务化方案](../alg/axis_loop.md) |
| 实施 | 改哪里、按什么顺序、做到哪、验证证据 | 本文 |

三者冲突时，在本文 §6 记下差异，再回对应文档修订；不在实施里偷改口径。"代码存在""离线测试通过""真实运行通过"三件事分开记录，不互相替代。

## 2. 实施约束

- **在哪里做**：本目录（`verifier`，main 分支，含 10-20 主轴改版的未提交改动）。新项目是纯新增，对 llm_probe 只改 §3.1 列出的分发点。⟡ 如果要求单独开分支或 worktree，需要在 P1 之前说。
- **实验隔离**（记忆 experiment-isolation）：工作流路线的基线在隔离副本里跑（P0），评测进行中不改它会读到的文件。`report/eval-main-axis/run_eval.py` 默认读 `verifier-integrate`，新旧对照时用 `EVAL_CODE` 指定代码目录。
- **环境**：只用 `.env` 里的 `PYTHON_EXECUTABLE`（agno 环境）。要用的 `jsonschema 4.26.0`、`mcp 1.12.4` 都已安装，**本期不加新包**。
- **不保留兼容**（AGENTS.md）：llm_probe_loop 里不带旧的 `eval_axes`；ES 直连、`verify_quote` 回读、receipts 核验直接删；`knowledge_sources.json` 改名为 `sources.json`，不写 migration。
- **不碰**：`impl/core/tool_loop` 的接口；llm_probe 的评测逻辑；其他项目。
- **提交**：等用户说了再提交。

## 3. 设计落点（对应方案）

### 3.1 新项目与分发点（方案 §2）

```text
impl/projects/llm_probe_loop/      ← cp -R impl/projects/llm_probe
  删除  eval_axes/  knowledge_loop/  process_loop/
  新增  axis_loop.py               项目接入（§3.6）
        materials.py              内置材料取值函数（§3.3）
        mcp_servers/es/           ES 包装成 MCP server（§3.5）
  改    judge.py                  _main_axis_result / ProcessJudgeExecution → 调用 axis_loop.build_report
        project.yaml              project.id = llm_probe_loop
  批量  91 处 impl.projects.llm_probe → impl.projects.llm_probe_loop（26 个文件）；3 处项目 id 字面量
impl/data/llm_probe_loop/          ← 拷贝 llm_probe 的 capability_map.json、knowledge_sources.json（改名 sources.json）
```

分发点：llm_probe 只改这些地方，行为不变。

| 文件 | 现在 | 改成 |
|---|---|---|
| `impl/server/service.py` | 12 处 `project == "llm_probe"` / `from ..projects.llm_probe.xxx` | `project in EVAL_AXES_PROJECTS`；`importlib.import_module(f"impl.projects.{project}.xxx")` |
| `impl/core/table_view.py:209-211` | 硬 import `llm_probe.business_trace.dossier`、`llm_probe.eval_axes.registry` | 按 trace 的 project_id 取模块；llm_probe_loop 提供同名接口（§3.6） |
| 前端 13 处 | `'llm_probe'` 常量 | `EVAL_AXES_PROJECTS` 数组 |

llm_probe_loop 对外提供与 llm_probe 同名的入口：`eval_axes.run_for_trace` / `build_report`，以及 `describe_axis_types`。core 的 `eval_axes.py` 按项目名找 `impl.projects.<id>.eval_axes`，所以新项目里保留一个只做转发的 `eval_axes.py`，转到 `axis_loop`。

### 3.2 `impl/core/axis_loop/` 模块（方案 §3–§7）

| 模块 | 职责 | 对应方案 |
|---|---|---|
| `definitions.py` | `AxisDef` / `SubloopDef` dataclass；读写 `axis_definitions.json`（复用 `capability_store` 的存储读写）；output 字段表 → JSON Schema；加载期校验（方案 §3.4 全部条目） | §3 |
| `materials.py` | `MaterialRegistry`（标准名 → schema、description、load）；白名单解析（`名.路径.{字段}`）；路径对 schema 的静态检查；按白名单取值、投影；呈现（标题 + 文本 / 稳定的 JSON） | §4 |
| `view.py` | `TaskView`、`CallView`；按白名单裁剪 | §7.1 |
| `checks.py` | 标准校验 `covers`、`refs_in`、`quote_in_material`、`quote_in_call`、`searched`、`from_call`；参数校验；路径求值（复用 runner 的 `_item_values` 写法） | §7.2 |
| `acceptance.py` | 验收流水线 1–5；用户代码加载与签名检查（`check(view)` / `synthesize(view)`） | §5.3 |
| `ledger.py` | 台账：状态机（未出现 / 已出现 / 已完成 / 作废 / 撤下 / 不出现）、作废的传递、触发重算、程序任务合成、推送文本、事件记录 | §5.4、§11.2 |
| `gate.py` | 工具门禁 Hook（类别、子 loop 所属轴是否已出现）；`StampCallId` 搬过来作为 post_tool | §5.1 |
| `subloop.py` | 子 loop：独立 ToolLoop + `as_tool(render=按白名单拼材料与参数)`；返回 `{text, structured}`；失败时中止父 loop | §6 |
| `context.py` | token 估算、80% 归档、`recall` 工具 | §9 |
| `loop.py` | `AxisLoop`：组装 ToolLoop（固定工具列表、hooks、completion_hook=台账、BudgetStop）；`run(case) -> LoopReport` | §1、§5、§10 |
| `report.py` | LoopReport → `build_report` 同形的 dict | §11.1 |

依赖方向：`loop → ledger / gate / subloop / acceptance / context → checks / view / materials / definitions`。不 import 任何项目代码。

### 3.3 内置材料（方案 §4.1）

`llm_probe_loop/materials.py` 登记 11 个取值函数，从 RunTrace 和 capability_map 里取：

| 标准名 | 取值来源（现有代码） |
|---|---|
| `case.user_turns` / `case.requests` / `case.deliveries` | `business_trace/expectation_material.py` 现有的按轮拆分；`judge._request_payload` |
| `case.business_status` | `core.live_protocol.business_call_failure` |
| `scenario.capability` / `criterion` / `description` / `downstream` / `process_obligations` | `load_capability_map(...)[scenario]`；description 经 `expand_material_uris` 展开 |
| `scenario.boundary` | `sources.expand_boundary` |
| `axis.note` | 场景 `axes[]` 中当前轴的 description |

业务调用失败时（`case.business_status.ok = false`），AxisLoop 不启动，照现有口径出结论（兑现 = not_fulfilled），并在 loop 记录里写明。

### 3.4 第一期的轴定义（方案 §12.1）

写进 `impl/data/llm_probe_loop/axis_definitions.json`。说明正文从现有 prompt 迁移，去掉格式话术：

| 轴 / 子 loop | 说明的来源 | 现有校验 → 新写法 |
|---|---|---|
| `expectations` | `expectations.py` 的 `SYSTEM` | 形状、id 唯一、source_refs → schema + `refs_in`；"必须引本轮用户原话""歧义组 ≥2""有要求不可空集" → `checks.py` |
| `claims` | `knowledge_loop/extract.py` 的 `EXTRACT_SYSTEM` | span 逐字 → `quote_in_material(case.deliveries)`；context 逐字、qualifies 指向、context 不夹带别条 → `checks.py` |
| `truthfulness` | `truthfulness.py` 的 `_JUDGE_SYSTEM` | verdict / gap 的 if/then → schema；basis 必须是检索得到的引文 → `from_call(search_knowledge)` + `refs_in`；轴级 verdict → `synth.py` |
| `fulfillment` | `fulfillment.py` 的 `DELIVERY_SYSTEM` | 逐条覆盖 → `covers`；claim_refs 存在 → `refs_in`；"引了被否定的说法必须判没给到""有核事实时 fulfilled 必须引 verified" → `checks.py`（即 `check_assessments`）；blocking、not_fulfilled 列表、整体状态 → `synth.py`（复用 `_derive_overall_status`） |
| └ `judge_blocking` | `fulfillment.py` 的 `BLOCKING_SYSTEM` | `covers` 全部期望 |
| `carryability` | `carryability.py` 的 `_SYSTEM` | 覆盖 → `covers`；做不了 / 做错了必须有依据 → schema if/then；依据引自责任范围 → `quote_in_material(scenario.boundary)`；依据引自知识 → `from_call(search_knowledge)`；轴级 verdict → `synth.py` |
| `main_verdict`（程序） | — | `synth.py` 调用现有的 `main_verdict()`（从 llm_probe 复制过来，不改） |
| `search_knowledge`（共享子 loop） | `knowledge_loop/loop.py` 的 `SYSTEM` | 现有 `Checklist` 全部改写为 schema + `searched` + `refs_in` + `quote_in_call`，不写代码 |

### 3.5 MCP（方案 §8）

- `core/axis_loop` 不管 MCP。MCP 客户端放在 `llm_probe_loop/sources/`，由现有 `mcp_tools.py` 改写：用官方 `mcp` SDK 的 `stdio_client` + `ClientSession`；返回统一成 `{content, structuredContent?, isError}`；对外只给 `mcp_call / mcp_read / mcp_find` 三个通用工具，各实例的工具清单作为推送文本。
- `sources.json`：`{name: {category, command, args, env, tools?, max_chars, notes}}`。场景条目新增 `sources: [{instance, params}]`，轴框里可以加 `sources: [实例名]`。
- `mcp_servers/es/server.py`：用 `mcp` SDK 的 FastMCP 暴露 `es_outline`、`es_search`、`es_read`，内部直接调用搬过来的 `es_client` + `es_tools` 逻辑，检索语义不变。现有 ES 登记迁成 `command: python -m impl.projects.llm_probe_loop.mcp_servers.es --source <名>`。

### 3.6 项目接入（方案 §2.3、§11）

`llm_probe_loop/axis_loop.py`：

```text
build_case(spec, trace) -> Case                  RunTrace + 场景 → case（含业务调用状态）
build_report(spec, trace, run_id="") -> dict     加载定义 → 校验 → AxisLoop(...).run(case) → report.py 组装
describe_axis_types() -> list                    给前端：轴定义列表（替代 registry.describe_axis_types）
```

- 模型客户端：沿用 `eval_axes/llm.py` 里 `axis_llm` 的记账和模型策略，搬到 `llm_probe_loop/llm.py`，角色名 `axis_loop`。
- trace_id、stage：`AxisLoop` 用 `LoopContext(trace_id=run_id, stage="axis_loop")`；子 loop 继承前缀（ToolLoop 的既有行为）。

## 4. 实施步骤与状态

| 步 | 内容 | 完成标准 | 状态 |
|---|---|---|---|
| P0 | 基线：在隔离副本里，用 llm_probe 的工作流路线在 dev 43 条上跑 3 次，记录一致率、误放行、重跑一致率、token、耗时 | `report/axis-loop-20261021/baseline/` 下有结果 + RESULT.md；可以复算 | 完成：128/129 成功，一致 89.8%、误放行 9/65、三次一致 41/42、耗时中位 169s |
| P1 | 新项目骨架：复制、改名、拷数据、分发点（§3.1） | llm_probe_loop 能被 project_loader 加载；llm_probe 的现有测试全部通过；其他项目测试不受影响 | 完成 |
| P2 | 定义与材料：`definitions.py`、`materials.py`、加载期校验 | 单测：方案 §3.4 每个报错条目各有一个反例；白名单投影与路径检查 | 完成 |
| P3 | 视图、标准校验、验收流水线 | 单测：每个标准校验正反例；流水线 1–5；合成出错时中止；同一视图连续跑两次结果相同 | 完成 |
| P4 | 台账、门禁、子 loop、AxisLoop 组装 | 用脚本化的 StepClient 跑通：出现 / 作废传递 / 撤下 / 程序任务重算 / 门禁拒绝 / 子 loop 隔离（消息里不出现交付）/ 子 loop 失败即中止 / completion | 完成 |
| P5 | MCP：SDK 客户端、`isError`、ES MCP server、`sources.json` | 单测：ES server 与旧 `es_tools` 在同一组查询上返回逐字一致（用录下来的查询）；MCP 翻页、搜索 | 完成 |
| P6 | 项目接入 + 第一期 6 个轴和 2 个子 loop 的定义、checks、synth（§3.4） | 离线：报告与 `build_report` 同形；`main_verdict` 在同一组合成结果上与 llm_probe 一致；防污染测试（方案 §13） | 完成（carryability 未定义，见 §6.16） |
| P7 | 真实运行：单条 case 跑通；然后 dev 43 条 × 3 次 | 指标按需求 §9 与 P0 对比，写 RESULT.md；判错 case 能从 events 里定位 | 完成：dev 128/129 成功，见 RESULT.md |
| P8 | 调优：只在 dev 上调，直到过硬门槛 | 硬门槛全部满足；每次调整都记录在 §5 | 未开始 |
| P9 | holdout 19 条跑一次 | 结果写进 RESULT.md，不再回头调 | 未开始 |
| P10 | 页面：轴定义页（配置表单、说明、上传代码）；场景页轴框选实例；信息源页通用化 | 用页面新建一个测试轴，不改代码就能跑出结果（需求 §6 的验收） | 未开始 |
| P11 | 判胜负，删输的那一方：项目目录、`EVAL_AXES_PROJECTS` 里的那一项、前端里的那一项 | 用户拍板 | 未开始 |

- P10 放在 P7–P9 之后：先用手写的 `axis_definitions.json` 跑通端到端，再上页面（AGENTS.md："先跑通最小端到端"）。页面编辑的是同一份存储，不会出现两套定义。
- 每一步结束都更新本表和 §5。

## 5. 验证证据

- **P1**：`llm_probe_loop` 能被 project_loader 加载；全量测试 2017 passed / 27 failed，其中 26 个失败与本次改动无关（工作区原有未提交改动与测试不一致：需求材料改成 `{query}`、`build_tools` 加了 `recorder` 等），1 个（`test_project_config_contract` 写死项目列表）已随新项目更新，通过。
- **P2–P4**：`tests/test_axis_loop_core.py`（26）、`tests/test_axis_loop_run.py`（10）全部通过：定义加载期报错逐条反例、路径与投影、标准校验正反例、验收流水线、出现 / 作废 / 撤下 / 程序任务 / 门禁 / 子 loop 隔离（子 loop 消息里不出现交付）/ 子 loop 失败即整案失败 / 合成出错即失败 / 上下文归档与超限失败。
- **P5**：`tests/test_llm_probe_loop_es_mcp.py`（3）通过：ES 经本地 MCP server 的检索、回读结果与直连 `EsTools` 逐字一致；报错带 `isError`；未选用的索引被拒。
- **P6**：轴定义存储 `impl/data/llm_probe_loop/axis_definitions.json` 加载期校验无报错（曾查出 truthfulness 的 claims 缺元素 schema，已补）；llm_probe_loop 全部模块可导入。
- **P7 dev**：`report/axis-loop-20261021/RESULT.md`。127 次配对：一致 115 vs 基线 114，误放行 9/64 vs 9/64，三次一致 42/42 vs 41/42；耗时中位 330s vs 168s，请求均值 22.2 vs 20.3；token 未测。
- **P7 单条**：`F-annual-ok`（hr-handbook-qa，gold=fulfilled）→ 五个轴全部完成，兑现 fulfilled，主轴「做成了」；153 s、16 次模型请求、16 次工具调用；`claims` 出现前主上下文里没有交付文本；兑现第一次提交被拒（"有核事实结果时，fulfilled 必须引用至少一条 verified 的 claim"），改后接受。同一条在工作流路线冒烟耗时 99.7 s。

## 6. 与方案 / 需求的差异

待回方案文档修订的（标 ★ 的是新增机制，需用户确认）：

1. **复制时先连 eval_axes 一起复制**，P6 再删 adapters/runner/types/knowledge_loop/process_loop：非评测模块（need_judge、capability、judge）引用了它们，先保证 P1 能加载。现已删净。
2. **table_view 按 trace.project_id 动态取模块**（`impl.projects.<id>.business_trace.dossier` / `.eval_axes.registry`），llm_probe 不改；llm_probe_loop 的 `eval_axes/registry.py` 提供同名 `AXIS_TYPES`。
3. **main 目录 `.env` 有两行过时变量**（`EVAL_AXES_ES_ENABLED/URL`，verifier-integrate 早已删），导致配置加载直接报错、测试跑不起来；已按 integrate 删掉，备份 `.env.bak-axisloop-*`。
4. **知识路由**要求仓库根目录 `projects/<id>/project.yaml`，已为 llm_probe_loop 加一份（复制 llm_probe 的、改 id）。
5. **视图里的材料按标准名给完整值**（方案 §7.1 写的是按白名单条目）：投影只决定放进上下文给模型看多少；代码不是模型，给完整值不构成污染，且 `of` 路径可直接写 `<标准名>.<路径>`。
6. ★ **带参数的内置材料**：材料可声明参数（如 `case.turn_requirements` 的 `turn`），只有参数里含这些名字的子 loop 能读，加载期检查。起因：需求按轮写、每轮看不到后面的轮（spec/alg/expectations.md §2.1；后一轮常是对上一轮交付的反应，等于漏交付），这是"任务里一部分不能看"，按需求 §3.2.3 要用子 loop，而子 loop 要按轮取材料。
7. ★ **需求轴 = 主 loop 里的编排任务 + 每轮一个子 loop `turn_expectations`**：主任务只看 `case.turns`（轮次编号，不含原话），对每一轮调一次子 loop，期望由程序从调用结果里取（全部程序填）。
8. **合成程序只返回程序填的字段**，由程序合并进模型填的部分（方案 §5.3 写的是返回完整结果）：模型填的字段不让代码改。
9. **分条交时同一分项再交是替换**（方案 §5.3 写的是重复交被拒）：改错只重交那一条；替换后收尾要重交。
10. **标准校验加 `on: item | final`**，分条交时逐项校验与收尾校验分开声明；**定义加 `item_key`**（分项编号写进哪个字段）。
11. **信息源工具按实例暴露**（`<实例>__<工具>`，现有 MCP 工具名与 schema 原样），不用通用 `mcp_call(source, tool, args)`：工具列表仍是一开始就固定（场景选用的实例在 loop 开始前已知），模型还能拿到每个工具真实的参数说明。MCP 客户端沿用项目已有的 fastmcp；ES 的本地 MCP server 用官方 `mcp` SDK 的 FastMCP。
12. **知识源登记没有改名为 `sources.json`**，ES 条目仍是 `type: es`（连接信息），由评测器自动拉起本地 ES MCP server 访问；场景选用沿用轴框描述里的 `{es://…}`、`{mcp://…}`、`{material://…}` 引用，不加新的 `sources` 字段（页面现成支持）。
13. **归档策略**：接近上限时归档最早的工具返回（最近一批除外），不按"已完成任务"挑：工具调用不归属任务。
14. **ES 字段骨架**（scenario.knowledge 材料）经 ES 的 MCP server 取，不直连。
15. **预算是模块常量**（`eval_axes/__init__.py: SETTINGS`），还没进配置。
16. **承载性没有定义进第一期存储**：评测集场景都没开承载性（工作流基线也不跑它），先不迁；主轴结论对承载性是软依赖，没开照常出结论。
17. **业务 trace 场景**：llm_probe_loop 的判官不接过程六轴（第二期），`requires_business_trace` 全为 False。
18. **需求轴的判准**取场景里需求轴框的描述；场景预设迁移时把原兑现框描述（场景判准原文）填进需求轴框，同现方案"兑现自推期望"读的材料一致。说法只抽最后一轮交付（`case.final_output`），同现方案。

## 7. 未决事项

- ⟡ 在本目录做，还是单独开分支或 worktree（§2）。
- ⟡ 必须隔离的子 loop 不给参数够不够用：P7 试运行后定（方案 §15）。
- ⟡ 预算系数与上下文上限的初值：P4 先取现有各轴 `ExecutionLimits` 的总和，P7 后回填。
- 风险：单 case 一个 loop，所有轴在一个上下文里，可能比现方案更不稳定（记忆 langfuse-provider：主判官重跑不稳）。P7 的重跑一致率是第一道关。

## 8. 重构计划（2026-10-22 grill 定，需求 / 方案已同步修订）

起因（`report/axis-loop-20261021/RESULT.md` 补充一节与查因记录）：去掉端点故障后仍约 2 倍耗时。主要是真实性取证结果（每 case 12–21 万字证据原文）回到主 loop 公共上下文、之后每轮都带着；其次是固定编排开销（需求、blocking 要主 loop 模型调度）。

| 步 | 内容 | 完成标准 | 状态 |
|---|---|---|---|
| R1 | 框架：`run_mode: isolated`（台账启动独立子 loop，结果即轴结果，作废重跑）；去掉"轴自带子 loop" | 单测：出现即自动跑、结果写入、上游改动重跑、失败即整案失败、主 loop 看不到其过程 | 完成 |
| R2 | 框架：`dispatch.py` 插口 + 白名单元素筛选 `[字段=值,…]` + `view.parts`；撤掉带参数的内置材料 | 单测：分发多份、每份只见自己的选择、选择越界即失败、合并走 synth | 完成 |
| R3 | 框架：公共 loop 工具（`shared_tools`，原 `shared_subloops`），独立运行的轴里可调一层；子 loop 开归档 | 单测：嵌套一层可用、两层被拒、归档在子 loop 生效 | 完成 |
| R4 | 框架：预算进全局运行配置 `axis_loop.*`；loop 失败时各轴不留半截输出（A1） | 配置可改、测试覆盖 | 完成 |
| R5 | 项目：`case.requirements` 内置材料（不带参数）；删 `case.turns` / `case.turn_requirements`；返回命中场景预先维护的错误码 → 运行失败（不启动 loop），没命中的照常进 loop，没配错误码就不判失败；`role` 进定义；信息源类别按登记判断；删 `requires_business_trace` | 单测 + 加载期校验 | 完成 |
| R6 | 配置：需求（isolated + dispatch 按轮）、blocking 独立成轴、真实性（isolated + search_knowledge，可补查）、兑现读 `result.blocking`；迁移场景预设 | 加载期校验无报错；防污染测试（§13 方案） | 完成 |
| R7 | 检视 C1–C5 收尾（重复逻辑、私有调用、死代码、知识源目录建两次） | 全部测试通过 | 完成 |
| R8 | 重测：调大上下文记录保留上限，两条路线各 dev 1 轮测 token 与耗时；loop 再跑 dev × 3 看一致率与稳定性 | RESULT.md 新增一节 | 完成：准确率、误放行、稳定性持平；耗时中位 300s vs 169s、输入 token 中位 2.4 倍，两条门槛没过（RESULT.md R8 节） |

R1–R7 验证：`tests/test_axis_loop_core.py`（31）、`tests/test_axis_loop_run.py`（9：分发每份只见自己那一轮、blocking 看不到交付、取证原文只在真实性子 loop 里、主 loop 只推 main 轴、独立运行失败即整案失败、分发选择越界即失败、上游修改让独立运行的下游自动重跑、合成出错即失败、上下文超限）、`tests/test_llm_probe_loop_project.py`（6：定义加载、可见性、按轮分发、硬依赖、错误码只认登记的）、ES MCP（3）、项目契约（27），共 75 passed。真实单条 `F-annual-ok`：结论对，14 次请求（重构前 16），主 loop 上下文合计 7.5k 字（只有说法抽取与兑现两个任务）。
实现细节：预算键名用现有 `eval_axes` 节下的 `loop_*`；分发出去的每份子 loop 只交模型填的字段、不合成，各份收齐后由轴的 synth 一次合成完整结果；事件里 `subloop` 是一次子 loop 运行，`isolated` 是这个轴完成。

§6 偏差中已回填进方案的：5（视图材料按标准名）、10（`on` / `item_key`）、11（工具按信息源暴露）、12（沿用登记与引用写法）、15（预算进配置）、17（trace 第二期）；被这次重构取代的：6、7（带参数材料、需求轴编排）。
