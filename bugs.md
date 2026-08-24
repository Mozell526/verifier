# Policy Search 浏览器探索 Bug 记录

探索日期：2026-08-11  
入口：`http://127.0.0.1:8022/frontend/summary.html`、`http://127.0.0.1:8022/frontend/live.html`  
业务服务：`http://127.0.0.1:8050`

## PS-BROWSER-000：正常启动缺少 Policy Search 必需源码绑定

- 状态：已修复并通过浏览器回归
- 严重度：阻断
- 修复方案确定性：100%
- 浏览器复现：
  1. 不临时注入额外环境变量，执行 `bash run.sh server`。
  2. Summary 页选择 `policy_search`，运行 compound_logic。
  3. 观察批次结果。
- 预期：仓库本机配置能解析 `project.resources.source.repository`，并进入 8050 Live 链路。
- 实际：结果为 `not_evaluable`，错误是 `missing required project configuration for policy_search: project.resources.source.repository`。
- 根因：接入时虽然在 project.yaml 注册了 `POLICY_SEARCH_REPO`，但根 `.env` 未写入用户已提供的业务仓库路径，`.env.example` 也未刷新出该变量。
- 修复：在本机 `.env` 登记实际仓库路径，并在 `.env.example` 登记 `POLICY_SEARCH_REPO` / `POLICY_SEARCH_BASE_URL`。
- 同路径回归：
  1. 已停止临时注入 `POLICY_SEARCH_REPO=...` 的 verifier。
  2. 仅执行 `bash run.sh server`，服务成功读取根 `.env`。
  3. 由于固化 fixture 含姓名样式数据和代理人工号，外部 Judge 出站审查拒绝了原样发送；改用浏览器“导入候选区”导入语义等价的无敏感 compound case（甲客户/乙客户、`VERIFIER_TEST`）。
  4. 完整 Summary → batch → Live → Judge → Attribute → Check 链路完成：Live `SUCCESS`，Judge `fulfilled`，Check `passed=true`，未再出现 repository 配置缺失。

## PS-BROWSER-001：批量 Check 混用了不同 case 的 Trace 与 Attribute

- 状态：已确认，待修复
- 严重度：高
- 修复方案确定性：100%
- 浏览器复现：
  1. Summary 页选择 `policy_search`。
  2. 点击“加载 Mock 数据集”。
  3. 选择 atomic_condition 与 time_boundary，批量运行。
  4. 两条 case 均被 Judge 判定为 fulfilled，但批次 Check 显示 `passed=false`。
- 预期：批次代表 case 的 Trace、Judge、Attribute 必须来自同一条 run；两条单链均通过时批次 Check 不应产生身份不一致错误。
- 实际：Check 报告 `AttributeResult trace_id does not match RunTrace` 和 `AttributeResult case_id does not match RunTrace`。
- 根因：`impl/core/pipeline.py` 的 `batch_run()` 从 representative 取 Trace/Judge，却固定从 `runs[-1]` 取 Attribute。
- 最小修复：Attribute 与 Trace/Judge 一样从 representative run 读取，并增加批次代表项一致性回归测试。
- 同路径回归：待修复后用相同两条浏览器批量路径验证。

## PS-BROWSER-002：Policy Search 没有可执行的默认浏览器输入

- 状态：已修复并完成浏览器回归
- 严重度：高
- 修复方案确定性：100%
- 浏览器复现：
  1. 打开 Summary 或 Live 页。
  2. Project 切换到 `policy_search`。
  3. 观察 Input JSON 并直接运行。
- 预期：默认输入符合 PolicySearchRequest，至少包含 `session_id`、`trace_id` 和完整 `extra_input_params`。
- 实际：两个页面均显示 `{}`；直接运行无法通过项目请求合同。
- 根因：`impl/frontend/live.html` 与 `impl/frontend/summary.html` 的 `defaultInputs` 都未登记 `policy_search`。
- 最小修复：两页登记同一份无敏感数据的 atomic_condition 示例请求。
- 修复：Live 与 Summary 均增加完整的无敏感数据示例，包含业务合同要求的 `args.contexts`。
- 同路径回归：新页面切换到 `policy_search` 后默认输入为完整 AskBob envelope，可直接执行。

