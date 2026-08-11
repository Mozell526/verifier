# Investigation-owned Index Strategy Exploration

Date: 2026-08-05
Status: proposed, simulation-backed
Scope: `spec/alg/investigate-keyindex.md`, `spec/alg/investigate.md`, `.agents/skills/draft/SKILL.md`

## 1. Problem

The protocol currently describes several useful Index forms and construction rules, but it can be read as if the protocol already knows how each material type should be indexed. That is too strong. A Collection's useful object boundary, retrieval projection, channels, and load target depend on the real project's source structure and runtime discovery needs.

The stable contract should therefore be an exploration method, not a closed mapping from material type to Index strategy.

## 2. Design principle

Core defines the generic Key-Index protocol, retrieval/load tools, provenance rules, and quality gates. Investigation explores whether and how each concrete Collection should be indexed. Solidify materializes only a strategy that passed investigation review. Runtime consumes the resulting Catalog and Index read-only.

Investigation may conclude that:

- one candidate strategy is suitable;
- several independent Indexes are useful;
- no Index is needed;
- no candidate is currently adequate, producing an unresolved investigation gap.

## 3. Exploration flow

```text
Collection profiling
  → candidate object boundaries
  → candidate source-derived projections
  → candidate retrieval channels
  → candidate target_ref design
  → deterministic experimental build
  → frozen retrieval/load simulation
  → quality and AI-hacking review
  → selected strategy | no-index | unresolved
  → Solidify
```

### 3.1 Collection profiling

Investigation records only facts needed to explore navigation:

- source structure and revision;
- content scale and context pressure;
- stable identities and possible object boundaries;
- deterministic load boundaries;
- runtime discovery tasks that the Collection is expected to support.

### 3.2 Candidate strategy

A candidate declares:

- indexed Collection;
- selected source objects and Entry granularity;
- exact, lexical, embedding, structured-filter, or other supported channels;
- deterministic projection rules over source content;
- `target_ref` construction and expected resolver;
- expected cost and known coverage limits.

Examples such as field-, rule-, enum-value-, mapping-, section-, or statement-level Indexes are informative patterns only. They are not normative type-to-strategy mappings.

### 3.3 Experimental build

The experiment materializes candidate Entries deterministically from source objects. Harness AI may propose selectors, projection composition, granularity, and channels, but must not freely author per-entry search prose, case synonyms, expected answers, or hidden routing instructions.

Every projection component must retain source derivation. Every `target_ref` must be tested independently from retrieval.

### 3.4 Frozen simulation

The comparison suite is frozen before candidate comparison and contains multiple classes:

- stable identifier lookup;
- source-vocabulary questions;
- held-out paraphrases not copied from source examples;
- ambiguous or multi-object questions;
- unrelated and unsupported questions;
- target-resolution and loaded-context checks.

Investigation compares candidates on:

- recall at the configured load budget;
- false-positive behavior and candidate rejectability;
- target-resolution success;
- loaded Evidence precision and sufficiency;
- projection size, truncation, duplication, and update cost;
- source derivation and absence of case leakage.

A search hit alone is never success. End-to-end navigation requires a correctly resolved target and correctly loaded real Evidence.

### 3.5 Conclusion

The investigation report records candidates, test classes, results, trade-offs, selected strategy, and remaining limitations. Metrics do not automatically select the winner; Harness AI performs semantic review under the protocol gates. If no strategy is adequate, it records an unresolved gap rather than adding fallback or AI-authored retrieval text.

## 4. Simulation evidence

### 4.1 `business-field-definitions`

231 field-level objects from the current Authority Environment were evaluated with exact, character lexical, BGE embedding, and RRF fusion.

| Projection candidate | Original queries Recall@5 | Held-out paraphrase Recall@5 | Observation |
|---|---:|---:|---|
| field + generic ContextUnit description | 6/11 | 5/10 | too little business meaning |
| field + source description/retrieval text/operator | 10/11 | 10/10 | strong compact candidate |
| previous + source examples/patterns | 11/11 | 10/10 | higher source-query recall, larger entries |
| previous + negative examples | 11/11 | 10/10 | no measured gain |

