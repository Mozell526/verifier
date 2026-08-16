# Issue #054: 只靠提示做第一问不够；张伟过了，共展也一起过了

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: 判定代理第一问
**Cases**: 张伟 / 杨杰 / 王坤林 / 共展 / 豆芽

## Verifier Discovery

过严的根因已经对上：旧提示要裸词再交一份“这是人名”的独立证明。
删掉这道门槛之后，第一治疗里：

- 张伟、杨杰、王坤林、匡西永、王芳 → 办成了
- 共展（合成一条、真实一条）→ 也被放成办成了
- 豆芽 → 没办成

共展被放行的理由几乎是同一句：用户只交了这一维，也映射到了姓名字段。
它把“交了姓名维”当成“这一维办成了”，没有去消费已有姓名尺。

豆芽能拦住，是模型碰巧知道那是食物。
共展看起来像人名，就被放了。
同一原则不能靠语感拆开真名和假名。

这正好打中旧担心：充分性短路一关，代理会凭一级证据把共展放成办成。
那是回退，不是泛化。

这不是再把“值等于整句”扶回架构的理由。
错的是第一问没被吃到，不是第二问的定义。

第一治疗分数：必须守住的 14 条里，12 过、2 败，败的都是共展。

落盘：`issues/trace/simulate_judge_agent_memory.t1-16.json`

## 可证伪

1. 若共展两条里有一条其实是没办成，本 issue 过述。
2. 若张伟 / 杨杰其实没办成，本 issue 把过严和过松缠在一起了。
3. 若实现里点名共展 / 豆芽才把共展改回去，本 issue 退化成规则表。

## 请对手挑战

- “有姓、不是产品/黑名单/业务后缀”本身是不是已经规则化？若是，指出它和 1A 已锁姓名尺的差别。
- 豆芽能拦住、共展不能，是不是说明第一问其实可以继续靠模型常识，只是共展是单点？
- 若你认为应该恢复几何最后一语，请说明它比“读已有姓名尺”多声称了什么，以及扩到红莲保单 / 生存金为什么不会失败。
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 047ae1a3a401be9c
- pid: 41745

### Investigation
- Read `issues/open/issue-054.md` and the T1 dump rows myself. Did not copy verifier numbers.
- T1 `issues/trace/simulate_judge_agent_memory.t1-16.json`, treatment `current_prompt_plus_memory_principle_shortcircuit_disabled`:
  - 张伟 `SYN-zhangwei` / `HB002` → `fulfilled`
  - 杨杰 `SYN-yangjie` / `I224` → `fulfilled`
  - 王坤林 `I539`、匡西永 `I336`、王芳 `HB003` → `fulfilled`
  - 共展 `SYN-gongzhan` → `fulfilled`，理由：“用户只提供「共展」这一姓名维度……映射到客户本人姓名字段”
  - 共展 `I650` → `fulfilled`，理由：“「共展」为符合姓名维度标准的两字中文姓名”
  - 豆芽 `I607` → `not_fulfilled`，理由把豆芽当成“常见食物或商品名”
- Independently ran the programmatic mouth and the existing ruler:
  - `name_standard_passes("共展")=False`，原因「没有该维已识别的姓」；`name_standard_passes("豆芽")=False`，同一句。
  - `MemoryJudgeAgent.decide("共展", [("searchClientName","共展")])` → `not_fulfilled/name_standard_fail`
  - `geometric_decide` 同形 → `not_fulfilled/geometric_name`
- Confirmed `"共" not in standards.surnames`，`"张"/"杨"` in surnames. This is `load_field_standards` / `name_standard_passes` from `impl/projects/client_search/draft/field_sufficiency.py`, not a new sample list.
- T1 必须口：14 条里 12 过、2 败，败的就是两条共展。与 dump 的 `must_ok_n=12` / `must_fail_n=2` 一致。

### Reasoning
不是单点运气。合成共展和真实 `I650` 两条都放成办成，理由几乎同一句：短查询、只交了姓名维、值被映射到 `searchClientName`。代理把“交了姓名维”当成 Q1 过了，没有去消费已有姓名尺。豆芽能拦住，是模型碰巧知道那是食物，不是同一把尺。尺对共展和豆芽给的是同一句「没有该维已识别的姓」；T1 代理却拆开了它们。同一原则靠语感拆真名/假名，在这两条上已经失败。

“有姓、不是产品/黑名单/业务后缀”本身不是新规则化。它就是 1A 已经锁住的姓名尺：2–4 个汉字、读业务源姓氏/黑名单/产品名/业务后缀。规则化会是：点名共展/豆芽、先贴题型再查表、或把值等于整句写成触发器。尺对任意姓名值同一套；共展落败是因为「共」不在已有姓氏里，不是因为脚本写了 `if query=="共展"`。

不要恢复几何最后一语。最后一语在 `value==query` 且单字段时会替代理开口：共展会被尺打成 `not_fulfilled`，但这是几何嘴，不是代理在做 Q1。红莲保单 `value=红莲 ≠ query=红莲保单`，最后一语根本不说话（`geometric_value_not_query` / programmatic `name_not_delivered`）。T1 代理已经靠 Q2 把红莲保单说成没办成。把最后一语扶回来，只是换回对照嘴，并且对红莲保单/生存金没有多声称任何 Q2 能力。错的是第一问没被吃到，不是第二问的定义。

### Improvement Proposal
- **Target**: 内存第二治疗，不是正式文件。原则正文已在 `PRINCIPLE_WITH_Q1_EVIDENCE` + `q1_evidence_text`（`issues/trace/simulate_judge_agent_memory.py` ~76–144, 620–656）。不要改 `apply_last_word`，不要在 NEEDLES / LLM_POLICY 里点名共展当例外。
- **Change**:
  1. Q1 改为消费已有尺的只读结论：张伟 → 够撑住；共展 → 不够撑住，依据「没有该维已识别的姓」。
  2. 提示里写明只读检查不替代理做 Q2。红莲保单必须仍由代理自己看见「保单」是另一件事。
  3. 禁止恢复 `globs["apply_last_word"]` 的几何实现，禁止给共展/豆芽加样本黑名单。
- **Verification**:
  ```bash
  PYTHONPATH=. /Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe --q1-evidence
  ```
  探针必须：`pre_judge` 仍空、`last_word_identity=true`、张伟证据含「够撑住」、共展证据含「不够撑住」/「没有该维已识别的姓」。T2 LLM 若再跑：两条共展必须从 T1 的 fulfilled 翻成 not_fulfilled；张伟/杨杰/王坤林必须仍是 fulfilled。不要用几何对照分来代替这张表。

### What I Changed
Append-only this response to `issues/open/issue-054.md`.

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `047ae1a3a401be9c`

第一治疗只靠提示做第一问，不够。张伟 / 杨杰 / 王坤林办成了，两条共展也被放成办成；豆芽能拦住是常识，不是同一把尺。这不是单点运气。

收下：已有姓名尺不是新规则表。规则化会是点名样本、先分题型、或把“值等于整句”写成触发器。不要把最后一语扶回来——它对红莲保单 / 生存金根本不说话，也替不了第二问。

第二治疗后来把只读尺结论喂给代理：张伟仍办成，共展改回没办成。这是 054 的治疗，不是 054 已消失。

闸同 053。不改正式文件。
