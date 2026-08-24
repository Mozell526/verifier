# Authority 担保协议（Grilling 会话共识）

- 状态：设计共识已达成（2026-08-07，grilling 会话 8 轮），待按 §10 顺序实施。
- 上游关系：本 spec **扩展** `spec/alg/authority.md`（下称"主协议"），不替代它。
  主协议已定的 Runtime 契约（Environment 绑定、Tool audit、snapshot、§8.1–8.5 消费规则）
  全部继续有效；本 spec 在其上新增 claim 担保模式、义务协议、判后核对门禁与验证设施。
  两者冲突处以本 spec 为准，并在 §11 记录理由。
- 范围：协议层项目无关（§9 泛化约束）；首个落地项目为 client_search draft judge，
  验证通过晋升后才允许提取到 core（§9.2）。

---

## 1. 设计定位

### 1.1 判决中的两类断言

Judge 的判决本质是一组断言，分两类：

| 类别 | 例子 | 核实方式 |
|---|---|---|
| 描述性断言 | "live 实际输出了条件 X" | 来自 trace，用证据核实，不需要 authority |
| 规范性断言 | "该字段应被支持 / 该枚举值合法 / 该口语应映射到 X / 该请求属于产品职责" | judge 在替业务系统说话，judge 无终审权；终审权在权威资料 |

### 1.2 resolve 的定位转变

`authority.resolve` 从"问答神谕"（judge 提问、authority 回答）扩展为
"**担保人**"（judge 声明自己说了什么，authority 逐项核对有无权威背书）。
两种模式共存于同一工具：

- **提问模式**（现状）：`resolve(question)`，返回 resolved/unresolved，语义不变；
- **担保模式**（新增）：`resolve(question, claim)`，judge 把自己即将写入判决的
  规范性断言提交核验，返回四值（§2.2）。

定位依据：authority 第二路输入的信息量 = **本判决中做出的规范性断言集合**。

### 1.3 核心原则

1. **说了就要有担保**：判决动用的每条规范性断言，必须被随附资料或 authority 调用
   之一背书，否则该断言依赖的结论不成立（§3、§4）。
2. **责任必须可归因**：每条违规 finding 必须指明该改哪个资产（§4.3），
   否则 harness AI 无法行动。
3. **没给途径就不罚执行者**：authority 工具未被构造时，judge 的越资料断言
   归责于可用性门禁/调查层，不归责于 judge（§4.3 F2）。
4. **消费保持 pull**（用户明确否决 push），本 spec 的全部机制是"带牙的 pull"：
   牙长在义务核对与惩罚上，不长在强制调用上。

---

## 2. resolve 的 claim 扩展

### 2.1 claim 对象

`AuthorityRequest` 新增**可选** claim 成分；不传 claim 时行为与主协议完全一致
（向后兼容）。claim 为结构化对象，禁止用自由文本重述结论：

| 字段 | 含义 | 约束 |
|---|---|---|
| `claim_statement` | 待担保的结论原文 | 非空；是断言本身，不是引导性问题 |
| `subject` | 断言主题锚点 | **项目自定义、协议不解释**（§9.1）；同项目内可确定性比较 |
| `conclusion_kind` | 断言类别 | 对齐调查报告 conclusion_kind 词表（normative_rule / external_fact / inlive_boundary / current_behavior） |
| `intended_use` | 该断言用于哪个验收项 | expectation_id 或等价定位 |

反例（禁止）：把 claim 写成"请确认成交日=保单生效日对吗？"——引导性提问会复刻
028 类绕过（§附录 A.2），claim 必须是结论陈述。

### 2.2 四值返回

担保模式下 `AuthorityResolution.status` 扩展为四值（提问模式仍为
resolved/unresolved，不受影响）：

