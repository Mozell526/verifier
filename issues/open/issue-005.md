# Issue #005: Promotion readiness is asserted without proving judgment accuracy improved

**Class**: effectiveness
**Severity**: medium
**Status**: verifier-raised
**Evidence**: run-report-analysis

## Verifier Discovery

The active Judge loop is marked `ready_for_promotion_checks` and the role review records `decision=improved`. Its comparison evidence states:

- all 13 Current and Draft overall statuses are identical;
- the main authority delta is four citations added to every case;
- no unresolved case was executed;
- unresolved behavior is supported only by a unit test;
- all three “authority-critical” examples receive all four anchors rather than proving case-specific applicability.

The Draft does produce a more atomic assessment shape, but the receipt does not compare those new per-expectation judgments to an independent oracle. Structural granularity and extra citations do not by themselves prove improved judgment accuracy, which is the acceptance condition.

Root cause: the promotion review schema verifies that evidence strings and criteria exist, but the reviewer can self-certify “improved” without an outcome-level accuracy delta or an adversarial unresolved/authority-conflict case.

Owning layer: Draft Loop review and promotion evidence.

