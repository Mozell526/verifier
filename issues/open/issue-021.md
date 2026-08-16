# Issue #021: 四口径对照——wide 回退缺陷族，surname 误杀保单号，role 混合包 41/47 且 6 个 miss 全是 live 丢姓名；仍不得发版

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: Evaluation / Rule overlay（内存实验，不是某一条 LLM 句子）
**Cases**: 混合包 48 条（47 条有期望；昊轩 unlabeled）。集 A 341 只作缺陷族闸，不当 KPI。

## Verifier Discovery

用户要的是：正常 case 和 bad case 都跑当前 judge，再在内存里调试，看哪种处理能平衡「长尾过严」和「误伤」。本轮混合包 48/48 都有冻结 live + 新鲜 draft judge。叠加脚本不 import `draft/judge.py`。

### 触发输入

脚本：`issues/trace/simulate_1a_mixed_program.py`
落盘：`issues/trace/simulate_1a_mixed_program.json`
痕迹：`issues/trace/name_scenario_runs/*.json`
复现：`python3 issues/trace/simulate_1a_mixed_program.py`

本轮落盘 SHA-256：`fc2e77f8e59d6a38211c3a463386f6718699eef03914359c0904ccf6d2308b6b`
`current_sources`：**48/48 `fresh_judge`**。不再用 xlsx 顶混合包。

### 四列分数（47 条有期望；昊轩不进分母）

| 口径 | tested | agree | miss | 集 A F/NF | 缺陷族闸 |
|---|---:|---:|---:|---|---|
| 当前 draft judge | 47 | 36 | 11 | 213 / 128 | 假姓名仍 NF；真名自己抖（见 020） |
| 1A-wide（凡 2–4 字都 F） | 47 | 27 | 20 | 238 / 103 | **假姓名 4/4 抬 F** |
| 1A-surname（先目录/业务词，再姓+名） | 47 | 35 | 12 | 210 / 131 | 假姓名仍 NF；**5 条姓名+保单号误杀** |
| **1A-role（角色闸，不点名 ID）** | **47** | **41** | **6** | 215 / 126 | 假姓名仍 NF；保单号不误杀 |

当前 11 个 miss：匡西永 + 张伟/王芳/周婷婷/吴志强 + 姓名+产品六条。
wide 20 个 miss：六条姓名+产品仍 NF，外加共展/豆芽/见光/傻生、十里堡/细岗、贷款/口令/团体险/生存金/分红/外国人、查金风、家办客户 全部被抬 F。
surname 12 个 miss：张忠波/高吉禄/胡秀清/胡蒙刚/叶成群「保单号」五条被压成 NF，家办客户被抬 F，外加六条姓名+产品。
role 6 个 miss：**全部是 HB009–HB014 姓名+产品**。叠加器看见 live 没交 `searchClientName`，主动 abstain，保持当前 NF。

### 按角色（role 口径）

| 角色 | n | role agree | current agree | wide agree | surname agree |
|---|---:|---:|---:|---:|---:|
| 真名裸词 | 12 | 12 | 7 | 12 | 12 |
| 假姓名 | 4 | 4 | 4 | **0** | 4 |
| 地名当姓名 | 2 | 2 | 2 | **0** | 2 |
| 业务词当姓名 | 6 | 6 | 6 | **0** | 6 |
| 盘客族 | 4 | 4 | 4 | 4 | 4 |
| 查金风 | 1 | 1 | 1 | **0** | 1 |
| 家办客户 | 1 | 1 | 1 | **0** | **0** |
| 姓名+保单号 | 5 | 5 | 5 | 5 | **0** |
| 姓名+产品 | 6 | 0 | 0 | 0 | 0 |
| 合法单号 | 4 | 4 | 4 | 4 | 4 |
| 居家潜客 / 金凤 | 2 | 2 | 2 | 2 | 2 |

### 集 A 翻面（341，xlsx current，不当准确率）

- wide：25 条 NF→F。里面有王坤林（要的），也有共展/豆芽/见光/傻生、十里堡、贷款、家办客户、查金风、昊轩。016 仍成立。
- surname：7 条。王坤林 NF→F（要的）；五条「X保单号」F→NF；家办客户 NF→F（「家」在姓氏表）。017 的残留还在。
- role：2 条。王坤林 NF→F（要的）；**I248 红莲保单** NF→F。`红莲` 不在目录产品投影里，但「红」在姓氏表，`PERSON_THEN_POLICY` 把它当成「人名+保单」。这是 role 在集 A 上的残留，不是混合包分数。

