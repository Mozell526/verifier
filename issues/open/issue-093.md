# Issue #093: 这块东西不是 not_fulfilled 的原因说明项

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 安放 / 绝对排除原因说明项
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户本轮的疑惑是：

> 我目前仍然觉得，这东西像是 not fulfilled 的一个原因说明项，如果你的方案不这样定，你需要说明排除他的绝对理由

「像」来自现行协议已经把「功能本身未实现」写成没办成的理由（`fulfilled.md` §2.2）。这不是幻觉。本号要打的是：这块东西能不能因此住进原因栏。

原因说明项在本轮的工作定义：

```text
住进现行原因栏，去解释「为什么这一次没办成」。
现行落点：summary_from_fulfillment → display_reason → 评估卡「原因：」
```

不是「只在没办成那一行才给人看」。那是看见时机，章程 §4 停住。时机不改身份。

排除必须是绝对的：放进原因栏，会改掉用户已锁的对象、单位、不看什么、或三态出口里至少一项。给不出这一条，本号失败，方案就该改去就原因栏。

### 放进原因栏会改掉什么

1. **单位被改掉。**
   已锁单位：这件事 × 产品事实。不看这一次交付。
   原因栏只因这一次被判没办成才存在。`summary_from_fulfillment` 在 `not_fulfilled` 分支写的是 `not_fulfilled · blocking=[ids] · ...`，答的是刚才那个词为什么是没办成。
   放进去，单位从「产品事实」变成「这一次失败原因」。

2. **三态出口被收掉。**
   已锁出口：立住了 / 没立住 / 说不清。
   原因栏没有「立住了」这个第一性出口。「立住了」不能解释为什么没办成。
   040 碰撞针已经写过：漏了姓名 = 没办成 × 立住了。这一格若成立，原因栏只能写下「没立住」，写不下「立住了」。
   放进去，三态被收成「没立住」一个原因值。已锁出口被改掉。

3. **「不区分技术原因」被改掉。**
   已锁：不区分没立住的技术原因。
   原因栏正是原因分类处。`fulfilled.md` §2.2 列的是漏条件 / 改错值 / 功能未实现……
   放进去，这块东西变成这些原因里的一项。已锁「不区分」被改掉。

4. **前缀消费顺序被倒过来。**
   `authority.md` §8.3 原文：职责内能力缺失 → 不强制改状态；期望未达成 → not_fulfilled；实际达成 → fulfilled。
   产品事实在选 fulfilled 的词之前就已经裁完，而且同时喂给办成了和没办成。
   原因栏发生在选词之后，只挂没办成。
   放进去，「已经裁完的能力/职责判断」不再是前缀，变成后记。已锁「产品事实从哪来」被改掉。

5. **「办成了 × 没立住」被抹掉。**
   040 第 4 条：办成了，不能自动排除没立住。
   `fulfilled.md` §3 第二步与 §8.3 同一条：职责内能力缺失 + 实际达成 → 办成了。
   按 fulfilled.md，这能算办成。办成看的是这一次给到了没有，不看功能立住了没有。用户先前觉得自相矛盾，矛盾只在把「已立住」偷塞进办成的定义里。协议没有这一条。
   原因栏在办成了时写的是 `fulfilled · N blocking expectations all met`。没立住进不去。
   放进去，已锁还能写的组合少一格。

以上任一条单独已经够绝对。五条同时成立，不是口味。

### 可证伪

同时成立才算本 issue 站住：

1. 「原因说明项」被排除，是因为它会改掉已锁的单位 / 出口 / 不区分 / 前缀来源，至少一项；
2. 论证不得依赖「因为这是第二问」；
3. 不得把「只在没办成时才给人看」当成身份。

若 Consensus 写成「它就是 NF 的原因说明项」，必须同时改掉已锁出口里的「立住了」或改掉「不看这一次交付」。本轮不得重开已锁内容，故该写法失败。
若 Consensus 只说「更干净所以分开」，本 issue 失败。

## Proposed Change

Consensus 只锁：这块东西不是 not_fulfilled 的原因说明项。排除是绝对的，不是口味。看见时机仍停住。

## Evidence

用户本轮原文：「我目前仍然觉得，这东西像是not fulfilled的一个原因说明项」。

已锁单位 / 出口见章程 §2。

`fulfilled.md` §2.1 办成了的三个条件：职责内、材料足够、证据证明结果拿到了。没有「功能已立住」。

`fulfilled.md` §2.2：

> 不区分原因：
> - 漏条件、加多条件、改错值、条件关系理解错；
> - …
> - 功能本身未实现，但用户期望已提出。

「功能未实现」在这里是没办成的一种理由。这是「像」的来源。它不是这块东西的宿主。

`fulfilled.md` §3 第二步：

> resolved=职责内能力缺失 → 结合第三步实际交付：
>      期望未达成 → 没办成
>      实际达成   → 办成了

`authority.md` §8.3：

