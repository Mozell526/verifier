# Issue #020: 当前 draft judge 对同形态裸名仍左右互搏；集 B 真名 7F/5NF，王坤林与匡西永相对 xlsx 对翻

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: Evaluation / Judge prompt（同一把尺自己在抖，不是 1A 政策没定）
**Cases**: I224 杨杰、I310 郑鑫、I336 匡西永、I539 王坤林；HB001–HB008 集 B 裸名。对照 I650 共展、I607 豆芽（NF 方向对，不得吐回）

## Verifier Discovery

用户只拍 1A / 4A。本轮按章程把正常 + bad 混合包的 live 和当前 draft judge 都跑了。011 已经钉过：同是 2–4 汉字裸词 + 同一 `searchClientName MATCH`，新 judge 自己选提示里的哪半句。本 issue 不重开 011 的结论，只补混合包上的新鲜判定：受害者换人了，机制没换。

### 触发输入

混合包：`issues/trace/name_scenario_mixed_pack.json`
痕迹：`issues/trace/name_scenario_runs/{I224,I310,I336,I539,HB001..HB008}.json`
xlsx（只读对照）：`/Users/xiaozijian/Downloads/verifier-client_search-cases-20260814-185013.xlsx`
提示原文：`impl/projects/client_search/draft/judge.py` L1504–1508
复现：

```bash
python3 -c "import json;from pathlib import Path
ids=['I224','I310','I336','I539','HB001','HB002','HB003','HB004','HB005','HB006','HB007','HB008']
for cid in ids:
 d=json.loads(Path(f'issues/trace/name_scenario_runs/{cid}.json').read_text())
 print(cid, d['query'], d['live']['fields'], d['live']['values'], d['judge_status'])"
```

### 同 live、同当前 judge

十二条真名裸词的 live 全是 `searchClientName MATCH <token>`，形态和共展一样。新鲜判定却劈成两半：

| ID | query | live | xlsx | 新鲜判定 | 模型咬的半句 |
|---|---|---|---|---|---|
| I224 | 杨杰 | `searchClientName MATCH 杨杰` | F | **F** | 「形态就是姓名 / 字段语义为人名」 |
| I310 | 郑鑫 | 同形 | F | **F** | 「两字中文姓名」 |
| I336 | 匡西永 | 同形 | **F** | **NF** | 「裸词，没有独立证明其为人名」 |
| I539 | 王坤林 | 同形 | **NF** | **F** | 「单姓加两字名的中文人名形态」 |
| HB001 | 李明 | 同形 | — | **F** | 「符合中文姓名结构」 |
| HB002 | 张伟 | 同形 | — | **NF** | 「仅凭裸词和字段映射不够」 |
| HB003 | 王芳 | 同形 | — | **NF** | 「裸词，未独立证明为人名」 |
| HB004 | 陈静 | 同形 | — | **F** | 「明确指向姓名为陈静的客户」 |
| HB005 | 周婷婷 | 同形 | — | **NF** | 「证据仅支持带姓名上下文的规则」 |
| HB006 | 吴志强 | 同形 | — | **NF** | 「字段定义只能证明字段语义」 |
| HB007 | 马文博 | 同形 | — | **F** | 「独立的三字中文姓名」 |
| HB008 | 欧阳文博 | 同形 | — | **F** | 「明确可按客户本人姓名理解」 |

集 B 八条真名：4F / 4NF。集 A 两条三字真名：王坤林与匡西永相对 xlsx **对翻**。011 的左右互搏还在，只是这回王坤林被抬上去、匡西永掉下来。不是固定 ID 名单。

假姓名对照（方向对，闸必须留住）：

| ID | query | live | 新鲜判定 |
|---|---|---|---|
| I650 | 共展 | `searchClientName MATCH 共展` | NF |
| I607 | 豆芽 | 同形 | NF |
| I358 | 见光 | 同形 | NF |
| I168 | 傻生 | 同形 | NF |

### 提示原文（同一段，无代码闸）

`draft/judge.py` L1504–1508：

> If actual treats a token as a person name, Reference/path match alone is not intent proof. Without independent name evidence, do not mark that dimension fulfilled.
> 独立姓名证据指资料明确该 token 是人名（**或该形态就是姓名检索**）；
> live 把它写成姓名、路径碰巧叫 searchClientName，都不够支撑 fulfilled（§2.1）。

