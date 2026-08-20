# Application

llm_probe 评估任意非流式 HTTP JSON 接口里带 LLM 的那一截。

Case 的 live_request 是 curl 信封：`body` 是被测接口的原生 JSON；`url` / `method` / `headers` 描述怎么发；`capability` 或 `capability_ref` 给出能力口径；`show_schema` 可选，告诉 judge 输出里哪些部分重要。

HTTP JSON body 只发 `body`。url 缺省时按 `capability_ref` 去对应项目的 `runtime.services.primary` 拼。`runtime.services.primary` 在本项目里只是模式占位，真正目标由 case 决定。

被测服务由调用方自行启动。verifier 不拉起、不重启这些服务。