| 值 | 含义 | 调用方后果 |
|---|---|---|
| `supported` | 有资料管辖该 subject，且资料结论与 claim 一致 | 断言获得担保，判决可依赖；statement 给出资料说法与依据 |
| `contradicted` | 有资料管辖，但资料结论与 claim 相反 | 断言是错的：依赖它的肯定性 verdict 不得成立（§4.2 惩罚阶梯） |
| `ungoverned` | 没有任何资料管辖该 subject | 无关对错——没有权威可保：依赖结论降 not_evaluable；finding 指向可用性/管辖映射或 judge 越权 |
| `gap_only` | 有资料管辖但资料不足以给出结论（含已登记 coverage_gap） | 真缺口：降 not_evaluable + 记录 required_evidence，供人类决定补资料 |

`ungoverned` 与 `gap_only` 都必须强制把依赖该断言的 assessment 降为
`not_evaluable`（与主协议 §8.4 对 unresolved 的硬校验同口径，但归因不同，§4.3）。
拆成四值的理由：主协议 unresolved 把"没人管"和"管了但不够"混为一谈，
judge 分不清就容易自己编答案（028 实证，§附录 A.2）。

### 2.3 单次调用内部两阶段（防锚定）

担保模式的一次 resolve 内部必须两阶段，对外仍是单次调用：

1. **盲查阶段**：Authority Agent 不知道 claim 内容，仅按 question/subject 在绑定
   资料空间内独立检索并得出结论（沿用主协议 §5 判断顺序）；
2. **比对阶段**：将独立结论与 claim 比对，产出四值之一。

audit 必须同时记录独立结论与比对结果，使"先独立裁决"可事后验证。
禁止把 claim 直接作为检索 query 或让比对阶段推翻盲查结论。

### 2.4 cache 与 audit

- cache key 扩展为 (question, claim 规范化, environment_snapshot_sha256)；
  提问模式 key 不变；
- Tool audit 记录完整 request（含 claim）与四值 resolution（主协议 §4.3 口径）；
- tool_failure 与业务四值严格分离（主协议 §4.2/§8.4 继续有效）。

---

## 3. 义务协议（义务清单）

义务 = 判决中需要权威保证的规范性断言集合。要保证什么由"说了什么"决定；
说什么由 live 的实际输出与 judge 认为 live 应有的输出决定——
**义务集合天然因项目而异、因 case 而异，不存在全局固定清单**。

### 3.1 双轨结构

| 轨 | 时机 | 作用 | 地位 |
|---|---|---|---|
| 前置开列 | 判前，确定性计算 | 把"本案需求保证事项"注入 judge 上下文，引导其先求担保再下判 | 仅引导，允许漏 |
| 判后核对 | 判后，判决进入 history/晋升之前 | 解析判决动用的规范性断言，逐条核对担保 | **责任主体**，不允许漏 |

只靠前置于行不通：028 案中前置信号未触发、judge 自断契约口径，
证明开列清单必有漏洞；判后核对兜底（§附录 A.2）。

### 3.2 前置开列（引导）

- 输入：trace 命中锚点 × 调查报告 MaterialDecisions 的 governs 管辖映射；
- 输出：义务项列表，每项含 {subject 锚点, governed_by（MaterialDecision 引用）,
  conclusion_kind, availability（工具当前是否可用）}；
- 注入 judge 上下文（client_search 中扩展现有 `authority_obligation_contract`）；
- **无论 authority 工具是否构造都注入**：工具不可用时，义务项标注
  availability=unavailable，提示 judge"该事项无担保通道，若断言须承担
  not_evaluable 后果"，引导其避免越资料断言。

### 3.3 判后核对（责任主体）

见 §4。义务销账规则：一次 `resolve(question, claim)` 担保模式调用，按
`claim.subject` 销账同锚点的义务项；判决时做差集，未销账义务项进入判后核对。

---

## 4. 判后核对门禁

### 4.1 输入与任务

- 输入：判决本身（expectations / assessments / reasoning_summary /
  expected / missing / wrong / extra）+ 本次随附压缩资料 + 本次 authority
  调用 audit + 调查报告（全量 MaterialDecisions）。