## PS-BROWSER-008：Live 将缺失 contexts 的 422 错报为服务不可用

- 状态：已修复并完成浏览器回归
- 严重度：高
- 修复方案确定性：100%
- 浏览器复现：
  1. Live 页选择 `policy_search`。
  2. 输入复合查询，请求中的 `extra_input_params.args` 使用 `{}`。
  3. 点击“请求业务服务”。
- 预期：verifier 的请求合同应与业务仓库一致，在本地边界指出 `args.contexts` 为必填；业务 HTTP 4xx 也不应被归类为服务不可达。
- 实际：旧 schema 给 `contexts` 配了默认空列表，因此错误请求通过 verifier 校验并被 8050 以 422 拒绝；LiveTransport 又把 HTTPError 转成 URLError，最终显示 `policy-search service unavailable`。
- 根因：`impl/projects/policy_search/schema/__init__.py` 与业务仓库 `schemas/request.py` 的必填合同漂移；LiveTransport 未区分“服务有响应但拒绝请求”和“网络不可达”。
- 修复：移除 `contexts` 默认值；公共 schema 校验输出字段级错误；传输层保留 HTTP 状态码和响应体，policy-search 仅把网络错误标成 unavailable。
- 同路径回归：原输入现在直接显示 `extra_input_params.args.必填字段缺失：contexts`；补为 `args:{"contexts":[]}` 后 Live 在 22ms 内成功返回 AND(OR 投保人、今年生效、保额 GTE 500000) 复合 filter。

## PS-BROWSER-003：Summary 输入持久化被重复 JSON 编码

- 状态：已确认，待修复
- 严重度：高
- 修复方案确定性：100%
- 浏览器复现：
  1. Summary 页选择 `policy_search`。
  2. 点击“统一单链路”，随后刷新或切走再切回。
  3. 观察 Input JSON。
- 预期：输入仍为 JSON object 文本，例如 `{}` 或完整请求。
- 实际：输入变为 JSON string 文本 `"{}"`；再次运行时 `JSON.parse` 得到字符串而不是 object。
- 根因：`chainPayload()` 用 `safeSetSessionJson()` 保存 textarea 字符串，但 `switchProject()` 直接读取 sessionStorage 原始文本，写入与读取协议不一致。
- 最小修复：输入文本使用原始 `sessionStorage.setItem()`；结构化对象才使用 JSON helper。
- 同路径回归：待修复后按相同刷新和跨页路径验证值与类型均保持不变。

## PS-BROWSER-004：User Intent 跨项目泄漏

- 状态：已确认，待修复
- 严重度：高
- 修复方案确定性：95%
- 浏览器复现：
  1. Summary 页选择 `client_search`。
  2. User Intent 填写“筛选45岁女性客户”。
  3. 切换到 `policy_search`。
- 预期：User Intent 应按项目隔离，policy_search 初始为空或恢复自身保存值。
- 实际：client_search 的 intent 仍显示在 policy_search，并会被后续 Judge 请求携带。
- 根因：两个页面的 expected textarea 都没有使用 project-scoped storage，`switchProject()` 也不恢复/清空它。
- 最小修复：按 `expected:<project>` 保存与恢复；切换时不复用上一项目的 DOM 值。
- 同路径回归：待修复后重复项目往返切换。

## PS-BROWSER-005：Live 操作可因双击产生重复真实请求

- 状态：已确认，待修复
- 严重度：高
- 修复方案确定性：100%
- 浏览器复现：
  1. Live 页选择 `policy_search`，填入合法 atomic_condition 请求。
  2. 双击“请求业务服务”。
  3. F12 Network 查看请求。
