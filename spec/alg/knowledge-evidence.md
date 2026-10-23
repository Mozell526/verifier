# 知识查证方案

> 状态：草案（2026-10-14），对着 `demand/claims.md`（2026-10-20 起原 `demand/knowledge_evidence.md` 并入其中；知识源要求并入 `demand/information_sources.md` §4.12–4.13）打磨。需求与本文冲突时以需求为准，回来修本文。
> 2026-10-20 补：found / not_found 是查与判分段的内部中间态，不是对外结论（§2）；unverifiable 必须带缺口类型（§5）。
> 实施记录写在 `spec/implementation/knowledge-evidence.md`（本文确认后再写）。
> 标 ⟡ 的条目待用户确认。

# 第一章：方案

## 1. 总体

```text
各用知识的轴提待查项 ──► ①出清单（来源可扩展，抽取可替换） ──► 待查清单（state）
  （第一版：真实性 ← 被测回答）
                                              │
场景知识源（目录 + 工具） ──► ②查证 ToolLoop ◄─┘
                                │  模型自由检索；逐条 submit_item，程序当场验收
                                ▼
                          知识案卷（knowledge_evidence 轴 output）
                                │
                                ▼
                          ③真实性轴：逐条比对，固定流程，不调工具
                                │  output 形状不变
                                ▼
                          能力兑现轴（现状不动，仍读真实性结果）
```

- ①② 在新轴 `knowledge_evidence`（标题「知识查证」）里；③ 是改造后的 `truthfulness`。
- 承载性轴本期不动，仍自己查（需求 §2.6「之后」）。

## 2. 查与判的分界

需求 §2.4 写的是案卷给「找到支持 / 找到矛盾 / 没找到」三种结果，同时 §2.1 说查证「只取证，不判对错」。支持还是矛盾本身就是判定，两条放在一起有冲突。本方案建议：

| | 查证（ToolLoop） | 真实性（工作流） |
|---|---|---|
| 交什么 | 每条：**找到相关原文**（附逐字引用）/ **没找到**（附检索记录） | 每条：verified / refuted / unverifiable + 理由 |
| 依据 | 原文是否讲的是同一对象、同一条件下的同一事项 | 引用原文与断言是否一致 |

理由：

1. 查和判的边界在程序里可见：判错时能直接看到"引用的原文是对的，比对错了"还是"引用就不相关"，正是需求 §1 第 2 条要解决的问题。
2. 判定一步只看引用原文及其上下文，不看检索过程。这样它不会被检索时的思路带偏，和现在"抽取与核验隔离"是同一个做法。
3. 下游复用：承载性、能力兑现以后要的是原文，不是真实性的结论。

代价：每条找到的事实多一次不带工具的模型调用，输入只有一两段原文，成本小。

2026-10-14 用户同意。2026-10-20 起需求侧只认核事实的三值（`demand/claims.md` §3：有支持 / 有矛盾 / 查不到）；found / not_found 是本方案查与判分段产生的中间态，只在知识查证轴内部和它的 item 级展示里出现，不进主轴组成、不进任何对外汇总。

## 3. ①出清单

- 接口：`extract_items(output_text, question, runtime) -> list[Item]`。查证只依赖这个接口。
- 第一版实现是现有真实性的抽取步骤**原样搬过来**：提示词 `_EXTRACT_SYSTEM`、校验 `_claims`（逐字、唯一、上下文不夹带别条的值）、一次带错误的修复。从 `truthfulness.py` 移到新模块，真实性不再抽取。
- `Item = {item_id, kind, origin, text, context}`：
  - `kind`：`claim`（核对说法，`text/context` 逐字摘自回答）/ `question`（查问题，`text` 是要查的问题；第一版不产生）；
  - `origin`：提出这条的轴（第一版恒为 `truthfulness`）。
  - `text/context` 与现在 `claim_id/text/context` 同义。改名是因为它进了清单后叫"待查项"，不再只是真实性的断言。
