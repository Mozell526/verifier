# client_search live schema — metadata + dataclass-backed check
from __future__ import annotations

from impl.core.live_schema_check import LiveSchemaCheck
from impl.core.project_loader import load_project
from impl.core.structured_output import dataclass_to_json_schema
from impl.projects.client_search.capability_manifest import build_capability_manifest, lean_capability_manifest
from impl.projects.client_search.schema import ClientSearchExtractOutput, ClientSearchRequest

def _source_field_definitions_path() -> str:
    return load_project("client_search").source_path("field_definitions")


def _source_field_enum_paths() -> list[str]:
    spec = load_project("client_search")
    return [
        path
        for path in (
            spec.source_path("field_enums"),
            spec.source_path("planfullname_enums"),
            spec.source_path("abbrname_enums"),
            spec.source_path("claimplancodename_enums"),
            spec.source_path("profname_enums"),
        )
        if path
    ]


REQUIRED_INPUT_FIELDS = ["user_text"]
CAPABILITY_MANIFEST = lean_capability_manifest(build_capability_manifest(
    _source_field_definitions_path(),
    enums_path=_source_field_enum_paths(),
))

REQUEST_SCHEMA = ClientSearchRequest
EXTRACT_OUTPUT_SCHEMA = ClientSearchExtractOutput
REQUEST_JSON_SCHEMA = dataclass_to_json_schema(REQUEST_SCHEMA)
EXTRACT_OUTPUT_JSON_SCHEMA = dataclass_to_json_schema(EXTRACT_OUTPUT_SCHEMA)

check = LiveSchemaCheck(REQUEST_SCHEMA, EXTRACT_OUTPUT_SCHEMA)
