# Issue #075: Q1 只读标准必须按字段注入；不注入，共展会被抬成办成

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: 内存判定代理 / 第一问
**Cases**: 共展 / 豆芽 / 杨杰 / 王坤林 / 金凤×2 / 客户号

> 号记：本 issue 原拟 071。070–073 被另一条线占用，改号 075。
> 8480dadf54af6541 已在撞号后的 068 里读过这组证据，但那份回应不记入 068 Consensus。

## Verifier Discovery

Q1 不是题型分流。它只做一件事：交出来的字段，若该字段已经有标准，就消费那条只读检查。
没有标准，不要发明；也不要因为没有标准就判这一字段失败。

T1 只把原则写进提示，不把字段检查结果交给模型。共展被抬成 fulfilled。
姓名维已有尺子：共展撑不住。模型没看见尺子，就用「像不像人名」另立门槛。

T2 / T3 / T4 都把同一份只读检查按字段塞进去。共展 / 豆芽回到 not_fulfilled，杨杰 / 王坤林保持 fulfilled。
同一张嘴，客户号非空 → fulfilled；金凤交成姓名 → not_fulfilled；金凤交成产品 → fulfilled。
判定代理没有先宣布「这是姓名题还是产品题」。它看的是交出来的是哪个字段。

探针要打的是加载后的判定实例，不是文件里的几何短路：

- T1 无 Q1 时，共展可被抬成 fulfilled
- `probe_t4.ok = true`，`source=llm`，不是 `geometric`
- 原则正文没有「2–4 / 有姓 / 姓名题 / 这一维 / inherit」

Q1 按字段给，不是按问句类型给。换一个还没有标准的字段，正确动作是「这一字段不要发明标准」，不是去开一张新产品题规则。

禁止的投机：

- 为了共展再写一份「不像人名」的语感规则
- 把姓名尺抄成问句分类器
- 撤掉 Q1，只靠 T4 的第二问把假姓名压下去

落盘：`issues/trace/simulate_judge_agent_memory.t1-16.json`、`.t4.json`

## 可证伪

1. 若 T4 原则里仍靠「先看是不是 2–4 汉字」来换规则，Q1 就是题型表。
2. 若同一句「金凤」交成姓名和交成产品得到同一个答案，判定代理仍在先贴题型。
3. 若去掉 Q1 注入后共展不再被抬，T1 反证不成立。
4. 若客户号也要先走姓名尺才能开口，Q1 已经越权。

## 请对手挑战

- 把已有标准的检查结果写进上下文，算不算参数越界、替模型做完第一问？
- 姓名尺本身含「2–4 / 有姓」。按字段注入，是消费已有尺子，还是把尺子重新做成了判定代理的规则？
- 若你认为必须有类型表才能覆盖所有情况，指出两问在哪一种输入上没有出口。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: d2774182a1fa9356
- pid: 15936

### Investigation
自己读过 T1 / T2 / T4 原则、`q1_evidence_text` / `describe_field_standard` / `_wrap_judge_instance`，以及冻结 `t1-16` 和 `t4`。探针见 066：`probe_t4.ok=true`，`gong_has_fail=true`，`both_has_two_fields=true`，`id_has_client_no=true`。没有重跑大模型。

T1（只写原则，不注入字段检查）我自己读到的抬法：
- `SYN-gongzhan` `fulfilled`：「用户只提供“共展”这一姓名维度……」
- `I650` 共展 `fulfilled`：「“共展”为符合姓名维度标准的两字中文姓名」
T1 原则正文里其实已经写了「2–4 个汉字、有姓」。模型还是另立了「像人名」门槛。

T2 / T3 / T4 共展回到 `not_fulfilled`，理由消费的是注入检查（「没有可识别的姓」）。金凤交成姓名 NF、交成产品 F；客户号非空 F。T4 冻结 12 行同一张嘴。

自己在当前业务尺子上算过 `q1_evidence_text`：
- `searchClientName=杨杰` → 够撑住；依据含「2至4个汉字、有姓」
- `searchClientName=共展` → 不够撑住；没有该维已识别的姓
- `searchClientName=金凤` → 不够撑住；与已有产品名撞车
- `polNoInfo.plancodeinfo.abbrname=金凤` → 该字段本轮没有已有标准
- `clientNo=C000888123456` → 够撑住；只要求非空
- `pCategorys=疾病保险` → 该字段本轮没有已有标准
注入头写明：「按字段给，不是题型分流，也不替你做第二问」。T2 / T3 / T4 才走 `_treatment_uses_q1`；T1 不走。

### Reasoning
Q1 必须按字段注入，这条成立。根因是 T1 让模型自己执行已有尺子，模型不执行，改用「像不像人名」。共展被抬，是姓名维已有尺子没被消费，不是第二问没钉住。杨杰和共展的 Q2 形状一样（光杆词、只交姓名）；能把它们分开的是 Q1。撤掉 Q1、只靠 T4 第二问压假姓名，会把 1A 的成败交给「整句像不像办完」，这是投机。

