---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 81d2ac4a0afb73d1
- pid: 77264

### Investigation
- 四案原文：I161 新 reasoning 把『去年投保』建成「该字段 `is_supported=false` 属上游能力边界」；I046 旧 reasoning 把同一缺口建成「当前能力清单……没有可用于投保日期筛选的能力」。I034 / I616 旧 judge 把空条件本身当成能力边界正确（格式外「正确行为是不生成保单号条件」；称谓「现有字段不支持客户昵称、称谓」）。
- `draft/judge.py` `_unsupported_boundary_evidence`（L454 起）从 `intent_summary` / `robot_text` 刮 `暂不支持|当前不支持|不支持`，产出 `unsupported_notices`、`graceful_degradation_candidate`。012 Consensus：这是材料，不是闸。I034 / I616 的「未识别到明确查询条件」连这则材料都刮不到。
- 协议禁这条取值路径：`material-positioning.md` 不变量 1，`current_behavior` 不能代替 `normative_rule`；`inlive_boundary` 只升级空间（有什么），不升级选择（本次对不对）。`authority.md` §8.2：问题必须是「产品是否支持 / 是否属于职责」，不得写成「当前输出对不对」。§11.2：不能把模型常识或当前代码「正在使用」自动升级为正式标准。`fulfilled.md` D5 / D6：先问该不该支持，再谈清单里支不支持。
- 仓库里和「地图」长得像、但占的是别的格子的东西（逐项核过，不当成产品功能地图）：
  1. `field_definitions_args.yaml` 的 `is_supported`：调查报告标成 `inlive_boundary`（M1 代理下游可承载空间）。原文限制：「is_supported 只决定字段当前是否允许作为搜索条件；它不决定用户表达是否应映射到该字段」。
  2. `judge_boundary-template.md`（`project-judge-boundary-source`）：normative_rule 只归责**评价范围**，并登记 M1。不是逐维「产品认不认」。
  3. CoverageGap `responsibility-boundary-unsupported-field`（`authority-investigation-report.md`）：已经写明缺的是「业务方对 is_supported=false 字段逐项确认的职责边界声明（职责外 vs 职责内能力缺失）」。这是**要地图的缺口记录**，不是地图。
  4. `find-target-customers`（`project.yaml` / `judge_business_contract.md`）：一条产品使用场景，不是维度清单。
  5. mock `default_scenarios`（`single_condition` / `unsupported_family_phrase` 等）：测例名，不是产品声明。
  6. fulfilled §2.3 车牌 / 公司名：协议举例，不是客户搜索功能地图；称谓 / 去年 / 残号不在那里。
- 章程 §4.1–§4.3 正是这张地图上三个空格。本轮不代填。

### Reasoning
同意：`is_supported=false` / 空条件 / 「暂不支持」文案**填不满**用户要的产品标签。用户要的是「产品功能定位以内、当前尚未支持」= **地图上有、空间里还没有**。三件实现侧信号只能描述现状：

- catalog `is_supported=false` 回答「现在能不能当搜索条件」——调查里已经把它放在空间格，并另开了职责归属缺口；
- robot「投保日期暂不支持搜索」是 live 自我说明，012 定为材料；
- 空条件 + 「未识别」更弱：它连「系统承认这是一个它认但不做的维」都没有，只是没交出对象。

用它们去填「产品尚未支持」，会把明天 parser 拒的东西写成产品边界，把「产品认但还没做」和「产品根本不认」混进同一张 IT 清单。这正是用户不要的。

收紧 verifier 的「仓库里没有成文地图」：作为 **normative 产品功能地图**（客户搜索认哪些事），没有。作为 014 那条减法的**另一半**，仓库里已经有空间代理（`is_supported` / 字段枚举，调查按 M1 打成 `inlive_boundary`）和一张「地图缺了」的 CoverageGap。所以：

- 空间侧：已登记的 `inlive_boundary` 可以回答「当前空间做不做得到」——前提是信任模型仍成立，且只升级空间；
- 地图侧：没有任何 in-repo 资料能回答「这个点在不在产品功能定位里」。缺这一条，维级「尚未支持」不得落笔；
- `is_supported` 可以继续当空间材料，不能当「产品认不认」的裁决。空条件和「未识别」连空间材料都不够格。

不把 mock `default_scenarios`、能力清单、或 live 拒识授权成功能地图。去年 / 称谓 / 格式外编号进不进地图，仍是章程 §4。

### Improvement Proposal
- **Target**: 取值源头，不是画地图，也不是改 catalog。
- **Change**: 维级「尚未支持」必须能回指两条独立证据：产品功能地图条款（normative_rule / 业务方职责声明）+ 已登记空间缺口（`inlive_boundary`，须 M1）。缺任一条不得写这个标签。只有 `is_supported=false` / 空条件 / 「暂不支持」文案 → 最多记 current_behavior 或空间材料。CoverageGap `responsibility-boundary-unsupported-field` 继续当「地图未到」的正式缺口，不要用实现去填。
- **Verification**: I161 不能仅因 `is_supported=false` 宣布去年是产品边界；I616 不能仅因空条件宣布称谓是能力边界；I034 不能仅因未识别宣布残号「尚未支持」。对照：若用户日后补了地图条款且空间登记仍是 false，才允许在该维写「地图内、空间还没有」——仍不升成第四态（014），也不和空条件共用整体格（013）。