F 的句子咬括号里「形态就是姓名检索」。NF 的句子咬「路径叫 searchClientName 不够 / 要独立人名证据」。同一函数、同一段字符串，没有代码按形态分流。模型这回选哪半句，哪半边真名就活。

### 期望

1A：2–4 字中文名可单独撑 F；杨杰与王坤林同侧 = F；共展/豆芽仍 NF。
4A 双闸第二扇：集 B 真名头部 F 不得掉。张伟 / 王芳 / 周婷婷 / 吴志强 是集 B 里故意放的常见真名，不是长尾。
fulfilled §2.1：F 要证据证明用户要的结果拿到了。对「李明」「周婷婷」这种客户搜索最常见形态，live 已经给出姓名条件。
material-positioning 不变量 1：不能把「模型这回有没有咬到括号」当成正式规则。

### 实际

当前 draft judge 用「要独立人名证据」防共展，把头部分布里同一形态的真名误伤了一半。集 A 的 341 条 bad case 会把这把尺训练得更愿意咬「不够」那半句；真实问句里「张伟」「王芳」远比「共展」常见。这就是用户说的：数据集都是长尾，现实分布不一样。

过严不是「凡姓名都 NF」。杨杰 / 李明 / 王坤林 这回是 F。过严是**同形态没有稳定程序**，所以无法用「再严一点 / 再松一点」在 341 上调参来平衡。

### 根因层

提示把互斥的两句话写在同一段里，又没有程序出口按「姓+名 / 目录否决 / 假姓名」分流。LLM 每次抽签。011 用杨杰 vs 王坤林 钉过一次；本轮新鲜判定把这两人翻过去，再用张伟 / 周婷婷 证明不是那两个 ID 的问题。

### 和 011 / 016 / 017 / 019 的边界

- 011：xlsx 上的左右互搏。本 issue 用混合包新鲜判定证明机制还在，不重开 011 的 Consensus。
- 016 / 017：内存宽口径 / 姓氏口径的回退。本 issue 钉的是**当前 judge 自己**，还没叠加上去。
- 019：姓名+产品是 live 丢姓名。那六条当前 judge 诚实打 NF（「遗漏姓名」），方向对，不是本 issue。
- 昊轩仍停住，本 issue 不当对照、不代选。

### 不是什么

- 不是要改 `draft/judge.py` 或 prompt。本轮只比较。
- 不是要在提示里写「王坤林算人名」「张伟算人名」。
- 不是说共展/豆芽也该 F。
- 不是 341 准确率问题。

### 可证伪修复

同一把程序尺，必须让上表十二条真名落在同一侧 = F，且共展/豆芽仍 NF。验收不看某一条 LLM 句子，看冻结痕迹 + 内存叠加出口（见 021）。在提示里加「王坤林是人名」这种例外，不算修复。

```bash
python3 -c "import json;from pathlib import Path
true=['I224','I310','I336','I539','HB001','HB002','HB003','HB004','HB005','HB006','HB007','HB008']
fake=['I650','I607','I358','I168']
# after a real fix these would be overlay exits, not LLM luck
print('document-only this round; overlay in issue-021')"
```

## Architect Response

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: f3e708f76cfa44c3
- pid: 66079

### Investigation
Did not re-run the 48 LLM judges. Re-read frozen traces for the 12 true bare names and the 4 fake-name controls, the xlsx statuses, and `impl/projects/client_search/draft/judge.py` L1504–1508. Independently re-ran the overlay script only to confirm these 12 are the `current` column’s misses, not overlay artifacts.

Frozen live is the same shape for all 12: `searchClientName MATCH <token>`. Fresh `judge_status` from the traces:

| ID | query | xlsx | fresh | which half the reason bites |
|---|---|---|---|---|
| I224 | 杨杰 | F | **F** | 字段语义为人名 / 形态就是姓名 |
| I310 | 郑鑫 | F | **F** | 两字中文姓名 |
| I336 | 匡西永 | **F** | **NF** | 裸词，没有独立证明其为人名 |
| I539 | 王坤林 | **NF** | **F** | 单姓加两字名的中文人名形态 |
| HB001 | 李明 | — | **F** | 符合中文姓名结构 |
| HB002 | 张伟 | — | **NF** | 仅凭裸词和字段映射不够 |
| HB003 | 王芳 | — | **NF** | 裸词，未独立证明为人名 |
| HB004 | 陈静 | — | **F** | 明确指向姓名为陈静的客户 |
| HB005 | 周婷婷 | — | **NF** | 证据仅支持带姓名上下文的规则 |
| HB006 | 吴志强 | — | **NF** | 字段定义只能证明字段语义 |
| HB007 | 马文博 | — | **F** | 独立的三字中文姓名 |
| HB008 | 欧阳文博 | — | **F** | 明确可按客户本人姓名理解 |

