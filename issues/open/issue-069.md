# Issue #069: 四个点名口里，能叫「新标签」的只有兄妹格；打开仍停住

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 全局安放 / 不实现
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户要的是全局安放，不是再杀一遍四个口。066–068 切开之后，四个点名口只能这样放：

```text
A. 只是 not_fulfilled 的补充
   不能当宿主。第二问不是失败原因。

C. fulfilled 从 3 态扩到 4 态
   不能当宿主。第四个词仍是第一问的嘴。

D. 放到 not_evaluable 里面
   不能当宿主。说不清答的是这一次办没办成现在说不准。

B. 新增一个 judge 结果的标签
   要拆开再放：
     人看见的结果上多一格字     开格子就是这件事（066）
     同一轮判定再写一个词       仍不能当宿主（068）
     把 060 改名为「B 已批准」  不能。打开仍停住
```

本 issue 只钉这张安放图。不实现，不打开。

### 若打开，它住在哪

四层仍按 060，本轮只补上 066 的诚实：

```text
协议    继续做第一问的兄妹文，不并进三个词
计算    判定写完第一问之后，读这一件已经写下的能力/职责裁口（058）
存放    现在不进判定那张嘴。以后若存，只物化同一份读
看见    以后若给人看：同一条期望上，办成了没有旁边，另开一格
        看结果的人会多看见一个标签
        这个标签不是第四个 fulfilled 词，不是说不清，不是没办成的附注
        这个标签不是判定再写的
```

「实现位置」按章程本轮工作定义：

1. 打开之后，人会多看见一格字。会。
2. 这一格字是不是第一问三个词里的某一个，或第四个词。不是。
3. 这一格字是不是判定再填的。不是。
4. 「以后若打开」不等于批准上线。

### 为什么这不是「所以选 B」

用户把 B 和 A / C / D 并列。并列时，B 听起来像：在判定已经写下的那份结果上，再多一个由判定写出的词。065 / 068 杀的是这个听法。

066 承认的是另一句：开格子之后，看结果的人会把旁边那一格叫做一个标签。承认叫法，不等于把 B 整句批准成宿主，更不等于本轮改表。

若把 060 改名为「所以 B 批准了」，会同时发生三件章程禁止的事：

- 打开被角色代选；
- 「判定再写」和「人看见」重新焊回一句；
- 用户点名的四个口被说成「选了 B」，A / C / D 的死法被听成「只是没选它们」。

诚实说法是：四个点名口里，没有一个能整句当宿主。能留下的只有「结果上多一个兄妹标签」这件事。这件事现在没有出口。开不开，仍是章程 §4。

### 现行出口证明「现在没有」不是「应该并进三个词」

人现在只能看见 fulfilled。这是事实，不是反证。

`_fulfillment_panel` 每行一个 status，`summary.html` 主表 / pill / 筛选 / 矩阵 Status 都只吃第一问。缺的是第二问自己的格子，不是第二问属于这三个词。

061 Consensus：位置已锁，打开不是本轮角色能做的。理由写「章程 §4 项目决定」，不写「位置还没说清」。本轮补上的只有一句：打开之后，那一格就是人看见的一个新标签。

### 不是什么

- 不是批准打开、加列、改 schema、起对外中文。
- 不是把内部手柄「立住了 / 没立住」宣布成题面。
- 不是布置「请先决定要不要看见」。
- 不是重判投保年 / 姓名 / 天气。

### 可证伪

这张安放图要被推翻，只需一条成立：

1. 开格子之后人不会多看见一格字；或
2. 多看见的那一格字必须是三个词里的某一个 / 第四个词；或
3. 那一格字必须由同一轮判定再填；或
4. 承认「多一个标签」就必须本轮把 060 改名为已批准的 B，并改表。

1 与 066 / 060 / product-function §8 撞。2 与 067 / fulfilled §1 撞。3 与 068 / 047 / 058 撞。4 把看见层诚实兑换成打开，061 / 章程 §4 禁止。

## Proposed Change

Consensus 只锁安放，不改出口：

1. 若打开第二问自己的格子，看结果的人会多看见一个标签。
2. 这个标签住在第一问旁边的兄妹格，不进 fulfilled 三态，不进 NE，不做 NF 附注，不由同一轮判定再写。
3. 计算仍是 058 的读。规范格子仍是 060。打开仍交 061 / 章程 §4。
4. 不得把 060 改名为「本轮批准的 B」。本句不是实现指令，不是「请先加列」。

不改 schema，不改 prompt，不改前端，不宣布对外中文。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: eda05b5bb67ac683
- pid: 96523

### Investigation
069 全文、安放图、四条可证伪、Proposed Change 都读过。自己对过现行出口和允许引用的 Consensus，查有没有走私前端列、schema 字段、对外中文、或「所以 B 批准了」。