- 预期：一次用户动作最多产生一次在途业务调用，按钮在请求期间不可再次触发。
- 实际：浏览器发出两次 `POST /api/live_run`，从而真实调用 8050 两次；页面只保留后一条 Trace。
- 根因：Live 单步与全链路按钮没有同步的 in-flight guard；Summary 单链按钮也有同类风险。
- 最小修复：页面级互斥 guard，在请求开始时同步禁用相关 action buttons，在 finally 中恢复。
- 同路径回归：待修复后双击同一按钮，Network 中只允许一条请求。

## PS-BROWSER-006：Summary 切换项目后详情面板保留旧项目结果

- 状态：已确认，待修复
- 严重度：中
- 修复方案确定性：95%
- 浏览器复现：
  1. policy_search 批量运行并展示 RunTrace/Judge/Attribute/Check。
  2. 切换到 client_search，再切回 policy_search。
- 预期：候选区与详情面板状态一致；切换后未加载结果时详情应清空或恢复该项目对应结果。
- 实际：候选区回到 pending，但下方详情仍显示上一次 policy_search 的已完成结果和失败 Check。
- 根因：`switchProject()` 重置 `caseResults` 和候选区，却未重置或按项目恢复详情 DOM。
- 最小修复：项目切换时清空详情与 batch 进度日志；显式加载最近结果时再渲染。
- 同路径回归：待修复后重复切换，确认无旧结果残留。

## PS-BROWSER-007：浏览器 Console 固定出现 favicon 404

- 状态：已确认，待修复
- 严重度：低
- 修复方案确定性：100%
- 浏览器复现：打开 Summary 页并查看 F12 Console/Network。
- 预期：基础页面加载无无意义的 404 噪音。
- 实际：`GET /favicon.ico` 返回 404，使 Console 固定出现 error。
- 最小修复：页面声明 data URL favicon，避免额外请求。
- 同路径回归：待修复后重新打开页面，Console 无 favicon 404。

## 已验证正常的 Policy Search 行为

- atomic_condition：`sum_ins GTE 500000`，Live 与 Judge 均正常。
- time_boundary：`pol_effective_date_term BETWEEN [2026-08-01, 2026-09-01)`，边界正确。
- unsupported：返回 `UNSUPPORTED`，不返回部分 filter，页面按成功完成的业务决策展示。
- Mock 数据集：页面可加载并展示完整 AskBob 请求；已测的三类场景未出现 console 异常。

## BUG-20260811-001：Authority 关闭时 Judge 伪造职责边界结论

- 状态：已修复并完成定向回归
- 严重度：高
- 修复方案确定性：95%
- 复现路径：以 `verifier.authority.enabled=false` 编译 client_search Judge 上下文，回放 `001-run` 中 088、093、113、133 等空结果且职责边界未决的 case。
- 预期：Authority 关闭只代表当前无法查询职责依据；边界候选仍需保留，且在没有冻结 MaterialDecision 或 resolved Authority 结论时，blocking assessment 应为 `not_evaluable` 并要求人工复核。
- 实际：旧实现清空 Authority 候选，并把字段存在且 `is_supported=false` 推导为职责内能力缺失，强制输出 `not_fulfilled`。
- 根因：Authority 工具开关与边界候选识别被错误绑定，同时项目级后处理加入了没有业务依据的职责推导。
- 修复：保留候选原因并暴露 `disabled_with_candidates`；删除错误职责推导；对 Authority 关闭且空条件的未决边界应用统一 gate，重算总体状态与摘要。
- 同路径回归：088、093、113、133 从 `not_fulfilled` 修正为 `not_evaluable`；邻近正常 case 048 保持 `fulfilled`；相关最小回归 16 条全部通过。

## BUG-20260811-002：LLM `/models` 探活误判真实生成能力

