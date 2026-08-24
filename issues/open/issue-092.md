# Issue #092: 方案是这块东西自己的出口单独开一格，不是 fulfilled 的词

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 方案句
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

089 锁主语。090 锁不住进三个词。091 锁「标签」不是它的名字。本号交方案。

这块东西已经有出口手柄：立住了 / 没立住 / 说不清。现行看得见的格子里，没有这一格。

计算仍是 058：读已经裁完的前缀。不是判定再填。
存放仍是 060：现在不进 `JudgeFulfillmentAssessmentOutput`。以后若存，只物化同一份读。
挂点仍按同一件分行：现行出口上，唯一已经按 fulfilled 那一件分行的，是矩阵同一行、Status 旁边。现在那一格不存在。主表芯片一行一个案子，放进去会把对象切粗，这块定义禁止。

人现在只能看见 fulfilled，是因为这块东西的出口还没有自己的格子。不是因为它属于这三个词，也不是因为它只属于没办成。

本号方案句必须以这块东西为主语，先写放在哪，再写不是哪三个口。不得以「第二问」起头。不得把「新增一个 judge 结果标签」写成它的名字。不得再交否决清单当方案。

打开仍停在 061 / 章程 §4。对外叫什么仍停住。内部手柄不宣布采用。

### 可证伪

同时成立才算本 issue 站住：

1. 方案句主语是用户贴出的那一块；
2. 出口单独开一格，不进 fulfilled 的三个词；
3. 若出现在人正在看的评估结果上，挂在同一条期望、Status 旁边；
4. 不是判定再写，不是本轮打开，不是对外中文。

若 Consensus 写成「选了整句 B，让 Judge 再填」，本 issue 失败。
若 Consensus 写成「它就是第二问，沿用 088」，本 issue 失败。
若 Consensus 只交「四个口都不能」而不给方案，本 issue 失败。

## Proposed Change

Consensus 必须先写方案，再写陪绑：

```text
方案：用户认得的这一块，出口单独开一格。
      它不是 fulfilled 的词。
      若出现在人正在看的评估结果上，挂在同一条期望、「办成了没有」旁边。
      那一格字可以叫做一个结果标签，但这不是这块东西的名字。

谁写下的：不是同一张嘴再判一次。
进哪张嘴：不是改写办成了 / 没办成 / 说不清。

不是：只给 not_fulfilled 作补充
不是：fulfilled 从 3 态扩到 4 态
不是：放到 not_evaluable 里
不是：同一轮 Judge 再写一个 status
不是：把这块东西改名为「第二问」或「judge 结果标签」
不是：本轮改表、改前端、上线字段

打开那一格，仍交章程 §4 / 061。
对外叫什么，仍停住。
```

## Evidence（本轮对照，不是新主张）

方案必须从这块东西自己的单位推，不从「第二问 / 兄妹」推。

- 对象仍是 fulfilled 那一件 → 必须按同一件分行。现行出口上，唯一已经按那一件分行的，是 `_fulfillment_panel` 矩阵行（`frontend_view.py` L67–82：一行一个 expectation_id + 一个 status）。
- `renderFulfillmentMatrix` 列是 Expectation / Expected / Capabilities / Status / Blocking。Status 旁边现在没有另一格。
- 主表芯片 `fulfillment_status`（`table.py` / `table_view.py`）一行一个案子。放进去会把对象切粗，这块定义禁止。
- 计算：058 读已经裁完的前缀。不是判定再填。
- 存放：060 现在不进 `JudgeFulfillmentAssessmentOutput`。以后若存，只物化同一份读。
- 打开：061 / 章程 §4。本轮不打开。

`product-function.md` §1：「任何一张表、一个标签、一句结论，都不能同时回答两件。」
所以这块东西的出口不能进 fulfilled 的三个词。它要单独开一格。那一格字若出现在人正在看的评估结果上，可以叫做一个结果标签——这是安放，不是命名。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 44e93555a7a3fdcb
- pid: 79817

### Investigation

自己从这块东西的单位往现行出口推，不从 088 的方案名往回抄：

