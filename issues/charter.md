# Charter — 1A/4A 姓名场景：正常 + bad 混合过 judge，内存调试口径

> 替换上一轮 `issues/charter.md`（只做 341 叠加、集 B 未测）。
> 016–018 已 Consensus，不重开。
> 用户只拍 1A / 4A；去年 / 格式外 / 称谓 仍停住。
> 用户 `/council`：把这类场景的正常 case 和 bad case 都拉去跑一遍 judge，然后在内存里调试 judge，看哪种处理效果更好。

## 1. Goal & Definition of Done

- Goal: 只盯 1A 姓名场景。拉一份**正常 + bad** 的混合包（不是 341 准确率），先拿真实 live，再跑当前 draft judge；然后**不改 judge 源码**，在内存里对照几种判定出口。
- Done:
  1. 混合包 + live/judge 痕迹落盘；
  2. 内存对照至少四列：当前 judge、1A-wide、1A-surname、1A-role（角色闸，不是点名补丁）；
  3. 双闸仍是合取：集 A 缺陷族不得回退，集 B / 混合包头部 F 不得掉；
  4. 每个站得住的根因一个 issue；architect 独立重跑**内存叠加**并写 Consensus。

## 2. Oracle

- **政策**：1A = 2–4 字中文名可单独撑 F；杨杰与王坤林同侧=F；共展/豆芽仍 NF。
- **双闸**：集 A 盘客/假姓名/目录产品不得回退；集 B 真名 / 真名+产品 / 合法单号 F 不得掉。
- **对错尺子**：`spec/alg/fulfilled.md`、`spec/alg/material-positioning.md`。
- **不是 oracle**：canvas、341 准确率、过严 8 条、当前 LLM 逐案句子、叠加器自己的 18/18。
- 允许用 live 已解析出的产品/地址/会员等级字段当目录投影。
- 模拟必须**不点名 341 ID 当规则**。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/projects/client_search/` 生产路径、xlsx、canvas、`draft/judge.py`、`head_set_b.json`。
- May write: `issues/**`、`trace/**`。
- 不改「去年」、不改格式外/称谓。那两题的 case 必须 abstain。
- 不得把第三种内存口径直接并进判定或提示。本轮只比较，不发版。

## 4. Escalation

不得由角色拍板：

1. 「去年」核心还是附加（停住）
2. 格式外/称谓空条件怎么标（停住）
3. 昊轩（二字无姓）在 1A 下必须 F 还是可以继续 NF

## 5. Evidence standards

- 可复现脚本 + 落盘 JSON。
- architect 必须自己重跑内存叠加，不抄 verifier 数字。
- 本轮允许对混合包调用当前 draft judge（用户点名要跑）。LLM 痕迹冻结在 `issues/trace/`；architect **不要重花 LLM**，只核对冻结痕迹和叠加出口。
- 集 B 若某条没有 live 或没有 judge，必须写「未测」，不得用程序出口冒充。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 可跑当前 judge；不改 prompt。内存里可以试角色闸，但不能当成已上线口径。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 问的是「哪种 judge 处理更好」，要独立重算混合包，防止用 341 长尾自嗨。