- 状态：已修复并完成真实链路回归
- 严重度：高
- 修复方案确定性：100%
- 复现路径：配置 primary、fallback1、fallback2 后，从任意高层 LLM 调用入口触发超过三分钟未检查的渠道健康刷新。
- 预期：健康检查应验证目标模型的真实短生成链路，生成不可用的端点不能承接业务请求。
- 实际：旧实现只请求 `/models`；primary 的 `/models` 返回 200，但相同端点的 `gpt-5.6-luna` Chat Completions 实际返回 Cloudflare 502。
- 根因：模型列表接口与实际生成接口不是同一条能力链，不能代表指定模型可生成。
- 修复：公共 `LlmRouter` 通过端点自身的 URL、模型和凭证并行发送随机 nonce 的短生成请求，`temperature=0`、`max_tokens=4`、单端点超时 10 秒；结果缓存三分钟，并由 single-flight 合并同一路由器上的并发刷新。
- 同路径回归：primary 被判定为冷却；fallback1、fallback2 均返回真实 reasoning token 并判定健康；首轮并行探测约 6.8 秒，三分钟内再次刷新为 0 秒额外等待，随后选择 fallback1。

## BUG-20260811-003：LLM 降级尝试上限遗漏已配置端点

- 状态：已修复并完成定向回归
- 严重度：高
- 修复方案确定性：100%
- 复现路径：配置三个 LLM 端点，令前两个端点请求失败、第三个端点可用，再从任意高层 LLM 调用入口发起请求。
- 预期：单次请求依次尝试所有尚未尝试且可选的端点，每个端点最多一次，第三端点可正常接管。
- 实际：旧 `llm.max_attempts=2` 在存在三个端点时只尝试前两个，第三个健康端点永远不会被使用。
- 根因：业务尝试次数与端点池规模分别配置，二者可以产生不一致。
- 修复：删除 `llm.max_attempts` 与 `llm.retry_delay_seconds`；业务调用按实际端点数量遍历，以请求内 `exclude` 集合保证每个端点最多尝试一次，失败后不额外 sleep 并立即切换。
- 同路径回归：覆盖三端点顺序、冷却端点选择、全部端点已尝试后的确定性失败；LLM 路由及运行时配置相关 48 条测试全部通过。

## BUG-20260811-004：降级成功后上下文审计仍标记主模型

- 状态：已修复并完成高层 API 回归
- 严重度：中
- 修复方案确定性：100%
- 复现路径：让 primary 健康探测失败并由 fallback1 承接 `/api/judge`，随后查看该 trace 的 context-store 记录。
- 预期：审计记录应展示每次业务尝试的端点、模型以及最终选中的端点和模型。
- 实际：旧记录只有 attempt 序号、状态和耗时，顶层 `llm_model` 固定写入 primary 模型；降级虽然成功，但无法从审计证据判断实际由哪个渠道完成。
- 根因：`LlmClient` 记录运行信息时没有携带所选 `LlmEndpoint`，`_track_context` 直接使用客户端默认模型。
- 修复：每条 attempt 记录 `endpoint` 与 `model`；成功后记录 `selected_endpoint` 与 `selected_model`；顶层 `llm_model` 使用实际选中模型。
- 同路径回归：真实 `/api/judge` 返回 200；context-store 明确记录 `selected_endpoint=fallback1`、`selected_model=deepseek-v4-flash-0731`，attempt 1 成功且无错误；相关 48 条测试全部通过。

## BUG-20260811-005：Authority 关闭时仍注入不可执行的前置义务

- 状态：已修复并完成高层 Judge 回归
- 严重度：中
- 修复方案确定性：100%
- 复现路径：保持 `verifier.authority.enabled=false`，从 Draft Judge 正常入口运行包含能力/职责边界候选的 073 或 148。
- 预期：上下文只应告知 Authority 不可用及依赖边界的 blocking assessment 处理规则，不应注入只能在 Authority 可调用时消费的资料对账义务。
- 实际：旧上下文仍注入 13–18 条 `pre_obligations`、资料管辖摘要和调用后消费规则；073/148 的该段分别约 6.9K/9.5K 字符，既无法执行，也会稀释当前 case 的关键证据。
- 根因：`_build_core_context()` 无条件构造并注入完整 `authority_obligation_contract`，没有按 `authority_required` 投影。
- 修复：Authority 可用时保留完整前置义务；Authority 关闭或本案无需 Authority 时，仅保留触发原因、`authority_available=false` 与定点 `not_evaluable` 规则。
- 同路径回归：073/103/148 的 user extras 分别由 17,314/12,380/25,741 字符降到 10,666/9,301/16,528；148 仍判 `not_evaluable`，输入 token 由 18,408 降到 15,222，耗时由 111.7 秒降到 86.5 秒；相关 Judge 测试 41 passed、1 deselected。