Count: **12 true names = 7F / 5NF**. Set B eight alone = **4F / 4NF** (HB001/004/007/008 vs HB002/003/005/006). Issue title’s 7F/5NF is the twelve-name union; the body is right that set B itself is 4/4. Task text that said “set B true names are 7F/5NF” is the union, not set B alone.

xlsx vs fresh on the two three-character set A names: 匡西永 F→NF, 王坤林 NF→F. Same IDs as 011, opposite polarity. Not a fixed victim list.

Fake-name controls I650/I607/I358/I168: same live shape, all fresh NF. Direction required by 1A. Must stay.

Prompt at `draft/judge.py` L1504–1508 is one paragraph with two mutually exclusive clauses: “or 该形态就是姓名检索” vs “live 把它写成姓名、路径碰巧叫 searchClientName，都不够”. No code fork. Confirmed by reading the source, not by trusting the issue quote.

`exit_role` / `exit_surname` / `exit_wide` all raw-`fulfilled` on these 12 (surname-shaped bare name + live `searchClientName`). The 5 NF are current-judge misses, not overlay misses.

I485 昊轩 is **not** a 020 control. Frozen fresh judge for I485 is `not_fulfilled` (same as xlsx). I do not use it here and I do not decide charter §4.3.

### Reasoning
Agree. This is 011’s mechanism on a fresh mixed-pack draw, not a re-opening of 011’s Consensus. 1A / decisions.md: 2–4 character Chinese names already searched as client name = F; 杨杰 and 王坤林 same side = F; 共展/豆芽 stay NF; no “王坤林 is a person” prompt exception. 4A second gate: set B true names must not drop F. 张伟 / 王芳 / 周婷婷 / 吴志强 are the head distribution 1A itself named (李明 / 周婷婷), not 341 long-tail.

The overstrictness is not “every name is NF”. It is that the same live shape has no stable program, so half the head names die when the model bites the “path is not enough” clause. You cannot tune 341 accuracy to fix a coin-flip inside one prompt paragraph.

019 is a different layer (live dropped the name). These 12 have the name. 016/017 are overlay regressions, not current-judge flip-flops. I do not reopen them.

### Improvement Proposal
- **Target**: A later write-enabled change to the judge **program**, not a this-round prompt edit and not an ID allowlist. This charter forbids editing `draft/judge.py`.
- **Change**: Split the L1504–1508 paragraph into a code/role fork that does not name case IDs:
  - If query is 2–4 CJK, live has `searchClientName` whose value is that token, and the token has surname/compound-surname shape → F (covers 杨杰/王坤林/张伟/周婷婷/欧阳文博).
  - If the same live shape has no surname shape (共展/豆芽/见光/傻生) → keep NF.
  - Catalog / toponym / business-word vetoes stay outside this fork (021).
  - Do not write “王坤林算人名” / “张伟算人名”.
- **Verification**: On the frozen traces, the 12 IDs above must all be F and I650/I607/I358/I168 must stay NF. Acceptance is an overlay/program exit, not a new LLM draw.

## Consensus
**Verdict**: real-problem

双方独立读 12 条真名裸词冻结痕迹：live 全是 `searchClientName MATCH <token>`，新鲜判定 **7F / 5NF**。集 B 八条单独是 **4F / 4NF**。标题里的 7F/5NF 是十二人并集，不是集 B 自己。匡西永 xlsx=F / 新鲜=NF，王坤林 xlsx=NF / 新鲜=F。假姓名四条仍 NF。

接受 architect：这是 011 同一段提示左右互搏的新鲜抽签，不重开 011。当前 judge 不能当可用口径。本轮不改 `judge.py` / 提示，不写「张伟算人名」这种例外。

本 issue 在这 12 条仍出现同形 NF、或假姓名被吐回 F 时保持 open。
