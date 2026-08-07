# Draft Authority Investigate / Solidify 通用门禁设计

日期：2026-08-07  
状态：待用户审核  
范围：Draft 协议的 Investigate 与 Solidify 阶段；client_search 作为首个验收项目

## 1. 背景

Draft 已具备 AuthorityEnvironment、`authority.resolve`、Search→Load、EvidenceRef、Tool audit 与 Authority Gate 等运行时基础，但当前仍可能出现：

- Investigate 生成了格式合法但语义空泛的 Authority 报告；
- 调查报告记录了宽泛 coverage gap，却没有把冲突绑定到 Runtime 可查询的判断对象；
- Solidify 只证明普通 Judge 合同被加载，没有证明 Authority 资产被 Runtime 消费；
- 已激活资料对同一业务对象冲突，Runtime 却无法发现；
- Authority decision question 只覆盖局部操作符问题，没有覆盖会改变 blocking 结论的核心业务决定；
- AI 通过摘要、历史结论、当前行为或硬编码样本答案绕过真实证据链。

client_search 的代表性表现包括：

- “孤儿单”的 `value_mappings` 与字段 notes 冲突，但没有形成可消费的冲突资产；
- `licensePlateNo` 的 supported/unsupported 声明冲突，但 Solidify 后 Runtime 没有稳定召回；
- “少儿万能险”只裁决生日字段操作符，遗漏更核心的产品语义决定。

本设计不新增独立 Authority 阶段。Authority 调查仍属于 Investigate，Authority 资产固化仍属于 Solidify。本设计只补充通用门禁，验证 AI 是否真正完成了这两阶段的 Authority 工作。

## 2. 目标与非目标

### 2.1 目标

门禁必须证明：

1. 调查资料真实、可定位、可加载且定位语义明确；
2. 同一判断对象上的一致 claim、冲突 claim 与覆盖缺口能被结构化发现；
3. 冲突不能通过删除资料、选择当前行为或引用历史答案被静默消解；
4. Investigation 产物可以针对真实决定问题完成 Search→Load 与 resolved/unresolved 模拟；
5. Solidify receipt 能证明 Material、Claim、Coverage Gap、Key-Index 和 Tool 已进入 Runtime；
6. 同一组 Probe 经 Solidify 后可以通过正式 Runtime 接口重放；
7. 门禁按通用问题类型工作，不依赖项目名、case ID 或业务关键词；
8. 小资料不被迫建立索引，大资料不允许全量塞入 Prompt；
9. 门禁失败阻止进入下一阶段，但不伪装成业务三态结果。

### 2.2 非目标

第一版不做：

- 预枚举未来所有 Authority decision question；
- 要求 Investigate 提前解决全部 coverage gap；
- 强制所有资料使用 embedding；
- 强制所有项目建立 Key-Index；
- 用冻结业务案例数量作为 Investigation/Solidify 合格条件；
- 修改 Production Judge 或自动 Promote；
- 把 Runtime 的 Authority 漏选/过选效果评测全部塞入本门禁；
- 新建与现有 AuthorityResolution、EvidenceRef、InvestigationManifest 重复的公共协议对象。

## 3. 核心原则

### 3.1 Claim-centric，而不是 case-centric

门禁围绕“判断对象 + 条件 + 结论类型 + 来源 claim”工作，不围绕“孤儿单”“车牌号”等样本关键词工作。

稳定标识至少包含：

```text
subject.kind
subject.key
conditions
conclusion_kind
```

例如：

```text
value_mapping / orphanType:孤儿单 / 当前产品版本 / normative_rule
capability_boundary / licensePlateNo / 当前搜索链路 / inlive_boundary
operator_support / familyInfo.familyclientbirthday / 当前下游协议 / external_fact
```

### 3.2 调查报告不是 Runtime 结论缓存

Investigate 可以登记资料定位、claim、冲突和 coverage gap，但不得提前为未来 Case 产出 resolved/unresolved 结论稿。Runtime 仍根据当前 decision question 和 Environment snapshot 现场综合。

### 3.3 结构通过不等于语义通过

Schema validator 只验证对象合法。是否真正调查到位由 Claim 冲突扫描和 Authority Probe 验证。

### 3.4 Search 与 Evidence 分离

