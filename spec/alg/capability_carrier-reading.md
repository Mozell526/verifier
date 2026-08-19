# 轴2 读法抽取改造方案（正则占位 → LLM mapper）

> 状态：已落地（2026-08-17）。实施见 `impl/core/capability_carrier.py`。
> 母协议：`spec/alg/capability_carrier.md`。本方案只动协议判断顺序里的**第二步**
>（期望 → 最小完整表达）的落地方式；第三步仍是确定性代码，但缺维度/缺值定案前
> 先过受治理口径表，再全量目录反查。placement 映射不动。口径表是轴2 调查产物，
> 进 `current_fingerprint`，不进 Judge / 不进 Judge solidify。

## 0. 背景：这是欠账，不是新需求

母协议设计时就把分工写死了：

```text
第二步  期望的语义 → 空间里的维度        ← 语义映射，设计定位是 LLM
第三步  受治理能力空间查承载             ← 确定性代码
```

风险表当时登记过「期望→维度语义映射是 LLM，有错误率」。但落地走了两轮占位：

1. 第一版（057）：正则读期望，读不出中文维度就说不清——明确标注"确定性占位，不是真 LLM mapper"；
2. 第二版（现行 `impl/core/capability_carrier.py`）：重写为独立模块，把字段别名词典做富，仍未接 LLM。

341 条实测（jmz0815 runB）证明：第三步没出过错，错全部出在第二步的占位上。

## 1. 实测定性：哪层坏了

结构面全对：F 212 条轴2 为空、NF 129 条全有落位、无轴1 回写。
锁定族全对：盘客/车牌/投保日/活动/属相，别名稳定命中 + `is_supported=false` 显式资料。

出锁定族后三个系统性错误，全在读法抽取：

| # | 机制 | 后果 | 实例 |
|---|---|---|---|
| 1 | 别名匹配失败 → `_extract_dimensions` 从期望句抠短语当维度名 → M1 查不到 → 走 `entry is None` 判「做不了·空间缺维度」 | 最强结论（做不了）可被正则垃圾触发，citation 空转 | 「空间缺维度 **交付老客户**」(I112)、「**正确表达本次单一**」(I548)、「**可执行客户**」(I529)、「**账户追加客户核心**」(I203) |
| 2 | 期望文本撞上任何 supported 字段的别名 → `CARRY_YES` →「做错了（完整表达存在）」 | 做错了成兜底桶；正确字段 `is_supported=false` 也救不回来 | I127 未兑换积分、I058 满期金、I091 承保日（正确字段不支持/不存在，撞上了别的字段）；129 条里「完整表达存在」92 次 |
| 3 | 判定单位是 Judge 现写的期望句，措辞变 → 撞的别名变 → 类型变 | 同一空间事实多套答案，轴2 继承 Judge 措辞方差 | 被保人：I102 做不了 / I317 做错了 / I056 说不清；老客户：I112 做不了 / I155、I603 做错了；投保日：I046 做不了 / I091 做错了 / I161 整维消失 |

共性：**承载性判定的输入不是空间事实，而是措辞与词典的碰撞结果**——与母协议
「资料视角、不看交付」的定位相反。且赌输时不落说不清，随机落进做不了或做错了。

## 2. 改造原则

1. **恢复协议原分工**：第二步语义映射交给 LLM；第三步 `evaluate_reading` /
   `resolve_carrier` / `map_placement` 确定性代码不动。
2. **LLM 只出读法，不出结论**。输出是候选 `field × value × operator` 读法组，
   承载性照旧由确定性代码对快照裁。LLM 永远接触不到 placement 三态。
3. **「不看交付」由输入构造保证**：mapper 的输入只有期望文本 + 受治理维度目录。
   不给 live 输出、不给轴1 理由、不给 robot_text。结构隔离，不靠提示词纪律。
4. **失败方向收敛到说不清**：读法抽不出、字段出目录、replicate 不一致，
   一律说不清（带差在哪儿 + 缺料）。做不了必须资料自认，做错了必须完整表达被证实。

## 3. 机制

### 3.1 管线

```text
NF blocking 期望
  → LLM 读法抽取（新，见 3.2）
  → resolve_carrier（不动）
  → map_placement（不动）
```

删除：`_extract_dimensions`、`_DIMENSION_PATTERNS`、别名 hit 计分、`_PROCESS_CUE` 正则直判。
别名/negatives 数据保留——不再当判定器，改作 mapper 提示词里的维度目录注释。

### 3.2 读法抽取契约

