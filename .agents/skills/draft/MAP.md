# Draft Skill 文件映射

执行者按需查找工具、模板和脚本。`SKILL.md` 讲目标、阶段和约束；本文件只说明真实入口与当前支持边界。

## 公共入口

| 路径 | 用途 | 何时用 |
|---|---|---|
| `reference/draft_config_template.yaml` | Harness/Skill 构造 DraftConfig 的参考骨架；不是 `draft_loop.py` 直接加载的统一 Config loader | 用户准备配置时 |
| `reference/project_yaml_draft_switch_template.yaml` | `project.yaml` 灰度开关模板 | 配置 `<role>_draft.enabled` 时 |
| `reference/draft_report_template.md` | 最终结论报告模板 | 出具结论时 |
| `scripts/introspect_protocol.py` | 协议自省 | 写 draft 前检查抽象方法 |
| `scripts/check_draft.py` | draft 可编译、可加载、协议与灰度校验；promotion 模式还必须运行 unseen cases | 候选实现后 |
| `scripts/validate_investigation.py` | 调查包结构、引用与实现入口门禁 | Solidify 前必须运行 |
| `scripts/validate_key_index_experiment.py` | 校验冻结 probes、候选来源、模拟指标、shortlist；`--require-selected` 还要求 Loop 证据 | Key-Index 候选筛选及最终选中前 |
| `scripts/solidify.py` | 写入 Judge/Mock Solidify receipt | 固化后证明 source ID → 资产 → runtime observable |
| `scripts/review_iteration.py` | 写入 Judge/Mock 逐轮 Role review receipt | 每轮语义 review 前 |
| `scripts/render_loop_comparison_table.py` | 从冻结 iteration-cases 与 run report 渲染 Current/Draft 逐 case 对比表（基础列 + 场景列） | 每轮 review 必出 |
| `scripts/run_iteration.py` | 在冻结条件下执行一次 Current/Draft，保留逐 case 原始事实 | Draft Loop 每轮 |
| `scripts/draft_loop.py` | 冻结 identity、保存 active loop、迭代、失败和 Harness 决策 | Draft Loop 确定性状态入口 |
| `impl/core/draft_promotion.py` | 校验 promotion plan 并确定性搬运已配置文件 | 仅用户明确授权 Promote 后 |

## 调查模板

| 路径 | 用途 |
|---|---|
| `reference/investigation/` | Manifest、overview、Attribute trace 与 Role 专属合同模板 |
| `reference/investigation/judge/docs/judge-investigation-contract.json` | Judge 的 `business_expectations + live_boundary + evaluation_dimensions` 唯一合同 |
| `reference/investigation/judge/docs/authority-investigation-report.json` | Judge 权威调查结构化真相源：`materials + coverage_gaps`，schema version 2 |
| `reference/investigation/judge/docs/authority-investigation-report.md` | 上述 JSON 的确定性渲染结果，不得手写 |
| `scripts/render_authority_report.py` | 从 Judge authority report JSON 生成 Markdown |
| `reference/investigation/mock/docs/mock-investigation-contract.json` | Mock 调查合同 |
| `reference/investigation/attribute/docs/business-flow.*` | Attribute `.mmd + .md + .trace.json` 三件套 |

Judge 报告描述资料在 `conclusion_kind + governs + scenario + conditions` 下直接决定的范围，以及当前资料覆盖缺口；它不预枚举未来 Case，不保存 Runtime resolved/unresolved 结论。Runtime 缺料只供用户决定是否再发起 Investigate，不自动回写。


## Key-Index 候选实验

Key-Index 在证明前是 Draft 候选，不是正式调查资产。执行者按以下顺序使用现有入口：

1. 先记录 Collection profile 与 exact/lexical/embedding/rerank 的 channel consideration；每个通路写
   `experiment/deferred/rejected/not_applicable + reason`，不强制实现不适用的 embedding 或 rerank。
2. 在项目调查目录保存冻结且分离的 development/holdout probes、候选说明和确定性结果；holdout 不得
   用于调参，用过即失效并转 development。这些实验文件只有登记进 Manifest 后才成为正式 artifact。
3. 用 `scripts/validate_key_index_experiment.py --phase investigate` 检查 baseline + alternative（或有证据
   的 alternative exclusion），再用 `--phase simulation` 检查完整 Index/Builder/projection/channels/
   Search/target_ref/Resolver/Load 套件、SearchHit channel receipt、recall、可拒绝性、target resolution、
   loaded context 与成本；不为明显不合格候选运行完整 Role。
4. 将同时通过 development 与 holdout 冻结阈值的 shortlist 作为隔离 provisional candidate 接入 Draft
   Role，再通过 `run_iteration.py` / `draft_loop.py` 比较最终业务结果、Search/Load/Authority audit、
   token 和 latency；该临时实现不能宣称正式 `selected`。
5. 只有 `--phase selection`（或兼容 `--require-selected`）与 Loop 都通过的候选才形成 `selected`，登记
   为 Manifest `key_indexes`，并刷新最终实现和 `solidify.py` receipt；`no_index/unresolved` 不得被
   静默改成全量 fallback。

每次比较前冻结 probes 和候选实现。badcase、reference answer、expected trace 与人工答案词只能作为
评价信息，不能进入 Builder、Entry projection 或 query rewrite。SearchHit 是导航结果，Load 后的真实
对象/片段才可作为 Evidence。

## Active loop 与 restart

- project/role 已有 active loop 时，继续当前 loop。
- frozen identity、objective、review、cases 或 Draft fingerprint 改变时，使用 `scripts/draft_loop.py --restart`。
- restart 会归档旧状态和迭代证据，创建新 active loop，并从 iteration 1 开始；历史不得覆盖或删除。
- `run_iteration.py` 不负责决定是否 restart，也不负责 promotion。

## 当前支持矩阵

| 能力 | Attribute | Judge | Mock | Live |
|---|---:|---:|---:|---:|
| Draft Loop | 是 | 是 | 是 | 否 |
| Solidify receipt | 否 | 是 | 是 | 否 |
| Role review receipt | 否 | 是 | 是 | 否 |
| ROLE.md | 是 | 是 | 是 | 当前不存在 |

Live 是协议扩展点，不应被文档描述成已有执行实现。

## Promotion

Promotion 不是 Loop 的自动尾动作。只有用户明确确认后，才可调用 `impl/core/draft_promotion.py` 的确定性入口，按已验证 plan 搬运文件；不得由 LLM 临场选文件，不得修改 frozen cases 或 Current baseline。
