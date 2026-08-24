# Issue #043: 1A 是字段标准；当成整句成功会在冻结集上误抬生存金和红莲保单

**Class**: evaluation
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: 内存消融（不是生产代码）
**Cases**: I248 红莲保单、I213 唐诗颖的生存金、I154 张小岗保费/居养、I597 车险+邢同文。只作针。

## Verifier Discovery

1A 已拍：2–4 字中文名可单独撑**姓名维**成功；杨杰与王坤林同侧；共展/豆芽仍失败。
用户担心的扩散，就是有人把「姓名维过了」写成「整句办成了」。

本 issue 用冻结 live 做消融，不发明新题型。

### 两问

```text
Q1  这个交出来的姓名值，够不够撑住姓名维？（1A）
Q2  用户要的事是不是就是这一维，并且已经交齐？
```

`field_only`（`simulate_1a_sufficiency_program.py`）故意把 Q1 当成 Q2：
只要 live 交了一个过 1A 的姓名、或一段能在问句里落地的单号，就主动改成功。
从不过失败。

`sufficiency` 只在「恰好一个字段，值等于整句，且 Q1 通过」时改成功。

### 冻结集 A 上的结果

脚本：`python3 issues/trace/simulate_1a_sufficiency_program.py`
落盘 SHA-256：`aaa5381cefef843ad52b706dc1a7813db5308c8b707f3ae07b3cefd859f5c980`

相对当前判定：

| 口径 | 翻到成功 | 翻到失败 |
|---|---|---|
| sufficiency / live_identity / object_cover | 只 I539 王坤林 | 0 |
| field_only | 10 条 | 0 |

field_only 多出来的 9 条当前都是失败，包括：

| ID | 用户说的 | live 交出来的 | 为什么误抬 |
|---|---|---|---|
| I248 | 红莲保单 | 姓名=红莲 | 用户还要了保单 |
| I213 | 唐诗颖的生存金有没有领取？ | 姓名=唐诗颖 | 用户要的是生存金状态 |
| I154 | 张小岗这个月增加多少保费可以享受居养。 | 姓名=张小岗 + 潜客 | 用户要的是保费/居养 |
| I597 | 车险客户并且客户姓名为邢同文的客户 | 车险 + 姓名=邢同文 | 用户还要了车险 |
| I153 | 陈莹……查被保险人王跃菊 | 陈莹 / 王跃菊 / 父母 | 用户要的是关系网络里的被保险人 |
| I031 | 牛龙，猴 | 姓名=牛龙 | 后半截属相/生肖还在 |
| I079 | 6923账号的保单 | 单号=6923 | 残号当整句成功 |
| I595 I638 | 整句客户号 | 同一值写成 clientNo 和 polNo | 双字段不是本轮充分性 |

王坤林在两口都会被抬。它不是消融的反例。它是 1A 在 Q1+充分性同时打中时的正例。

### 混合包 41 不能给 field_only 开脱

混合包两口都是 41/47。多出来的 6 行只是模式从 inherit 变成 overlay，终态仍是成功：

张忠波/高吉禄/胡秀清/胡蒙刚/叶成群保单号，以及 HB018「找一下客户号…」。

这些题标签本来就是成功，所以分数不动。
9 条误抬几乎都不在 47 条标签里。
4A 要的对照集不是这张混合包分数。

### 协议对齐

`fulfilled.md` §2.1：办成了必须证明用户要的结果拿到了。
交了姓名只证明姓名维可能办成，不证明生存金/保费/车险/保单号也办成。

`material-positioning.md` 不变量 1：`current_behavior` 不能冒充产品事实。
这里对称：当前交了一个姓名，不能冒充整句请求已被满足。

### 不是什么

- 不是要删姓氏目录。目录仍只作 1A 输入
- 不是说这些题的当前失败都判错了
- 不是让判定去补「生存金未领取」
- 不是重开昊轩

### 可证伪