调用：`project_llm_client(spec, role="capability_carrier_mapper", tools=[])` +
`complete_json`（structured output），与 judge/attribute 同一套 client 设施。

输入：

- 期望文本（`expectation_id` / `user_intent` / `expected_outcome` / `acceptance_criteria`）；
- 维度目录：快照全部字段的 名称 + description + aliases + operators + enums 摘要
 （封闭清单，来自 `snapshot_from_capability_manifest`，不变）。

输出（JSON，全部字段必填）：

```jsonc
{
  "process_only": false,          // 纯过程约束（不增加/不虚构类）→ 承载得了
  "alternatives": [               // 每个 alternative = 期望的一种完整读法
    {
      "readings": [               // 合取：全部承载才算该读法承载
        {"field": "policies_insure_date", "value": ["2025-06-01", "2025-06-30"], "operator": "RANGE"}
        // 前缀/尾号：operator 仍是 MATCH，match_mode 单独写
        // {"field": "clientMobile", "value": "158", "operator": "MATCH", "match_mode": "prefix"}
      ]
    }
  ],
  "unmapped": [                   // 目录里找不到承载字段的维度
    {
      "surface": "满期金金额",     // 期望里的原始表述
      "nearest": [                 // 必填：扫过的最近候选及不匹配原因
        {"field": "policies_universal_acct_transfer", "why": "语义是转入万能账户金额，非满期金"}
      ]
    }
  ]
}
```

读法字段形态（structured output 必须收下，再由代码归一）：

- `operator`：目录操作符名（`MATCH` / `RANGE` / `GTE` 等）。前缀或尾号写
  `operator=MATCH` + `match_mode=prefix|suffix`。模型若把
  `{match_mode:"prefix"}` 塞进 operator，归一成 `MATCH` + `match_mode`，
  不得因类型校验失败而归位失败。
- `value`：标量字符串、数字、区间数组 `[起点, 终点]`、或 `{min,max}` /
  `{start,end}`。代码归一成字符串后再裁承载；区间本身不是缺操作符。

硬约束（代码侧校验，违反即该期望归位失败，run 标记 error）：

- `readings[].field` 必须 ∈ 目录字段名，出目录 → 该读法作废；
- `unmapped[].nearest` 不许为空——空扫描声明无效，防 LLM 偷懒直接判缺维度；
- `alternatives` 与 `unmapped` 不得同时为空。

### 3.3 三态怎么落（对齐母协议 §3）

| mapper 结果 | 确定性代码裁定 | placement |
|---|---|---|
| 读法字段 `is_supported=false` / 封闭枚举缺值 / 缺操作符 | 承载不了 | 做不了（引用字段条目） |
| `unmapped` 且 nearest 扫描成立，**且全量目录反查无命中** | 承载不了（封闭空间查无此维） | 做不了（引用目录 revision + nearest） |
| 所有读法全承载 | 承载得了 | 做错了 |
| 读法之间答案不一致 | 口径分歧 | 说不清 |
| 双抽不一致、第三抽 2/3 多数票仍无多数 | 口径分歧 | 说不清 |
| 抽取重试耗尽 / 快照不可用 | 归位失败 | 不落三态；run_status=error |
| `process_only` | 承载得了 | 做错了 |

缺维度 / 缺值不得在 mapper 口头声明上直接定案。定案前确定性代码对
`unmapped.surface` 和缺值字符串做一次**全量目录反查**（全量枚举 + 描述里出现过的唯一别名，
不限于 prompt 里那 12 个枚举样本）：

- 枚举命中 → 改写成该字段读法，再走第三步；
- 唯一受治理别名命中 → 改写成该字段读法，再走第三步；
- 无命中 → 原缺维度 / 缺值成立。

反查是成员资格判断，不另调 mapper。二字枚举只做分词整词命中（「财富」不得切中「财富分群」）；
别名排除字段「不表示」否定项；泛词（「客户」等）不许靠子串命中劫持其它维度。
有封闭枚举的字段被别名命中时，必须带上别名当值再裁，空值不得跳过枚举校验。

与现行实现的两个关键翻转：

- **「空间缺维度」不再由抽维失败触发**——只能由带 nearest 扫描的 `unmapped` 声明触发，
  citation 从空转变成可审计（最近候选为什么不行）；
- **「完整表达存在」不再由撞词触发**——读法是 LLM 对期望语义给出的，
  且值/操作符照旧过封闭枚举校验。

### 3.4 一致性：按维度去重缓存

母协议 §6 已要求「（期望的目标维度 × 空间快照）去重，一轮只裁一次」。占位实现没做，
这正是同维多套答案的放大器。本方案落实：

