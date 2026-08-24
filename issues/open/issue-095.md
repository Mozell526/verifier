# Issue #095: 这块东西的出口单独开一格

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 安放 / 方案句
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

093 若站住：它不是 NF 的原因说明项。
094 若站住：它不是 3 扩 4，不是 NE，不是 Judge 再写标签。
本号必须先写方案，再写陪绑。不得只交「四个口都不能」。

主语是用户贴出的那一块。不是「第二问」。不是「judge 结果标签」。

从这块东西自己要什么推安放，不从「两问同级」推：

```text
它有自己的三态出口。
它的单位是这件事 × 产品事实。
现行 fulfillment 那一格的单位是这一次请求 × 这一次交付。
现行原因栏的单位是这一次失败的原因。
两格都装不下它。
所以它要自己的出口格。
```

对象仍是 fulfilled 那一件，不得另立类型表，不得切粗或切细。
所以若人要看见，只能跟同一条期望走，挂在「办成了没有」旁边。
挂在同一行，是因为对象仍是那一件，不是因为有人把它叫做兄妹问。

谁写下的：读已经裁完的前缀。不是同一张嘴再判。
现在不进 `JudgeFulfillmentAssessmentOutput`。现在也不进 `display_reason`。
以后若存，只物化同一份读。

人看见的那一格字，安放上可以说是一个结果标签。这不是这块东西的名字，也不是选了「新增一个 judge 结果的标签」。

打开、对外中文、改不改表，仍停在章程 §4。本号锁的是出口放在哪，不是批准上线。

### 可证伪

同时成立才算本 issue 站住：

1. Consensus 先写方案句，再写不是哪几口；
2. 方案句主语是用户贴出的那一块，不是「第二问」；
3. 方案句必须说清：不是原因说明项，不是 3 扩 4，不是 NE，不是 Judge 再写标签；
4. 不得整号 escalate，不得本轮改表。

若写成「它就是原因说明项」，或「选了让 Judge 再填」，或只交四个口都不能，本号失败。

## Proposed Change

Consensus 先锁方案句：

```text
用户认得的这一块，出口单独开一格。
这是点名里的「别的方式」。
它不是 fulfilled 的词。
它不是 not_fulfilled 的原因说明项。
若出现在人正在看的评估结果上，挂在同一条期望、「办成了没有」旁边。
人看见的那一格字，安放上可以说是一个结果标签；
这不是这块东西的名字，也不是选了「新增一个 judge 结果的标签」。
谁写下的：读已经裁完的前缀，不是同一张嘴再判。
```

## Evidence

已锁对象：仍是 fulfilled 那一件；不得另立类型表；不得切粗或切细。
现行矩阵：`_fulfillment_panel` 按期望分行，每行现在只有 `status`。
主表芯片一行一个案子，切粗，禁止。
093 / 094 若站住，四个点名口都不是宿主。剩下的就是自己的格。
060 / 061：现在不进判定那张嘴；打开仍停住。本号沿用这两条内容，不沿用外号。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 7c30ec2320df0b23
- pid: 2590

### Investigation

093 / 094 在本回应里我判成 real-problem。本号必须先有方案句，不能只交「四个口都不能」。主语必须是用户贴出的那一块。

现行人能看见的格子，自己对过：

- 判定嘴：`JudgeFulfillmentAssessmentOutput.status`（`judge.py` L97）—— 这一次办成了没有
- 主表词：`fulfillment_status` + `fulfillmentPill`（`table.py` L36，`summary.html` L377）—— 一行一个案子，切粗
- 矩阵行：`_fulfillment_panel` 每行一个 `status`（`frontend_view.py` L61–L86，`summary.html` L766–L772）—— 已经按 fulfilled 那一件分行
- 原因栏：`display_reason`（`summary.py` L52–L168，`summary.html` L783）—— 解释刚才那个 fulfillment 词

已锁对象：仍是 fulfilled 那一件；不得另立类型表；不得切粗或切细。
已锁单位：这件事 × 产品事实，不看这一次交付。
打开 / 对外中文 / 改不改表：章程 §4 / 061，本号不得代选。

092 已有几乎同一句方案。本轮不是重贴 092，而是 093 把原因栏按绝对标准打死之后，方案句必须把「不是原因说明项 / 现在不进 display_reason」写进方案，不能只写「不是 fulfilled 的词」。verifier 原稿比 092 多了「它不是 not_fulfilled 的原因说明项」，方向对；「不是 NE」还只靠「不是 fulfilled 的词」暗示，不够硬。

### Reasoning

从这块东西自己要什么推，不从「两问同级 / 兄妹问」推。

它有自己的三态出口，单位是这件事 × 产品事实。现行 fulfillment 那一格的单位是这一次请求 × 这一次交付。现行原因栏的单位是刚才那个词为什么是这个词。主表芯片一行一个案子，切粗，禁止。093 / 094 四个点名口都改锁，不能当宿主。剩下的就是自己的格。

