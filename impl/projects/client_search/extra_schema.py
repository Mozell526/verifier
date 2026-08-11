"""Project-specific schemas for annotated client_search extra fields."""

EXTRA_SCHEMAS = {
    "verifier.extra.semantic_equivalence_rules": {
        "value_type": "mapping",
        "required_keys": [
            "equivalent_condition_forms",
            "operator_compatibility",
            "equivalent_fields",
        ],
        "allowed_keys": [
            "equivalent_condition_forms",
            "operator_compatibility",
            "equivalent_fields",
        ],
        "properties": {
            "equivalent_condition_forms": "list",
            "operator_compatibility": "list",
            "equivalent_fields": "list",
        },
    }
}