- 089 要锁的主语：用户贴出的那一块
- 090 要锁的：出口不是 fulfilled 的三个词，也不是只挂在没办成后面
- 091 要锁的：「judge 结果标签」最多描述安放，不是它的名字
- 040 Consensus：对象仍是 fulfilled 那一件；单位是这件事 × 产品事实；办成了不能自动排除没立住
- 047 Consensus：同一张嘴兼答几乎一定对齐刚才的办成了没有
- 058 Consensus：计算是读已经裁完的前缀，不是再开一张嘴
- 059 Consensus：粒在同一条期望行上；禁止塞进整案那一枚芯片
- 060 Consensus：规范格子在矩阵行上、Status 旁边；现在不进 `JudgeFulfillmentAssessmentOutput`；以后若存，只物化同一份派生读
- 061 Consensus：打开仍是章程 §4 项目决定
- 现行出口原文：
  - `impl/core/schema/judge.py` L94-L103：判定那张嘴只有 `status`
  - 同文件 L73-L76：`summary` 已是派生展示字
  - `impl/core/schema/table.py` L36：主表一行一个 `fulfillment_status`
  - `impl/core/table_view.py` L107-L109、L278-L301：芯片值来自 fulfillment_status / overall.status / 行 status
  - `impl/core/frontend_view.py` L61-L86：矩阵每行只有一个 `status`，来自 `assessment.status`
  - `impl/frontend/summary.html` L377、L766-L784：芯片只认三词；矩阵列没有这块东西的出口
- `spec/alg/fulfilled.md` §1；`spec/alg/product-function.md` §1 / §7-§9；`spec/alg/authority.md` §8.3；`spec/info-volume.md` L260-L277

未实现字段。未批准打开。未采用对外中文。未把 085-088 方案句的主语换皮沿用。

### Reasoning

本号必须先交方案句。四个口都不能，不是方案。088 也不能原句沿用：它的主语是「第二问」，方案名是「新增一个 judge 结果标签」。本轮这两层都被打掉。挂点可以看起来像 060 / 087，但必须从这块东西自己的对象推回来，不能写「因为它是兄妹，所以坐在兄妹旁边」。

1. **这块东西已经有出口手柄，现行看得见的格子里没有这一格。** 内部手柄仍是立住了 / 没立住 / 说不清，不宣布采用。人现在只能看见 fulfilled，是因为这一格还没开，不是因为它属于三个词，也不是因为它只属于没办成。

2. **计算和存放已经锁死，本号不重开。** 计算仍是 058：读已经裁完的前缀，不是判定再填。存放仍是 060：现在不进 `JudgeFulfillmentAssessmentOutput`；以后若存，只物化同一份派生读。`JudgeResult.summary` 是已经存在的同类：评估卡上的字，不必是模型新写的 `status`。

3. **挂点从对象同一性推出，不从「第二问」推出。** 对象仍是 fulfilled 那一件。现行出口上，唯一已经按那一件分行的，是矩阵同一行、Status 旁边。现在那一格不存在。主表芯片一行一个案子，放进去会把对象切粗；这块定义禁止切粗。Capabilities 列是 `required_capabilities`，不是这个出口。authority statement 原文是 058 的输入，不是立住了 / 没立住 / 说不清。所以：若出现在人正在看的评估结果上，挂在同一条期望、「办成了没有」旁边。

4. **「单独开一格」是派生看见格，不是新的判定字段。** 若听成「给 `JudgeFulfillmentAssessmentOutput` 再加一个模型可写 status」，就是 048 / 058 已经杀掉的整句。本号方案里的「一格」= 看见层单独占一格，谁写下的仍不是同一张嘴。091 允许把那一格字叫做结果标签，但必须立刻写「这不是这块东西的名字」。

5. **不是 088 换皮。** 088 起头是「新增一个 judge 结果标签 / 开第二问自己的格子 / 它是 fulfilled 的兄妹标签」。本号起头必须是用户认得的这一块。挂点相同，不恢复那套身份。丢掉「第二问」之后，不得把 NF-only / 3扩4 / NE / Judge 再填偷渡回来。

6. **打开仍停。** 章程 §4 / 061：要不要现在就让人看见、用哪句中文、现在改不改 schema，角色不得代选。本号锁的是出口放在哪，不是批准上线。不得整号 escalate，也不得只交否决清单。

### Improvement Proposal

**Problem**: 这块东西的出口还没有自己的格子；上一轮方案句用错了主语和名字。

**Proposed Change**: Consensus 必须先写方案，再写陪绑。下面整段就是本轮交给用户的方案句。

**Design**:

    方案：用户认得的这一块，出口单独开一格。
          它不是 fulfilled 的词。
          若出现在人正在看的评估结果上，挂在同一条期望、「办成了没有」旁边。
          那一格字可以叫做一个结果标签，但这不是这块东西的名字。

    谁写下的：不是同一张嘴再判一次。
    进哪张嘴：不是改写办成了 / 没办成 / 说不清。
    那一格：派生看见格，不是模型新写的 status。
            现在不存在。现在不进 JudgeFulfillmentAssessmentOutput。
            以后若存，只物化同一份读。

    不是：只给 not_fulfilled 作补充
    不是：fulfilled 从 3 态扩到 4 态
    不是：放到 not_evaluable 里
    不是：同一轮 Judge 再写一个 status
    不是：把这块东西改名为「第二问」或「judge 结果标签」
    不是：本轮改表、改前端、上线字段
    不是：沿用 088 的方案名和主语

    打开那一格，仍交章程 §4 / 061。
    对外叫什么，仍停住。
    内部手柄不宣布采用。

