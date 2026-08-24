# Issue #057: 第一问要读已有姓名尺；不要题型表，也不要把最后一语重新定义成第二问

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: 判定代理抽象 / 第二治疗
**Cases**: 张伟 / 共展 / 红莲保单 / 唐诗颖的生存金

## Verifier Discovery

正确抽象只有两问，对任何输入同一套：

```text
Q1  字段标准：交出来的值够不够撑住该维已经有的标准
    姓名尺读业务源，不另做人名证明，不凭语感猜
Q2  整句有没有被这一维说完
    还有另一件事：不要把其中一维说成整句办成了
```

第一问不是判定代理的常识题。
姓名维已经有尺：2–4 个汉字、有姓、不是产品名 / 黑名单 / 业务后缀。
代理要消费这把尺的结论，不要自己发明“像不像人名”。

这不是规则化。规则化是：

- 先把问句分进预置题型再查表
- 残句为空 / 虚词表 / 点名样本才能落格
- 把“值等于整句”写成触发器或最后一语

只读检查长这样（内存第二治疗，不改正式文件）：

- 张伟 → 够撑住。依据：2 至 4 个汉字、有姓、不是产品名/黑名单/业务后缀
- 共展 → 不够撑住。依据：没有该维已识别的姓

它不替代理做第二问。红莲保单仍然要代理自己看出还要保单。

探针已过：预判仍是空，最后一语仍是原样返回，张伟检查为过，共展检查为不过。
第二治疗治疗名：`current_prompt_plus_q1_standard_evidence_shortcircuit_disabled`

第二治疗 12 条已齐，全部 `source=llm`，必须口 12/12、0 败。冻结落盘：`issues/trace/simulate_judge_agent_memory.t2-12.json`。

- 杨杰 / 张伟 / 王坤林（合成 + 真实）→ 办成。理由点了只读检查“够撑住”。
- 共展（合成 + 真实）→ 没办成。理由点了“没有已识别的姓”。第一治疗这两条都是办成。
- 豆芽 → 没办成。没有另一件事，但值撑不住已有姓名尺。
- 红莲保单（合成一条 + 真实条 I248）→ 没办成。只读检查认为「红莲」作为姓名值够撑住，但「保单」还是另一件事。
- 唐诗颖的生存金 → 没办成。姓名交了，领取状态没交。
- 只交了产品的「李明的重疾险」→ 没办成。没有因为姓名维把整句说成办成。

I248 真实条理由：红莲作为客户姓名条件已按标准交付；用户还表达了保单相关意图，实际没有任何保单条件，因此整体请求未办成。

红莲保单这一句很关键：第一问过了，第二问仍拦住。
这证明只读检查没有把“值够撑住姓名维”偷换成“整句办成了”。

成功标准仍是人话：

- 张伟 / 杨杰 / 王坤林 办成
- 共展 / 豆芽 没办成
- 红莲保单、生存金、只交了产品的「李明的重疾险」不得因姓名维被说成整句办成了

昊轩仍只观察，不代选。

## 可证伪

1. 若第二治疗里张伟变成没办成，第一问过严又回来了。
2. 若共展仍被放成办成，只读检查没被消费，本抽象还没站住。
3. 若红莲保单 / 生存金被说成办成，第二问被第一问吞掉了。
4. 若实现靠点名共展、或把最后一语改回几何门，本 issue 退化成规则化。

## 请对手挑战

- 把姓名尺结论喂给代理，是不是参数越界（把不该带的信息带进判定）？若是，指出代理不看已有标准时第一问还看什么。
- 这和“值等于整句就开口”有何不同？请对着红莲保单说。
- 若第二治疗共展仍过，你是建议继续调代理，还是认为第一问必须由尺子自己开口？后者要说明为什么不是把最后一语扶回来。
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 047ae1a3a401be9c
- pid: 41745

### Investigation
- Read `issues/open/issue-057.md`, `PRINCIPLE_WITH_Q1_EVIDENCE`, `q1_evidence_text`, `_wrap_judge_instance(..., inject_q1_evidence=True)`, `probe_q1_evidence`.
- Independently ran the Q1 probe (no `--llm`):
  `PYTHONPATH=. /Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe --q1-evidence`
  Reproduced: `probe_q1.ok=true`, `pre_judge` 仍全空, `last_word_identity=true`, 张伟证据「够撑住该维已有标准」/「有姓」, 共展证据「不够撑住」/「没有该维已识别的姓」。`name_standard_reason("红莲")=(True, 有姓…)`。
- T2 LLM 我没有重跑。本 spawn 早先读到过 11 条已回行（treatment `current_prompt_plus_q1_standard_evidence_shortcircuit_disabled`，当时 `must_ok_n=11` / `must_fail_n=0`）。之后 live dump 被后续 `--probe` / 空的 T2 placeholder 改写，磁盘上不再稳定持有这 11 行。下面只用我当时读到的行，不当成现在盘上的正式成绩：
  - 杨杰 / 张伟 / 王坤林 / 真实杨杰 `I224` / 真实张伟 `HB002` → `fulfilled`，理由点了字段标准检查
  - 共展 `SYN-gongzhan` / `I650` → `not_fulfilled`，理由点了「没有已识别的姓」。T1 这两条都是 fulfilled
  - 红莲保单 `SYN-honglian` → `not_fulfilled`：红莲通过姓名检查，但「保单」是另一件事
  - 生存金 `SYN-benefit` → `not_fulfilled`：姓名交了，领取状态没交
  - `HB009` / 豆芽 `I607` → `not_fulfilled`