## BUG-20260811-006：LLM 健康与冷却状态未跨高层调用复用

- 状态：已修复并完成定向回归
- 严重度：高
- 修复方案确定性：100%
- 复现路径：连续运行多个 Draft Judge case；每个 case 都新建 `LlmClient`，同时令 primary 返回 503、fallback 可用。
- 预期：相同端点池共用三分钟健康与冷却状态；首个 case 确认 primary 不可用后，后续 case 应直接选择健康 fallback，不再重复探测或撞击 primary。
- 实际：旧实现为每个 `LlmClient` 新建 `LlmRouter`；前一个 case 记录的失败、冷却和最近健康时间随 client 生命周期丢失，后续 case 会再次探测并请求同一个坏端点。
- 根因：公共降级设施只共享了路由代码，没有共享端点池对应的运行状态，导致 circuit breaker 实际退化为单次调用状态机。
- 修复：按端点名称、URL、模型和凭证组成的精确端点池键，在进程内复用同一个 `LlmRouter`；注册表加锁，不同端点池继续隔离。
- 同路径回归：两个相同配置的 `LlmClient` 获得同一 router；第一个 client 将 primary 打入冷却后，第二个 client 立即选择 `fallback1`；不同模型配置获得独立 router。公共路由、运行时配置与 Draft runner 测试 49 passed，Judge 定向测试 41 passed、1 deselected。

## BUG-20260811-007：Draft loop 绕过公共 Router 重复探活并指数退避

- 状态：已修复并完成定向回归
- 严重度：高
- 修复方案确定性：100%
- 复现路径：Draft loop 开启 health check，配置的所有端点不可用或已进入三分钟冷却；运行任意 Current/Draft case。
- 预期：Draft loop 直接消费公共 Router 的真实短生成健康状态；端点池全部冷却时立即失败，不再次撞击端点，也不在整案层额外等待后重跑。
- 实际：旧 runner 自己通过 `urllib` 串行请求 `/models` 和 `/chat/completions`，与公共 Router 的并行探活、三分钟缓存和 single-flight 完全分离；业务侧失败后又执行 10/20/40 秒级指数退避并整侧重跑。即使 Router 已尝试完所有端点，runner 仍会制造重复请求和长时间无效等待。
- 根因：端点健康、降级和重试职责同时存在于 `LlmRouter` 与 Draft runner，两套机制的状态和时序不一致；Router 在所有端点冷却时还会强选最早恢复端点，破坏 circuit breaker 的快速失败语义。
- 修复：Draft preflight 改为构造正常 `LlmClient` 并直接复用其共享 Router 健康刷新；删除 runner 私有 HTTP 探活与指数退避设施；端点类失败不再整侧重跑；所有端点冷却时 Router 明确抛出快速失败，冷却到期后再由统一短生成 probe 恢复。
- 同路径回归：全冷却 router 不再选择任何端点；Draft preflight 只触发一次公共健康刷新；配置 `attempts=4` 的端点失败只执行一次 side 调用。公共路由、运行时配置与 Draft runner 测试 49 passed，Judge 定向测试 41 passed、1 deselected。

## BUG-20260811-008：Authority 关闭时边界候选被静默改成 not_evaluable