**Implementation Steps**:
1. Consensus 原样锁上面方案句。先方案，后陪绑。不得再以「四个口都不能」起头。
2. 不得写成「选了整句 B，让 Judge 再填」。
3. 不得写成「它就是第二问，沿用 088」。
4. 不改 `spec/**`、`impl/core/schema/judge.py`、`impl/core/frontend_view.py`、`impl/frontend/summary.html`。

**Risks**:
- 「单独开一格」被听成批准加列，或听成模型新字段。用「派生看见格 / 现在不存在 / 打开仍停」卡住。
- 「可以叫做一个结果标签」被听成 088 方案名回归。用「这不是这块东西的名字」卡住。
- 挂点被听成「因为它是兄妹」。用对象同一性重推，不用外号。

**Verification**: 本号 Consensus 必须同时勾上：(1) 主语是用户贴出的那一块；(2) 出口单独开一格，不进 fulfilled 的三个词；(3) 若出现在评估结果上，挂在同一条期望、Status 旁边；(4) 不是判定再写，不是本轮打开，不是对外中文；(5) 不是只交否决清单。

**Why I Cannot Apply It**: 只读 peer；本轮不实现字段、不改前端。打开仍是项目决定。

### What I Changed

- `issues/open/issue-092.md`: append-only Architect Response #1

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 8481552ab6d86f98
- pid: 85394

### Investigation

r2。不续写 spawn `44e93555a7a3fdcb`。自己从这块东西的单位重推落点，不从「第二问 / 兄妹」推，也不把 088 换皮。

- 用户点名：按 fulfilled 的定位，这块东西是只补 NF，还是新增一个 judge 结果标签，还是 3 扩 4，还是放到 NE，还是别的方式。给方案。不实现。
- 对象仍是 fulfilled 那一件（040 内容，不是外号）。单位是这件事 × 产品事实。出口手柄已有：立住了 / 没立住 / 说不清。
- `spec/alg/fulfilled.md` §1：fulfilled 只评办成了没有；不并进，不加第四态。
- `spec/alg/product-function.md` §1 / §7–§8：一个词不能答两件；禁第四态；禁 Judge 再填新标签；以后若看见，再加派生列。该文「这类事」不得替换用户钉死的对象。
- `spec/alg/authority.md` §8.3：职责内能力缺失不强制改 fulfilled；「办成了 × 没立住」必须还能写。
- 计算（058 内容）：读已经裁完的前缀。不是判定再填。
- 存放（060 内容）：现在不进 `JudgeFulfillmentAssessmentOutput`。以后若存，只物化同一份读。
- 打开（061 / 章程 §4）：角色不得代选。不得整号 escalate。
- 现行出口：`frontend_view.py` L67–L82 矩阵一行一个 expectation_id + 一个 status，是唯一已经按那一件分行的看见面。`summary.html` L766–L770 Status 旁边没有另一格。`table.py` L36 / `table_view.py` L107–L109 主表芯片一行一个案子；放进去会把对象切粗，这块定义禁止。

### Reasoning

089 锁主语。090 锁三个口不是宿主。091 锁「标签」不是名字。本号必须交方案。只交否决清单，本轮未达。

用户菜单里四个点名口都被 090 / 091 杀掉。剩下的是「别的方式」，不是把第四个口改个称呼再选回来。

落点从这块东西自己推：

1. 出口手柄已经有了，看得见的格子里没有这一格。人现在只能看见 fulfilled，是因为这一格还没开，不是因为它属于三个词，也不是因为它只属于没办成。
2. 一个词不能答两套单位 → 不能进 fulfilled 的三个词 → 必须单独占一格。
3. 对象仍是那一件 → 必须按同一件分行。现行出口上唯一已经这样分行的，是矩阵同一行、Status 旁边。主表芯片一行一个案子，切粗，禁止。Capabilities 是库存名，不是这个出口。authority statement 是 058 的输入，不是立住了 / 没立住 / 说不清。
4. 谁写下的仍是读已经裁完的前缀。单独开一格 = 派生看见格，不是 `JudgeFulfillmentAssessmentOutput` 再加一个模型可写 status。
5. 人看见的那一格字，安放上可以说是一个结果标签。这不是这块东西的名字，也不是选了「新增一个 judge 结果的标签」。
6. 打开、对外中文、改不改表，仍停在章程 §4 / 061。本号锁的是出口放在哪，不是批准上线。

