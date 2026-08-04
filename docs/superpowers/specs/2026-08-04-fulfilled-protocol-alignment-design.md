# Fulfillment Protocol Alignment Design

## Goal

Align the shared Judge path and the `client_search` draft Judge with
`spec/alg/fulfilled.md` without introducing a second fulfillment vocabulary or
making fulfillment aggregation depend directly on investigation findings.

The repair must close these business escape paths:

1. no blocking expectation is treated as overall `fulfilled`;
2. an honest refusal is treated as successful delivery of a result request;
3. a known missing delivery is downgraded to `not_evaluable`;
4. a capability or responsibility assumption is used for a decisive result
   without the Authority check required by the protocol;
5. project guidance continues to emit the legacy `uncertain` status.

## Business invariants

The implementation follows these invariants from `fulfilled.md`:

- `BusinessExpectation.blocking` identifies a must-deliver part of the user's
  core goal. It is not an assessment status.
- `FulfillmentAssessment.status` remains exactly one of `fulfilled`,
  `not_fulfilled`, and `not_evaluable`.
- A blocking assessment can have any of the three statuses. Authority affects
  the assessment it governs, not overall aggregation directly.
- Overall aggregation is deterministic: a blocking `not_fulfilled` wins; then
  a blocking `not_evaluable`; only all blocking expectations fulfilled can
  produce overall `fulfilled`.
- If no blocking expectation exists, the evaluation contract has not proved
  that the user's core goal was assessed. Overall status therefore cannot be
  `fulfilled`; it is `not_evaluable`. Individual assessments are left intact.
- A non-blocking gap remains visible but does not overturn a successfully
  assessed core goal.
- For a result request, transparent refusal can satisfy a separate boundary-
  handling expectation, but cannot satisfy the core delivery expectation.
- A confirmed in-scope missing delivery is `not_fulfilled`. Only the four
  protocol causes, plus explicit Authority tool unavailability, can justify
  `not_evaluable`.

## Approaches considered

### A. Change only the shared aggregation return value

Change `if not blocking_ids` from `fulfilled` to `not_evaluable` and update one
test. This closes the most visible bug but leaves the duplicated draft behavior,
legacy vocabulary, and project-specific escape paths unguarded.

### B. Protocol-aligned narrow repair (selected)

Make the shared and draft aggregation behavior identical, add regression tests
for the business invariants, fail closed when a `not_evaluable` assessment has
no explicit cause, preserve the existing Authority-to-assessment boundary, and
update only active client-search Judge guidance that still uses `uncertain`.
This closes the protocol gaps without redesigning Judge schemas.

### C. Redesign expectation and assessment schemas

Introduce new contract-validity fields or a fourth overall status. This is out
of scope and conflicts with the protocol's explicit three-state vocabulary.

## Design

### 1. Shared overall aggregation

`impl/core/judge.py` remains the canonical public finalizer. Its aggregation
will return `not_evaluable` when expectations or assessments are absent, when
there are no blocking expectations, or when any blocking expectation lacks a
fulfilled assessment and no blocking failure is present.

The function will not mutate expectation blocking flags or individual
assessment statuses. `overall_fulfillment.blocking_expectations` continues to
record the exact IDs used by aggregation.

### 2. Draft parity

The isolated draft execution module currently duplicates the aggregation
algorithm. It will receive the same no-blocking behavior and matching tests so
draft evaluation cannot disagree with the shared public path.

This change does not consolidate the modules in this pass because the draft is
intentionally isolated for candidate comparison. Parity is enforced through
parameterized tests over both finalizers.

### 3. `not_evaluable` cause validation

The Authority gate already distinguishes explicit causes in assessment
evidence. An empty evidence payload currently bypasses its documented
fail-closed behavior. Empty or untagged `not_evaluable` assessments will be
marked with an auditable `needs_human_review` evidence entry. Explicit
`结论类型：输入坏` and `结论类型：完全无关` remain exempt from Authority.
Explicit `职责外` and `依据不充分` continue to require an Authority audit
reference.

This gate does not change overall aggregation itself; it only prevents an
unexplained `not_evaluable` assessment from silently passing review.

### 4. Result delivery and refusal boundary

The client-search prompt and deterministic reconciliation will preserve two
separate concepts:

- the blocking core delivery expectation (find the requested target customers);
- an optional/non-core boundary-handling expectation (be transparent and avoid
  fabricated conditions).

Transparent handling may fulfill the latter only. The former is
`not_fulfilled` when Authority confirms the capability is in scope and delivery
is missing; it is `not_evaluable` only for an applicable protocol cause with the
required evidence and Authority audit.

No hard-coded case IDs, phrases, fields, or expected outputs will be added.

### 5. Decisive capability checks

The operator capability check must not infer product responsibility from the
current capability manifest alone. A directly closed executable-semantic fact
may still be compared deterministically. If the decisive conclusion depends on
whether an operator/capability should be supported, the governed assessment
must consume an Authority resolution; unresolved becomes `not_evaluable`.

The repair will use structured conflict/capability evidence already present in
the Judge context and audit trail. It will not consume `AuthorityFinding`
directly and will not synthesize resolved findings.

### 6. Vocabulary

Active client-search Judge instructions will replace legacy `uncertain` wording
with `not_evaluable`. Historical probe outputs and attribution compatibility
labels are not rewritten unless they are active Judge inputs; changing frozen
historical artifacts would corrupt evidence provenance.

## Data flow

1. Judge derives business expectations and marks the user's must-deliver core
   expectations as blocking.
2. Judge assesses each expectation using current trace evidence and, only when
   required, an Authority resolution.
3. Authority gate validates audit references and fail-closes unexplained
   `not_evaluable` assessments.
4. Project reconciliation performs only protocol-safe deterministic checks.
5. The public finalizer aggregates blocking assessment statuses into one of the
   three overall statuses.
6. Summary generation reports the resulting core status and any non-blocking
   gaps without inventing a second verdict.

## Error handling

- Missing expectations, assessments, blocking expectations, or blocking
  assessments produce overall `not_evaluable`, never vacuous success.
- A blocking `not_fulfilled` remains decisive even if another independent
  blocking assessment is `not_evaluable`.
- Missing or invalid Authority references force the governed assessment to
  `not_evaluable` and attach a human-review marker.
- Authority execution failure is reported as Authority capability unavailable,
  not as a fabricated business conflict.
- Existing unrelated user changes in the dirty worktree are preserved.

## Tests and acceptance

Add or update tests covering:

- no blocking expectations cannot yield overall `fulfilled`, for both shared
  and draft finalizers;
- a non-blocking failure does not overturn a fulfilled blocking core goal;
- missing blocking assessment yields `not_evaluable`;
- blocking failure wins over an independent blocking `not_evaluable`;
- empty or untagged `not_evaluable` fails closed with human review;
- input-bad and unrelated explicit causes do not require Authority;
- honest refusal cannot fulfill the blocking result-delivery expectation;
- decisive operator handling does not bypass a governed unresolved Authority
  question;
- active Judge guidance contains no legacy `uncertain` status.

Run focused Judge and Authority tests first, then the broader relevant suite.
Run the frozen client-search comparison only if its required runtime and frozen
inputs are available; it is evidence for promotion, not a substitute for the
deterministic protocol tests.

Acceptance requires all focused tests to pass and no new case-specific rules,
fallback success paths, schema vocabulary, or direct Finding-to-fulfillment
dependency.
