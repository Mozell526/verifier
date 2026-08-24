# Issue #071: 承认「开格子是多一个标签」，不会让另外三个口复活

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 四个点名口 / 兄妹标签仍是兄妹
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

070 承认：开格子，在人看见的那一层就是结果上多一个标签。

用户点名的四个口是：

```text
A. 只是 not_fulfilled 的补充
B. 新增一个 judge 结果的标签
C. fulfilled 从 3 态扩到 4 态
D. 放到 not_evaluable 里面
```

本 issue 只钉：承认 070 之后，A / C / D 会不会因此变成合法宿主。不会。兄妹格上的标签，仍是兄妹，不是第一问三个词里的某一个，也不是第四个词。

### 第一问的嘴现在仍只有三个词

`spec/alg/fulfilled.md` §1：

> 本协议只评第一层：办成了没有。
> 「这类事现在是不是产品已经有的功能」见邻协议，不并进本协议三态，也不新增第四态。

同文件开篇：词表沿用 `spec/info-volume.md`，不新增第四态。

`spec/info-volume.md`：整体仍是 fulfilled / not_fulfilled / not_evaluable，不引入 partial；judge 只产出 fulfillment。

`impl/core/schema/judge.py`：`JudgeFulfillmentAssessmentOutput.status` 仍是一条状态。

所以 070 多出来的那一格字，若要保住第一问，就不能写进这条 status。写进去，就不是「旁边多一个标签」，是「原来那个标签换了词表」。

### 三个死口在 070 之后分别改写什么

| 点名口 | 070 之后若拿它当宿主 | 人看见的变成什么 | 踩哪条 |
|---|---|---|---|
| A. 只是 NF 补充 | 新标签只在没办成后面出现 | 办成了 × 没立住 这格从看见层消失；没办成被加上原因 | 062；fulfilled §2.2 不区分原因；authority §8.3 实际达成仍可 fulfilled |
| C. 3 扩 4 | 新标签变成 status 的第四个词 | 主表芯片、筛选、pill、矩阵 Status 同时多一种颜色 | 064；fulfilled §1；product-function §7.1 |
| D. 放进 NE | 新标签住进「说不清」 | 长期「没立住」被说成临时「判断不了」；办成了的正格被改口 | 063；fulfilled §2.3 临时态；authority_gate 能力缺失不得降 NE |

062 / 063 / 064 本轮不重开其对错。这里只核对：070 承认「多一个标签」，有没有把这三行改成「所以可以并进三个词」。没有。并进三个词，改的是第一问的嘴，不是给第二问开格子。

### 「用户只能看见 fulfilled」不能倒推回这三个口

现行出口确实只有第一问。061 / 048 已经把这件事收成看见问题：缺的是出口，不是定义。

070 之后，老实话是：

```text
若打开：人看见两个标签
        一个答办成了没有
        一个答产品把这件事立住了没有
若不开：人继续只看见第一个
```

把「现在只看见一个」兑换成「所以第二个必须住进第一个」，是 047 / 048 已经否过的倒推。070 只承认打开之后会多一个标签，不承认这个标签必须挤进已经存在的那一个。

### 不是什么

- 不是重开 062 / 063 / 064 的对错。
- 不是说 B 口因此整句复活。B 口里「判定再写一个词」仍按 072 另钉。
- 不是批准打开。

### 可证伪

承认 070 之后，A / C / D 仍能当宿主，要同时成立：

1. 结果上多一格字，必须写进已经存在的那一个 status；
2. 或者只在没办成 / 说不清后面才允许这格字出现；
3. 或者第四个词可以不改写办成了 / 没办成 / 说不清的含义。

1 把兄妹格收成改词表。2 把第二问单位改回「这一次没给到」。3 与 fulfilled §1、info-volume 三词归因切口、summary.html 四处同吃 status 直接撞。所以 070 成立，A / C / D 仍死。

## Proposed Change

Consensus 只锁：承认「开格子是结果上多一个标签」，不会让「只是 NF 补充 / 3 扩 4 / 放进 NE」复活。那个标签若打开，仍是第一问旁边的兄妹，不是三个词里的某一个，也不是第四个词。

不改 schema，不改前端，不宣布对外中文。


---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: c5e8ded5a0e2f031
- pid: 7902

**盘上正文冲突**：当前 `issue-071.md` 写的是另一条线（A/C/D 会不会因「多一个标签」复活）。本 spawn 把 071 分给：Q1 必须按字段注入已有标准，不是按题型分流；T1 抬共展是反例。下面只判这一句。

