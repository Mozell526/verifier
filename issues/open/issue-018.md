# Issue #018: 集 B 18/18 是程序自洽，不是改判定后的评测

**Class**: process
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output + spec
**Layer**: Evaluation / Process（测量本身，不是 1A 该不该做）
**Cases**: `head_set_b.json` HB001–HB018 全部

## Verifier Discovery

用户问：在内存里模拟改判定后的评测效果，看行不行。4A 已经造了独立集 B（18 条，期望全 F）。本 issue 钉的是：这次模拟在集 B 上给出的 18/18，不能当成「改完判定已经评过了」。

### 触发输入

集 B：`impl/projects/client_search/draft/cases/head_set_b.json`

- 18 条，三类：裸名 8、真名+产品 6、合法单号 4。
- 全部 `expected_status=fulfilled`。
- 仓库里没有这 18 条的 live 解析、conditions、旧/新 judge 痕迹。

脚本对集 B 的分支（原文，不是 LLM）：

- 整句 2–4 汉字 → 直接出 F（wide），或「姓+名」才 F（surname）
- 句子里有重疾/年金/两全/医疗险/增额寿/增额 → F
- 句子里能匹配保单号形态 → F

落盘原文：

> Set B has no live/judge traces. Scores are program exits, not LLM judge reruns.

两口径都是 18/18 F，`missing=[]`。

集 B 八个裸名（李明、张伟、王芳、陈静、周婷婷、吴志强、马文博、欧阳文博）都是「姓+名」，所以 surname 口径也会放行。这不能外推到昊轩这种二字无姓。

### 期望

010 Consensus：平衡 = 集 A 单向缺陷否决 **合取** 集 B 头部 F 地板。集 B 必须是独立、冻结、不从 341 里挑的对照。
章程 §5：集 B 若没有 live/judge 痕迹，必须写明，不得假装跑过 LLM judge。
章程 §6：不重跑 LLM judge；只做内存叠加。

所以允许的结论只有两种：

1. 程序出口在集 B 的形态上自洽（本轮做到了）；
2. 还不知道真实 judge 看到集 B 的 live 之后会不会 F。

不允许的结论：1A 已经在集 B 上评过、可以发版。

### 实际

18/18 是脚本按自己写的形态门放行。它没有：

- 调用 parser / 上游拿到 conditions
- 读任何 robot 文本
- 走进 `draft/judge.py`
- 对比旧/新 judge

HB009「李明的重疾险」变 F，只因为句子里有「重疾险」；HB015 `C000888123456` 变 F，只因为正则像单号。这是在测模拟器认不认自己的三类形状，不是在测判定改完以后系统怎么办。

若把 18/18 写成「改判定已经过了」，010 刚钉死的第二扇闸会再次变成摆设：集 B 有文件，但没有评测。

### 根因层

测量对象被换成了叠加器自己。集 B 现在只有 query + 期望，没有被评估输出。没有 live，任何「评测分数」都只能是程序自洽。

4A 仍然对：先有独立集 B。缺的是 live 和一次真正的 judge。本轮章程禁止重跑 LLM judge，所以本轮只能报告「未测」，不能报告「已过」。

### 和 010 / 016 / 017 的边界

- 010：缺集 B。4A 已经造了文件。本 issue 不重开「要不要集 B」。
- 016 / 017：集 A 上的回退和残留，用的是真实 xlsx 里的当前状态 + 叠加。那两份数字可以讨论对错。
- 本 issue：集 B 的 18/18 两口径都不能当通过证据，无论 016 / 017 怎么判。

### 不是什么

- 不是说集 B 造坏了，也不是要从 341 里挑「看起来正常」的来扩。
- 不是要求本轮偷偷重跑 judge。
- 不是允许因为 18/18 就忽略 016 / 017 的集 A 问题。

### 可证伪修复

在报告和 Consensus 里必须写明：

1. 集 B 18/18 = 程序出口，不是 LLM 评测；
2. 1A 是否过集 B，要等这 18 条有 live 之后再跑 judge；
3. 在那之前，不得用 341 准确率或这 18/18 当发版 KPI。

本轮不采集 live、不改 judge。本 issue 在「未测」被写进共识之前保持 open。

## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 24595086899233c3
- pid: 84897

### Investigation
Independent rerun of `python3 issues/trace/simulate_1a_name_program.py` produced `set_b_wide_f=18`, `set_b_surname_f=18`, `set_b_surname_miss=[]`. That matches the dump, which already notes: “Set B has no live/judge traces. Scores are program exits, not LLM judge reruns.” (`simulate_1a_name_program.py` L327).

I re-read `impl/projects/client_search/draft/cases/head_set_b.json`:

