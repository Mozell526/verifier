# Charter — fulfilled 之外要不要单独表达「产品位内当前可支持」

> 本轮只辩原则，不重开 006–018，不改代码，不改协议正文。
> 用户 `/council`：2 和 3 看起来像一类（业务没满足，但现有能力下也算尽力了），但真正要辩的不是这几个 case。
> 当前 `fulfilled` 只回答「用户需求有没有满足」。有时还要看「产品功能定位以内，系统能不能明确指出当前尚未支持」。这层现在缺。
> 要辩：新增一层标签，还是改 `fulfilled.md`。不要做成纯 IT 能力清单。

## 1. Goal & Definition of Done

- Goal: 钉死这层抽象该不该有、挂在哪、不能跟「办成了」混成一个词。
- Done:
  1. 每个根因一个 issue + 协议原文；
  2. architect 独立重读协议后写 Consensus；
  3. 给用户的结论必须是原则选项，不要再让用户先填「去年 / 称谓 / 格式外」功能地图。

## 2. Oracle

- **对错尺子**：`spec/alg/fulfilled.md`（三态，不新增第四态）、`spec/alg/material-positioning.md`（`current_behavior` 不能冒充正式规则）、`spec/alg/authority.md` §8.3（职责外 → NE；职责内能力缺失 → 未达成则 NF，不得降 NE）、`spec/info-volume.md`（整体不引入 partial）。
- **不是 oracle**：canvas、341 准确率、当前 `is_supported=false` / 空条件 / 「暂不支持」文案、任何「系统尽力了所以算过关」。
- 2 和 3 只当碰撞举例，不重判对错。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/projects/client_search/` 生产路径、xlsx、canvas、`draft/judge.py`、协议正文。
- May write: `issues/**`、`trace/**`。
- 不发明上线字段，不给最终中文名。

## 4. Escalation

角色不得代选：

1. 要不要对外同时看见两件事：办成了没有，以及产品位内当前是否正确承认「尚未支持」
2. 若要第二件事：定义写在 `fulfilled.md` 附录、独立短文，还是 authority 消费章
3. 展示用的中文名字（若只是展示名，不改三态）
4. 现在是否改 schema

不要把「去年算不算核心 / 称谓认不认 / 格式外算不算单号」当作本轮主问题。那些仍停住。

## 5. Evidence standards

- 协议原文 + schema 原文。不得用「我感觉像同一类」代替失败对象对照。
- architect 必须自己重读 cited 协议，不抄 verifier 转述。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 不重跑 judge；不改 prompt；不实现字段。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 问的是协议分层，不是改 golden，也不是改评测脚手架。
