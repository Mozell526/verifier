# 20260810 Authority EFS hash 漂移 check report（上下文工程）

## 背景

用户换用相对固定仓库（`.env` → `client_search_jmz_raw`，HEAD=b4ffbb62）并要求按新仓库冻结。
检查 authority 上下文工程时发现：investigation manifest 登记的 business_source EvidenceRef hash
与冻结源 b4ffbb62 实际内容不一致（`source_staleness_cli report-drift` 权威输出 3 个 `needs_review`）。

## 发现

`impl/projects/client_search/draft/investigation/judge/manifest.json`（source_revision=b4ffbb62）中：

| ref_id | manifest 登记 sha256 | b4ffbb62 实际 sha256 | routing | 影响 |
|---|---|---|---|---|
| business-field-enums | 2fdedff78ab5 | 756787c38295 | needs_review | business-field-enums.decision-1（orphanType 枚举空间） |
| business-enhanced-rules | 48ede687a71c | 341621b2e16d | needs_review | business-enhanced-rules.decision-1（familyclientbirthday 操作符） |
| business-time-knowledge | 5b2ba2dd8b79 | dbea6c340f6a | needs_review | business-time-knowledge.decision-1（无注册消费者，fail-closed） |

其余 3 个 business_source refs（field-definitions / value-mappings / planfullname-enums）hash 一致。
`jmz` 与 `jmz_raw` 两仓库同 HEAD=b4ffbb62、文件内容一致，说明 manifest 的 EFS hash 是**换仓库前更早状态**固化的，
换仓库后只更新了 source_revision 字段，EFS hash 未重钉。

## 定点重验证（本轮已人工复核，无 LLM）

- business-field-enums.decision-1（orphanType 合法枚举空间）：
  新文件 orphanType.values = [在职有效客户, 纯存续单客户, 非纯存续单客户]，与 claim `orphan-type-enum-space` 一致，**结论仍成立**。
- business-enhanced-rules.decision-1（familyclientbirthday 操作符规则）：
  新文件仍含 `家里老人-出生年份之前`（LTE）等 familyclientbirthday 规则，**结论仍成立**。
- business-time-knowledge.decision-1（相对时间词换算口径，current_behavior）：
  新文件仍含 week_offset/next_month 等条目；无注册消费者（fail-closed），仅需重钉 hash。

## 运行时影响

- authority_environment 在 warn policy 下用当前实际内容物化（不 fail），所以 001-run 与 A/B 冒烟
  的判定基于**当前正确内容**，判定方向不受影响；
- 但 manifest 登记 hash 过期违反"冻结资料一致性"审计要求（资料引用与冻结源 revision 不对齐），
  promotion 的 strict policy 会 fail-closed，需先重钉。

## 建议（待人工确认）

1. 按当前冻结源 b4ffbb62 重钉这 3 个 EFS hash（重新固化 manifest + 重新生成 solidify receipt）；
2. 重钉前先确认 enhanced_rules_args.yaml 的未提交本地改动（`git status` 显示 M）是否应纳入冻结，
   避免重钉后又漂移；
3. 重钉后重跑 report-drift 应全部 clean。

> 状态：发现已记录；未擅自重钉（尊重"先别动/先处理上下文问题"）。待人工确认后再执行重钉与 002 重跑。
