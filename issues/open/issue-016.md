# Issue #016: 1A-wide 把共展/豆芽抬回 F，集 A 姓名缺陷族回退

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: Evaluation / Rule overlay（内存叠加，不是某一条 LLM 句子）
**Cases**: I650 共展、I607 豆芽、I358 见光、I168 傻生；对照 I539 王坤林、I224 杨杰

## Verifier Discovery

用户已拍 1A：2–4 字中文名可单独撑 F，但共展/豆芽仍须 NF。本 issue 验证的是「凡 2–4 个汉字就算姓名成功」这条宽口径，在内存叠加里行不行。

### 触发输入

脚本（不 import judge）：`issues/trace/simulate_1a_name_program.py`
落盘：`issues/trace/simulate_1a_name_program.json`
复现：`python3 issues/trace/simulate_1a_name_program.py`

集 A 当前新 judge：F=213 / NF=128。
1A-wide：F=220 / NF=121，**19 条翻面**。

假姓名探针（当前都是 NF，方向对）：

| ID | query | live 字段 | 当前 | 1A-wide |
|---|---|---|---|---|
| I650 | 共展 | `searchClientName=共展` | NF | **F** |
| I607 | 豆芽 | `searchClientName=豆芽` | NF | **F** |
| I358 | 见光 | `searchClientName=见光` | NF | **F** |
| I168 | 傻生 | `searchClientName=傻生` | NF | **F** |

同一口径把王坤林、杨杰都打成 F，看起来满足「同侧」，但这是用「所有 2–4 字」换来的，不是用「真名」换来的。

另外被抬成 F 的还有：I005 十里堡、I294 细岗、I485 昊轩、I548 家办客户、I112 老客户、I208 续收、I246 客户、I584 财富分群。

### 期望

章程 §2 双闸是合取：

1. 集 A 缺陷族不得回退：盘客/圈客、假姓名（共展/豆芽）、目录产品误走姓名。
2. 集 B 头部 F 不得掉。
3. 政策原文：杨杰与王坤林同侧=F；**共展/豆芽仍 NF**。

011 Consensus 已钉：I650 / I607 的 NF 必须保住，不得因为「也是 2–4 字」放行。
fulfilled §2.1：F 要证据证明用户要的结果拿到了。共展/豆芽没有「这是客户本人姓名」的证据。
material-positioning 不变量 1：不能把「字数碰巧是 2–4」当成正式规则。

### 实际

1A-wide 的出口是：非 parked、非盘客、整句 2–4 个汉字 → F。

所以共展/豆芽/见光/傻生与杨杰走同一条门。集 A 姓名缺陷族在这一口上整族回退。双闸第一扇已经关不上。

集 B 在这一口上 18/18 F，救不了集 A 的回退；而且那 18/18 本身不是 LLM 评测（见 018）。

### 根因层

把 1A 读成了「字数闸」，丢掉了 1A 后半句「假姓名仍 NF」。
2–4 字只是形态桶，不是姓名证据。桶里同时装着真名、假名、地名、业务词。宽口径没有第二道「目录 / 姓 + 名」门，所以无法在王坤林和共展之间切开。

### 和 011 / 017 / 018 的边界

- 011：已经证明杨杰 F、王坤林 NF 是同形态互搏。本 issue 不重开那条。
- 本 issue 只钉：用「凡 2–4 字 → F」去修 011，会把 011 要求保住的共展族吐回 F。
- 017：换「姓+名 + 目录」之后，共展族能保住，但还有别的误伤。
- 018：集 B 的 18/18 不能拿来给 1A-wide 开绿灯。

### 不是什么

- 不是否认 1A。1A 要的是真名可单独撑 F，不是任何二字词都撑 F。
- 不是要在提示里写「共展不算人名」。那是 011 已禁的局部样本补丁。
- 不是现在改 `draft/judge.py`。

### 可证伪修复

不采用 1A-wide 作为上线口径。验收：

```bash
python3 issues/trace/simulate_1a_name_program.py
```

落盘里 `gates_wide.fake_name` 必须仍是 4 条 NF。只要共展/豆芽/见光/傻生任何一条变 F，本 issue 未关。

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 24595086899233c3
- pid: 84897

### Investigation
Independently re-ran `python3 issues/trace/simulate_1a_name_program.py` (did not copy verifier numbers). Dump SHA-256 stayed `d6bc3473bbf62d26cb3d393f1de4a9c0a23b7846af1d5aba858b1450d2fde9b3` before and after; then imported `issues/trace/simulate_1a_name_program.py` and recomputed overlays myself against the xlsx and `head_set_b.json`.

