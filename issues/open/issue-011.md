# Issue #011: 同形态裸名在新 judge 内部已经左右互搏——杨杰/郑鑫/匡西永 F，昊轩/王坤林 NF

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output + code-analysis
**Layer**: Configuration / Interaction（同一段裸词规则，模型每次咬不同半句）
**Cases**: I224 杨杰、I310 郑鑫、I336 匡西永（F）；I485 昊轩、I539 王坤林（NF）。对照：I650 共展 NF 方向对。

## Verifier Discovery

006 钉的是跨类型：常见中文名过严，单字/称谓反过松（昊轩 vs 配）。本 issue 钉的是**同类型内部**：都是 2–4 汉字裸词 + 同一 live `searchClientName MATCH <token>` + 同一个新 judge，标签已经反了。这不是「新更严所以更好」，是同一把尺自己在抖。

### 同 live、同新 judge

数据：`/Users/xiaozijian/Downloads/verifier-client_search-cases-20260814-185013.xlsx`（新）对照 `...-205846.xlsx`（旧）。原文在 `issues/trace/name-class-table.json`。

精确 2–4 汉字裸词 75 条（47 NF / 28 F）。其中 live 带 `searchClientName` 的 31 条里，F 只有 3 条：

| ID | q | live | 旧 | 新 | reasoning_summary 咬到的条款 |
|---|---|---|---|---|---|
| I224 | 杨杰 | `searchClientName MATCH 杨杰` | F | **F** | 「用户仅输入“杨杰”，实际输出将其作为客户本人姓名」 |
| I310 | 郑鑫 | `searchClientName MATCH 郑鑫` | F | **F** | 「用户输入是明确的二字客户姓名」 |
| I336 | 匡西永 | `searchClientName MATCH 匡西永` | F | **F** | 「姓名形态检索有已加载增强规则与字段定义佐证」 |
| I485 | 昊轩 | `searchClientName MATCH 昊轩` | F | **NF** | 「字段资料只证明姓名字段语义，未独立证明该词为人名」 |
| I539 | 王坤林 | `searchClientName MATCH 王坤林` | F | **NF** | 「当前证据未独立确认其为客户本人姓名」 |
| I650 | 共展 | `searchClientName MATCH 共展` | F | **NF** | 「未独立证明其为人名」（这条 NF 对，机制不得吐回） |

I224 / I310 / I485 都是二字中文；I336 / I539 都是三字「姓+名」形态。差别不在 live，不在旧新对照，在新 judge 自己选了哪半句。

### 提示原文（同一段，无代码闸）

`impl/projects/client_search/draft/judge.py`：

- L1497：「字段定义只证明该字段声明的语义」
- L1504–1508：「If actual treats a token as a person name, Reference/path match alone is not intent proof. Without independent name evidence, do not mark that dimension fulfilled. 独立姓名证据指资料明确该 token 是人名（**或该形态就是姓名检索**）；live 把它写成姓名、路径碰巧叫 searchClientName，都不够支撑 fulfilled（§2.1）。」
- L1493–1496：enhanced_rules 是可撑 F 的二级；matched_pattern 是不能单独撑 F 的三级

F 三条咬括号里的「形态就是姓名检索」或把字段定义/增强规则抬成独立证据。NF 两条咬「字段定义不算证据 + 要独立人名证据」，丢掉括号。同一函数、同一段字符串，没有代码按形态分流。

### 协议

- fulfilled §2.1：F 要证据证明用户要的结果拿到了。对「王坤林」「杨杰」这种客户搜索最常见形态，live 已经给出姓名条件；把「目录里有没有这条人名」当成唯一独立证据，会系统误伤头部裸名。
- 同一条也禁止无证据 F。I650 共展、I607 豆芽走 NF 是对的——目录产品/歧义词不得因为「也是 2–4 字」就放行。
- 所以本 issue 的缺陷不是「新对姓名太严」或「新对姓名太松」，是**同形态没有稳定程序**：杨杰能 F，王坤林就不能只因为模型这回没咬到括号。

### 和 006 的边界

| | 006 | 011 |
|---|---|---|
| 对照 | 昊轩/王坤林 NF vs 配/周老板 空条件还要姓名 | 杨杰/郑鑫/匡西永 F vs 昊轩/王坤林 NF |
| 类型 | 跨类型（已抽姓名 vs 空条件） | 同类型（都已抽 2–4 汉字姓名） |
| 已共识 | 四条不是同一把尺 | 不重开；本 issue 用 006 未使用的 F 对照 |

006 的修复方向 A/B（形态能否单独撑 F）仍是章程 §4，本 issue 不代用户选。无论选 A 还是 B，杨杰和王坤林必须落在同一侧。