SearchHit 只能导航；只有 Load 后物化且绑定 revision/hash 的内容可以进入 `basis_evidence_ref_ids`。

### 3.5 不制造不必要资产

- 小资料：允许直接 Load；
- 大资料：要求 Key-Index Search→Load；
- 动态事实：要求 VerifiableTool；
- 没有冲突：不要求伪造业务冲突；
- 没有 embedding 的必要性或实验证据：不得把 embedding 宣称为正式能力。

## 4. 总体流程

```text
Investigate AI
  ↓
G1 资料真实性与定位门禁
  ↓
G2 Claim 覆盖与冲突门禁
  ↓
G3 Investigation Authority Probe
  ↓
允许 Solidify
  ↓
Solidify AI
  ↓
G4 Authority 资产映射门禁
  ↓
G5 Runtime Authority Probe 重放
  ↓
允许 Draft Loop
```

每个门禁独立产出 receipt。不得用后续门禁成功覆盖前序门禁失败。

## 5. G1：资料真实性与定位门禁

### 5.1 输入

- `InvestigationManifest`
- `AuthorityInvestigationReport`
- Manifest 登记的 EvidenceRef、artifact、Key-Index 和 ToolRequirement
- 实际文件或来源系统 metadata

### 5.2 每份 Material 的最低要求

每份 Material 必须可确定：

- `material_id`；
- 真实 `source_ref_ids`；
- `source_position`；
- 可决定的 `conclusion_kinds`；
- `governs`；
- `conditions`；
- `related_to`；
- revision 或 sha256；
- direct Load、Key-Index Load 或 Tool 的可执行路径。

`source_position` 至少能表达以下既有材料定位语义：

- 正式规范；
- 业务批准资料；
- Runtime 能力事实；
- 当前实现行为；
- 历史案例；
- 辅助参考。

具体字段表示优先复用 `material-positioning.md` 与 Authority 调查报告现有 schema，不为这些标签另建平行公共枚举。

### 5.3 硬失败

以下任一情况使 G1 失败：

- `governs` 没有真实 EvidenceRef；
- EvidenceRef 位置不存在或 hash/revision 不匹配；
- 只有摘要，没有原始资料的 Load 路径；
- SearchHit 被登记为决定性 Evidence；
- 当前行为或历史案例被无依据地定位为正式规范；
- Material 没有适用条件，导致适用范围不可判断；
- 同一 Material 的定位声明自相矛盾；
- 大资料既没有可用 Key-Index，也没有被明确判定为可安全整读的小资料。

### 5.4 输出

`investigation-authority-material-receipt.json`，至少记录：

```text
material_id
source_ref_ids
position_valid
revision_valid
load_route
gate_status
failures
```

## 6. G2：Claim 覆盖与冲突门禁

### 6.1 Claim 记录

Claim 是调查报告内部的可消费索引，不是新的 Runtime resolution。第一版优先扩展 AuthorityInvestigationReport 或其确定性派生产物，不修改公共 AuthorityRequest/Resolution。

最小语义：

```json
{
  "claim_id": "stable-id",
  "subject": {
    "kind": "value_mapping | field_semantic | operator_support | capability_boundary | responsibility_boundary | other",
    "key": "project-stable-key"
  },
  "claim": "source-stated conclusion",
  "conditions": {},
  "conclusion_kind": "normative_rule | external_fact | inlive_boundary",
  "source_ref_ids": ["evidence-ref"],
  "material_ids": ["material-id"]
}
```

`subject.kind` 不做封闭业务枚举；通用 validator 只要求非空和稳定，项目可以增加类型。协议保留上述推荐类型用于跨项目审计。

### 6.2 冲突识别

在相同：

```text
subject + conditions + conclusion_kind
```

范围内，若存在不能同时成立的 claim，则必须满足以下之一。

#### 已由调查资料明确解决

必须记录：

```text
resolved_by
basis_source_ref_ids
resolution_reason
```

`resolution_reason` 必须说明为什么某资料在当前条件和上下游中具有决定性，不能只写“优先级更高”或“以最新资料为准”。

#### 尚未解决

必须绑定：

```text
coverage_gap_id
basis_source_ref_ids
required_evidence
```

`required_evidence` 必须指出能够改变结论的资料类型、适用条件或验证方式，不能只写“需要更多资料”。

