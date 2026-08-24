# Charter — 第二问四个结果口

> 本轮只辩：按 fulfilled 的定位，第二问是不是只补 not_fulfilled，以及四个点名的结果口哪一个能当宿主。
> 不重开 006–061 的对错结论，不改代码，不改协议正文，不改前端。
> 用户 `/council`：按照 fulfilled 的定位，他是否只是一个 not fulfilled 的补充，应该新增一个 judge 结果的标签，还是 fulfilled 标签从 3 态扩展到 4 态，甚至是把它放到 NE 里面。不实现。

## 1. Goal & Definition of Done

- Goal: 钉死四个点名结果口各自死在哪，以及按 fulfilled 的定位，第二问到底不进哪张嘴。
- Done:
  1. 每个点名口一个 issue + 现行出口原文 + 同一件期望上的落点对照；
  2. architect 独立重读 fulfilled / 现行出口后写 Consensus；
  3. 交给用户的是「这四个口哪个能当宿主」，不是字段名，不是对外题面，也不是本轮改表。

本轮四个点名口（必须逐个对上，不得合成一句「都不行」就结束）：

```text
A. 只是 not_fulfilled 的补充
B. 新增一个 judge 结果的标签
C. fulfilled 从 3 态扩到 4 态
D. 放到 not_evaluable 里面
```

「实现位置」在本轮的工作定义（可证伪）：

1. 能指出每个口会改写第一问的哪一张嘴，或根本答不上第二问；
2. 对象仍是第一问那一件，不得为了更好塞进某个口把对象切粗或切细；
3. 现在用户只能看见 fulfilled，必须能说明：这证明看见层还没开，不证明第二问属于这三个词里的某一个；
4. 不得把「以后若另开一格」写成批准上线。

## 2. Oracle

- **对错尺子**：`spec/alg/fulfilled.md` 第一章、`spec/alg/product-function.md` §1 / §6–10、`spec/alg/authority.md` §8.3、`spec/info-volume.md`、046–048 / 058–061 Consensus、用户标注的两问结构。
- **不是 oracle**：canvas、准确率、`is_supported=false`、空条件、「暂不支持」文案、姓名/年/天气类型表、053–057 判定代理的「第二问」（整句有没有被这一维说完，对象不同）。
- 漏姓名 / 投保年 / 格式外 / 查天气 / I161 只当落点碰撞，不重判对错。

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

058–061 已锁的四层落点本轮只引用，不重写题面。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/**`、xlsx、canvas、`draft/judge.py`、协议正文、`issue-006`–`issue-061` 的已有正文（只许在本轮新 issue 里引用 Consensus）。
- May write: `issues/**`、`trace/**`。
- 不发明上线字段，不改前端，不代拟对外终句，不宣布采用「立住了 / 没立住 / 现成有 / 现成没有」。

## 4. Escalation

角色不得代选：

1. 要不要现在就让人在结果里看见第二问
2. 用哪一句中文当对外题面
3. 现在改不改 schema / 结果表
4. 去年算不算核心 / 称谓认不认 / 格式外算不算单号（仍停住）

本轮可以锁「这四个口哪个能当宿主」。打开与否仍停住。

## 5. Evidence standards

- 协议原文 + 现行出口原文（schema / 前端 / authority_gate / frontend_view）+ 已锁 Consensus。
- 不得用「我感觉放这里更干净」代替：同一件期望上的落点对照、以及「塞进这个口之后第一问还在不在」。
- architect 必须自己重读 cited 协议和出口，不抄 verifier 转述。
- 任一落点若让 Judge 再填一格、给 fulfilled 加枚举、只在 NF 后出现、把没立住写成 NE、或先分成姓名/年/天气再查表，即未达本轮。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 不重跑 judge；不改 prompt；不实现字段。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 问的是 fulfilled 定位下的结果口，不是改 golden，也不是改评测脚手架。
