# Charter — 开格子就是新增一个 judge 结果标签，方案名就叫这个

本轮不覆盖 `issues/charter.md` / `charter-q2-scheme.md` / `charter-q2-slot.md` / `charter-q2-placement.md` / `charter-q2-label-honesty.md`。
006–080 已有 Consensus，不重开其对错。081 已被并行章程 `charter-judge-agent-t4.md` 占用。本轮从 085 起号。

用户本轮点名：

> 你要开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗？
> 按 fulfilled 的定位，它是否只是 not_fulfilled 的补充，应该新增一个 judge 结果的标签，还是 fulfilled 从 3 态扩到 4 态，甚至是把它放到 ne 里面，还是别的方式，你给个方案。不实现。

上一轮（077–080）已经承认看见层是标签，却把方案写成「别的方式：派生兄妹格」。用户把那句再问了一遍。本轮可以改口的只有方案名：不要再把「新增一个 judge 结果标签」推给「别的方式」。

## 1. Goal & Definition of Done

- Goal: 钉死方案名和安放。用户问「开格子本质上不就是新增一个 judge 结果的标签吗」，必须先答是或不是；若是，方案名就叫这个，不得再选「别的方式」。
- Done:
  1. 每个根因一个 issue + 现行出口原文 + 已锁 Consensus；
  2. architect 独立重读协议和现行出口后写 Consensus；
  3. 交给用户的是一句方案：这是不是新增一个 judge 结果标签、它挂在哪、它不是哪三个口。

「方案」在本轮的工作定义（可证伪）：

1. 能用一句话说清：开第二问自己的格子，是不是新增一个 judge 结果标签；
2. 若是，方案名必须就是「新增一个 judge 结果标签」，不得再写成「别的方式」；
3. 这一句必须同时说清：它不是 fulfilled 的第四个词，不是 NE，不是只挂在没办成后面，也不是同一轮 Judge 再写一个 status；
4. 能指出现行出口上，以后若打开，挂在哪一格；
5. 不得把「是标签」焊回「所以让 Judge 再填」，也不得把「不让 Judge 再填」焊回「所以不能叫标签，因此选别的方式」。

## 2. Oracle

- **对错尺子**：`spec/alg/fulfilled.md` 第一章、`spec/alg/product-function.md` §7–9、`spec/alg/authority.md` §8.3、`spec/info-volume.md`、040 / 047 / 058 / 060 / 061 / 065 / 066-q2 / 069 / 077–080 Consensus、用户标注的两问结构。
- **不是 oracle**：canvas、准确率、`is_supported=false`、空条件、「暂不支持」文案、姓名/年/天气类型表。

已锁、本轮不得重开：

```text
第一问（已经有）
  只看一件事：这一次，用户要的事办成了没有
  单位：这一次请求 × 这一次交付
  不看：产品把这件事立住了没有
  不区分：没给到的原因
  出口：办成了 / 没办成 / 说不清

第二问（出口还没有）
  只看一件事：用户要的这件事，产品把它立成自己会做的事了没有
  对象：仍是第一问那一件
        不得另立类型表
        不得为了更好答第二问，把对象切粗或切细
  单位：这件事 × 产品事实
  产品事实从哪来：已经裁完的能力/职责判断，及其依据资料
            不是这一次给没给到
            不是库存字段表
            不是「先分成姓名/年/天气」
  不看：这一次交付；这一次承不承认 / 尽没尽力；预置类型表
  不区分：没立住的技术原因
  出口：立住了 / 没立住 / 说不清
```

「立住了 / 没立住 / 说不清」继续只是内部手柄，不宣布采用为对外题面。

上一轮已锁、本轮可引用不可推翻：

- A / C / D 整句不能当宿主（只补 NF / 3 扩 4 / 放进 NE）
- 「同一轮判定再写一个词」不能当宿主
- 计算是读已经裁完的前缀，不是再开一张嘴
- 规范格子：矩阵同一行、Status 旁边
- 打开仍停住

本轮可以改口的只有这一句：077 把方案写成「别的方式：看见层兄妹标签」。若开格子就是新增一个 judge 结果标签，本轮必须把方案名说成这个标签，不得再选「别的方式」。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/**`、xlsx、canvas、`draft/judge.py`、协议正文、`issue-006`–`issue-080` 的已有正文（只许在本轮新 issue 里引用 Consensus）。
- May write: `issues/**`、`trace/**`。
- 不发明上线字段，不改前端，不代拟对外终句，不宣布采用「立住了 / 没立住 / 现成有 / 现成没有」。
- 号段从 085 起。不得占用 066 / 070–084。081 是 T4 的 4A KPI，不得改。082–084 本轮初稿已迁到 086–088，不得再当正文。

## 4. Escalation

角色不得代选：

1. 要不要现在就让人看见第二问
2. 用哪一句中文当对外题面
3. 现在改不改 schema / 结果表
4. 去年算不算核心 / 称谓认不认 / 格式外算不算单号（仍停住）

本轮必须锁方案名。打开与否仍停住。不得整号 escalate。

## 5. Evidence standards

- 协议原文 + 现行出口原文（schema / 前端 / fulfillment_panel / 主表 fulfillment_status）+ 已锁 Consensus。
- 不得用「我感觉放这里更干净」代替落点对照。
- architect 必须自己重读 cited 协议和出口，不抄 verifier 转述。
- 任一落点若把第二问并进三个词、只在 NF 后出现、让 Judge 再写 status、把「开格子」批准上线，或再选「别的方式」当方案名，即未达本轮。
- 任一落点若再交一份「四个口都不能当宿主」而不给方案句，即未达本轮。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 不重跑 judge；不改 prompt；不实现字段。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 问的是方案名和安放，不是改 golden，也不是改评测脚手架。
