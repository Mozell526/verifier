# Investigate Judge Review Trace

## Commands and observations

1. Targeted suite:

```text
python -m pytest -q tests/test_investigation_role_contracts.py \
  tests/test_judge_authority_analysis.py tests/test_solidify_receipt.py \
  tests/test_draft_role_review.py tests/test_authority_enforcement.py
80 passed
```

2. Official investigation entry point:

```text
python .agents/skills/draft/scripts/validate_investigation.py \
  --project client_search --role judge
ok: true
source_revision_drifted: false
```

3. Adversarial validator probes:

```text
spec-illegal-anchor-type => ACCEPTED
empty-dimension-ids => ACCEPTED
empty-analysis-id => ACCEPTED
dynamic-verification-without-tool => ACCEPTED
unresolved-with-database-type => ACCEPTED
resolved-with-unresolved-question => ACCEPTED
priority-hack-because => ACCEPTED
```

4. Capability-manifest boundary probe:

```text
polNoInfo.plancodeinfo.abbrname expected=25 got=8 missing=17
missing enum file: fields=80, nonempty enums=2
```

5. Full suite:

```text
600 passed, 21 failed
```

Twenty failures require the local API server on `127.0.0.1:8023` and are environment-blocked. One additional config-contract failure reported a public environment bypass in the changed authority implementation; it is secondary to the five scoped findings above.