- 任务：提取判决依赖的规范性断言，逐条标三种状态之一：

| 状态 | 判定 | 处置 |
|---|---|---|
| 资料背书 | 断言内容在随附压缩资料内（封闭集合对账可得） | 通过——压缩资料与 authority 同源（同一套调查资产的摘录直投交付） |
| authority 背书 | 存在担保模式调用且 status=supported | 通过 |
| 无担保 | 两者皆非 | 产出 finding + 按 §4.2 惩罚阶梯处置 |

### 4.2 惩罚阶梯（已拍）

1. **未担保**（无担保且非 contradicted）：依赖该断言的 assessment 降
   `not_evaluable` + finding。语义：不是判你错，是"你没证明"。
2. **contradicted**：依赖该断言的肯定性 verdict 不得成立；assessment 标
   `needs_human_review` + finding。语义："说错了"。
3. **loop 层**：带惩罚记录的 case 不计入 draft 赢案；findings 全量进入
   晋升判定书（§7.3）。

### 4.3 归责三类 finding（已拍）

| finding 类型 | 情形 | 罚 judge？ | 整改指向（remediation_target） |
|---|---|---|---|
| `judge_failed_to_call` | authority 工具可用，judge 未求担保即断言 | 罚（§4.2） | judge 提示词 |
| `availability_miss` | 工具未构造，判决动用随附资料外断言 | **不罚** | 可用性门禁 / 调查层 |
| `compaction_miss` | 断言在全量资料（调查报告）中有、压缩投影没带出 | 不罚 | solidify / 压缩逻辑 |

每条 finding 结构：{finding_type, subject, assessment_id, 证据摘要,
remediation_target}。remediation_target 必须落到具体资产，
这是门禁回放考试及格线之一（§6.2）。

### 4.4 核对机制：两层（已拍）

1. **确定性对账层**：字段/枚举/操作符/映射是封闭集合，判决引用项与随附压缩
   资料做集合对账，纯代码。先例：client_search judge.py 已有
   `_apply_operator_capability_check`、`_apply_explicit_unsupported_boundary_gate`
   等判后确定性核对，本层是其口径扩展。
2. **窄域 LLM 审计层**：语义级断言（散文里的规则，如"成交→按保单生效日"）
   确定性对账抓不到，由窄域审计识别——输入仅判决+资料，任务仅"列出判决动用
   了哪些资料中不存在的规则"，不得扩权。

禁止纯 LLM 审计（不稳、贵）或纯确定性（漏散文规则）的单层方案（§11 D4）。

---

## 5. 可用性与治理真相源

### 5.1 可用性保持窄口（已拍）

authority 环境的构造条件维持现状（client_search：
`_authority_candidate_reasons` 冲突驱动信号），**暂不放宽**为
"命中受管辖锚点即构造"——后者在 client_search 会使几乎每案都构造
（几乎每案都碰字段/枚举），agent 会话与 LLM 调用暴涨，即"authority 泛滥"。

放宽是 **loop 的输出，不是设计的输入**：`availability_miss` findings 的累积
是唯一放宽依据——某受辖域反复出现"该有工具没构造"，才对该域放宽触发条件，
且放宽后必须重跑门禁回放考试（§6.2）。

### 5.2 管辖真相源（已拍）

治理判断（"什么受什么资料管辖"）的真相源是调查报告的
**MaterialDecisions 治理映射**（materials × governs × conclusion_kind ×
conditions）。

key-index 是**通用导航机制**（调查层通道索引、field 查询、authority 导航索引
都是其消费方），与 authority 只有相关性、无必然联系；代码自身定义其为
"只收窄该看哪份资料，不是证据、不能被引用为依据"。**任何治理判断不得挂在
key-index 的存在性或命中上。**

---

## 6. 验证设施

### 6.1 四象限探针（已拍）

