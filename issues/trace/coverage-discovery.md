# Discovery — coverage-gate vs name-type machine

Script: `issues/trace/simulate_1a_coverage_program.py`
Dump: `issues/trace/simulate_1a_coverage_program.json`
SHA-256: `f180cb60bcbde3a978bbaa64e28971988676d4ea97194fd990d4be05bd72e835`

Does not overwrite `simulate_1a_mixed_program.py`. Frozen traces reused. No LLM rerun.

## Columns

| col | status | mixed agree/47 | set A F/NF | set A flips |
|---|---|---|---|---|
| current | baseline | 36 | 213/128 | — |
| wide | negative | 27 | 238/103 | lift 25 including 共展/豆芽/昊轩 |
| surname | negative | 35 | 210/131 | lift 王坤林+家办客户; drop 5 保单号 |
| role | rejected machine | 41 | 215/126 | lift 王坤林+红莲保单 |
| live_identity | candidate | 41 | 214/127 | lift **only** 王坤林 |

## Candidate

`exit_live_identity`: overlay only when live has exactly one field and that value equals the whole query.

- `searchClientName` + 2–4 汉字 + surname catalog → F
- `clientNo` / `polNo` exact → F (same gate, not a name regex)
- else inherit

Does not read mixed-pack `role`. Does not parse 保单号/的/买了.

## Why 41/47 is not the win

Both role and live_identity miss only HB009–HB014. Those six have no live name. 019 already nailed this as parser. Overlay cannot honestly mark them F.

Role's extra machinery (`PERSON_THEN_POLICY`, 业务词, 场景分流) does not buy any mixed-pack agree beyond flipping the same bare names. It does buy a set A leak: I248 `红莲保单` (value=`红莲` ≠ query) lifted F because the query *looks like* a 4-char name.

## Overlay vs inherit (mixed)

- role: 17 overlay / 31 inherit
- live_identity: 15 overlay / 33 inherit (12 bare names + HB015–HB017 exact IDs)

共展/豆芽/昊轩/盘客/金凤/姓名+产品/姓名+保单号: live_identity inherit.

## Set A live_identity overlays (57)

- 53 exact IDs already F
- 3 exact names already F (杨杰/郑鑫/匡西永)
- 1 lift: 王坤林 (1A required)

## Architect tightening (025)

I248 leak is real, but the live branch is `PERSON_THEN_POLICY` (`保单号?` makes 号 optional), not the 4-char `BARE_NAME` arm. I248 is outside the mixed pack, so 41/47 cannot see it.

SHA after architect rerun is unchanged: `f180cb60bcbde3a978bbaa64e28971988676d4ea97194fd990d4be05bd72e835`.