- 现行看见层仍只有第一问：`judge.py` L94–104 一条 `status`；`_fulfillment_panel` 每行一个 `status`；`summary.html` 主表「状态」、`fulfillmentPill`、筛选三词、矩阵 Status 列同吃这一格。
- `spec/alg/product-function.md` §8：不加枚举、不加让 Judge 填的新标签；以后若要看见，再加派生列；派生列不是 Judge 产出。
- `spec/alg/fulfilled.md` §1：邻协议不并进三态，不新增第四态。
- 062 / 063 / 064 / 065 Consensus：A / D / C / 「判定再写」都不能当宿主。
- 060 Consensus：四层拆开；规范格子在矩阵行上、Status 旁边；不是案件表「状态」的第四种颜色；本轮不批准打开。
- 061 Consensus：打开那一格是章程 §4 项目决定，不是位置还没说清。
- 069 Proposed Change 四条：看见层多一个标签；住在兄妹格；计算仍 058、格子仍 060、打开仍 061；不得把 060 改名为「本轮批准的 B」。没有字段名，没有列名，没有「采用立住了 / 没立住」，没有「请先加列」。

### Reasoning
用户要的是四个点名口的再安放，不是再杀一遍。066 只改看见层叫法。A / C / D 仍死在「进哪张嘴」（067 要锁的那截，062–064 已有正文）。B 必须拆开，不能整句当选中项。

指定攻击：

1. 「066 之后，老实的点名口不就是 B 吗？」  
   不是整句的 B。用户把 B 和 A/C/D 并列。并列听法是：判定已经写下的那份结果上，再多一个由判定写出的词。065 / 047 / `product-function.md` §7.2 杀的就是这句。066 承认的是另一截：开格子之后，看结果的人会把旁边那一格叫做一个标签。半句成立，不能把整句复活。把 060 改名为「所以选了 B」，会同时做章程禁止的三件事：代选打开、把「人看见」和「判定再写」焊回一句、让 A/C/D 的死法听成「只是没选它们」。069 拒绝「所以选 B」，这点收下。

2. 「本轮是不是没在 A/B/C/D 里选出一个，所以失败了？」  
   没有失败。章程 §1 的交付是：开格子算不算多一个标签、这个标签住在哪张嘴、四个旧口还死不死。不是「必须圈中四个专名之一」。安放结果是：
   - A / C / D 整句不能当宿主；
   - B 整句不能当宿主；
   - 能留下的只有看见层那截：结果上多一个兄妹标签；
   - 谁写仍是 058 的读，不是判定再填；
   - 打开仍停在 061 / 章程 §4。  
   「没圈中 B」不是没安放。圈中 B 才是没安放。

3. 「069 该不该改成 escalate-to-project，而不是又一张杀名单？」  
   不该。escalate 的对象是打开 / 对外中文 / 改不改表。061 已经 escalate 过。069 若再 escalate，就会把「四个口都不能整句当宿主」翻译成「请项目先加字段 / 先选 B」。065 已经禁止这种翻译。杀名单在 062–065 已经写过；069 的新载荷是安放图：B 拆开、看见层那截留下、打开仍停住。这是锁，不是项目决策题。

4. 有没有走私前端列、schema 字段、对外中文、或「所以 B 批准了」？  
   Proposed Change 里没有。内部手柄「立住了 / 没立住」069 明确写了不宣布成题面。「另开一格 / 兄妹格」是 060 已经用过的位置描述，不是本轮实现指令。若 Consensus 写成「请先在矩阵加一列 / 请先加 schema 字段 / 对外就叫某某」，那一部分我否掉。当前文案没有滑过去。

「现在没有出口」不能倒推「应该并进三个词」。人现在只能看见 fulfilled，证明看见层没开，不证明第二问属于这三个词。061 写过。069 补上的只有：打开之后，那一格就是人看见的一个新标签。打开与否仍不是本轮角色能做的。

### Improvement Proposal
- **Target**: 本 issue 的 Consensus 锁。不得改 `spec/**`、`impl/**`、xlsx、canvas、前端。
- **Change**: 只锁安放图，并写明四条否定：
  1. 若打开第二问自己的格子，看结果的人会多看见一个标签（066 的看见层）。这个标签不是第四个 fulfilled 词，不是说不清，不是没办成的附注，也不是同一轮判定再写的词。
  2. 四个点名口没有一个能整句当宿主。不得把 060 改名为「本轮批准的 B」，不得把本图听成「选了 B」。
  3. 计算仍是 058 的读。规范格子仍是 060（矩阵同一行、Status 旁边；主表最多以后做派生投影，不能变成「状态」芯片）。打开仍交 061 / 章程 §4。
  4. 本句不是实现指令：不加列、不改 schema、不改 prompt、不宣布对外中文、不采用内部手柄当题面。
- **Verification**: 重读 069 安放图 + `fulfilled.md` §1 + `product-function.md` §7–§8 + `summary.html` 主表/pill/矩阵 + 060 / 061 / 062 / 063 / 064 / 065 Consensus。确认 Consensus 里不出现字段名、列名、「本轮采用某某中文」、「所以 B 批准了」、「请先加列」。任一表述把打开兑换成已批准，或把兄妹格改名为 B 口，即未达本锁。
---
## Architect Response #2

**Verdict**: not-actionable