> statement = 职责内能力缺失（应具备但未实现/表达不了）
>     → 不强制改状态；Judge 结合 live 实际交付判断：
>         期望未达成 → not_fulfilled
>         实际达成   → fulfilled
>     → 不能因为“功能未实现”自动降级为 not_evaluable

`impl/core/summary.py` `summary_from_fulfillment`：
- fulfilled → `fulfilled · {n} blocking expectations all met`
- not_fulfilled → `not_fulfilled · blocking=[ids]...`
- not_evaluable → 这一次为什么说不准

`impl/core/frontend_view.py` `_judge_panel`：`display_reason` 取自这份 summary。
`impl/frontend/summary.html` 评估卡：`<b>原因：</b>` + `display_reason`。

040 Consensus 第 4 条：办成了，不能自动排除没立住。
040 碰撞针：漏了姓名 = 没办成 × 立住了；没立住但这回绕过给到了 = 办成了 × 没立住。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 7c30ec2320df0b23
- pid: 2590

### Investigation

独立重读，不抄 verifier 转述，也不把 089–092 当已经结案。

用户已锁内容（章程 §2 / 040 Consensus 内容，不沿用「第二问」外号）：

- 只看：用户要的这件事，产品把它立成自己会做的事了没有
- 对象：仍是 fulfilled 那一件；不得另立类型表；不得切粗或切细
- 单位：这件事 × 产品事实；不看这一次交付
- 产品事实从哪来：已经裁完的能力/职责判断及其依据资料
- 出口：立住了 / 没立住 / 说不清
- 040 第 4 条：办成了，不能自动排除没立住
- 040 碰撞针（只作可证伪，不进定义）：漏了姓名 = 没办成 × 立住了；没立住但这回绕过给到了 = 办成了 × 没立住

协议原文：

- `spec/alg/fulfilled.md` §1 L28–L30：本协议只评办成了没有；邻题不并进，不新增第四态。
- 同文件 §2.1 L34–L40：办成了三条件是职责内、材料足够、证据证明结果拿到了。没有「功能已立住」。
- 同文件 §2.2 L42–L52：没办成不区分原因；「功能本身未实现，但用户期望已提出」列在理由里。这是「像原因说明项」的真来源，不是幻觉。
- 同文件 §3 L86–L89：职责内能力缺失 + 期望未达成 → 没办成；+ 实际达成 → 办成了。
- `spec/alg/authority.md` §8.3 L499–L503：职责内能力缺失不强制改状态；期望未达成 → not_fulfilled；实际达成 → fulfilled；不能因为「功能未实现」自动降 not_evaluable。

现行原因栏，我对着代码看了，不是对着 issue 转述看的：

- `impl/core/summary.py` `summary_from_fulfillment` L52–L168
  - fulfilled → `fulfilled · {n} blocking expectations all met`（L134–L137）
  - not_fulfilled → `not_fulfilled · blocking=[ids]…`（L139–L144）
  - not_evaluable → 这一次为什么说不准（L111–L157）
  - 三个分支都写 `reason`。原因栏**不是**「只因这一次被判没办成才存在」。
- `impl/core/frontend_view.py` `_judge_panel` L104–L108：`display_reason = summary["reason"]`
- `impl/core/frontend_view.py` `_fulfillment_panel` L61–L86：矩阵按期望分行，每行只有一个 `status`
- `impl/frontend/summary.html` L377 `fulfillmentPill` 只认三词；L766–L772 矩阵 Status 一列；L783 评估卡 `<b>原因：</b>` 吃 `display_reason`

090 Consensus 杀的是「只补 not_fulfilled / 只挂在没办成后面」。它没有点名 `display_reason` 这一格。用户本轮问的嘴，090 没打死。

### Reasoning

原因说明项在本轮的工作定义成立：住进现行原因栏，去解释「为什么这一次没办成」。这不是看见时机。看见时机（只在没办成那一行才打开）仍停在章程 §4，不能冒充安放。

排除不是口味。放进这张嘴，会改掉已锁内容里不止一项。

1. **单位被改掉。** 已锁单位是这件事 × 产品事实，不看这一次交付。`summary_from_fulfillment` 的单位是刚才那个 fulfillment 词为什么是这个词：三次交付聚合。住进去，单位从产品事实变成这一次失败原因 / 这一次词的注释。

2. **三态出口被收掉。** 「立住了」不能解释为什么没办成。漏了姓名这一格若成立，原因栏只能写下「没立住」，写不下「立住了」。已锁出口少一态。

3. **040 第 4 条被改掉。** 办成了 × 没立住 进不了「解释为什么没办成」。原因栏在办成了时写的是 `fulfilled · N blocking expectations all met`。没立住进不去。已锁还能写的组合少一格。

4. **对象被切粗。** 已锁对象是 fulfilled 那一件（期望行）。现行 `display_reason` 是案件级一句。塞进去，是为了更好答这一块把对象切粗。这条 verifier 没单列，但是绝对的。

