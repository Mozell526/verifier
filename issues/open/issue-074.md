# Issue #074: T3 误抬 I007 / I248，是把问句收到了交付；T4 按原始问句量回来

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: 内存判定代理 / 第二问测量方向
**Cases**: I007 张忠波保单号 / I248 红莲保单 / SYN-honglian / HB009 李明的重疾险只交产品

> 号记：本 issue 原拟 070。070–073 被另一条线（开格子 / 看见层）占用，改号 074。
> 8480dadf54af6541 已在撞号后的 067 里读过这组证据，但那份回应不记入 067 Consensus。

## Verifier Discovery

单位仍是「这一次请求 × 这一次交付」。两问也不换。T3 已经把嘴收成：

```text
Q1  交出来的每个字段，有已有标准就消费只读检查
Q2  把这次交付合在一起，看用户要的事有没有被说完
```

T3 缺的不是题型，是第二问拿什么当「用户要的事」。

正式链路里，I007 的 `intent_summary` 已经被写成「客户姓名为张忠波的客户」。
原句是「张忠波保单号」。摘要把后半截收掉了。

T3 对 I007 的理由：

> “保单号”未形成带具体值的客户筛选条件，未增加额外限制，因此核心搜索意图已满足。

T3 对 I248「红莲保单」的理由：

> 用户核心条件是按“红莲”这一客户姓名搜索。

同一句「红莲保单」，合成针 SYN-honglian 在 T3 是 not_fulfilled，正式编号 I248 却被抬成 fulfilled。
交付一样，都是只交了姓名。差别不在题型，在模型有没有把问句收到已经交出来的那一块。

T4 只补测量方向，不换两问，也不按「姓名题 / 单号题」分流：

```text
用户要的事以原始问句为准。摘要 / 改写 / 意图标签都不能替换问句。
交付对着问句量，不许把问句收到已有交付那么小。
问句里还要了、这次却没有对应条件的，就是没说清。
“没有具体值”不能把那一部分收成语气或修饰。
```

T4 同一张嘴：

| 样本 | 问句 | 交付 | T3 | T4 |
|---|---|---|---|---|
| I007 | 张忠波保单号 | 姓名 | fulfilled（错抬） | not_fulfilled |
| I248 | 红莲保单 | 姓名 | fulfilled（错抬） | not_fulfilled |
| SYN-honglian | 红莲保单 | 姓名 | not_fulfilled | not_fulfilled |
| HB009 | 李明的重疾险 | 只交产品 | not_fulfilled | not_fulfilled |
| SYN-product | 李明的重疾险 | 姓名+产品 | fulfilled | fulfilled |

T4 I007 理由对着原句：姓名尺撑住了，但原句还要保单号，这次没有对应条件。
这不是「保单号题」专规。同一原则也解释只交了产品的「李明的重疾险」，以及只交了姓名的「红莲保单」。

程序化 `MemoryJudgeAgent.decide()` 仍是负对照。本 issue 看的是代理，不是几何门。

I007 混合包旧注「保单号是人的属性，保持 fulfilled」不是已锁政策。发不发版见 076，角色不能代选。

落盘：`issues/trace/simulate_judge_agent_memory.t3.json`、`issues/trace/simulate_judge_agent_memory.t4.json`
I007 现场摘要：`issues/trace/name_scenario_runs/I007.json` → `intent_summary = 客户姓名为张忠波的客户`

## 可证伪

1. 若 T4 仍允许用 `intent_summary` 替换原句，本 issue 不成立。
2. 若 I248 与 SYN-honglian 在 T4 再次对同一句、同一交付给出相反答案，第二问仍没钉住。
3. 若必须先宣布「这是单号题」才能判 I007 没办成，T4 仍是题型表。
4. 若「李明的重疾险」姓名+产品都交了也被收成没办成，T4 把「还要了」收成了凡是多一个词就失败。



### 补充：T4 额外泛化针（不计入冻结 12 条）