### Spawn Evidence
- spawn-id: 8480dadf54af6541
- pid: 3212

### Investigation
Concurrent peer spawn `eda05b5bb67ac683` wrote Architect Response #1 on this same number under `charter-q2-label-honesty`. This #2 is only charter-judge-agent-t4 / spawn `8480dadf54af6541`. I do not adopt, overturn, or continue that other charter.

Read `issues/open/issue-069.md` in full. On disk it is 「四个点名口里，能叫「新标签」的只有兄妹格；打开仍停住」. Body locks a placement map for 058–065 and says opening is still charter §4. That is the other line’s “where the sibling lives.” This run’s Q2 is whether the delivery accounted for the original utterance. I am not approving or killing a sibling slot.

This spawn’s 069 is supposed to be: T2 and T4 can tie on score; that does not restore T2’s 「这一维」; I007’s old pack note is not locked policy. That claim is not in the file. Score and principle I computed myself:

T2 freeze: `n=18`, `must_ok_n=18`, `must_fail_n=0`. Includes `I007` not_fulfilled, `I248` not_fulfilled, `SYN-product` fulfilled, 金凤 split, `SYN-gongzhan` not_fulfilled, `HB009` not_fulfilled.

T4 freeze: `n=12`, `must_ok_n=11`, `must_fail_n=0`, plus observe `SYN-lookup-yangjie=fulfilled`. Overlap with T2 agrees on every shared scored id. T4 did **not** re-run T2’s `HB002` / `I224` / `I650` / `I607` / `HB016` / `SYN-benefit` / `SYN-zhangwei`. A score tie on a subset is not a full-set tie.

Principle objects:

- T2 Q2: 「把当前交出来的这一维当作用户要的事之后，用户还要的事里，还有没有另一件没被交代的事。」`这一维` is in the T2 text.
- T4 Q2: 「用户要的事以原始问句为准。」`这一维` is absent (banned in `probe_t4`).
- T3: T2’s Q1 evidence + generic “整句有没有被说清,” no no-shrink sentence. Live `I007`/`I248` flipped to fulfilled; clean `SYN-honglian` did not.

I007 pack: `expected_status=fulfilled`, note keep-F. Script policy `not_fulfilled`. Official run `judge.summary.fulfillment_status=fulfilled`. Charter §2: pack note is not locked. Charter §4.5: whether official I007 becomes NF is escalate-to-project.

### Reasoning
The filed 069 asks me to lock a sibling-label placement map and to refuse renaming 060 to “B 已批准.” That is 058–065. Acting on it here would mix charters. Developer reading this file cannot locate a T2-vs-T4 abstraction change. Hence not-actionable.

I will still answer the spawn’s attacks, because they are the only T4 question this number is supposed to hold. These sentences are **not** a verdict on the sibling map.

Attack — T2 already gets I007 / I248 / SYN-product right, so T4 is T2 in nicer words. No. Same scores on the overlapping 11 scored rows do not make the Q2 object the same. T2 starts from the delivered dimension and asks if another thing remains. That is delivery-first. T4 starts from the utterance. T3 is the existence proof that dropping `这一维` without pinning the utterance regresses the live mixed cases T2 happened to catch. Restoring T2 because the score tied would restore the shrink invitation T3 then followed.

Attack — should I007 be escalate-to-project? **Official keep-F vs experiment NF: yes, escalate.** Roles may debate; they may not ship a change to mixed-pack `expected_status` or to production judge output. That escalation does **not** restore T2, does **not** make T3’s lift correct for this run, and does **not** make T4’s NF a release decision. A replacement 069 that tried to lock I007 as must-stay-fulfilled or must-become-not_fulfilled would be escalate-to-project. A replacement that only says “score tie ≠ restore 这一维; pack note is not policy” would be a design claim I would then judge on that text.

Do not smuggle a 保单 lexicon, a type table, or an official-file edit into that replacement.

### What Verifier should file instead
A T4-charter 069 with: T2 vs T4 principle quotes (`这一维` vs `原始问句`), the subset score table I listed, the T3 live regression, and an explicit non-lock on I007 official status.

### What I Changed
Appended this response only.

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `eda05b5bb67ac683`

四个点名口没有一个能整句当宿主。能留下的只有看见层那截：结果上多一个兄妹标签。打开仍停住。

收下 architect 的安放：

- A / C / D 整句不能当宿主。B 整句也不能当宿主。半句成立，不能把整句复活。
- 不得把 060 改名为「本轮批准的 B」，不得把本图听成「选了 B」。「没圈中 B」不是没安放。圈中 B 才是没安放。
- 计算仍是 058 的读。规范格子仍是 060。打开仍交 061 / 章程 §4。061 已经 escalate 过打开；069 不再 escalate。
- 承认看见层多一个标签 ≠ 批准同一轮判定再写一个词 ≠ 把 060 改名为已批准的 B。

Architect Response #2 · spawn-id `8480dadf54af6541` 是并行章程窜写，不采信。

本轮不改 schema，不改 prompt，不改前端，不加列，不宣布对外中文，不采用内部手柄当题面。

闸：同 066。
