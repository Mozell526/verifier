# Draft Skill 落实不到位：修复方案流程文档

> 状态：方案，待确认后实施。基于 2026-08-16 的核查结论。
> 范围：draft skill 合同与执行链（含 client_search draft judge），以及轴2
> `spec/alg/capability_carrier.md` 落地时的防重蹈条款。
> 原则：不推翻现有四阶段结构（Investigate / Solidify / Draft Loop / Promote），
> 只把"文案义务"补成"可执行验收"，把"可无限搁置"改成"有上限的搁置"。

## 0. 核查结论（问题清单，修复对象）

| # | 层 | 问题 | 证据位置 |
|---|---|---|---|
| P1 | 执行 | `judge.py` §3.1 开关文案错装：`authority_enabled=True` 分支注入"Authority 关闭时…"规则；关闭分支把 NE 全禁（比 fulfilled.md §3.1 更严，输入坏/完全无关本是合法 NE） | `impl/projects/client_search/draft/judge.py` L1459-1463、L1520-1525 |
| P2 | 执行 | 硬预判旁路残留：`pre_judge` / `apply_last_word` / field_sufficiency 硬口可绕过 LLM 与 authority 直接定 F/NF（fulfilled.md §9 任务4 残留） | `draft/judge.py` L1763-1765、L1784；`field_sufficiency.py` L306-319 |
| P3 | 流程 | 候选手改旁路：judge.py 在 solidify 之外被改，收据 stale 在 run 后才炸，整轮作废（history/053）；investigation 产物（8/12-13）与 judge.py（8/16）脱节 | `history/053/iterations/001-run.json` |
| P4 | 合同 | 净胜不可机算：`relative_improvement_no_regression` 由 harness 自填，review 脚本只查字段齐全不数翻转案 | `.agents/skills/draft/SKILL.md`、`review_iteration.py` |
| P5 | 合同 | criterion fail 不拦路："fail 不否决 improved"无豁免登记（052 轮 `atomic_pre_actual_expectations` fail 照走） | `history/052/iterations/001-role-review.json` |
| P6 | 流程 | 搁置无上限：不计分案（083/058/103/048/138）、未修问题（058 过严 iter4→5）、`.stale-*` gate 反馈，都可无限期滚动，不阻塞任何后续步骤 | `.state/judge/` 各处 |
| P7 | 合同 | knowledge.md 闭环死锁：只在 promotion 前更新，但 53 轮从未 promote，故永远空模板；验收只打印 mtime | `.agents/skills/draft/judge/knowledge.md` |
| P8 | 合同 | 双合同并存：`.claude/skills/draft/` 旧四层模型未删，与权威版 `.agents/skills/draft/` 漂移 | 两目录 |
| P9 | 合同 | 调查合同缺强制审查项："如实拒绝≠办成 / 三态互斥 / 不许逃逸"未进 `judge-investigation-contract.json`（fulfilled.md §9 任务1） | `draft/investigation/judge/docs/` |

根因：合同把执行质量押在 LLM 自觉上，状态机允许 fail / 搁置 / 手改不阻塞后续，
最便宜的路径总是赢。

---

## 阶段一：修 Bug（P1、P2）——收益直接，先做

### 1.1 修 §3.1 文案错装（P1）

改动：`impl/projects/client_search/draft/judge.py`

- L1459-1463 两分支文案按 fulfilled.md §3.1 重排：
  - `authority_enabled=True` 分支：只保留开启模式规则（先形成意图/交付/标准问题，
    再消费 resolution；职责外 NE 仅在 resolved 之后）；删除全部"Authority 关闭时…"语句；
  - `else` 分支：改为"依据当前 trace 与确定性工具尽判 F/NF；能力边界候选、
    不支持提示、空条件不得触发 NE；输入坏、完全无关、actual/trace 不可得仍可判 NE
    并写明成因"——即恢复 §3.1 允许的合法 NE 成因，不再全禁；
- L1520-1525 无条件拼接的混写段：拆进对应 `authority_enabled` 分支，
  每个分支只包含本模式的规则；
- **同步修订 review 判据**：ROLE.md / review 的 `not_evaluable_evidence_gap`
  现按"Authority 关着不要 NE"打分（052 轮把 NE=0/30 记为 pass），必须先改成
  "关闭时 NE 仅限输入坏/完全无关/actual 不可得"，再改 prompt——顺序反了
  review 会把修复后的正确行为判成退化。

验收：

- 构造 `authority_enabled` 真/假两份 system prompt 快照，断言：开启分支不含
  "Authority 关闭时"字样；关闭分支包含"输入坏/完全无关"合法成因、不含
  "只判 fulfilled/not_fulfilled"全禁句；
