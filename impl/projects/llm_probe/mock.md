# Mock

默认使用固化 fixture。种子 case 从现有非流式项目的 live_request 转成信封，并带上 `capability_ref`。

动态生成按 capability 预设（资料管理页维护，存于 `impl/data/llm_probe/capability_map.json`）中目标项目的 `mock_body` 模板产出可被目标服务接受的 `body`（`{query}` 占位符注入意图问句），并带上 `capability_ref`。默认 `capability_ref` 按 key 排序选取，不依赖键序。意图层不是本项目的输入。
