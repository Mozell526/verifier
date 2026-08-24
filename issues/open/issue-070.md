# Issue #070: 开第二问自己的格子，人看见的结果上就是多一个标签

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: 看见层 / 开格子是不是新标签
**Cases**: 只作落点碰撞，不重判。

## Verifier Discovery

用户本轮打的是上一轮 065 那一句：

> 你要开第二问自己的格子，本质上不就是新增一个 judge 结果的标签吗？

065 Consensus 把「新增一个 judge 结果的标签」收成「同一轮判定再写一个词」，然后说旁边那一格「读者也许会叫它一个标签」，但「不是本轮点名的那个口」。

这一句答的是谁写。用户问的是人看见的是什么。两件事被焊成一句「所以不能叫标签」。焊完之后，开格子这件事在看见层被否认了。

号段说明：066 已被并行章程 `charter-judge-agent-t4.md` 占用。本轮看见层诚实从 070 起号，不覆盖 T4 的 066。

### 人现在看见的那一格是什么

`impl/core/frontend_view.py` `_fulfillment_panel`：矩阵每一行只带一个 `status`。

`impl/frontend/summary.html`：

- 主表「状态」列吃整体第一问；
- `fulfillmentPill()` 只给三个词上色；
- 顶部 `stat-not-fulfilled` 把 `not_fulfilled` 和 `not_evaluable` 算进同一格；
- `renderFulfillmentMatrix` 每一行只有 Status 这一格词。

所以人现在看见的结果，只有第一问那三个词。065 说「旁边那一格不是标签」，但旁边那一格今天并不存在。不存在的格子，不能拿来证明「开了也不算标签」。

### 若打开第二问自己的格子，人会看见什么

060 Consensus 已经把规范格子锁成：

```text
看见   规范格子 = 矩阵同一行、Status 旁边
```

`spec/alg/product-function.md` §8 自己的说法是：

> 以后若要看见，再加派生列
> 派生列如果以后要加，也只是把本协议三态单独列出来，供人对照阅读。

打开这一格之后，看结果的人会在同一条期望上多读到一格字。那一格字回答的是第二问，不是办成了 / 没办成 / 说不清。

章程本轮的工作定义第一条：

> 能指出：若打开第二问自己的格子，看结果的人会不会多看见一格字

会。多看见的那一格字，就是结果上多出来的一个标签。065 用「谁写」把这个「会」说成「不能叫标签」，是在看见层回避用户的句子。

### 065 切开了什么，没切开什么

065 真锁住的是：

```text
同一轮判定再写一个词  ≠  结果对象上以后出现派生读
```

这一刀可以留。本 issue 打的是它后半句的否定：

```text
派生读若被人看见  ≠  一个标签
```

后半句不成立。人看见的结果上多一格字，就是多一个标签。叫不叫「judge 结果标签」，取决于「judge 结果」指什么：

| 口语里的「judge 结果」 | 开格子之后 | 065 怎么答 | 看见层的老实话 |
|---|---|---|---|
| 判定那张嘴又吐一个词 | 不是 | 不是 | 仍不是 |
| 人看完判定之后，结果上多一格字 | 是 | 不许叫标签 | 是 |

用户问的是第二行。065 答的是第一行，再用第一行去否认第二行。这就是字词游戏。

### 不是什么

- 不是批准打开那一格。打开仍交 061 / 章程 §4。
- 不是把 060 改名为「所以 B 口批准了」。
- 不是让判定再写一个词。047 / 065 谁写那一刀还在。
- 不是把多出来的那一格并进 fulfilled 三个词。
- 不是重开 T4 占用的 066。

### 可证伪

「开格子不算多一个标签」要同时成立：

1. 打开第二问自己的格子之后，看结果的人仍然只看见办成了 / 没办成 / 说不清；
2. 或者那一格字虽然在，但不算结果上的标签；
3. 或者「标签」只能指判定嘴里吐出来的词，人看见的那一格不许叫标签。

1 与 060 / product-function §8 的「旁边一格 / 派生列」直接撞。2 是改词典，不是改事实。3 就是 065 被打的那句。所以在人看见的那一层，用户那句话成立。

## Proposed Change

Consensus 只锁：若打开第二问自己的格子，看结果的人会多看见一格字；这一格字就是结果上多出来的一个标签。065「旁边那一格不能叫标签」这一句作废。

不改 schema，不改前端，不宣布对外中文，不批准打开。


---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: c5e8ded5a0e2f031
- pid: 7902

**盘上正文冲突**：当前 `issue-070.md` 写的是另一条线（开格子 / 看见层）。本 spawn / `charter-judge-agent-t4.md` 把 070 分给 T3 收问句、T4 对着原句量。067–069 的看见层第二问不是判定代理 Q2。下面只判 T4 这条，不判开格子，不重开 067–069。

**Evidence Verification**:
自己读了冻结 T2 / T3 / T4 和 `name_scenario_runs/I007.json`。没有重跑 12 行大模型。`--probe --treatment t4` 见 066 回应；冻结 sha1 未改。

T3（`generic_two_question_request_level_q1_evidence_shortcircuit_disabled`，`must_fail_n=2`）：