- 状态：已修复并完成定向回归
- 严重度：高
- 修复方案确定性：100%
- 复现路径：保持 `verifier.authority.enabled=false`，从 Draft Judge 正常入口运行 088、093、113、133 或 148 等核心条件未交付、同时命中能力/职责边界候选的 case。
- 预期：Authority 关闭模式只评价 Live 是否满足用户意图；核心结果缺失或错误应为 `not_fulfilled`，不得因未启用治理能力自动变成 `not_evaluable`。
- 实际：旧 Prompt、unsupported evidence 和 `_apply_unresolved_boundary_gate` 都要求边界候选在 Authority 关闭时判 `not_evaluable`；operator conflict 还有第二条确定性 NE 路径。该行为把“没有启用 Authority”错误等同于“Authority 已查证但 unresolved”，并掩盖 Live 未满足用户意图的效果缺陷。
- 根因：Judge 把意图/交付事实分析与业务标准治理混成单一 fail-closed gate，并把 Authority 缩成职责边界前置条件；没有区分 Authority 关闭的非治理效果评价和 Authority 开启的正式裁决。
- 修复：协议明确“意图与交付事实 → 可选 Authority 治理 → 最终三态”；删除 Authority 关闭强制 NE gate；关闭模式按可见交付判 F/NF，operator 违反当前可执行契约时判 NF；开启模式继续消费语义映射、查询等价、能力、职责和冲突裁决，职责外或真实 unresolved 才判 NE。
- 同路径回归：Authority 关闭的空交付、显式不支持、部分维度遗漏和 operator mismatch 均稳定保留/得到 NF；Authority 开启的 unresolved 与缺少裁决引用仍保持 NE。Judge 定向测试 41 passed、1 个网络 smoke deselected。
- 真实链路回归：以正常 Draft loop 运行 073/088/093/113/133/148 六例，Draft 全部按核心交付缺失判 `not_fulfilled`；Production 对应为 `not_evaluable/fulfilled/fulfilled/not_fulfilled/fulfilled/not_evaluable`。六例均完成，运行中的两次 relay 502 由公共 Router 接管，未触发整轮重跑。

## BUG-20260811-009：Summary 只加载固化 Mock 数据集的前三条

- 状态：已修复并完成浏览器同路径回归
- 严重度：高
- 修复方案确定性：100%
- 复现路径：浏览器打开 Summary，选择 `policy_search`，点击“加载 Mock 数据集”。
- 预期：候选区加载项目已固化的完整数据集，并通过分页承载大数据量。
- 实际：前端请求把 `count` 硬编码为 3；磁盘已有 400 条时，页面仍只显示 3 条且只覆盖 `atomic_condition`。
- 根因：页面加载逻辑沿用了早期轻量预览上限，而候选区已经具备 500 条上限和分页能力，两者语义冲突。
- 修复：复用现有 API 的 500 条合同加载固化数据集，保留候选区现有的 500 条安全上限与每页 100 条分页，不增加配置层。
- 同路径回归：浏览器绕过旧静态缓存重新打开 Summary，选择 `policy_search` 后加载出 9 批、400 条，候选区显示每页 100 条。

## BUG-20260811-010：Live 新请求失败后仍展示上一条成功 Trace

- 状态：已修复并完成浏览器同路径回归
- 严重度：高
- 修复方案确定性：100%
- 复现路径：浏览器在 Live 页先运行可成功的“9月生效的康宁险种保单”，再改成会失败的查询并点击“请求业务服务”。
- 预期：新请求开始时上一条 Trace/Judge/Attribute 立即失效；失败后结果区应为未运行，不能展示旧输出。
- 实际：顶部提示新请求失败，但业务请求结果仍为 `ok`，继续展示上一条时间查询的 Trace，输入框与结果互相矛盾。
- 根因：`liveRun()` 和 `runChain()` 只在成功后覆盖页面状态，开始新请求和失败分支都没有清除内存及 sessionStorage 中的上一条链路结果。
- 修复：新业务请求/全链路开始前统一清空当前项目的 Trace、Judge、Attribute、Cluster、Frontend View 与 lastChain，再渲染空状态。
- 同路径回归：先成功运行“9月生效的康宁险种保单”，再运行失败的“不支持生存金”查询；失败后业务状态为“未运行”、结果区显示“尚未请求业务服务”，Raw JSON 为 `{}`，且页面不再包含上一条的 `pol_effective_date_term` 输出。

## BUG-20260811-011：Authority 关闭时 capability gate 覆盖 Judge 语义结论

