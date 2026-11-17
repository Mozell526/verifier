"""侦探交的发现：环节编号在表里、新环节有端点、出处都是读过的（spec/alg/axis_loop.md §12.2.2、resources.md §11）。"""
from impl.projects.llm_probe_loop.process_axes import TRACE, check_analysis


def _norm_id(raw: object) -> str:
    text = str(raw or "").strip().removeprefix("trace://")
    return text.rpartition("/fields/")[0] if "/fields/" in text else text


def check(view):
    inlined = set(view.resources.inlined) if view.resources is not None else set()
    called = {_norm_id(i) for c in view.calls if c.tool == "read_material" and not c.is_error for i in (c.args.get("ids") or [])}
    return check_analysis(view.materials[TRACE], view.own, inlined | called)
