# Investigate Judge Authority Closure Design

## Objective

Complete one evidence-driven Judge path from project investigation through
Solidify and case-time judgment. The implementation must satisfy
`spec/alg/investigate-judge.md` and
`spec/alg/investigate-judge-authority.md` without treating internal project
configuration as external business authority.

The first complete project is `client_search`. Shared code must remain
project-independent so another project can adopt the same contract without
field-name or case-specific branches.

## Scope

This change includes:

- strict `JudgeInvestigationContract` and `AuthorityAnalysis` validation;
- a registered `client_search` Judge investigation package;
- minimal, dimension-scoped Solidify authority projections;
- case-time authority consumption with explicit applicability;
- focused structural, adversarial, integration, and Current/Draft tests;
- promotion evidence only when an independent expected outcome proves an
  accuracy improvement without regression.

This change does not redesign the public `JudgeResult` or
`FulfillmentAssessment` schemas, create a second investigation manifest, or
perform open-ended authority research at case time.

## Authority Boundary

Authority answers what is correct for the business. Internal source code,
configuration, prompts, historical references, and existing Judge behavior can
prove current system behavior, but cannot by themselves prove external truth.

Each judgment point is classified into one of these outcomes:

- `resolved`: independently supported by evidence and, where necessary, a
  declared executable fact check;
- `unresolved`: the available causal chain and evidence cannot establish the
  external truth, with one concrete clarification question recorded.

The validator enforces deterministic contract rules. Semantic review assesses
whether evidence really supports the conclusion. Keyword matching is not used
as a substitute for causal review.

## Architecture

### Investigation contract

`JudgeInvestigationContract` remains the only Judge-specific contract beneath
the public `InvestigationManifest`. It contains product-level business
expectations, the Live boundary, evaluation dimensions, and authority analyses.

Validation rejects:

- blank or duplicate analysis IDs;
- empty or unknown dimension references;
- fewer than two source claims;
- incomplete causal chains;
- anchor types outside the specification;
- inconsistent resolved/unresolved fields;
- resolved conclusions without evidence;
- dynamic verification without a declared ToolRequirement;
- unknown EvidenceRef or ToolRequirement references.

Dynamic verification is declared structurally instead of inferred from prose.
The authority contract will carry an explicit verification mode or equivalent
typed signal, with backward compatibility handled at the loader boundary only
when the meaning is unambiguous.

### Client Search investigation

The package lives at:

```text
impl/projects/client_search/draft/investigation/judge/
  manifest.json
  overview.md
  docs/judge-investigation-contract.json
  evidence/
```

It defines the complete-product user outcome, the parser Live boundary, and
separate dimensions for intent preservation and downstream consumability.

The initial authority analyses cover:

- legal enum-value space;
- evaluation boundary;
- spoken-language semantic mapping;
- query-form equivalence.

Evidence is classified by what it can actually prove. Database reality remains
unresolved when no database observation is available. A code path may resolve
how the current parser normalizes a phrase, but not whether that behavior is the
business-approved meaning.

The package is registered as a Judge investigation asset in `project.yaml` and
must pass the official validation entry point with all implemented tools
executed before Solidify.

### Solidify projection

Solidify derives two runtime inputs:

- the stable business contract: expectations, Live boundary, and dimensions;
- minimal authority anchors scoped by `dimension_ids`.

Each `authority:<analysis_id>` owns exactly one mapping and at least one
observable. Runtime projections include only identity, dimension scope, status,
conclusion, verification declaration, tool availability, and conservative
directive. They exclude source claims, causal chains, evidence reference IDs,
and causal reasoning.

The legacy `authority-registry.json` is not a runtime truth source. It may remain
as explicitly historical investigation material until regression evidence is
complete.

### Case-time judgment

Every generated case expectation retains an auditable binding to its product
expectation and evaluation dimension. Authority enforcement uses that binding,
not project-specific expectation IDs or field names.

An anchor applies only when:

1. its dimension includes the case expectation's dimension;
2. the current judgment needs that authority question;
3. any required case-time fact check has produced valid evidence.

An unresolved anchor changes only dependent assessments to `not_evaluable`.
It cannot suppress findings in unrelated dimensions. A resolved anchor with an
unavailable dynamic tool permits stable project-level conclusions but forbids
assuming that an unchecked case-level fact is true.

## Failure Handling

All lifecycle gates fail closed:

- missing or invalid Judge investigation package blocks Solidify;
- stale or unexecuted validation receipts block candidate use;
- missing Solidify mappings or observables block Draft review;
- missing authority evidence yields `not_evaluable` only for dependent
  assessments;
- malformed runtime projections are rejected rather than silently ignored.

No fallback converts missing evidence into `fulfilled`, weakens an existing
standard, or manufactures a custom truth source to make tests pass.

## Testing

The focused suite covers:

- dataclass and JSON round trips;
- every structural rejection rule with adversarial mutations;
- EvidenceRef and ToolRequirement cross-reference validation;
- no investigation-only field leakage into runtime context;
- one mapping and observable per authority analysis;
- dimension isolation for resolved and unresolved anchors;
- unavailable dynamic tools and successful fact-check paths;
- official CLI validation and Solidify entry points;
- `client_search` representative resolved, unresolved, and conflict cases.

Current and Draft run on frozen cases. Promotion evidence must compare atomic
judgments with independent expected outcomes. Identical overall statuses,
additional citations, or self-reported review improvement are insufficient.

## Acceptance Criteria

The work is complete when:

- the `client_search` Judge package passes the official validator;
- all four project authority judgment points are represented honestly;
- strict adversarial validator tests pass;
- each authority analysis is independently mapped and observed by Solidify;
- runtime applies authority only to relevant dimensions and cases;
- investigation details do not leak into runtime prompts or public schemas;
- the legacy tier registry is not read as runtime truth;
- focused and relevant regression tests pass;
- Promotion is recommended only if independent Current/Draft evidence proves
  improved judgment accuracy with no visible regression.