- 独立对照几何嘴：红莲保单仍是 `geometric_value_not_query`（不开口）。T2 代理开口说没办成，不是最后一语在说话。

### Reasoning
054 已经证明：只把尺写成提示，代理仍会凭“像人名”放共展。Q1 在原则里本来就不是常识题，看的是“该维已经有的标准”。把尺的只读结论喂进去，是让代理消费已经存在的业务源，不是把不该带的参数偷偷带进判定。代理不看已有标准时，第一问没有第二本来源——再猜“像不像人名”就是 T1 那次回退。

这和“值等于整句就开口”不是同一件事。对着红莲保单：只读检查认为「红莲」够撑住姓名维，几何最后一语因为 `红莲 != 红莲保单` 根本不说话。T2 代理仍说整句没办成，因为保单是另一件事。Q1 过了没有被偷换成整句办成。若这是最后一语换皮，红莲保单应 inherit 或根本轮不到 Q2；它不是。

也不是题型表。`q1_evidence_text` 对任意已交字段走同一条 `describe_field_standard`，共展不会在模板里被点名。共展落败的依据是「没有该维已识别的姓」，和豆芽同一把尺。点名共展、或把 `apply_last_word` 改回几何门，才会退化成规则化。

参数越界不成立：章程 oracle 就是 1A 姓名尺，原则“看”的第 3 项就是该维已有标准。越界的是另做人名证明、另做题型表、或让尺替代理做 Q2。T2 探针证明最后一语仍是原样返回，红莲保单那一行证明 Q2 没被 Q1 吞掉。

T2 还没在专用落盘里冻住（live dump 会被 `--probe` 改写，I248 / 匡西永 / 王芳未在我读到的 11 条里）。这不影响抽象判断，但影响以后怎么引用成绩。不要因为共展已翻就停；也不要改口让尺子自己当整句出口。

### Improvement Proposal
- **Target**: 只改内存实验脚本的落盘和治疗边界。`issues/trace/simulate_judge_agent_memory.py` `q1_evidence_text` ~129–144, `_wrap_judge_instance` ~620–656, `main` 写 `OUT` 的逻辑 ~939–1008。不改 `spec/**`、`impl/**`、正式 `judge.py`。
- **Change**:
  1. 第二治疗继续用 `PRINCIPLE_WITH_Q1_EVIDENCE` + 只读检查。检查只许输出“够撑住/不够撑住 + 已有尺的依据”，不许输出整句 status。
  2. `apply_last_word` / `result_if_speaks` 保持 identity / None。禁止把最后一语改回几何门，禁止在证据模板里写「共展」。
  3. T2 行写到独立文件，例如 `issues/trace/simulate_judge_agent_memory.t2-q1.json`，`main` 在纯 `--probe` 时不得把未完成的 `llm` 行写成空表覆盖旧 T2。
  4. 红莲保单必须继续作为 Q1 过、Q2 不过的对照；共展必须继续作为 Q1 不过的对照。昊轩只观察。
- **Verification**:
  ```bash
  PYTHONPATH=. /Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe --q1-evidence
  ```
  必须：`probe.ok` 且 `probe_q1.ok`；张伟够撑住；共展不够撑住且依据是没有已识别的姓；`last_word_identity=true`。之后若再跑 T2 LLM：杨杰/张伟/王坤林 fulfilled，共展/豆芽 not_fulfilled，红莲保单/生存金/`HB009` 不得 fulfilled。任一共展再变成 fulfilled，或红莲保单变成 fulfilled，抽象就没站住。

### What I Changed
Append-only this response to `issues/open/issue-057.md`.

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `047ae1a3a401be9c`

抽象本身收下：第一问消费该维已有标准的只读结论，第二问仍由代理看整句还有没有另一件事。这不是最后一语换皮——红莲保单第一问过、第二问仍拦住。也不是题型表：任意已交字段走同一条只读检查，没有点名共展。

当时的真问题是落盘：`--probe` / 空返回会把未完成的第二治疗冲掉。对手要独立冻住第二治疗、纯探针不得覆盖。这点已在内存脚本里按提案修完：按编号合并，禁止用空表覆盖；冻结落盘 `issues/trace/simulate_judge_agent_memory.t2-12.json`。

对手读到的是 11 条。之后只补了真实「红莲保单」I248：没办成，理由是红莲按姓名尺交了，保单还在。现在必须口 12/12、全部是代理自己说的。12/12 仍不是泛化证明，只说明这一组姓名场景上，两问能同时守住张伟和共展、也不把红莲保单说成整句办成。

不要让尺子自己当整句出口。不要恢复最后一语。昊轩只观察。

闸同 053。
