# Discovery — 1A 内存评测模拟

脚本：`issues/trace/simulate_1a_name_program.py`
落盘：`issues/trace/simulate_1a_name_program.json`
命令：`python3 issues/trace/simulate_1a_name_program.py`

本轮不 import / 不改 `draft/judge.py`。叠加只动「2–4 字中文名」出口；去年 / 格式外 / 称谓 10 条 parked，两口径都保持原状态。

## 三列对照（集 A，N=341）

| 口径 | F | NF | 相对当前翻面 |
|---|---:|---:|---:|
| 当前新 judge | 213 | 128 | — |
| 1A-wide（凡 2–4 字、非盘客 → F） | 220 | 121 | 19 |
| 1A-surname+catalog（先目录/盘客/业务词，再姓+名撑 F） | 209 | 132 | 8 |

## 双闸探针

政策：杨杰与王坤林同侧=F；共展/豆芽仍 NF。

| 探针 | 当前 | 1A-wide | 1A-surname |
|---|---|---|---|
| 杨杰 / 郑鑫 / 匡西永 | F | F | F |
| 王坤林 | NF | F | F |
| 昊轩（二字无姓） | NF | F | NF（§4.3 仍未拍） |
| 共展 / 豆芽 / 见光 / 傻生 | NF | **F（回退）** | NF |
| 金凤 / 宝贝卡 / 孝心 / 满意 / 陇佑智盛 | F | F | F |
| 查金风（I344，`searchClientName=金风`） | NF | NF | NF（目录投影「金风」拦住） |

## 1A-wide 19 翻面（不可上线）

抬成 F：十里堡、傻生、细岗、见光、昊轩、王坤林、家办客户、豆芽、共展；以及空条件「老客户」「续收」、`客户`、`财富分群`。

压成 NF：张忠波/高吉禄/胡秀清/胡蒙刚/叶成群 +「保单号」；居家潜客。

## 1A-surname 8 翻面（探针过，残留在）

该抬的：王坤林 NF→F。共展族仍 NF。

残留误伤：上面 5 条「姓名+保单号」F→NF（规则里的「保单」子串）；居家潜客 F→NF（「潜客」过宽）；家办客户 NF→F（「家」在百家姓）。

## 集 B

`impl/projects/client_search/draft/cases/head_set_b.json` 18 条，无 live、无 judge 痕迹。
两口径都是程序出口 18/18 F，**不是**重跑 LLM judge。

## 编号说明

`issue-013`–`015` 属于已归档章程 `charter-unsupported-label.md`（开关 2/3）。用户已声明 2/3 先不动。本轮新开 `issue-016`–`018`。