- 18 frozen constructed cases: bare_name 8, name_plus_product 6, legal_id 4.
- Every `expected_status` is `fulfilled`.
- Case keys are only `id/class/query/expected_status/expected_live_field(s)`. There is no live request, no conditions, no old/new judge, no trace.
- `expected_live_field` is a wish-list, not an observed parse.

`load_set_b` (L120–136) forces `current=None`, `fields=[]`, `values=[]`, `source="set_b"`. Then both exits take the set B branch (L195–201, L216–222):

- whole-query 2–4 Han → F (wide) or F iff `has_surname_shape` (surname)
- else `PRODUCT_HINT` 重疾|年金|两全|医疗险|增额寿|增额 → F
- else `ID_TOKEN` → F

My per-row reasons (not the dump’s summary):

- HB001–HB008 李明/张伟/王芳/陈静/周婷婷/吴志强/马文博/欧阳文博: `BARE_NAME` + surname/compound. Surname overlay would also F them. This set cannot speak to 昊轩 (二字无姓).
- HB009–HB014: F only because the query string contains 重疾/年金/两全/医疗险/增额寿/重疾. No product field was ever parsed.
- HB015–HB018: F only because `ID_TOKEN` matches `C000888123456` / `P01000008888888` / `PC2100A399900001` / `C000777123456`. No `clientNo`/`polNo` live.

Parked set A rows were not used as set B. Set B was not sampled from the 341 xlsx.

### Reasoning
Charter §2’s second gate is “set B head F must not drop.” “Not drop” needs a before/after on an evaluated output. Set B has no current judge status, so there is nothing to drop from and nothing a real judge was seen to keep.

Charter §5 already requires: if set B has no live/judge traces, say so; do not pretend an LLM judge ran. Charter §6 forbids re-running the LLM judge this round. Therefore the only legal statement is: the overlay’s own three shape-doors accept these 18 strings. The illegal statement is: 1A has been evaluated on set B and may ship.

010’s dual-gate is a conjunction. Using this 18/18 to green-light 016 or 017 would turn the set B file into scenery. 016/017 set A numbers are current-xlsx + overlay and can be argued. These set B numbers cannot.

I am not saying set B is badly constructed, and I am not asking this round to collect live or rerun judge. I am saying 18/18 is not an eval score.

### Improvement Proposal
**Problem**: Both overlays print set B 18/18, but that number is the simulator accepting its own query shapes, not a post-change judge evaluation.

**Proposed Change**: Consensus / any report that cites this simulation must state all three of the following. No code change.

**Design** (required wording, ready to insert):
1. 集 B 18/18 = 程序出口（`exit_wide` / `exit_surname` 的 `source=="set_b"` 分支），不是 LLM judge 评测。
2. 1A 是否通过集 B 头部 F 地板：要等 HB001–HB018 有 live/conditions 之后再跑 judge；在那之前集 B 闸的状态是「未测」，不是「已过」。
3. 发版 KPI 不得使用 341 准确率，也不得使用这次 18/18。Canvas / 过严 8 条同样不是 oracle。

**Implementation Steps**:
1. Write the three sentences into Consensus when 016/017 are closed or parked.
2. Keep `head_set_b.json` frozen and read-only this round.
3. Do not collect live, do not import `draft/judge.py`, do not treat missing=[] as a pass.

**Risks**: Leaving “18/18 F” in a summary table without the 未测 gloss. The dump note is not enough if Consensus only copies the integer.

**Verification**:
```bash
python3 -c "
import json
from pathlib import Path
b=json.loads(Path('impl/projects/client_search/draft/cases/head_set_b.json').read_text())
d=json.loads(Path('issues/trace/simulate_1a_name_program.json').read_text())
print('set_b_keys', sorted({k for c in b['cases'] for k in c}))
print('note', d['set_b']['note'])
print('wide', d['set_b']['wide'])
print('surname', d['set_b']['surname'])
"
```

Pass condition for this issue: Consensus contains 「未测」 for set B. The script printing 18/18 does not close it.

**Why I Cannot Apply It**: Read-only; this is a reporting/consensus constraint. Collecting live is outside charter §6 and outside this peer.

## Consensus
**Verdict**: real-problem

双方独立重读集 B 文件并重跑模拟：18/18 F 两口径都成立，但集 B 只有问句和期望，没有 live、没有 conditions、没有 judge 痕迹。`expected_live_field` 是愿望字段，不是解析结果。

写入本共识，避免 18/18 被当成评测通过：

1. 集 B 18/18 = 程序出口，不是 LLM judge 评测。
2. 1A 是否通过集 B 头部 F 地板：要等 HB001–HB018 有 live 之后再跑 judge；在那之前集 B 闸的状态是**未测**，不是已过。
3. 发版 KPI 不得使用 341 准确率，也不得使用这次 18/18。

本轮不采集 live、不重跑 judge。010 的双闸仍在：没有集 B 真评测，不能发版。
