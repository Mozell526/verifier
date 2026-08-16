# Issue #038: 源头仍是提示里的姓名闸与 1A 互搏；原则再干净也不能并进 judge

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Judge host / check「只改结果不改源头」
**Cases**: `draft/judge.py` L1504–1508；对照 020 新鲜 judge 同形态左右互搏；本轮零生产改动

## Verifier Discovery

check skill：结果不对时要找生产源头，不能只改评测表上的数。本轮内存候选在冻结集上只抬王坤林，合成探针多了两格。这仍是叠加器。源头没动。

### 触发输入

只读：

- `impl/projects/client_search/draft/judge.py` L1504–1508（裸词规则）
- `impl/projects/client_search/draft/judge.py` L897 `_operator_justified`
- 冻结痕迹：I336 匡西永新鲜失败、HB002 张伟新鲜失败、I539 王坤林新鲜成功，live 都是 `searchClientName MATCH <整句>`
- 本轮脚本不 import、不 patch `judge.py`

原文：

> live 把它写成姓名、路径碰巧叫 searchClientName，都不够支撑 fulfilled
> 独立姓名证据指资料明确该 token 是人名（或该形态就是姓名检索）

1A 已拍：2–4 字中文名可单独撑成功。提示前半句还在要求「独立姓名证据」，后半句又说「该形态就是姓名检索」。模型每次咬半句，这就是 020 的左右互搏。

### 期望

012 Consensus：搬进代码的是出口和 blocking 标签，对齐 `_operator_justified`；不要另起规则 DSL。
020 Consensus：当前 draft 对同形态裸名仍左右互搏。
028 Consensus：内存口径再好看也不能并进 judge。

本 issue 不重开这三句的对错，只加本轮新约束：**037 的「分数撞车 / 合成探针多两格」不是源头已修。**

章程红线：不得把任一内存口径并进判定或提示。打开宿主必须用户确认。

### 实际

`simulate_1a_principle_program.py` 只读冻结 traces 和 xlsx，在内存里叠一层出口。重跑当前 `draft/judge.py`，匡西永 / 张伟这类整句真名仍可能失败，王坤林仍可能成功。尺自己在抖。

把 `decide_object_cover` 贴进 prompt 或写成 if/else，会同时犯三件事：

1. 012 禁止的另起 DSL
2. 用户已否的「看似没规则化、本质是规则化」换皮
3. check 说的只改结果：下次重跑宿主，叠加器还得再盖一层

姓名+产品六条 live 把姓名丢掉。改判定补不回来。019 已钉，本轮再次只 inherit。

### 根因层

原则解决的是「何时允许改判、何时必须闭嘴」。它不解决「宿主提示和 1A 还在互搏」。后者是生产源头。没有用户点头，角色不能打开 `judge.py`。

### 和 012 / 020 / 028 的边界

- 012：出口进代码，LLM 写证据。不重开。
- 020：左右互搏仍在。不重开。
- 028：已经 escalate 过同一源头。本 issue 是同一源头在新章程下的再钉，不是新的生产缺陷。

### 不是什么

- 不是本轮原则写错了所以不能发版。
- 不是要求立刻改 prompt。
- 不是允许先把对象覆盖并进代码「看看效果」。

### 可证伪修复

打开 `draft/judge.py` 或对应提示前，必须有用户确认。确认之前，任何「内存 41/47」或「合成探针 15/15」都不能当成修复。验收：工作区 `git diff -- impl/projects/client_search/draft/judge.py` 仍为空。

## Architect Response #1

**Verdict**: escalate-to-project

### Spawn Evidence
- spawn-id: 770d8502492aedbc
- pid: 44788

### Investigation

- Read `impl/projects/client_search/draft/judge.py` `_operator_justified` (L897 region) and the 裸词规则 at L1504–1508. Current host text:

  > If actual treats a token as a person name, Reference/path match alone is not intent proof. Without independent name evidence, do not mark that dimension fulfilled. 独立姓名证据指资料明确该 token 是人名（或该形态就是姓名检索）；live 把它写成姓名、路径碰巧叫 searchClientName，都不够支撑 fulfilled（§2.1）。