四象限（有/无 authority × resolved/unresolved）**已实证存在**（§附录 A.1），
探针规格：

| 象限 | 定义 | 期望值（机器可查） |
|---|---|---|
| Q1 | authority 可用 + 可裁决 | 担保调用 supported，verdict 依赖成立 |
| Q2 | authority 可用 + 不可裁决 | unresolved/gap_only → 依赖项 not_evaluable + gap finding |
| Q3 | 无 authority + 以其他证据下判 | 断言均获随附资料背书，无误报 finding |
| Q4 | 无 authority + 真缺口 | not_evaluable，且不罚 judge（无工具可罚） |

- 每象限 ≥3 条，共 ≥12 条；**改造冻结真实案例构造**（同一 trace，变动
  authority 可用性/命中锚点），不做全合成 trace（§11 D8）；
- "无 authority + 真缺口"象限直接复用调查报告已登记的 coverage_gaps
  （client_search 现有 2 条：semantic-mapping-authority、
  query-form-equivalence-authority）；
- 探针期望值机器可查；**每轮 loop 探针先于业务案例运行，探针不过当轮作废**。

### 6.2 门禁回放考试（已拍）

门禁本身需要考试：回放已标注历史给门禁打分，防止漏检与误报。

- 标注集：已知脏案（028 类重述绕过 / 008 类 tool_failure 伪装 / 133 类
  pull 失效）+ 已知干净案（production 判对且标签闭环的案例）；
- **标签分两档**：闭环 / 边界。仅闭环标签计入及格线；边界案只观察门禁行为、
  不计分（回应"考试前提=答案正确，但前提不一定总能保证"）；
- 三条及格线：
  1. 已知脏案检出率 ≥90%；
  2. 干净案误报 ≤1；
  3. 每条 finding 可行动——必须映射到具体整改资产（§4.3 remediation_target）；
- 门禁任何改动后必须重跑回放考试，防止门禁自身退化。

---

## 7. 晋升判据（此前已拍，不再翻案）

### 7.1 晋升条件

- 差异案例 ≥10 条，且差异案中 draft对 : production对 ≥ **3:1**；
- 帕累托不掉点：不允许任何指标（P/R/A 或后续指标）下降；实在无法提升也须
  帕累托最优；
- 新增 FP 强否决：draft 比 production 多判错哪怕 1 条 ok 案例即不晋升，
  除非 recall 提升足够大且该 FP 经人工复核确认"判得其实有道理"
  （GT 边界案/reference 本身错的平反路径）；
- FP 的下游代价 = 复核 + 阻断发布。

### 7.2 reference 与台账（无真正 GT）

- reference 不由人直接给定，由 agent 从资料**闭环推导**，产出推导台账：
  {case_id, reference_conclusion, evidence_chain, derivation_status
  （closed / escalated / boundary）, exhaustion_note, human_review}；
- 允许缺口，但必须证明已穷尽当前可得信息、确实无法更进一步；
- 未定性项在 runtime 中记 not_evaluable，供人类后续决定是否补资料；
- 用户只审升级案（escalated）与改判案；审完冻结为"裁决版 reference"。

### 7.3 晋升判定书（6 字段，全机器可查）

1. 差异清单（caseid / live 输出 / production judge / draft judge）；
2. 逐案对错判定（引用 reference 台账条目）；
3. 3:1 与阈值核查结果；
4. 四象限探针结果；
5. 门禁 findings 汇总（按 §4.3 归责分类）；
6. FP 平反栏。

废除主观"依据准确性"评分项，替换为 citation 必备 + 门禁验证。
harness AI 做晋升判断，但输入必须全部可判断/确定性。

---

## 8. 消费规则补丁（对主协议 §8 的扩展）

- 主协议 §8.1–8.5 全部继续有效；
- 新增：判决动用规范性断言前，消费顺序为
  随附压缩资料对账 → （工具可用时）resolve 担保模式 → 两者皆不可得则
  该断言不得支撑肯定性结论（降 not_evaluable）；
