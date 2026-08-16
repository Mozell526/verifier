# Issue #017: 1A-surname 能切开王坤林/共展，但「保单/潜客/家」子串仍误伤

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: Evaluation / Rule overlay（目录+姓氏双闸的残留，不是 1A 政策本身）
**Cases**: I539 王坤林 vs I650 共展；残留 I007/I103/I107/I156/I238、I611 居家潜客、I548 家办客户

## Verifier Discovery

1A 的可执行读法不是「凡 2–4 字」，而是「先目录/盘客/业务词，再姓+名可单独撑 F」。本 issue 验证这条双闸在内存里能不能过，以及过了探针之后还剩什么。

### 触发输入

同一脚本 / 落盘：`issues/trace/simulate_1a_name_program.py`、`simulate_1a_name_program.json`。
复现：`python3 issues/trace/simulate_1a_name_program.py`

集 A 1A-surname：F=209 / NF=132，**8 条翻面**。

姓名探针（政策要的那一侧）：

| ID | query | 当前 | 1A-surname |
|---|---|---|---|
| I224 | 杨杰 | F | F |
| I310 | 郑鑫 | F | F |
| I336 | 匡西永 | F | F |
| I539 | 王坤林 | NF | **F** |
| I650 | 共展 | NF | NF |
| I607 | 豆芽 | NF | NF |
| I358 | 见光 | NF | NF |
| I168 | 傻生 | NF | NF |
| I485 | 昊轩 | NF | NF（二字无姓，章程 §4.3 未拍） |

杨杰与王坤林同侧=F，共展/豆芽仍 NF。这一刀切对了。

目录产品探针（金凤/宝贝卡/孝心/满意/陇佑智盛）仍是 F，没有被压成 NF。
I344 查金风 当前已是 NF，目录投影补了「金风」，本口径未翻面。

同一口 8 条翻面里，除王坤林外全是残留：

| ID | query | live | 当前 | 1A-surname |
|---|---|---|---|---|
| I007 | 张忠波保单号 | `searchClientName=张忠波` | F | **NF** |
| I103 | 高吉禄的保单号 | `searchClientName=高吉禄` | F | **NF** |
| I107 | 胡秀清保单号 | `searchClientName=胡秀清` | F | **NF** |
| I156 | 胡蒙刚保单号 | `searchClientName=胡蒙刚` | F | **NF** |
| I238 | 叶成群保单号 | `searchClientName=叶成群` | F | **NF** |
| I611 | 居家潜客 | `pajjmemberstatus=潜客` | F | **NF** |
| I548 | 家办客户 | 空条件 | NF | **F** |

### 期望

双闸合取：

1. 集 A：假姓名/盘客/目录产品不得回退——本口径在点名探针上做到了。
2. 集 A 里已经办成的「真名 + 单号意图」不得被姓名出口误杀。4A 集 B 也要求真名 / 真名+产品 / 合法单号保持 F。
3. 盘客闸只能打「去盘客 / 圈客」这类对象，不能把已经按会员等级交成的「居家潜客」打掉。
4. 百家姓只用来识别「姓+名」，不能把「家办客户」抬成姓名成功。

fulfilled §2.1：张忠波保单号 live 已经交出姓名，用户要找这个人的单，当前 F 有证据。叠加不得只因为句子里有「保单」两个字就改判没办成。

### 实际

脚本里三处过宽：

1. `BUSINESS_NON_NAME` 含「保单」。`张忠波保单号` 被当成业务非姓名，又看到 `searchClientName`，出口改 NF。五条同构全部误杀。
2. `PANKE = 盘客|圈客|潜客`。「居家潜客」命中「潜客」，整句直接 NF。它 live 走的是居家会员等级，不是盘客动作，当前已是 F。
3. 百家姓含「家」。「家办客户」整句 4 字、首字在姓表，空条件也被抬成 F。

所以：点名探针能过，不代表这条叠加能当判定程序。残留会在集 A 里打死「姓名+保单号」，并误抬业务词。

昊轩仍 NF。二字无姓要不要进 1A，章程 §4.3 留给用户，本 issue 不代选。

### 根因层

双闸的「目录 / 业务否决」用了子串词表，不是角色。