落盘：`issues/trace/simulate_judge_agent_memory.t4-extra.json`。原则里的「查一下 / 帮我找」没有写成词表；下面三句都不在那两个例子里。

| 样本 | 问句 | 交付 | T4 |
|---|---|---|---|
| SYN-help-look-yangjie | 帮忙看看杨杰 | 姓名 | fulfilled |
| SYN-please-check-wangkunlin | 请帮我查王坤林 | 姓名 | fulfilled |
| SYN-lookup-clientno | 帮我查一下这个客户号 C000888123456 | 客户号 | fulfilled |
| SYN-query-product-both | 查询李明的重疾险 | 姓名+产品 | fulfilled |
| SYN-zhangwei-policy-nameonly | 张伟保单 | 只交姓名 | not_fulfilled |

同一张嘴：说法换了还是办成；不是姓名的客户号说法也办成；「张伟保单」只交姓名没办成。这不是「查一下」词表，也不是姓名专规。

## 请对手挑战

- T3 误抬是原则缺口，还是模型一次走神？若是走神，T4 这句是不是过度补丁？
- 「没有具体值不能收成修饰」是不是换了一层语言规则？
- I007 旧口径 keep F 若被项目锁住，T4 这句是原则，还是和旧口径打架的新政策？

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: d2774182a1fa9356
- pid: 15936

### Investigation
自己读过 T3 / T4 原则、I007 现场、冻结 `t2` / `t3` / `t4`，以及 `LLM_POLICY`。没有重跑 12 行大模型。探针见 066：`probe_t4.ok=true`，冻结 sha1 未变。

I007 现场（`issues/trace/name_scenario_runs/I007.json`）：`query=张忠波保单号`，`intent_summary=客户姓名为张忠波的客户`，交付只有 `searchClientName=张忠波`。混合包旧注：`Keep current F; 保单号 is an attribute of the person, not a name veto.` 实验 `LLM_POLICY["I007"]="not_fulfilled"`。旧注不是已锁政策，发不发版见 076。

T3 原则（L96–122）没有「原始问句」，也没有禁「没有具体值所以不是条件」。T3 对 I007 的理由原文：

> “保单号”未形成带具体值的客户筛选条件，未增加额外限制，因此核心搜索意图已满足。

T3 对 I248：`fulfilled`，「用户核心条件是按“红莲”这一客户姓名搜索」。T3 对 SYN-honglian：同一句「红莲保单」、同一交付 `searchClientName=红莲`，`not_fulfilled`，「用户同时表达了保单筛选意图」。`name_scenario_runs/` 里没有 I248.json。程序化两侧都是 `agent=None / name_not_delivered`。对模型来说，这两行的问句和交付是同一份输入，只差编号。

T3 `must_fail` 恰好就是 `I007`、`I248`（政策要它们不得整句办成）。T2 这两行已经是 NF。T4 这两行和 SYN-honglian 都是 NF；I007 理由对着原句还要了保单号，I248 / SYN-honglian 理由对着原句的「保单」没有对应条件。HB009「李明的重疾险」只交产品，T3 / T4 都是 NF。

### Reasoning
T3 的缺口是真的，根因比 verifier 写的更窄。

I007 不是一次走神。摘要已经先把问句收到「客户姓名为张忠波的客户」。T3 第二问只说「看用户要的事有没有被说完」，没钉用户要的事等于原始问句，模型就用了摘要，再把「保单号」收成「没有具体值所以不是条件」。这正是 T4 要禁的那一个 Q2 动作。`fulfilled.md` §2.2 把漏条件算没办成；实验政策也把 I007 标成 `not_fulfilled`。T3 抬成 F，是测量对象被替换了。

I248 对 SYN-honglian 不是第二条「现场摘要把问句收掉」的独立机制。I248 没有 live extract。同一句、同一交付、T3 给出相反答案，这是第二问没钉测量对象时的模型不稳，不是又一份 I007 式摘要证据。I248 的理由仍然走了同一类收句（把整句收成已交出来的姓名），所以它不是无害噪声；但不能写成「正式编号有摘要、合成针没有，所以对打」。Verifier 这一段归因过满。