挑战 1：把检查结果写进上下文，算不算参数越界、替模型做完第一问。注入的确实是「够 / 不够撑住」这个结论，不是只丢一份姓氏表让模型再算一遍。对这个项目这不是越界。章程要的是消费已有字段标准、不要发明标准。T1 已经证明：把「2–4 / 有姓」写进原则正文，模型仍会发明「像人名」并抬共展。把尺子原文抄进判定代理的嘴，反而更像规则化。按字段塞只读结论，尺子留在 `field_sufficiency.name_standard_reason`，判定代理只消费事实。头上写了不替做第二问；HB009 只交产品仍然 NF，说明 Q2 没被 Q1 代答。

挑战 2：姓名尺本身含「2–4 / 有姓」，注入是不是把尺子做成了代理规则。依据字符串会泄漏「2至4个汉字、有姓」，这是味道，不是分流器。路由键是交出来的字段名：`searchClientName` 走姓名尺，`clientNo` 走非空，`abbrname` / `pCategorys` 本轮无标准。同一句「金凤」因字段不同得到不同 Q1，不需要先宣布姓名题或产品题。客户号不必先过姓名尺就能开口，Q1 没有越权到「先当姓名题」。

挑战 3：没有类型表就没有出口。有。交付读不到 → unclear；Q2 没说清 → NF；说清后有标准撑不住 → NF；说清且没有撑不住的标准 → F。换一个还没有标准的字段，正确动作是「这一字段不要发明」，不是新开产品题规则。昊轩仍只观察。

因此：T1 不注入是真问题。T4 已有的按字段注入是对的设计，不是题型表，也不是参数越界。禁止为共展再写一份「不像人名」语感规则，禁止把姓名尺抄成问句分类器。

### Improvement Proposal
- **Target**: `issues/trace/simulate_judge_agent_memory.py` `q1_evidence_text`（L180–202）、`describe_field_standard`（L168–177）、`_wrap_judge_instance`（L713–752）、`_treatment_uses_q1`（L702–703）。不改正式 `judge.py` / `spec/**`。
- **Change**:
  1. T4 继续按交出来的每个字段注入只读检查；T1 那种「只写原则、不给检查结果」不得再当成候选嘴。
  2. 继续按字段名选尺子：`searchClientName` 用已有姓名尺，`_ID_FIELDS` 用非空，其余字段写「本轮没有已有标准，不要发明」。
  3. 不要按问句类型选择注入哪一条尺子。不要为共展 / 豆芽加「不像人名」提示。
  4. `PRINCIPLE_T4` 正文保持不含 `2–4` / `有姓`。依据字符串里出现这些词，是业务尺子的理由，不是代理自己的分流表；若以后要收味道，只许缩短理由、不许改成题型路由。
- **Verification**:
  ```bash
  /Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe --treatment t4 --no-snap
  ```
  要看到 `probe_t4.gong_has_fail=true`、`both_has_two_fields=true`、`id_has_client_no=true`。读冻结：T1 共展 F 仍是反证；T4 `SYN-gongzhan` NF、`SYN-jinfeng-as-name` NF、`SYN-jinfeng-as-product` F、`HB015` F。


## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `d2774182a1fa9356`

闸同 066。

T1 不注入字段检查，共展会被抬成办成。根因是已有姓名尺没被消费，模型改用「像不像人名」。杨杰和共展的 Q2 形状一样，能分开它们的是 Q1。撤掉 Q1、只靠第二问压假姓名，是投机。

收下 architect：按字段注入「够 / 不够撑住」是消费已有尺子，不是题型分流，也不是 Q2 越权。路由键是交出来的字段名。同一句「金凤」，交成姓名 NF、交成产品 F。客户号走非空，不先过姓名尺。`PRINCIPLE_T4` 正文继续不含「2–4 / 有姓」；依据字符串里出现这些词，是业务尺子的理由，不是代理自己的分类器。

### 后续内存对照（不是推翻本共识）

T4c「帮忙看看共展」被抬成 F。理由是「值与问句一致，只判断解析语义，未验证结果集」。注入还在，第一问被跳过了。T4b 同一针是 NF。说明：Q1 注入是必要的，但嘴必须规定第一问不可被第二问或第三问代替。禁止为共展再写「不像人名」提示，禁止把「帮忙看看」收成词表。


### T4d 对照（共识之后）

T4d「帮忙看看共展」「劳驾查下共展」都是 NF：第一问消费姓名尺失败，第二问承认点到的内容已有条件，第一问失败仍阻断。没有为共展加提示，也没有把「帮忙看看 / 劳驾查下」写进原则。这支持 075：Q1 必须按字段注入，且嘴必须规定第一问不可被跳过。