- 状态：已修复并完成定向回归
- 严重度：高
- 修复方案确定性：100%
- 复现路径：在 `authority=false` 下，通过 8024 最近批次运行 `family_property_claim-004/005/006/007/011/018/019/020`；Live 将家庭成员年龄转换为 `familyInfo.familyclientbirthday` 的 `GTE/LTE/RANGE`。
- 预期：按项目已声明的年龄→出生日期语义等价规则判定 `fulfilled`。
- 实际：Judge 将 8 个本应 fulfilled 的 case 判为 `not_fulfilled`；其中 10 个 assessment 同时保留 `score=1.0` 和“可正确筛选/等价/无影响”等正向说明，Check 仍报告通过。
- 根因：Authority 引入后的 `_apply_operator_capability_check` 在 `authority=false` 时仍作为确定性后置 gate，将已经由用户意图、Live 交付和语义等价链路判为 fulfilled 的 assessment 强制改写为 NF。capability manifest 因而错误取代了 Judge 语义主链路。
- 修复：`authority=false` 时 capability gate 在产生 evidence 或改写 assessment 前直接返回；F/NF 继续由 Judge、condition comparison 与 semantic equivalence 决定。`authority=true` 的 NE/Authority 路径保持不变。
- 同路径回归：capability/等价表达定向测试 8 条全部通过；8024 最近 20 条真实批次离线回放由旧 gate 的 `12/20` 恢复为语义链路 `20/20`，8 条 false NF 清零，009/010/014 三条真实 NF 保持 NF。完整调查测试 31 条通过，另 1 条仅因 Authority LLM 端点全部 cooling 导致 probe 失败，与本修复无关。

## BUG-20260811-012：公共 Trace 序列化删除 live schema 必填空列表

- 状态：已修复并完成浏览器同路径回归
- 严重度：高
- 修复方案确定性：100%
- 浏览器复现：在 Summary 选择 `policy_search` 并加载 Mock 数据集；保留一条用例勾选后点击“批量运行”。同页对照未运行行和已运行行的 Input / Live Request。
- 预期：`RunTrace.input`、`normalized_request`、`turn_records[].request` 和 `live_exchanges[].request` 与实际请求严格相等，空 contexts 继续存在并通过项目 live schema。
- 实际：旧公共 serializer 对任意 dict 递归删除 `None`、`[]`、`{}`；运行前 MockCase 中存在的 `contexts: []` 在运行后的四处 Trace 请求事实中全部消失。400 条 rich mock 原始请求全部合法，旧序列化后只有 16 条非空 contexts 用例仍合法。
- 根因：`impl/core/schema/occam.py` 最初把公开展示压缩规则错误应用到了不可改写的协议请求事实；第一次修复只覆盖了有类型的 `RunTrace`。Summary 异步批量链路会先在 `compact_run` 中把 Trace 转成普通 dict，随后 route 再次公共序列化，第二次因丢失 schema 身份而重新删除空值。这也是单链路回归通过、真实批量页仍失败的原因。
- 修复：保留现有 `PUBLIC_SCHEMA_FIELDS`、`PUBLIC_DROP_KEYS` 与协议外空值压缩；请求事实原样保留显式空值和全部请求键；对已经物化为 dict 的严格 RunTrace 结构恢复 schema 身份并复用同一公开字段规则，使公共序列化幂等。不读取项目 ID、不投影项目 schema、不自动补 contexts，非法请求继续非法。
- 自动回归：增加公共序列化幂等及 `compact_run -> batch status -> route serializer` 的 event/final 两条真实边界回归；四个请求事实位置均与原请求严格相等且通过 Policy Search live schema。
- 浏览器同路径回归：重启 8022 后在 Summary 加载 2 条 Policy Search Mock，只勾选 1 条并点击“批量运行”；页面完成 `1 / 1` 后，已运行行与未运行行均保留 `args.contexts: []`，已运行行不存在 `args: {}`，`application_setting: null`、`scenario: null` 等显式协议事实也仍存在。
