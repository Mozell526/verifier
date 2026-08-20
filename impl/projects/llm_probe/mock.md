# Mock

默认使用固化 fixture。种子 case 从现有非流式项目的 live_request 转成信封，并带上 `capability_ref`。

动态生成只保证 REQUEST_SCHEMA 形状：`body` + `capability_ref`。意图层不是本项目的输入。
