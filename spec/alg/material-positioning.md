# Material Positioning 协议（资料定位）

> 定义资料相对被测系统（Live）的**定位**分类：`conclusion_kind` 四值、Gate 行为、
> 以及条件定位（`inlive_boundary`）的信任模型登记规则。
> 调查侧按本协议给资料打标；Runtime Authority/Judge 按本协议消费 Gate。
> 相关 spec：`spec/alg/authority.md`（裁决流程）、`spec/alg/fulfilled.md`（三态判定）、
> `spec/alg/investigate-authority-judge.md`（MaterialDecision/CoverageGap schema 与调查协议）。

# 第一章：定位框架

## 1. 目标与范围

每份进入调查报告或证据空间的资料，都必须能回答两个问题：

1. **你站在哪里**：相对被测系统，你是独立的尺子、被测对象本身、还是边界的代理？
2. **你能证明什么**：哪类问题可以由你裁决（Gate）？

本协议定义：判定轴、分类框架、`conclusion_kind` 四值与 Gate 行为、防循环不变量、
条件定位的信任模型登记。

本协议不定义：资料的 schema 结构（→ investigate-authority-judge.md §9
MaterialDecision）、Authority 的裁决流程（→ authority.md §5/§8）、三态判定
（→ fulfilled.md）。

## 2. 唯一判定轴：独立性

`conclusion_kind` 承载的不是"三种客观现实"，而是**资料相对被测系统的定位**。
唯一判定轴 = **资料所陈述的内容是否独立于被测系统**（不由被测系统自身的行为或
配置决定）。

- 打标依据是**独立性**，不是**出处**：出处在系统内的资料也可能描述由外部决定的
  事实（见 §3 接缝格）；出处在系统外的资料也可能只是转述系统行为；
- 判定顺序：
  1. 陈述内容是否由被测系统自身决定？是 → `current_behavior`；
  2. 否：说法是规定性（"应该"）还是描述性（"是"）？
     - 规定性 → `normative_rule`；描述性 → `external_fact`；
     - 例外：内容指向 Live↔外部边界的可达空间、出处在 Live 内、**且真边界
       不可直接观测**（拿不到下游/外部的一手数据）→ `inlive_boundary`
       （§3 接缝格、§4.1 判据）。真边界可观测时直接取外部一手数据，
       标 `external_fact`，不需要"代理"。

## 3. 分类框架：2×2 + 接缝格

| 站位 \ 说法 | 说"应该"（规定性） | 说"是"（描述性） |
|---|---|---|
| 独立于被测系统 | `normative_rule`（独立的尺子） | `external_fact`（独立的现实） |
| 被测系统自己 | **故意留空** | `current_behavior`（被量的东西） |
| 接缝：出处在系统内、内容指向外部边界 | 不适用 | `inlive_boundary`（边界代理） |

**故意留空的那格是防循环不变量**：不存在"被测系统自己说自己应该如何"的权威定位——
系统自己的输出不能证明系统自己对。任何打标都不得落入该格。

**接缝格**：有些资料出处在被测系统内（如 Live 的字段/枚举配置），但其陈述的空间
由下游/外部决定（parser 造不出空间外的东西）。它既不是完全独立的现实
（标 `external_fact` 等于在出处上说谎，且绕过 Gate 前提），也不是系统行为的自我
描述（标 `current_behavior` 会被 Gate 卡死）→ 单列第 4 值 `inlive_boundary`。
一句话定义：**inlive_boundary = 真边界不可观测时的可达代理**；真边界可观测时
直接用 external_fact，不产生代理定位。

# 第二章：conclusion_kind 四值与 Gate

## 4. 四值定义与 Gate 行为

| kind | 定位 | 回答的问题 | 能否解除正式规则 Gate |
|---|---|---|---|
| `current_behavior` | 被测系统自己（描述性） | 当前系统现在如何做 | 不能 |
| `normative_rule` | 独立的尺子（规定性） | 业务、产品、监管或契约要求应该如何做 | 可以 |
| `external_fact` | 独立的现实（描述性） | 外部系统或现实当前实际是什么 | 可以 |
| `inlive_boundary` | 边界代理（描述性，有条件） | 系统在 Live↔外部边界上能表达/到达什么（可达能力空间） | **有条件**（见下） |