盘客 20 条三口都保持 NF。金凤/宝贝卡/孝心等目录产品三口都保持 F，没有被压成姓名失败。

### 期望

章程双闸是合取：

1. 集 A 缺陷族不得回退：盘客、假姓名、目录产品误走姓名。
2. 集 B / 混合包头部 F 不得掉：真名、真名+产品、合法单号。

不是 oracle：341 准确率、canvas、叠加器自己的 41/47。
姓名+产品的 6 个 miss 不能靠改判定补——019 已经钉了 live 丢姓名。叠加器若因为句子里有「重疾」就报 F，是在用问句补 live。

### 实际

1. **wide 不可用**。要真名的同时把共展/豆芽/地名/业务词一并抬 F。集 A 第一扇闸关不上。016 不重开，本轮新鲜判定只是把同一结论铺到混合包上。
2. **surname 探针能切开王坤林/共展，但不能用**。它会回退当前已经判对的五条「姓名+保单号」，还会把空条件的「家办客户」抬成 F。
3. **role 是目前唯一不回退缺陷族、还能抬真名、且不误杀保单号的内存口径。** 混合包 41/47，剩下 6 条它主动放手。集 A 只多翻了王坤林和红莲保单。
4. **role 仍不得并进 `judge.py` / prompt。** 本轮章程写明只比较、不发版。I248 红莲保单说明「姓氏表 + X保单」还会误抬目录外的疑似产品词。41/47 不是发版门槛。

### 昊轩（必须写明，不得当结论）

I485 昊轩：xlsx = NF；本轮新鲜 draft judge = **F**；三口叠加对 `undecided_given_name` 都是 abstain，所以混合包四列都继承新鲜 F，集 A 四列都继承 xlsx NF。
章程 §4.3 未拍。角色不得把「这回 LLM 判了 F」读成 1A 已覆盖二字无姓。021 的分母不含昊轩。

### 根因层

长尾 bad case 和真实分布的平衡，不能靠「凡 2–4 字都成功」，也不能靠当前这把会抖的尺。要的是按场景角色分流：真名形态可单独撑 F，假姓名/地名/业务词/盘客留下，姓名+保单号不要因为句子里有「保单」就被姓氏探针误杀，姓名+产品必须先看见 live 交没交姓名。

这不是调 341 阈值能解决的。wide / surname / 当前 LLM 抽签，都会在其中一扇闸上翻车。

### 和 016 / 017 / 018 / 019 / 020 的边界

- 016 / 017：当时还没有混合包新鲜 judge。本 issue 用 48 条新鲜判定重算，结论方向不变，不重开那两份 Consensus。
- 018：当时集 B 18/18 是程序自洽。现在裸名和单号有 live+judge；姓名+产品 live 没过，见 019。
- 019：六条 miss 的根因在 parser，不在叠加松紧。
- 020：当前 judge 同形态裸名左右互搏。021 把它当成「current」这一列，不把 36/47 当成可用口径。

### 不是什么

- 不是要改 `draft/judge.py`、prompt、xlsx、canvas、`head_set_b.json`。
- 不是要把 1A-role 发版。
- 不是 341 准确率竞赛。
- 不是代用户拍昊轩 / 去年 / 称谓。

### 可证伪修复（比较口径，不是发版）

在不改生产判定的前提下，内存 role 口径必须同时满足：

1. 混合包真名 12/12 F，假姓名 4/4 NF，姓名+保单号 5/5 F，盘客/地名/业务词不抬 F；
2. 集 A 假姓名 4/4 仍 NF，盘客仍 NF，目录产品仍 F；
3. 姓名+产品六条不得因为问句里有产品词就被报 F。

当前落盘已经满足 1–3。I248 红莲保单仍是 role 的集 A 残留。把 role 写进 judge 之前，这条必须先有独立否决，不能靠「41/47 看起来不错」。

```bash
python3 issues/trace/simulate_1a_mixed_program.py
python3 -c "import json;d=json.load(open('issues/trace/simulate_1a_mixed_program.json'));print(d['mixed']['score_role']);print(d['set_a']['role']);print(d['set_a']['gates_role']['fake_name'])"
```

## Architect Response

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: f3e708f76cfa44c3
- pid: 66079

