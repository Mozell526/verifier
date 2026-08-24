# Issue #045: 原则锁住之后，仍不得并进判定；剩余项是项目决定

**Class**: architecture
**Severity**: medium
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: Judge host / check「只改结果不改源头」
**Cases**: `impl/projects/client_search/draft/judge.py` 裸词规则；昊轩 / 去年 / 称谓 / 格式外

## Verifier Discovery

042–044 把嘴锁成充分性。本 issue 只划：哪些事角色不能代做。

### 源头还在提示里

`impl/projects/client_search/draft/judge.py` 约 L1504–1508：

> 独立姓名证据指资料明确该 token 是人名（或该形态就是姓名检索）；
> live 把它写成姓名、路径碰巧叫 searchClientName，都不够支撑 fulfilled。

这句和 1A 互搏：1A 说 2–4 字中文名可单独撑姓名维；提示说还要目录级人名证据。
王坤林过严从这里来，不从覆盖门来。

028 / 038 已经把源头钉在这。本轮不重开，也不把内存函数补进提示。
check 的 c) 条：只改内存对照、不改这句，下次重跑 judge 仍过严。
本轮章程禁止改 `draft/judge.py`。所以这里只能 escalate。

### 剥虚词是攻击面，不是优化

`strip_any` 为了「效果更好」准备了一张虚词表，并放开字段类。
冻结集上它抬了「综拓潜客」和「客户」。
再往表里加「岁 / 以上 / 有 / 未」，年龄保费题会开始被句子形状操纵。

aihacking：谁能在问句里加减虚词，谁就能拨判定。
这不是充分性测试，是规则表。本轮禁止把它当候选。

### 仍停住

1. 要不要对外看见第二问 / 用哪句中文 / 改不改 schema
2. 去年算不算核心
3. 称谓 / 格式外空条件怎么标
4. 昊轩在 1A 下必须成功还是可以继续失败
5. 现在改不改提示里的姓名闸

角色不得代选，也不得请用户把所有可能形状列完。
覆盖在 044 里已经是全函数：打不中充分性就不改判。

### 不是什么

- 不是说 042–044 还没锁住
- 不是请用户再写一句对外题面
- 不是宣布采用「充分性 / 立住了 / 现成有」当对外词

### 可证伪

1. 若本轮有角色把 sufficiency 并进 `draft/judge.py` 或提示，本 issue 被越权。
2. 若 Consensus 把昊轩 / 去年 / 称谓写成已经代选，本 issue 失败。
3. 若把 042–044 写成「还没做完所以请用户先列表」，本 issue 失败。

---
---
## Architect Response #1

**Verdict**: escalate-to-project

### Spawn Evidence
- spawn-id: 15b6719c8967bbf9
- pid: 81087

### Investigation

- Read `issues/open/issue-045.md`, charter §3–§4, Consensus-only `issue-028.md` and `issue-038.md`, and `impl/projects/client_search/draft/judge.py` L1504–1508. The host still says:

  > If actual treats a token as a person name, Reference/path match alone is not intent proof. Without independent name evidence, do not mark that dimension fulfilled. 独立姓名证据指资料明确该 token 是人名（或该形态就是姓名检索）；live 把它写成姓名、路径碰巧叫 searchClientName，都不够支撑 fulfilled（§2.1）。

- This round's script does not import or patch `draft/judge.py`. Charter red line: must not touch `impl/projects/client_search/` or `draft/judge.py`. 028 / 038 already escalated the same sentence. I am not re-judging those issues; I am checking that the source has not moved. It has not.
- 042–044 are **not** unfinished in the sense that would reopen a shape inventory. I independently reran the sufficiency script (SHA `aaa5381cefef843ad52b706dc1a7813db5308c8b707f3ae07b3cefd859f5c980`) and judged those three files in this same spawn: covering is residual regularization (042), field_only mis-lifts seven frozen rows after dropping I595/I638 (043), sufficiency is the candidate mouth and the object_cover score tie is not a win (044). They are still first-round argue, not Consensus yet. That does **not** authorize "请用户把所有可能形状列完", and it does **not** authorize merging a memory function into the host while we wait.
- `strip_any` on this dump lifts I129 综拓潜客 and I246 客户. `SYN-age` still has leftover `保费` after the current particle table. That is an attack surface (who edits the particle list edits the verdict), not an optimization path. Charter already forbids it as a candidate.
- Parked items in charter §4 are untouched: 去年, 格式外/称谓, 昊轩, 要不要看见第二问 / 改 schema / 对外中文.

