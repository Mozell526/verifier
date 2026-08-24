# Iteration 001 — Harness Review Recommendation (draft, 待人工批)

> 建议稿，不落 loop.json、不推进迭代。请人工批改后才可调用 review。

## 建议 decision / route
- decision: `insufficient_evidence`
- route: `investigate`
- 一句话：iteration 001 业务判定无退化、有 3 例方向性修复，但 5 条 not_evaluable 中
  3 条（113/133/138）是 authority tool_failure 落盘，不满足 review 标准
  "unresolved 原因和所需证据必须可审计"，不足以作为"可证明改善"建议选中。

## 证据：30 条翻转矩阵（frozen, source=b4ffbb62）
- 两侧一致：22 条（无退化）
- 方向性改善：123 (nf→fulfilled)；088、148 (fulfilled→nf，authority 证明本可支持却被拒)
- 如实拒绝→说不清：093/113/133/138 (fulfilled→ne)
- 依据不足：008 (nf→ne)
- 无任何反向退化（current 对 draft 无"改差"）

## 未通过 review 标准的点
- 113/138 authority = tool_failure×2（search 后未紧跟 load / key-index 候选悬空）
- 133 = gap_only（可审计）+ tool_failure×1
- 148 = tool_failure×1（tool_budget_exceeded）；其 draft 判定 not_fulfilled
- 影响：这 3 条 ne 没有 required_evidence 缺料清单、证据链回不到实际 Load，
  与 fulfilled.md §10"依据链可回溯 + 缺料清单"冲突；需要Authority 侧决定：
  (a) 放宽 `_validate_authority_tool_sequence` 允许 search→search→load / 终态前消费，
      使模型导航偏差转成 unresolved+required_evidence（可审计）；
  (b) 或按之前"nav 噪声不追"策略，接受 tool_failure fail-closed ne（但过不了 §10 严格栏）。

## 下一步（investigate）
1. 已落地：非端点型执行失败→unresolved/gap_only+缺料清单（impl/core/authority_tool.py，116 测试绿）。
2. 以真实 LLM 重跑迭代（默认 workers=4，不压 2）验证 113/133/138/148 变为可审计 ne。
3. 通过后重新 review，才谈 promotion。
