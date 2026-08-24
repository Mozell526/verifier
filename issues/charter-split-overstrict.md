# Charter — client_search 新旧 judge：互有对错 / 过严

## 1. Goal & Definition of Done

- Goal: 独立核对 `spec/patch/20260814/client-search-judge-compare-0814.canvas.tsx` 里标成「互有对错」和「过严」的 8 条：I485 I539 I161(+I046) I263 I288 I034 I616 I638。判定 canvas 的归因和 4 个根因是否站得住。
- Done: 每条有可复核证据（judge JSON / 协议原文 / draft 提示原文）；每个站得住的根因一个 issue；经 architect 挑战后写 Consensus。

## 2. Oracle

- 主尺子：`fulfilled.md`、`material-positioning.md`（canvas 自称的尺子）。
- 运行时行为：新 judge xlsx `verifier-client_search-cases-20260814-185013.xlsx` 与旧 `20260814-205846.xlsx` 的同 live 判定，以及 `impl/projects/client_search/draft/judge.py` 系统提示。
- docs 与 runtime 冲突时：runtime 是系统行为，但 **judge 对错以协议为准**，不能用 current_behavior 自我背书。
- canvas 本身不是 oracle，只是待审主张。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/projects/client_search/` 生产路径、xlsx、canvas。
- May write: `issues/**`、`trace/**`。只分析，不改代码、不改 judge。

## 4. Escalation

- 核心 vs 附加约束怎么划（「去年」算不算 blocking）→ 用户决定
- 姓名形态能否单独撑 F → 用户决定
- 是否启用/改 draft judge 提示 → 用户决定

## 5. Evidence standards

- 默认：可复现命令 + 原文摘录。协议条款、judge JSON expectation/reasoning、prompt 行号必须原文，不靠记忆。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: sonnet
- 不做全量 D1–D8；只审这 8 条及相关对照（I046）

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 问题在 judge 口径/协议适用，不是改 golden、也不是改评测脚手架