### 6.3 冲突扫描职责

冲突候选由两条路径共同产生：

1. 确定性扫描：相同 subject 范围内的枚举值、布尔能力声明、操作符集合和明确结构化 claim；
2. 受约束 AI 审查：识别自然语言 claim 是否互斥，并且必须输出 claim/material/evidence ID，不能仅给自然语言判断。

AI 不能修改或删除输入 claim。AI 审查结果只补充冲突关系；最终 validator 根据完整 claim 集校验 resolution/gap 是否存在。

### 6.4 硬失败

- 发现冲突但没有 resolution 或 coverage gap；
- coverage gap 没有绑定具体 subject；
- resolution 没有决定性 Evidence；
- `required_evidence` 不可执行或不具体；
- 报告 claim 数量少于从结构化资料确定性抽取出的 claim 数量；
- 通过隐藏、删除或合并互斥 claim 消除冲突；
- 使用历史 Judge verdict 作为规范性冲突的唯一裁决依据。

### 6.5 输出

`investigation-authority-claim-receipt.json`，包括：

```text
claim_count
subject_count
conflict_count
resolved_conflict_count
unresolved_conflict_count
uncovered_conflicts
claim_source_coverage
```

## 7. G3：Investigation Authority Probe

### 7.1 目的

验证 Investigation 产物不仅“写了报告”，而且能够支持真实的资料发现、加载和保守裁决。

### 7.2 Probe 类型

通用 Probe 类型：

1. 单一决定性资料，应 resolved；
2. 多份一致资料，应 resolved；
3. 同 subject 冲突且无决定性资料，应 unresolved；
4. supported/unsupported 或职责边界冲突，应 unresolved；
5. 资料相关但条件不适用，应被排除；
6. 只有 current behavior，没有正式标准，应 unresolved；
7. 大资料必须 Search→Load；
8. 小资料允许 direct Load；
9. 动态事实必须经过对应 VerifiableTool。

只运行项目实际具备的通道和问题类型。若没有真实冲突，Harness 可以使用隔离的合成冲突验证 unresolved 机制；合成资料不得写入正式 Investigation Evidence 空间，也不得参与 Draft Loop。

### 7.3 Probe 选择

Probe 由 Harness 根据 Investigation 产物确定性选择：

- 所有真实冲突 subject，第一版上限 5 个；超过上限时按稳定 ID 排序并覆盖不同 conclusion_kind；
- 至少一个无冲突 subject；
- 每种实际出现的 `conclusion_kind` 至少一个；
- 每种实际声明的 load route 至少一个；
- 如果冲突 subject 超过上限，未抽中的冲突仍必须通过 G2 静态覆盖门禁。

不得由 Investigate AI 自选一组只容易通过的 Probe。

### 7.4 Probe 审计

每条 Probe 必须记录：

```text
decision_question
selected_subject
search_calls
load_calls
tool_calls
excluded_material_ids + reason
basis_evidence_ref_ids
resolution status
required_evidence
environment_snapshot_sha256
```

### 7.5 硬验收

- 所有真实冲突 Probe 必须 unresolved，或具有符合协议的决定性 resolved 依据；
- resolved 必须有 statement、reason 和 basis Evidence；
- unresolved 必须有具体 reason、已发现 basis Evidence 和 required evidence；
- 条件不适用资料不得进入 basis；
- 大资料不得绕过 Search→Load；
- SearchHit 不得进入 basis；
- current behavior 不得单独决定 normative rule；
- Evidence revision 必须与 Environment snapshot 一致。

### 7.6 输出

`investigation-authority-probe-receipt.json`，包含每条 Probe 的状态和整体 `passed/failed`。Probe 失败时不得进入 Solidify。

## 8. G4：Solidify Authority 资产映射门禁

### 8.1 Solidify receipt 必须证明的映射

```text
Material              → Runtime Context / Evidence
Claim Index           → Authority Search / Lookup
Coverage Gap          → Runtime 可发现的 unresolved 背景
Key-Index             → Search Tool + Load Tool
ToolRequirement       → VerifiableTool
Investigation snapshot→ AuthorityEnvironment snapshot
```

每条 mapping 复用现有 Solidify receipt 模式：

```text
mapping_id
source_ids
asset_ids
runtime_observables
```

