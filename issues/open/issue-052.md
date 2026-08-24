# Issue #052: 新实验必须打 judge 自己；针过了，混合包分数不是发版 KPI

**Class**: evaluation
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: draft judge + `issues/trace/simulate_field_sufficiency_host.py`
**Cases**: 合成针 13 条；冻结混合包 9 条；field_only 误抬 7 条

## Verifier Discovery

用户要在内存里调试 judge，看哪种处理较好。
较好按章程不是混合包分数最高，而是：

1. 杨杰 / 王坤林 由 **judge 自己** 判 fulfilled
2. 共展 / 豆芽 由 judge 自己 判 not_fulfilled
3. 红莲保单 / 生存金 / 李明的重疾险 不说话
4. field_only 那 7 条误抬不得复现
5. 真名+产品没交姓名，保持失败（解析，不是判定补人）

旧脚本 `simulate_1a_sufficiency_program.py` 是 overlay，不再当生产。
新实验 import 的是 `field_sufficiency` 和 `ClientSearchJudge`。

```bash
/Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_field_sufficiency_host.py
```

落盘：`issues/trace/simulate_field_sufficiency_host.json`

本轮 verifier 跑出来的针（对手必须自己重跑，不抄）：

- 杨杰 / 王坤林 / 合法客户号：`pre_judge=fulfilled`
- 共展 / 豆芽 / 昊轩 / 金凤当姓名：`pre_judge=not_fulfilled`
- 红莲保单 / 唐诗颖生存金 / 李明的重疾险 / 李明重疾险 / 金凤当产品 / 真名+产品没交姓名：`pre_judge=None`
- field_only 仍会把 I248 / I213 / I154 / I597 / I153 / I031 / I079 抬成 fulfilled；本嘴全是 inherit
- 冻结混合包里王坤林已经是 F；过严证据在 341 集 A 的 current 标签，不在这 48 条

I210「金凤」live 交的是产品字段，不是姓名。本嘴 inherit。
当前 LLM 把它判成 fulfilled 是产品维的事，不是本轮开口。

HB009「李明的重疾险」live 只交了产品、没交姓名。本嘴 inherit，保持失败。

## 可证伪

1. 若新实验不 import `ClientSearchJudge` / `field_sufficiency`，只是又写一套 overlay，本 issue 未修。
2. 若任一合成针 `ok` 为假，本 issue 未修。
3. 若 7 条 field_only 误抬被本嘴改成 fulfilled，本 issue 未修。
4. 若用混合包 41 分或 341 对错率当发版理由，本 issue 读错 oracle。

## 请对手挑战

- 针是不是按样本特制、换一句就倒？
- `last_word` 在 inherit 时展示 leftover LLM 的 NF，会不会被误读成「本嘴主动改失败」？
- 8011 未测。若你认为没有页面实测就不能结，说需要什么最小复现。

不要把集 B 没来之前的 341 分当成胜利。不要代拟对外中文。
