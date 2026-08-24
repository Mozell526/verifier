# Issue #050: 充分性打中时，judge 必须自己说话；Q1 失败是字段标准，不是 overlay 改失败

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: draft judge `pre_judge` / `reconcile_result`
**Cases**: 杨杰 / 王坤林 / 共展 / 豆芽 / 金凤当姓名

## Verifier Discovery

044 overlay 的嘴是：只主动抬成功；Q1 失败 → inherit；从不过失败。
那是补丁政策。补丁没有资格声称「我认出这是假的」。

judge 不是补丁。用户问的是「用户要的事办成了没有」。
当充分性测试已经打中，剩下的唯一问题就是 Q1：这个值撑不撑得住这一维。

```text
恰好一个字段 且 值 == 整句 且 该字段有授权标准
  Q1 过 → fulfilled
  Q1 不过 → not_fulfilled
否则 → inherit（pre_judge 返回 None，LLM 照旧）
```

为什么 Q1 失败必须由 judge 说 NF：

删掉裸词段之后，共展 / 豆芽的形状是「值=整句、字段叫姓名」。
若 judge 此时 inherit，LLM 可能凭一级证据放成 F。那是回退，不是泛化。

这不是「认出假名」。共展走 NF，是因为它过不了已有的姓名维标准（2–4 字、有姓、不是产品/黑名单/业务后缀）。
金凤当姓名走 NF，是因为产品枚举里有「金凤」，不是因为点名了金凤。
昊轩二字无姓 → Q1 失败 → NF。这是 1A 已有行为，不是代选昊轩必须成功。

挂点：

- `pre_judge` → `result_if_speaks`；证据够时短路 LLM
- `reconcile_result` 在 comparison / operator / fail-closed **之后** `apply_last_word`
- 说话时整份合同替换成一条 blocking expectation。原因：`_derive_overall_status` 见任何一条 blocking NF 就整体 NF；只补一条 F 会被 LLM 残留的 NF 顶住

```bash
/Users/xiaozijian/miniconda3/envs/agno/bin/python -m pytest tests/test_client_search_field_sufficiency.py -q
/Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_field_sufficiency_host.py
```

## 可证伪

1. 若杨杰 / 王坤林在 `pre_judge` 不是 fulfilled，本 issue 未修。
2. 若共展 / 豆芽 / 金凤当姓名在 `pre_judge` 不是 not_fulfilled，本 issue 未修。
3. 若杨杰的 reconcile 仍保留 LLM 残留的 blocking NF，本 issue 未修。
4. 若实现里出现「假名列表」或点名共展/豆芽，本 issue 退化成规则表。

## 请对手挑战

- 044「从不过失败」是不是也被本轮推翻了？若你认为 judge 说 NF 就是「主动改失败」，请指出它比 Q1 多声称了什么。
- 整份合同替换是不是权责越界（aihacking：返回值越界）？
- overlay 对 Q1 失败 inherit、judge 对 Q1 失败 NF，这个分界是不是事后圆场？

不要把覆盖门或残句代数扶回来。不要新开授权字段。
