# Issue #042: 用户说不清的别扭，是覆盖门在冒充原则

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 原则 / 标准 / 边界（内存候选，不是生产代码）
**Cases**: 只作碰撞针。不重判 025–041 的对错结论。

## Verifier Discovery

用户原话：方案很奇怪，很难指出到底是啥问题，担心扩散到别处失败，看似没有规则化、本质其实是规则化。

025 已经否掉题型分流。035 已经把「值=整句」降成对象覆盖的特例。
用户还是不安。本 issue 只钉：不安对应的是「残句为空 / 对象把问句盖住」这张嘴，不是又要换一句口语。

### 覆盖门在干什么

`decide_object_cover`（`simulate_1a_principle_program.py`）对任意输入问三件事：

1. 每个交付值是不是问句里的连续原文
2. 挖掉这些原文后残句空不空
3. 交出来的东西里有没有姓名或单号，姓名过不过 1A

三问都过，才主动改成功。从不过失败。

这看起来没有「姓名题 / 保单题」这些类型名，所以像原则。
它实际定义的是：问句有没有被身份对象消耗完。

`fulfilled.md` §1 评的是「用户要的事办成了没有」。
消耗完问句 ≠ 办成了用户要的事。

### 为什么这就是规则化

章程本轮把规则化写成：

- 先分预置类型再查表
- 或用残句是否为空定义办成了没有
- 或新形状必须再剥虚词 / 再加字段类才能落格

对象覆盖踩中后两条。它不需要类型名。

扩散形状不靠再想例子，冻结集和合成针已经有：

- 「唐诗颖的生存金有没有领取」交了姓名。残句不是空的。覆盖门这口不说话；若有人把 1A 当整句成功，生存金题会被抬走。见 043。
- 「李明的重疾险」交齐后还剩「的」。要抬它就得剥「的」。
- 「45岁女性保费10万以上」交齐年龄/性别/保费后还剩「岁/以上」。覆盖门因为没有姓名/单号闭嘴；要张嘴就得加字段类，再剥「以上」。
- `strip_any` 真的去掉身份门之后，冻结集上抬了「综拓潜客」「客户」。见 044。

所以「看似没规则化」来自：没有题型名、对任意输入问同一套。
「本质是规则化」来自：那一套是句子消耗规则，扩散必须加表。

### 和 035–038 的关系

不重开 035「整句门不是原则」。
不重开 026「整句门过双闸、只抬王坤林」当局部地板。

否的是 036 把对象覆盖扶成整句门的上位原则。
本轮合法关系见 `issues/trace/name-sufficiency.md` §6：

```text
整句相等 + 字段标准 = 本轮授权的充分性测试
≠ 覆盖门的特例
≠ 「用户要的事办成了没有」的一般定义
```

替代原则在 044。消融在 043。仍停住的项目决定在 045。

### 不是什么

- 不是说 1A 错了
- 不是要重开题型分流
- 不是宣布采用某一句对外中文
- 不是把 41/47 当失败或胜利

### 可证伪

1. 若「残句为空」能被协议原文证明就是「用户要的事办成了没有」，本 issue 失败。
2. 若对象覆盖离开姓名/单号场、又不加虚词表/字段类，仍能正确处理生存金/保费/年龄题，本 issue 失败。
3. 若 036 的对象覆盖已被证明只是充分性测试的另一种写法、且不含残句定义，本 issue 失败。

### 未消元

- 1A 被当成整句成功会误抬什么：043
- 充分性候选与分数撞车：044
- 看不看得见、并不并进 judge：045

---
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 15b6719c8967bbf9
- pid: 81087

### Investigation

