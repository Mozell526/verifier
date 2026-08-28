# Materials Protocol

User-managed materials describe **what** to evaluate (glossaries, capability text, API notes). System assets such as `evaluation.md` and `judge_boundary.md` describe **how** to evaluate and stay code-managed.

Design background: `docs/materials-system-implementation.md`. This file is the frozen V1 runtime contract.

## Layering

The materials page is a read model over four layers, split by **writer × mutability**:

| Layer | Writer | Page | Editable | Integrity |
|---|---|---|---|---|
| System assets (`project.yaml assets`, kind context/tool/…) | maintainers, with code | read-only list | no | git |
| Investigation artifacts (`assets` kind investigation, draft + production) | machine (investigation flows) | read-only: manifest summary, overview, file list, `source_revision` | **never** (hash chain rejects manual edits) | hash chain |
| Production materials (slots / free) | user upload, or adopt-materialize (V1.5) | read/write | yes — editing a non-upload material downgrades provenance to `derived` and marks `edited` (页面亮「内容已非原样」) | content-hash seal |
| Project structured stores (e.g. `capability_map`) | user | rendered **only when declared** in `materials.yaml stores` | yes | store schema |

Investigation operations are 查看 / 重新调查 / 采纳 / 丢弃; on a remote host only 查看 exists (re-investigate and adopt need the business source, which never ships to the server). Trust tiers are displayed, not enforced (`min_trust` gating deferred until there is a second operator).

`/api/materials` returns `{project_id, sections: [...]}` where each section carries `kind` (`slots` / `free` / `investigation` / `system_assets` / `capability_map`), `editable`, and its items. The frontend renders sections purely from this response — project differences are declaration-driven, nothing is hardcoded per project. `/api/material/asset_view` gives the read-only projection of one asset (investigation package: manifest summary + `overview.md` + file list; context/tool: truncated body).

## Entities

Each material lives at `impl/data/<project>/materials/<id>/`:

- `manifest.json` — identity, title, `sha256` of the body, size, provenance, timestamps
- `content.md` — UTF-8 text only (markdown / txt / yaml / json pasted as text)

`id` is a slot id when the material fills a declared slot; otherwise it is a free material id. Both must match `^[a-z][a-z0-9_-]*$`.

Reference scheme: `material://<project>/<id>`. Resolvers expand it to the sealed body. Consumption modes on a material are combinable:

| Mode | When it applies | Missing / over-budget |
|---|---|---|
| binding | slot `roles` include the current role | required slot missing → refuse the run; total bound chars > 30000 → refuse |
| reference | a `material://` URI is expanded | missing id → resolution error |
| queryable | not in V1 | — |

Server verifies **content hash** only. Source hashes (business-repo revision) are declarative metadata and are not checked on a remote eval host.

Provenance `source` is one of `user_upload`, `investigation`, `derived`. Trust display order: local investigation > external investigation > derived > upload. V1 does not sign payloads.

## Slots

Slots are a project contract, not an end-user object. Maintainers declare them in `impl/projects/<project>/materials.yaml` (not `project.yaml`: the project config parser rejects unknown keys).

```yaml
slots:
  - slot_id: field_glossary
    title: 字段口径表
    required: true
    roles: [judge]
    fill: [upload]
```

`fill` may list `upload`, `investigate_http`, `source_bind`. V1 only implements `upload`. Roles are `judge`, `mock`, `attribute`.

The same file may declare `stores:` — project-specific structured material stores the page should render. Allowed values: `capability_map`. A store not declared is not shown; its CRUD APIs stay project-scoped either way.

Users fill slots and create free materials on `materials.html`. They do not create slots. Recurring free materials may be promoted to a slot by a maintainer.

`llm_probe` declares no slots and `stores: [capability_map]` (capability presets are llm_probe-specific — only its code resolves `capability_ref`). `client_search` requires `field_glossary` for judge and declares no stores.

## Lifecycle (V1)

- Upload / overwrite via `/api/material/upload` writes content then a sealed manifest. Overwriting a material whose provenance is `investigation` or `derived` with different content downgrades provenance to `{source: derived, edited: true}` (origin preserved in `derived_from` / `detail`); identical content keeps provenance untouched.
- Get via `/api/material/get` returns summary + body after hash check.
- Delete via `/api/material/delete`. Deleting a required slot blocks later runs.
- Overview via `/api/materials` (sections, see Layering). Read-only asset projection via `/api/material/asset_view`.

Investigation artifacts stay in `draft/investigation/` (candidate) and `investigation/` (production). Adopting them into materials (materialize) is V1.5 and is not part of this runtime.

## Preflight and injection

- `live_run` / `run_chain` / non-empty `batch_run` call `require_materials(project_id)` before work. Missing required slots raise with slot titles and point at the materials page.
- Judge loads `binding_materials_for_role(project_id, "judge")`, injects the bodies into the system prompt, and records `kind: bound_material` evidence with uri + sha256.

Limits: body ≤ 200_000 characters; sum of bound bodies for one role ≤ 30_000 characters. Over-budget is an error, not a silent trim.
