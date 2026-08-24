"""Policy Search live schema 不变量。"""
from __future__ import annotations

from impl.core.live_schema_check import LiveSchemaCheck
from impl.core.structured_output import dataclass_to_json_schema
from impl.projects.policy_search.schema import PolicySearchExtractOutput, PolicySearchRequest

REQUIRED_INPUT_FIELDS = ["session_id", "trace_id", "extra_input_params"]

REQUEST_SCHEMA = PolicySearchRequest
EXTRACT_OUTPUT_SCHEMA = PolicySearchExtractOutput
REQUEST_JSON_SCHEMA = dataclass_to_json_schema(REQUEST_SCHEMA)
EXTRACT_OUTPUT_JSON_SCHEMA = dataclass_to_json_schema(EXTRACT_OUTPUT_SCHEMA)

check = LiveSchemaCheck(REQUEST_SCHEMA, EXTRACT_OUTPUT_SCHEMA)
