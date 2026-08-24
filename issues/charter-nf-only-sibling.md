# Charter — 产品功能是不是只有 not_fulfilled 才有；Judge 说了 fulfilled 还会不会改口

> 本轮只辩原则，不重开 006–045 的对错结论，不改代码，不改协议正文，不改前端。
> 用户反馈：理解上不是只有 not_fulfilled 才有「产品功能」吗？要做判断的不是 harness AI，而是 Judge。Judge 如果已经判成 fulfilled，等会还会违逆自己的结论吗？所以才在考虑是不是应该做成 fulfilled 的新枚举值。

## 1. Goal & Definition of Done

- Goal: 钉死三件事——（1）产品功能是不是 NF 专属；（2）若 Judge 已经说办成了，第二问还在不在、算不算改口；（3）这件事是否因此必须做成 fulfilled 的新枚举值。
- Done:
  1. 每个根因一个 issue + 协议原文 + 失败对象对照；
  2. architect 独立重读协议后写 Consensus；
  3. 交给用户的是原则结论（有没有、谁答、算不算改口、要不要并进 fulfilled），不是上线字段，也不是改前端。

## 2. Oracle

- **对错尺子**：`spec/alg/fulfilled.md` 第一章（只看一件事、三态、不区分没办成的原因、不新增第四态）、`spec/alg/product-function.md`（另一件事、不进 Judge 产出）、`spec/alg/authority.md` §8.3（职责内能力缺失 + 实际达成 → fulfilled）、`spec/info-volume.md`（不引入 partial；judge 只产 fulfillment）、`spec/alg/material-positioning.md` 不变量 1。
- **已锁但仍可被本轮原则打到的点**：013–015 / 022–024 / 029–031 Consensus。本轮问的是「是不是只有 NF 才有 / Judge 会不会改口 / 因此要不要枚举」，不是重开第二问的抽象句。
- **不是 oracle**：canvas 准确率、`is_supported=false`、空条件、「暂不支持」文案、常识功能地图、前端现在只显示 fulfilled 这一事实本身（它只证明看见问题，不证明词表该怎么改）。
- I046 / I161 / 盘客 / 王坤林 只当碰撞举例，不重判对错，不预填去年 / 称谓。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/projects/client_search/` 生产路径、xlsx、canvas、`draft/judge.py`、协议正文、`impl/frontend/**`、`issue-006`–`issue-045`。
- May write: `issues/**`、`trace/**`。
- 不发明上线字段，不改前端，不宣布采用某一句对外中文。

## 4. Escalation

角色不得代选：

1. 要不要现在让用户在结果表里看见第二问
2. 看见的话放在哪一列、叫什么中文
3. 现在改不改 schema
4. 去年算不算核心 / 称谓认不认 / 格式外算不算单号（仍停住）

## 5. Evidence standards

- 协议原文 + 已锁 Consensus。不得用「我感觉只有失败才需要」代替格子对照。
- architect 必须自己重读 cited 协议，不抄 verifier 转述。
- 任一方案若让「办成了」自动消灭第二问，或让 Judge 同一张嘴兼答两问，或给 fulfilled 加第四态，必须当场说明它踩了哪条 oracle。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 不重跑 judge；不改 prompt；不实现字段；不改前端。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 问的是协议分层和出口形状，不是改 golden，也不是改评测脚手架。本线程前几轮 `/council` 已反复确认这一对阵容。