- 冻结 30 条重跑：预期 输入坏/完全无关 类 case 恢复 NE（如有），其余逐 case 不退化。

风险：关闭分支放开合法 NE 后，个别原判 NF 的案子可能翻 NE——逐 case 对照，
翻转只允许发生在成因为输入坏/完全无关的案子上。

### 1.2 收硬预判旁路（P2）

改动：

- `pre_judge`（`result_if_speaks`）与 `apply_last_word` 保留的每个硬判路径，
  逐条核对 fulfilled.md：确定性可证的（如输出协议校验失败）保留；
  涉及业务语义预判的（field_sufficiency 硬口按裸词/字段直接定 NF），改为
  只产出"待核对提示"注入 prompt 证据区，最终状态由 LLM 判定；
- 每条保留的硬路径在代码注释标注 fulfilled.md 依据条款。

验收：冻结集重跑无退化；grep 确认无"绕过 LLM 直接写 status"的业务语义路径。

风险：去掉硬口后个别案子判定可能变松——用冻结集翻转清单人工过一遍。

---

## 阶段二：止血（P3、P8）——封旁路、删旧版

### 2.1 候选手改旁路前置拦截（P3）

改动：`draft_loop.py run`（或其前置校验）：

- 现状：solidify receipt 的 `candidate_role_sha256` 在 run 执行中才校验、炸掉整轮；
- 改为：run 启动前先校验候选文件 sha 与 receipt 一致；不一致直接拒绝启动，
  提示"候选已在 solidify 之外变更，先重跑 scripts/solidify.py 更新收据"；
- receipt 校验范围补齐：候选模块 + `role_assets` 声明的全部文件。

验收：手改 judge.py 一处 → `draft_loop.py run` 拒绝启动且给出修复指令；
恢复后可正常启动。

### 2.2 删除旧合同目录（P8）

改动：删 `.claude/skills/draft/`（含 judge/ROLE.md、knowledge.md 副本），
只保留 `.agents/skills/draft/`。若有引用旧路径的文档/脚本，一并改指权威路径。

验收：`rg "claude/skills/draft"` 全仓无引用。

风险：无（AGENTS.md 原则：过时的直接删，不留兼容层）。

---

## 阶段三：合同加固（P4、P5、P6、P7、P9）

### 3.1 净胜机算（P4）

改动：`review_iteration.py`（或新增 `score_iteration.py`，被 review 强制调用）：

- 从 `<NNN>-run.json` 逐 case 读取 Current/Draft 的 overall status，机算：
  win / loss / tie / 不计分 四类计数与净胜值；不计分案必须带机器可读的
  `excluded_reason`（人判不完 / 歧义-缺 / 检索缺口 / 工具中断 / 其他+说明）；
- `relative_improvement_no_regression` 的 pass/fail 由机算结果决定：
  loss>0 → fail；净胜≤0 → 不得 improved；harness 只填解释，不填结论；
- 机算结果落盘 `<NNN>-score.json`，review 收据引用其 sha256。

验收：伪造一份 harness 自称净胜+5 但机算净胜-1 的 review → 被拒绝。

### 3.2 criterion fail 豁免登记（P5）

改动：review 合同与 `review_iteration.py`：

- 保留"个别 fail 不否决 improved"，但改为白名单制：每个 fail 的 criterion
  必须附 `waiver`（豁免理由 + 计划处理轮次），无 waiver 的 fail → decision
  强制降为 `unchanged` 且 route 不得为 `promotion_checks`；
- waiver 进 pending 清单（见 3.3），受轮数上限约束。

### 3.3 搁置上限：pending 清单（P6）

改动：`.state/<role>/pending.json`（新文件）+ `draft_loop.py` 状态机：

- 三类条目统一登记：不计分案、fail-criterion waiver、stale gate feedback；
  每条含：首次出现轮次、原因、计划出路（Investigate 补料 / Solidify 改资产 /
  人拍板）；
- 上限：同一条目滚动超过 3 轮未清 → run 拒绝启动，强制二选一：
  route 回对应阶段处理，或人工确认延期（延期记录进条目，再给 3 轮）；
- `.stale-*` 重命名文件禁止：gate feedback 只允许"已解决（删除）"或
  "进 pending 清单"，不允许改名搁置。

验收：构造一条 4 轮未清的不计分案 → run 拒绝启动；人工延期后可再跑。

### 3.4 knowledge 沉淀解锁（P7）

改动：合同触发点从"promotion 前"改为"每轮 review 后"：

