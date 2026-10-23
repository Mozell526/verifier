"""主轴结论：调用现有的 M 函数（spec/math-abstract/judge.md §3.1），不改。"""
from impl.projects.llm_probe_loop.eval_axes.main_verdict import main_verdict


def synthesize(view):
    truth = view.materials.get("result.truthfulness")
    results = [{"type_id": "fulfillment", "status": "succeeded", "output": view.materials["result.fulfillment"]}]
    if truth is not None:
        results.append({"type_id": "truthfulness", "status": "succeeded", "output": truth})
    verdict = main_verdict(results)
    return {"verdict": verdict["verdict"], "reason": verdict["basis"], "composition": verdict["composition"]}
