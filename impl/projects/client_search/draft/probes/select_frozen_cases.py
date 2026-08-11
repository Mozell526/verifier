from __future__ import annotations

import argparse
import json
from pathlib import Path

from impl.core.portable_artifact import write_portable_export


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--case-ids", required=True)
    args = parser.parse_args()

    source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    wanted = [item.strip() for item in args.case_ids.split(",") if item.strip()]
    by_id = {
        str(item.get("source_case_id") or item.get("id") or ""): item
        for item in source
        if isinstance(item, dict)
    }
    missing = [item for item in wanted if item not in by_id]
    if missing:
        raise ValueError(f"missing frozen case IDs: {missing}")
    write_portable_export(
        Path(args.output),
        [by_id[item] for item in wanted],
    )
    print(json.dumps({"case_count": len(wanted), "case_ids": wanted}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
