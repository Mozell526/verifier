# Checklist

- live_request 必须能解析出 url 或 capability_ref，以及 capability 或映射表里的能力描述。
- HTTP JSON 只发 body，信封字段不能出现在被测服务的请求体里。
- EXTRACT 只有 output_text 字符串。
- 流式响应必须失败，不能进入 judge。
- attribution.enabled 为 false。
- 轴2 走文本形态：capability 预设的 `boundary` 为 G。未填则每条未达成期望归位为「说不清（缺能力边界资料）」。
