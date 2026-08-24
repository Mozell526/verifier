# Issue #010: 评测目标绑在 341 条 badcase 上，没有头部对照闸，改 judge 不可泛化

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output + code-analysis
**Layer**: Evaluation / Process（评测目标本身，不是某一条判定句子）
**Cases**: 全表 341 条 `Scenario=badcase`；仓库内无头部对照集

## Verifier Discovery

用户问的是：这份数据集都是 badcase / 长尾，现实分布不一样，怎么平衡。平衡如果做成「把 341 调成假分布」或「在 341 上再加几条例外」，下一轮换一批长尾还会漂。本 issue 钉的是评测目标，不是某一条姓名规则。

### 触发输入

新 judge 落盘表：

`/Users/xiaozijian/Downloads/verifier-client_search-cases-20260814-185013.xlsx`

当场重算（openpyxl，data_only）：

- N = 341
- `Scenario` 唯一值：`badcase` × 341
- 新状态：`fulfilled=213`，`not_fulfilled=128`

旧表 `...-205846.xlsx` 同样 341 行，本计数不依赖它。

仓库内检索「正常集 / head set / 对照闸」：只出现在 canvas 方案 E 的文案，没有任何冻结用例、xlsx、或回归入口。

`impl/projects/client_search/project.yaml` 有 mock 场景名，但不是 judge 回归头部集：

```yaml
default_scenarios: [single_condition, multi_condition_and, product_category_or, product_exclusion, age_boundary, premium_unit_conversion, policy_status_filter, unsupported_family_phrase]
```

`impl/projects/client_search/draft/probes/` 现有探针全是 `judge-badcase-*`；`prepare_judge_badcase_cases.py` 从 badcase 源构造。这些场景名也从未作为本 341 表的对照闸跑过。

### 期望（协议 + 泛化尺子）

协议管单条对错：fulfilled §2.1 要求证据证明用户要的结果拿到了；material-positioning 不变量 1 禁止用 current_behavior 冒充正式规则。

泛化尺子（章程 §2）不是「341 准确率最高」，而是：改任何一条判定机制，必须同时

1. **单向缺陷否决**：盘客/活动、假姓名（共展）、目录产品误走姓名，不得回退；
2. **头部 F 地板**：同形态真实姓名、姓名+产品、合法单号，不得被这张长尾表上的 NF 压力系统性打掉。

两闸是合取，不是加权平均。过严 8 条是观察项，不是唯一 KPI。

### 实际

当前唯一在用的 judge 对照就是这 341 条 badcase。canvas 自己也写了（主张，不是 oracle）：

> 341 条全是 Scenario=badcase。盘客/活动、裸词业务词、残号、称谓被放大了；正常流量里占大头的是「王坤林」「张三+产品」「合法保单号」。
> 在这张表上把 NF 再推高，看起来像修好了过严以外的所有问题，到正常场景会把姓名检索系统误伤。

方案 E 只存在于 canvas 文本：「正常集对照闸，badcase 只做单向约束」。仓库里没有对应数据集，也没有过程闸。

同表内部已经能看见头部形态被当成长尾罚：I539「王坤林」新 judge = NF（见 issue-011）。这不是「以后可能误伤」，是这张表自己已经把最典型头部问法标成缺陷。

### 根因层

评测目标绑死在长尾全集上。没有第二闸，任何「在 341 上更好看」的改动都无法证伪「到头部是否变差」。这不是模型能力问题，是评价函数缺了一维。

### 和 006–009 的边界

006–009 钉的是提示内部打架导致的具体错判。本 issue 即使那四条全修完仍然在：修好了仍只在 badcase 上可见，头部地板不存在，下一轮换一批长尾还会用同一评价函数把头部问法打死。

### 不是什么

- 不是要把 341 重加权、抽样、或合成一个「更像生产」的分数。
- 不是从 341 里挑「看起来正常」的当头部集（canvas 也写了这会继续偏）。
- 不是现在就裁定头部集从哪来——章程 §4 留给用户：现造一截，还是等真实日志。
- 不是 canvas 方案 E 已经成立。E 是待审主张；本 issue 只钉「第二闸不存在」这一可核验事实。

