# Check list — 姓名泛化内存实验

范围：本轮只审查内存实验与判定出口形状。不改 `draft/judge.py`、xlsx、canvas、集 B、前端。
前端 `http://127.0.0.1:8011/index.html` 本轮不测（没有生产改动）。

| # | 检查项 | 结果 |
|---|---|---|
| C1 | 过度规则化：候选是否还在写 12 种姓名题型 / 保单号正则 / 用 pack role 分流 | 通过。`exit_live_identity` 只问整句是否被 live 收成一个身份字段。`exit_role` 列为负对照 |
| C2 | 局部样本修改：是否点名 341 ID 或写「王坤林算人名」 | 通过。脚本不点名 ID。昊轩靠「无姓则 inherit」abstain，不写死 ID |
| C3 | 只改结果不改源头：有没有把 41/47 当修完 | 通过并记入 028。源头仍是 L1504–1508 与 1A 互搏；本轮不发版 |
| C4 | 数据不同步：有没有改 xlsx / 集 B / 冻结 traces | 通过。只用冻结 `name_scenario_runs/` |
| C5 | 投机刷分：有没有用问句补姓名把 HB009–014 抬 F | 通过。六条 inherit NF |
| C6 | 投机改标准：有没有把 昊轩 擅自标成必须 F/NF | 通过。inherit，§4 仍停住 |
| C7 | 假姓名闸是否变成「只靠 inherit 刷 NF」且假装已解决 | 部分暴露。共展/豆芽 inherit NF 是 fail-closed；正例靠姓氏目录，不是黑名单。未声称假姓名检测已完成 |
| C8 | 业务单元格 1A/4A | 通过。杨杰=王坤林=F；共展/豆芽=NF；合法单号 F；姓名+产品不报 F |
| C9 | 双闸集 A | 通过。live_identity 只抬王坤林；盘客/假姓名/目录产品不回退 |
| C10 | 改代码前向用户确认 | 本轮不改生产代码 |

修改前先向用户确认。本轮结论：不要并进 `judge.py`。

| C11 | I248 实际分支是否被说成「四字名」 | 已收紧。architect 钉死是 `PERSON_THEN_POLICY`（`保单号?`），不是 `BARE_NAME` |
| C12 | 修改生产代码前向用户确认 | 通过。028 escalate，本轮零代码 |
| C13 | 优雅性：有没有把负对照再打补丁修成第二套机 | 通过。exit_role 保持负对照，不修 |

architect spawn-id `8eecb710b62b55a7`：exit 0，isolation + scope 有效。Consensus 已写。
