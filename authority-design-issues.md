# Authority 设计分歧盘点（2026-08-04 收敛版）

> 本文档只记录**当前最新**口径与收敛状态，历史论证过程不保留。
> 相关 spec：`spec/alg/authority.md`、`spec/alg/fulfilled.md`、
> `spec/alg/investigate.md`、`spec/alg/investigate-authority-judge.md`。
> 2026-08-04 上午轮已拍板：否掉「配对回写」「缺料自动输入」「findings 结论形状」三类
> "结论资产"；缺口走「Harness AI 生成 + 校验层确定性校验」；闭环走「评测报告 → 人 → 手动调查」；
> 呈现走 `not_evaluable` 的 reason / required_evidence。
> 2026-08-04 晚整体盘点 + key-index 模拟实测新增断点见 §4（先调研不实现）。
> 2026-08-04 晚定位收敛轮：新起 `spec/alg/material-positioning.md`，conclusion_kind
> 单列第 4 值 `inlive_boundary`（见 §4.4、§5）。
> 2026-08-05：信任框架简化（M0-M3 枚举删除、reference 不构成信任根）、越层修正（见 §5）。

## 1. 已收敛（最终口径，不再讨论）

1. 调查层按**资料**调查，交接物 = **证据空间**（物化可追溯资料），不是结论；
2. 能力声明（MaterialDecision）= **证据索引/预判**，不是裁决依据；裁决依据永远是实际
   Load 的原始资料；
3. **结论整合是 runtime Judge 的本职**，不是调查层的职责；不存在任何"结论资产"——
   「配对/回写」「结论块」「缺料自动输入」已全部否掉，runtime 不沉淀、不汇总任何结论；
4. 三态四成因：职责外 / 完全无关 / 依据不充分 / 输入坏；authority 管②（能力/职责边界
   裁决），Judge 管①③（用户意图 + 实际交付）并消费②；
5. 「空间里没有」≠「职责外」；职责内能力缺失 → 结合 actual → not_fulfilled / fulfilled；
6. **调查层触发只能由用户手动发起**；runtime 不直接驱动调查层，顶多「提醒」
   （通过 not_evaluable + 缺料清单记录影响）；
7. **「问题」的标准**：对 authority 闭环而言，唯一算"问题"的信号是 `not_evaluable`
   （依据不足）；`not_fulfilled` 是业务侧事实、`fulfilled` 正常，都不触发调查；
8. **findings 整个删除**：调查侧不产出任何"结论形状"对象（无 resolved/unresolved、
   无参考稿、无配对）；调查侧只产「资料能力声明 + 资料连接 + 覆盖缺口」；
9. **校验层**：覆盖缺口由 Harness AI 在调查中自然产出（含 required_evidence），校验层
   做**确定性校验**（"没有 MaterialDecision 管 X"是可核验事实），校验通过后才驱动同一轮
   定向补证；
10. **呈现**：`AuthorityResolution.unresolved.required_evidence` → Judge 的
    `not_evaluable` reason / required_evidence，per-case 记录，评测报告汇总同类缺料，
    人看到共性后手动触发新一轮调查。

## 2. 三个拍板点（2026-08-04 全部拍板）

### 2.1 findings 去留：删除

- 可行性试跑确认：result 文本与 `MaterialDecision.statement` 冗余；kind 语义已由
  `conclusion_kind` 承载；"提示 runtime"的职能与"runtime 现场综合"冲突；人工审核可直接
  审材料层；
- 唯一"真损失"（调查侧的结论整合对象）本就是伪需求——结论整合已收敛为 runtime Judge
  本职（§1.3）；
- 调查侧替代物 = **覆盖缺口（CoverageGap）**：材料层的确定性事实（"某业务事项 × 条件
  没有唯一决定资料 / 重叠无法消解"），带 `gap_reason` 与 `required_evidence`，不是对
  某个业务问题的结论。

### 2.2 缺料/补证驱动：Harness AI 生成 + 校验层校验

- Harness AI 在调查中自然发现"该依赖没资料定 / 冲突"，产出覆盖缺口与 `required_evidence`
  （不是预写结论）；
- **校验层**确定性校验缺口成立：核对需求方向声明过的依赖 × materials 实际决定范围；
  核对重叠是否已用条件区分或 `supersedes` 消解；不通过则退回修正或删除该缺口；
- 校验通过 → 同一轮内定向补证（沿来源/审批/生效/替代/上下游/验证连接继续查）；
- 冻结条件：缺口被消解，或所有可取得证据方向均已跟进并记录停止原因。

### 2.3 呈现：要的

- `AuthorityResolution.unresolved.required_evidence` → Judge 判 `not_evaluable`，
  reason / required_evidence 记录本 case 缺什么；
- per-case 记录、不自动汇总进调查层；评测报告汇总同类缺料，人看到共性后**手动触发**
  新一轮调查；
- Runtime 不沉淀、不自动输入调查层；调查层触发只由用户手动发起。

## 3. spec 修正状态（2026-08-04 全部完成）