This supports investigation-owned projection comparison. It does not establish a global projection recipe.

### 4.2 `business-enhanced-rules`

Three candidate granularities/projections were compared on eight supported held-out queries and one unrelated query.

| Candidate | Entries | Avg chars | Max chars | Recall@5 | Observation |
|---|---:|---:|---:|---:|---|
| field summary: field + rule names/operators | 110 | 108 | 1,205 | 8/8 | compact; weaker precise rule targeting |
| field with all patterns | 110 | 1,084 | 10,395 | 8/8 | good recall; oversized and semantically mixed |
| individual rule entries | 776 | 179 | 1,177 | 8/8 | precise targets and bounded projections; more entries |

The unrelated query still produced nearest embedding candidates in every strategy. Therefore embedding top-k cannot prove relevance, and unsupported-query behavior must remain rejectable by later selection/Authority rather than be converted into evidence.

The two Collections led to different reasonable candidates under the same exploration method. This is the desired property.

## 5. Responsibility boundaries

### Investigation / Harness AI

- profile the Collection;
- propose and compare candidates;
- choose test classes and freeze the suite before comparison;
- perform semantic review;
- select, reject, or leave the strategy unresolved.

### Deterministic builder / validator

- extract Entries according to the candidate declaration;
- preserve source derivation;
- validate Entry identities and target resolution;
- detect oversized projections, missing targets, and schema violations;
- produce comparable experiment receipts.

### Solidify / Core

- materialize approved exact/lexical/embedding or other declared assets;
- expose generic Catalog, `search_index`, and `load_entry` contracts;
- avoid adding project-specific routing or fallback.

### Runtime / Authority

- discover and query available Indexes;
- treat retrieval results as navigation metadata;
- load real Evidence and synthesize within Authority;
- never modify investigation strategy or assets.

## 6. AI-hacking gates

A strategy must fail review if it:

- inserts evaluation queries, expected-answer terms, or unsupported synonyms into projections;
- uses fuzzy/full-text fallback to conceal unresolved `target_ref`;
- changes Evidence or business definitions to improve retrieval metrics;
- lets Harness AI both tailor the strategy to an unfrozen test set and claim success from that same set;
- treats embedding top-k, rerank score, or a search hit as Evidence or resolution;
- forces every Collection to build an Index merely to satisfy a structural check.

## 7. Planned protocol changes after approval

### `investigate-keyindex.md`

- make strategy exploration the normative construction model;
- demote material-type Index forms to non-normative examples;
- add candidate declaration, frozen simulation classes, comparison receipt, and `selected | no_index | unresolved` outcomes;
- preserve existing generic protocol, multi-channel, source-derivation, target-resolution, and runtime read-only rules;
- avoid prescribing a universal extractor or fixed route.

### `investigate.md`

- state that optional Key-Indexes are investigation conclusions, not expected outputs for every large Collection;
- add strategy exploration and semantic review to investigation convergence;
- clarify that Solidify only materializes a selected strategy and does not invent one.

### `.agents/skills/draft/SKILL.md`

- instruct Draft investigation to detect navigation pressure and run the exploration loop;
- require frozen positive/paraphrase/ambiguous/unsupported/load checks;
- require explicit no-index/unresolved outcomes when appropriate;
- forbid free per-entry search prose and metric-driven case leakage;
- keep the exact artifact schema flexible until the spec change is accepted.

## 8. Non-goals

This change does not yet:

- define every material type's Index strategy;
- implement a universal strategy plugin framework;
- require embedding or rerank for every Index;
- allow runtime learning or write-back;
- make retrieval decide fulfilled, not_fulfilled, or not_evaluable;
- modify current implementation before the protocol design is reviewed.
