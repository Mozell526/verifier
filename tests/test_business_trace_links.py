"""Link enumeration uses only Agno structure and states relations, never verdicts."""
import json

from impl.projects.llm_probe.business_trace.links import AXIS_LINK_TYPES, build_links


def row(ident, kind, fields, **meta):
    return {"id": ident, "kind": kind, "turn": "turn1", "scope": "current", "run_id": "agent-run",
            "fields": {k: {"status": "available", "value": v} for k, v in fields.items()}, **meta}


def dossier():
    error = '{"execution":{"status":"ERROR","code":"X","retryable":false}}'
    return {
        "sources": [{"id": "turn1"}], "contents": {}, "gaps": [],
        "records": [
            row("run", "runs", {"input": "question"}),
            row("s0", "steps", {"output": "prepared"}, parent_ref="run", name="prepare"),
            row("s1", "steps", {"output": "routed"}, parent_ref="run", name="route"),
            row("s1/a", "steps", {"output": "agent out"}, parent_ref="s1", name="agent"),
            row("span-s1", "steps", {"input": "context: prepared"}, name="route.aexecute", representation="span"),
            row("t0", "tool_calls", {"arguments": {"b": 1, "a": [2, 1]}, "result": error,
                                     "metrics": {"start_time": 1, "end_time": 2}}, name="lookup"),
            row("t1", "tool_calls", {"arguments": {"a": [2, 1], "b": 1}, "result": error,
                                     "metrics": {"start_time": 3, "end_time": 4}}, name="lookup"),
            row("t2", "tool_calls", {"arguments": {"a": [1, 2], "b": 1}, "result": error,
                                     "metrics": {"start_time": 5, "end_time": 6}}, name="lookup"),
            row("t1-span", "tool_calls", {"arguments": {"a": [2, 1], "b": 1}}, name="lookup", persisted_ref="t1"),
            row("m-tool", "messages", {"content": error}, role="tool", tool_call_ref="t0"),
            row("m-out", "messages", {"content": "answer"}, role="assistant"),
            row("stored", "final_output", {"output": '{"answer":"x","trace_id":"T"}'}),
            row("delivered", "delivered_output", {"output": {"output_text": '{"answer": "x"}'}}),
            row("old", "tool_calls", {"arguments": {}}, name="lookup", scope="history"),
        ],
        "model_calls": [
            {"id": "call1", "turn": "turn1", "scope": "current", "output_message_ref": "m-out",
             "reconstructed_input": {"status": "verified", "message_refs": ["m-tool"]}},
            {"id": "call2", "turn": "turn1", "scope": "current", "exact_request": {"status": "available"},
             "reconstructed_input": {"status": "verified", "message_refs": ["m-tool"]}},
        ],
    }


def by_id(links):
    return {link["link_id"]: link for link in links["links"]}


def test_links_cover_each_type_with_both_ends_and_facts_only():
    links = by_id(build_links(dossier()))
    assert links["intent_understanding:turn1"]["input"] == [{"ref": "run", "field": "input"}]
    step = links["context_memory:step:s0→s1"]
    assert step["output"] == [{"ref": "span-s1", "field": "input"}]
    assert step["facts"] == {"next_input_recorded": True, "contains": True}
    assert links["planning_routing:branch:s1"]["facts"] == {"executed": ["agent"]}
    # Exact span request wins over reconstruction; reconstruction is labelled as such.
    assert links["model_capability:call2"]["input"] == [{"ref": "call2", "field": "exact_request"}]
    assert links["model_capability:call1"]["facts"] == {"input_source": "verified"}
    # A tool result reaching the model is recorded once, at its first model input.
    transfers = [k for k in links if k.startswith("context_memory:tool→model")]
    assert transfers == ["context_memory:tool→model:t0→call1"] and links[transfers[0]]["facts"] == {"contains": True}
    assert links["context_memory:deliver:turn1"]["facts"] == {"vs_stored": {"changed": [], "dropped": ["trace_id"], "added": []}}
    for link in links.values():
        assert not {"verdict", "status", "outcome"} & set(link["facts"])


def test_repeat_uses_canonical_arguments_and_skips_copies_and_history():
    links = by_id(build_links(dossier()))
    assert {k for k in links if k.startswith("tool_execution:")} == {"tool_execution:t0", "tool_execution:t1", "tool_execution:t2"}
    repeat = links["planning_routing:repeat:t1"]
    assert repeat["facts"] == {"tool": "lookup", "repeat_of": "t0", "started_after_prior_ended": True,
                               "same_result": True}
    # List order is meaning: a different order is a different call.
    assert "planning_routing:repeat:t2" not in links


def test_axis_filter_keeps_only_its_link_types():
    data = dossier()
    for axis_id, types in AXIS_LINK_TYPES.items():
        links = build_links(data, axis_id=axis_id)
        assert set(links["types"]) == set(types)
        assert {link["link_type"] for link in links["links"]} <= set(types)
    json.dumps(build_links(data), ensure_ascii=False)


def test_reconstructed_model_input_includes_its_agents_tool_definitions():
    data = dossier()
    data["records"] += [
        row("helper-run", "runs", {}, parent_ref="run", name="helper", run_id="helper-run"),
        row("def/helper", "definitions", {}, name="helper", definition_type="component"),
        row("def/helper/tools/0", "definitions", {}, name="lookup", definition_type="tool"),
        row("def/other/tools/0", "definitions", {}, name="lookup", definition_type="tool"),
    ]
    data["model_calls"][0]["reconstructed_input"]["run_id"] = "helper-run"
    links = by_id(build_links(data))
    # Agno sends the agent's tool schemas with every request; persisted messages alone miss them.
    assert links["model_capability:call1"]["input"] == [{"ref": "m-tool", "field": "content"},
                                         {"ref": "def/helper/tools/0", "field": "definition"}]
    assert links["model_capability:call2"]["input"] == [{"ref": "call2", "field": "exact_request"}]


def test_model_output_end_uses_span_output_when_message_content_not_saved():
    """持久化助手消息常不存正文；输出端不得指向空字段，改用 span 记录的输出。"""
    d = dossier()
    d["records"] = [r for r in d["records"] if r["id"] != "m-out"] + [
        {**row("m-out", "messages", {}, role="assistant"),
         "fields": {"content": {"status": "missing", "note": "本记录没有保存此字段"}}}]
    d["model_calls"][0]["output"] = {"status": "available", "value": "answer"}
    assert by_id(build_links(d))["model_capability:call1"]["output"] == [{"ref": "call1", "field": "output"}]
    d["model_calls"][0]["output"] = {"status": "missing"}
    assert by_id(build_links(d))["model_capability:call1"]["output"] == [{"ref": "m-out", "field": "content"}]
