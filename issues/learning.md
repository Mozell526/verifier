# Learning Context

## Accepted Patterns

- Judge contract is registered through the existing `InvestigationManifest.artifact_refs`; no second top-level manifest was introduced.
- Runtime projection excludes `source_claims`, `causal_chain`, `evidence_ref_ids`, and `causal_reasoning`.
- Each `authority:<analysis_id>` has its own Solidify mapping and observable.

## Confirmed Problem Patterns

- Structural tests cover declared happy paths but omit adversarial schema cases, allowing invalid authority contracts through the official validator.
- Runtime authority enforcement preserves dimension IDs in context but does not use them when mutating assessments.
- Capability aggregation assumes the first intent owns all field metadata, losing later `enum_ref` values for repeated fields.
- Migration evidence sometimes renames an implementation document as a user-authored template, weakening causal provenance.

