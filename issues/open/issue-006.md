# Issue #006: 裸词姓名证据标准自相矛盾——常见中文名过严，单字/称谓反过松

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output + code-analysis
**Layer**: Configuration / Interaction（draft judge 系统提示内部条款互相否决；模型每次只咬一句）
**Cases**: I485 昊轩、I539 王坤林（canvas 互有对错）；I288 配、I616 海蜂老板娘周老板（canvas 过严）

## Verifier Discovery

同 live 下新 judge 把「昊轩」「王坤林」打 NF（旧 F），把空条件的「配」「周老板」也打 NF（旧 F）。四条不是同一方向的严：前两条是「已经抽出姓名仍因缺目录级人名证据不算办成」；后两条是「没抽姓名，却要求必须抽」。同一轮提示里的裸词规则被正反各用一次。

### 同 live

| ID | query | live | 旧 | 新 |
|---|---|---|---|---|
| I485 | 昊轩 | `searchClientName MATCH 昊轩` / 客户姓名为昊轩的客户 | F | NF |
| I539 | 王坤林 | `searchClientName MATCH 王坤林` / 客户姓名为王坤林的客户 | F | NF |
| I288 | 配 | `conditions=null` / 未识别到明确查询条件 | F | NF |
| I616 | 海蜂老板娘周老板 | `conditions=null` / 未识别到明确查询条件 | F | NF |

源：`verifier-client_search-cases-20260814-185013.xlsx` vs `…205846.xlsx`。抽取见 `issues/trace/split-overstrict-8cases.json`。

### 新 judge 实际怎么判

I485 reasoning：「昊轩是未带姓名指示词的裸词。字段资料只证明姓名字段语义，未独立证明该词为人名」。expected 仍写了应输出 `searchClientName MATCH 昊轩`，同时又因缺独立确认判 NF。

I539 expected 改成「需要确认姓名意图后再执行」+ 澄清文案；blocking 项是「避免裸词误判」。三字「姓+名」被当成必须澄清的歧义。

I288 expected：必须 `searchClientName MATCH 配`。reasoning：「已加载规则明确覆盖一至三个中文字符的姓名模糊匹配」。空条件 = 缺核心姓名筛选。

I616 expected：必须 `searchClientName MATCH 周老板`。把称谓当自然人姓名。

### 提示原文（同一段里）

`impl/projects/client_search/draft/judge.py`：

- L1497：「字段定义只证明该字段声明的语义」
- L1504–1508 裸词规则：「Without independent name evidence, do not mark that dimension fulfilled. 独立姓名证据指资料明确该 token 是人名（**或该形态就是姓名检索**）；live 把它写成姓名、路径碰巧叫 searchClientName，都不够支撑 fulfilled（§2.1）。」
- L1493–1496：enhanced_rules 是可撑 F 的二级；matched_pattern 是不能单独撑 F 的三级
- L1514–1519：明确业务对象但无条件 → 按当前交付判 NF

I485/I539 只执行了「要独立证据」+「字段定义不算证据」，丢掉括号里的形态条款。I288 把三级 path match「姓名-模糊匹配」抬成必须交付。I616 用「明确对象+空条件=NF」压过裸词规则自己写的「无法确认是人名就不要 F」。

### 协议

- fulfilled §2.1：F 要证据证明用户要的结果拿到了。王坤林这类客户搜索最常见形态，live 已经给出姓名条件；把「目录无人名条目」当成唯一独立证据，会系统误伤正常裸名检索。
- fulfilled §2.1 同一条也禁止无证据 F。旧 judge 用能力清单/增强规则自证「昊轩=人名」，证据链偏弱（material-positioning 不变量 1：current_behavior 不能冒充正式规则）。所以 I485/I539 标「互有对错」成立，不是「新一定错、旧一定对」。
- I288/I616 不是互有对错：空条件拒识更贴近字段 notes「无法确认是自然人人名时宁可不输出」。新要求必须输出，和它对 高/任/昊轩 的 NF 直接打架。

### 与 canvas 的差别（不要整段照抄）

- I539 过严比 I485 硬：三字「王+坤林」形态就是姓名检索；二字「昊轩」无姓，歧义更大，更接近真·互有对错。
- 形态条款写成可 F 证据是方案，不是协议已经裁定的结论。章程 §4：姓名形态能否单独撑 F → 留给用户。本 issue 只钉「四条用的不是同一把尺」。

### 未消元

- 未重跑 judge，只读已落盘 xlsx。
- 未独立 Load 本轮 catalog 里 searchClientName notes 全文；notes 表述来自 canvas 与历史 retry-report 摘录，peer 应回源核对。

---
## architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 5f7ddad9f3a27ddc
- pid: unknown

### Investigation
独立回源，不照抄 canvas / verifier：

