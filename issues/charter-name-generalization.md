# Charter — 姓名场景泛化：coverage-gate 候选 vs 规则机负对照

> 本轮主章程。不覆盖 `issues/charter.md`（019–021 已完成）或
> `issues/charter-sibling-question.md`（022–024）。
> 016–024 已有 Consensus 的不重开。
> 用户只拍 1A / 4A。用户否掉上一轮 `exit_role`：太规则化，姓名只是问题之一。
> 用户 `/council` + check / generalization / elegance / aihacking / bussiness：
> 解决姓名类场景的泛化性，并在内存里调试 judge，看哪种处理更好。

## 1. Goal & Definition of Done

- Goal: 不改 judge 源码。在冻结 live/judge 上对照：**负对照**（current / wide / surname / role）对一个**更短的 coverage-gate 候选**。候选不得再做成姓名题型状态机。
- Done:
  1. 新脚本 + 落盘（不改旧 `simulate_1a_mixed_program.py` 当发版口径）；
  2. 必须报「主动 overlay / 继承 inherit」，禁止只报 41/47；
  3. 双闸仍是合取：集 A 盘客/假姓名/目录产品不得回退；集 B 真名 / 合法单号 F 不得掉；姓名+产品不得用问句补姓名抬 F；
  4. 3–5 个新 issue（025+）；architect 独立重跑内存脚本并写 Consensus。

## 2. Oracle

- **政策**：1A = 2–4 字中文名可单独撑 F；杨杰与王坤林同侧=F；共展/豆芽仍 NF。
- **双闸**：集 A 缺陷族不得回退；集 B 真名 / 真名+产品 / 合法单号 F 不得掉。真名+产品若 live 没交姓名，诚实 NF，不算判定胜利。
- **对错尺子**：`spec/alg/fulfilled.md`、`spec/alg/material-positioning.md`。
- **不是 oracle**：canvas、341 准确率、混合包 41/47、过严 8 条、当前 LLM 逐案句子。
- 允许用 live 已解析出的产品/地址字段当目录投影。
- 模拟必须**不点名 341 ID 当规则**，也不得用混合包 `role` 字段做出口分流。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/projects/client_search/` 生产路径、xlsx、canvas、`draft/judge.py`、`head_set_b.json`。
- May write: `issues/**`、`trace/**`。
- 不改「去年」、不改格式外/称谓。昊轩必须 abstain。
- 不得把任一内存口径并进判定或提示。本轮只比较，不发版。
- 禁止再发明第四套姓名状态机（百家姓架构 + 保单号正则 + 业务词表 + 场景角色分流）。

## 4. Escalation

不得由角色拍板：

1. 「去年」核心还是附加（停住）
2. 格式外/称谓空条件怎么标（停住）
3. 昊轩（二字无姓）在 1A 下必须 F 还是可以继续 NF

## 5. Evidence standards

- 可复现脚本 + 落盘 JSON。
- architect 必须自己重跑**新**内存脚本，不抄 verifier 数字，不重跑 48 次 LLM。
- 冻结痕迹在 `issues/trace/name_scenario_runs/`。
- 候选必须比 `exit_role` 短，且不得依赖 `PERSON_THEN_POLICY` / 混合包 role 分流。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 不改 prompt。内存里可以试 coverage-gate，但不能当成已上线口径。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 用户已 `/council`，且要防「换一套规则机把 41/47 再刷一遍」。