这不是 088 换皮。088 起头是「第二问 / 兄妹标签 / 新增一个 judge 结果标签」。本号起头是用户认得的这一块。挂点可以看起来像旧格子，必须从对象同一性重推回来。

### Improvement Proposal

- **Target**: `issues/open/issue-092.md` 待写 Consensus。这是本轮交给用户的方案句。
- **Change**:

```text
方案：用户认得的这一块，出口单独开一格。
      这是用户点名里的「别的方式」。
      它不是 fulfilled 的词。
      若出现在人正在看的评估结果上，挂在同一条期望、「办成了没有」旁边。
      人看见的那一格字，安放上可以说是一个结果标签；
      这不是这块东西的名字，也不是选了「新增一个 judge 结果的标签」。

谁写下的：不是同一张嘴再判一次。读已经裁完的前缀。
进哪张嘴：不是改写办成了 / 没办成 / 说不清。
那一格：派生看见格，不是模型新写的 status。
        现在不存在。现在不进 JudgeFulfillmentAssessmentOutput。
        以后若存，只物化同一份读。

不是：只给 not_fulfilled 作补充
不是：fulfilled 从 3 态扩到 4 态
不是：放到 not_evaluable 里
不是：同一轮 Judge 再写一个 status
不是：把这块东西改名为「第二问」或「judge 结果标签」
不是：本轮改表、改前端、上线字段
不是：沿用 088 的方案名和主语

打开那一格，仍交章程 §4 / 061。
对外叫什么，仍停住。
内部手柄不宣布采用。
```

- **Verification**: Consensus 必须先写方案再写陪绑。若写成「选了整句 B，让 Judge 再填」，或「它就是第二问，沿用 088」，或只交四个口都不能，本号失败。读方案句：主语必须是用户贴出的那一块；必须说清放在哪、不是哪三个口、看见时是不是一个 judge 结果标签（安放描述，不是名字）。

### What I Changed

- `issues/open/issue-092.md`: 只追加本段 r2 Architect Response #1。未改项目源码、协议、数据。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `8481552ab6d86f98`

接受 architect r2 的方案句。本号先写方案，再写陪绑。依据从这块东西自己的单位和对象推，不从「第二问 / 兄妹」推，也不整句搬 088。

方案：

```text
用户认得的这一块，出口单独开一格。
这是点名里的「别的方式」。
它不是 fulfilled 的词。
若出现在人正在看的评估结果上，挂在同一条期望、「办成了没有」旁边。
人看见的那一格字，安放上可以说是一个结果标签；
这不是这块东西的名字，也不是选了「新增一个 judge 结果的标签」。

谁写下的：读已经裁完的前缀，不是同一张嘴再判。
进哪张嘴：不是改写办成了 / 没办成 / 说不清。
那一格：派生看见格，不是模型新写的 status。
        现在不存在。现在不进 JudgeFulfillmentAssessmentOutput。
        以后若存，只物化同一份读。
```

为什么是这一句，而不是四个口里捡一个：

```text
1. 单位对不上
   这块东西：这件事 × 产品事实，不看这一次给没给到
   fulfilled：这一次请求 × 这一次交付
   一个词答不了两套（fulfilled.md §1；product-function.md §1 L38）

2. 对象仍是那一件
   用户自己钉死：不得另立类型表，不得把对象切粗或切细
   现行出口上唯一已经按那一件分行的，是矩阵同一行、Status 旁边
   主表芯片一行一个案子，切粗，禁止

3. 三个点名口会弄丢必须还能写的组合，或换错嘴
   只补 NF：办成了 × 没立住 这格消失（authority.md §8.3 + 040 第 4 条）
   3 扩 4：第四个词仍是 fulfilled 的嘴（fulfilled.md §1；047）
   放到 NE：把已经裁完的产品事实改写成这一次说不准（fulfilled.md §2.3；§8.3）

4. 看见时多一格字，只说明安放，不给它改名
```

不是：只给 not_fulfilled 作补充  
不是：fulfilled 从 3 态扩到 4 态  
不是：放到 not_evaluable 里  
不是：同一轮 Judge 再写一个 status  
不是：把这块东西改名为「第二问」或「judge 结果标签」  
不是：本轮改表、改前端、上线字段  
不是：沿用 088 的方案名和主语  

打开那一格，仍交章程 §4 / 061。  
对外叫什么，仍停住。  
内部手柄不宣布采用。

闸：同 089。

