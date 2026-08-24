# Issue #036: 无歧义切法是对象覆盖：残句非空必须不改判，残句空也不是成功

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 原则 / 标准 / 边界（内存候选，不是生产代码）
**Cases**: 红莲保单、张忠波保单号、李明的重疾险、综拓潜客、共展、家办客户

## Verifier Discovery

035 钉死整句覆盖门只是局部代理。本 issue 钉替代结构。037 才给冻结数字。038 才说能不能并进判定。

用户要的层级是 `fulfilled.md` 那种：只看一件事、有单位、有不看、有封闭三态。不是再找一个更顺的字符串相等。

### 触发输入

原则正文：`issues/trace/name-object-coverage.md`

实现：`issues/trace/simulate_1a_principle_program.py` 里的 `decide_object_cover`

验收命令：

```bash
python3 issues/trace/simulate_1a_principle_program.py
```

### 期望

章程：「排除所有可能的歧义，能覆盖所有可能出现的情况」。

工作定义（可证伪）：

1. 任意 (问句, live 条件) 都能落到「主动改成功 / 主动改失败 / 不改判」之一，没有「看情况」。
2. 问句是用户要什么，live 是系统做了什么。不能从问句发明成功。
3. 不看混合包角色，不问句定题型，不剥「的 / 查一下 / 保单号」。
4. 本原则本轮不主动改失败——主动改失败就是在声称已经认出假姓名或次要词。

### 实际

决策顺序是全函数，见原则文第 4–6 节。压缩成四句：

1. live 值必须是问句里的连续片段；对不上 → 不改判。
2. 挖掉这些片段后还剩下非空白字 → 不改判。
3. 残句空了，但交出来的对象里没有姓名也没有单号 → 不改判。
4. 残句空了，且有身份对象，姓名若出现则过 1A 姓氏门 → 主动改成功。

第 2 句挡住题型泄漏：红莲保单剩下「保单」，不抬成功。张忠波保单号剩下「保单号」，不改失败。

第 3 句挡住「残句空 = 成功」：集 A I129「综拓潜客」live 交了「综拓」+「潜客」，残句为空，当前失败。合成探针 SYN-zongtuo 同步不改判。

第 4 句里的姓氏目录是 1A 已经拍过的先验，不是题型分流。共展 / 豆芽 / 昊轩走「姓名不过门 → 不改判」，不是 overlay 失败。

主动改失败：空集。假姓名闸继续由当前失败守。

### 根因层

「覆盖所有情况」若理解成穷举题型，会立刻长回 025 的状态机。正确闭包是第三态：不改判。不改判不是漏洞，是原则还没被授权说话的地方。

「排除歧义」若理解成再找一句口语，会立刻长回覆盖门。正确做法是把谓语锁死：残句 = 挖掉跨度后剩下的原文，空白可忽略，虚词不可忽略。

### 和 1A / 019 / 027 的边界

- 1A：2–4 字中文名可单独撑成功。本原则只在残句空且 live 交了这个姓名时用它。不重开 1A。
- 019：姓名+产品六条 live 丢姓名。本原则禁止从问句补人。不重开 019。
- 027：单元格过了 ≠ 假姓名检测完成。本原则继续 inherit，不准 overlay NF。不重开 027。

### 不是什么

- 不是第四套姓名状态机。
- 不是宣布已经会剥「的」和「查一下」。
- 不是把姓氏表升级成架构；它只给姓名对象过 1A 门。

### 可证伪修复

哪一口做了下面任何一件，就不是本原则：把红莲保单抬成功；把张忠波保单号改失败；把家办客户从空 live 抬成功；把李明的重疾险在没交姓名时抬成功；把共展写成「已会认假」；把综拓潜客抬成功；开始剥「查一下」。验收看合成探针 `synthetics_all_ok` 以及原则文第 8 节。

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 770d8502492aedbc
- pid: 44788

### Investigation

- Read the full principle (`issues/trace/name-object-coverage.md` §3–§9) and `decide_object_cover` L93–147. Sequential order: empty query / no live / pair mismatch / empty value / not a contiguous unused span / leftover after span removal / no name-or-id field / name fails 1A / `other` field / else overlay F. `status is None` = inherit. No branch reads `pack_role`. Overlay NF is impossible.
- Re-ran the principle script. `synthetics_all_ok=true`, 15/15. SHA-256 matched the dump.
- Checked the charter cases myself:

| case | live | residual / reason | mode | current |
|---|---|---|---|---|
| I248 红莲保单 | searchClientName=红莲 | residual `保单` | inherit | NF |
| I007 张忠波保单号 | searchClientName=张忠波 | residual `保单号` | inherit | F |
| I129 综拓潜客 | validSinsPol=综拓 + pajjmemberstatus=潜客 | residual empty, `no_identity_field` | inherit | NF |
| I650 共展 / I607 豆芽 / I485 昊轩 | searchClientName=自身 | residual empty, `name_not_ok` | inherit | NF |
| I210 金凤 | product abbrname=金凤 | `no_identity_field` | inherit | F |
| I548 家办客户 | empty | `no_live` | inherit | NF |
| HB009–014 | name dropped or ungrounded / leftover | inherit | NF |
| SYN-concat-name-product 李明重疾险 | name+product | residual empty, `overlay_f_mixed` | overlay F | n/a |
| SYN-particle-name-product 李明的重疾险 | name+product | residual `的` | inherit | n/a |

