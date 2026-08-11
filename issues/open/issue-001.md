# Issue #001: Authority validator accepts contracts forbidden by the spec

**Class**: functionality
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output + code-analysis

## Verifier Discovery

The official validator reports the current package as `ok: true`, but direct contract probes show that all of the following are accepted:

- empty `analysis_id`;
- empty `dimension_ids`;
- `anchor_type=system_semantic_definition`, which is absent from the spec enum;
- dynamic `verification_method` with empty `tool_requirement_ids`;
- `status=unresolved` with `anchor_type=database_reality`;
- `status=resolved` with a non-empty `unresolved_question`;
- priority-only reasoning disguised by adding “因为”.

Reproduction:

```bash
python - <<'PY'
import copy, json
from pathlib import Path
from impl.core.schema.investigation_judge import JudgeInvestigationContract, validate_judge_contract
p = Path("impl/projects/client_search/draft/investigation/judge/docs/judge-investigation-contract.json")
base = json.loads(p.read_text())
cases = {
    "empty-dimension-ids": lambda d: d["authority_analyses"][0].__setitem__("dimension_ids", []),
    "empty-analysis-id": lambda d: d["authority_analyses"][0].__setitem__("analysis_id", "  "),
    "dynamic-without-tool": lambda d: d["authority_analyses"][0].__setitem__("tool_requirement_ids", []),
    "priority-hack": lambda d: d["authority_analyses"][0]["anchor"].__setitem__(
        "causal_reasoning", "A 优先级高于 B，因为 A 赢。"
    ),
}
for name, mutate in cases.items():
    raw = copy.deepcopy(base)
    mutate(raw)
    validate_judge_contract(JudgeInvestigationContract.from_dict(raw))
    print(name, "ACCEPTED")
PY
```

All four cases print `ACCEPTED`. The other three variants were also executed and accepted.

Root cause is in `impl/core/schema/investigation_judge.py`: validation checks referenced dimension members but not a non-empty dimension list, adds a non-spec anchor type, does not enforce status/type consistency, does not classify dynamic verification requirements, and implements priority-only rejection as a permissive keyword regex.

Owning layer: schema validation.