- 清单来源：每个用知识的轴类型可声明一个"待查项来源"函数 `(trace, axis) -> list[Item]`；知识查证轴按**本次启用**的轴收集各来源的项，合并成一份清单（与过程案卷按启用的下游轴整理同一做法）。第一版只有真实性一个来源（即上面的抽取）。
- 抽取口径以 `demand/claims.md` §2 为准（2026-10-20）：事实 = 能单独为真或为假的主张，**不限于带数字的**（C9）；对象和条件可来自用户问题（C8，10-19 用户确认）；一个数的值与它的单位、币种、时点各是一条（C1，10-20 用户定），修饰的那几条带 `qualifies` = 数值那条的 claim_id，判定与 M 据此放过"值已核实、单位核实不了"（`demand/main_axis.md` §2.6）。落地见 `spec/adapter/claims-extraction-plan-20261019.md`。
- **拆出的说法要能单独成立**（2026-10-17 实验，2026-10-18 采用）：`text + context` 离开回答单独读，意思和在回答里一样。
  - `context` 只放两种：事实归属对象的标识（姓名、保单号、产品名或代码、办理事项名称）和成立条件；不放任何被断言的数量和属性（它们是断言本身）。
  - 回答自己编的序号、指代（"方式一""第二张"）不进 `context`，换成所指对象的标识在回答里的原文写法；找不到所指对象就不抽这条。
  - "上下文不夹带别条的值"的校验，不把一串字母数字内部的字符算作别条的值（保单号里的"0"不是金额"0"）。
  - 依据：F20"方式一"、C08 丢"第 2 张保单"在 v7 不再判错；前提夹带引起的抽取失败 v7 4/12 → v8a 0/12（`report/knowledge-evidence-20261014/RESULT.md`）。
- 清单为空 → 轴成功，案卷为空，不开 loop（与现在"回答不含可核验的事实断言"一致）。
- 抽取失败（两次都不过校验）→ 轴失败。

## 4. ②查证 ToolLoop

用 `impl/core/tool_loop`，形态参照 `process_loop/analysis.py`。

### 4.1 上下文怎么分配

| 放在哪 | 内容 | 来源 |
|---|---|---|
| 系统提示词 | 角色、两种结果的定义、归属规则、"没找到"的要求、数字等价写法、引用规则、预算 | 通用，从现在 `_VERIFY_SYSTEM` 改写；与场景无关 |
| 首条用户消息 | 场景描述（展开知识源引用后的文本 + 知识源目录及其说明）、ES 字段骨架、待查清单、用户问题 | 场景框 `description`、程序 |
| 工具说明 | 各知识源怎么查 | MCP 来自 tools/list 原样；ES / 资料来自现有工具说明 |

不放被测回答全文。清单里每条已经带了定位上下文，和现在核验阶段"不向核验泄露整份回答"一致。

系统提示词里写明两条取证规则（需求 §2.4）：

- **正反都查**：每条同时找支持的、矛盾的、附加条件或例外（其他版本、免责、适用条件），不能找到一段支持的就停；可以带着自己的判断决定往哪查，但不在提交里写支持还是矛盾。
- **相关原文全部引用，不挑**：互相矛盾的原文都引。

程序兜不住"挑没挑"，靠提示词，验收时人工抽查；真实性判定时另给引用前后的上下文窗口（§5），部分兜底。

场景专属的查法（比如"先查客户再查保单"）写在场景描述里，或者写在 MCP 工具自己的说明里，评测器不写。

**业务描述**（2026-10-17 实验，2026-10-18 采用；依 `demand/information_sources.md` §4 第 9、10 条与 ⟡3 的倾向）：
- 业务事实（对象靠什么区分、金额单位、别名对应）由业务方写进业务描述资料，场景的知识查证框以 `{material://项目/资料id}` 引用，查证可读、可引；某个知识源的返回怎么读（分页、"本页条数等于总数即全量"、字段含义）写进该源登记的 `description`，进目录时记为 `notes`，查证和判定都看。
- 业务工具自己返回里的提示、字段说明照常是原文，查证照引、判定照读；它们按作用归入 §5 的 ② 或 ③，不是 ①，不能单独作为 refuted 的依据。
- 两处都只写数据事实，不写判法和查法（"回答写了单位就算对""可再按保单号逐个查详情"都不能写）。
- 评测系统不内置任何具体业务的事实；没写的，对不上就判 unverifiable。

### 4.2 工具

