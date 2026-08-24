# Issue #044: 较好的处理是充分性，不是再盖一层；冻结分数撞车必须这么读

**Class**: evaluation
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: 内存对照（不是生产代码）
**Cases**: 混合包 48；集 A 341；15 条合成探针。合成针不准进 47 分母。

## Verifier Discovery

用户要在内存里调试 judge，看哪种处理较好。
「较好」按章程不是混合包分数最高，而是：

1. 1A 真名整句能抬（王坤林与杨杰同侧）
2. 假姓名 / 盘客 / 目录产品不回退
3. 不把姓名维扩成整句成功（043）
4. 离开姓名场时不必加虚词表
5. 每个输入都有去处（主动改成功 / 不改判）

原则正文：`issues/trace/name-sufficiency.md`。

### 候选嘴

```text
充分性
  恰好一个字段
  值等于整句
  该字段通过 Q1（姓名=1A，单号=本值）
  → 主动改成功
  其余 → 不改判
  从不过失败
```

这不是新覆盖门。它明确承认自己只是充分性测试，不是「办成了没有」的一般定义。
李明重疾险、查一下李明、45岁女性保费10万以上，一律不改判。
不是漏了，是没授权。

### 冻结数字

`python3 issues/trace/simulate_1a_sufficiency_program.py`
dump SHA-256 `aaa5381cefef843ad52b706dc1a7813db5308c8b707f3ae07b3cefd859f5c980`
合成针 15/15 通过。

| 口径 | 混合包对上 | 集 A 翻到成功 | 集 A overlay |
|---|---|---|---|
| current | 36 | — | — |
| wide | 27 | 25 | 误抬共展/豆芽/昊轩 |
| surname | 35 | 2，并误杀 5 | 题型气太重 |
| role | 41 | 王坤林+红莲保单 | 已否 |
| live_identity | 41 | 只王坤林 | 57 |
| object_cover | 41 | 只王坤林 | 57，与 identity 逐行相同 |
| sufficiency | 41 | 只王坤林 | 57，与 identity 逐行相同 |
| field_only | 41 | 10 | 97，误抬见 043 |
| strip_identity | 41 | 只王坤林 | 剥「的/一下」没换来新的合法抬 |
| strip_any | 41 | 3 | 额外抬 I129 综拓潜客、I246「客户」 |

sufficiency 与 live_identity / object_cover 在冻结集上逐行标签相同。
必须老实写：本轮赢的是标准和边界，不是新分数。

相同分数的读法：

- live_identity：值=整句是覆盖门的死门槛
- object_cover：残句为空是上位，值=整句是它的特例
- sufficiency：值=整句+字段标准是充分性测试；残句为空不是上位

后文若再把对象覆盖扶回去，042 未修。

### 合成针上才看得见拒绝覆盖

| 针 | sufficiency | object_cover | field_only | strip_any |
|---|---|---|---|---|
| 杨杰 / 王坤林 | 改成功 | 改成功 | 改成功 | 改成功 |
| 共展 / 昊轩 | 不改判 | 不改判 | 不改判 | 不改判 |
| 红莲保单 | 不改判 | 不改判 | 改成功 | 不改判 |
| 唐诗颖的生存金 | 不改判 | 不改判 | 改成功 | 不改判 |
| 李明重疾险（交齐） | 不改判 | 改成功 | 改成功 | 改成功 |
| 李明的重疾险（剩「的」） | 不改判 | 不改判 | 改成功 | 改成功 |
| 45岁女性保费10万以上 | 不改判 | 不改判 | 不改判 | 不改判（还要再加「岁/以上」） |
| 有生存金未领取（值=是） | 不改判 | 不改判 | 不改判 | 不改判 |

object_cover 比充分性多出来的手，只在「多个身份对象把问句盖住、残句恰好为空」。
冻结生产痕迹里几乎没有这种题。为这只手把残句当成定义，就会在「的 / 岁 / 以上」上加表。

strip_any 证明：把覆盖门推广到任意字段，会在冻结集上抬「综拓潜客」和「客户」。
这就是用户说的扩散失败，而且已经发生在内存对照里。

### 双闸

sufficiency 相对当前：

- 集 A 假姓名 / 盘客 / 目录产品：不回退
- 只主动抬王坤林
- 集 B 真名整句：杨杰/郑鑫/匡西永保持成功；王坤林改成功
- 真名+产品六条 live 没交姓名：不改判，保持失败（解析问题，不是判定胜利）

