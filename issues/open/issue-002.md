# Issue #002: Runtime authority enforcement ignores dimension and case applicability

**Class**: functionality
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output + code-analysis

## Verifier Discovery

`project_authority_runtime_context()` retains `dimension_ids`, but `_enforce_authority_directives()` never reads them. For every unresolved anchor it rewrites every fulfilled/not_fulfilled assessment except one hard-coded field-protocol expectation to `not_evaluable`. Resolved anchors are likewise cited on every case without checking whether the case judgment actually needs that authority question.

The existing test `TestUnresolvedAnchorForcesNotEvaluable` explicitly expects this blanket behavior: an unresolved `intent-completeness` anchor rewrites two arbitrary assessments. The active 13-case review confirms the same fan-out for resolved anchors: every case receives all four authority citations (52 citations total), including cases unrelated to enum legality or query-form equivalence.

This violates the required mapping from an AuthorityAnalysis to its bound evaluation dimension and the “minimum current judgment content” rule. It also creates a failure mode where an unresolved fact in one dimension suppresses valid findings in another.

Root cause: the runtime `FulfillmentAssessment` has no preserved product-dimension binding, and enforcement substitutes a global post-processing loop plus a hard-coded exception for that missing mapping.

Owning layer: Judge runtime/Solidify projection.

