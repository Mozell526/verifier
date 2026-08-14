from impl.core.show_schema import ShowSchema

SHOW_SCHEMA = ShowSchema(
    input_fields=["extra_input_params.policySearchParseArgs.query"],
    output_fields=["status", "message", "query", "filter"],
)