**定位之间的信息关系（唯一排序规则）**：同一业务事项被多份资料覆盖时，
外部信息优先于系统内信息：

```text
normative_rule / external_fact  >  inlive_boundary  >  current_behavior
（外部独立信息）                  （边界代理，         （系统自身行为，
                                    须用户同意登记）      只解释现状）
```

- `inlive_boundary` 的启用前提 = 项目已登记信任模型（§5，业务方声明，即"用户同意"）；
- 未登记时，系统内配置资料的定位仍是 `current_behavior`，排序不变；
- runtime 如何消费该排序（Gate 检查、resolve 流程）见 `authority.md` §8（已补
  引言段），本 spec 不定义消费机制。

**不变量**：

1. `current_behavior` 类 Decision 只能解释系统现状，永远不能代替 `normative_rule`
   或 `external_fact` 类 Decision；覆盖缺口必须标注缺的是哪一类定位的资料，不得用
   当前行为类资料冒充正式规则或外部事实；
2. `inlive_boundary` 类 Decision 的合法性来自"空间由下游决定、parser 造不出空间外
   的东西"：**只升级空间（有什么），不升级选择（本次选哪个）**；解析规则、时间换算、
   归一选择属于系统行为，仍受 `current_behavior` 限制；
3. 发现 Live 输出空间外的字段/值（漂移）是**发现信号**，不是掩盖点；漂移出现时
   信任模型按 §5.3 失效/降级。

### 4.1 inlive_boundary 的打标判据

可标 `inlive_boundary` 的陈述必须同时满足：

- 陈述对象是 Live↔外部边界上的**可达空间**：字段空间、枚举值空间、操作符空间、
  值映射的目标值空间；
- 该空间由下游/外部决定，Live 只能在其内选择，不能扩充；
- 项目已登记承载该空间的信任模型（§5），且本条 Decision 的 `conditions` 可回指登记。

反例（不得标 `inlive_boundary`）：解析规则、时间换算、归一化选择、prompt/路由配置
——这些是系统行为，定位仍是 `current_behavior`。

# 第三章：信任模型登记（inlive_boundary 的启用规则）

## 5. 信任模型

`inlive_boundary` 是**条件定位**，不默认启用：项目必须显式登记信任模型；
未登记的项目一律走默认路径（M0），其系统内配置资料仍是 `current_behavior`，
Gate 行为不变。

### 5.1 判定清单（声明 M1 必须全部满足；任一不满足走默认路径）

- C1 输出受控可枚举：Live 输出字段/值来自有限稳定可列举空间，非自由文本；
- C2 空间有可观测代理：存在可读、可定位、可核验的空间代理资料，且业务方声明
  "代理=下游空间"；
- C3 输出真实作用于下游并被校验：空间外输出要么被下游拒绝、要么被自身校验拦住
  （可观察）；
- C4 业务方显式声明：边界文档授权（如"数据库信息从配置/枚举获取""只有外部约束
  是硬标准"），非 verifier 自封；
- C5 评价目标是选择正确性：用户意图落到"选哪个字段/值"，不是内容质量；
- C6 空间/选择可分离：假设只升级空间（有什么），不升级选择（本次选哪个）。

### 5.2 登记形式（不新增 schema 字段）

- **项目级**：项目边界文档（用户原文，如 judge_boundary-template.md）承载信任模型
  声明：采用哪个模型 + C1-C6 逐条满足说明 + §5.3 失效条件；该文档本身按
  `normative_rule` 登记为证据（业务方声明）；
- **材料级**：`inlive_boundary` 类 `MaterialDecision.conditions` 引用该声明
  （如 `trust_model: M1 受控输出空间`、`输出空间=下游能力边界代理`）；
- **校验层**：确定性核对信任模型登记存在、每条 `inlive_boundary` decision 的
  conditions 可回指登记（investigate-authority-judge.md §13 校验层职责）。