**Evidence Verification**:
自己重跑了 T4 探针，并在同一解释器里调用 `q1_evidence_text` / `MemoryJudgeAgent.decide`，没有抄 verifier 数字，没有重跑大模型。

T1 冻结（`current_prompt_plus_memory_principle_shortcircuit_disabled`）`SYN-gongzhan` → `fulfilled`。理由：「用户只提供“共展”这一姓名维度，实际输出原样提取该值并映射到客户本人姓名字段，使用支持的 MATCH，未缺失或增加其他条件。」T1 `must_fail` 含 I650 和 SYN-gongzhan。T2 / T3 / T4 共展都是 `not_fulfilled`，理由消费了「没有可识别的姓 / 没有该维已识别的姓」。

我算出的 Q1 证据（`q1_evidence_text`，`simulate_judge_agent_memory.py` L180–198）：

- `searchClientName=共展` → 「不够撑住…没有该维已识别的姓」
- `searchClientName=杨杰` → 「够撑住…2至4个汉字、有姓…」
- `searchClientName=金凤` → 「不够撑住…与已有产品名撞车」
- `abbrname=金凤` → 「该字段本轮没有已有标准检查。不要发明标准…」
- `searchClientName=李明` + `pCategorys=疾病保险` → 姓名够撑住；产品无标准、不要发明
- `clientNo=C000888123456` → 「够撑住…只要求值非空」

探针：T4 `gong_has_fail=true`，双字段证据里同时有两个字段名。`_wrap_judge_instance`（L713–751）只按 `delivered_pairs` 调 `describe_field_standard(field, value)`，不读题型、不读样本号、不读混合包角色。

**Reasoning**:
T1 已经证明：只把原则塞进 extras、不按字段给只读检查，模型会把「交了姓名维」当成「这一维办成了」。共展是 1A 钉子（杨杰 / 王坤林同侧成功，共展 / 豆芽仍失败）。T1 抬共展，不是边界噪声，是 Q1 没被消费。

注入姓名尺不是参数越权。姓名尺是该字段已经有的标准（`load_field_standards` / `name_standard_reason` L152–168），不是本轮新开的授权字段，也不是「这是姓名题」的分流。Q1 证据头已经写明：「按字段给，不是题型分流，也不替你做第二问。」同一句「金凤」，交成姓名和交成产品得到两条不同检查——这就是按字段，不是按问句类型。若是题型分流，金凤会先被标成姓名题或产品题，再换嘴；实际换的是交付字段。

把「不够撑住…依据：没有姓」写进 extras，确实是把 Q1 的答案递给模型。这是「消费只读标准」的机制，不是样本级答案。T1 证明原则文本 alone 不够。代理真正要做的是 Q2；Q1 本就不该另造尺子。越权会是：不管交了什么字段都灌姓名尺，或按样本 id 灌例外。现在不是。

红莲 / 张忠波的姓名值 Q1 都够撑住。所以 070 的整句 F 不能怪 Q1 注入；那是 Q2 收问句。071 只锁 Q1 的键是字段。

## Improvement Proposal

**Problem**: T1 不按字段注入已有标准，共展被抬成 fulfilled，1A 的假姓名钉被拆掉。
**Proposed Change**: 内存 T2/T3/T4 继续走 `q1_evidence_text` 按交付字段给只读检查。不要改成按问句类型选尺子，不要把姓名尺灌进没有姓名字段的交付。
**Design**:
```text
for field, value in delivered_pairs:
    check = describe_field_standard(field, value, standards)
    if check is None:  # 如 abbrname / pCategorys
        「没有已有标准；不要发明，也不要因此判这一字段失败」
    else:
        写出够撑住 / 不够撑住 + 该字段已有依据
```
`describe_field_standard` L171–177：只有 `_NAME_FIELD` 走姓名尺，`_ID_FIELDS` 走非空，其余 None。
**Implementation Steps**:
1. Consensus 锁：Q1 的键是交付字段，不是题型。T1 抬共展是反例。
2. 保持 `_treatment_uses_q1` 对 T2/T3/T4 为真（L703）。
3. 不要在原则里写「若问句像姓名题则…」。
**Risks**: 把 Q1 短文当成整句答案，重演 T3 收问句（070）。Q1 明说不替做第二问，必须留着。
**Verification**:
```bash
/Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe --treatment t4 --no-snap
```
要求 `probe_t4.ok=true`、`gong_has_fail=true`、`both_has_two_fields=true`、`id_has_client_no=true`。再断言冻结 T1 `SYN-gongzhan=fulfilled` 且 T4 `SYN-gongzhan=not_fulfilled`。不重跑大模型。