### 邻接、不作主证据

单字姓：I186「金」F（咬「姓名-姓氏前缀 / validated_surname_prefix」）vs I184「高」NF / I535「任」NF（咬「Catalog 无百家姓 / 字段只证明语义」）。同属「模型选句子」，用来说明 011 不是 2–4 字特例。I288「配」已在 006，不重开。

### 可证伪修复（确定性姓名程序，不是再写一句 prompt）

先目录/枚举，再形态，禁止模型自选半句：

1. token 命中产品/地址/客群/盘客等受控空间 → 不得当姓名；已当姓名则 NF（保住共展/金凤/十里堡）。
2. 剩余 2–4 汉字、且不在上述空间 → 同一出口（F 或「形态可 F」；具体能否单独撑 F 见 §4）。
3. 拉丁字母、单字、称谓/老板 → 不得仅凭形态撑 F（006 的过松侧）。

用这套程序、不点名 ID，必须同时：I224/I310/I336 与 I539 同侧；I650 仍 NF。

### 未消元

- 未重跑 judge。
- 未独立 Load 本轮 catalog 的 `searchClientName` notes / 百家姓规则全文；I168、I186 的 notes 引用待 peer 回源。
- 「2–4 汉字能否单独撑 F」仍留给用户，本 issue 只钉内部不一致。
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 37225eeb6839ec61
- pid: 45981

### Investigation

从新表重算姓名切片，并回读 live `conditions` 与 `Judge JSON`，不信任 `name-class-table.json` 的现成摘要。

精确 2–4 汉字裸词：n=75，新状态 47 NF / 28 F。其中 live `conditions` 含 `field=searchClientName`：n=31，F 只有 3 条——I224 杨杰、I310 郑鑫、I336 匡西永。与 verifier / `issues/trace/name-class-table.json` 一致。

同 live 模式 `searchClientName MATCH <token>`、同一个新 judge：

| ID | q | matched_patterns | 旧 | 新 | 模型实际咬到的条款 |
|---|---|---|---|---|---|
| I224 | 杨杰 | 疑似姓名候选、姓名-模糊匹配 | F | F | 「仅输入杨杰，当作客户本人姓名」；actual_evidence 把字段定义 + 模糊匹配规则当独立证据 |
| I310 | 郑鑫 | 疑似姓名候选、姓名-模糊匹配 | F | F | 「明确的二字客户姓名」+ 字段定义支持 MATCH |
| I336 | 匡西永 | 疑似姓名候选、姓名-模糊匹配 | F | F | 「已加载增强规则姓名-模糊匹配：`{SEARCH}([一-鿿]{1,3})` → searchClientName MATCH，佐证该形态即姓名检索」 |
| I485 | 昊轩 | 姓名-模糊匹配 | F | NF | 「字段资料只证明姓名字段语义，未独立证明该词为人名」 |
| I539 | 王坤林 | 疑似姓名候选、姓名-模糊匹配 | F | NF | 「当前资料未提供该词为人名的独立证据」 |
| I650 | 共展 | 姓名-模糊匹配 | F | NF | 「未独立证明其为人名」（方向对，机制不得吐回 F） |

关键对照不是「新更严」。I336 与 I539 的 live 字段、操作符、值形态、`matched_patterns` 四项相同，都是三字「姓+名」。差别只在新 judge 选了 L1504–1508 的哪半句。

提示原文（`impl/projects/client_search/draft/judge.py`）：

- L1493–1497：`enhanced_rules` 是可撑 F 的二级；`matched_pattern` / 字段定义是不能单独撑 F 的三级；「字段定义只证明该字段声明的语义」。
- L1504–1508：既要求「没有独立姓名证据不得 F」，又在括号里写「或该形态就是姓名检索」；紧接着又说 live 写成姓名、路径叫 `searchClientName` 都不够。

`ClientSearchJudge`（L1747 起）只组 context / 调 LLM / normalize / reconcile，没有按形态分流的函数。邻接单字「金」I186=F vs 「高」I184=NF / 「任」I535=NF 同属选句，不作 011 主证据，不重开 006。

昊轩不是最干净的对子：live 缺「疑似姓名候选」，「昊」也不是常见姓。王坤林才是主证——经典「王+坤林」、patterns 与匡西永相同，仍 NF。I168「傻生」还用了「傻非百家姓」作负证据；同一把「百家姓」没有被正向用到「王坤林」。

未重跑 judge。未独立 Load 本轮 catalog 的 `searchClientName` notes / 百家姓全文。章程 §4.1（2–4 字能否单独撑 F）不代选。

### Reasoning

011 成立，根因比「新对姓名太严」更深：同一段裸词规则没有稳定出口，模型每次咬不同半句。

