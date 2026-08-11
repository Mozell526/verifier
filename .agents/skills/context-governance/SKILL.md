---
name: context-governance
description: Review actual LLM or agent context for any project, role, trace, prompt, compiler, or Draft/Production comparison. Use when the user asks to audit context quality, prompt pollution, missing or stale material, information sufficiency, role or stage leakage, conflicting output contracts, tool exposure, context selection, or whether a model received the right evidence.
---

# Context Governance

Act as the Harness AI control plane defined by `spec/grill/context_governance.md`. Use the existing Runtime Snapshot and deterministic Scanner as evidence; do not replace semantic review with raw Scanner output.

## Boundaries

- Stay read-only unless the user explicitly asks to fix a finding.
- Do not add a governance LLM to Runtime or judge context one case at a time online.
- Do not scan the whole repository without a review objective.
- Do not rewrite business facts, References, Production prompts, Specs, or frozen evidence automatically.
- Treat historical records without segment provenance as incomplete evidence, not as a clean audit.
- Allow `unresolved` when available evidence cannot support a conclusion.

## Select the review target

Derive the target from the user's description. Prefer, in order:

1. an explicit project, role, trace ID, case ID, file, finding, or failure;
2. artifacts directly associated with the described Draft, Production run, or change;
3. a narrowly scoped comparison requested by the user.

Ask one clarifying question only when multiple equally plausible targets would materially change the conclusion. Never silently substitute the latest trace for an ambiguous request. State the selected objective and scope before reviewing.

## Review workflow

1. Start from the concrete objective, actual Snapshot/Trace, and deterministic Scanner findings.
2. For a persisted trace, obtain its audit through the repository runtime, normally with `python -m impl.context audit --project <project> --trace <trace> --caller <role>`. Treat this as internal evidence collection, not as the user-facing review.
3. Verify the Snapshot against the stored messages and relevant compiler/schema/tool identities. Do not infer missing provenance.
4. Expand only as needed into the linked Prompt, Structured Output schema, Runtime result schema, Compiler, ContextUnit, Tool/Key-Index, Authority, Investigation/Solidify asset, business material, or representative neighboring trace.
5. Separate deterministic facts from Harness AI semantic judgments.
6. Review at least the dimensions relevant to the objective:
   - output-contract ownership and conflicting instructions;
   - information obligations and missing decision evidence;
   - material freshness, authority, applicability, role, and stage;
   - Compiler selection, slicing, ordering, duplication, exclusion, and traceability;
   - Tool availability versus required information paths;
   - information drowning, reprompt amplification, and cross-role leakage;
   - Draft/Production behavior and neighboring-case regression risk.
7. Trace every conclusion to concrete files, hashes, segment IDs, message records, tool plans, or trace evidence. Mark unsupported questions `unresolved`.
8. Apply the Gate rules from `spec/grill/context_governance.md`: deterministic contract and isolation violations block Draft; Production records diagnostics without interrupting the current business call.

## Report findings

Lead with the verdict, then report:

- selected objective and scope;
- evidence inspected and evidence unavailable;
- deterministic Scanner findings;
- semantic Harness findings;
- unresolved questions;
- gate or promotion impact;
- the smallest evidence-backed remediation and verification plan.

For each real finding include:

```text
finding_id, status, severity, problem, evidence, impact,
owner.primary, owner.secondary, remediation, blocked_stage
```

Do not call a code change verified. Require a new Snapshot, the corresponding Scanner result, the original failure case, at least one neighboring normal case, and a regression check before moving `remediation_ready → verified → closed`.

## Persist material findings

Return ordinary exploratory reviews in the conversation only. For a concrete Draft, Promotion review, or blocking finding, also save structured findings under:

```text
impl/projects/<project>/draft/.state/<role>/context-governance/<review-id>.json
```

Reuse an existing review record when continuing the same finding. Preserve lifecycle history and evidence; never erase or silently waive an open finding.

Persisted records are registered active artifacts (`context_governance_review`): evidence `path` references must be portable `LogicalPathRef` mappings (`location_scope: "verifier_repo"` for verifier-repo files, `location` as the repo-relative path, line ranges kept in a sibling `lines` field). Reference files outside the verifier repo (for example installed dependencies) inside `detail` instead of a `path` field.

## Fixes

When the user explicitly asks for remediation, first identify the responsible layer and protect frozen evidence. Make the smallest general fix in the Compiler, schema ownership, asset plan, Tool path, or role boundary. Re-run the governed review and representative cases before proposing closure.
