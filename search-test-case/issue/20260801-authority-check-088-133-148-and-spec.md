# 2026-08-02 Authority Check：088/133/148 判定 + draft 实现对照 spec（更新版）

> 本文档更新并替代上一版（2026-08-01 记录）。上一版基于 006-run 旧产物；本节基于
> 2026-08-02 代码状态（lean/full manifest 分离 + unsupported 边界口径统一 + solidify
> receipt 重建）后的全新实测，反映当前真实行为。

审查范围：
- 三个 case 判定分析：`source-badcase-088`（7月盘客）、`source-badcase-133`（中银保信）、
  `source-badcase-148`（查一下徐晓燕名下是否有住院医疗保险）。
- draft 实现对照 `spec/alg/authority.md`（运行时协议）与 `spec/alg/investigate-authority-judge.md`（调查协议）。
- 用户三个问题：(1) 148 是否像 not_evaluable；(2) 088/133 是否应为 not_evaluable；
  (3) check 实现是否满足 spec。

验证依据：
- 2026-08-02 实测：`run_unseen.py --project client_search --role judge`，
  148 单 case（`/tmp/case148.json`）、088+133 双 case（`/tmp/cases088133.json`），
  case 均取自冻结集 `impl/projects/client_search/draft/probes/judge-badcase-final-30.json`。
- 全量回归：`pytest -q --ignore=hooks/api-check` → **610 passed**。
- 实现文件：`impl/projects/client_search/capability_manifest.py`（lean/full）、
  `impl/projects/client_search/live.py`、`impl/projects/client_search/live_schema.py`、
  `impl/projects/client_search/draft/judge.py`、`impl/core/authority_*.py`、
  `impl/projects/client_search/judge.py`（production，未改动）。

---

## 一、三个 case 判定事实（2026-08-02 实测）

| Case | 输入 | Live（parser 输出） | Production | Draft |
|---|---|---|---|---|
| 148 | 查一下徐晓燕名下是否有住院医疗保险 | 仅 `searchClientName MATCH 徐晓燕`，robot="客户姓名为徐晓燕的客户" | **not_fulfilled**（5 assessments / 5 blocking），但 reasoning 误称"当前能力清单未提供保险字段或枚举" | **not_fulfilled**（4 / 3 blocking），正确命中 `planfullname:[住院医疗保险]` 枚举，定位"筛选住院医疗保险产品"+"AND 组合"两处缺失 |
| 088 | 7月盘客 | conditions=[]，robot="提示：盘客暂不支持搜索，无法进行查询。" | **fulfilled**（3/3 blocking，"盘客不在能力清单，空条件+明确提示=正确处理"） | **not_evaluable**（核心"检索7月盘客目标客户" NE 0.96；边界"透明告知" fulfilled 0.99） |
| 133 | 中银保信 | conditions=[]，robot="未识别到明确查询条件" | **not_fulfilled**（2/2 blocking，"中银保信是四字姓名候选，应映射 searchClientName MATCH"） | **not_evaluable**（核心"检索中银保信相关目标客户" NE 0.90；边界"不将机构名误识别为客户姓名" fulfilled 0.99） |

三个 case 的 `authority_tool_call_ids` 均为 `[]`；`environment_snapshot_sha256` 一致
（a702ae60...），说明运行在同一环境快照下。

---

## 二、三个 case 的判定分析（回答用户三个问题）

### 问题 1：148 像 not_evaluable 吗？—— 不是；production/draft 都判 NF，但 draft 证据正确

- 保险维度技术上**可表达**：`polNoInfo.plancodeinfo.planfullname` 的枚举含**精确值
  "住院医疗保险"**（全量 7343 项，full manifest 已加载）；`pCategorys`（险种大类）、
  `abbrname`（产品简称）、`claimplancodename` 均有命中候选。
- 因此 actual 遗漏保险条件属于**业务未交付** → not_fulfilled，不是能力缺失的 NE。
- "像 NE"的直觉来自 production 侧的证据缺失感，根因是 production 的结构性盲区（见 F7）：
  `judge.py:_compact_capability_manifest` 只保留 `trace_fields` 命中的字段，而 parser 只输出
  了姓名条件，所以 production 的 evidence space 里**根本没有 planfullname**，只能
  "推测"能力清单没有保险字段 → 上一版误判 NE，新版虽判 NF 但 reasoning 仍然错误
  （"当前能力清单未提供保险字段或枚举"与真实 manifest 矛盾）。
- draft 的 full manifest 命中检测在 prompt 之外先把 `住院医疗保险 → planfullname` 算好，
  judge 直接使用该证据 → NF 判定精确、可审计。

### 问题 2：088 是 NE 吗？—— 是，draft 现在的判定符合用户直觉与 spec §11-3

- 核心目标（检索"7月盘客"目标客户）：能力清单无法确认"盘客"可表达（`condition_comparison
  .evaluable=false`，expected_source=not_available）→ 不得输出肯定业务结论 → **not_evaluable**。