### 可证伪修复（过程闸，不是分数）

立双集合取，缺一不可：

- 集 A（本 xlsx）：盘客/漏错/目录三条净胜不回退；
- 集 B（头部）：姓名 / 姓名+产品 / 合法单号，F 不得掉。

没有集 B 之前，禁止把 341 上的准确率或过严 8 条当作发版依据。

### 未消元

- 未持有真实流量日志，不能给出头部占比。
- 未把 mock `default_scenarios` 实际跑成 judge 对照；只核到它们不是本 341 表的第二闸。
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 37225eeb6839ec61
- pid: 45981

### Investigation

当场用 openpyxl `data_only` 重算，不沿用 canvas / verifier 写的数字。

新表 `/Users/xiaozijian/Downloads/verifier-client_search-cases-20260814-185013.xlsx`（sheet=`用例池候选区`）：

- N = 341（含表头 342 行）
- `Scenario` 唯一值：`badcase` × 341
- 新状态：`fulfilled=213`，`not_fulfilled=128`
- `来源=uploaded_or_manual` × 341；`执行模式=live / live_service` × 341

旧表 `...-205846.xlsx`：同样 N=341、`Scenario=badcase` × 341；旧状态 `fulfilled=257` / `not_fulfilled=83` / `not_evaluable=1`。两表 ID 集合与顺序相同。

仓库检索：

- `正常集` / `head set` / `对照闸`：只出现在 `spec/patch/20260814/client-search-judge-compare-0814.canvas.tsx` 方案 E 文案（约 L683–694）。无冻结 xlsx、无回归入口。
- `impl/projects/client_search/project.yaml` L56 `default_scenarios` 挂在 `runtime.mock_cases`，场景名是 `single_condition` / `age_boundary` / `unsupported_family_phrase` 等 live 生成标签，不是「王坤林 / 姓名+产品 / 合法单号」judge 对照闸。
- `impl/projects/client_search/mock.md` seed 是「45岁女性保费10万以上」这类结构化条件，不是头部姓名/单号。
- `impl/projects/client_search/draft/probes/` 现有探针文件名全是 `judge-badcase-*`；`prepare_judge_badcase_cases.py` 的 `SELECTED_CASE_IDS` 全是 `badcase-00x`。

同表内部形态（用于核对 010 是否把「表里完全没有头部」说满）：

- 精确 2–4 汉字裸词 `re.fullmatch(r'[\u4e00-\u9fff]{2,4}', user_text)`：75 条（47 NF / 28 F）。28 条 F 里只有 I224 杨杰 / I310 郑鑫 / I336 匡西永 的 live 条件是 `searchClientName MATCH`；其余是产品简称、地址、客群、会员状态。
- I539「王坤林」新状态确为 `not_fulfilled`（见 011）。
- 含 10 位以上数字的 query 有 58 条，多数新状态是 F。说明 341 **不是**「零头部形态」；缺的是独立第二闸，不是表里完全看不见单号。

已读：`issues/charter.md` §2/§4/§6，`spec/alg/fulfilled.md` §2.1，`spec/alg/material-positioning.md` 不变量 1。未持有真实流量日志。未把 mock `default_scenarios` 实际跑成 judge。

### Reasoning

010 钉的是评价函数缺维，不是某一条姓名句子。这条成立。

当前唯一在用的、带 341 规模落盘标签的 judge 对照就是这张全 `Scenario=badcase` 表。章程 §2 已经写明：341 准确率和过严 8 条不是 oracle；泛化尺子是缺陷族不回退 **合取** 头部形态不系统性误伤。仓库里没有集 B，所以「在 341 上更好看」无法证伪「到头部是否变差」。这不是模型能力问题，是测量缺了一维。material-positioning 不变量 1 也禁止用 current_behavior（这张表上的 NF 变多）冒充正式对错。

和 006–009 / 011 / 012 的边界我同意，不重开前四条：

- 006–009：提示内部打架的表面错判。
- 011：同形态姓名在新 judge 里已经左右互搏（王坤林是 010 的现场伤亡，不是 010 的全部）。
- 012：判定程序的宿主放错层。010 解释的是「为什么只改句子还会被当成进步」。

需要收的口，避免把 010 做成 canvas E 的背书：

