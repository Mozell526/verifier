# Issue #003: Capability manifest drops later enum references for repeated fields

**Class**: functionality
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output + code-analysis

## Verifier Discovery

`build_capability_manifest()` resolves enum values only inside `if field_name not in fields`. When later intents reuse the same field with another `enum_ref`, their enum values are ignored.

Observed on current client_search sources:

```text
field: polNoInfo.plancodeinfo.abbrname
enum refs: millionMedicalProducts, taxPreferredPensionProducts,
           polNoInfo.plancodeinfo.abbrname
expected union: 25 values
manifest output: 8 values
missing: 17 values
```

Missing values include `税优养老`, `智盈倍护`, `盛世优享`, `安颐尊享`, the `颐享延年*` family, and `金越养老年金（分红）`.

The loader also silently returns an empty enum registry for a missing or malformed `enums_path`; a probe with `/does/not/exist.yaml` returned 80 fields but only 2 fields with inline enums. This can make the Judge context look valid while losing the external protocol material it is meant to expose.

Root cause: field-level aggregation is initialized from the first intent rather than merging enum metadata across all intents, combined with fail-open enum loading.

Owning layer: client_search capability manifest.