### Reasoning

Escalate is the right verdict. The remaining break is the host name-gate versus 1A, plus four parked product decisions. Nothing in-scope in 042–044 repairs that.

1A says a 2–4 字中文名 can carry the **name dimension** by itself. L1504–1508 tells the model that `searchClientName` plus the token is not enough unless a directory-grade "独立姓名证据" also appears, while the same paragraph offers「该形态就是姓名检索」as an escape. 038 already recorded the same live shape `searchClientName MATCH <整句>` flipping 匡西永 / 张伟 vs 王坤林. Memory sufficiency can overlay 王坤林 (and would overlay 杨杰). Next fresh host run can still fail the next 王坤林. check 的 c) 条 is correct: change only the overlay, leave this sentence, and the judge is still too strict.

042–044 being mid-argue is not a reason to convert this issue into `needs-more-info` or to ask for a complete shape list. Coverage this charter defined is a total function: miss the sufficiency test → inherit. The inventory request is the thing 045's falsifier 3 kills.

What this peer must not do: pick 昊轩, pick 去年, pick a public Chinese sentence, paste `decide_sufficiency` into the prompt, or "improve" covering with a larger particle table. Those are either project decisions or the regularization 042 just rejected.

### Improvement Proposal

- **Target**: `impl/projects/client_search/draft/judge.py` L1504–1508 (host name-gate). Parked, not to be chosen here: 昊轩 under 1A; 去年; 称谓/格式外; schema / 对外中文 / 要不要看见第二问.
- **Change**: Only after the user opens the host. 028 already wrote the opening checklist; this issue does not invent a second one. Minimum when opened: delete the self-fighting 裸词 paragraph; 1A's name-dimension exit becomes a **code** gate, not another prompt sticker; LLM writes evidence only; 昊轩 stays abstain until the user chooses; HB009–014 stay parser (019), not a judge patch. Memory `decide_sufficiency` / `decide_object_cover` / residual algebra stay out of the prompt (012 / 038).
- **Verification** (still the non-merge check, not a fix check):

```bash
git diff -- impl/projects/client_search/draft/judge.py
python3 -c "from pathlib import Path; text=Path('impl/projects/client_search/draft/judge.py').read_text(); assert 'decide_sufficiency' not in text; assert 'decide_object_cover' not in text; assert '独立姓名证据指资料明确该 token 是人名' in text; print('045 still escalated; host untouched')"
```
- **Why peer cannot apply**: Architect is read-only. Charter §3 / this spawn's permission mode forbid editing `draft/judge.py`. 昊轩 / 去年 / 称谓 / 对外题面 are charter §4 project decisions. 028 / 038 already require an explicit user confirmation before the host is opened.
## Consensus

**Verdict**: escalate-to-project
**Official peer**: Architect Response #1 · spawn-id `15b6719c8967bbf9`

原则锁住之后，仍不得并进判定。剩余项是章程 §4 项目决定，不是「042–044 还没做完」。

源头仍在 `impl/projects/client_search/draft/judge.py` L1504–1508：提示要求目录级「独立姓名证据」，和 1A「2–4 字中文名可单独撑姓名维」互搏。王坤林过严从这里来。028 / 038 已经 escalate 过同一句。本轮脚本没有 import / 补丁这句。check 的 c) 条成立：只改内存对照、不改这句，下次重跑 judge 仍过严。

角色不得代做：

1. 把充分性 / 覆盖门 / 残句代数并进提示或 `draft/judge.py`
2. 代选昊轩 / 去年 / 称谓 / 格式外
3. 代拟对外中文，或请用户把所有可能形状列完
4. 用更大的虚词表「优化」覆盖门（`strip_any` 已证明这是攻击面）

覆盖在 044 已是全函数：打不中充分性就不改判。escalate 不得再读成抽象没做完。

闸：exit 0，`isolation_valid=true`，`scope_valid=true`。host 未动。
