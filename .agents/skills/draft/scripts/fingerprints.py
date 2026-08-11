"""Draft Loop freeze/resume 共享指纹（公共设施）。

Current/Draft/Runner 三档指纹用于判断“本次运行起点是否与上次相同”：
- current_fingerprint：production 侧项目资产 + impl/core 代码；
- draft_fingerprint：候选 Role 的 draft 资产与代码（不含 .state）；
- runner_fingerprint：Draft runner 脚本（比较/快照语义），变化会使
  之前落盘的运行时快照失去可比性。

任何一档变化都意味着旧 partial 的行不能复用（stale），必须丢弃重跑。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable


def _paths_hash(paths: Iterable[Path], *, roots: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(path.resolve() for path in paths)):
        label = str(path)
        for root in roots:
            if path.is_relative_to(root.resolve()):
                label = str(path.relative_to(root.resolve()))
                break
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def current_fingerprint(spec: Any) -> str:
    paths = []
    project_root = spec.project_package_path()
    for path in project_root.rglob("*"):
        if not path.is_file() or "draft" in path.relative_to(project_root).parts or "__pycache__" in path.parts:
            continue
        paths.append(path)
    verifier_root = spec.verifier_root_path()
    core_root = verifier_root / "impl" / "core"
    paths.extend(path for path in core_root.rglob("*.py") if "__pycache__" not in path.parts)
    return _paths_hash(paths, roots=(project_root, verifier_root))


def draft_fingerprint(spec: Any, role: str) -> str:
    project_root = spec.project_package_path()
    root = project_root / "draft"
    paths = [
        path
        for path in root.rglob("*")
        if path.is_file() and ".state" not in path.parts and "__pycache__" not in path.parts
    ]
    return _paths_hash(paths, roots=(project_root,))


def runner_fingerprint(spec: Any) -> str:
    verifier_root = spec.verifier_root_path()
    scripts_root = verifier_root / ".agents" / "skills" / "draft" / "scripts"
    paths = [
        path
        for path in scripts_root.rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    return _paths_hash(paths, roots=(verifier_root,))
