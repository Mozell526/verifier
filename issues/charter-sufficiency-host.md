# Charter — 充分性落到 draft judge

> 用户更新：要正确抽象、边界清楚、不要规则化；排除歧义，覆盖所有可能出现的情况；
> **然后构建 judge agent 的实现**。再次 `/council` + check / generalization /
> elegance / aihacking / bussiness。只盯 1A / 4A。昊轩必须成功、去年、称谓、
> 格式外、对外中文：仍停住，不代选。
>
> 042–045 已锁原则，不重开其对错。046–048 是另一条 sibling/枚举线，不混。
> 本轮从 049 起号。用户已打开「Investigation only」：要改的是 draft judge，
> 不是再写一份对照脚本。

## 1. Goal & Definition of Done

- Goal: 把已锁的充分性抽象落到 `draft` judge。judge 自己按两问判定；
  不是内存 overlay，不是题型表，不是覆盖门，不是又贴一段提示。
- Done:
  1. 源头互搏的裸词四句已删，且没有换成另一段「独立姓名证据」贴纸；
  2. `pre_judge` 在充分性打中时短路 LLM；`reconcile_result` 最后一句话幂等覆盖整份合同；
  3. 打中时 Q1 过 → fulfilled，Q1 不过 → not_fulfilled；打不中 → inherit（LLM 照旧）；
  4. 新实验打**新模块 + draft judge**，至少钉住：杨杰/王坤林 F；共展/豆芽 NF；
     红莲保单、唐诗颖生存金、李明的重疾险、李明重疾险 inherit；金凤当姓名 NF；
     真名+产品没交姓名 inherit；field_only 那 7 条误抬不得复现；
  5. 3–5 个新 issue（049+）；architect 独立重跑新实验并写 Consensus。

「不要有规则化」的工作定义（可证伪）：

1. 原则只许规定：看什么、不看什么、单位、封闭出口。对任意输入同一套。
2. 若必须先把问句分进预置类型再查表，即为规则化。
3. 若用残句为空 / 虚词表 / 再加字段类才能落格，即为规则化。
4. 若实现里出现点名样本 ID、混合包 `role`、或「王坤林算人名」例外，即为规则化。

「能覆盖所有可能出现的情况」的工作定义（可证伪）：

1. 覆盖 = 全函数：任意一次「问句 × live 条件」必落三态之一
   （fulfilled / not_fulfilled / inherit）。
2. inherit 是正式出口，不是漏洞。
3. 未在例表里出现过的形状，仍必须不改原则就能落格。

本轮 judge 与 044 overlay 的分界（必须写进 issue，不得混）：

```text
overlay（044）：只许主动抬成功；Q1 失败 → inherit；禁止主动改失败
judge 自己：充分性测试打中时必须说话
  Q1 过 → fulfilled
  Q1 不过 → not_fulfilled   # 这是字段标准，不是「认出假名」
  否则 → inherit
```

## 2. Oracle

- **政策**：1A = 2–4 字中文名可单独撑该姓名维；杨杰与王坤林同侧=成功；共展/豆芽仍失败。
  4A = 独立头部对照集 B；没有集 B 之前不拿 341 对错率发版。
- **尺子**：`spec/alg/fulfilled.md` §1 / §2.1，`issues/trace/name-sufficiency.md`。
  评的是「用户要的事办成了没有」。
- **不是 oracle**：canvas、341 准确率、混合包分数、过严 8 条、当前 LLM 逐案句子。
- 姓名尺读业务源 `field_mapping_args.yaml` + 产品枚举，不用 341 集 A 投影。
- 禁止点名 341 ID 当规则，禁止用混合包 `role` 分流。

## 3. Red lines

- Must not touch: `spec/**`、production `impl/projects/client_search/judge.py`、
  xlsx、canvas、`src/**`、`issue-006`–`issue-048` 已有正文
  （只许在本轮新 issue 里引用 Consensus）。
- May write: `impl/projects/client_search/draft/judge.py`、
  `impl/projects/client_search/draft/field_sufficiency.py`、
  对应测试、`issues/**`、`trace/**`。
- 不改「去年」、不改格式外 / 称谓。不得代选昊轩必须成功。
- 禁止把 `decide_sufficiency` / `decide_object_cover` / 残句代数贴进 prompt。
- 禁止剥虚词表。禁止新开年龄/产品/保费授权字段。

## 4. Escalation

不得由角色拍板：

1. 「去年」核心还是附加（停住）
2. 格式外 / 称谓空条件怎么标（停住）
3. 昊轩（二字无姓）在 1A 下必须成功
4. 要不要看见第二问 / 改不改 schema / 对外题面（仍停住）

## 5. Evidence standards

- 可复现：新实验必须 import 新模块和 `ClientSearchJudge`，不得再抄旧 overlay 当生产。
- architect 必须自己重跑新实验，不抄 verifier 数字，不重跑 48 次 LLM。
- 针必须分列 speak / inherit，禁止只报混合包分数。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 本轮已授权改 draft judge；不改协议。

## 7. Cast

- Initiator: verifier（用户已要求构建 judge 实现）
- Opponent: architect
- Reason: 防「换一套几何门把分数再刷一遍」，并审 Q1 失败在 judge 里说 NF 是不是又规则化。
