# Investigate Judge Authority Standardization Review

## Scope

Reviewed the Judge investigation contract, AuthorityAnalysis validator,
client_search investigation package, Solidify evidence, runtime authority
enforcement, comparator reconciliation, and related tests.

## Findings And Resolution

- [x] Replace hand-authored `succeeded` Solidify evidence with an executable
  probe. `judge_solidify_probe.py` now loads the selected investigation,
  verifies every authority projection and writes the registered smoke artifact.
- [x] Remove unsupported authority certainty. The evaluation-boundary anchor is
  unresolved until the user-authored boundary source or business confirmation
  is available; the AI-authored integration document and its consumer are not
  treated as independent authority chains.
- [x] Align protocol examples with the strict loader. Every complete
  AuthorityAnalysis JSON example now declares `verification_mode` consistently
  with its ToolRequirement dependencies.
- [x] Preserve atomic Judge assessments. The deterministic client-search
  comparator now upserts only its own assessment instead of replacing the full
  assessment list.
- [x] Avoid blanket unresolved enforcement. The aggregate comparator
  expectation keeps product and dimension bindings but does not claim an
  authority dependency that the case has not established.
- [x] Prove case-time authority consumption. The executable Solidify probe now
  invokes the production authority enforcement path for every anchor and
  verifies three cases: a bound matching dimension becomes `not_evaluable`, a
  mismatched dimension is unchanged, and an unbound expectation is unchanged.
- [x] Exercise the candidate reconciliation path. An offline test instantiates
  `ClientSearchJudge` and verifies that `reconcile_result` consumes a bound
  unresolved authority, clears score/confidence, and records its citation.
- [x] Keep the protocol dataclass example executable by importing `Literal`.

## Anti-Hacking Checks

- No fallback converts missing authority evidence to `fulfilled`.
- Internal configuration remains current-system evidence, not external truth.
- Runtime authority enforcement requires explicit authority and dimension
  bindings.
- Solidify success is generated from executable checks rather than a manually
  asserted status.
- Solidify evidence distinguishes applicability from global fallback: only an
  explicitly bound authority with an intersecting dimension changes a result.
- Comparator reconciliation no longer erases evidence gaps reported by atomic
  assessments.

## Verification

- Run the Judge Solidify probe and require `status=succeeded`.
- Validate the client_search Judge investigation package and confirm source
  revision drift is false.
- Rebuild the Judge Solidify receipt and require all eight contract sources and
  five mappings/observables.
- Run the focused authority, investigation, comparator, schema and config tests.
- Run the repository test suite excluding API fixtures that require the local
  service on port 8023.

Latest result: 26 focused tests passed; the offline repository suite passed
with 561 tests and one dependency deprecation warning.

## Remaining Business Blockers

All four client_search authority questions remain unresolved until external
evidence becomes available. This is a correct conservative state, not a
promotion result. Online Current/Draft accuracy and promotion still require the
business API/LLM environment and an independent outcome oracle.