- I007「张忠波保单号」→ `fulfilled`。理由：「实际条件完整交付了客户本人姓名张忠波，符合该字段既有标准；“保单号”未形成带具体值的客户筛选条件，未增加额外限制，因此核心搜索意图已满足。」
- I248「红莲保单」→ `fulfilled`。理由：「用户核心条件是按“红莲”这一客户姓名搜索；实际交付了 searchClientName MATCH 红莲，符合既有字段标准，且未增加未表达的筛选限制。」
- 孪生针 SYN-honglian「红莲保单」→ `not_fulfilled`。理由：「用户同时表达了保单筛选意图，实际条件未包含任何保单相关约束。」

T4 同一三句全部 `not_fulfilled`，理由写的是原问句 / 原句还要保单号或「保单」。T2 在没有 T4「不许收问句」那段的情况下，I007 / I248 已经是 `not_fulfilled`。程序化 `decide("张忠波保单号", [(searchClientName, 张忠波)])` → `None` / `not_one_complete_dimension`。Q1 证据对张忠波、红莲都是「够撑住…2至4个汉字、有姓」。所以 T3 抬成功是 Q2，不是 Q1。

I007 live：`query=张忠波保单号`，`intent_summary=robot_text=客户姓名为张忠波的客户`，正式 `judge_status=fulfilled`，理由已经把保单号收成「无值字段短语」。`name_scenario_runs/I248.json` 不存在；`llm_case_list()` 给 I248 的 `extracted=None`。混合包 I007.note = 「Keep current F; 保单号 is an attribute of the person, not a name veto。」脚本 `LLM_POLICY["I007"]="not_fulfilled"`。章程 §2 / §4.5：旧注不是已锁政策。

**Reasoning**:
T3 在 I007 上的那句，就是 T4 明文禁止的动作：「没有具体值所以不是条件」。这不是偶发翻盘，是模型把问句收到了已有交付那么小。I007 的 live `intent_summary` 已经先丢掉保单号，管道在请模型这么做；T3 的嘴没有把「用户要的事」钉在原始问句上，所以它跟着收。

I248 对 SYN-honglian 的分裂是模型噪声。两边问句都是「红莲保单」，两边都是 `searchClientName=红莲`，I248 没有 extracted / 没有 intent_summary。同一套输入，T3 一句收成姓名题办成了，一句还认保单是另一件事。这不能证明「保单」词表，也不能证明删掉 `intent_summary` 就够。它证明 T3 的 Q2 不稳：没有钉原句时，模型可以重写「用户要的事」。

所以 070 的主声称成立：T3 抬 I007 / I248 是收问句，不是运气。I248 vs 红莲针的对错差本身是噪声；I248 的理由仍是收问句，I007 的理由更是原文级的收。T4 对着原句量，打中的是这个对象。删摘要是管道补丁，不是嘴。T2 已经能挡住这两句，所以这是 T3 回归，不是新发现的病例。

不得在这里把正式 I007 keep-F 锁死。实验政策 NF 和包注 F 章程已经写明冲突。T3 跟正式判定走同一句「无值字段短语」，对本轮不是赢。正式要不要改 I007，交 072 / 项目。

## Improvement Proposal

**Problem**: T3 的 Q2 允许把原始问句收到已有交付那么小，因而在 I007 / I248 上把整句说成办成了。
**Proposed Change**: 内存实验继续用 T4 的 Q2 钉死原始问句。不要加「保单」词表，不要把删 `intent_summary` 当成充分修复，不要改正式 `judge.py` / spec。
**Design**:
- 嘴：保持 `PRINCIPLE_T4` L134–137（用户要的事=原始问句；不许把没被覆盖的部分收成语气 / 修饰 / 「没有具体值所以不是条件」）。
- 管道：I007 的 `intent_summary` 已丢保单号，只解释 I007 为什么更好收；I248 没有这个字段，删摘要挡不住 I248。
- 负对照：程序化 `decide` 对这两句必须继续 `None`，证明说话的是代理不是几何。
**Implementation Steps**:
1. Consensus 只锁：T3 在 I007 / I248 上的 F 是收问句；T4 对着原句量是对的对象。
2. 不要在原则里加「X保单 ⇒ NF」规则。
3. 不要把 I007 正式 `expected_status=fulfilled` 写进本号。
**Risks**: 把 I248 vs SYN-honglian 的噪声当成「T4 必须加保单词表」；或把删摘要当成嘴已经修好。
**Verification**:
```bash
/Users/xiaozijian/miniconda3/envs/agno/bin/python -c "
import json
from pathlib import Path
t3=json.loads(Path('issues/trace/simulate_judge_agent_memory.t3.json').read_text())
t4=json.loads(Path('issues/trace/simulate_judge_agent_memory.t4.json').read_text())
r3={x['id']:x for x in t3['llm']['rows']}
r4={x['id']:x for x in t4['llm']['rows']}
assert r3['I007']['llm_status']=='fulfilled'
assert '未形成带具体值' in r3['I007']['llm_reason']
assert r3['I248']['llm_status']=='fulfilled'
assert r3['SYN-honglian']['llm_status']=='not_fulfilled'
assert r4['I007']['llm_status']=='not_fulfilled'
assert r4['I248']['llm_status']=='not_fulfilled'
assert r4['SYN-honglian']['llm_status']=='not_fulfilled'
print('070 freeze reading ok')
"
```
不重跑 12 行大模型。不改正式文件。