- Read `issues/open/issue-042.md`, `issues/charter-sufficiency.md` §1–§3, `issues/trace/name-sufficiency.md` §1 / §6 / §9, `spec/alg/fulfilled.md` §1 / §2.1, `spec/alg/material-positioning.md` 不变量 1, and Consensus-only blocks in `issue-035.md` / `issue-036.md`.
- Read `decide_object_cover` at `issues/trace/simulate_1a_principle_program.py` L94–148 and `decide_sufficiency` / `decide_field_only` / `decide_strip` at `issues/trace/simulate_1a_sufficiency_program.py` L79–177.
- Independently reran `python3 issues/trace/simulate_1a_sufficiency_program.py`. Exit 0. `dump_sha256=aaa5381cefef843ad52b706dc1a7813db5308c8b707f3ae07b3cefd859f5c980`. `synthetics_ok=true`. Did not rerun the 48 LLM judges. Did not touch the two older simulators as release口径.
- Own dump, not verifier prose:
  - set A: `sufficiency_vs_live_identity=0`, `sufficiency_vs_object_cover=0`
  - mixed pack: same two diffs empty; agree `current=36` / `wide=27` / `surname=35` / `sufficiency=object_cover=live_identity=field_only=41`
  - set A flips: sufficiency / object_cover / live_identity each `lifted_to_f=1` (I539 王坤林); field_only `10`; strip_any `3`
- Re-applied the decide functions on frozen rows and synthetics. Two function-identity facts:

  1. `object_cover` is **not** the same total function as `sufficiency`. Witness `SYN-concat`「李明重疾险」+ `searchClientName=李明` + `abbrname=重疾险`: sufficiency `None/not_single_field`, live_identity `None`, object_cover `fulfilled/overlay_f_mixed` residual `''`. Frozen production traces simply do not contain this cell, so the 0-row collision is observational, not definitional.
  2. Covering's Q2 is residual emptiness. `decide_object_cover` L109–116 returns inherit whenever `leftover_text` is non-blank. I248 residual `保单`. I213 residual `的生存金有没有领取？`. `SYN-particle` residual `的`. `SYN-age` residual `岁保费以上`; after `DOMAIN_PARTICLES` (`岁/以上/有/未`) the leftover is still `保费`.
- Leaving the name/id field already fails on frozen set A. I129「综拓潜客」: residual already `''`, object_cover `no_identity_field`, strip_any `fulfilled/strip_cover`. I246「客户」: same pattern (`isBuyInsurance=客户`). That is the spread the user named, already visible in-memory.
- 036 Consensus did **not** rewrite `fulfilled.md` §1. It locked covering as the upper cut for this overlay (`issue-035.md` Consensus: 整句相等 = 对象覆盖在「恰好一个字段且值=问句」时的特例) and already said peeling `的/查一下/保单号` is the next table. 042 does not over-read the residual predicate; it correctly rejects the polarity that put that predicate above the sufficiency test.

### Reasoning

Residual-empty covering is hidden regularization. The charter's own falsifiers are met, and 042's three kill-shots all miss.

`fulfilled.md` §1 / §2.1 grades「用户要的事办成了没有」and requires evidence that the user got the result they asked for. `decide_object_cover` grades「交付值是不是原文、挖掉后还剩字吗、有没有姓名/单号」. Consuming the sentence is not proving the request. Protocol text does not identify those two questions. Falsifier 1 fails to kill the issue.

Object_cover cannot leave the name/id field and still handle 生存金 / 保费 / 年龄 without a particle table or a new field class. On those shapes it either inherits (I213, `SYN-age`) or, once `require_identity` is dropped, it lifts I129 / I246. Falsifier 2 fails to kill the issue.

Object_cover is not「充分性测试的另一种写法、且不含残句定义」. The residual branch is L109–116. The multi-object empty-residual branch is `overlay_f_mixed` on `SYN-concat`. Falsifier 3 fails to kill the issue.

The "looks un-regularized" surface is real: one procedure, no 姓名题/保单题 labels, total function over `(query × live)`. The "is regularized" interior is also real: Q2 is a sentence-consumption rule. New shapes do not land by the same rule; they demand the next particle (`的`) or the next field class (`岁/以上` still leave `保费`). That is exactly charter §1 items 3–4.