- review 产出中新增 `knowledge_delta` 字段：本轮验证过的事实（可为空但必须显式
  声明 `none` + 理由）；累计 3 轮 `none` → 提示人工确认是否真无沉淀；
- `check_draft.py --promotion` 的 knowledge 校验从"打印 mtime"改为
  "断言 knowledge.md 至少包含一个非模板条目，或有显式豁免记录"。

### 3.5 调查合同补强制审查项（P9）

改动：`judge-investigation-contract.json` schema 增三个必填断言字段：
"如实拒绝≠办成""三态互斥""不许逃逸"，`validate_investigation.py` 校验存在性；
内容按 fulfilled.md §5/§7 填写。

---

## 阶段四：轴2 落地防重蹈（配合 capability_carrier.md）

`spec/alg/capability_carrier.md` §10 的验收全部落成脚本断言，不写 ROLE 文案：

1. `enabled_scopes: []` 时确定性面与现状一致 → 断言对象是 system prompt 快照、
   工具暴露列表、配置解析结果的 diff，**不是 LLM 输出**（LLM 重跑天然波动，
   拿输出逐字节比较会假阳性）；
2. 开启 `capability_carrier` 前后轴1 逐 case 不变 → 同一批 run 内派生对照，
   判后 pass 结构上不可能改轴1，此断言验证的是"没人把归位写回 JudgeResult"；
3. 归位三态覆盖：每条 NF blocking 期望必有归位结果，说不清必带
   差在哪儿 + 缺料字段 → schema 校验；
4. 归位结论资料引用可回溯 → 断言引用指向 M1 登记 / capability_manifest /
   investigation 报告中的真实条目；
5. 归位列渲染、收件箱报告作为 run artifact 落盘，进 review 收据 sha 链。

轴2 的 review 不引入任何"harness 自填 pass"的判据——它的全部验收都可机算，
这是它与现有 judge loop 最大的纪律差异，必须守住。

---

## 实施顺序与依赖

```text
阶段一（P1、P2）    独立，先做，冻结集重跑验证
阶段二（P3、P8）    独立，止血，半天量级
阶段三（P4-P7、P9） 依赖阶段二完成（避免在可旁路的状态机上加固）
                    3.1 净胜机算 → 3.2 豁免登记 → 3.3 pending 清单
                    （3.2/3.3 依赖 3.1 的机算产物）
                    3.4 / 3.5 独立，可并行
阶段四              依赖 capability_carrier.md 方案确认，可与阶段三并行
```

每阶段完成判据：对应验收断言全绿 + 冻结 30 条重跑无未解释退化。
全部完成后跑一轮完整 draft loop（Investigate 增量 → Solidify → Loop），
验证新门禁下流程可走通且 053 类事故不再发生。

## 风险点与前中后检验清单

### 各阶段风险点

| 阶段 | 风险 | 后果 | 缓解 |
|---|---|---|---|
| 1.1 | prompt 措辞是 LLM 行为敏感面，重排可能引起**非目标案子**判定漂移，不止预期的 NE 恢复 | 冻结集外隐性漂移 | 翻转清单逐案归因；NE 只允许出现在输入坏/完全无关（断言） |
| 1.1 | review 判据未同步：ROLE.md 现按"关着不要 NE"打分 | 修复后的正确 NE 被 review 记为退化，loop 打回 | 先改判据再改 prompt（已写进 1.1 改动项） |
| 1.2 | `apply_last_word` / `pre_judge` 可能承担 schema 修补等隐性职责，误删导致协议类 case 不稳定 | 原本稳定的判定变松或报错 | 实施前枚举全部行为并标注依据，确定去留清单后再动 |
| 1.2 | 硬口改"提示注入"后 LLM 可能不理会提示 | 原稳定 NF 变 F（变松） | 冻结集翻转清单人工过一遍；变松案必须能指到条款 |
| 2.1 | 拦截范围定义过宽（role_assets 声明的无关文件变动也拒跑） | 误报频繁，绕过状态机动机更强 | 校验范围精确到候选模块+声明资产；拒绝时给一键修复指令 |
| 2.2 | 不同 agent 运行时 skill 发现目录不同（`.claude/` vs `.agents/`），删旧目录可能让某些会话加载不到 draft skill 或 fallback 到用户级旧版 | skill 静默降级，比双目录漂移更隐蔽 | 实施前确认所有运行时的发现路径；若某运行时硬性要求 `.claude/`，那是发现机制不是兼容层，改为单向同步产物 |
| 3.1 | 机算把"有把握"的主观置信去掉，模糊赢也计赢 | 净胜高估 | 不计分登记必须发生在机算前；首轮核对机算与人工直觉冲突率 |
| 3.1 | `excluded_reason` 枚举不全，"其他"被滥用 | 变相回到自觉记账 | 首轮跑完统计 reason 分布，"其他"占比超 1/3 即补枚举 |
| 3.2/3.3 | 3 轮上限是拍的：太紧 → 人工延期疲劳；pending 清单本身变新垃圾桶（全登记全延期） | 强制机制名存实亡 | 观察 2-3 轮延期率；延期率过半就调上限或收紧出路要求 |
| 3.3 | run 拒绝启动在无人值守场景卡死自动化 | loop 停摆无人知 | 拒绝时落盘明确的人工介入项；不做静默重试 |
| 3.4 | 每轮强制 `knowledge_delta` 催生凑数条目 | 知识库污染，比空更糟 | 条目必须带 run/review sha 证据引用；review 抽查 |
| 3.5 | schema 增必填字段 → 现存 investigation 包集体 gate fail | 阻塞下一轮 loop | 与一次 investigation 增量同批实施，不单独上 |
| 4 | 承载性裁决的"期望→维度"语义映射是 LLM，有错误率 | 归位列错误误导人工拍板 | 资料引用强制 + 抽查；归位不进计分，错误影响有界 |
| 通用 | 冻结集全是 bad case，对"变松"不敏感 | prompt 改动变松检不出来 | 实施前准备一小撮正常/clean case 对照集（正呼应"bad case 上准确率高不代表正常场景准"） |
| 通用 | 多阶段改动混批，翻转无法归因 | 出问题回滚不了单项 | 分阶段独立提交、独立重跑，禁止跨阶段混批 |

