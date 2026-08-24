# Issue #004: Client-search authority migration uses internal materials as external authority

**Class**: effectiveness
**Severity**: high
**Status**: verifier-raised
**Evidence**: artifact-analysis

## Verifier Discovery

The contract introduces `system_semantic_definition` as an anchor type and uses it for `enum-value-authority` and `semantic-mapping-authority`, although the spec's authority types are external/business anchors and explicitly warns that project configuration may itself be wrong.

The enum analysis also combines two different questions in one resolved anchor:

- what the current parser accepts (supported by code/config);
- what values exist in the customer database (explicitly not verified).

The description admits the database question is unresolved, but the overall anchor remains `resolved`. This avoids the required unresolved path by broadening the anchor type beyond the spec.

The evaluation-boundary causal chain is not independently evidenced. Manifest refs `judge-boundary-template` and `judge-boundary-protocols` both point to the same `judge_boundary_protocals.md`; the template ref summary itself says the independent template is still pending. The contract nevertheless describes one source as a direct user-authored standard and the other as its AI implementation.

The old `authority-registry.json` is also still registered as an `EvidenceRef` with “5 tiers” and “conflict rules”, and the active role review says runtime knowledge comes from “investigation contract + authority registry”. This is inconsistent with the requirement that runtime no longer use the tier registry as truth.

Root cause: the migration preserved internally convenient sources by relabeling them as authority/evidence instead of splitting proven system behavior from unresolved external truth.

Owning layer: investigation artifacts and semantic hand-off.