Score collision with sufficiency on set A / mixed is not a counter-argument. Those two mouths agree on the frozen traces because the traces almost never deliver multiple identity/catalog objects that tile the query. The functions diverge as soon as that cell appears. 036's "covering is the upper principle, whole-query is its special case" is the polarity this charter forbids. Do not promote `object_cover` or residual-empty as architecture.

### Improvement Proposal

- **Target**: `issues/trace/name-sufficiency.md` §6 (already written, must be the lock); `issues/trace/simulate_1a_principle_program.py` L94–148 stay a **control**; `issues/trace/simulate_1a_sufficiency_program.py` L107–126 stay the candidate mouth. Do not edit `simulate_1a_coverage_program.py` / `simulate_1a_principle_program.py` as release口径. Do not touch `draft/judge.py`.
- **Change**: Consensus on this issue must invert the 035 polarity and stop there.

```text
整句相等 + 字段标准
  = 本轮授权的充分性测试
  ≠ 覆盖门的特例
  ≠ fulfilled.md「用户要的事办成了没有」的一般定义

object_cover / live_identity / strip_* = 对照
残句为空不得再当 Q2
不得为了抬「李明重疾险 / 生存金 / 保费 / 年龄」加虚词表或字段类
```

No new decide function. No public Chinese sentence. `decide_object_cover` keeps its residual branch so the control still exhibits the regularization; it is not deleted and not promoted.
- **Verification**:

```bash
python3 issues/trace/simulate_1a_sufficiency_program.py
python3 -c "import json; from pathlib import Path; d=json.loads(Path('issues/trace/simulate_1a_sufficiency_program.json').read_text()); assert d['dump_sha256']=='aaa5381cefef843ad52b706dc1a7813db5308c8b707f3ae07b3cefd859f5c980'; assert d['set_a']['sufficiency_vs_object_cover']==[]; assert d['set_a']['sufficiency_vs_live_identity']==[]; rows={r['id']:r for r in d['synthetics']['rows']}; assert rows['SYN-concat']['sufficiency'] is None; assert rows['SYN-concat']['object_cover']=='fulfilled'; assert rows['SYN-particle']['object_cover'] is None; assert rows['SYN-age']['object_cover'] is None; print('042 lock ok')"
```
## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `15b6719c8967bbf9`

用户说不清的别扭，就是覆盖门在冒充原则。覆盖门对任意输入问同一套（值是不是原文、挖掉后还剩字、有没有姓名/单号），所以看起来没有题型名。它实际定义的是「问句有没有被身份对象消耗完」。消耗完问句 ≠ `fulfilled.md` §1「用户要的事办成了没有」。

本 issue 三支可证伪都没被打死：协议原文没有把残句为空写成办成；离开姓名/单号场、不加虚词表/字段类，覆盖门处理不了生存金/保费/年龄；覆盖门也不是「不含残句定义的充分性另一种写法」。`SYN-concat`「李明重疾险」已经把两张嘴分开：充分性不改判，覆盖门改成功。冻结集上行级终态相同，只说明生产痕迹里几乎没有「多对象刚好把问句盖住」这一格，不是函数相同。

本轮锁死关系（覆写 035「覆盖门是上位、值=整句是它的特例」这一句极性，不重开 035 其它对错）：

```text
整句相等 + 字段标准
  = 本轮授权的充分性测试
  ≠ 覆盖门的特例
  ≠ fulfilled.md「用户要的事办成了没有」的一般定义
```

`object_cover` / 残句为空只留作对照。不得再当架构。不得为了抬「李明重疾险 / 生存金 / 保费 / 年龄」加虚词表或字段类。

闸：exit 0，`isolation_valid=true`，`scope_valid=true`。architect 独立重跑 SHA-256 `aaa5381cefef843ad52b706dc1a7813db5308c8b707f3ae07b3cefd859f5c980` 未变。不并进 `draft/judge.py`。