- 担保模式四值的分支消费：supported → 按 statement 继续评价；
  contradicted → §4.2-2；ungoverned / gap_only → 依赖项 not_evaluable，
  gap_only 额外挂 required_evidence（与主协议 §8.4 unresolved 口径对齐）。

---

## 9. 泛化约束

### 9.1 协议层不得假设"字段"概念

不是所有 live 系统都有字段。claim.subject、义务锚点、对账集合在协议层
统一为**项目自定义锚点**：协议只要求锚点非空、同项目内可确定性比较；
client_search 实例化为字段/枚举值，其他项目可为接口名、条款号、流程节点等。
义务销账（§3.3）按同项目同型锚点对账。

### 9.2 机制落点

判后核对门禁按通用协议定义（输入 = 判决 + 随附资料 + 调用记录；
治理依据 = MaterialDecisions 管辖映射，项目无关），先在 client_search
draft 落地验证；**过晋升判据后才允许提取到 core**。不直接写死在
client_search，也不一步登天进 core。

---

## 10. 实施顺序（已拍）

| 步 | 内容 | 改动范围 |
|---|---|---|
| ① | resolve claim 参数 + 四值 + 两阶段 | AuthorityRequest/AuthorityResolution 扩展、AuthorityTool、resolve_authority |
| ② | 前置义务开列（引导） | judge 上下文注入（扩展 authority_obligation_contract） |
| ③ | 判后核对（确定性层 + LLM 审计层）+ 三类 finding 归责 | reconcile 阶段扩展（现有判后核对口径泛化） |
| ④ | 12 条四象限探针 | probes/（改造冻结真实案例） |
| ⑤ | 门禁回放考试（含三条及格线） | 门禁验证设施 + 标注集 |
| ⑥ | draft SKILL / 相关 spec 更新 | .agents/skills/draft、spec 引用同步 |
| ⑦ | 30 条全量重跑 + 结构化晋升判定书 | loop 产出 |

### 10.1 实施状态与证据口径

- ①、②已落地并有单元/协议回归；
- ③的控制面归责、四值误消费检查、`checked_claims` 与 `assessment_actions` 已落地；
- ④当前只有四象限**控制面合成探针**，它只证明门禁分支接线，不能冒充“每象限 3 条冻结真实案例”的端到端验证；
- 因此在 12 条真实四象限案例和历史回放考试通过前，不得把步骤④/⑤记为完成，也不得开始晋升判断；
- 测试运行必须记录 Python 环境与依赖；默认系统 Python 缺少项目依赖时，应使用项目配置的 executable，不能把收集失败写成业务失败。

约束（贯穿全程）：不改 Production Judge；不改冻结案例；不按 case ID 打补丁；
泛化优先；汇报用表格、不模棱两可。

---

## 11. 决策记录（重要取舍及理由）

| # | 决定 | 否决的替代方案 | 理由 |
|---|---|---|---|
| D1 | resolve 加 claim 参数，单工具 | 新增独立 authority.verify 工具 | judge 路由成本（实测 BASE 仅 4/30 调用，工具越多越难选）；audit/cache/门禁沿用单入口 |
| D2 | 可用性保持冲突驱动窄口，放宽数据驱动 | 先验放宽为"命中受管辖锚点即构造" | authority 泛滥：client_search 几乎每案都会构造；放宽应有 finding 证据 |
| D3 | 治理判断以 MaterialDecisions 为准，不挂 key-index | 以 key-index 命中判定管辖 | key-index 是通用导航机制，代码定义其非证据；与 authority 只有相关性 |
| D4 | 确定性对账 + 窄域 LLM 审计两层 | 纯 LLM 审计 / 纯确定性 | 纯 LLM 不稳且贵；纯确定性漏散文规则（028） |
| D5 | 四值 supported/contradicted/ungoverned/gap_only | 复用 resolved/unresolved | unresolved 混淆"没人管"与"管了不够"，诱导 judge 自断（028 实证） |
| D6 | claim.subject 用通用锚点 | subject_fields（字段列表） | 不是所有 live 系统有字段概念，协议层必须项目无关 |
| D7 | 归责三类 finding，availability_miss 不罚 judge | 无差别惩罚 judge | 没给工具就不能罚自断；finding 必须可行动、指向具体资产 |
| D8 | 探针改造冻结真实案例 | 全合成 trace | 生态效度；成本小；coverage_gaps 现成可复用 |
| D9 | 判后核对为责任主体，前置开列仅引导 | 只靠前置义务清单 | 028 证明开列清单必有漏洞；义务跟着"说了什么"走 |
| D10 | 消费保持 pull（"带牙的 pull"） | push（强制注入 authority 结论） | 用户明确否决 push；牙长在义务核对与惩罚上 |

