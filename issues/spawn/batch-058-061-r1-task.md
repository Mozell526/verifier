Read each issue file below in full. Inspect the cited protocol files and current exits yourself. Append one Architect Response to each file. Never overwrite prior content.

Issue files (respond to all four, separately):
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-058.md
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-059.md
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-060.md
- /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/open/issue-061.md

Do **not** review or append to issue-006 through issue-057. Those belong to other charters and already have their own status. You may cite Consensus blocks only from 040, 041, 046, 047, 048.

Do **not** mix this with issue-053 through issue-057. Their 「第二问」 is a different object: whether the whole sentence was finished by one dimension.

## Your Role
You are architect acting as an argue peer. Follow the argue protocol in ~/.codex/skills/council/PROTOCOLS.md.

Every response MUST use the field name **Verdict** (not Judgment) and pick exactly one of:
real-problem | reasonable-design | needs-more-info | not-actionable | escalate-to-project

Every response MUST include `### Spawn Evidence` with the spawn-id from this spawn.

## Context
Charter: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/charter-q2-placement.md
Discovery: /Users/xiaozijian/WorkSpace/projects/claude_code/verifier-runB/verifier/issues/trace/q2-placement-discovery.md
Oracle: spec/alg/fulfilled.md, spec/alg/product-function.md, spec/alg/authority.md §8.3, spec/info-volume.md, spec/alg/material-positioning.md
Current exits to read yourself:
- impl/core/schema/judge.py
- impl/core/authority_gate.py
- impl/core/frontend_view.py `_fulfillment_panel`
- impl/core/table_view.py status / fulfillment_status
- impl/frontend/summary.html case-list「状态」and `renderFulfillmentMatrix`
Prior locks (Consensus blocks only): issues/open/issue-040.md, issue-041.md, issue-046.md, issue-047.md, issue-048.md

## What this run is
The two-question structure is already locked. The user asked a placement / implementation question:

1. How is Q2 actually computed?
2. Where does it live?
3. The frontend currently only shows fulfilled. Where would a person see Q2?

This is a protocol-and-exit debate. Do not re-judge cases. Do not implement fields. Do not change the frontend. Do not adopt a final Chinese public sentence. Do not announce 立住了 / 没立住 as the public wording.

## Permission Mode
review: append response only. Do not modify spec/**, impl/**, xlsx, canvas, or frontend.

## How to write
Do not use nested heredocs. Write each response to a temp file first, then append that file to the issue. Every response must include `### Spawn Evidence` with the spawn-id.

## Investigate before judging
Quote the protocol sections and current exits yourself. Do not treat the verifier write-up as already true.

Challenge specifically:

- 058 claims Q2 is a read of already-cut authority prefixes + source materials, not a new Judge fill. Attack: is the prefix map itself a new classifier? If this-run has no authority call, saying 说不清 empties Q2 on ordinary successes — is that honest, or is it no exit? If "already-cut" may look past this run, how is that not the forbidden catalog / is_supported table?

- 059 claims grain stays on the same expectation row. Attack: users only see the case-list「状态」chip. If Q2 can never live there, is the sibling invisible by construction? Why may overall fulfillment aggregate, but overall Q2 may not? If one expectation mixes an established search with a missing year, does refusing to split hide two product facts?

- 060 claims four layers, and the only later hang-point is a sibling cell of Status on the expectation matrix. Attack: the matrix is behind a case drill-in; the user asked how a person sees this. Is that answering the wrong surface? Is "projection now, persist later" the forbidden temporary design? Should product-function.md §3's 认种类 be explicitly barred as an implementation spec?

- 061 claims this run must not change exits, and visibility stays with the user. Attack: the user asked how to implement and where people see it. If nothing is shown, did the run fail to answer? Should 061 be escalate-to-project rather than another protocol argument?

If verifier smuggled a frontend column, a new schema field, or a public Chinese name into the conclusion, reject that part. Placement may be locked without implementing.

Do not rubber-stamp all four with the same paragraph. Pick exactly one Verdict per issue from the protocol vocabulary.