### 5.3 失效条件（登记在项目声明里）

- R1 空间漂移且不可观测 → 假设失效，需只读导出/观测验证；
- R2 空间外输出出现 → 发现信号，不得掩盖；
- R3 下游校验链路不可达 → 假设降级，退回语义判断 + not_evaluable。

### 5.4 信任根只有两种

| 信任根 | 内容 | 定位后果 |
|---|---|---|
| 外部信息（优先） | 独立于被测系统的导出、文档、业务确认 | 资料可标 `normative_rule` / `external_fact`，无条件可用 |
| 用户同意（次之） | 业务方显式声明"系统内空间 = 外部边界代理"（M1，见 C1-C6） | 空间类陈述可标 `inlive_boundary`；未声明则仍是 `current_behavior` |

当前只定义 M0（默认：外部信息）与 M1（受控输出空间）两种。其他信任根
（如运行期事实上报）待真实场景出现后再定义，不预设。

**reference/参考答案不构成信任根**：大部分 reference 是 AI 标注的伪参考答案，
本身需要被验证，不能作为权威来源；gold answer 类资料按其实际来源归类
（业务方确认过的 → external_fact / normative_rule；AI 生成的 → 不构成信任根）。

# 第四章：与相关概念的区分

## 6. 区分表

| 概念 | 所在 spec | 回答什么 | 与本协议的关系 |
|---|---|---|---|
| `LiveBoundary` | investigate-judge.md | 完整产品期望中哪部分归责于 Live（归责边界） | 不同概念：LiveBoundary 管"归责给谁"，`inlive_boundary` 管"这份资料能当什么证据"；不得混用 |
| Authority 能力/职责边界裁决 | authority.md §8.1/§8.2 | 产品有没有某能力、某事项属不属于职责 | `inlive_boundary` 资料是 resolve 这类问题的证据 |
| `locator` / keyindex `target_ref` | investigate-authority-judge.md §9、investigate-keyindex.md | 资料的物理/结构定位 | 定位（positioning）是语义分类，与物理定位正交 |
| `CoverageGap.conclusion_kind` | investigate-authority-judge.md §11 | 缺的是哪一类定位的资料 | 缺口标注必须与缺失资料的定位一致；缺能力空间资料时记 `inlive_boundary` |
| 产品功能三态 | product-function.md | 用户要办的这类事，现在是不是产品已经有的功能 | 不同问题：本协议管资料站在哪；产品功能管事情种类现在立住了没有。不得用 `inlive_boundary` / 字段空间去代替"有没有这项功能" |

## 7. 引用关系（各 spec 分工）

- `investigate-authority-judge.md`：MaterialDecision/CoverageGap 的
  `conclusion_kind` Literal 与 §11.2 业务边界以本协议为准（§9/§11 Literal 已含
  四值，§11.2 已改为引用本协议）；
- `authority.md`：§5 resolved 最低要求、§8 Gate 消费中涉及的资料定位判断以本协议
  为准（§8 引言已补信息关系段）；§8.5 缺料清单补证类别含 `inlive_boundary`
  （已补）；
- `fulfilled.md`：§9 补齐权威依据的缺料口径按本协议判定缺的是哪类定位（已对齐）；
- `investigate-judge.md`：§5.2 Authority Gate 与 Task 8 约束引用本协议四值与
  信任模型登记（已对齐）；
- `investigate-keyindex.md`：§12.2 索引命中加载后按本协议信息关系筛候选（已对齐）。

# 第五章：防滥用（防 AI hack）

## 8. 硬性禁令

1. 不得把任意系统内配置描述标成 `inlive_boundary` 来绕过 Gate——打标必须能回指
   "空间由下游决定"的具体依据（业务方声明 + 空间代理资料）；
2. 不得用 `inlive_boundary` 裁决 normative 问题或"本次选得对不对"；
3. 不得把漂移（空间外输出）解释为"空间的一部分"来掩盖；
4. 边界类资料的权威**不来自行为自我背书**：合法性根是"下游决定空间 + 业务方声明
   + 可观测代理"，不是"系统现在就是这么做的"。
