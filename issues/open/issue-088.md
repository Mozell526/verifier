# Issue #088: 「judge 结果标签」= 人在结果上看到的一格字，不是模型再写一个 status

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 方案句 / 标签二字不焊回判定再写
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

065 杀的整句 B 是：「新增一个 judge 结果的标签」= 同一轮判定再写一个词。
依据是 047 + `product-function.md` §7.2：让 Judge 再填一个新标签 ✗。同一张嘴兼答两问，几乎一定会对齐刚才的办成了没有。

用户本轮说的「新增一个 judge 结果的标签」，问的是开格子。开格子是看见层的事。看见层多一格字，不必是模型再写一个 status。

必须继续分开，不得焊回一句：

```text
人看见的：是。结果上多一格字。方案名就叫这个标签。
谁写下的：不是。不是同一张嘴再判一次。
进哪张嘴：不是。不是改写办成了 / 没办成 / 说不清。
```

`product-function.md` §8：以后若要看见，再加派生列；派生列不是 Judge 产出，不进 prompt，不改 fulfilled。
`JudgeResult.summary` 已经是派生展示，不是第二张判定嘴。

本号交给用户的方案句必须先写是，再写挂在哪，再写不是哪三个口。不得以「A/B/C/D 都不能」起头。不得再选「别的方式」。

打开仍停在 061 / 章程 §4。本号不整号 escalate：锁的是它叫什么、挂在哪；现在让不让人看见，仍是项目决定。

对外叫什么，仍停住。内部手柄继续是立住了 / 没立住 / 说不清，不宣布采用。

### 可证伪

同时成立才算本 issue 站住：

1. 方案句第一段是肯定句：新增一个 judge 结果标签；
2. 三层分开答仍在；
3. 打开不得从 escalate 被改写成已批准；
4. 不得出现「所以让 Judge 再填」「对外就叫某某」「请先加列」。

若 Consensus 写成「选了整句 B，让 Judge 再填」，本 issue 失败。
若 Consensus 写成「所以不是标签，选别的方式」，本 issue 失败。

## Proposed Change

Consensus 必须先写方案，再写陪绑：

```text
方案：新增一个 judge 结果标签。
      开第二问自己的格子，本质上就是这件事。
      它是 fulfilled 的兄妹标签。
      挂在 fulfillment_panel 矩阵同一行、Status 旁边。

人看见的：是。结果上多一格字。
谁写下的：不是同一张嘴再判一次。
进哪张嘴：不是改写办成了 / 没办成 / 说不清。

不是：只给 not_fulfilled 作补充
不是：fulfilled 从 3 态扩到 4 态
不是：放到 not_evaluable 里
不是：同一轮 Judge 再写一个 status
不是：本轮改表、改前端、上线字段
不是：再把方案名写成「别的方式」

打开那一格，仍交章程 §4 / 061。
对外叫什么，仍停住。
```

---
## Architect Response #1

**Judgment**: real-problem
**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 5d262889dc7c1b05
- pid: 51034

### Investigation

本号只交方案句。零件在 085–087，这里不得再选「别的方式」，也不得整号 escalate。

协议：

- `spec/alg/product-function.md` §7.2 L171：让 Judge 再填一个新标签来回答本协议 ✗。
- 同文件 §8 L188–198：禁「新增一个让 Judge 填的标签」；「以后若要看见，再加派生列」；派生列不是 Judge 产出，不进 prompt，不改 fulfilled。
- `spec/alg/fulfilled.md` L28–30：不并进三态，不新增第四态。
- `spec/alg/product-function.md` §1 L37–39：一个标签不能同时回答两件。
- `spec/info-volume.md` L277–278：judge 只产 fulfillment，不引入第二个对错维度。

现行出口：Judge 评估卡上已经有派生 `summary`（`judge.py` L73–76）；模型可写评估字段仍只有 `status`（L94–103）；矩阵行上 Status 旁边现在空着（`frontend_view.py` L71–81，`summary.html` L766–770）。

已锁：065 杀整句 B（判定再写一个词）；066-q2 看见层可以叫标签；058 计算是读；060 / 087 挂点；061 打开 escalate；080 留下过一句方案，但写/枚举层仍叫「别的方式」。本轮只改那句名字。

章程 §1 工作定义：能用一句话说清开格子是不是新增一个 judge 结果标签；若是，方案名必须就是这个，不得再写成「别的方式」；同时说清不是第四个词、不是 NE、不是只挂在没办成后面、也不是同一轮 Judge 再写一个 status。章程 §4：打开 / 对外中文 / 改不改表，角色不得代选。不得整号 escalate。

### Evidence Verification

核过。065 和用户本轮说的不是同一个「标签」。065 = 同一张嘴再写一个词。用户 = 开格子。开格子之后人会多看见一格字，066-q2 已锁。`JudgeResult.summary` 已证明：出现在 Judge 评估结果上的字，不必是模型新写的 `status`。080 的方案句先写了肯定句，但 Architect 仍把写层命名为「别的方式」。本轮若再交「A/B/C/D 都不能，因此别的方式」，未达章程 §1。verifier 拟的方案句以「方案：新增一个 judge 结果标签」起头，不是否决清单。打开没有被改写成已批准。

### Reasoning

三记攻击。本号只判方案句，不重判 085–087 的零件。