### Investigation
Independently ran `python3 issues/trace/simulate_1a_mixed_program.py`. Did not copy verifier numbers. Re-read `exit_wide` (L215–225), `exit_surname` (L228–247), `exit_role` (L250–279), `apply_exit`, `is_parked`, and `load_set_a` (set A rows have **no** mixed-pack `role` label). Imported the module and printed raw exits vs applied status for all 48 mixed rows, plus set A flips and parked unit queries.

My mixed-pack applied scores (47 labeled; I485 excluded from the denominator):

| 口径 | tested | agree | miss | misses |
|---|---:|---:|---:|---|
| current | 47 | 36 | 11 | I336 + HB002/003/005/006 + HB009–HB014 |
| wide | 47 | 27 | 20 | HB009–HB014 + 共展/豆芽/见光/傻生 + 十里堡/细岗 + 贷款/口令/团体险/生存金/分红/外国人 + 查金风 + 家办客户 |
| surname | 47 | 35 | 12 | I007/I103/I107/I156/I238 + HB009–HB014 + I548 |
| role | 47 | 41 | 6 | HB009–HB014 only |

Set A applied counts: current 213/128, wide 238/103, surname 210/131, role 215/126. Matches the issue. Dump SHA after my rerun is `14b1ecec80eaed2247b392a23d24651476adfc26f9943c574c6a3dcd3f86f66d` (issue cited `fc2e77f8…`); scores and live_facts are the same. I treat the dump as a claim I recomputed, not as an authority.

`current_sources` is 48/48 `fresh_judge`. No xlsx fallback on the mixed pack.

Parked / 昊轩:

- Mixed pack contains **zero** 去年 / 格式外 / 称谓 rows. `is_parked` never fires on the 48. Unit queries `去年投保` / `弟弟` / `老板娘` / `大写P07` / `C00OO123` / `配` all return raw `None` on all three exits.
- I485 昊轩 is `role=undecided_given_name`. Mixed-pack raw exits are all `None` → inherit **fresh `not_fulfilled`**. Frozen trace `issues/trace/name_scenario_runs/I485.json` `judge_status` is `not_fulfilled`; xlsx `状态` is also `not_fulfilled`. There is **no** fresh-F vs xlsx-NF contradiction in this frozen pack. Issue 021’s sentence “本轮新鲜 draft judge = F … 混合包四列都继承新鲜 F” is factually wrong.
- Set A load has no `undecided_given_name` label. On set A, `exit_wide(I485)` is raw **F** (one of wide’s 25 NF→F flips). `exit_surname(I485)` is raw NF (no surname shape). `exit_role(I485)` is raw `None` → inherit xlsx NF. I do **not** read any of this as a §4.3 decision.

Name+product overlays: all three raw `None` on HB009–HB014. They do not invent `searchClientName` from “重疾/年金/两全/医疗/增额寿”. Role also has **no positive F branch** for this family; even if live later added the name, role would still return `None` and inherit current. That is the correct “don’t fake a name” behavior. It also means 41/47 will not become 47/47 by fixing overlay tightness.

Role is not a standalone judge. Applied 41/47 is overlay + inherit:

- Fake names / toponyms / most business words / 盘客: role raw `None`, inherit current NF. Wide actively lifts them. Surname actively NFs fake names (good) but also NFs 姓名+保单号 (bad) and lifts 家办客户 (「家」 in the surname table).
- 姓名+保单号: role actively F on I007/I107/I156/I238. **I103 `高吉禄的保单号` raw role is `None`**: `PERSON_THEN_POLICY` greedy `{2,4}` eats `高吉禄的`, that token is not in `values`, so the F path misses; agree is inherit current F.
- I248 红莲保单 (set A only): role raw **F**. `红莲保单` matches `PERSON_THEN_POLICY`, `红` is in `SURNAMES`, live has `searchClientName=红莲`. This is a real residual, not a mixed-pack score.

Set A role flips = 2: I539 王坤林 NF→F (wanted by 1A) and I248 红莲保单 NF→F (not wanted). Disk-客 stay NF. 金凤/宝贝卡/孝心/满意/陇佑智盛 stay F via inherit (`live_catalog_only` → `None`).

### Reasoning
The four comparison claims hold, with the tightenings above.

