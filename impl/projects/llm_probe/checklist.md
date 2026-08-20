# Checklist

- live_request 必须能解析出 url 或 capability_ref，以及 capability 或映射表里的能力描述。
- HTTP JSON 只发 body，信封字段不能出现在被测服务的请求体里。
- EXTRACT 只有 output_text 字符串。
- 流式响应必须失败，不能进入 judge。
- attribution.enabled 为 false。
- 轴2 暂不接入（接入判定第①问不通过）：本项目不拥有受治理能力空间，能力口径是
  case 自带的自由文本或借自 capability_map.yaml 指向的业务项目，物料归属在被探测项目。
  不开 `enabled_scopes`，不写 `capability_provider`。