Recomputed set A (N=341): current F=213 / NF=128; 1A-wide F=220 / NF=121; **19 flips**. Parked 10 rows all `exit=None` and unchanged: I034 / I046 / I153 / I161 / I245 / I263 / I288 / I383 / I616 / I638.

XLSX live for the fake-name probes (all current NF, `searchClientName` = query):

| ID | query | live field | current | wide |
|---|---|---|---|---|
| I650 | 共展 | searchClientName=共展 | NF | **F** |
| I607 | 豆芽 | searchClientName=豆芽 | NF | **F** |
| I358 | 见光 | searchClientName=见光 | NF | **F** |
| I168 | 傻生 | searchClientName=傻生 | NF | **F** |

`has_surname_shape` is False for 共/豆/见/傻. `exit_wide` (`simulate_1a_name_program.py` L189–208) still returns `fulfilled` on `BARE_NAME` after parked/panke. That is the 1A-wide door.

Same wide pass also lifts I005 十里堡、I294 细岗、I485 昊轩、I548 家办客户、I112 老客户、I208 续收、I246 客户、I584 财富分群. I539 王坤林 goes NF→F, but so do the fake names.

Tightening, not a refute: 19 flips are not all “2–4 字抬成 F”. Six go the other way — I007/I103/I107/I156/I238 保单号 F→NF via `BUSINESS_NON_NAME`「保单」(L20–22, L184–186, L204–205), and I611 居家潜客 F→NF via `PANKE`「潜客」(L19, L193–194). Discovery already listed those kills. They do not save the fake-name gate.

Set B 18/18 F under wide is a program exit (`source=="set_b"` at L195–201). It cannot offset the set A defect-family miss. Parked rows were not touched.

### Reasoning
Charter §2 is a conjunction: 杨杰/王坤林 same side = F, **and** 共展/豆芽 stay NF; set A 盘客/假姓名/目录产品 must not regress. 011 already nailed I650/I607 NF. `fulfilled.md` §2.1 requires evidence the user got a person-name result; mapping 共展/豆芽 onto `searchClientName` is not that evidence. `material-positioning.md` invariant 1 forbids promoting “length happens to be 2–4” into a normative rule.

1A-wide operationalizes 1A as a length bucket. That bucket holds true names, fake names, toponyms, and business words. Wide has no second door that can keep 王坤林 F while keeping 共展 NF. Therefore the first dual-gate fails. This is not a reasonable reading of 1A; it drops the second half of the policy.

I do not reopen 011. I do not treat 昊轩 (also lifted here) as a 1A requirement — charter §4.3 is still unowned. I do not propose a third overlay.

### Improvement Proposal
**Problem**: Reading 1A as “any 2–4 Han chars → F” puts 共展/豆芽/见光/傻生 back to F and fails the set A fake-name gate.

**Proposed Change**: Reject 1A-wide as a shippable overlay. Do not patch `draft/judge.py`. Do not write “共展不算人名” into a prompt.

**Design**: Keep using `exit_wide` only as a negative control. Closing criterion is the existing dump field, not a new rule:

- `set_a.gates_wide.fake_name` must remain four NF rows (I650/I607/I358/I168).
- Any one of those four becoming F means 1A-wide is still live and this issue stays open.

**Implementation Steps**:
1. Consensus / report: write “1A-wide fails set A fake-name gate; not adopted.”
2. Do not merge `exit_wide` into judge or prompt.
3. Leave parked 10 abstaining.

**Risks**: Treating 王坤林’s wide F as proof that wide “implements 1A”. It does not — the same door lifts the fake-name family.

**Verification**:
```bash
python3 issues/trace/simulate_1a_name_program.py
python3 -c "import json; d=json.load(open('issues/trace/simulate_1a_name_program.json')); print(d['set_a']['gates_wide']['fake_name'])"
```

**Why I Cannot Apply It**: Read-only argue peer; this is a reject-the-overlay decision, not a source edit.

## Consensus
**Verdict**: real-problem

双方独立重跑同一脚本，数字一致：集 A 当前 F=213 / NF=128；1A-wide F=220 / NF=121，19 条翻面。共展 / 豆芽 / 见光 / 傻生 全部 NF→F。parked 10 条未动。

接受 architect 的收口：19 条里还有 5 条「姓名+保单号」和「居家潜客」被压成 NF，这不能反过来救假姓名闸。王坤林被抬成 F，是和共展走同一扇「2–4 字」门，不是 1A 要的那一刀。

1A-wide 不采用。不得并进判定，不得在提示里写「共展不算人名」。本 issue 在 `gates_wide.fake_name` 仍出现任何一条 F 时保持 open。