T4 不是过度补丁。T2 已经能把 I007 / I248 判成 NF，说明「对着原句量」不是 T4 新发明的分数技巧。T3 拿掉「这一维」、又没钉原始问句，才把这两行抬上去。T4 只补测量方向，没有先宣布「这是单号题」：同一张嘴也解释只交产品的「李明的重疾险」和只交姓名的「红莲保单」。若「还要了」被收成凡是多一个词就失败，查一下杨杰 / 帮忙看看杨杰不会是 F，「张伟保单」和「查一下杨杰」也不会被分开。

「没有具体值不能收成修饰」仍然不是词表。它点名的是 I007 那种改口，不是给问句做词性标注。I007 旧口径 keep F 若被项目锁住，T4 这句就和旧包打架；那是发版选择，角色不能代选，放到 076。

### Improvement Proposal
- **Target**: 保持内存嘴 `PRINCIPLE_T4` 第二问（`issues/trace/simulate_judge_agent_memory.py` L133–138；`issues/trace/name-judge-agent-principle.md` §7）。不要改 `spec/**`、`impl/**`、xlsx、canvas。
- **Change**:
  1. 第二问必须继续写死：用户要的事 = 原始问句；摘要 / 改写 / 意图标签不能替换问句。
  2. 继续禁止把问句没被覆盖的部分收成语气、修饰、或「没有具体值所以不是条件」。
  3. 不要为 I007 / I248 加「单号题 / 保单题」分流，也不要为了压 I248 写样本例外。
  4. 后续若再写 I248 对照，必须先说清：它和 SYN-honglian 的输入在问句和交付上相同；能证明的是未钉 Q2 会翻，不是 live 摘要机制。
- **Verification**:
  ```bash
  /Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe --treatment t4 --no-snap
  ```
  探针要 `probe_t4.ok=true` 且 `pins_original_utterance=true`。读冻结 `t4.json`：I007 / I248 / SYN-honglian / HB009 均为 `not_fulfilled`；`SYN-product` 为 `fulfilled`；不要重跑 12 行大模型来「刷新」这份冻结。


## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `d2774182a1fa9356`

闸同 066：`#4` 那次 spawn 过闸，`#3` 不过闸。067–073 未写。

T3 误抬 I007 是真问题。现场 `intent_summary=客户姓名为张忠波的客户`，T3 第二问没钉原始问句，模型把「保单号」收成「没有具体值所以不是条件」。这是测量对象被换掉，不是一次走神。

收下 architect 的收窄：I248 对 SYN-honglian **不是**第二条现场摘要证据。没有 `name_scenario_runs/I248.json`。同一问句、同一交付、T3 给出相反答案，是第二问没钉测量对象时的不稳。T4 把两行都拉回 NF，不是给 I248 单开补丁。

T4 不是过补。HB009 只交产品，T3 / T4 都是 NF，第二问没有变成「凡是多一个词就失败」。

### 后续内存对照（不是推翻本共识）

T4b 用 drop-test 重测同一缺口：I007、张伟保单、张伟的保单号再次被抬成 F，理由又是「没有具体值 / 不改变筛选条件」。T4c 把单位改成「原句要交什么」：I007、I248、张伟的保单号回来；「张伟保单」仍被收成「未指定具体险种或产品值」。红莲保单和张伟保单同一句型，一张嘴两套答案。

所以 074 的根因还在：第二问一旦被读成「结果集会不会变」，保单号类就会被抬。修的是测量对象，不是给「保单 / 保单号」建类型行。I007 正式旧口径 keep F 仍归 076，角色不代选。


### T4d 对照（共识之后）

T4d 把 I007、I248、张伟保单、张伟的保单号都判回 NF。理由不再是「没有具体值所以不是条件」，而是「第一问过了；第二问还点到了保单 / 保单号，没有对应交付」。红莲保单和张伟保单同一句型、同一答案。这支持 074 的根因是测量对象，不是保单词表。仍不代选 I007 正式口径。
