---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 81d2ac4a0afb73d1
- pid: 77264

### Investigation
- 重读章程 §2 / §4、`spec/alg/fulfilled.md` 开篇与 §6、007 / 009 Consensus；未重开其对错。
- 从 `issues/trace/split-overstrict-8cases.json` 逐条抽出四案 live / reasoning，不靠 verifier 转述：
  - I046 live：`投保险种简称为平安学业福的客户` + `提示：投保日期暂不支持搜索，系统将按可支持字段搜索。`，conditions 长度 1（学业福 MATCH）。新 overall=`not_fulfilled`（「去年」blocking=true 未交）；旧 overall=`fulfilled`（日期当能力外透明退化）。
  - I161 live：投保人林秀微 AND 全家保 + **同一句**日期提示，conditions 长度 2。新 overall=`fulfilled`（两个 blocking 已交；『去年投保』写成 `is_supported=false`、blocking=false）。旧 overall=`not_fulfilled`（裸名改成投保人，与日期无关）。
  - I034 live：`未识别到明确查询条件`，`conditions=None`。新 overall=`not_fulfilled`（要 MATCH `P07000000`）；旧 overall=`fulfilled`（格式外拒识）。
  - I616 live：同一句未识别，`conditions=None`。新 overall=`not_fulfilled`（要把「周老板」当姓名）；旧 overall=`fulfilled`（称谓不可查）。
- 核对材料函数：`draft/judge.py` `_UNSUPPORTED_NOTICE`（L57–58）只刮 `暂不支持|当前不支持|不支持`；`_unsupported_boundary_evidence`（L454 起）的 `graceful_degradation_candidate` 还要求 `supported_condition_count > 0`。I034 / I616 的「未识别到明确查询条件」**进不了**这条材料通道。
- 007 Consensus：I046 / I161 必须同侧；盘客/活动（整句唯一对象缺失）不能和这条一起放。009 Consensus：I034 空条件不得 NF，也不得 F；合法保单号空条件仍须 NF。

### Reasoning
同意主结论：开关 2 和 3 只共享「系统没乱映射」这种态度，不共享失败对象，因此**不能共用一个整体格**。这不是松严问题。若用一个整体「尽力了 / 尚未支持」把它们收在一起：

- I161（人+产品已可搜，新 judge = F）会和 I034（什么条件都没有，新 judge = NF）拿同一分；
- 007 的「去年同侧」和 009 的「空条件既不是 F 也不是 NF」会被重新拧死；
- 盘客/活动那种「职责内、唯一对象没给」也会被这句态度救走。

协议出口已经按对象分开：fulfilled §6 整体 = 核心诉求聚合；§2.2 / §7.1 / D3 禁止把如实告知升成办成了。开关 2 的 live 上**已经有可执行条件**（险种，或姓名+险种），没交的是日期维。开关 3 的 live 上**零条件**，没成形的是唯一查询对象。

两处收紧，不改主判：

1. **可以共享维层词表，不能共享同一个维标签取值，更不能共享整体格。** 问句「挡不挡整句 / 在不在产品定位里 / 当前空间有没有」可以两边都问（见 014 的层，不是已接受的 schema 字段）。但取值不是同一个：开关 2 的未交块是已有条件旁边的日期维；开关 3 的未交块是唯一对象没成形（009：输入坏 / 职责外 / 或用户未定的 non-blocking 说明）。同一套问题 ≠ 同一个标签。
2. **不要把「去年」先写成附加维。** 那是章程 §4.1，本轮不代选。本 issue 只需要「已有可执行条件 + 日期维未交」对「零条件、唯一对象未成形」。I046 / I161 仍按 007 同侧，哪边 blocking 留给用户。

它们连 live 提示族都不一样：2 是「投保日期暂不支持搜索」，3 是「未识别到明确查询条件」。感觉像一类，材料通道已经把它们拆开了。

### Improvement Proposal
- **Target**: 协议分层，不是 `draft/judge.py`，也不是新整体枚举。本轮不改代码、不发明上线字段。
- **Change**: 评任何「尚未支持 / 尽力了」之前先问主事交没交出来。主事已交、只剩日期维 → 走 007 的维级拆分，不和空条件合并。主事没成形 → 走 009，不因为「没乱编」记成和 I161 同类。维层可以共用 014 的三个问句；整体出口保持三态。禁止用一个整体标签收 2+3。
- **Verification**: 用同一份 `split-overstrict-8cases.json` 做对照表：I161 与 I034 不得落入同一整体格；I046 与 I161 必须同侧；I034 / I616 空条件不得再变成办成了；盘客/活动不得因「系统尽力了」离开 NF。
