# Judge Knowledge Baseline

一等产物，与 draft 同等。promotion 时一起成为新 baseline，下一轮 AI 站在这一层之上探索。

## 链路地图

记录业务输入 → 业务输出 → 判定的关键环节、分支和已知 gap。每个项目按 `impl/projects/<project>/` 实际结构补充。

- 业务输入边界：judge 能看到什么、不能看到什么。
- 判定分支：哪些条件触发 fulfilled / not_fulfilled / not_evaluable。
- 已知 gap：哪些业务场景下当前判定会失真。

## Gap 模式

沉淀"这类 gap 怎么识别和判定"，不是"这条 case 怎么修"。

- 模式名：简要描述。
- 触发条件：哪类 trace/业务输入会出现这个 gap。
- 判定路径：从哪些业务字段推断 gap。
- 关联标准：项目已有 semantic comparator/runtime check 怎么使用。

<!-- verified-entry -->
- 模式名：关闭 Authority 时非法 NE 应收成 NF。
- 触发条件：核心条件未交付，但 Judge 写成 not_evaluable。
- 判定路径：overall_fulfillment.status；合法 NE 仅输入坏/完全无关。
- 关联标准：fulfilled.md 反面 9。机算不再按 F>NE>NF 记输；这类修正要标 flip_label=win。
- 证据: draft/.state/judge/iterations/001-run.json#source-badcase-073

<!-- verified-entry -->
- 模式名：无 inlive 映射的产品别名静默改写不得 F。
- 触发条件：用户产品名（合家福）被 live/Draft 换成目录内近邻名（合家欢）。
- 判定路径：SearchHit 不是 Evidence；catalog 无等价映射则 NF。
- 关联标准：fulfilled.md 反面 1、§4.1。
- 证据: draft/.state/judge/iterations/001-run.json#source-badcase-128

<!-- verified-entry -->
- 模式名：空条件加提示不能当 F。
- 触发条件：盘客/车牌等明确不支持，live 只给提示。
- 判定路径：无可执行条件 → NF；透明说明只能 non-blocking。
- 关联标准：fulfilled.md 反面 1。
- 证据: draft/.state/judge/iterations/001-run.json#source-badcase-088

<!-- verified-entry -->
- 模式名：单轮翻转不能归因到候选。
- 触发条件：同一 draft fingerprint 两次 run 的 overall status 不一致，或 Current 侧零改动也翻。
- 判定路径：只有各 replicate 复现的同一组 status pair 才能进 win/loss；其余进 variance。
- 关联标准：Draft Loop 稳定性口径。
- 证据: draft/.state/judge/iterations/001-run-r2.json

<!-- verified-entry -->
- 模式名：Current 指纹漂移后的 F/NF/NE 晃动不得当新基线。
- 触发条件：frozen Current sha 相对 059 已变，同一 case 两侧 replicate 的 Current status 不一致。
- 判定路径：pair 不一致进 variance；不得用本轮 Current 重写 059 轴1 真相。
- 关联标准：Draft Loop 稳定性口径。
- 证据: draft/.state/judge/iterations/001-score.json

<!-- verified-entry -->
- 模式名：LLM 失败 NE 不是业务说不清。
- 触发条件：reasoning_summary 含「LLM 调用失败」。
- 判定路径：exclusions.reason=tool_interrupt；禁止标 win/loss。
- 关联标准：LLM 失败只许 NE，且不计分。
- 证据: draft/.state/judge/iterations/001-run.json#source-badcase-123

## Probe 库

被验证过有效的 judge probe 及适用场景（外部业务视角，不读取内部代码）。

- probe 名：来源文件路径。
- 输入：从 trace 取哪些业务字段。
- 输出：能稳定显示什么 gap。
- 边界：在哪类 case 上无效。

## 被否决的假设

试过什么、为什么不 work。

- 假设：改 X 能解决。
- 实验：怎么验证的。
- 结果：为什么不 work 或在什么边界失效。

## 泛化边界

这个优化在什么范围有效，超出什么边界可能失效。

- 适用范围：哪类 case 验证过。
- 不适用范围：哪类 case 没验证或已知可能失效。
- 风险条件：触发 not_evaluable 误判或强判 fulfilled 的条件。

## 维护

- 每轮 review 后更新本文件（`knowledge_delta`）；连续 3 轮 `none` 须人工确认。
- 只记录被验证过的事实，条目必须带 run/review sha 证据引用。
- 删除被新探索推翻的旧条目。
