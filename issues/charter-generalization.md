# Charter — 1A 改判定的内存评测模拟

> 本轮替换 `issues/charter-unsupported-label.md`（「尚未支持」标签，用户已声明 2/3 先不动）。
> 006–012 已 Consensus，不再重开。
> 用户已拍：1A（2–4 字中文名可单独撑 F）、4A（独立集 B 18 条）。
> 用户 `/council`：在内存里模拟改判定后的评测效果，看行不行。

## 1. Goal & Definition of Done

- Goal: 不改 judge 源码，在内存里对 1A 姓名出口做可复现叠加；用双闸衡量效果——集 A 缺陷族不得回退，集 B 头部 F 不得掉。
- Done: 模拟脚本 + 落盘对照表；每个根因一个 issue + 原文数字；architect 独立重跑模拟后写 Consensus。

## 2. Oracle

- **政策**：1A = 2–4 字中文名可单独撑 F；杨杰与王坤林同侧=F；共展/豆芽仍 NF。
- **双闸**：集 A（341 badcase）盘客/假姓名/目录产品不得回退；集 B（`head_set_b.json`）真名 / 真名+产品 / 合法单号 F 不得掉。
- **对错尺子**：`spec/alg/fulfilled.md`、`spec/alg/material-positioning.md`。
- **不是 oracle**：canvas、341 准确率、过严 8 条、当前 LLM 逐案句子。
- 模拟必须**不点名 341 ID 当规则**。允许用 live 已解析出的产品/地址字段当目录投影。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/projects/client_search/` 生产路径、xlsx、canvas、`draft/judge.py`。
- May write: `issues/**`、`trace/**`、`impl/projects/client_search/draft/cases/**`（集 B 已冻结，本轮只读）。
- 不改「去年」、不改格式外/称谓。那两题的 case 模拟必须 abstain（保持原状态）。

## 4. Escalation

不得由角色拍板：

1. 「去年」核心还是附加（停住）
2. 格式外/称谓空条件怎么标（停住）
3. 昊轩（二字无姓）在 1A 下必须 F 还是可以继续 NF

## 5. Evidence standards

- 可复现脚本 + 落盘 JSON。architect 必须自己重跑，不抄 verifier 数字。
- 对照至少给出：当前新 judge、1A-wide、1A-surname+catalog 三列。
- 集 B 若没有 live/judge 痕迹，必须写明，不得假装跑过 LLM judge。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model（不要写 sonnet）
- 不重跑 LLM judge；不改 prompt。只做内存叠加。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 问的是「改完评测行不行」，要独立重算，防止自嗨。
