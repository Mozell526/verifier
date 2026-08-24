# Charter — 和 fulfilled 同级的第二问，到底该问什么

> 本轮只辩抽象，不重开 006–021，不改代码，不改协议正文。
> 用户反馈：上一轮「产品位内有没有正确承认尚未支持」太窄，不像 fulfilled.md 那种层级。
> 「尽力了」可以看，但不确信是最好的抽象，要看其他角度。
> 用户自己试了几种问法，并点名：「放对地方 / 处置站不站得住」不合适，不懂位置是什么。
> 「办得了吗」可能分成两种，且容易和 fulfilled 搅在一起。

## 1. Goal & Definition of Done

- Goal: 钉死第二问的抽象层级、和 fulfilled 的切面、死掉的问法、还活着的候选。
- Done:
  1. 每个根因一个 issue + 协议原文；
  2. architect 独立重读协议后写 Consensus；
  3. 给用户的是 fulfilled.md 同级的候选问法，不是功能地图，也不是上线字段名。

## 2. Oracle

- **对错尺子**：`spec/alg/fulfilled.md` 第一章（只看一件事、三态、不区分没办成的原因、不新增第四态）、`spec/alg/authority.md` §1 / §8.2 / §8.3、`spec/alg/material-positioning.md` 不变量 1、`spec/info-volume.md`（不引入 partial、不需要第二套对错）、013–015 Consensus（死路仍死：第四态、「尽力了=F」、用 NE 表达定位内缺口、拿系统自报当标签）。
- **不是 oracle**：canvas、准确率、`is_supported=false`、空条件、「暂不支持」文案、常识功能地图。
- 2 / 3 只当碰撞举例，不重判对错。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/projects/client_search/` 生产路径、xlsx、canvas、`draft/judge.py`、协议正文、`issue-006`–`issue-021`。
- May write: `issues/**`、`trace/**`。
- 不发明上线字段，不给最终中文名。

## 4. Escalation

角色不得代选：

1. 活着的候选里，最终采用哪一句作为对外问法
2. 要不要现在改 schema
3. 去年算不算核心 / 称谓认不认 / 格式外算不算单号（仍停住）

## 5. Evidence standards

- 协议原文 + 013–015 已锁死路。不得用「我感觉更泛化」代替失败对象对照。
- architect 必须自己重读 cited 协议，不抄 verifier 转述。
- 每个候选问法必须能说明：它不偷走 fulfilled 的题；它不会把格式外和「现在办不了」收成同一个词。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 不重跑 judge；不改 prompt；不实现字段。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 问的是协议分层和抽象，不是改 golden，也不是改评测脚手架。