### 8.2 Runtime observable

第一版至少包含：

- Material 可按 EvidenceRef 加载；
- Claim 可按 subject 或 decision question 导航；
- Key-Index SearchHit 可以继续 Load；
- coverage gap 的 required evidence 可被 Authority 看见；
- AuthorityEnvironment snapshot 与 Investigation receipt 一致；
- ToolRequirement 对应 Tool 已注册且 schema 匹配。

### 8.3 硬失败

- 决定性 Material 未进入 Environment；
- Claim Index 只存在于报告文件，Runtime 没有查询路径；
- Key-Index 存在但 Search/Load Tool 未注册；
- coverage gap 在固化后丢失；
- Candidate 只能读取摘要，不能加载原始 Evidence；
- snapshot 与 Investigation revision 不一致；
- Candidate Role 或 Prompt 内嵌 Probe 答案以绕过资产消费；
- receipt 只证明 `authority.resolve` 字符串或函数存在，没有证明资产可消费。

## 9. G5：Runtime Authority Probe 重放

### 9.1 重放规则

G3 通过后，Solidify 必须使用同一份冻结 Probe suite 重放。重放只能走候选 Runtime 正式入口：

```text
AuthorityEnvironment
→ Search / direct Load / Tool
→ Load Evidence
→ authority.resolve
→ Tool audit
```

不得直接读取 Investigation 中的预期结果，不得在 Candidate Role 中注入 Probe verdict。

### 9.2 附加验收

- Environment snapshot 与 G4 receipt 一致；
- Tool audit 真实存在；
- 相同 decision question 在同一任务中不重复解析；
- unresolved 的 required evidence 不丢失；
- resolved 的 basis Evidence 仍指向原 revision；
- G3 与 G5 的状态差异必须能归因到资产映射或 Runtime 消费问题；
- 所有失败提供 material/claim/asset/tool ID，不接受仅自然语言“模型判断错误”。

### 9.3 阶段判定

| G3 | G5 | 判定 |
|---|---|---|
| failed | not run | Investigation 不合格 |
| passed | failed | Solidify 不合格 |
| passed | passed | 可进入 Draft Loop |

## 10. AI 语义交接审查

### 10.1 Investigate Review

受约束 AI 只回答：

1. objective 依赖哪些 conclusion_kind；
2. 对应资料是否已调查并正确定位；
3. 已发现冲突是否全部进入 Claim Index、resolution 或 coverage gap；
4. Runtime 是否有办法按当前决定问题找到并加载资料。

每个结论必须引用 Manifest、Material、Claim、Coverage Gap、EvidenceRef 或 ToolRequirement ID。无 ID 的自然语言“调查充分”不构成通过依据。

### 10.2 Solidify Review

受约束 AI 只回答：

1. 哪些 Authority 调查资产被固化；
2. 每个资产对应哪个 Runtime observable；
3. G5 是否证明 Runtime 真正消费了这些资产。

AI Review 不能覆盖确定性 validator 或 Probe 失败。

## 11. 阶段状态与失败报告

门禁状态保持分层，不混入业务三态：

```text
investigation_structure_failed
investigation_evidence_failed
investigation_authority_coverage_failed
investigation_authority_probe_failed
solidify_authority_mapping_failed
solidify_authority_replay_failed
ready_for_draft_loop
```

失败记录至少包含：

```text
gate_id
stage
subject_id / material_id / asset_id / tool_id
failure_reason
evidence_refs
required_action
```

门禁失败：

- 阻止进入下一阶段；
- 不产出 fulfilled/not_fulfilled/not_evaluable；
- 不参与 Production/Draft 业务效果比较；
- 不允许通过降低 schema、删除冲突资料或跳过 Probe 放行。

## 12. 反投机与泛化门禁

第一版必须加入以下审计：

- 禁止按 project ID、case ID、用户原句硬编码 Probe verdict；
- 冲突检测以 subject/claim 为中心；
- Probe expected status 来自 claim 拓扑与资料定位，不来自历史 Judge 输出；
- 测试同时使用真实项目材料和无业务关键词的合成材料；
- 删除任一冲突 claim 后 hash/claim coverage 必须变化，不能静默通过；
- Candidate Prompt 不得包含 Probe 的 expected resolution；
- embedding 只能在实验结果证明改善 Search→Load 后被选为正式 provider；
- 不得通过全量加载资料绕过 Key-Index；
- 不得用 fallback 自动产生“安全 unresolved”掩盖 Search/Load 失效，工具失败必须单独记录。