- 通读 `draft/judge.py` L1477–1526「client_search 直接证据」整块。逐条核对行号与原文：
  - L1504–1508 裸词规则，确实含括号形态条款「独立姓名证据指资料明确该 token 是人名（**或该形态就是姓名检索**）」，且「live 把它写成姓名、路径碰巧叫 searchClientName，都不够支撑 fulfilled（§2.1）」。
  - L1497 确有「字段定义只证明该字段声明的语义」。
  - L1493–1496 证据分级：enhanced_rules 为二级（「只有实际引用到的二级证据才能支撑 fulfilled」）；L1496 matched_pattern / 字段操作符合法性为三级，「不能单独证明用户意图已满足」。
  - L1514–1519 确有「明确业务对象但 actual 无可执行条件…按当前交付判 not_fulfilled」。
- 复核 `issues/trace/split-overstrict-8cases.json`：I485/I539 live 为 `searchClientName MATCH`（已抽姓名），I288/I616 live 为 `conditions=null`（未抽），四条均 old=F / new=NF。与「同 live」表一致。
- 抽查 `context_store/client_search/client_search:I263:1786695659788/judge-*.json` 原始 response，与 trace 摘录一致，确认 trace 非摘断/捏造（此条虽属 008，但验证了 trace 保真）。
- 消元 verifier「未消元#2」（searchClientName notes 全文）：字段 yaml 是 `business://` 外部 URI，repo 内无源文件；但 notes 句「无法确认是自然人人名时宁可不输出」在 `draft/.state/judge/history/052/iterations/001-run.json` 多案 reasoning 中逐字复现（关爱、年华案），且同处把 `姓名-模糊匹配` 规则 `{SEARCH}([一-鿿]{1,3})` 明确定性为「低优先级」「缺少人名语义支撑」「不应覆盖『宁可不输出』」。notes 的保守口径真实且稳定，可回源成立。

### Reasoning
四条确实不是「同一把尺」，而是同一条裸词规则被正反各用一次，方向相反：

1. I485/I539：live 已抽出姓名，新 judge 却只要「目录级独立人名证据」，咬「要独立证据」+「字段定义不算证据」两句，丢掉括号里的形态条款「或该形态就是姓名检索」。对最常见 2/3 字中文名过严。
2. I288：live 空条件未抽，新 judge 反而要求必须抽 `searchClientName MATCH 配`，把三级 path match「姓名-模糊匹配（1–3字）」抬成「应交付」的二级强制项。而对昊轩又拒绝接受形态证据——同一条证据分级被反向使用。
3. I616：把称谓「周老板」当必须交付的自然人姓名，既违反裸词规则自己的保守性，也违反 notes「无法确认是自然人人名时宁可不输出」。

决定性对照是 I288 vs I485：同一条规则，对单字「配」要求必须输出，对更像完整人名的「昊轩」却拒绝输出。这不是严松刻度差异，是口径反转。history/052 进一步证明：I288 所依赖的「姓名-模糊匹配」规则在历史口径里被写成「过度捕获、不能当人名证据」，新 judge 却把它当成交付依据。四条无法由同一套提示一致推出。

我认可 verifier 的两点克制：(a) I485/I539 标「互有对错」成立——旧 judge 用能力清单/增强规则自证「昊轩=人名」，是 current_behavior 自我背书，撞 positioning 不变量1，旧证据链同样弱；(b) 「姓名形态能否单独撑 F」是政策选择，章程 §4 留给用户。本 issue 只钉「四条用的不是同一把尺」，该主张站得住。不是 reasonable-design：矛盾真实存在，不是目标约束下的有意取舍。

### Improvement Proposal
（permission mode = review，且章程红线禁改 judge；以下为建议，交由有写权限角色在用户裁定后实施）
- **Target**: `impl/projects/client_search/draft/judge.py` §裸词规则 L1504–1508 与 §证据分级 L1490–1503。
- **Change**: 让裸词规则单调一致。无论用户选哪个方向——
  - 方向 A：把「2–4 字中文姓名形态且未命中产品/活动/枚举」写成可撑 F 的独立姓名证据（放回昊轩/王坤林，保持 VIE/ZHANG/共展/周老板 保守）；或
  - 方向 B：维持要求目录级人名证据（昊轩/王坤林继续 NF）。
  两个方向都必须同时：(i) 把「姓名-模糊匹配」钉死为三级，只解释 live 如何生成、永不写成「应生成姓名条件」（修 I288）；(ii) 称谓/单字不得被强制抽成姓名（修 I616）。一致性 + (i) + (ii) 在两方向下都成立，唯一随用户裁定的是形态条款是否可 F。
- **Verification**: 同 live 重跑 I485/I539/I288/I616 + 对照 高/任/VIE/共展；断言四条落到同一明文口径，且 I288/I616 不再要求抽单字/称谓。

---
## Consensus
**Verdict**: real-problem
**Summary**: 四条不是同一把尺。I539/I485 已抽出姓名却因「目录无人名证据」NF（互有对错：旧用增强规则自证也脏）；I288/I616 空条件拒识反而被要求必须抽单字/称谓。决定性对照是「配」必须输出、「昊轩」不准输出。形态条款能否单独撑 F 留给用户（章程 §4）；无论选哪边，模糊匹配必须降回三级，称谓/单字不得强制抽取。