- Extra fact the issue did not need, but the residual rule does: `has_surname_shape("红莲")` is True and 红莲 is **not** in the product catalog. If residual were ignored, I248 would be a surname-shaped name overlay. Residual is the load-bearing boundary, not decoration.
- Alignment I actually ran: leftmost unused occurrence, live-field order. Principle text §4.1 does not lock that search order.

### Reasoning

This is the right replacement cut. I will not rubber-stamp “already zero ambiguity”.

**Totality.** Every `(query, live)` I traced lands in overlay-F or inherit. Overlay NF is an empty set **by authorization**, not a missing cell. §6’s seven-row table plus §4’s numbered stops are a total function. “覆盖所有情况” here correctly means “every input has a defined destination”, not “every sentence is rewritten to the business-correct label”.

**Two-reads.** The predicates the user can actually trip are locked:

- 对象 = live condition, not a guessed question type
- 残句 = leftover raw characters after spans; whitespace may vanish; `的` / `查一下` / `保单号` may not
- 不改判 = this mouth does not speak; it is **not** “already recognized as fake”
- 身份对象 = field is name or client/policy number

Three leftover spec holes, none of them the user’s three questions:

1. Span placement is deterministic in code (field order, first unused hit) but not written in §4.1. A second occurrence / overlapping pair can inherit under greedy and succeed under another alignment. Lock the code’s rule in the text.
2. Implementation `residual.strip()` drops all Unicode whitespace (`\u3000` included). The prose only lists 空格 / 换行 / 制表. Lock “Unicode whitespace” or change the code to those three.
3. §6’s last row omits `other` fields. §4.3 clause 10 and the `other_field` return already inherit. Put `other` in the table so the compression cannot be two-read.

**Is “never overlay NF” a hole?** No. Overlay NF would claim “I detected a fake / this must not succeed”. That is the 027 path: cell-still-NF ≠ fake-name detector finished. 共展 / 豆芽 stay inherit-NF because 1A surname fails, not because this mouth classified them as fake. The only operational residue is: if the **host** ever marks 共展 F, inherit will keep that wrong F. That is 038’s host fight, not a missing clause here. Filling it would grow a blacklist, which this charter forbids.

**Is leftover-including-`的` too conservative to be a principle?** No. Peeling `的` is the next rule table. The moment 残句为空 starts meaning “leftover is only particles / speech wrappers”, 残句 has two readings and we are back to `exit_role`. SYN-particle-name-product vs SYN-concat-name-product is the right pair: same objects, one extra `的`, opposite modes. Keep it. Do not decide 昊轩 / 去年 / 称谓 here; they already have a destination (inherit).

This is not a fourth name state machine. It does not read mix-pack `role`. Surname catalog is used only as the already-decided 1A gate on a **name field**, after residual is empty.

### Improvement Proposal

- **Target**: `issues/trace/name-object-coverage.md` §4.1 and §6; `decide_object_cover` already implements the intended order.
- **Change**:
  1. Add to §4.1: 跨度按 live 条件顺序、在问句里取第一段尚未占用的相同连续原文；任一值占不到 → 不改判。禁止换一种对齐把同一输入改成主动改成功。
  2. Add to §4.2: 残句比较前去掉的空白 = Unicode whitespace（含全角空格），不是「虚词」。
  3. Add a row to §6: 对齐且残句空，但出现 `other` 字段 → 不改判。
  4. Do **not** peel `的` / `查一下` / `保单号`. Do **not** add overlay NF.
- **Verification**: re-run `python3 issues/trace/simulate_1a_principle_program.py`. Require `synthetics_all_ok=true` and these reasons: I248 `residual_nonempty`/`保单`; I007 `residual_nonempty`/`保单号`; I129 `no_identity_field`; I650 `name_not_ok`; SYN-concat-name-product `overlay_f_mixed`; SYN-particle-name-product residual `的`. `git diff -- impl/projects/client_search/draft/judge.py` stays empty.

## Consensus
**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `770d8502492aedbc`

对象覆盖是替代切法，而且是全函数。任意 (问句, live) 落到「主动改成功」或「不改判」。主动改失败是空集，这是授权边界，不是缺格：一旦允许主动改失败，就会重新长出假姓名黑名单 / 保单号否决。共展 / 豆芽走的是「姓名不过 1A 门 → 不改判」，不是「已经会认假」。

残句含「的」必须 inherit。剥「的 / 查一下 / 保单号」就是下一张规则表。I248 是承重墙：红莲有姓氏形态、也不在产品目录里；挡住抬成功的是残句「保单」，不是「看起来不像人名」。

接受三处规格锁，并已写回原则文（代码本来就是这个顺序，不改脚本、不改 SHA）：

1. §4.1：跨度按 live 条件顺序，取第一段尚未占用的相同连续原文；禁止换对齐把同一输入改成主动改成功。
2. §4.2：残句比较前去掉的空白 = Unicode whitespace（含全角空格），不是虚词。
3. §4.3 / §6：出现 `other` 字段 → 不改判。

昊轩 / 去年 / 称谓继续停在不改判，本 issue 不代选。合成探针 15/15 仍过。不并进 `draft/judge.py`。