fulfilled §2.1 要求 F 必须有证据证明用户要的结果拿到了。对「王坤林」「杨杰」这种客户搜索最常见形态，live 已经给出姓名条件。把「目录里有没有这条人名」当成唯一独立证据，会系统误伤头部裸名。同一条也禁止无证据 F：I650 共展、I607 豆芽走 NF 是对的，不得因为「也是 2–4 字」放行。

所以缺陷不是松/严选边，是 **同形态没有程序**。杨杰能 F、王坤林不能 F，只因为这回没咬到括号，或者这回没把已加载的「姓名-模糊匹配」算成独立证据。material-positioning 不变量 1：不能把「本轮 Search 碰巧 Load 到哪条 enhanced_rule」当成正式规则。I336 明确引用了该规则，I539 说「当前资料未提供」——即便真是检索运气不同，也是同一缺陷的两种表面。

和 006 的边界成立：006 是跨类型（已抽姓名 vs 空条件还要姓名）；011 是同类型内部（都已抽 2–4 汉字姓名）。006 的 A/B（形态能否单独撑 F）仍归章程 §4。无论选 A 还是 B，杨杰和王坤林必须落在同一侧。

再往 L1504–1508 加一句「王坤林算人名」或「三字从姓走 F」，正好踩泛化 a（过度规则化）和 b（只改局部样本）。出口必须由代码按「先目录、再形态」选定，模型只写证据，不选边。

### Improvement Proposal

- **Target**: `impl/projects/client_search/draft/judge.py`。禁止再改 L1504–1508 的括号文案。新增确定性姓名程序（catalog / 枚举 / 地址 / 盘客空间作输入，模型不得选出口）。政策旋钮「2–4 汉字能否单独撑 F」仍升级用户（章程 §4.1）。
- **Change**:
  1. 先目录/枚举/地址/客群/盘客等受控空间：token 命中 → 不得当姓名；live 已写成 `searchClientName` 则该维 NF。这锁住共展 / 金凤 / 十里堡 / 圈客。
  2. 剩余 2–4 汉字、且不在上述空间 → **同一出口**。出口值（F，或「形态可 F，仍要别的独立证据」）由用户选一次，写进代码常量/配置，不写进提示让模型每次重读。
  3. 拉丁字母、单字、称谓/老板 → 不得仅凭形态撑 F（006 过松侧，不重开 006，只复用同一程序）。
  4. `ClientSearchJudge.reconcile_result` 或等价的 pre-LLM context 组装处执行上述分流；LLM 只能消费「本 token 的姓名程序出口=…」，不能改写出口。
- **Verification**（不重跑 judge 即可先核程序；程序落地后再重算表）:
  - 用新表重算 31 条 `searchClientName` 裸词：杨杰/郑鑫/匡西永 与 王坤林必须同侧；昊轩若留在 2–4 汉字桶里也必须与杨杰同侧，或被事先剔出该桶并写明规则（「无姓二字」）——不得再靠模型临场决定。
  - I650 共展、I607 豆芽、I210/I211 金凤（产品字段 F，不是姓名 F）必须仍不得被姓名程序放行。
  - 不点名 ID 的验收：目录产品不走姓名；2–4 汉字非目录裸名同出口；单字/称谓不得仅凭形态撑 F。
- **Why I Cannot Apply It**: architect 只读；本轮章程 §6 不改 prompt、不实现方案 A–D。§4.1 的出口值仍要用户拍板。

---
## Consensus
**Verdict**: real-problem

同形态裸名在新 judge 内部左右互搏成立。双方独立重算：2–4 汉字裸词 75 条（47 NF / 28 F）；live 带 `searchClientName` 的 31 条里 F 只有杨杰 / 郑鑫 / 匡西永。

接受 architect 对主证的收紧：

- 最干净对子是 **I336 匡西永 F vs I539 王坤林 NF**：live 字段、操作符、值形态、`matched_patterns`（疑似姓名候选 + 姓名-模糊匹配）四项相同，都是三字「姓+名」。差别只在新 judge 咬了 L1504–1508 的哪半句。
- 昊轩不是最干净对子（缺「疑似姓名候选」，「昊」也不是常见姓），仍属同一缺陷族，但不再当主证。
- 「傻生」用百家姓作负证据，同一把尺没有正向用到「王坤林」——还是选句，不是稳定程序。
- I650 共展 / I607 豆芽 NF 必须保住；不得因为「也是 2–4 字」放行。

和 006 的边界保持：006 跨类型，011 同类型内部。章程 §4.1（2–4 字能否单独撑 F）不代选；无论选哪边，杨杰和王坤林必须同侧。禁止再往括号里加「王坤林算人名」这种局部例外。