- **知识源工具**：沿用 `sources.build_tools(catalog, recorder)` 的同一组 ES / 资料 / MCP 工具。现在它们返回 agno 形态，需要像 `process_loop/tools.dossier_tools` 那样还原成 `VerifiableTool`。
- **`submit_item(item_id, status, citations, search_calls, note, gap)`**：逐条提交。
  - `status`：`found` / `not_found`；
  - `gap`：`not_found` 时必填，`object_absent`（按对象查过，对象整个不在）/ `item_absent`（对象在，这一项不在）；`found` 时为空。`demand/claims.md` §3.3 要求下游分得开这两种，程序只能从查证人这里拿到，所以在提交时就要；
  - `citations`：`[{call_id, quote}]`，`found` 必填、`not_found` 必须为空；
  - `search_calls`：为这一条做过的检索调用的 `call_id` 列表，至少一个；
  - `note`：检索思路与取舍，`not_found` 时写清查了什么、为什么认为没有。

### 4.3 证据统一用回执（call_id）

现在三类知识源的引用格式各不相同：ES 是 `文档ID#字段`，要再读一次 ES 来回读；资料是行号区间；MCP 是 `call_id`，直接核对回执。本方案统一成 MCP 的做法：

- 每次知识源工具调用都有一个 `call_id`（`c<调用序号>`，由 loop 盖进返回）。不另建台账：ToolLoop 的 History 已记下每次调用的参数、返回与批次（2026-10-14 实施时定）。工具自己的返回里若有同名键（MCP 翻页句柄已改名 `page_id`），以 loop 的编号为准。
- 引用 = `{call_id, quote}`。程序核对：
  - `call_id` 是本次 loop 之前批次里的成功调用；
  - `quote` 逐字出现在那次调用的返回里（JSON 返回也比对解出的字符串字段，与现在 `verify_mcp_quote` 一致）。
- 不再回源重读：证据就是"本次实际拿回的东西"（需求 §2.5）。JSON 字符串返回也比对解出的字段。
- MCP 登记的 `env` 里可写 `{request.<字段>}`，取自本样本的请求体（如工号）：业务按谁的身份答，评测就按谁的身份查；样本里没有该字段时轴失败，不换身份查（`information_sources.md` S9）。
- MCP 知识源登记必须声明 `tools` 白名单，评测只暴露这些工具（需求 §2.7 只读）；入参没写说明的，评测侧补中性占位，不要求业务方改 schema。这样以后 ES 和资料迁到 MCP 时，引用格式和核对逻辑都不用改。
- 原来"检索片段不能代替原文，引用前必须 read"的规则保留在提示词里，作为引导，不作为硬校验。ES 检索结果里的片段本身也是逐字原文，硬性要求先 read 只会多一次调用；上下文够不够，由真实性判定时看到的上下文窗口兜住（§5）。

### 4.4 验收（submit_item 当场返回 accepted 或拒绝原因）

1. `item_id` 在清单里，且还没有被接受过的提交。已接受的提交不能覆盖：要改就说明它查错了，应当在提交前想清楚。
2. `search_calls` 非空，每个都是此前批次的**成功**知识源调用。
   - 程序只能保证"真查过"，判断不了"查的是不是这一条"。后者靠 note 和事后人工抽查，验收里统计。
   - 同一次调用可以被几条共用。
3. `found`：`citations` 非空，每条按 §4.3 回读通过；`call_id` 必须同时出现在 `search_calls` 里，或者是 search_calls 之后的 read 类调用。
4. `not_found`：`citations` 为空；若 `search_calls` 里有失败的调用，拒绝。工具报错不是"没找到"。
5. 拒绝原因写成事实陈述，点名哪条、哪一项。

同批不可见：沿用 History 语义，同一批里的检索结果要到下一批才能引用（与 `ReceiptGate` 同口径）。

### 4.5 结束

- `completion_hook = Checklist`（继承 `RequireDone` 的思路）：清单里每条都有被接受的提交才算 `Done`；否则 `Continue("还差：<item_id 列表>")`。
- `ready_to_finish`：最后一条被接受后直接结束，不再请求模型写收尾文本（同 `StructureCompleted`）。
- 清单存在 `Checklist` 对象里，这就是讨论里说的 state。第一版不提供追加工具，但结构上允许追加（需求 §2.3）。

### 4.6 预算