- Read frozen traces, same live shape `searchClientName MATCH <整句>`:
  - I336 匡西永: `judge_status=not_fulfilled`. Reason: 输入是裸词，没有独立证明其为人名.
  - HB002 张伟: `judge_status=not_fulfilled`. Reason: 仅凭裸词和自身姓名字段映射不足以证明其为客户本人姓名.
  - I539 王坤林: `judge_status=fulfilled`. Reason: 单姓加两字名的中文人名形态 … searchClientName MATCH 王坤林.
- `git diff -- impl/projects/client_search/draft/judge.py` is empty. Principle script does not import or patch `judge.py`.
- 012 / 020 / 028 are not reopened. 020 already named this left/right bite. 028 already escalated “memory口径不得并进 judge”. This issue only adds the new-charter nail: 037’s score collision + two synthetic cells are **not** a host fix.

### Reasoning

Escalate-to-project is the right verdict. There is no smaller **in-scope** action that fixes this issue.

What is still broken is the host prompt vs 1A: 2–4 字中文名可单独撑成功, but L1504–1508 still tells the model that `searchClientName` + the token is not enough unless it also finds “独立姓名证据”, while the same sentence offers “该形态就是姓名检索” as an escape. The three traces above are the same live object with opposite labels. The ruler is shaking. Object-cover can overlay F on those bare names in memory (and so can `live_identity`). That is a compare-only floor. Next fresh `draft/judge.py` run can still fail 匡西永 / 张伟 and pass 王坤林.

Why not a smaller in-scope write?

- Charter red line: do not touch `draft/judge.py`, do not merge any memory口径 into judge or prompt, this round compares only.
- Pasting `decide_object_cover` into the prompt or into an if/else is exactly 012’s forbidden second DSL, plus the user-rejected “看似没规则化、本质是规则化” reskin, plus check’s “只改结果不改源头”.
- More synthetics, a prettier JSON, or another issues/** note would document the fight. They would not stop the host from oscillating.
- HB009–014 remain inherit because live dropped the name. That is 019 (parser), not a judge patch.

The only move that addresses the source is a project-owner / user-confirmed edit of the 裸词规则 (and then a fresh host run). Architect cannot apply that.

### Improvement Proposal

- **Target**: `impl/projects/client_search/draft/judge.py` L1504–1508 (裸词规则) and the 1A prior it contradicts. Not the memory script. Not xlsx / set B / canvas.
- **Change** (owner only, after explicit user confirmation): rewrite the 裸词 paragraph so a 2–4 字、姓氏目录命中、非产品/地址目录词的 `searchClientName` value that equals the whole query is allowed to be fulfilled **without** a second “independent name evidence” veto. Do not paste `decide_object_cover`, residual algebra, or mix-pack roles into the prompt. Do not invent overlay NF. Leave 昊轩 / 去年 / 称谓 parked.
- **Verification**: after the owner change, re-run the **host** (not only the memory script) on I336 / HB002 / I539 / I224 and confirm the three 匡西永/张伟/王坤林 no longer split on the same live shape. `python3 issues/trace/simulate_1a_principle_program.py` may still be used as a compare floor, but its 41/47 and 15/15 must not be cited as the fix.
- **Why peer cannot apply**: architect is read-only; charter forbids opening `draft/judge.py` without user confirmation. This round’s writable set is `issues/**` only.

## Consensus
**Verdict**: escalate-to-project
**Official peer**: Architect Response #1 · spawn-id `770d8502492aedbc`

保持 escalate，不改成 real-problem。本轮原则和内存对照没有更小的 in-scope 动作能修源头。

源头仍是 `draft/judge.py` L1504–1508 裸词规则和 1A 互搏。同一 live 形状 `searchClientName MATCH <整句>`：匡西永 / 张伟失败，王坤林成功。尺子在抖。对象覆盖能在内存里把这些整句真名 overlay 成功，那只是对照地板；下一次宿主重跑仍可能把匡西永 / 张伟打失败。

禁止把 `decide_object_cover`、残句代数、混合包角色贴进提示或代码。那是 012 禁止的第二套 DSL，也是用户已经否掉的「规则换皮」。HB009–014 保持 inherit，是解析丢姓名（019），不是判定补丁能修的。

打开 `draft/judge.py` 或对应提示前，必须有用户确认。确认之前，内存 41/47、合成 15/15 都不能当成修复。验收：`git diff -- impl/projects/client_search/draft/judge.py` 仍为空。
