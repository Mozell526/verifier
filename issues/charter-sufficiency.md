# Charter — 姓名场景：充分性，不是覆盖门

> 本轮主章程。不覆盖已有章程。
> 025–041 已有 Consensus 的不重开其对错结论。
> 本轮要审的是：035–038 留下的「对象覆盖 / 残句为空」
> 是不是用户说的「看似没有规则化，本质其实是规则化」。
>
> 用户只拍 1A / 4A。用户更新：方案很奇怪，很难指出问题，
> 担心扩散到别处失败，看似没规则化本质是规则化。
> 用户 `/council` + check / generalization / elegance / aihacking / bussiness：
> 解决姓名类场景的泛化性，并在内存里调试 judge；
> 要正确抽象，边界清楚，不要规则化，排除歧义，覆盖所有可能出现的情况。

## 1. Goal & Definition of Done

- Goal: 不改 judge 源码。钉死可泛化的原则 / 标准 / 边界，并在冻结 live 上内存对照。
  候选不得再做成姓名题型状态机，也不得把「残句为空 / 整句被对象盖住」再包装成新架构。
  `object_cover` 与 `live_identity` 本轮都降为对照，不再当可泛化架构卖。
- Done:
  1. 原则正文把两问拆开：字段证据标准 ≠ 整句覆盖；
     每个输入都有定义结果（主动改成功 / 不改判）；禁止主动改失败；
  2. 新脚本 + 落盘（不改旧 `simulate_1a_coverage_program.py` /
     `simulate_1a_principle_program.py` 当发版口径）；
  3. 必须分列 overlay / inherit，禁止只报混合包分数；
  4. 必须有消融：把 1A 当成「交了姓名就算整句办成」时，
     会误抬哪些冻结题（至少包含红莲保单、生存金类）；
  5. 3–5 个新 issue（042+）；architect 独立重跑新脚本并写 Consensus。

「不要有规则化」的工作定义（可证伪）：

1. 原则只许规定：看什么、不看什么、单位、封闭出口。对任意输入同一套。
2. 若必须先把问句分进预置类型（姓名题 / 保单题 / 生存金题），再按类型查表，即为规则化。
3. 若用「挖掉交付值后残句是否为空」当「用户要的事办成了没有」的定义，即为规则化。
4. 新形状若要靠「再剥一个虚词 / 再加一种字段」才能落格，即为规则化。

「能覆盖所有可能出现的情况」的工作定义（可证伪）：

1. 覆盖 = 全函数：任意一次「问句 × live 条件」必落两态之一（主动改成功 / 不改判）。
2. 覆盖 ≠ 尽量多改判。不改判是正式出口，不是漏洞。
3. 未在例表里出现过的形状，仍必须不改原则就能落格。

## 2. Oracle

- **政策**：1A = 2–4 字中文名可单独撑该姓名维成功；杨杰与王坤林同侧=成功；共展/豆芽仍失败。
  4A = 独立头部对照集 B，不从 341 条 badcase 里挑；没有集 B 之前不拿 341 对错率发版。
- **双闸**：集 A 盘客 / 假姓名 / 目录产品不得回退；集 B 真名 / 合法单号成功不得掉。
  真名+产品若 live 没交姓名，诚实保持失败，不算判定胜利。
- **对错尺子**：`spec/alg/fulfilled.md`、`spec/alg/material-positioning.md`。
  评的是「用户要的事办成了没有」，证据只认 live 交出的条件。
- **不是 oracle**：canvas、341 准确率、混合包 41/47、过严 8 条、当前 LLM 逐案句子、
  残句为空、整句相等本身。
- 允许用 live 已解析出的产品 / 地址字段当目录投影。
- 模拟必须**不点名 341 ID 当规则**，也不得用混合包 `role` 字段做出口分流。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/projects/client_search/` 生产路径、xlsx、canvas、
  `draft/judge.py`、`head_set_b.json`、`issue-006`–`issue-041` 已有正文
  （只许在本轮新 issue 里引用 Consensus）。
- May write: `issues/**`、`trace/**`。
- 不改「去年」、不改格式外 / 称谓。昊轩必须 abstain。
- 不得把任一内存口径并进判定或提示。本轮只比较，不发版。
- 禁止再发明第四套姓名状态机。
- 禁止把 `object_cover` / `exit_live_identity` 再包装成「新原则」却不声明它只是充分性特例。

## 4. Escalation

不得由角色拍板：

1. 「去年」核心还是附加（停住）
2. 格式外 / 称谓空条件怎么标（停住）
3. 昊轩（二字无姓）在 1A 下必须成功还是可以继续失败
4. 要不要看见第二问 / 改不改 schema / 对外题面（仍停住）

## 5. Evidence standards

- 可复现脚本 + 落盘 JSON。
- architect 必须自己重跑**新**内存脚本，不抄 verifier 数字，不重跑 48 次 LLM。
- 冻结痕迹在 `issues/trace/name_scenario_runs/`。
- 原则必须是全函数。负对照保留 current / wide / surname / role / live_identity / object_cover。
- 消融 `field_only` 必须单独报：它若没有误抬「姓名已交、但用户还要了别的事」，本轮失败。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 不改 prompt。内存里可以试充分性，但不能当成已上线口径。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 用户已 `/council`，且要防「换一套覆盖门把分数再刷一遍」。
