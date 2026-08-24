# Investigation Evidence Staleness Policy

## Status

Design approved for implementation planning. This document restores the
per-lifecycle behavior used by the current `verifier-branch` implementation.

## Problem

An `EvidenceRef` points at a live business-source file and records the content
hash observed during investigation. The business source can legitimately gain
unrelated examples or rules after the investigation package is created. Treating
every content-hash change as a hard failure prevents Draft candidate experiments
even when the investigation package, candidate code, and runtime contracts are
unchanged.

The opposite failure mode is unsafe: silently accepting missing files, path
escapes, changed manifests, changed Tools, or changed candidate assets would
make the experiment unauditable. Staleness therefore needs an explicit
lifecycle policy, not a global hash bypass.

## Goals and non-goals

Goals:

- Keep strict checks when a command is asserting that an investigation or
  promotion asset is current.
- Allow an existing Draft candidate to run against the current business source
  while recording evidence drift.
- Make drift visible in iteration reports and runtime audit data.
- Preserve all structural, permission, manifest, Tool, contract, and candidate
  integrity gates in every policy.
- Keep the policy Core-generic; no project-specific exceptions or aliases.

Non-goals:

- Automatically deciding whether a business-source edit is semantically
  relevant.
- Updating EvidenceRef hashes or investigation conclusions automatically.
- Starting investigation, Solidify, or promotion as a side effect of runtime.
- Weakening checks for files, paths, manifests, Tools, candidate code, or asset
  mappings.

## Policy

The investigation package validator accepts an explicit business-source
staleness policy:

| Policy | Business-source revision/content drift | Structural and integrity failures |
| --- | --- | --- |
| `strict` | fail | fail |
| `warn` | collect warnings and continue | fail |

`strict` is the default. `warn` applies only to business-source revision and
EvidenceRef content-hash drift. It never applies to a missing source, a source
outside the configured repository, a missing EvidenceRef target, malformed
Manifest/artifacts, changed Tool bytes or Tool set, changed contracts, changed
candidate code, or changed role-asset mappings.

Lifecycle callers use the policy as follows:

- Explicit investigation validation: `strict`.
- Creating or re-running Solidify: `strict`.
- Promotion checks: `strict`.
- Existing Draft Loop candidate runtime and its receipt re-check: `warn`.
- Production/current runtime: `strict`.

This means an existing candidate can be experimentally evaluated on newer
business material, but a new validation receipt, new Solidify claim, or
promotion cannot be issued until the drift is explicitly resolved.

## Data flow and audit

The validator returns structured staleness warnings, each containing the
EvidenceRef identifier and expected/current hash when applicable, plus the
frozen/current source revisions. The candidate-side validation path carries
these warnings through the runtime preflight into the iteration report.

Each affected side records:

- the applied staleness policy;
- business-source revision drift, if any;
- EvidenceRef content drift entries;
- the normal Authority/runtime snapshot and tool audit.

Warnings are informational runtime facts. They do not become Authority basis
evidence, do not change Judge status, and do not count as Draft improvement.

## Error handling

Under either policy, validation fails closed for structural or security errors:

1. Resolve and verify the configured source root.
2. Resolve each EvidenceRef without path expansion or fallback guessing.
3. Validate Manifest, artifacts, contracts, Tools, and role assets.
4. Apply the selected policy only to source revision/content drift.

Candidate runtime may continue only after steps 1–3 succeed. A warning must not
be converted into `not_evaluable`, `tool_failure`, or a successful business
resolution.

## Verification plan

Add or update tests for:

1. strict policy rejects source revision drift and content-hash drift;
2. warn policy returns structured warnings for both drift types;
3. warn policy still rejects missing files, path escapes, malformed manifests,
   changed Tool bytes, and changed candidate/contract assets;
4. candidate Draft Loop continues with drift and persists policy/warnings in
   the run report;
5. explicit validation, Solidify, promotion, and production callers remain
   strict;
6. existing no-drift behavior remains unchanged.

The implementation should mirror the generic policy plumbing in
`verifier-branch`; it must not add a `client_search`-specific bypass.