- 「保单」是字段词，出现在「姓名+单号意图」里是合法问法，不是「这不是人名」。
- 「潜客」同时是盘客家族词，也是一条已办成的会员等级值。
- 「家」同时是姓，也是「家办」的头一个字。

011 要的出口是「先目录、再形态」。本叠加把目录做成了过宽词表，形态做成了「首字在百家姓」，两头都会误伤。

### 和 016 / 018 / §4.3 的边界

- 016：1A-wide 连共展都抬回去，直接否决。本口径已经切开支那一刀。
- 本 issue 钉的是：探针过了仍不能上线，除非残留误伤关掉。
- 018：集 B 18/18 仍然只是程序自洽，不能用来宣称残留可接受。
- 昊轩是否必须 F：升级点，角色不选。

### 不是什么

- 不是推翻 1A，也不是要退回「王坤林继续 NF」。
- 不是要在提示里点名这 5 个保单号或「家办客户」。
- 不是现在改 judge / prompt。
- 不是把金凤按姓名放行——金凤当前 F 是产品字段，本叠加没有把它们改成姓名 F。

### 可证伪修复

保留「姓+名撑 F、共展族 NF」，收紧否决词：

1. 「保单」不得单独把已抽出的真名+单号意图打成 NF。
2. 「潜客」不得覆盖已按会员等级交成的「居家潜客」。
3. 「家办客户」不得因首字「家」被抬成 F。

验收（仍只跑模拟，不改 judge）：

```bash
python3 issues/trace/simulate_1a_name_program.py
```

必须同时成立：

- `gates_surname.head_name`：杨杰/郑鑫/匡西永/王坤林 均为 F；共展/豆芽/见光/傻生 均为 NF。
- I007 / I103 / I107 / I156 / I238 保持 F（不得因「保单」翻面）。
- I611 居家潜客保持 F。
- I548 家办客户保持 NF。

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 24595086899233c3
- pid: 84897

### Investigation
Same independent rerun and in-process recompute as 016. Set A 1A-surname: F=209 / NF=132; **8 flips**. Parked 10 untouched (same IDs as 016, all `exit=None`).

Named 1A probes under `exit_surname` (`simulate_1a_name_program.py` L210–241):

| ID | query | current | surname | surname-shape |
|---|---|---|---|---|
| I224 | 杨杰 | F | F | True |
| I310 | 郑鑫 | F | F | True |
| I336 | 匡西永 | F | F | True |
| I539 | 王坤林 | NF | **F** | True (王) |
| I650 | 共展 | NF | NF | False |
| I607 | 豆芽 | NF | NF | False |
| I358 | 见光 | NF | NF | False |
| I168 | 傻生 | NF | NF | False |
| I485 | 昊轩 | NF | NF | False (二字无姓; §4.3 not decided) |

Catalog products 金凤/宝贝卡/孝心/满意/陇佑智盛 stay F (product field, overlay abstains). I344 查金风 stays NF (`searchClientName=金风`; catalog projection adds 金风).

The other 7 of the 8 flips are residuals. XLSX live, not dump folklore:

| ID | query | live | current | surname |
|---|---|---|---|---|
| I007 | 张忠波保单号 | searchClientName=张忠波 | F | **NF** |
| I103 | 高吉禄的保单号 | searchClientName=高吉禄 | F | **NF** |
| I107 | 胡秀清保单号 | searchClientName=胡秀清 | F | **NF** |
| I156 | 胡蒙刚保单号 | searchClientName=胡蒙刚 | F | **NF** |
| I238 | 叶成群保单号 | searchClientName=叶成群 | F | **NF** |
| I611 | 居家潜客 | pajjMemberGradeInfo.pajjmemberstatus=潜客 | F | **NF** |
| I548 | 家办客户 | empty conditions | NF | **F** |

Code paths I traced:

1. `BUSINESS_NON_NAME` contains 保单 (L20–22). `catalog_blocks` is True; because `searchClientName` is present, `exit_surname` L223–229 returns NF. Five isomorphic name+单号意图 cases are killed.
2. `PANKE = 盘客|圈客|潜客` (L19). `is_panke` runs before any field-role check (L214–215). I611 is a member-grade hit, not a 去盘客/圈客 action, and is already F.
3. `SURNAMES` includes 家 (L35 `曲家封芮`). I548 is 4 Han chars, empty live, `has_surname_shape` True → F.