1. **wide fails the fake-name gate.** Mixed pack 4/4 fake names raw F. Set A wide also lifts 共展/豆芽/见光/傻生 plus 昊轩/家办客户/查金风/十里堡/贷款…. First dual-gate door does not close. Same direction as 016; I do not reopen 016.
2. **surname false-kills name+policy.** All five `X保单号` raw NF because `BUSINESS_NON_NAME` matches `保单` before the surname-shape F path. Also lifts I548 家办客户. Same direction as 017; I do not reopen 017.
3. **role applied 41/47, and the 6 misses are exactly HB009–HB014.** Those six are 019 live drops. Role abstains; it does not promote them from the query text. Treating 41/47 as a ship KPI would be wrong — charter already says so, and the inherit structure makes it worse: defect-family “passes” are mostly current-judge NF that role never touched.
4. **role must not be merged into `judge.py` / prompt.** Charter §3: this round compares, does not ship. If role replaced the LLM, raw `None` would no longer inherit NF, so 共展/豆芽 would stop being actively held down. I248 and the I103 greedy `的` capture are further blockers. I will not invent a fourth overlay.

Current 36/47 is not a usable column (020). 341 accuracy / canvas / the overlay’s own 41/47 are not oracle. Dual-gate is a conjunction: wide fails door 1; surname fails door 2 (and also lifts 家办客户); current fails door 2 on head names; role as an *overlay* is the only column that lifts the 12 true names without lifting fake names or killing 保单号, and it still must not ship.

I485: data only. Frozen fresh = NF, xlsx = NF, mixed overlays abstain. I do not decide whether 二字无姓 must be F.

### Improvement Proposal
- **Target**: Keep `issues/trace/simulate_1a_mixed_program.py` as a comparison harness. Do **not** copy `exit_role` into `impl/projects/client_search/draft/judge.py`. Do not add a fourth overlay. Do not edit xlsx / canvas / set B / 昊轩 labels.
- **Change** (comparison hygiene, not a ship):
  1. Continue scoring role only as `apply_exit` overlay. Publish raw-exit vs inherit as two columns before anyone talks about merge.
  2. Name+product stays raw `None` until 019 live actually emits `searchClientName`. No query-text backfill.
  3. Before any later write-enabled peer even *considers* a role merge: add an independent veto so `X保单` / `X保单号` is F only when the person token equals live `searchClientName` **and** the remainder is a policy-id query, not a product-ish token (blocks I248 红莲保单); make the person group non-greedy around optional `的` (fixes I103); do not treat inherit-NF as a fake-name gate — fake names need an explicit no-surname-shape NF if role ever becomes the judge.
  4. Leave I485 unlabeled / abstain. §4.3 stays with the user.
- **Verification**:

```bash
python3 issues/trace/simulate_1a_mixed_program.py
python3 -c "import json;d=json.load(open('issues/trace/simulate_1a_mixed_program.json'));print(d['mixed']['score_role']['agree'], d['mixed']['score_role']['disagree']);print([m['id'] for m in d['mixed']['score_role']['misses']]);print(d['set_a']['role']);print(d['set_a']['gates_role']['fake_name'])"
```

Expect role agree=41, misses=HB009–HB014, fake-name applied NF, and no edit to `draft/judge.py`.

## Consensus
**Verdict**: real-problem

双方独立重跑 `python3 issues/trace/simulate_1a_mixed_program.py`。当前落盘 SHA-256：`14b1ecec80eaed2247b392a23d24651476adfc26f9943c574c6a3dcd3f86f66d`（architect 重跑后覆盖；分数与旧 SHA `fc2e77f8…` 一致）。47 条有期望：current 36、wide 27、surname 35、role 41。集 A：current 213/128，wide 238/103，surname 210/131，role 215/126。

接受 architect 的三处收紧，并更正本 issue 原文：

1. **昊轩不是新鲜 F。** 冻结 `I485.json` 的 `judge_status=not_fulfilled`，与 xlsx 同侧。混合包三口对 `undecided_given_name` 都 abstain。集 A 上 wide 会把昊轩抬 F，surname 保持 NF，role 继承 xlsx NF。这不是 §4.3 已拍。
2. **role 的 41/47 是叠加+继承，不是独立判定。** 假姓名/地名/多数业务词/盘客的「过」多半是 raw=`None` 继承当前 NF。I103 `高吉禄的保单号` 因 `{2,4}` 贪心吃掉「高吉禄的」而 miss 主动 F 路，靠继承才对。I248 红莲保单是集 A 残留：role raw=F。
3. **wide 不可用，surname 不可用，role 不得并进 `judge.py`。** 姓名+产品六条 miss 归 019，不能靠改判定补。不发明第四口。

本 issue 在 role 被并进判定、或假姓名闸变成只靠继承 NF 时保持 open。
