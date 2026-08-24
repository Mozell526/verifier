# Issue #028: 源头仍是提示里的姓名闸与 1A 互搏；内存口径再好看也不能并进 judge

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Judge host / check「只改结果不改源头」
**Cases**: `draft/judge.py` L1504–1508；对照 020 新鲜 judge 同形态 7F/5NF

## Verifier Discovery

check skill：结果不对时要找生产源头，不能只改评测表上的数。本轮内存候选把混合包从 36 拉到 41，集 A 只抬王坤林。这仍是叠加器。源头没动。

### 触发输入

只读：

- `impl/projects/client_search/draft/judge.py` L1504–1508（裸词规则）
- `impl/projects/client_search/draft/judge.py` L897 `_operator_justified`
- 冻结痕迹：I336 匡西永新鲜 NF、HB002 张伟新鲜 NF、I539 王坤林新鲜 F，live 都是 `searchClientName MATCH <整句>`
- 本轮脚本不 import、不 patch `judge.py`

原文：

> live 把它写成姓名、路径碰巧叫 searchClientName，都不够支撑 fulfilled
> 独立姓名证据指资料明确该 token 是人名（或该形态就是姓名检索）

1A 已拍：2–4 字中文名可单独撑 F。提示前半句还在要求「独立姓名证据」，后半句又说「该形态就是姓名检索」。模型每次咬半句，这就是 020 的左右互搏。

### 期望

012：出口进代码，LLM 仍写证据，不得自行放行。风格对齐 `_operator_justified`。
check：源头不对，下次重跑还是错。
本轮章程：任何内存口径都不得并进判定。

### 实际

- 当前 draft judge 对整句真名仍抖（I336 / HB002 等）。
- coverage-gate 在内存里把「整句被收成 searchClientName + 姓氏目录」当成 1A 的确定性出口。这是候选形状，不是已上线闸。
- 若现在把函数粘进 `judge.py`，会跳过：提示怎么改、blocking 标签怎么搬、昊轩政策、姓名+产品 parser。那是只改结果。

### 根因层

源头有两层，不要并成一层：

1. **判定宿主**（012 / 本 issue）：1A 这种已拍出口不该再让模型选半句。coverage-gate 是一种可讨论的闸形状。
2. **解析交付**（019）：姓名+产品 live 丢姓名。闸再干净也变不成 F。

check 的正确动作是：先让用户确认要不要动判定宿主；动的时候删掉 L1504–1508 的互搏句，改成代码闸 + LLM 证据；parser 另开，不在本轮偷偷做。

### 和 012 / 020 / 026 的边界

- 012：宿主放错层。仍成立。
- 020：同形态互搏。新鲜痕迹仍在。不重开数字，只指回源头。
- 026：候选效果。本 issue 禁止把 026 的 41/47 当成已经修了源头。

### 不是什么

- 不是本轮改 `judge.py` 或 prompt。修改前必须问用户。
- 不是把姓氏表写进提示当「王坤林算人名」。
- 不是代选昊轩。

### 可证伪修复

重跑当前 draft judge，整句真名（杨杰/王坤林/张伟/匡西永）仍左右互搏，则源头未修。把叠加器分数写进报告当「已修复」，则未修本 issue。

发版前最低限度（需用户确认后才做）：代码闸决定 1A 出口；L1504–1508 互搏句删除；LLM 不得自行放行；昊轩继续 abstain。

---

## Architect Response #1

**Verdict**: escalate-to-project

### Spawn Evidence
- spawn-id: 8eecb710b62b55a7
- pid: 95897

### Investigation

只读，未改 `judge.py` / xlsx / set B / 脚本。确认脚本顶部声明且实际 import 只有 `inspect/json/re/collections/pathlib/openpyxl`，不 import、不 patch `draft/judge.py`。

`impl/projects/client_search/draft/judge.py` L1504–1508 原文仍在：

- L1504 `### 裸词规则`
- L1505–1506 路径/Reference 不够，没有独立姓名证据不得 F
- L1507 「独立姓名证据指资料明确该 token 是人名（或该形态就是姓名检索）」
- L1508 「live 把它写成姓名、路径碰巧叫 searchClientName，都不够支撑 fulfilled（§2.1）」