1. **不是**「341 里没有任何头部形态」。表里已有合法单号（58 条数字 query，多数 F）和三条姓名 F。缺的是独立、冻结、不从 341 里挑「看起来正常」的集 B。
2. **不是**现在就裁定集 B 从哪来。章程 §4.4 把「现造一截 vs 等真实日志」留给用户。010 只钉「第二闸不存在 + 在它出现前不能拿 341 准确率发版」。
3. **不是**把 341 重加权成假分布。verifier 这段「不是什么」成立，我附议。
4. canvas 方案 E 仍是待审主张，不是修复规格。

可证伪点已经够：只要仓库里还没有独立于 341 的头部冻结集，并且发版讨论仍引用 341 F/NF 或过严 8 条当 KPI，010 就还在。即使 006–009 和 011 的表面全修完，只要测量仍只有集 A，换一批长尾还会用同一评价函数把头部问法打死。

### Improvement Proposal

- **Target**: 评测过程闸，不是 `draft/judge.py` 某一句，也不是两张 xlsx。落地物应是独立于 341 的集 B 冻结入口 + 发版合取检查；集 B 来源按章程 §4.4 升级用户。本轮章程 §6 只立根因，不实现方案 E。
- **Change**:
  1. 立双集合取，缺一不可，禁止加权平均：
     - 集 A = 本 341 `Scenario=badcase`：盘客/活动、共展类假姓名、目录产品误走 `searchClientName` 三条净胜不得回退。
     - 集 B = 头部对照：二字/三字中文姓名、姓名+产品、合法单号。F 地板不得掉。集 B **禁止**从 341 里挑「看起来正常」的子集。
  2. 集 B 未冻结之前，禁止把下列数字当作 draft judge 发版依据：341 `fulfilled` 计数、341 准确率、过严 8 条观察项、任何「在 341 上 NF 更高所以更严更好」的叙述。
  3. 集 B 从哪来（现造一截 vs 等真实日志）写入用户决定，不由角色代选。在用户选定之前，过程规则已经生效：只有集 A 的单向否决，没有发版分数。
  4. 不要实现 canvas 方案 E 的文案本身；E 只提示「需要第二闸」，不规定集 B 的抽样和标注。
- **Verification**（不重跑 judge）:
  - 重算 341/`Scenario`/`状态`：应对 `badcase=341`、`fulfilled=213`、`not_fulfilled=128`。
  - 在 `impl/projects/client_search` 与 `spec` 检索 `正常集|head set|对照闸|头部对照`，排除 canvas 后应仍无冻结集。
  - `draft/probes/` 在去掉 badcase/authority/solidify/测试脚手架后，不应冒充集 B。
  - 集 B 一旦按用户决定冻结：改任何一条判定机制必须同时跑集 A 单向否决和集 B F 地板；任一失败即不可发版。在那之前，本 issue 的验收是「没有人再用 341 准确率当发版 KPI」。
- **Why I Cannot Apply It**: architect 只读。集 B 来源是章程 §4 用户决策；本轮章程 §6 禁止实现方案 A–E。

---
## Consensus
**Verdict**: real-problem

双方独立重算一致：341 条全是 `Scenario=badcase`，新状态 F=213 / NF=128；仓库里没有独立于 341 的头部冻结集。评价函数缺第二维，这是过程问题，不是某一句提示。

接受 architect 的收口，写入本共识，避免 010 滑成 canvas 方案 E 的背书：

1. 341 **不是**「零头部形态」。表里已有大量合法单号（约 58 条数字 query，多数已是 F）和三条姓名 F。缺的是独立、冻结、不从 341 里挑「看起来正常」的集 B。
2. 平衡 = 集 A 单向缺陷否决 **合取** 集 B 头部 F 地板，禁止加权、禁止重加权 341。
3. 集 B 从哪来（现造一截 vs 等真实日志）仍归章程 §4，本轮不代选。集 B 冻结前，341 准确率 / 过严 8 条不得当发版 KPI。
4. 006–009 / 011 修完也不关闭 010：测量仍只有集 A 时，换一批长尾还会把头部问法打死。

本轮不实现方案 E，不改 xlsx / 代码。