- 缓存键：`sorted(fields of reading) × snapshot revision`；
- 同轮内同一读法集合的承载性只裁一次，跨 case 复用；
- 审计断言：同轮内同一 field 集合的 placement 类型必须一致（缓存保证，断言兜底）。

mapper 调用本身按期望文本 sha 去重缓存，落 context store（同 judge 的 LLM 缓存形态），
重跑不重付费。

### 3.5 波动治理

当年不接 LLM 的顾虑是重跑波动。正解不是退回正则，而是：

- structured output + 低温；
- mapper 调用退避重试 + 换端点；只缓存成功读法；重试耗尽 → 归位失败，run 标记 error；
- 同 run 双抽 replicate：比较的是**裁决签名**（carry / recognition / gap_kind；
  carry=yes 时不比引用字段集），不比 LLM 自由文本；
  签名不一致 → 加抽第三次做 2/3 多数票，仍无多数才说不清（口径分歧）。
  不许在做不了/做错了之间掷硬币；
- unmapped 不得压过已完整承载的 alternative；
- 母协议 §10 已改过验收口径：确定性面比 diff，LLM 输出不做逐字节比较。

## 4. 审计与验收

新增 gate 断言（进 `capability_carrier_audit`）：

1. 做不了必带四种资料自认之一：`is_supported=false` / 缺值 / 缺操作符 / unmapped+nearest；
2. `readings[].field` ∉ 目录 → fail；
3. 同轮同 field 集合 placement 类型一致；
4. 说不清必带 gap_kind + missing_material（已有，保留）。

金标回归（用 jmz0815 runB 的 341 条做对照，实施时固化为 fixture）：

| case | 现状 | 改后必须 |
|---|---|---|
| I127 未兑换积分 / I058 满期金 / I091 承保日 | 做错了 | 做不了 |
| I112 / I548 / I529 / I203「空间缺维度 <碎片>」 | 做不了（垃圾维度名） | 维度名可读、nearest 可审计，或说不清 |
| I102 / I317 / I056 被保人三套答案 | 三套 | 同一角色维类型一致 |
| I211 / I218 金凤（姓名/产品读法相反） | 做错了 | 说不清（口径分歧） |
| 盘客 14 条 / 车牌 2 条 / 投保日 3 条 / 活动 / 属相 | 做不了 | 不动（盘客须引用 customerReview，不得写成空间缺维度） |
| 圈客/口令/少儿万能/孤儿单/手机前缀 等做错了主干 | 做错了 | 不动 |
| I049 平安福 / I566 鑫盛鑫利 | 做不了（缺值或缺维） | 做错了（全量枚举命中 abbrname） |
| I057 17周岁以下 | 做不了（空间缺维度） | 做错了（clientAge） |

冻结 30 条双 replicate：轴1 逐 case 不变（判后 pass 结构保证）；轴2 类型双抽一致。

## 5. 改动清单

| 位置 | 动作 |
|---|---|
| `impl/core/capability_carrier.py` | 删 `infer_readings` 正则/别名评分、`_extract_dimensions`、`_PROCESS_CUE` 直判；新增 LLM mapper + 读法缓存；`evaluate_reading` 收窄 `entry is None` 出口（字段必在目录内，缺维度只走 unmapped 路径）；缺维度/缺值定案前 `rescue_catalog_misses` 先口径表再全量反查；`resolve_carrier` / `map_placement` 不动 |
| `impl/projects/<id>/capability_lexicon.yaml` | 受治理业务词口径（unsupported / carried / missing）；入快照与 mapper 目录，不进 Judge |
| `impl/core/pipeline.py` | 判后 pass 调用点不变，传入 spec 供 mapper 建 client |
| `spec/alg/capability_carrier.md` §6 / §8 | 「期望→维度映射由 LLM 执行、承载查询确定性」写回落地章；轴2 资产走 current_fingerprint，冻结 NF 金标做变更门禁 |
| `tests/test_capability_carrier.py` | 金标 fixture + 口径表 / 冻结 NF gate |

不做：

- 不动轴1、不动 Judge prompt、不动 JudgeResult schema；
- 不进 loop 计分（母协议 §5.9）；
- 不走 in-run authority Request/Resolution 通道（母协议 §6）；
- 不给 mapper 开工具（纯文本进出，环境已由快照封闭）。

## 6. 成本

单位是 NF blocking 期望（每轮 30 case 约 45–60 条），经 3.4 两层缓存后实际调用
远低于期望数；单次调用输入 ≈ 期望文本 + 维度目录摘要，与 attribute 单步同量级。
