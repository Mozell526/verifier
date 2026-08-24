# Loop 对比表

每轮 review 必出；由 `scripts/render_loop_comparison_table.py` 确定性渲染前几列事实；禁止只贴聚合指标、禁止手写替代表。

## 基础列（每轮必出）

| case | query 输入 | live 输出 | production <role> 结果 | draft <role> 结果 | harness 分析 |
| --- | --- | --- | --- | --- | --- |
| `<case>` | `<query 输入>` | `<live 输出>` | `<production <role> 结果>` | `<draft <role> 结果>` | `<Harness AI 按该 Role 的 ROLE.md 填写>` |

- `query 输入` = live 用户请求
- `live 输出` = 冻结 trace 的 Live 对外输出（不是 Role 判定）
- `production <role> 结果` / `draft <role> 结果` = 该 role 两侧原始判定
- `harness 分析` = 必出最后一列（排在 production/draft 之后；若有场景列，也排在场景列之后）。**不是 Role 判定。** Python 渲染器只填 `-`，不得撰写分析；**Harness AI 在 review 时逐 case 填写。** Review 引用该表前，这一列不得再是 `-`。写清有把握哪侧更好、两侧都对/都错、还是不计分；不计分的案不进净胜、不改候选。Judge 场景如何填 harness 分析见 `../judge/ROLE.md`。Mock 及其他 Role 按各自 `ROLE.md` 填写。

## 场景列

- role=judge 且任一侧存在 authority 调用时，自动追加 `authority(production)` / `authority(draft)`（调用数 + resolution 状态）
- 其他场景通过 `--scenario-columns '{"列名": "row 内点号路径"}'` 注入对应列
- 场景列插在 production/draft 结果之后、`harness 分析` 之前

## 落盘

与 run report 同目录：`<NNN>-run-comparison-table.md`

## Review evidence

必须同时引用：

- `<NNN>-run.json`
- `<NNN>-role-review.json`
- `<NNN>-run-comparison-table.md`