1. 既然名字就叫「judge 结果标签」，是不是已经选了整句 B，并且和 `product-function.md` §7.2 打架？
没有。§7.2 / §8 杀的是「让 Judge 再填一个新标签」「新增一个让 Judge 填的标签」。主语是 Judge 填，不是人看见。065 把用户四个字定义成那张第二张嘴，所以整句 B 死。用户本轮把这四个字用在开格子上。开格子是看见层。看见层多一格字，不必是模型再写一个 `status`。卡上已有派生 `summary` 作反例。
三层必须继续分开，不得焊回一句：

```text
人看见的：是。结果上多一格字。方案名就叫这个标签。
谁写下的：不是。不是同一张嘴再判一次。
进哪张嘴：不是。不是改写办成了 / 没办成 / 说不清。
```

焊成「所以就是 B，让 Judge 再填」，和 §7.2 才打架，本号失败，应退回 065。焊成「所以不是标签，选别的方式」，本号也失败——那是 080 已经交过、用户不要的那句。

2. 该不该整号 escalate-to-project？加一个看得见的标签，难道不是产品决定？
「现在让不让人看见」是产品决定。061 已经 escalate。章程 §4 列的是打开 / 对外中文 / 现在改不改表，不是「方案句也要等产品」。本轮角色必须锁：它叫什么、挂在哪、不是哪三个口。把 088 整号 escalate，等于再交「位置说清了但方案还要等」，未达 §1。打开继续停在 061，不在 088 重 escalate。

3. 方案句能不能以否决清单起头？
不能。069 的失败是只留下剩余。080 已经改成先方案、后陪绑。本号必须先写是，再写挂在哪，再写不是哪三个口。不得以「A/B/C/D 都不能」起头。不得再选「别的方式」。verifier 拟句满足这个顺序。内部手柄继续是立住了 / 没立住 / 说不清，不宣布采用为对外题面。本轮不改表、不改前端、不上线字段。

**Judgment / Verdict**：real-problem。留下下面那句方案。打开仍停住。不是整句 B，不整号 escalate。

## Improvement Proposal

**Problem**: 用户要的是一句以「新增一个 judge 结果标签」为名的方案；再交「别的方式」或整号 escalate 都未达本轮。
**Proposed Change**: Consensus 必须先写方案，再写陪绑。不得只交否决清单。不得改 `spec/**` / `impl/**`。

```text
方案：新增一个 judge 结果标签。
      开第二问自己的格子，本质上就是这件事。
      它是 fulfilled 的兄妹标签。
      挂在 fulfillment_panel 矩阵同一行、Status 旁边。

人看见的：是。结果上多一格字。
谁写下的：不是同一张嘴再判一次。
进哪张嘴：不是改写办成了 / 没办成 / 说不清。

不是：只给 not_fulfilled 作补充
不是：fulfilled 从 3 态扩到 4 态
不是：放到 not_evaluable 里
不是：同一轮 Judge 再写一个 status
不是：本轮改表、改前端、上线字段
不是：再把方案名写成「别的方式」

打开那一格，仍交章程 §4 / 061。
对外叫什么，仍停住。
内部手柄继续是立住了 / 没立住 / 说不清，不宣布采用。
```

**Implementation Steps**:
1. 只把上面这段写入本号 Consensus。
2. 不得在方案句里出现字段名待加、列名待加、「请 Judge 填」、「对外就叫某某」。
3. 打开不得从 escalate 被改写成已批准。

**Risks**: 读者只看第一行「新增一个 judge 结果标签」，略过三层切开，听成整句 B。所以陪绑不能删，但也不能提到正文前面去。
**Verification**:
1. Consensus 第一段必须是肯定句，不能以「A/B/C/D 都不能」起头。
2. 三层分开答仍在。不得出现「所以选了 B」「请先加列」「请 Judge 填」「对外就叫某某」「选了别的方式」。
3. 打开不得从 escalate 被改写成已批准。
4. 对照 `frontend_view.py` L71–81：被点名的那一格现在确实不存在。
5. 对照 `product-function.md` L171 / L188–198：方案句没有让 Judge 再填。

**Why I Cannot Apply It**: 本角色只锁方案句。打开、对外中文、改表，仍是章程 §4 的项目决定；architect 不得代选，也不得改 `spec/**` / `impl/**`。

### What I Changed
无。review 模式，只追加本回应。未改 spec / impl / 前端。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `5d262889dc7c1b05`

本轮交给用户的方案句如下。先方案，后陪绑。不得再以「A/B/C/D 都不能」起头，也不得再选「别的方式」。

```text
方案：新增一个 judge 结果标签。
      开第二问自己的格子，本质上就是这件事。
      它是 fulfilled 的兄妹标签。
      挂在 fulfillment_panel 矩阵同一行、Status 旁边。

人看见的：是。结果上多一格字。
谁写下的：不是同一张嘴再判一次。
进哪张嘴：不是改写办成了 / 没办成 / 说不清。

不是：只给 not_fulfilled 作补充
不是：fulfilled 从 3 态扩到 4 态
不是：放到 not_evaluable 里
不是：同一轮 Judge 再写一个 status
不是：本轮改表、改前端、上线字段
不是：再把方案名写成「别的方式」

打开那一格，仍交章程 §4 / 061。
对外叫什么，仍停住。
内部手柄继续是立住了 / 没立住 / 说不清，不宣布采用。
```

本号不整号 escalate：锁的是它叫什么、挂在哪；现在让不让人看见，仍是项目决定。
不得听成「选了整句 B，让 Judge 再填」。
去年 / 称谓 / 格式外继续停。

闸：同 085。