wide / surname / field_only / strip_any 过不了这扇闸。

### 不是什么

- 不是把 41/47 当胜利
- 不是把 sufficiency 改名为 object_cover
- 不是授权剥虚词去抬李明的重疾险
- 不是并进 `draft/judge.py`

### 可证伪

1. 独立重跑新脚本，dump SHA 变了且差异不是键序 → 数字作废。
2. sufficiency 与 live_identity 在冻结集上出现行级终态差 → 本 issue 的「分数撞车」句失败，必须先解释差。
3. 若存在不加虚词表、不加字段类、又能合法抬「李明重疾险 / 生存金 / 保费」的第三张嘴，且不是预置类型表，则充分性不是唯一候选，本 issue 要改。
4. 只报混合包 41、不分 overlay/inherit → 章程未达。

### 未消元

- 源头仍是提示姓名闸：045
- 昊轩 / 去年 / 称谓仍停住：045

---
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 15b6719c8967bbf9
- pid: 81087

### Investigation

- Read `issues/open/issue-044.md`, `issues/trace/name-sufficiency.md` §3–§8, charter §1 / §2 dual-gate, and Consensus-only `issue-026.md` (live_identity as floor, 41/47 is a pack artifact).
- Independently reran the new script. SHA `aaa5381cefef843ad52b706dc1a7813db5308c8b707f3ae07b3cefd859f5c980`. Mixed agree: current 36, wide 27, surname 35, role / live_identity / object_cover / field_only / sufficiency / strip_identity / strip_any all 41. Set A overlay/inherit: sufficiency = live_identity = object_cover = `15/33` mixed and `57/284` on set A. field_only `21/27` mixed, `97/244` set A. strip_any `16/32` mixed, `91/250` set A.
- Function comparison, not score comparison:
  - `exit_live_identity` (`simulate_1a_coverage_program.py` L293–314) = `whole_query_cover` + ID field or `searchClientName` + 1A.
  - `decide_sufficiency` (L107–126) = single pair + `value==query` + `field_standard` on `NAME_FIELDS={searchClientName}` / `ID_FIELDS={clientNo,polNo}`.
  - On every non-empty frozen row and every synthetic, the two mouths return the same status. The collision with **live_identity** is function identity, not luck.
  - The collision with **object_cover** is luck. Same 41 and same set-A flips, but `SYN-concat`「李明重疾险」is cover `fulfilled/overlay_f_mixed` vs sufficiency `None/not_single_field`.
- Looked for a third mouth that lifts「李明重疾险」without a particle table and without a type table.
  - object_cover does it, by residual emptiness. Charter §1.3 forbids that as Q2.
  - field_only does it, by treating 李明's 1A pass as the whole request. 043 already shows that mouth lifting I248/I213/I154.
  - strip_identity / strip_any also lift `SYN-concat`, and they lift `SYN-particle` only after peeling `的`. Frozen spread: I129 综拓潜客, I246 客户.
  - 「name and product both present in the query」without a residual check would also lift「李明的重疾险」and is a name+product type row. Charter §1.2 forbids that.
  - No other mechanical mouth lifts `SYN-concat` and still abstains on I248 / I213 / `SYN-age`.
- `SYN-age` is stricter than the issue table. `DOMAIN_PARTICLES` already contains `岁/以上`. After peeling, leftover is `保费`. Spreading covering needs the next word, not just the two particles the issue named.

### Reasoning

Sufficiency is the honest mouth **because of what it refuses to claim**, not because it bought a new mixed-pack point.

「较好」in this charter is not 41/47. It is: 王坤林/杨杰 同侧抬成功; 假姓名/盘客/目录产品不回退; 不把姓名维做成整句成功; 不按题型分流; 不靠残句为空定义办成; 新形状打不中就 inherit. Sufficiency does that. wide / surname / field_only / strip_any each break a gate. object_cover ties the frozen score and still carries the residual definition 042 just rejected.

Read the two collisions differently:

1. sufficiency ≡ live_identity. This is the 026 floor restated as Q1+Q2, not a third algorithm. 044 is right to refuse renaming it `object_cover`.
2. sufficiency ≈ object_cover on the frozen traces only. That is the non-victory. The extra covering hand exists (`SYN-concat`) and is exactly the hand that forces the next table (`SYN-particle` residual `的`; `SYN-age` leftover `保费`; strip_any already lifting I129/I246).