| spec | 本轮修正 |
|---|---|
| `authority.md` | §6 调查侧不产出配对、Runtime 不沉淀结论资产；§14.2 去除结论形状对象；§22 task 10 不建立跨 case 复用资产 |
| `investigate-authority-judge.md` | §11 findings → CoverageGap；§12 报告 schema 改 coverage_gaps；§13 校验层补证循环；§14 Validator 缺口口径；§16/§17 单层证据空间 + 只提醒手动触发；§26 验收 |
| `investigate.md` | §1.7.2 覆盖缺口口径；§1.9 无配对、无回写；§1.10 缺料记录 → 报告汇总 → 人手动触发 |
| `fulfilled.md` | §2.3 硬前提第 1 条改"同任务内 decision_question 去重命中"；§9 任务 2 改覆盖缺口 + 校验层口径 |

基线：`spec/bak/2026-08-04-authority-design/`（改 spec 前的原始四份）。

## 4. 整体盘点 + key-index 模拟实测后的断点（2026-08-04 晚新增，先调研不实现）

### 4.1 实测结论（e2e 6 场景 + 单层 8 问，确定性检索，不依赖 embedding）

- 链路在 spec 层面能串：investigate → solidify（evidence_refs 物化 ContextUnit）→
  authority.resolve（search_index 集合层 → load_entry → 单资料层下钻 → 现场综合）→
  gate → 三态 → per-case 缺料 → 人手动触发下一轮调查。
- 实验 A（当前真实调查包：10 material 全 `current_behavior` + 4 缺口，按旧口径）：
  **0/6 resolved，全部 not_evaluable**；nav 与 flat 一致。key-index 检索/下钻仍正常
  （S3 abbrname 找到全部排除值、S4 planfullname 找到「住院医疗保险」）。
  ⚠️ 该结论已在 §4.4 场景假设下修正：能力类问题不再被 current_behavior 阻塞，
  S1/S2/S4 可用现有料 resolve，S5 需登记用户原文，S3/S6 归 Judge 语义。
- 实验 B（正对照：补证 + 正确分类为 normative/external）：**6/6 resolved，6/6 与业务
  期望一致**（S1/S4 not_fulfilled，其余 fulfilled）。
- 上下文：flat 整读 planfullname_enums 371KB / abbrname_enums 313KB 不可持续；
  nav 集合层 top-4 ≈ 1-2KB。
- 结论：key-index 解决「找得到、读得动」，不解决「资料本身不是 normative/external」。

### 4.2 断点清单（按影响排序）

1. **调查层质量（最大，非 spec 分歧，是当前项目调查包事实）**
   10/10 material 全 `current_behavior`（= 只描述「系统当前如何做」；权威等级不够裁决
   「应该如何做(normative_rule)/外部事实(external_fact)」，investigate-authority-judge.md
   §11.2）→ 一切 normative/external 类 decision_question 必然 unresolved→not_evaluable。
   且用户原文 `judge_boundary-template.md` 在仓库（projects/client_search/ 与 impl/ 各
   一份）**未登记进 manifest evidence_refs**，只登记了 AI 落地的
   `judge_boundary_protocals.md`。→ 这是当前「串不起来」的真因。

2. **`locator` vs `target_ref`（spec 措辞，一行；根因是「key」撞名）**
   概念澄清：key-index 的「key」指「能定位到真实内容的那把钥匙」，在 schema 里由
   `target_ref` 承担（对象 ID / 对象内部 locator / 容器引用）；字段 `entry.key` 只是
   索引内编号，与概念「key」撞名，是歧义根源。
   现状问题：`investigate-authority-judge.md` §308「大资料的 locator 可以使用 keyindex
   定义的 key」——承担定位职责的是 `target_ref`，不是字段 `key`。
   → **已拍板（用户确认）**：`MaterialDecision.locator` 本质就是 keyindex entry 的
   `target_ref` 的一种（对象内部 locator，如 YAML path）；`entry.key` 只是索引内编号，
   不是 locator。§308 改为「大资料的 locator 可直接作为 keyindex entry 的 target_ref；
   entry.key 是索引内编号，不是 locator」。待与断点 3 一并落地 spec 措辞（本轮先调研
   不实现）。

3. **`authority.md` §6「可选输入，不是硬前置」（spec 措辞，一行）**
   与 §5 第 4 步「按需调用检索/Key-index」、§6 Investigate 义务「大资料需要检索时
   提供 Key-index」矛盾。**已拍板并落地（2026-08-05）**：「可选」指调查层产出可选
   （不要求每次调查都产出 Key-index），不是 Authority 工作方式可忽略；authority.md
   §6 措辞已改。

4. **authority 只裁决能力/边界，Gate 不得把 resolved 直接映射 fulfilled**
   S4 实测：resolved（合法险种）后仍需 Judge 看 actual「只回姓名」→ not_fulfilled。
   分工本身 OK（authority.md §8.3 + fulfilled.md §5），实现已 fail-closed；仅记录口径，
   无 spec 改动。

5. **MaterialDecision.governs 粒度 —— 已关闭（2026-08-05）**
   维持既有口径：governs = 这份资料直接决定的业务事项，不强制写细。用户语言的
   匹配由 keyindex §12.4 的 search_text 投影承担（实测有效），不新增规则。

