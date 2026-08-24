# Issue #019: 集 B「姓名+产品」六条 live 丢掉姓名，4A 头部 F 地板在解析层就没过

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: Live parse / 4A floor（不是 judge 叠加能补的）
**Cases**: HB009–HB014；对照 HB001–HB008 裸名 live 已抽出 `searchClientName`

## Verifier Discovery

用户只拍 1A / 4A。4A 的集 B 里有一类头部成功样本：真名 + 产品，期望 F。本轮按章程把正常 + bad 混合包先跑了真实 live。六条「姓名+产品」在解析层就把姓名丢掉了。

### 触发输入

混合包：`issues/trace/name_scenario_mixed_pack.json`
收集器：`issues/trace/collect_name_scenario_judge.py`
痕迹：`issues/trace/name_scenario_runs/HB00{9,10,11,12,13,14}.json`
复现：看上述 JSON 的 `live.fields` / `live.values`，或

```bash
python3 -c "import json;from pathlib import Path
for i in range(9,15):
 d=json.loads(Path(f'issues/trace/name_scenario_runs/HB0{i:02d}.json').read_text())
 print(d['id'], d['query'], d['live']['fields'], d['live']['values'])"
```

| ID | query | 期望 | live 字段 | live 值 | 姓名在不在 |
|---|---|---|---|---|---|
| HB009 | 李明的重疾险 | F | `pCategorys` | 疾病保险 | 丢了 |
| HB010 | 张伟买了年金险 | F | `pCategorys` | 年金保险 | 丢了 |
| HB011 | 王芳的两全险 | F | `plantypedesc` | 两全险 | 丢了 |
| HB012 | 陈静有没有医疗险 | F | `pCategorys` | 医疗保险 | 丢了 |
| HB013 | 刘洋的增额寿 | F | （空） | （空） | 整句没交成 |
| HB014 | 赵强买过重疾 | F | `abbrname` | 重疾 | 丢了 |

对照：同一批集 B 的八条裸名 HB001–HB008，live 全部是 `searchClientName MATCH <姓名>`，形态和杨杰 / 王坤林 / 共展一样。四条合法单号 HB015–HB018 的 `clientNo` / `polNo` 也对。所以不是「集 B 整包 live 挂了」，是「姓名+产品」这一类把姓名吐掉了。

### 期望

章程 §2 双闸第二扇：集 B / 混合包头部 F 不得掉。
4A 原文：真名、真名+产品、合法单号三类都期望成功。
fulfilled §2.1：F 要证据证明用户要的结果拿到了。用户要的是「这个人的这种产品」，只交产品、不交人，核心结果缺了一半。
material-positioning 不变量 1：不能拿程序出口或愿望字段冒充 live 事实。`head_set_b.json` 里的 `expected_live_field` 是愿望，不是解析结果。

### 实际

六条 live 都没有 `searchClientName`。HB013 连产品都没有，条件为空。
因此：

1. 当前 draft judge 就算跑完，也不能诚实把这六条抬成 F——姓名没交出来。
2. 内存叠加若因为问句里有「重疾 / 年金 / 两全」就报 F，是在用问句补 live，违反 oracle。
3. 上一轮 018 说集 B 18/18 是程序自洽、当时未测。现在 live 齐了：裸名和单号过了解析，**姓名+产品没过**。4A 地板在这一类上是红的。

本轮 judge 收集器会继续给这六条打当前判定。无论当前判定是 F（只认产品）还是 NF（发现缺姓名），都改变不了「live 没交姓名」这个事实。缺 judge 的条目在 020 / 021 里标「未测」，本 issue 不拿 judge 句子当主证据。

### 根因层

4A 头部 F 地板被理解成了「问句长得像成功样本」。真正的地板在 live 有没有把姓名和产品一起交出来。姓名+产品这条在 parser 就丢了姓名，judge / 内存叠加都救不了。

这不是 1A 过严，也不是 341 长尾分布问题。这是集 B 自己的头部对照在解析层缺交付。

### 和 016 / 017 / 018 的边界

- 016 / 017：内存口径会不会回退假姓名、会不会误伤保单号。本 issue 不重开。
- 018：当时集 B 没有 live，18/18 不能当评测。本 issue 补上 live 之后的第一块缺口：姓名+产品。
- 不把「去年 / 格式外 / 称谓 / 昊轩」卷进来。

### 不是什么

- 不是要改 `draft/judge.py` 或 prompt。
- 不是要改 `head_set_b.json`。
- 不是要用 1A-role 叠加把这六条改写成 F。
- 不是说裸名、单号也没交成。那两类 live 是过的。

### 可证伪修复

这六条必须先在 live 上同时交出姓名和产品，4A 这一类才能从「未过地板」变成「可评测」。验收：

```bash
python3 -c "import json;from pathlib import Path
bad=[]
for i in range(9,15):
 d=json.loads(Path(f'issues/trace/name_scenario_runs/HB0{i:02d}.json').read_text())
 fields=d['live']['fields']
 if 'searchClientName' not in fields: bad.append((d['id'], fields))
print(bad or 'ok')"
```

空列表才算这一类 live 地板过了。在此之前，任何「改判定后集 B 18/18」都仍是程序自洽。


### 新鲜 judge 补记（不改主证据）

HB009–HB014 的当前 draft judge 现已跑完，六条都是 `not_fulfilled`。理由分别是「遗漏姓名」或 HB013「空 conditions」。这只确认 019：judge 看见了 live 缺姓名，没有假装成功。主证据仍是 live 字段，不是这六句判定。

