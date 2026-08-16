# Learning Context

## Accepted Patterns

- Judge contract is registered through the existing `InvestigationManifest.artifact_refs`; no second top-level manifest was introduced.
- Runtime projection excludes `source_claims`, `causal_chain`, `evidence_ref_ids`, and `causal_reasoning`.
- Each `authority:<analysis_id>` has its own Solidify mapping and observable.

## Escalation Backlog

- 姓名形态能否单独撑 F（issue-006 方向 A/B）
- 「去年」算 blocking 核心还是附加维（issue-007）；若用「去掉后仍是某类人」则 I046 也应 non-blocking
- 格式外/称谓空条件落 NE 还是 non-blocking 说明（issue-009）；禁止恢复「拒绝=F」

## Mechanism notes (split/overstrict run)

- 章程 7 字段够用。§2 oracle=协议、§4 升级点挡住了三处不该由角色拍板的政策。
- 一批 4 issue 一个 spawn：22 分钟，spawn-id 对齐，isolation_valid + scope_valid。architect 卡面只有 Read,Grep，但仍写入了 `issues/**`——再次证明 allowedTools 不是沙箱；git 对账因为 issues/** 隐式放行所以 scope_valid=true。
- 4/4 real-problem。不是纯盖章：009 否掉了「可以恢复旧 F」；007 指出 canvas 把 I046 算「新更好」可能反了。

## Confirmed Problem Patterns

- Structural tests cover declared happy paths but omit adversarial schema cases, allowing invalid authority contracts through the official validator.
- Runtime authority enforcement preserves dimension IDs in context but does not use them when mutating assessments.
- Capability aggregation assumes the first intent owns all field metadata, losing later `enum_ref` values for repeated fields.
- Migration evidence sometimes renames an implementation document as a user-authored template, weakening causal provenance.

## Mechanism notes (generalization run, 010–012)

- Codex `spawn-peer` 会把章程里的 `--model sonnet` 当成 Claude 别名丢掉（`model: null`），本轮实际跑的是会话默认 `grok-4.6`。隔离闸仍过：spawn-id `37225eeb6839ec61` 对齐，`isolation_valid` + `scope_valid`，约 9.6 分钟。下次章程 §6 若要指定模型，写 Codex 可用名，不要写 sonnet/opus。
- architect 卡面 `Read,Grep`，本轮显式要了 `Read,Bash` 以便重算 xlsx；allowed_tools 仍只是合同字符串，不是沙箱。git 对账 `issues/**` 隐式放行。
- 3/3 real-problem。不是盖章：010 否掉「341=零头部」；011 把主证从昊轩收到匡西永 vs 王坤林；012 否掉「消灭 LLM / 另起 DSL」，对齐已有 `_operator_justified`。
- peer 第一次用嵌套 heredoc 追加失败（`unmatched \``），改走 `/tmp/arch-01x.md` 再 append，内容完整。以后 task 可提示「先写临时文件再追加」。

## Escalation Backlog（本轮未关）

- 姓名形态能否单独撑 F — **已定 1A**（杨杰与王坤林同侧=F）
- 「去年」算 blocking 核心还是附加维（007；I046 与 I161 必须同侧）
- 格式外/称谓空条件落 NE 还是 non-blocking 说明（009）；禁止恢复「拒绝=F」
- 头部对照集 B — **已定 4A**：现造 `head_set_b.json`（18 条）

## Mechanism notes (unsupported-label run, 013–015)

- spawn-id `81d2ac4a0afb73d1`，exit 0，isolation_valid + scope_valid，elapsed 391s。model 仍是 inherit → grok-4.6。
- 3/3 real-problem。不是盖章：013 收成「可共享问句、不可共享取值/整体格」，并禁止把去年先写成附加维；014 把 review-only 整桶也判成第四态；015 收成「无 normative 地图，但有空间代理 + CoverageGap」。
- peer pid 写 77264，meta.pid=77044（wrapper vs child），spawn-id 对齐即可。
- 本轮 git 对账里出现 `issues/trace/simulate_1a_name_program.*` 与 `issues/charter-unsupported-label.md`，不是本 initiator 写的；未当本轮产物消费。issues/** 隐式放行所以 scope_valid 仍为 true。

## Mechanism notes (1A simulation run, 016–018)

- 用户把范围收回 1A/4A 后，上一份「尚未支持」章程已被归档，但 `issue-013`–`015` 和 spawn `81d2ac4a0afb73d1` 已经按旧题写完。本轮不覆盖那三份，不写它们的 Consensus；新开 `016`–`018`。
- `spawn-peer` 仍会丢掉非 Codex 模型名（`model: null`），本轮不传 `--model`。architect 必须 `Read,Bash` 才能自己重跑 `simulate_1a_name_program.py`。
- 集 B 没有 live。任何 18/18 只能当程序自洽，不能当评测通过。这条写进 018，避免下一轮再把「有文件」当成「测过了」。
- 本轮 spawn `24595086899233c3`：exit 0，isolation_valid + scope_valid，约 5.9 分钟。3/3 real-problem，不是盖章——016 收紧「19 翻面不全是抬 F」；017 把「探针过了」和「可上线」切开；018 强制共识写「未测」。

## Mechanism notes (unsupported-label principle rerun, 013–015)

- 本轮主章程是 `issues/charter-unsupported-label.md`。`issues/charter.md` 仍是已完成的 1A/4A 混合跑，不要覆盖。
- 官方对手是 r2 spawn-id `6286c10358770df9`：exit 0，`isolation_valid=true`，elapsed 447s。`scope_valid=false`，但 `out_of_scope_changes` 全是 `impl/data/context_store/.../judge-*.json`（HB001 / I224 / I539 / I650 等）。architect stderr / 回应 0 次提到 `context_store` / 这些 case。按协议把这类 host 并发写豁免，不重开 spawn。
- 无效上一轮：`issues/spawn/batch-013-015-r1/` spawn-id `e288ae27bc0d2d22` 写了 Architect Response #1（内容可用，R2 承认并收紧），但本轮官方对手是 Response #2，spawn-id 必须对 `6286c10358770df9`。wrapper/child pid 不一致仍只要求 spawn-id 对齐。
- 更早的 `81d2ac4a0afb73d1` 是错题主问题（让用户填功能地图）。那份 `issues/report-unsupported-label.md` 已重写；013–015 的 Consensus 以本轮原则版 + R2 为准，不沿用旧 3/3 real-problem 盖章。
- 015 是 `escalate-to-project`，不是 3/3 盖章。活张力在：verifier 想推正交出口方案 E，architect 锁死路、把挂点和是否改 schema 交回用户。
- 用户「你想让我定啥」来自上一轮把主问题写成功能地图。本轮只问要不要同时看见 Q2，不问去年/称谓/格式外认不认。

## Mechanism notes (1A/4A mixed-pack run, 019–021)

- 主章程改回 `issues/charter.md`（混合包 + 内存四口径）。016–018 已 Consensus，不覆盖。
- 官方对手 spawn-id `f3e708f76cfa44c3`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 584s。wrapper pid 65819 / meta.pid 65842 / 回应写 pid 66079，只要求 spawn-id 对齐。
- 3/3 real-problem。不是盖章：019 收成「judge NF 诚实，红在 parse」；020 把标题 7F/5NF 收成十二人并集、集 B 自己 4F/4NF；021 当场否掉 initiator「昊轩新鲜 F」——冻结 `I485.json` 是 NF，与 xlsx 同侧。
- initiator 任务书写了错误前提（「fresh judge 昊轩 = F」）。architect 按冻结痕迹核对后纠正。以后 task 里的数据主张也是待审，不是已证事实。
- architect 重跑叠加覆盖了 `simulate_1a_mixed_program.json`。旧 SHA `fc2e77f8…` → `14b1ecec…`，分数未变。issue 正文仍可能引旧 SHA，Consensus 以落盘文件为准。
- `yield_time_ms` / `write_stdin.session_id` 在本客户端会被序列化成 float，工具拒绝解析。长等改走本机 sleep/轮询文件，不要用这个参数。
- 上一轮收集器 PID 45482 曾被误判已死、险些双进程抢写 `name_scenario_runs/`。收集器要先看冻结 `live.extracted` 再决定打不打 live。

## Mechanism notes (sibling-question run, 022–024)

- 章程：`issues/charter-sibling-question.md`。不覆盖 `charter.md` / `charter-unsupported-label.md`。
- 官方对手 r1 spawn-id `ad014f66ee11ca7f`：exit 0，isolation_valid + scope_valid，elapsed 408s。pid meta=79381 / 回应写 79816（wrapper vs child），spawn-id 对齐即可。
- 不是盖章：022 否掉「评测员打分」作正式切名；023 把 2×2 降成内部图例，禁止把「该做」公开成新轴；024 是 escalate，否掉把「办得了吗」升格为对外主问。
- 回应格式用了 `**Judgment**` 而不是协议要求的 `**Verdict**`，但五词词表齐全且不歧义。下次 task 写明必须用 Verdict 字段名。不因此重开 spawn。
- git 对账没列出 `issues/open/issue-022`–`024`：文件在 spawn 前已是 untracked，porcelain 前后都是 `??`。写入确在 issues/**，按隐式放行处理。
- 019–021 已被 1A/4A 占用，本轮从 022 起号。不要把两套 issue 混读。

## Mechanism notes (name-generalization run, 025–028)

- 主章程：`issues/charter-name-generalization.md`。不覆盖 `charter.md` / sibling / unsupported。016–024 已 Consensus，不重开。
- 官方对手 r1 spawn-id `8eecb710b62b55a7`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 622s。wrapper pid 95645 / 回应写 95897，只要求 spawn-id 对齐。
- `changed_paths` 没列出 `issues/open/issue-025`–`028`：文件在 spawn 前已是 untracked，porcelain 前后都是 `??`。写入确在 issues/**，按隐式放行。
- 不是盖章：025–027 `real-problem`，028 `escalate-to-project`。025 当场收紧「I248 实际分支是 PERSON_THEN_POLICY，不是四字名」。026 把 41/47 降成包的伪影。027 把共展路径钉成「覆盖已命中、姓氏未命中才 inherit」。
- architect 用了协议要求的 `**Verdict**` 字段名（022–024 用过 Judgment，本轮 task 写明后对齐）。
- 落盘 SHA `f180cb60…bd72e835` 在 architect 21:18 重跑后未变。旧脚本 `simulate_1a_mixed_program.py` 没动。
- stderr 里出现过未落盘的草稿（pid 12345、「脚本跑 025 次」、虚构 `exit_role.py`）。官方 append 是干净的。以后看 issue 文件，不看 stderr 草稿。
- `yield_time_ms` / `write_stdin.session_id` 仍会被序列化成 float。长等继续走本机 sleep + 读 `meta.json`。

## Mechanism notes (unambiguous-sibling run, 029–031)

- 章程：`issues/charter-unambiguous-sibling.md`。不覆盖 `charter.md` / sibling / unsupported / name-generalization。025–028 属于姓名覆盖章程，本轮从 029 起号。
- 官方对手 r1 spawn-id `bebcc12b6cb57a13`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 487s。meta.pid=6519 / 回应写 pid 6990，只要求 spawn-id 对齐。
- `changed_paths` 没列出 `issues/open/issue-029`–`031`：文件在 spawn 前已是 untracked，porcelain 前后都是 `??`。写入确在 issues/**，按隐式放行。
- 不是盖章：029 / 030 `real-problem`，031 `escalate-to-project`。030 当场否掉「四字已经无歧义」，并改掉 verifier「办成了 ⇒ 不得叫」——§8.3 允许能力缺失 + 实际达成 → F。
- architect 用了协议要求的 `**Verdict**` 字段名。
- 「无歧义」= 换语境不翻面 + 失败对象不同格 + 不能靠第一问答完。不是「再找一句第一眼不会读错的口语」。escalate 不得误读成抽象没做完、再开一轮找更顺的句子。
- 用户可见回复不得代拟对外终句，也不得宣布采用「办不了吗 / 办得了吗 / 该有但还没有 / 定位内尚未具备」。

## Mechanism notes (zero-ambiguity-boundary run, 032–034)

- 章程：`issues/charter-zero-ambiguity-boundary.md`。不覆盖 `charter.md` / sibling / unambiguous / unsupported / name-generalization。029–031 属于上一轮无歧义章程，本轮从 032 起号。
- 官方对手 r1 spawn-id `553f3282e3ce51ad`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 517s。meta.pid=25776 / 回应写 pid 25994，只要求 spawn-id 对齐。
- `changed_paths` 没列出 `issues/open/issue-032`–`034`：文件在 spawn 前已是 untracked，porcelain 前后都是 `??`。写入确在 issues/**，按隐式放行。
- 不是盖章：032 / 033 `real-problem`，034 `escalate-to-project`。032 当场把「格子对、定义句错」切开，没有整包推翻 030。033 只降 023.5，不整包推翻 023；并把 catalog / `is_supported` / `current_behavior` 写进「不看」，不只写在「不是什么」。034 作废 031「请自己写一句」。
- architect 用了协议要求的 `**Verdict**` 字段名。
- 本轮「无歧义」= 定义谓语不能两读 + 答第二问不得看交付 + 失败对象不同格 + 015/023/030 只留一套。不是「再找一句第一眼不会读错的口语」。escalate 不得再读成抽象没做完、再开一轮找更顺的句子。
- 用户可见回复不得代拟对外终句，也不得宣布采用「现成有 / 现成没有 / 办不了吗 / 定位内尚未具备」。
- `write_stdin.session_id` / `yield_time_ms` 仍会被序列化成 float。本轮长等走 node_repl sleep + 读 `meta.json`。

## Mechanism notes (name-principle run, 035–038)

- 章程：`issues/charter-name-principle.md`。不覆盖 `charter.md` / name-generalization / sibling / unambiguous / unsupported / zero-ambiguity。025–034 已有 Consensus，不重开。本轮从 035 起号。
- 官方对手 r1 spawn-id `770d8502492aedbc`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 609s。meta.pid=39851 / 回应写 pid 44788，只要求 spawn-id 对齐。
- `changed_paths` 没列出 `issues/open/issue-035`–`038`：文件在 spawn 前已是 untracked，porcelain 前后都是 `??`。写入确在 issues/**，按隐式放行。
- 同窗口 host porcelain 还看到 `charter-no-rule-total.md` / `issue-039`–`041` / `batch-039-041-r1/**`。那是另一份章程（第二问类型表），不是 architect 写产品代码。本轮收口不碰 039–041。
- 不是盖章：035 / 036 / 037 `real-problem`，038 `escalate-to-project`。035 当场收紧「341 几乎没改判」= 翻面只有王坤林，overlay 仍有 57 行。036 锁三处规格：跨度顺序、Unicode 空白、`other` 入表；原则文已写回，脚本未改。037 要求报告带多字段扫描，不能只报空差表。
- architect 用了协议要求的 `**Verdict**` 字段名。独立重跑 SHA `0205668a62c18e516a12d973e3273988235a02b6caafaf9a9807341548d95367` 未变；收口再跑一次仍未变。旧脚本 `simulate_1a_coverage_program.py` 只被 import。
- 分数撞车必须这么读：赢的是标准和边界，不是新分数。禁止把混合包 41/47 或 inherit-NF 当胜利。合成探针两格不准进 47 分母。
- 用户可见回复先讲原则和例子（杨杰 / 王坤林 / 红莲保单 / 李明的重疾险 / 共展），禁止甩「41/47」「整句身份」当结论。不得再把 `live_identity` 卖成可泛化架构。
- `write_stdin.session_id` / `yield_time_ms` 仍会被序列化成 float。本轮 spawn 在接手时已结束，未再长等。

## Mechanism notes (no-rule-total run, 039–041)

- 章程：`issues/charter-no-rule-total.md`。不覆盖 `charter.md` / sibling / unambiguous / zero-ambiguity / name-principle。035–038 属于姓名原则章程，本轮从 039 起号。
- 官方对手 r1 spawn-id `d149b6afbcb7ad4b`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 546s。meta.pid=45094 / 回应写 pid 49103，只要求 spawn-id 对齐。
- `changed_paths` 没列出 `issues/open/issue-039`–`041`：文件在 spawn 前已是 untracked，porcelain 前后都是 `??`。写入确在 issues/**，按隐式放行。
- `changed_paths` 里出现过 `issues/report-name-principle.md` 和 `issues/spawn/batch-035-038-r1/last-message.txt`。二者仍在 `issues/**`，未判 scope 失败。以后 spawn 前先确认工作区没有别的 issues 文件在写。
- 不是盖章：039 / 040 `real-problem`，041 `escalate-to-project`。039 当场收窄「033 整包都是类型门」→ 只退休「认哪一类 / 那一档」操作化，并否掉 039 对覆盖的过读。040 当场改掉「第一问塌成结果」和「计算位置写弱」。
- architect 用了协议要求的 `**Verdict**` 字段名。
- 本轮「不要有规则化」= 不许先分预置类型再查表；「覆盖」= 全函数，不是把针表写长。escalate 不得再读成抽象没做完，也不得请用户列全情况。
- 用户可见回复不得代拟对外终句，也不得宣布采用「立住了 / 没立住 / 现成有 / 现成没有」。
- `write_stdin.session_id` / `yield_time_ms` 仍会被序列化成 float。本轮长等走 node_repl sleep + 读 `meta.json`。
## Mechanism notes (sufficiency run, 042–045)

- 章程：`issues/charter-sufficiency.md`。不覆盖 `charter.md` / name-principle / no-rule-total。025–041 已有 Consensus，不重开其对错结论。本轮从 042 起号。只审覆盖门是不是用户说的「看似没规则化、本质是规则化」。
- 官方对手 r1 spawn-id `15b6719c8967bbf9`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 723s。meta.pid=76429 / 回应写 pid 81087，只要求 spawn-id 对齐。
- `changed_paths` 没列出 `issues/open/issue-042`–`045`：文件在 spawn 前已是 untracked，porcelain 前后都是 `??`。写入确在 issues/**，按隐式放行。本轮 spawn 期间未写其它 issues 文件。
- 不是盖章：042 / 043 / 044 `real-problem`，045 `escalate-to-project`。043 当场按可证伪第 1 条拿掉 I595 / I638（问句就是那个客户号，不是「交了姓名还要别的」），七条误抬仍在，未整包翻案。044 把「充分性 ≡ live_identity」和「充分性 ≈ 覆盖门」拆开读：前者是 026 地板，后者是冻结痕迹假撞车，`SYN-concat` 已分开。
- architect 用了协议要求的 `**Verdict**` 字段名。独立重跑 SHA `aaa5381cefef843ad52b706dc1a7813db5308c8b707f3ae07b3cefd859f5c980` 未变。旧脚本 `simulate_1a_coverage_program.py` / `simulate_1a_principle_program.py` 只被 import。
- 035 极性在 042 Consensus 被覆写：值=整句 + 字段标准 = 本轮充分性测试，不再是覆盖门的特例。不重开 035「整句覆盖门不是原则」和「翻面只有王坤林」。
- 分数撞车必须这么读：赢的是标准和边界，不是新分数。禁止把混合包同分或 inherit-NF 当胜利。合成探针不准进标签分母。
- 用户可见回复先讲两问和例子（杨杰 / 王坤林 / 红莲保单 / 唐诗颖生存金 / 李明的重疾险），禁止甩分数、「整句身份」、覆盖门当架构。不得代拟对外中文，不得并进 judge。
- `write_stdin.session_id` / `yield_time_ms` 仍会被序列化成 float。本轮长等走 node_repl sleep + 读 `meta.json`。上一棒 spawn 因权限超时没跑起来，本轮重 spawn 成功。

## Mechanism notes (nf-only-sibling run, 046–048)

- 章程：`issues/charter-nf-only-sibling.md`。不覆盖 `charter.md` / sufficiency / sibling / unambiguous。006–045 已有 Consensus，不重开其对错结论。本轮从 046 起号。只审「是不是只有 NF 才有 / Judge 会不会改口 / 因此要不要枚举」。
- 官方对手 r1 spawn-id `7fed62d9178ba6d4`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 470s。meta.pid=13326 / 回应写 pid 14816，只要求 spawn-id 对齐。
- `changed_paths` 没列出 `issues/open/issue-046`–`048`：文件在 spawn 前已是 untracked，porcelain 前后都是 `??`。写入确在 issues/**，按隐式放行。本轮 spawn 期间未写其它 issues 文件。
- 不是盖章：三份都是 `real-problem`，但 046 当场拿掉 I161 合法证人、收窄 §8.3「实际达成」= 同一条期望；047 把「我们=Judge」收成立场缝不是所有权证明；048 连 NF 原因码救援一并否掉，且禁止把「另开一列」写成批准。
- architect 用了协议要求的 `**Verdict**` 字段名。
- 用户可见回复先讲三句原则（不是只有失败才有 / 不算改口 / 不要新枚举），禁止甩格子名、字段名、I161 当胜利。不得代拟对外中文，不得改前端。
- `write_stdin.session_id` / `yield_time_ms` 仍会被序列化成 float。本轮长等走 node_repl sleep + 读 `meta.json`。

## 2026-08-16 retro — 053–057 内存判定代理

- 官方对手 r1 spawn-id `047ae1a3a401be9c`：exit 0，`isolation_valid=true`，elapsed 617s。`scope_valid=false`，`out_of_scope_changes` 全是 `impl/data/context_store/**/judge-*.json`（08-14 旧条 + `mem:I248` / `HB009` / `I607`）。architect 回应 0 次要改这些文件。按既有协议豁免 host / 跑判定旁路落盘，不重开 spawn。
- wrapper pid 41557 / 回应写 41745，只要求 spawn-id 对齐。第一眼 `exit_code=null` 是 wrapper 尚未收口；约 10 分钟后 meta 写完。不要在 `ended_at` 出现前把还在收口的 spawn 标成 isolation-failed。
- 不是盖章：053 / 054 / 057 `real-problem`，055 / 056 `reasonable-design`。053 当场把 `source=llm` 降成负检查；054 否掉“共展是单点”；055 锁住 Q2 定义；056 禁止把 27/27 当泛化；057 收下只读尺、否掉最后一语换皮，并要求独立冻住 T2。
- 机制摩擦：architect 按任务书跑 `--probe`（无 `--llm`）会改写 live dump。T2 一度被空表覆盖。内存脚本已改成按 id 合并；T2 冻在 `simulate_judge_agent_memory.t2-12.json`。下次任务书必须写 `--probe --q1-evidence`，并点名冻结文件。
- `write_stdin.session_id` / `yield_time_ms` 仍会被序列化成 float，本轮长等继续走 node_repl sleep。

## 2026-08-16 retro — 058–061 第二问实现位置

- 章程：`issues/charter-q2-placement.md`。不覆盖 `charter.md` / nf-only-sibling / 053–057。006–057 已有 Consensus，不重开其对错结论。本轮从 058 起号。只审四层落点，不改题面，不改代码。
- 官方对手 r1 spawn-id `f7ab9fd0b34ddbc9`：exit 0，`isolation_valid=true`，elapsed 396s。`scope_valid=false`，`out_of_scope_changes` 全是 `impl/data/context_store/**/judge-*.json`（08-14 旧条 + 08-16 旁路落盘）。architect 回应 0 次要改这些文件。按 053–057 惯例豁免 host / 跑判定旁路落盘，不重开 spawn。
- wrapper pid 59609 / 回应写 59819，只要求 spawn-id 对齐。
- 不是盖章：058 / 060 `real-problem`，059 `reasonable-design`，061 `escalate-to-project`。058 当场删掉「再读已经用来裁过同类问题的资料」——那是被禁的结论目录，不是 040 的依据资料。059 锁住粒，不把主表看不见兑换成切粗。060 把矩阵写成规范格子而不是当前视线，并把投影收成最终存放形态。061 停在 §4，不布置「请先起名 / 请先改表」。
- 机制摩擦：与 053–057 相同，host 并发写 context_store 会把 write-scoped peer 打成 `scope_valid=false`。本轮 architect 只读、writable_globs 为空，仍被记进 out_of_scope。豁免条件保持：路径只在 context_store judge dump，且 peer 没有要求改它们。
- 用户可见回复先讲四层落点（协议 / 计算 / 存放 / 看见），禁止甩字段名当胜利。不得代拟对外中文，不得改前端，不得把「立住了」宣布成题面。
- `write_stdin.session_id` / `yield_time_ms` 仍会被序列化成 float。本轮长等继续走 node_repl sleep。
## 2026-08-16 retro — 062–065 第二问四个结果口

- 章程：`issues/charter-q2-slot.md`。不覆盖 `charter.md` / q2-placement / 006–061。本轮从 062 起号。只审四个点名结果口，不改题面，不改代码。
- 官方对手 r1 spawn-id `c902435f16f979ab`：exit 0，`isolation_valid=true`，elapsed 327s。`scope_valid=false`，`out_of_scope_changes` 88 条全是 `impl/data/context_store/**/judge-*.json`。architect 回应 0 次要改这些文件。按 058–061 惯例豁免 host / 跑判定旁路落盘，不重开 spawn。
- wrapper pid 78885 / 回应写 79074，只要求 spawn-id 对齐。
- 不是盖章：四份都是 `real-problem`，但切开不同。062 当场纠正 gate 会把误写 NE 的能力缺失抬回 NF，并不删 F 正格；063 把「职责外→NE」收成第一问消费，不是第二问住在 NE；064 把同一芯片上的显示别名也收进 C；065 拒绝把 060 改名为 B，也拒绝改成 escalate。
- 用户可见回复先讲四个口都不能当宿主，禁止甩字段名当胜利。不得代拟对外中文，不得改前端，不得把「立住了」宣布成题面。
- `write_stdin.session_id` / `yield_time_ms` 仍会被序列化成 float。本轮长等继续走 node_repl sleep。


## 2026-08-16 retro — 066-q2 / 067–069 开格子是不是新标签

- 章程：`issues/charter-q2-label-honesty.md`。不覆盖 `charter.md` / q2-placement / q2-slot / 006–065。065「B 口不能叫标签」本轮可以打。只审看见层诚实和四个口再安放，不改题面，不改代码。
- 官方对手 r1 spawn-id `eda05b5bb67ac683`：exit 0，`isolation_valid=true`。`scope_valid=false`，路径全是 `impl/data/context_store/**/judge-*.json`。architect 回应 0 次要改这些文件。按 058–065 惯例豁免 host / 跑判定旁路落盘，不重开 spawn。回应写 pid 96523，只要求 spawn-id 对齐。
- 机制摩擦 1：号段撞车。并行章程 `charter-judge-agent-t4.md` 占用 `issue-066.md`，后改号 074–076。本轮看见层备份在 `issue-066-q2-label-honesty.md`，067–069 仍是本条线正文。070–073 是事后副本，未作为官方 Consensus。未再 spawn `batch-070-073-r1`。
- 机制摩擦 2：同目录后写入。`issues/spawn/batch-066-069-r1/meta.json` 被并行章程 spawn `8480dadf54af6541` 覆盖；该 spawn 还在 067–069 / 066 正号追加了第二份 Architect Response，并拒绝审本轮题面。官方只采 `eda05b5bb67ac683` 的第一份。以后并行章程必须自备 out-dir，禁止复用对方 batch 目录。
- 不是盖章：066-q2 / 067 / 069 `real-problem`，068 `not-actionable`。066 只改看见层叫法，不掀「判定再写不能当宿主」。067 挡住「用户只能看见一枚芯片所以必须住进去」。068 拒绝为旧闸再开号。069 拒绝把安放听成「选了 B」，也拒绝再 escalate 打开。
- 用户可见回复先讲：开格子就是多一个标签；四个口都不能整句当宿主；B 要拆开；打开仍停住。禁止甩字段名当胜利。不得代拟对外中文，不得改前端，不得把内部手柄宣布成题面。
- `write_stdin.session_id` / `yield_time_ms` 仍会被序列化成 float。本轮接手时官方 spawn 已结束，未再长等。

## Mechanism notes (q2-scheme run, 077–080)

- 章程：`issues/charter-q2-scheme.md`。不覆盖 `charter.md` / q2-placement / q2-slot / q2-label-honesty。006–076 已有 Consensus，不重开其对错结论。本轮从 077 起号。
- 官方对手 r1 spawn-id `344d097baef18f39`：exit 0，`isolation_valid=true`，elapsed 425s（11:04:45–11:11:50）。meta.pid=23323 / 回应写 pid 23530，只要求 spawn-id 对齐。
- `scope_valid=false`：32 条全是 host 写的 `impl/data/context_store/**/judge-*.json`。architect 0 次要改这些文件。按 053–069 惯例豁免。
- 不是盖章：四号都是 `real-problem`，但攻击面不同。077 区分看见层/字段层，并说明相对 066-q2 的增量是「写成方案」不是重锁诚实。078 拒把「是标签」兑换成现有芯片。079 把新名字绑回 060 的格子，不另找格。080 拒整号 escalate，要求先写肯定句。
- 本轮失败条件已避开：没有再交「四个口都不能宿主，因此没有方案」。方案句先写，陪绑后写。
- 用户可见回复必须先答「是，看见层就是新标签」，再给方案句。禁止再把「标签」只留给「判定再写」然后说没有方案。
- 不得代拟对外终句，不得宣布采用「立住了 / 没立住」，不得布置改表。
- `write_stdin.session_id` / `yield_time_ms` 仍会被序列化成 float，本轮用 node_repl sleep 等待。

## Mechanism notes (q2-is-label run, 085–088)

- 章程：`issues/charter-q2-is-label.md`。不覆盖 `charter.md` / q2-scheme / q2-placement / q2-slot / q2-label-honesty。006–080 已有 Consensus，不重开其对错。081 是 T4 的 4A KPI，本轮从 085 起号。082–084 是撞号后的迁出桩，不以它们当正文。
- 官方对手 r1 spawn-id `5d262889dc7c1b05`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 448s（11:45:52–11:53:20）。meta.pid=50840 / 回应写 pid 51034，只要求 spawn-id 对齐。
- `changed_paths` 未越权。本轮 spawn 期间未改 spec / impl / 前端。
- 不是盖章：四号都是 `real-problem`，但攻击面不同。085 把 080「写层叫别的方式」判成分类错误，不是 066 复述。086 当场改掉 verifier 把「办成了 × 没立住」挂在 fulfilled.md 上过重：根因换成 040 + product-function + authority §8.3。087 拆开「评估卡上看得到」和「第一眼是芯片」。088 拒整号 escalate，要求先写肯定句。
- 本轮失败条件已避开：没有再把方案名写成「别的方式」，也没有把「是标签」焊回「所以 Judge 再填」。
- 用户可见回复必须先答「是，方案名就是新增一个 judge 结果标签」，再写挂在哪、不是哪三个口。禁止再交「四个口都不能，因此别的方式」。
- 不得代拟对外终句，不得宣布采用「立住了 / 没立住」，不得布置改表。
- 接手时官方 spawn 已结束，未再长等。

## Mechanism notes (judge-agent T4e, 076/081)

- r1 `batch-081-r1` isolation-failed，见该目录 `ABORTED.md`。不当官方 peer，不在本上下文补辩。
- r2 spawn-id `a4052bc3d0f3de56`：exit 0，isolation_valid true，scope_valid true，elapsed 425s。076 #2 / 原则 = reasonable-design，081 #1 = real-problem。不是盖章：081 把过严收在正式嘴重建裸词门槛，否掉用 17/1 发版和给王芳加例外。
- 用户已锁 I007 keep-F。红莲保单 / 张伟保单不得因 I007 代选。昊轩 / 去年 / 称谓 / 格式外 / 对外中文继续停住。
- 本轮只写 Consensus，不改正式文件，不重跑 34 行，不重采 live。

## Mechanism notes (recognized-exit run, 089–092)

- 章程：`issues/charter-recognized-exit.md`。不覆盖 `charter.md` 及既有 q2-* / T4。006–088 已有 Consensus，不重开其对错；本轮只打「叫做第二问再推安放」。
- r1 `batch-089-092-r1` 先写下 `ISOLATION-FAILED.md`（进程中途像死了、当时无 last-message）。后来该进程又跑完，meta 变成 exit 0 / isolation_valid true。官方对手不取它，取重开后的 r2。
- 官方对手 r2 spawn-id `8481552ab6d86f98`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 476s（12:36:44–12:44:40）。wrapper pid 85171 / 回应写 85394，只要求 spawn-id 对齐。
- `changed_paths` 未越权。本轮 spawn 期间未改 spec / impl / 前端。
- 不是盖章：四号都是 `real-problem`，但攻击面不同。089 换主语，090 用单位打死三个口，091 把「标签」从名字降回安放，092 必须先写方案句。orchestrator 自己对了 fulfilled.md §1、product-function.md §1/§7–8、authority.md §8.3、现行出口和 040/047/058/060/061 内容后才写 Consensus。
- 本轮失败条件已避开：没有再以「第二问」起头给方案，也没有交「四个口都不能因此没有方案」，也没有把「结果标签」焊回「Judge 再填」。
- 用户本轮问的是「凭什么这样放」。用户可见回复必须先写依据（单位 / 对象 / 三口会弄丢什么），再写方案句。禁止只交方案名。
- 不得代拟对外终句，不得宣布采用「立住了 / 没立住」，不得布置改表。
- 接手时官方 spawn 已结束，未再长等。


## Mechanism notes (nf-reason-absolute run, 093–095)

- 章程：`issues/charter-nf-reason-absolute.md`。不覆盖 `charter.md` 及 recognized-exit / q2-* / T4。006–092 已有 Consensus，不重开其对错；本轮只打「像 NF 原因说明项」是否绝对排除得住。
- 官方对手 r1 spawn-id `7c30ec2320df0b23`：exit 0，`isolation_valid=true`，`scope_valid=true`，elapsed 499s（13:02:11–13:10:30）。wrapper pid 2305 / 回应写 2590，只要求 spawn-id 对齐。
- `changed_paths` 未列 issue 文件（同 089–092），但 issue 体积在 13:10:07 增长且含 spawn-id。`out_of_scope_changes` 空。未改 spec / impl / 前端。
- 不是盖章：三号都是 `real-problem`，但 architect 改掉了 verifier 两条「绝对理由」。093 不接受「不区分技术原因」「前缀顺序」单独足够；补上对象切粗，并堵死「三态后缀进 display_reason」。094 按绝对标准放过「人看见时多一格字」。095 逼方案句明写「不是焊进 NE / 现在不进 display_reason / 这一格还不存在」。
- 本轮失败条件已避开：没有靠「第二问」排除，没有把时机冒充身份，没有交「四个口都不能因此没有方案」，没有把「结果标签」焊回「Judge 再填」。
- 用户可见回复必须先答「不是原因说明项 + 绝对改掉了哪几锁」，再写方案句。禁止只交方案名。
- 不得代拟对外终句，不得宣布采用「立住了 / 没立住」，不得布置改表。