6. **枚举索引必须按字段分开（keyindex 应用层要求，无 spec 分歧）**
   S3 实测：排除集合值（百万任我行/倍享百万/百万随行）在 abbrname 有、planfullname 无
   精确值；下钻错枚举会误判「值不存在」。落到 keyindex 应用二/§8.1 的落实要求。

### 4.3 下一步

- 断点 2/3/5/7 全部收敛：断点 2、3 措辞已落 spec；断点 5 维持口径不改（见 §4.2）；
- 断点 7 已收敛 → 新起 `spec/alg/material-positioning.md`（已起草，见 §4.4/§5）；
  新 spec 审过后改三个 spec 的引用处（§4.4 落点清单）；impl 改动需另行拍板；
- key-index 按 §17 P0→P3 落地（先通用协议 + 集合层 capability index）。

### 4.4 断点 7：「输出空间=权威」→ 已收敛：新起 material-positioning spec + conclusion_kind 第 4 值 inlive_boundary（2026-08-04 拍板）

**收敛链（最终口径）**：

1. `conclusion_kind` 三分类的本质不是「三种客观现实」，而是**资料相对被测系统的
   定位/站位**；唯一判定轴 = **是否独立于被测系统**；打标依据是独立性，不是出处；
2. 输出空间（Live config 的字段/枚举/值映射）：内容描述的是外部边界（下游能力空间
   的代理），出处却在 Live 系统内 → 标 external_fact 会在出处上说谎并开 hack 口子，
   标 current_behavior 又被 Gate 卡死 → 单列第 4 值 **`inlive_boundary`（边界代理）**；
3. Gate：`inlive_boundary` **有条件解除**——仅能力/可表达性问题（字段能否表达 X、
   值 V 是否合法、空间是否含 Y、字段支持什么操作符），且项目已登记信任模型
   （代理不漂移前提）；不能回答 normative 问题，不裁决「选的对不对」（Judge 语义本职）；
4. 与 `LiveBoundary`（investigate-judge.md）划清：LiveBoundary = Judge 侧归责边界
   （期望的哪部分归责给 Live）；inlive_boundary = 资料定位（这份资料能当什么证据）；
5. 决定新起 **`spec/alg/material-positioning.md`**：承载定位框架、conclusion_kind
   四值与 Gate、信任模型登记（C1-C6 / R1-R3 / M0-M3）。

**对 §4.1 实测的修正**：client_search 的输出空间资料应打 inlive_boundary 而非
current_behavior；S1（无地址字段）、S2（clientAge RANGE）、S4（planfullname 含
住院医疗保险）无需「配置=外部事实」证明即可 resolve；S5 归责边界用 judge_boundary
用户原文（normative_rule）；S6 目标值是合法枚举值、语义正确即 fulfilled；
S3 排除集合构成归 Judge 语义本职（关闭，不需要业务确认）。

**落地清单（新 spec 审过后执行）**：

- spec：`investigate-authority-judge.md` §2.2/§9/§11/§11.2（§11.2 瘦身为引用）、
  `authority.md` §8.5 缺料补证列表、`fulfilled.md` §9 第 2 条；
- impl（需另行拍板）：`investigation_judge.py` `_VALID_CONCLUSION_KINDS` 加值；
  client_search 调查报告输出空间资料重分类 current_behavior → inlive_boundary；
- 信任前提不新增 schema 字段：项目边界文档（用户原文）承载信任模型声明，
  MaterialDecision.conditions 引用之。

**残留分歧**：无。S3 排除集合构成归 Judge 语义本职，不需要业务确认（2026-08-05 关闭）。

## 5. 信任框架 → 已简化并入 material-positioning.md（2026-08-05 更新）

信任框架按用户口径简化后并入 `spec/alg/material-positioning.md` §5。本节只留
决策记录：

- **统一信息关系（唯一排序规则）**：normative_rule / external_fact >
  inlive_boundary（须用户同意登记）> current_behavior（永不作裁决依据）；
- **信任根只有两种**：外部信息（优先，无条件）+ 用户同意（M1 受控输出空间，
  C1-C6 核对 + R1-R3 失效条件保留为登记要求）；原 M2（reference 信任）/
  M3（运行期事实）枚举**删除**——待真实场景出现再定义，不预设；
- **reference/参考答案不构成信任根**（2026-08-05 用户口径）：大部分 reference 是
  AI 标注的伪参考答案，本身需要被验证；gold answer 按实际来源归类；
- **inlive_boundary 定义收紧**：= 真边界不可观测时的可达代理；真边界可观测时
  直接 external_fact，不产生代理定位；
- **越层修正（已拍板）**：material-positioning.md 只管定位语义、打标判据、信任
  登记；runtime 消费规则（Gate 机制、resolve 流程）归 authority.md §8，spec 内
  不写消费条件；
- 打标粒度 = MaterialDecision（陈述级），同一资料可含不同定位的 decision；
  定位是项目相关的（调查按项目搞，未登记项目里同一资料仍是 current_behavior）。
