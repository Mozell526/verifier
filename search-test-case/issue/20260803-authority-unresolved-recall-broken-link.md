# 20260803 authority unresolved 决议召回断链（008 孤儿单误判 resolved）

## 现象
- 冻结集 008（输入「孤儿单」）draft 判 `not_fulfilled`（assessment 组合 fulfilled+not_fulfilled），
  按决议 #7 应为 `not_evaluable`（依据不足）。
- production 判 `fulfilled`；draft 比 production 在 008 上更差（把已知 unresolved 冲突判成了确定的 not_fulfilled）。

## 根因（已定位，含现场证据）
1. 调查侧决议 `judge-authority-resolutions.md` 的 **resolution.7** 明确 `status=unresolved`
   （孤儿单归一冲突：`value_mappings`「纯存续单客户」 vs `field_definitions`「在职有效客户」）。
2. authority 现场会话（trace `authority-2026-08-03T19:48:32Z-341f3ba6-cad.json`）：
   - search 返回 9 个候选，**全部是** `business-enhanced-rules` / `business-field-definitions`
     的字段切片，resolutions 文档与 value_mappings 都没有出现；
   - 只 load 了 C2（enhanced_rules orphanType）+ C6（field_definitions orphanType），
     两侧一致说「在职有效客户」，于是 authority 自信 resolved；
   - 全程没有看到决议 #7 的 unresolved 状态与 value_mappings 冲突面。
3. 断链位置：
   - resolutions 文档已物化为 unit `authority-ref-5cd1a74ac87e4e7f`（active，可搜索），
     但检索索引只含 `name + description`（`_record_search_text`），description 是英文摘要，
     与中文查询「孤儿单 / orphanType / 纯存续单客户」向量相似度不足，top-9 召回不到；
   - 对照 078/128（正确 unresolved）：078 走的是工具路径（`field.search_keys` 找不到字段），
     不是靠召回 resolutions 文档——说明当前「已知冲突面」能否被 authority 消费完全依赖
     检索运气 + 工具结果，机制不稳。

## spec 依据
- `investigate-authority-judge.md` §17：`status="unresolved"` 的 Finding 不生成复用配对，
  「在未命中配对时提示 Runtime 该问题已知证据不足、需要先补证而非重复综合」。
- 008 正是「未命中配对 → 应提示已知证据不足」的场景，实现未落地。

## 修复方向（待确认，不预先实施）
- 方向 1（调查层物化，主修）：resolutions 文档按决议条目切片物化（类似 field_definitions
  的字段级切片），每条决议独立 unit，`name/description` 用中文并携带 field/governs/status
  关键词，保证「孤儿单 / orphanType」查询稳定召回 #7。
- 方向 2（authority 消费规则，轻量）：`_resolve_system_prompt` 增加通用规则：归一/冲突类
  问题先检索既有决议与冲突扫描资料；命中 unresolved 决议或资料冲突面时不得单侧定论，
  应返回 unresolved 并引用决议单元。
- 不做：case 级硬编码、runtime 主动调查（维持「runtime 不主动调查」边界）。

## check 附带发现（P2，待评估）
- `_unsupported_boundary_evidence` 的 `decision_rule` 是高度规则化的判定文案
  （all_conditions_unsupported / graceful_degradation 等形状），有过度规则化风险。
- `_operator_conflict_fields` 依赖关键词（操作符/operator/MATCH/RANGE）推断冲突面，启发式脆弱。
- authority `load_context_units` 上限 8 条，而 search 单次可返回 10 个候选（078 一次 load 7 条，
  未触顶；属设计口径不一致，非当前阻塞）。
- 008 之外 9 条 diff 中：058/113 draft 更优（贴决议 #9/#8）；038/073/088/148 draft 偏严，
  疑似过判 not_fulfilled，需业务侧复核口径（fulfilled.md 边界）。

## 验证
- authority/judge 相关单测 69 条全过（含本 issue 相关机制）。
- 修复后需在冻结集上重跑 008 验证转 `not_evaluable`，并抽查 038/073/088/148 是否回归。
