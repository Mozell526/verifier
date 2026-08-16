# Discovery — sufficiency host landing

用户要的是构建 judge，不是再写对照脚本。

## 源头

- 提示互搏：draft judge 原「裸词规则」四句
- 原则：`issues/trace/name-sufficiency.md`（042–045）
- 实现：`impl/projects/client_search/draft/field_sufficiency.py`
- 挂点：`ClientSearchJudge.pre_judge` + `reconcile_result` 最后一句话

## 实验

```bash
/Users/xiaozijian/miniconda3/envs/agno/bin/python -m pytest tests/test_client_search_field_sufficiency.py tests/test_client_search_context_governance.py::test_draft_judge_system_has_intent_decomposition_and_evidence_grading -q
/Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_field_sufficiency_host.py
```

负对照仍是 field_only。覆盖门 / 残句 / 虚词表只许当对照，不许进 host。