1. 若 9 条里存在「用户要的事就是那个姓名维，而且已经交齐」，则该条应从误抬名单拿掉，不得整包翻案。
2. 若 field_only 在冻结集 A 上相对 sufficiency **没有**误抬「姓名已交、用户还要了别的事」，本 issue 失败。
3. 若有人用混合包 41=41 证明 field_only 可接受，本 issue 的分数条款被违反，不是 field_only 获胜。

### 未消元

- 覆盖门为何仍不是上位：042
- 充分性候选：044
- 并进 judge：045

---
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 15b6719c8967bbf9
- pid: 81087

### Investigation

- Read `issues/open/issue-043.md`, `fulfilled.md` §2.1, charter §1 Done item 4 / §5 ablation clause, and `decide_field_only` L79–104 / `decide_sufficiency` L107–126.
- Independently reran `python3 issues/trace/simulate_1a_sufficiency_program.py`. Same dump SHA `aaa5381cefef843ad52b706dc1a7813db5308c8b707f3ae07b3cefd859f5c980`.
- Own flip counts on set A: sufficiency / object_cover / live_identity `lifted_to_f=1`; field_only `lifted_to_f=10`; `field_only_vs_sufficiency` = 40 overlay diffs, of which **9** have `current=not_fulfilled`.
- Re-applied decide functions on every named row. The 9 current-NF extras, with this peer's Q2 read:

| ID | query | live | field_only | sufficiency | drop? |
|---|---|---|---|---|---|
| I248 | 红莲保单 | searchClientName=红莲 | F, hit 红莲 | None/`value_not_whole_query`; cover residual `保单` | keep — user asked for 保单 |
| I213 | 唐诗颖的生存金有没有领取？ | searchClientName=唐诗颖 | F, hit 唐诗颖 | None/`value_not_whole_query`; residual `的生存金有没有领取？` | keep — user asked 生存金状态 |
| I154 | 张小岗这个月增加多少保费可以享受居养。 | 张小岗 + 潜客 | F, hit **only** 张小岗 (`潜客` not name/id) | None/`not_single_field`; cover `not_grounded` | keep — user asked 保费/居养 |
| I597 | 车险客户并且客户姓名为邢同文的客户 | 车险 + 邢同文 | F, hit **only** 邢同文 | None/`not_single_field`; residual `客户并且客户姓名为的客户` | keep — user also asked 车险客户 |
| I153 | 陈莹……查被保险人王跃菊的信息 | 陈莹 / 王跃菊 / 父母 | F, hit **only** 陈莹 (`familyclientname` ∉ NAME_FIELDS; `父母` not in query) | None/`not_single_field`; cover `not_grounded` | keep — user asked 王跃菊, mouth used 陈莹 |
| I031 | 牛龙，猴 | searchClientName=牛龙 | F, hit 牛龙 | None/`value_not_whole_query`; residual `，猴` | keep — not a bare-name request |
| I079 | 6923账号的保单 | polNo=6923 | F, hit 6923 as id | None/`value_not_whole_query`; residual `账号的保单` | keep — fragment treated as whole request |
| I595 | C18688751950105 | clientNo=… and polNo=… (same value) | F, two id hits | None/`not_single_field`; cover `not_grounded` (second span cannot re-use the only occurrence) | **drop** — query **is** the ID; Q2 is already yes |
| I638 | C00OO731392 | clientNo + polNo, same value | same as I595 | same | **drop** — bare-ID request, already 交齐 |
| I539 | 王坤林 | searchClientName=王坤林 | F | F/`sufficient_name` | not a mis-lift; 1A + sufficiency same cell |

- Mixed pack: field_only and sufficiency both agree 41/47. The 6 mixed diffs (I007 张忠波保单号, I103 高吉禄的保单号, I107 胡秀清保单号, I156 胡蒙刚保单号, I238 叶成群保单号, HB018 找一下客户号…) are inherit→overlay on rows whose **final** label is already fulfilled. 41=41 does not inspect the 7 kept mis-lifts; most of them are outside the 47 labeled rows.

### Reasoning

The ablation holds after the two drops. `field_only` is the intentional confusion of Q1 with Q2: a passing name/id dimension is written as whole-request success. That is exactly the diffusion the user feared, and it is already on frozen set A.