- 边界子目标（透明告知、不虚构条件）：actual 提示类别与请求文本重叠（`request_notice_overlap`
  含"盘客"）且 conditions 为空 → **fulfilled**。
- production 判 fulfilled 等于对"核心检索目标已正确交付"给出了肯定结论，而该目标当前
  无 authority/能力依据 → 违反 §11-3"不得输出没有 Authority 支撑的肯定业务结论"。
- 上一版问题（F1：draft 把核心目标替换成边界型 expectation 后判 fulfilled）已修复；
  本版 draft 与 spec 口径一致。

### 问题 3：133 是 NE 吗？—— 是，draft 的 NE 是保守且正确的判定；production 的 NF 违反项目字段语义

- "中银保信"是机构名称（中国银保信），不是客户本人实体。`enhanced_rules` 与字段语义明确：
  机构名/公司名不得映射到 `searchClientName`（4 字及以上、含字母数字的标识不映射姓名）。
- actual 保持 conditions 为空 + "未识别到明确查询条件" = 完整边界处理 → 边界子目标 fulfilled。
- 核心目标（检索中银保信相关目标客户）：能力清单无机构名称字段 + 下游结果集未验证 →
  无法确认可交付性 → not_evaluable，不给肯定结论。
- production 的 NF 要求"把中银保信生成 searchClientName MATCH 条件"，等于**要求把机构名
  虚构为客户姓名条件**，与项目自身字段语义规则矛盾 → production 此判定不可采纳。
- 上一版结论（133=fulfilled，两方一致）基于"parser 边界处理完整即 fulfilled"的口径；本版
  draft 改为"核心交付 NE + 边界 fulfilled"，与 088 统一为同一 out-of-manifest 规则，
  且与用户"088/133 像 not_evaluable"的直觉一致。若坚持旧口径（parser 忠实即可 fulfilled），
  需在 spec 明确"judge 不评价核心业务目标可交付性"——当前 spec §11-3 支持 NE 口径。

---

## 三、与 spec 符合性 check list

| # | 检查项 | spec 依据 | 状态 | 说明 |
|---|---|---|---|---|
| C1 | Authority 运行时宿主无关（无 client_search/领域词引用） | authority.md §4.2、§12.3 | ✅ 通过 | `impl/core/authority_*.py` 零领域引用；EvidenceSpace/Materializer/ToolGateway/PermissionBoundary/Snapshot 组合成立 |
| C2 | 公共协议只暴露 AuthorityRequest / AuthorityResolution | §12.3 | ✅ 通过 | `schema/authority.py` 仅两个 frozen dataclass |
| C3 | authority.resolve 工具：缓存 / audit / snapshot | §5、§13 | ✅ 通过 | `authority_tool.py`；audit 记录 request/resolution/snapshot |
| C4 | gate：unresolved→not_evaluable、引用缺失→needs_human_review、resolved→不覆盖 | §8、§11-3 | ✅ 通过 | `authority_gate.py`；`draft/judge_execution.py` 已接入 |
| C5 | 调查产物存在（manifest/overview/contract/conflicts-scan） | investigate §13.3 | ✅ 通过 | 5 evidence_refs + 3 tool_requirements；4 unresolved anchors；冲突扫描 revision 固定 |
| C6 | unsupported 边界口径统一（能力缺失不给肯定结论：核心→NE，边界→fulfilled） | §11-3 | ✅ 通过（F1 已修） | `draft/judge.py` 规则统一为 out-of-manifest 核心 NE + 边界 fulfilled；088/133 实测输出与规则一致 |
| C7 | 多资料冲突/证据不足时调用 authority.resolve | §7、§8 | △ 部分通过 | 148 的字段归属已按权威 field notes 直接裁决为 planfullname（notes："具体产品全称→planfullname"），full manifest 枚举命中提供决定性直接证据，无需调用 authority（符合 §8"遇到标准冲突时才调用"）。但 30 条冻结集上 `authority_tool_call_ids` 全空，authority 运行时链路尚未被真实歧义 case 激活验证 |
| C8 | manifest 枚举配置完整（无 unresolved_enum_refs） | investigate §8 | ✅ 通过（draft） | full manifest 加载 field_enums + planfullname/abbrname/claimplancodename/profname 五源枚举；148 实测可见 `planfullname:[住院医疗保险]`。production 用 lean（按设计，防 436KB prompt），但见 F7 |
| C9 | 调查报告结构（结构化真相源 + governs 唯一决定性层） | investigate §15 | △ F5 未动 | 仍缺 `docs/authority-investigation-report.json/.md` 与 MaterialInvestigation/AuthorityFinding/governs 层；需与用户确认走补产物还是收窄 spec §15 |
| C10 | 数据/产物同步一致性 | check d) | ✅ 通过（F6 已修） | solidify receipt 已重建（candidate_role_sha256 c76478e8...、manifest_sha256 e4d33d45...）；全量 610 项通过 |