我查过一条可能把排除打穿的漏洞：原因栏对三种 status 都有字，能不能把三态当后缀写进 `display_reason`，从而保住 办成了 × 没立住？不能。那样写出来会是 `not_fulfilled · blocking=[姓名] · 立住了`。读者要么听成自相矛盾，要么把「立住了」听成没办成的原因。单位和第一性出口仍被改掉，对象仍被切粗。漏洞救不了这张嘴。

两条 verifier 论证我**不**接受为单独足够的绝对理由：

- 「不区分技术原因」：原因栏是分类处，不自动等于这块东西会被拆成缺字段 / 缺接口。只有把它写成 §2.2 那些理由里的一项时，这条才咬住。本号不必靠它。
- 「前缀消费顺序被倒过来」：显示位置不等于裁断位置。可以先读已经裁完的前缀，再把字显示到某处。绝对的是：不能让原因栏成为**判定处**（从这一次失败回推产品事实）。单凭「字出现在原因栏」不够死。本号死的是「去解释为什么这一次没办成」这个身份。

论证没有写成「因为这是第二问」，也没有把「只在没办成时才给人看」当成身份。排除过了本轮绝对门槛。若 Consensus 改口写成「它就是 NF 的原因说明项」，必须同时改掉已锁出口里的「立住了」，或改掉「不看这一次交付」，或改掉「不得切粗」。本轮不得重开这些，故该写法失败。

### Improvement Proposal

- **Target**: `issues/open/issue-093.md` 待写 Consensus。不改 `spec/**`、`impl/**`、前端。
- **Change**: Consensus 只锁下面这段：

```text
这块东西不是 not_fulfilled 的原因说明项。排除是绝对的，不是口味。

原因说明项 = 住进现行原因栏
  （summary_from_fulfillment → display_reason → 评估卡「原因：」）
  去解释「为什么这一次没办成」。

放进去会改掉已锁内容：
- 单位：这件事 × 产品事实，不看这一次交付
  → 变成这一次失败原因 / 刚才那个 fulfillment 词为什么是这个词
- 出口：立住了 不能当没办成的原因；三态被收成「没立住」
- 040 第 4 条：办成了 × 没立住 写不进「解释为什么没办成」
- 对象：原因栏是案件级一句；已锁对象是 fulfilled 那一件。塞进去是切粗。

即使拿「原因栏对三种 status 都有字」当漏洞，把三态后缀进 display_reason，
仍然改掉单位和第一性出口，且切粗。救不了。

看见时机（只在没办成时才给人看）仍停在章程 §4。时机不是身份。
不得写成「因为这是第二问」。
不得写成「更干净所以分开」。
```

- **Verification**:
  1. Consensus 若把这块东西收回原因栏当宿主，且不改已锁单位 / 出口 / 不看这一次交付 / 不得切粗，本号失败。
  2. Consensus 若只写「更干净所以分开」，本号失败。
  3. Consensus 若用「因为这是第二问」或「只在没办成时才给人看」当排除句，本号失败。
  4. 代码对照仍应看得到：`summary.py` L134–L144 的 reason 寄生在 fulfillment 词上；`summary.html` L783 评估卡「原因」吃的是这句。

### What I Changed

- `issues/open/issue-093.md`: 只追加本段 Architect Response #1。未改项目源码、协议、数据、其它 issue 正文。

---
## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `7c30ec2320df0b23`

接受 architect 的收紧。这块东西不是 not_fulfilled 的原因说明项。排除是绝对的，不是口味。

原因说明项 = 住进现行原因栏
  （summary_from_fulfillment → display_reason → 评估卡「原因：」）
  去解释「为什么这一次没办成」。

放进去会改掉已锁内容：

- 单位：这件事 × 产品事实，不看这一次交付
  → 变成这一次失败原因 / 刚才那个 fulfillment 词为什么是这个词
- 出口：立住了 不能当没办成的原因；三态被收成「没立住」
- 040 第 4 条：办成了 × 没立住 写不进「解释为什么没办成」
- 对象：原因栏是案件级一句；已锁对象是 fulfilled 那一件。塞进去是切粗

即使拿「原因栏对三种 status 都有字」当漏洞，把三态后缀进 display_reason，
仍然改掉单位和第一性出口，且切粗。救不了。

不接受为单独足够的绝对理由（architect 改掉 verifier 原稿）：

- 「不区分技术原因」：只有把它写成 §2.2 那些理由里的一项时才咬住，本号不必靠它
- 「前缀消费顺序被倒过来」：显示位置不等于裁断位置；死的是「去解释为什么没办成」这个身份

看见时机（只在没办成时才给人看）仍停在章程 §4。时机不是身份。
不得写成「因为这是第二问」。
不得写成「更干净所以分开」。

闸：exit 0，isolation_valid true，scope_valid true。spawn-id 对齐。wrapper pid 2305 / 回应写 2590。