- `BudgetStop(llm_calls, tool_calls, seconds)`，超出 → loop failed → 轴失败（需求 §2.8）。已经被接受的条目写进失败输出作诊断，但不算案卷。
- 初值按清单长度给：`tool_calls = 16 + 6 × 条数`、`llm_calls = 8 + 3 × 条数`、`seconds = 900`。16 是现在每条断言的工具上限。实验后校准，填进实施记录。
- 大返回：沿用现有截断 + 翻页（ES `max_field_chars`；MCP `max_chars` + `mcp_read`）。回执保存全文。
- MCP 另有 `mcp_find(page_id, keyword)`：在某次调用的完整返回里原样搜关键词，交回每处命中前后约 400 字（需求要求 6"真查过"、`information_sources.md` S4）。提示词写明：截断没看到的部分不能当作"没有"，用 `mcp_find` 搜或翻页看完。依据：客户详情约 5.3 万字、每页 6,000 字，客户级字段在 2.3 万字之后；v3 每轮调了客户详情从没翻页，v4 加 `mcp_find` 后伏云平 750,000 由 0/3 到 3/3（`report/knowledge-evidence-20261014/RESULT.md` v3/v4）。
- 判定拿到的引用上下文：结构化返回给包住引句的整条记录（不超过 3,000 字，最多 3 条），并附取回它的那次查询（工具与参数），归属靠查询条件判断（姓名是密文时）。

### 4.7 模型

- 角色 `truthfulness`（复用现有配置，不新增配置项），`reasoning_effort` 先用 `low`，与现在核验一致。
- 和 medium 的对比放进验收实验。

## 5. ③真实性改造

- `depend_on=(Dependency('knowledge_evidence'),)`（必需）；`inputs` 增加 `Input('evidence', source='axis.knowledge_evidence.output', fields=('items', 'sources'))`。
- 场景字段：真实性框不再需要知识源引用。`description` 改为可选，只作判定口径补充。
- 每条：
  - `not_found` → `unverifiable`，程序直接给，reason 取查证的 note，`gap` 原样带下（`object_absent` / `item_absent`），不调模型；
  - `found` 但判定认为原文对象不符或说不清 → `unverifiable`，`gap=mismatch`；
  - `found` → 一次不带工具的模型调用。输入：
    - 待查项（text、context）；
    - 各引用的 quote；
    - **该 quote 在回执原文中的前后窗口**（前后各约 500 字，程序切）。

    输出 `reason/verdict/citations`，`citations` 只能是给定引用的子集，程序校验。原文与断言对象不符、或说不清的，判 `unverifiable`。
- **判定只用一条边界**（2026-10-17 实验，2026-10-18 采用；取代此前叠加的逐条规则）：
  - 说法 = 某对象（某条件下）的某属性 = 某值；回答自己的编号、排序、指代不是任何对象的属性。
  - 原文按作用分三种：① 关于对象的事实（数据字段值、条款、业务规定）；② 数据怎么读（字段含义、归属、口径、单位、全不全）；③ 对使用者的要求（怎么写、能不能怎么展示）。
  - 只有 ① 定对错：① 有同一对象、同一属性、同一条件下的值，一致为 verified、不同为 refuted；没有为 unverifiable。② 用来确定 ① 说的是哪个对象、哪个属性、什么口径；③ 与对错无关。② ③ 不能作为 refuted 的依据。
  - 算出来的值：原文写明算法或说法自己写明了用哪些数怎么算，才照算法算；没有算法就是 ① 没给这个值。
  - 依据：同一份证据只重判判官，判冲突里判错的 26 → 15 次，"不得当作保单合计"一类不再判冲突；同证据两次结论一致率未提高（约 90%），剩余波动另计（`report/knowledge-evidence-20261014/rejudge/`）。
- `output`：`claims[{claim_id, text, context, verdict, reason, citations, gap}]`、`sources`、`coverage`、`errors`；`gap` 是新增键，unverifiable 时非空。能力兑现轴读它，不用改。引用在输出里由 `{call_id, quote}` 展开成 `{source, ref, note}`（source 由回执得出），前端不用改。
- 上游状态的传递：
  - 查证 `not_applicable`（被测系统调用失败、场景没声明知识源）→ 真实性也 `not_applicable`，原因照抄；
  - 查证 `failed` → 真实性 `blocked`（现有 runner 行为）；
  - 能力兑现的真实性依赖是可选的，照旧按"未纳入"处理。