Set B 18/18 under surname is still a program exit (018). The eight set B bare names are all 姓+名, so they cannot bless these residuals.

### Reasoning
The 王坤林 F ∧ 共展 NF cut is real. That is the part of 1A this overlay got right, and I am not asking to put 王坤林 back to NF.

Passing the named probes is not the same as a shippable 1A program. Charter dual-gate forbids set A defect-family regression; it does not license new false negatives on already-evidenced F cases. `fulfilled.md` §2.1: I007 live already delivered `searchClientName=张忠波` for a name+保单号 ask. Current judge F has evidence. Flipping it to NF because the characters 保单 appear is an overlay bug, not 1A.

Same for I611: 盘客闸 is supposed to hold 去盘客/圈客 at NF. I611’s live field is `pajjmemberstatus`, current F. Substring 潜客 is the wrong object. I548 is a business-segment phrase with empty conditions; first-character 家 is a 百家姓 collision, not name evidence.

Root cause (tighten, do not replace): the overlay’s “directory / business veto” is a substring lexicon, and its “name” door is “first char in 百家姓”. 011 asked for directory-then-morphology. This script implemented both sides as over-wide tokens. I will not invent a third shippable overlay here, and I will not decide 昊轩 (§4.3).

### Improvement Proposal
**Problem**: 1A-surname splits 王坤林/共展 correctly, but its 保单/潜客/家 token tables still flip seven other set A rows the wrong way.

**Proposed Change**: Keep the 姓+名 vs fake-name split. Do not ship this overlay until the three residual classes stop flipping. Do not add ID-named exceptions to prompt/judge. Do not write a new overlay in this round.

**Design** (acceptance constraints, not a new program):
- `gates_surname.head_name`: 杨杰/郑鑫/匡西永/王坤林 = F; 共展/豆芽/见光/傻生 = NF; 昊轩 left as NF until §4.3.
- I007 / I103 / I107 / I156 / I238 stay F (保单 must not veto an already-extracted true name + 单号意图).
- I611 stays F (潜客 must not cover 居家会员等级).
- I548 stays NF (家 must not promote 家办客户).
- Catalog products stay on their product fields; do not reclassify 金凤 as a name F.

**Implementation Steps**:
1. Consensus: 1A-surname probe cut is valid; overlay is not shippable while the 7 residuals remain.
2. Any later overlay (different peer / later charter) must re-run the same script and meet the bullets above.
3. Do not touch `draft/judge.py`, xlsx, set B, or parked rows.

**Risks**: “Fixing” 保单 by deleting it from the veto list without a role check could re-open true business-non-name false name maps. The constraint is role-sensitive: 保单 + already-extracted person name stays F; 保单 as the only object is not a name success. Do not encode that as a third overlay here.

**Verification**:
```bash
python3 issues/trace/simulate_1a_name_program.py
python3 -c "
import json
d=json.load(open('issues/trace/simulate_1a_name_program.json'))
print('head', d['set_a']['gates_surname']['head_name'])
print('fake', d['set_a']['gates_surname']['fake_name'])
print('flips', d['set_a']['flips_surname'])
"
```

Current rerun fails that check: the 7 residuals are still in `flips_surname`.

**Why I Cannot Apply It**: Read-only; user forbade inventing a shippable third overlay or editing judge/xlsx/set B/script.

## Consensus
**Verdict**: real-problem

双方独立重跑一致：1A-surname 集 A F=209 / NF=132，8 条翻面。杨杰 / 郑鑫 / 匡西永 / 王坤林 = F，共展 / 豆芽 / 见光 / 傻生 = NF。这一刀切对了，不把王坤林退回 NF。

接受 architect 的收口：点名探针过了 ≠ 可以上线。残留 7 条必须先关掉——

- 张忠波 / 高吉禄 / 胡秀清 / 胡蒙刚 / 叶成群 +「保单号」：当前已按真名交成，被「保单」子串误杀；
- 居家潜客：当前已按会员等级交成，被「潜客」误杀；
- 家办客户：空条件，被百家姓「家」误抬。

不得只靠删词表交差。昊轩仍 NF，是否必须 F 归章程 §4.3，本轮不代选。判定代码仍未改。