I248 / I213 / I154 — the three needles in the title — are clean. None of them is a bare-name request. I153 is even worse than the issue wrote: the mouth does not use 王跃菊 at all; `NAME_FIELDS={'searchClientName'}`, so it lifts on 陈莹 while the user asked for the insured 王跃菊. I031 leftover `，猴` is content, not decoration. I079 is a tail fragment standing in for「账号的保单」.

I595 / I638 are **not** "姓名已交、用户还要了别的事". The query equals the delivered ID. Sufficiency stays silent only because `len(pairs)!=1`, and covering cannot ground a duplicated span. Those two rows witness the single-field mechanical gate, not the Q1≠Q2 ablation. Per the issue's own falsifier 1 they come off the mis-lift list. The remaining seven still satisfy falsifier 2: field_only **does** lift「姓名/残号已交、用户还要了别的事」on the frozen set.

Do not let mixed-pack 41=41 rehabilitate field_only. The 6 labeled diffs do not change the end state; the 7 kept mis-lifts almost do not enter the 47-row denominator. 4A's contrast set is not that score.

王坤林 is the positive control, not a counter-example. Q1 and the authorized Q2 fire together only when the one delivered value **is** the whole query and the name standard passes.

### Improvement Proposal

- **Target**: Keep `decide_field_only` (`simulate_1a_sufficiency_program.py` L79–104) as the ablation, never as a candidate. Correct the published 9-row list in this issue's Consensus: **drop I595 and I638**; keep I248, I213, I154, I597, I153, I031, I079. Do not patch `draft/judge.py` to "fix" any of these current-NF labels.
- **Change**: Q1 remains 1A (and the ID non-empty+grounded standard). Q2 remains the sufficiency test in L107–126. Any later text that says "field_only also scores 41, so it is acceptable" is a charter violation, not a win.
- **Verification**:

```bash
python3 issues/trace/simulate_1a_sufficiency_program.py
python3 -c "import json; from pathlib import Path; d=json.loads(Path('issues/trace/simulate_1a_sufficiency_program.json').read_text()); rows=d['set_a']['field_only_vs_sufficiency']; nf=[r for r in rows if r['current']=='not_fulfilled']; ids=[r['id'] for r in nf]; assert ids==['I031','I079','I153','I154','I213','I248','I595','I597','I638']; keep={'I031','I079','I153','I154','I213','I248','I597'}; drop={'I595','I638'}; assert keep<=set(ids) and drop<=set(ids); assert d['set_a']['flips']['field_only']['lifted_to_f']==10; assert d['set_a']['flips']['sufficiency']['lifted_to_f']==1; print('043 ablation ok; publish keep', sorted(keep), 'drop', sorted(drop))"
```
## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `15b6719c8967bbf9`

1A 只是字段标准。把它当成整句成功，会在冻结集上误抬「姓名/残号已交、用户还要了别的事」。这就是用户担心的扩散，而且已经发生在内存消融里。

接受 architect 按本 issue 可证伪第 1 条做的点删，不整包翻案：

- **从误抬名单拿掉**：I595、I638。问句就是那个客户号，不是「交了姓名、用户还要别的」。充分性在这两行不说话，只是因为 live 把同一个值写进了两个字段名。这见证的是单字段机械门，不是 Q1≠Q2。
- **保留误抬**：I248 红莲保单、I213 唐诗颖的生存金、I154 张小岗保费/居养、I597 车险+邢同文、I153 陈莹/王跃菊、I031 牛龙，猴、I079 6923账号的保单。
- I539 王坤林不是误抬。它是 Q1 和充分性同时打中的正例。

I153 比 issue 原文更紧：`NAME_FIELDS` 只有 `searchClientName`，field_only 抬的是陈莹，用户要的是被保险人王跃菊。

混合包两口同分，不能给 field_only 开脱。4A 要的对照集不是这张分数。本轮不改这些题的当前失败标签，也不把 field_only 升成候选。

闸：exit 0，`isolation_valid=true`，`scope_valid=true`。同一 dump SHA。不并进 `draft/judge.py`。