---

## 四、发现的问题

### F1（P1）draft unsupported 规则自相矛盾 —— 已修复（关闭）
- 旧规则 A（判 not_fulfilled、不得判 NE）与规则 B（all_conditions_unsupported 判 fulfilled）
  矛盾，088 draft 误判 fulfilled。
- 现规则统一：请求条件命中清单 → 遗漏判 not_fulfilled；未命中清单（能力边界外）→ 核心
  交付 NE + 边界处理 fulfilled。088 实测恢复为 NE+fulfilled。

### F2（P2）148 的 production NE 依据不成立 —— 已关闭
- production 曾以"能力清单未提供保险字段/枚举"判 NE；事实相反（planfullname 枚举含
  精确值"住院医疗保险"）。本版 production 已改判 NF，但 reasoning 仍保留错误表述（见 F7）。

### F3（P2）148 字段归属歧义（pCategorys vs planfullname）—— 已由 draft 解决（关闭）
- draft 现按权威 field notes 将"住院医疗保险"归入 planfullname（产品全称），full manifest
  提供枚举命中证据；不再依赖 prompt 里的 pCategorys 大类规则。
- 归属可直接裁决（notes + 枚举决定性），未触发 authority 调用，符合 §8 调用规则。

### F4（P3）abbrname / planfullname 枚举加载不完整 —— 已修复（关闭）
- full manifest 现加载 5 个枚举源（field_enums + planfullname + abbrname +
  claimplancodename + profname），148 实测可见 `planfullname:[住院医疗保险]`；
  产品名类 case（"买了 e生保"、"投保险种名称为 X"）可获得确定性枚举证据。

### F5（P3）调查产物与 investigate-authority-judge.md §15 有差距；governs 唯一决定性体现弱 —— 仍存在
- 仍缺 `docs/authority-investigation-report.json/.md`（结构化真相源 + 确定性渲染），
  contract 的 authority_analyses 是"问题-冲突-未决"锚点，无
  MaterialInvestigation / AuthorityFinding / governs 分析层（§2.2、§8、§11）。
- 二选一：按 §15 补产物，或确认轻量 manifest 路线后在 spec 收窄 §15。涉及协议修改，
  需用户确认后执行。

### F6（P3）solidify receipt 过期 —— 已修复（关闭）
- receipt 已重建；全量回归 610 项全部通过。

### F7（P2）production 结构性盲区 —— 仅记录，不改动（用户要求不动 production）
- `impl/projects/client_search/judge.py:_compact_capability_manifest` 按 `trace_fields`
  过滤 manifest：parser 没输出的字段（如 148 的 planfullname）在 production 证据空间中
  不可见 → 148 production 仍称"能力清单未提供保险字段或枚举"（与 manifest 矛盾）；
  133 production 则要求把机构名虚构为客户姓名条件（违反项目字段语义规则）。
- 根因是 production 的 compact-by-trace_fields 设计，而非枚举加载。draft 通过
  full manifest 命中检测绕开了该盲区。若后续允许动 production，最小修复是把
  "请求文本→枚举反查命中字段"并入 production 的 manifest 注入（与 draft 同一来源）。

---

## 五、测试状态

- 2026-08-02 全量回归：**610 passed**（`pytest -q --ignore=hooks/api-check`）。
- authority / judge / investigation / capability / solidify 相关测试全部通过
  （`test_authority_enforcement.py`、`test_authority_gate.py`、`test_authority_runtime.py`、
  `test_client_search_judge_investigation.py`、`test_client_search_capability_manifest.py`、
  `test_judge_authority_analysis.py`、`test_solidify_receipt.py` 等）。
- 三个 case 实测（148/088/133）draft 判定均不劣于 production，且证据链更正确：
  - 148：draft 精确定位缺失条件；production 方向对但证据错误。
  - 088：draft NE（spec §11-3 合规）；production 肯定结论无依据。
  - 133：draft 尊重机构名语义；production 要求虚构客户姓名条件。

---

## 六、遗留决策点（待用户确认）

1. **F5**：调查产物按 §15 补齐 governs 层，还是收窄 spec §15 要求（轻量 manifest 路线）？
2. **authority 运行时链路实测**：30 条冻结集 authority_tool_call_ids 全空，authority 尚未在
   真实歧义 case 上激活；建议造一个真实字段归属冲突 case（如产品全称同时命中多字段且 notes
   不裁决）验证 authority.resolve 端到端。
3. **133 口径**：确认采用"核心 NE + 边界 fulfilled"（当前 draft，与用户直觉一致），
   还是回退"parser 忠实即可 fulfilled"（旧口径，需在 spec 明确 judge 不评价可交付性）。
4. **F7**：production 盲区是否立项修复（当前按用户要求不动 production）。
