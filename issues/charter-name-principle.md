# Charter — 姓名场景：原则 / 标准 / 边界（对象覆盖）

> 本轮主章程。不覆盖已有章程：
> `issues/charter.md`、`charter-name-generalization.md`、
> `charter-sibling-question.md`、`charter-unambiguous-sibling.md`、
> `charter-unsupported-label.md`、`charter-zero-ambiguity-boundary.md`。
> 016–034 已有 Consensus 的不重开。
> 用户只拍 1A / 4A。用户否掉的是气质：覆盖门看似没规则化，本质是规则化；
> 担心扩散到别处失败。主会话已当场认账：不得再把整句相等卖成可泛化架构。
> 用户 `/council` + check / generalization / elegance / aihacking / bussiness：
> 解决姓名类场景的泛化性，并在内存里调试 judge；
> 设计要注重抽象 / 原则 / 标准 / 边界，排除歧义，覆盖所有可能出现的情况。

## 1. Goal & Definition of Done

- Goal: 不改 judge 源码。写出无歧义的原则 / 标准 / 边界，并在冻结 live 上内存对照。
  候选不得再做成姓名题型状态机，也不得把「整句相等」重新包装成新架构。
  `live_identity` 本轮降为局部地板 / 负对照。
- Done:
  1. 原则正文（每个输入都有定义结果：主动改成功 / 主动改失败 / 不改判）；
  2. 新脚本 + 落盘（不改旧 `simulate_1a_coverage_program.py` 当发版口径）；
  3. 必须分列「主动 overlay / 继承 inherit」，禁止只报混合包分数；
  4. 若冻结数据上分数与 `live_identity` 完全一样，必须老实写：本轮赢的是标准和边界，不是新分数；
  5. 3–5 个新 issue（035+）；architect 独立重跑新脚本并写 Consensus。

## 2. Oracle

- **政策**：1A = 2–4 字中文名可单独撑成功；杨杰与王坤林同侧=成功；共展/豆芽仍失败。
- **双闸**：集 A 盘客 / 假姓名 / 目录产品不得回退；集 B 真名 / 合法单号成功不得掉。
  真名+产品若 live 没交姓名，诚实保持失败，不算判定胜利。
- **对错尺子**：`spec/alg/fulfilled.md`、`spec/alg/material-positioning.md`。
  评的是「用户要的事办成了没有」，证据只认 live 交出的条件。
- **不是 oracle**：canvas、341 准确率、混合包 41/47、过严 8 条、当前 LLM 逐案句子。
- 允许用 live 已解析出的产品 / 地址字段当目录投影。
- 模拟必须**不点名 341 ID 当规则**，也不得用混合包 `role` 字段做出口分流。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/projects/client_search/` 生产路径、xlsx、canvas、`draft/judge.py`、`head_set_b.json`。
- May write: `issues/**`、`trace/**`。
- 不改「去年」、不改格式外 / 称谓。昊轩必须 abstain。
- 不得把任一内存口径并进判定或提示。本轮只比较，不发版。
- 禁止再发明第四套姓名状态机（百家姓架构 + 保单号正则 + 业务词表 + 场景角色分流）。
- 禁止把 `exit_live_identity` / 整句覆盖门再包装成「新原则」却不声明特例关系。

## 4. Escalation

不得由角色拍板：

1. 「去年」核心还是附加（停住）
2. 格式外 / 称谓空条件怎么标（停住）
3. 昊轩（二字无姓）在 1A 下必须成功还是可以继续失败

## 5. Evidence standards

- 可复现脚本 + 落盘 JSON。
- architect 必须自己重跑**新**内存脚本，不抄 verifier 数字，不重跑 48 次 LLM。
- 冻结痕迹在 `issues/trace/name_scenario_runs/`。
- 原则必须是全函数：任意 (问句, live 条件) 都能落到三态之一，禁止「看情况」。
- 负对照保留 current / wide / surname / role / live_identity。候选另起函数名。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 不改 prompt。内存里可以试对象覆盖，但不能当成已上线口径。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 用户已 `/council`，且要防「换一套局部规则把分数再刷一遍」。