---

## 附录 A：实证依据（2026-08-07，60 份运行）

### A.1 四象限验证（冻结 30 条）

| 象限 | 实证案例 | 条数 |
|---|---|---|
| 有 authority + resolved | 088、113（两臂均 resolved） | 2 |
| 有 authority + unresolved | 023（两臂）、008-D | 2 |
| 无 authority + 以其他证据下判 | 其余 25 条（含 028） | ~21 |
| 无 authority + 无法下判 | GT-unclear 068/118/128/148（均无候选） | 4 |

象限外失败态（探针重点靶）：
- **有工具不调**：133（候选存在，judge 从未调用）——pull 失效；
- **该管辖却没构造工具**：028（候选理由未触发，judge 自断口径）——可用性漏报；
- 基础设施噪声：008-BASE 为 tool_failure、D 臂为 unresolved（同案两臂不同面具）。

### A.2 关键失败模式

1. **authority 几乎不被消费**：BASE 4/30 调用、策略 D 1/22；
2. **028 重述绕过**：judge 自断"成交→按保单生效日"，绕过 authority 合同；
   措辞门禁可被重述绕过 → 需要结构化 claim + 判后核对；
3. **temperature=0 仍有 6/30 flip**（噪声 ±10pp）→ 晋升判据要求差异案 ≥10
   与 3:1，抵御噪声；
4. **9/60 首轮 LLM 连接错误**：基础设施失败伪装成空 not_evaluable →
   门禁需区分 tool_failure 与业务 unresolved（主协议 §4.2 已有口径）。

### A.3 指标快照（flag = not_fulfilled 或 not_evaluable；正类 = GT bad+unclear 14 条）

| 臂 | P | R | A |
|---|---|---|---|
| Production | 85.7% | 42.9% | 70.0% |
| 旧 Draft（002-run） | 69.2% | 64.3% | 70.0% |
| BASE（门禁前重跑） | 56.2% | 64.3% | 60.0% |
| D（Claim-Decision 对齐门禁） | 58.8% | 71.4% | 63.3% |

剔除 6 条 GT 边界案后：**D 为最优**（P=90.9% / R=71.4% / A=79.2%），
但 D 相对 BASE 的净增益仅 1 案（023），统计上弱 → 本 spec 的机制
（担保模式 + 义务 + 判后核对）是对 D 的泛化与加固，不是对 D 的确认。

### A.4 关键文件

- 冻结案例：`impl/projects/client_search/draft/probes/judge-badcase-final-30.json`
  （id: source-badcase-003~148，步长 5）
- 结果：`/tmp/pos2_{BASE,D}_{003..148}.json`；GT：`/tmp/pos2_ground_truth.json`
- authority 工具现状：`impl/core/authority_tool.py`（单参数 decision_question）
- 调查报告：`impl/projects/client_search/draft/investigation/judge/docs/authority-investigation-report.json`
  （11 materials / 15 decisions / 2 coverage_gaps）