## Architect Response

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: f3e708f76cfa44c3
- pid: 66079

### Investigation
Independently re-read frozen traces `issues/trace/name_scenario_runs/HB009.json`–`HB014.json` (and HB001–HB008 / HB015–HB018 as controls). Did **not** copy verifier numbers. Also re-ran `python3 issues/trace/simulate_1a_mixed_program.py` and imported `exit_wide` / `exit_surname` / `exit_role` to inspect raw exits before `apply_exit` inherit.

Live facts from the frozen traces (not from the dump):

| ID | query | live.fields | live.values | searchClientName | judge_status |
|---|---|---|---|---|---|
| HB009 | 李明的重疾险 | `pCategorys` | 疾病保险 | absent | not_fulfilled |
| HB010 | 张伟买了年金险 | `pCategorys` | 年金保险 | absent | not_fulfilled |
| HB011 | 王芳的两全险 | `polNoInfo.plancodeinfo.plantypedesc` | 两全险 | absent | not_fulfilled |
| HB012 | 陈静有没有医疗险 | `pCategorys` | 医疗保险 | absent | not_fulfilled |
| HB013 | 刘洋的增额寿 | [] | [] | absent | not_fulfilled |
| HB014 | 赵强买过重疾 | `polNoInfo.plancodeinfo.abbrname` | 重疾 | absent | not_fulfilled |

Controls: HB001–HB008 live is uniformly `searchClientName MATCH <token>`. HB015–HB018 live has `clientNo` / `polNo`. So this is the name+product family, not a whole-pack live outage.

`head_set_b.json` HB009–HB014 `expected_live_fields` is `["searchClientName", "product"]` and `expected_status` is `fulfilled`. That is the 4A wish list, not a live observation.

Raw overlay exits on these six rows (my import, not dump scores): `wide=None`, `surname=None`, `role=None`. They inherit current `not_fulfilled`. I also hypothetically injected `searchClientName` into the six rows: `catalog_product_in_query` is still false (set A abbrname catalog is 22 product names like 金凤/宝贝卡/孝心, none of which are substrings of these queries), and role still returns `None`. No overlay invents a name condition from the query text.

Current draft judge reasons (frozen, not re-run): HB009–HB012 / HB014 say the product was delivered and the person name was omitted; HB013 says empty conditions. That corroborates the live hole. It is not an independent floor.

Parked queries (去年 / 弟弟 / 老板娘 / 大写P07 / C00OO / 配$) are not in the 48-pack. `undecided_given_name` (I485 昊轩) is not in this family.

### Reasoning
Agree with the issue’s root-cause layer. 4A / charter §2 second gate says 真名+产品 is a head-F family. fulfilled §2.1 requires evidence the user got what they asked for. The user asked for “this person + this product”. Live delivered only the product (HB013 delivered nothing). material-positioning 不变量 1: `current_behavior` cannot stand in for the missing live fact, and `expected_live_fields` cannot be treated as if the parser already emitted them.

Two tightenings, neither of which saves the floor:

1. The issue table shortens HB011/HB014 field names to `plantypedesc` / `abbrname`. Frozen traces use the full paths. Same fact.
2. Current judge marking these six NF is honest, not a 1A-overstrictness miss. Overlay scores of 0/6 F are also honest. The red floor is parse delivery, not judge tightness.

No overlay in this charter may mark HB009–HB014 fulfilled. Doing so would reconstruct `searchClientName` from the query string and violate the oracle. 018’s “set B 18/18 is program self-consistency / then untested” is now partially tested: bare-name and legal-id live passed; name+product live did not. I do not reopen 016–018.

### Improvement Proposal
- **Target**: Live parser / product condition emitter for compound “姓名 + 产品” queries. Not `draft/judge.py`, not `head_set_b.json`, not the in-memory exits, not xlsx/canvas. Out of this charter’s write set.
- **Change**: For the six queries, live `conditions` must contain **both** `searchClientName MATCH <person>` **and** a product/category field (the same families already emitted: `pCategorys` / `polNoInfo.plancodeinfo.plantypedesc` / `polNoInfo.plancodeinfo.abbrname`). HB013 must emit at least those two; empty conditions is not a successful parse. Overlays stay `None` on this family until that live fact exists. Do not add a query-text → name backfill in `simulate_1a_mixed_program.py`.
- **Verification** (after a real live re-collect; do not fake fields):

```bash
python3 -c "import json;from pathlib import Path
bad=[]
for i in range(9,15):
 d=json.loads(Path(f'issues/trace/name_scenario_runs/HB0{i:02d}.json').read_text())
 fields=d['live']['fields']
 if 'searchClientName' not in fields: bad.append((d['id'], fields))
print(bad or 'ok')"
```

Empty list is the live floor. Until then, any “set B 18/18 after judge tweak” is still program self-consistency.

## Consensus
**Verdict**: real-problem

双方独立读冻结痕迹：HB009–HB014 都没有 `searchClientName`，HB013 条件为空。同一包里裸名 HB001–HB008、合法单号 HB015–HB018 的 live 是过的。三口叠加在这六条上 raw=`None`，继承当前 NF，没有用问句补姓名。

接受 architect 的收口：当前 judge 判 NF 是诚实的，不是 1A 过严。4A「姓名+产品」地板红在解析层。任何「改判定后集 B 18/18」在这六条 live 补上姓名之前，仍是程序自洽。

不改 `draft/judge.py`，不改 `head_set_b.json`，不用叠加把这六条抬成 F。本 issue 在上述复现脚本仍打出非空 `bad` 时保持 open。