## 6. 新轴的类型声明

```text
type_id        knowledge_evidence      title 知识查证
summary        针对回答中的事实到场景知识源取证，交出知识案卷，不判对错
verdict_scope  item                    item_path items[].status
verdict_enum   found（找到相关原文）/ not_found（查过，没找到）
inputs         trace (sample.trace)
scenario       description（required，expand=catalog）——知识源引用只写在这里
output_fields  items, searches, sources, coverage, errors
limits         见 §4.6
```

- `items[]`：`item_id, kind, origin, text, context, status, citations[{call_id, source, quote}], search_calls, note`。
- `searches`：全部知识源调用回执（工具、参数、call_id、返回原文、错误），用于事后查看"查了什么、看到了什么"（需求 §2.5）。
- 前端：轴结果表沿用 item 级展示（key = 待查项原文、value = found / not_found、reason = note）。回执原文先只进导出和详情 JSON，不另做页面。
- 场景没声明任何知识源 → `not_applicable`（"场景未声明知识源"）。被测系统调用失败 → `not_applicable`（同现在）。

## 7. 预设迁移

- 现有预设里，真实性框描述中的 `{es://…}` / `{mcp://…}` / `{material://…}` 引用，搬到新增的知识查证框；真实性框清掉这些引用。
- 直接改 `capability_map.json` 数据（仓库与实例两处数据根），不写兼容层（AGENTS.md）。
- 保存时校验：不按目录展开的框（包括改造后的真实性）里出现 `{es://}` / `{mcp://}` → 报错，提示放到知识查证框。`{material://}` 仍可作判定口径内联。
- 迁移按句拆：带引用的句子（查哪里）归知识查证，其余句子（怎么判）留在真实性作判定口径。

## 8. 代码位置

```text
impl/projects/llm_probe/knowledge_loop/     新，平行于 process_loop/
  extract.py       ①出清单（从 truthfulness.py 搬来）
  loop.py          ②Checklist / submit_item 验收 / ToolLoop 组装
impl/projects/llm_probe/eval_axes/adapters/
  knowledge_evidence.py   新轴 run + AXIS_TYPE
  truthfulness.py         改为读案卷判定
impl/projects/llm_probe/eval_axes/sources/
  es_tools.py / mcp_tools.py / material_tools 包装    回执补 call_id + 返回原文；统一回读函数
```

## 9. 验收实验（对应需求 §4）

- 样本：F01–F10、L01–L05、M1–M3，加 3–5 条真实长回答（多段、带列表的保险回答，人工标出应抽出的事实）。
- 对照：`verifier-notrace-base`（现状真实性）与本实现，每条跑 3 轮。
- 报数：
  - ⟡ 按格分报（`spec/adapter/information-sources-plan-20261017.md` §2.1，bench `score` 的分层表）：漏查率、归属可疑数、因业务描述缺失的无法确认数、变义条数、冤枉率、一致率；评测器失败按拆说法 / 预算时限 / 其他分开记；判定正确率照报，不作决策依据；
  - 判定正确率、轴失败率；
  - 漏查（应为 0）、引用回读通过率（应为 100%）、没查就交没找到（应为 0）；
  - 漏抽率及三类归因；
  - 耗时 / 模型调用 / 工具调用；
  - `search_calls` 与条目相关性的人工抽查结果。
- 演示：新登记一个 MCP 知识源（用 insurance-tools 以外的一个最小 MCP 服务），场景引用后直接查证，评测器零改动。

## 10. 之后（不在本期）

- **ES、资料迁到 MCP**（原需求 ⟡3，2026-10-14 定验收后优先做；现归实施排期）：写一个只读的通用知识库 MCP 服务，暴露 outline / search / read，评测器删掉 `es_tools`、资料工具在这条路径上的分支。§4.3 已统一引用格式，届时只换工具来源。
- **查问题 + 核心要点漏说**（`demand/claims.md` ⟡1，排在 MCP 迁移之后）：加"查问题"来源（每个用户问题一条），查证取回相关原文，由判定轴（倾向能力兑现）对照回答判漏没漏、算不算错。查证部分不用改，只加一个来源和一个读者。
- 承载性改读案卷；trace 场景对照（`demand/information_sources.md` ⟡）；能力兑现直接读案卷（暂缓）。
