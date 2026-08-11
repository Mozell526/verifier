# 2026-08-01 Judge 边界/未支持口径 + 148 权威性 check 报告

审查范围：draft judge 实现（impl/projects/client_search/draft/judge.py）对照
spec/alg/authority.md 与 spec/alg/investigate-authority-judge.md；重点 case 088/133/148。
验证依据：draft iterations 005/006-run.json、probes/judge-badcase-final-30.json、
client_search 业务源配置（field_definitions/enums/value_mappings），50+28 项测试全部通过。

## 三个 case 的判定事实（production current vs draft，两轮一致）

| Case | 输入 | Production | Draft | 实际输出 |
|---|---|---|---|---|
| 088 | 7月盘客 | not_evaluable（1 NE + 3 fulfilled） | fulfilled（2 fulfilled） | conditions=[]，robot=“提示：盘客暂不支持搜索” |
| 133 | 中银保信 | fulfilled | fulfilled | conditions=[]，robot=“未识别到明确查询条件” |
| 148 | 查一下徐晓燕名下是否有住院医疗保险 | not_evaluable（姓名 fulfilled，保险 NE，交集 NE） | not_fulfilled（姓名 fulfilled，保险 NF，组合 NF） | 仅 searchClientName MATCH 徐晓燕 |

148 原始标注：机器人理解=“客户姓名为徐晓燕并且投保险种名称为住院医疗保险的客户”；标注=意图识别不对。

## 事实核验（业务源配置）

- field_enums pCategorys.values = 意外伤害/医疗/护理/疾病/定期寿/终身寿 共 6 项，**含“医疗保险”**；
  其 notes 明确：口语类词归大类，**具体产品简称/全称应映射到 abbrname / planfullname**。
- abbrname 完整枚举 10333 项（独立配置文件），**含“住院医疗/住院医疗A/B/团体住院医疗”等**；
  planfullname 完整枚举 7343 项，**含精确值“住院医疗保险”**。
- 但 manifest 只加载 field_enums_args.yaml：abbrname 仅 25 项（百万医疗+税优），
  planfullname 0 项，二者均带 unresolved_enum_refs（`polNoInfo.plancodeinfo.abbrname` /
  `.planfullname` 两个 enum_ref 在 field_enums 中不存在）。
- value_mappings：医疗险/医疗产品→医疗保险；无“住院医疗/住院医疗保险”直接映射。

## 发现的问题

### F1（P1）draft judge 规则 A/B 自相矛盾，088 被误判 fulfilled
judge.py system_extras 中：
- 规则 A（~836-838）：actual 明确提示请求条件暂不支持（acknowledges_requested_constraint=true）
  → 该维度判 not_fulfilled（归因能力边界），**不得判 not_evaluable**；
- 规则 B（~885-888）：all_conditions_unsupported=true（提示重叠 + 零条件）→ **判 fulfilled**。

同一“系统明确提示不支持”证据，两个规则给出相反结论，且只有 A 有确定性兜底
（_apply_graceful_degradation_check），B 仅靠 prompt。088 的 draft fulfilled 正是踩中 B。
按 spec authority.md §11.3 / §8：能力缺失且无法确定的 blocking 维度不得输出肯定结论，
应 not_evaluable 并说明原因；边界处理子目标（透明告知、不虚构条件）可 fulfilled。
即 088 的正确口径应与 production 一致：核心目标 NE + 边界子目标 fulfilled。
规则 B 与 spec 冲突，规则 A 的“不得判 not_evaluable”同样与 §11.3 表述存在张力。

### F2（P2）148 的 production not_evaluable 依据不成立
production 理由为“capability_manifest 仅提供 searchClientName，未提供住院医疗保险对应字段/
枚举或值映射”+ “field.search_definition 返回 field '住院医疗保险' not found”。
事实相反：pCategorys 枚举含“医疗保险”，value_mappings 有 医疗险→医疗保险；
且 field.search_definition 查的是**字段名**而非**枚举值**，not found 不能证明能力缺失。
保险维度实际可表达 → actual 遗漏该条件应判 not_fulfilled（draft 方向正确），
production 的 NE 是把“调查方式错误”当成了“能力缺失”。

### F3（P2）148 存在真实字段归属歧义，属 authority 应介入点，draft 未调用
draft 用 prompt 规则把“住院医疗保险”→ pCategorys 医疗保险（大类），
与 field notes（具体产品名→abbrname/planfullname）冲突；且 abbrname/planfullname 完整枚举
未加载进 manifest，judge 证据空间根本看不到“住院医疗/住院医疗保险”这两个值。
这正是 spec 描述的“多份资料对同一业务条件说法不同、直接证据不足”场景，
应按 §7/§8 调用 authority.resolve；draft 该 case authority_tool_call_ids 为空，未走 authority 链路。
（结论方向不受影响：无论走哪个字段，actual 都漏了保险条件 → not_fulfilled；
但期望条件字段与权威资料归属需要说清，否则后续 case 会用错误字段引导 parser。）

### F4（P3）abbrname / planfullname 枚举加载不完整（影响面不止 148）
manifest 对 polNoInfo.plancodeinfo.abbrname / planfullname 只加载了百万医疗、税优两组
业务词枚举，完整产品名枚举（10333 / 7343 项）未并入（unresolved_enum_refs）。
所有“买了 e生保”“投保险种名称为 X”类具体产品名 case 都会受影响，属于源头配置加载问题。

## 与 spec 符合性结论

- authority 架构（AuthorityEnvironment / authority.resolve tool / audit / gate）已落地，
  gate 的 unresolved→not_evaluable、引用缺失→needs_human_review 行为符合 authority.md §8；
  相关 50 项测试通过。
- 不符合项集中在 judge 侧 unsupported 兜底口径（F1）与 148 证据空间/权威性使用（F2/F3/F4）。

## 建议修复方向（待用户确认后执行）

1. 统一 unsupported 边界口径（修 F1）：核心业务目标（请求条件对应交付）→ not_evaluable
   （能力边界，不给肯定结论），边界处理子目标 → fulfilled；删除 B 的 fulfilled 与 A 的
   “不得判 not_evaluable” blanket 表述，prompt 与确定性兜底保持一致。
2. 修 manifest 枚举加载（修 F4）：将 abbrname/planfullname 独立枚举文件并入 capability
   manifest，消除 unresolved_enum_refs，使 148 这类产品名 case 可确定性判定。
3. 148 修复后重跑 30 case 回归，确认 draft 效果不倒退（当前 draft 在 148 已比 production 准，
   修复主要防 088 类偏差与后续产品名 case）。
