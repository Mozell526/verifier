from impl.core.resources import META_PREFIX, ResourceTable
from impl.projects.llm_probe_loop.business_trace import links
from impl.projects.llm_probe_loop.business_trace.providers import langfuse

ROW = {"id": "turn1/records/observations/15", "turn": "turn1", "kind": "tool_calls", "name": "backend.policy.search",
       "observation_type": "TOOL", "outcome": "success",
       "fields": {"output": {"status": "available", "value": "保单 P1"}, "input": {"status": "missing"}}}
OTHER = {"id": "turn2/records/run", "turn": "turn2", "kind": "runs", "fields": {}}
DOSSIER = {"sources": [{"id": "turn1", "recorder": "Langfuse"}, {"id": "turn2", "recorder": "Agno"}],
           "records": [ROW, OTHER], "contents": {}}


def test_mounts_only_langfuse_turns_with_descriptor_and_link_ends(monkeypatch):
    monkeypatch.setattr(links, "build_links", lambda dossier: {"links": [
        {"link_type": "tool_execution", "input": [{"ref": ROW["id"], "field": "input"}],
         "output": [{"ref": ROW["id"], "field": "output"}]},
        {"link_type": "context_memory", "input": [{"ref": ROW["id"], "field": "output"}], "output": []}]})
    monkeypatch.setattr(links, "TYPE_AXES", {"tool_execution": ("tool_execution",), "context_memory": ("context_memory", "x")})
    table = ResourceTable()
    langfuse.mount(DOSSIER, table)
    [block] = list(table)
    d = block.descriptor
    assert (str(d.uri), d.name, d.title, d.description) == (
        "trace://turn1/records/observations/15", ROW["id"], "backend.policy.search", "tool_calls · TOOL · success")
    assert block.body["name"] == "backend.policy.search" and block.body["fields"]["output"]["value"] == "保单 P1"
    assert d.meta[META_PREFIX + "roles"] == {"tool_execution": {"input": ["input"], "output": ["output"]},
                                             "context_memory": {"output": ["input"]}, "x": {"output": ["input"]}}
