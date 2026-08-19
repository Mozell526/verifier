# 轴2 稳定性治理方案（说不清 43% → 目标 ≤15%）

> 状态：已落地（2026-08-18）。实施见 `impl/core/capability_carrier.py`。
> 母协议：`spec/alg/capability_carrier.md`；读法抽取改造：`spec/alg/capability_carrier-reading.md`。
> 依据：runB 341 条实测（verifier-client_search-cases-1d729f5-rmname-runB.xlsx）
> + runB context store 101 条 mapper 调用日志复盘。

## 0. 实测定性

runB 128 条 NF、185 条 blocking 期望的轴2 归位：做错了 61、做不了 45、**说不清 79（43%）**。
79 条说不清没有一条是业务语义模糊，全部是工程问题，两类各有代码级根因：

| 类别 | 条数 | 根因（`impl/core/capability_carrier.py`） |
|---|---|---|
| 读法抽取失败或读法不稳 | 39 | LLM 调用失败零重试；两次抽取包在同一 try，一次异常连坐两次；`_mapper_cache` 把 None 永久缓存，一次瞬时 429 毒化整轮 |
| 两次读法裁决不一致 | 40 | 双抽等值判定过苛：unmapped 无条件压过 alternatives（多报一条 unmapped 整案翻转）；`_verdict_signature` 比引用字段集，同 carry 不同等价读法也算不稳；二抽无仲裁，`reasoning_effort="low"` 放大方差 |

旁证：101 条成功调用日志 0 条 JSON 解析失败、0 条目录外字段、0 条解析层丢弃——
说明失败全在调用层（配额/冷却），不在模型输出质量。

另有跨 case 不一致与成本问题：live 管线每 case 新建 `CapabilityCarrier`，
缓存不跨 case，同一期望普遍 4 次调用，同一业务维度跨 case 可得不同答案。

## 1. 失败语义：重试耗尽 → 归位失败 + run 标记 error（硬约束）

与轴1「LLM 失败 → not_evaluable，绝不 not_fulfilled」同一条纪律，且更严格：

- mapper 重试耗尽仍失败、或能力快照加载失败（`fields=None`）时，
  **不再落「说不清·工具失败」**——那会把基础设施故障伪装成业务归因，
  混进说不清统计并被下游当真消费。
- 该期望**归位失败**：carrier 报告写 `error`（含失败阶段与末次异常摘要），
  `placements` 不含该期望，三态里不出现它。
- 任何一条归位失败即把**本次 run 的运行状态标记为 error**
  （loop 运行报告 `run_status="error"`；live 管线在汇总层等价标记）。
  error 状态的 run 不得进入 review/solidify，不得作为对照数据消费，只能重跑。
- 「说不清」自此只保留业务性成因：口径分歧、空间未受治理、
  多数票仍无多数。`GAP_TOOL` 类说不清出口删除，不做兼容保留。

审计断言（进 `capability_carrier_audit`）：完成态 run 里不允许存在
`gap_kind=工具失败` 的归位，也不允许 blocking NF 期望缺归位且无 error 标记。

## 2. 改动清单（按性价比排序）

| # | 改动 | 修什么 | 预期收益 |
|---|---|---|---|
| 1 | mapper 调用加重试（退避 + 换端点），两次抽取各自独立 try，**只缓存成功结果**；重试耗尽走 §1 归位失败 + run error | 读法失败三个放大器 | 39 条读法失败基本清零；残余失败显式暴露而非污染说不清 |
| 2 | 裁决签名收窄：carry=yes 时不比引用字段集，只比 carry + recognition + gap_kind | 同答案不同等价读法被误判不稳 | 消假不稳 |
| 3 | 双抽不一致时加抽第三次做 2/3 多数票，仍无多数才落说不清·口径分歧 | 边界期望 2p(1-p) 抖动 | 压到 p² 量级；多数票是降方差，不违反母协议 §10「不许掷硬币」 |
| 4 | 归并逻辑：任一 alternative 全承载则参与 resolve，unmapped 只在无完整承载读法时定案；或合并两次抽取读法并集后只裁一次 | unmapped 压过 alternatives 的翻转主通道 | 边界期望稳定归位 |
| 5 | live 管线整 run 共享一个 carrier 实例（loop runner 已如此） | 跨 case 不一致 + 成本 | 调用量减半，同维度同答案 |

1+2+§1 不动协议语义（失败语义是新增约束，不改三态定义），先落地；
3、4 需同步修订本目录 `capability_carrier-reading.md` §3.5 与母协议 §10 的双抽验收口径。

## 3. 验收

- 用 runB 341 条做回归：说不清占比 ≤15%，做不了/做错了主干（盘客/车牌/
  人名误识别/单号类）归位不动。
- 冻结 30 条双 replicate：轴1 逐 case 不变；轴2 类型双抽一致。
- 注入故障演练：mock mapper 前 N 次抛异常——N 在重试预算内则归位结果与无故障
  一致；超预算则该期望归位失败、run_status=error、审计报告可见失败阶段。