同一提示里后半句承认「该形态就是姓名检索」，前半句和 L1508 又把 live `searchClientName` 整句检索否掉。L897 `_operator_justified` 的合同是「确定性 gate，prompt 不得自行放行其他例外」。1A 已拍「2–4 字中文名可单独撑 F」，却仍让模型在这两句里选边。

冻结痕迹（不重跑 LLM）仍是同形态互搏，数字沿用 020，不重开 020：

- I224 杨杰 / I539 王坤林：live `searchClientName MATCH <整句>`，新鲜 F
- I336 匡西永 / HB002 张伟：同一 live 形态，新鲜 NF
- I485 昊轩：新鲜 NF，与 xlsx 同侧

内存候选把混合包 36→41、集 A 只抬王坤林，全部发生在叠加器里。源头句子没动。

### Reasoning

诊断同意，处置升级，不在本轮修生产。

012 Consensus：出口进代码，LLM 写证据，不得自行放行。020 Consensus：当前 draft 对同形态裸名仍左右互搏。本 issue 不重开这两句的对错，只加本轮新约束：**026 的 41/47 和「只抬王坤林」不是源头已修。** check skill 说得对——只改评测表上的数，下次重跑当前 draft 还是抖。

章程 `issues/charter-name-generalization.md` §3 / §6 已经锁死：不改 `draft/judge.py`，不改 prompt，任何内存口径不得并进判定，本轮只比较。把 `exit_live_identity` 粘进 `judge.py` 会跳过提示怎么改、blocking 标签怎么搬、昊轩政策、姓名+产品 parser。那是只改结果，正好踩红线，也踩 021「role 不得并进」的同类错误。

因此本题不能判成「现在就按 026 的函数改宿主」的 real-problem。问题是真的，但打开宿主是项目侧决定；architect 只读，本轮也无权改。正确动作是：比较继续留在内存；发版前必须用户确认再动 L1504–1508。019 的解析层仍分开，不在本轮偷偷做。§4 三问继续停住。

### Improvement Proposal

- **Target**: 现在：什么都不并进 `impl/projects/client_search/draft/judge.py`。将来若用户明确打开判定宿主：L1504–1508 互搏句删除；1A 已拍出口改成代码闸（形状可讨论 coverage-gate，但必须是代码，不是再贴一套提示）；风格对齐 L897 `_operator_justified`（prompt 不得自行放行）；LLM 只写证据。昊轩继续 abstain。parser（HB009–014）另开。
- **Change**: 本轮零代码。禁止把 `simulate_1a_coverage_program.py` 的任一 `exit_*` 粘进 judge。禁止把 41/47 写进报告当「已修复」。
- **Verification**: 不重跑 48 次 LLM。读 L1504–1508 仍在，即源头未修。冻结 I336/HB002 仍 NF、I539/I224 仍 F，即互搏仍在。
- **Why peer cannot apply**: 角色只读；章程禁止改 `draft/judge.py` / prompt / 生产路径；删互搏句并上代码闸要用户先确认打开宿主。昊轩 / 去年 / 格式外不由本轮代选。

## Consensus
**Verdict**: escalate-to-project

接受 architect 把处置从「本轮可修」升级成项目侧决定。源头 `draft/judge.py` L1504–1508 仍在和 1A 互搏；内存 36→41 / 只抬王坤林都是叠加器。章程 §3 / §6 禁止本轮改 `draft/judge.py` 或把 overlay 并进判定。

check：修改生产代码前必须问用户。若以后打开宿主：删 L1504–1508 互搏句；1A 已拍出口改代码闸（形状可讨论 coverage-gate，必须是代码不是再贴提示）；对齐 `_operator_justified`；LLM 只写证据；昊轩 abstain；parser（HB009–014）另开。不得把 026 的 41/47 写进报告当「已修复」。

本 issue 在用户未确认打开宿主、或当前 draft 对整句真名仍左右互搏时保持 open。
