"""跨模块共享的稳定 JSON 哈希（确定性序列化 + sha256）。"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_sha256(value: Any) -> str:
    """对结构做确定性 sha256：紧凑分隔符 + sort_keys + default=str。

    与 authority_investigation_gates / investigation_validation 原有 _stable_hash、
    context_governance 原有 _stable_sha256 对 JSON 可序列化输入字节一致。
    """
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
