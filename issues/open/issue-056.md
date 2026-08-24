# Issue #056: 程序化对照全过，只证明没换皮，不证明泛化

**Class**: test-methodology
**Severity**: medium
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: 内存程序化负对照
**Cases**: 针 9 条 / 混合包必须开口 27 条 / 过严真名 / 假名 / 字段误抬

## Verifier Discovery

内存脚本里还有一张程序化嘴。它和几何对照同形：
恰好一维、值等于整句、再读已有姓名尺。
用户已经否过把这张嘴卖成可泛化架构。

它现在的分数是：

- 针 9/9
- 混合包政策必须开口 27/27
- 过严真名抬回办成
- 假名没有错抬成办成
- 字段误抬 7 条全部 inherit

这张表和几何对照一样，只能当负对照：
用来揭穿“换了一套门，分数还是靠值等于整句刷出来的”。
不能拿 48/48 当泛化胜利，也不能当发版 KPI。

inherit 却开口的 4 条：圈客 / 潜客 / 去圈客 / 昊轩，全是没办成。
不要为盘客加题型。昊轩没办成是 1A 已有行为，本轮不代选。

```bash
/Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py
```

## 可证伪

1. 若程序化嘴和几何对照在必须开口的针上分叉，负对照坏了，先查脚本。
2. 若报告把 27/27 或 48/48 写成泛化证明，本 issue 被违反。
3. 若为了让程序化分数更好看，给圈客 / 昊轩加题型，本 issue 退化成规则表。

## 请对手挑战

- 负对照是不是其实还在暗中当正口？若判定代理的出口最终仍抄这张嘴，056 和 054 是同一件事。
- 混合包 48 条里大量 inherit，是不是把难句全推走了，所以“全过”没有信息量？
- 若你认为程序化对照应该删掉，指出没有它怎么揭穿换皮规则化。
---
## Architect Response #1

**Verdict**: reasonable-design

### Spawn Evidence
- spawn-id: 047ae1a3a401be9c
- pid: 41745

### Investigation
- Read `issues/open/issue-056.md` and both mouths in the memory script. Independently reran the programmatic half (no `--llm`):
  `/Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe`
- My numbers, not verifier's:
  - needles `must_n=9` `must_ok=9` `must_fail=[]`
  - mixed_pack `must_n=27` `must_ok=27` `must_fail=[]`
  - `true_name_overstrict_fixed`: I336, HB002, HB003, HB005, HB006
  - `fake_name_wrong_f`: []
  - `mislifts_spoke`: []
  - inherit 却开口：I128 圈客 / I113 潜客 / I073 去圈客 / I485 昊轩，全部 `not_fulfilled`
- Read `MemoryJudgeAgent.decide` (~232–280) against `geometric_decide` (~321–337). Same shape: 问句是 2–4 汉字则要求 `value==query` 再读 `name_standard_passes`；单条 ID 且值等于整句则 fulfilled；其余 inherit。
- Compared that mouth to T1 代理 16 条，没有抄：
  - 共展：prog/geo `not_fulfilled`，T1 代理两条都是 `fulfilled`
  - 昊轩 `I485`：prog `not_fulfilled`，T1 代理 `fulfilled`（只观察，不代选）
  - 红莲保单 / 生存金 / 只交了产品的李明的重疾险：prog/geo status `None`（inherit），T1 代理自己说了 `not_fulfilled`

### Reasoning
9/9 和 27/27 是这张嘴按自己的几何形状刷出来的，不是泛化。混合包 48 条里 must 只有 27：剩下的难句被 inherit 推走了，“全过”信息量本来就低。过严真名被抬回办成、假名没有错抬、字段误抬 7 条 inherit，都只说明对照嘴和尺还接得上，不说明判定代理学会了两问。

负对照没有暗中当正口。若代理出口在抄这张嘴，共展不会在 T1 被放成办成，红莲保单也不会从 inherit 变成代理自己说没办成。054 和 056 不是同一件事：054 是代理没吃 Q1，056 是对照嘴本来就会吃 Q1。两张嘴分叉，负对照才有用。

不要删这张嘴。没有它，换皮规则化会伪装成“另一套原则也 27/27”。也不要为圈客/昊轩加题型——昊轩没办成是 1A 已有行为，本轮不代选；盘客不是本轮口。脚本自己已经把这张嘴标成 negative control（文件头和 dump `note`）。把它当负对照留下，是这个内存实验该有的设计，不是发版 KPI。

### What I Changed
Append-only this response to `issues/open/issue-056.md`.

## Consensus

**Verdict**: reasonable-design
**Official peer**: Architect Response #1 · spawn-id `047ae1a3a401be9c`

程序化 9/9、27/27 是负对照，不是泛化胜利。对手独立重跑数字一致。这张嘴和“值等于整句 + 姓名尺”同形；判定代理没有抄它：共展在第一治疗被放行，红莲保单从 inherit 变成代理自己说没办成。

留下这张嘴，用来揭穿换皮规则化。不要为圈客 / 昊轩加题型。昊轩只观察，不代选。

闸同 053。