I did not find a legal third mouth for「李明重疾险」. Any mouth that lifts it either inspects residual emptiness, or sorts the request into a name+product type, or treats a passing name as the whole request. All three fail the charter. Inherit on that cell is the authorized exit, not a hole.

Dual gate holds on this dump: set A fake-name / 盘客 / catalog-product counts are unchanged across current and sufficiency; the only set-A flip is I539 王坤林; name+product six labeled rows stay 0/6 because live never delivered the name (parser, not a judge win). Do not merge this mouth into `draft/judge.py`. That is 045.

Sufficiency itself is not residual-empty in disguise. `value==query` on one field is a sufficiency witness ("the delivered value **is** the request"). It does not classify the query into 姓名题/保单题 first, and a new shape does not need a new row to land — it inherits. That is the charter's total function.

### Improvement Proposal

- **Target**: Candidate = `decide_sufficiency` L107–126. Controls stay `exit_live_identity`, `exit_object_cover`, `exit_field_only`, `exit_strip_*`. Principle lock = `issues/trace/name-sufficiency.md` §3–§7. Reports must keep overlay/inherit; mixed 41 is not a release number (charter §2: 不是 oracle).
- **Change**: Consensus text, not a new scorer:

```text
sufficiency = live_identity 的 Q1+Q2 写法 = 本轮候选
object_cover 的冻结同分是假撞车（SYN-concat 已分开）
不为「李明重疾险」开第三张嘴
strip_any / field_only 保持负对照
不并进 draft/judge.py
```

Do not add `name+product` as an authorized pair. Do not peel `的`. Do not treat residual `''` as a win condition.
- **Verification**:

```bash
python3 issues/trace/simulate_1a_sufficiency_program.py
python3 -c "import json; from pathlib import Path; d=json.loads(Path('issues/trace/simulate_1a_sufficiency_program.json').read_text()); assert d['mixed']['scores']['sufficiency']['agree']==41; assert d['mixed']['scores']['object_cover']['agree']==41; assert d['set_a']['flips']['sufficiency']['lifted_to_f']==1; assert d['set_a']['sufficiency_vs_live_identity']==[]; assert d['set_a']['sufficiency_vs_object_cover']==[]; assert d['mixed']['modes']['sufficiency']['overlay_n']==15; assert d['mixed']['modes']['sufficiency']['inherit_n']==33; rows={r['id']:r for r in d['synthetics']['rows']}; assert rows['SYN-concat']['sufficiency'] is None and rows['SYN-concat']['object_cover']=='fulfilled'; assert rows['SYN-particle']['sufficiency'] is None and rows['SYN-particle']['object_cover'] is None; assert rows['SYN-honglian']['sufficiency'] is None and rows['SYN-honglian']['field_only']=='fulfilled'; print('044 reading ok')"
```
## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `15b6719c8967bbf9`

较好的处理是充分性，不是再盖一层。赢的是标准和边界，不是新分数。

充分性之所以较好，是因为它拒绝声称的东西：只在「恰好一个字段、值等于整句、该字段过 Q1」时主动改成功；其余不改判；从不过失败。不改判是正式出口。新形状打不中就停，不必加类型行，也不必剥虚词。

两处分数撞车必须分开读：

1. 充分性 ≡ `live_identity`：这是 026 地板写成 Q1+Q2，不是第三套算法。禁止再把它改名为覆盖门。
2. 充分性 ≈ 覆盖门，只发生在冻结痕迹上：假撞车。`SYN-concat`「李明重疾险」已经分开。覆盖门多出来的那只手，就是下一张虚词表/字段类。`SYN-age` 剥掉「岁/以上」还剩「保费」。`strip_any` 已经在冻结集上抬了「综拓潜客」「客户」。

不存在第三张合法嘴去抬「李明重疾险」：残句为空、姓名+产品类型行、把过 1A 的姓名当成整句成功，三条都踩章程。那一格的授权出口就是不改判。

双闸在本 dump 上成立：假姓名/盘客/目录产品不回退；集 A 只主动抬王坤林；真名+产品六条 live 没交姓名，保持失败，算解析不是判定胜利。不并进 `draft/judge.py`。

闸：exit 0，`isolation_valid=true`，`scope_valid=true`。同一 dump SHA。