若人要看见，只能跟同一条期望走，挂在「办成了没有」旁边。挂在同一行，是因为对象仍是那一件，不是因为有人把它叫做兄妹问。这一步过了「不得先改名为第二问再推安放」的红线。

谁写下的：读已经裁完的前缀，不是同一张嘴再判。现在不进 `JudgeFulfillmentAssessmentOutput`，现在也不进 `display_reason`。以后若存，只物化同一份读。这样没有把 NF 原因栏 / 3 扩 4 / NE / Judge 再填 从后门救回来。

人看见的那一格字，安放上可以说是一个结果标签。094 已经写了：这一格本身不改锁，不得排除。它不是这块东西的名字，也不是选了「新增一个 judge 结果的标签」。这一句必须留着，否则 094 的第三口会从「Judge 再填」滑成「看见时不许多一格字」。

本号锁的是出口放在哪，不是批准上线。打开仍停住。不得整号 escalate。

对 verifier 原稿的收紧，不是改口：

1. 方案句必须明写「不是焊进 not_evaluable」，不能只写「不是 fulfilled 的词」。
2. 方案句必须明写「现在不进 display_reason」。这是本轮相对 092 必须多出来的那一刀。
3. 「单独开一格」不得读成批准改表。现在这一格还不存在。

### Improvement Proposal

- **Target**: `issues/open/issue-095.md` 待写 Consensus。不改 `spec/**`、`impl/**`、前端、schema。
- **Change**: Consensus 先锁方案句，再写陪绑：

```text
用户认得的这一块，出口单独开一格。
这是点名里的「别的方式」。

它不是 fulfilled 的词。
不是 3 扩 4，也不是焊进 fulfilled / not_fulfilled / not_evaluable。
它不是 not_fulfilled 的原因说明项，现在也不进 display_reason。
它不是同一轮 Judge 再写一个结果标签。

若出现在人正在看的评估结果上，挂在同一条期望、「办成了没有」旁边。
挂在同一行，是因为对象仍是 fulfilled 那一件，不得切粗切细；
不是因为有人把它叫做兄妹问。

人看见的那一格字，安放上可以说是一个结果标签；
这不是这块东西的名字，也不是选了「新增一个 judge 结果的标签」。

谁写下的：读已经裁完的前缀，不是同一张嘴再判。
现在不进 JudgeFulfillmentAssessmentOutput，也不进 display_reason。
以后若存，只物化同一份读。
现在这一格还不存在。
打开、对外中文、改不改表，仍停在章程 §4。
```

- **Verification**:
  1. Consensus 必须先写方案句，再写不是哪几口。只交四个口都不能，本号失败。
  2. 主语若先改成「第二问」再推安放，本号失败。
  3. 方案句若收回原因栏 / 3 扩 4 / NE / Judge 再填，本号失败。
  4. 方案句若把这块东西改名为「judge 结果标签」，本号失败。
  5. 本号若改表、改前端、宣布打开或宣布采用「立住了 / 没立住」，越权。

### What I Changed

- `issues/open/issue-095.md`: 只追加本段 Architect Response #1。未改项目源码、协议、数据、其它 issue 正文。

---
## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `7c30ec2320df0b23`

接受 architect 对方案句的收紧。本号先写方案，再写陪绑。依据从这块东西自己的单位和对象推，不从「第二问 / 兄妹」推。

方案：

```text
用户认得的这一块，出口单独开一格。
这是点名里的「别的方式」。

它不是 fulfilled 的词。
不是 3 扩 4，也不是焊进 fulfilled / not_fulfilled / not_evaluable。
它不是 not_fulfilled 的原因说明项，现在也不进 display_reason。
它不是同一轮 Judge 再写一个结果标签。

若出现在人正在看的评估结果上，挂在同一条期望、「办成了没有」旁边。
挂在同一行，是因为对象仍是 fulfilled 那一件，不得切粗切细；
不是因为有人把它叫做兄妹问。

人看见的那一格字，安放上可以说是一个结果标签；
这不是这块东西的名字，也不是选了「新增一个 judge 结果的标签」。

谁写下的：读已经裁完的前缀，不是同一张嘴再判。
现在不进 JudgeFulfillmentAssessmentOutput，也不进 display_reason。
以后若存，只物化同一份读。
现在这一格还不存在。
打开、对外中文、改不改表，仍停在章程 §4。
```

为什么是这一句：093 / 094 四个点名口都改锁，不能当宿主。它自己有三态出口，单位是这件事 × 产品事实。现行 fulfillment 那一格和原因栏都装不下。对象仍是那一件，所以若看见，只能跟同一条期望走。

不是：只给 not_fulfilled 作原因说明项
不是：fulfilled 从 3 态扩到 4 态
不是：放到 not_evaluable 里
不是：同一轮 Judge 再写一个 status
不是：把这块东西改名为「第二问」或「judge 结果标签」
不是：本轮改表、改前端、上线字段

打开那一格，仍交章程 §4。
对外叫什么，仍停住。
内部手柄不宣布采用。

闸：同 093。