## 13. client_search 首轮验收

client_search 仅用于验证通用机制，不得把业务词写入 Core validator。

### 13.1 语义映射冲突

调查资产应能表达同一 subject 上的不同 claim，并在缺少决定性资料时形成 coverage gap。Probe 应得到 unresolved。

### 13.2 能力边界冲突

字段能力资料与业务边界资料对 supported/unsupported 声明冲突时，Probe 应得到 unresolved；不得由字段工具或冻结背景单方面覆盖另一方。

### 13.3 核心决定问题覆盖

产品语义与操作符能力是两个独立 subject。Probe suite 必须能分别验证，不能用局部操作符裁决替代核心业务语义裁决。

### 13.4 非冲突直接证据

普通字段、枚举和确定性 Comparator case 必须证明无需 Authority 也能完成调查资产加载，防止 Authority 过度绑定。

## 14. 第一版最小实施范围

第一版只实现：

1. G1 Evidence/Material 确定性校验；
2. Claim Index 的最小派生产物；
3. 结构化 claim 冲突扫描；
4. 受约束 AI 的自然语言冲突补充审查；
5. G3 Probe suite 生成和 Investigation 模拟；
6. Solidify receipt 的 Authority mapping 与 observable；
7. G5 同 Probe Runtime 重放；
8. client_search 的语义映射冲突、能力冲突、核心问题拆分和直接证据四类验收；
9. 对应 validator、receipt 和回归测试。

第一版不把 Claim Index 升级为公共 Runtime schema。先以 AuthorityInvestigationReport 的版本化扩展或确定性派生 artifact 落地；只有第二个项目证明需要跨实现直接交换时，才评估公共 schema。

## 15. 验收标准

### Investigate

- 所有 Material 的 Evidence、revision 和 Load route 可验证；
- 所有确定性可发现冲突都有 resolution 或 coverage gap；
- 所有 coverage gap 绑定具体 subject 和 required evidence；
- Probe 覆盖实际 conclusion_kind 和 load route；
- 真实冲突 Probe 100% 得到合规 unresolved 或有决定性依据的 resolved；
- 0 个 SearchHit 直接作为 basis Evidence；
- 0 个 current behavior 单独决定 normative rule。

### Solidify

- Investigation Authority 资产 mapping 覆盖率 100%；
- 每个 mapping 至少一个成功 runtime observable；
- 同组 Probe 经正式 Runtime 重放全部通过；
- snapshot/revision 一致；
- Tool audit 完整；
- 无 case-specific 硬编码；
- 无 Prompt 内嵌 Probe 答案；
- G5 通过后才能进入 Draft Loop。

## 16. 与既有协议的关系

- `spec/alg/investigate-authority-judge.md`：继续定义 Authority 调查语义和产物；本设计补充可执行门禁。
- `spec/alg/authority.md`：继续定义 Runtime AuthorityRequest/Resolution、Search→Load 和消费规则；本设计不修改其职责边界。
- `spec/alg/investigate-judge.md`：继续定义 Judge BusinessExpectation、LiveBoundary、EvaluationDimension 和 Authority Gate；本设计只验证其 Authority 上游资产是否可用。
- Draft Skill：在 Investigate→Solidify 与 Solidify→Draft Loop 两个跃迁点执行门禁。
- Solidify receipt：复用现有 source→asset→observable 模式，增加 Authority 专项 mapping，不另建平行 receipt 协议。

## 17. 后续实施顺序

1. 明确现有 AuthorityInvestigationReport 的最小可扩展点；
2. 实现 G1 Material validator；
3. 实现 Claim 派生与确定性冲突扫描；
4. 接入受约束 AI 冲突审查；
5. 实现 Probe suite 与 G3 receipt；
6. 扩展 Solidify receipt Authority mappings；
7. 实现 G5 Runtime replay；
8. 使用 client_search 四类场景验证；
9. 扩展到第二个项目验证泛化；
10. 通过后再评估是否同步进入长期 spec 正文。