### 实施前排查项

1. **固化基线**：当前工作区未提交变更先入库（含 8/16 手改的 judge.py），
   确认候选 sha 与最近 solidify receipt 的关系，diff 基线不清不动工；
2. **skill 发现路径盘点**：确认各 agent 运行时读 `.claude/` 还是 `.agents/`，
   `rg` 列出全部引用，决定 2.2 是"删"还是"单向同步"；
3. **机算口径先行**：定义翻转比较键（overall status 是否含 NE 成因子标签、
   tie 怎么算），写进 score 脚本注释，先于 3.1 实施；
4. **clean 对照集**：从正常流量选 10-20 条非 bad case 冻结，作为"变松"探测器；
5. **硬口行为清单**：枚举 `pre_judge` / `apply_last_word` / field_sufficiency
   全部路径，逐条标注 fulfilled.md 依据与去留；
6. **判据冲突核对**：ROLE.md / review 判据中与 P1 修复冲突的表述
   （"Authority 关着不要 NE"等）列全，安排在 prompt 改动之前修订。

### 实施中检验项

1. 每次 prompt 改动落两份 system prompt 快照（authority 真/假分支），
   diff 审查通过再跑；
2. 冻结集 + clean 对照集每阶段各跑一次，翻转清单逐案归因到本次改动条款，
   指不到条款的翻转 → 停下调查，不带病进下一阶段；
3. 2.1 拦截上线后先做全流程演练：改候选 → solidify → run 走通，
   再做事故重演：绕过 solidify 手改 → run 前被拦且给出修复指令；
4. 3.x 每上一个门禁，构造一个反例验证它真的拦（伪造净胜、无 waiver 的 fail、
   4 轮未清 pending）；
5. 3.5 与 investigation 增量同批，跑 `validate_investigation.py` 确认老包
   不会集体 fail。

### 实施后观察项（2-3 轮 loop）

1. 冻结集 + clean 集：无未解释翻转；NE 只出现在合法成因；clean 集无变松；
2. 053 类事故重演测试保持通过（手改候选 → run 前拦截）；
3. 统计三个健康度指标：`excluded_reason` 中"其他"占比、pending 延期率、
   `knowledge_delta` 的 none 率与凑数迹象（无证据引用的条目数）；
4. 净胜机算结果与 harness 解释的冲突率：经常冲突 → 复核比较键口径而不是改回自填；
5. 轴2 上线后抽查归位结论的资料引用真实性；prompt/工具面快照 diff 断言进 CI 常态化。

## 不做的事

- 不推翻四阶段结构，不改 Investigate/Solidify 的产物 schema（除 3.5 增字段）；
- 不改 fulfilled.md / material-positioning.md 判定标准本身；
- 不为修流程开启 authority 其余 scope（职责/口径/等价维持关闭）；
- 不给 unseen 集增加运行频次（仍 promotion-only）。
