from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from impl.core.draft_gate_feedback import analyze_judge_gate_obligations, score_judge_gate_replay


def run_replay(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for row in payload.get("records") or []:
        gate = analyze_judge_gate_obligations(
            result=row["result"], runtime=row.get("runtime") or {},
            obligations=row.get("obligations") or [],
        )
        records.append({**row, "gate": gate})
    score = score_judge_gate_replay(records)
    return {"schema_version": 1, "suite_id": payload.get("suite_id"), "score": score, "records": records}


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("judge-authority-gate-replay.json")
    result = run_replay(source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["score"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
