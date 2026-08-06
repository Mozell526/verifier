from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Iterable, Mapping


class PathScope(str, Enum):
    BUSINESS_SOURCE = "business_source"
    VERIFIER_REPO = "verifier_repo"
    PROJECT_PACKAGE = "project_package"
    KNOWLEDGE_ROUTE = "knowledge_route"
    ARTIFACT_PACKAGE = "artifact_package"

    @property
    def prefix(self) -> str:
        return _SCOPE_PREFIXES[self]


_SCOPE_PREFIXES = {
    PathScope.BUSINESS_SOURCE: "business",
    PathScope.VERIFIER_REPO: "verifier",
    PathScope.PROJECT_PACKAGE: "project",
    PathScope.KNOWLEDGE_ROUTE: "route",
    PathScope.ARTIFACT_PACKAGE: "artifact",
}
_PREFIX_SCOPES = {prefix: scope for scope, prefix in _SCOPE_PREFIXES.items()}
_PREFIX = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)://(.*)$")
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_WINDOWS_ENV = re.compile(r"%[A-Za-z_][A-Za-z0-9_]*%")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


class PathContractError(ValueError):
    def __init__(self, code: str, field_path: str, message: str) -> None:
        self.code = code
        self.field_path = field_path
        super().__init__(f"{code} at {field_path}: {message}")


@dataclass(frozen=True)
class PrefixedPath:
    scope: PathScope
    location: str

    def __str__(self) -> str:
        return f"{self.scope.prefix}://{self.location}"


def parse_prefixed_path(
    value: Any,
    *,
    field_path: str,
    allowed_scopes: Iterable[PathScope],
) -> PrefixedPath:
    if not isinstance(value, str) or not value.strip():
        raise PathContractError("PATH_PREFIX_REQUIRED", field_path, "expected a non-empty prefixed path")
    text = value.strip()
    if text.startswith("file://"):
        raise PathContractError("PATH_ABSOLUTE_CONFIG", field_path, "file:// paths are forbidden in configuration")
    allowed = frozenset(allowed_scopes)
    match = _PREFIX.fullmatch(text)
    if match is not None:
        prefix, raw_location = match.groups()
        scope = _PREFIX_SCOPES.get(prefix)
        if scope is None:
            raise PathContractError("PATH_PREFIX_UNKNOWN", field_path, f"unknown path prefix {prefix!r}")
        if scope not in allowed:
            raise PathContractError(
                "PATH_PREFIX_NOT_ALLOWED",
                field_path,
                f"prefix {prefix!r} is not allowed; expected one of {sorted(item.prefix for item in allowed)}",
            )
        return PrefixedPath(scope, _normalize_location(raw_location, field_path))

    _reject_nonportable_location(text, field_path)
    raise PathContractError("PATH_PREFIX_REQUIRED", field_path, "path must declare an explicit logical prefix")


def canonical_prefixed_path(
    value: Any,
    *,
    field_path: str,
    allowed_scopes: Iterable[PathScope],
) -> str:
    path = parse_prefixed_path(
        value,
        field_path=field_path,
        allowed_scopes=allowed_scopes,
    )
    return str(path)


@dataclass(frozen=True)
class PathRoots:
    verifier_repo: Path | None = None
    business_source: Path | None = None
    project_package: Path | None = None
    knowledge_route: Path | None = None
    artifact_package: Path | None = None

    def root_for(self, scope: PathScope, *, field_path: str) -> Path:
        value = getattr(self, scope.value)
        if value is None:
            raise PathContractError(
                "PATH_ROOT_UNBOUND",
                field_path,
                f"runtime root {scope.value!r} was not provided",
            )
        path = Path(value)
        if not path.is_absolute():
            raise PathContractError(
                "PATH_ROOT_UNBOUND",
                field_path,
                f"runtime root {scope.value!r} must be absolute",
            )
        return path.resolve()


@dataclass(frozen=True)
class ResolvedPath:
    logical: PrefixedPath
    physical: Path

    def __fspath__(self) -> str:
        return os.fspath(self.physical)

    def __str__(self) -> str:
        return str(self.physical)


class PathResolver:
    def __init__(self, roots: PathRoots) -> None:
        self.roots = roots

    def resolve(
        self,
        value: PrefixedPath | str,
        *,
        field_path: str,
        allowed_scopes: Iterable[PathScope] | None = None,
        expected_type: str = "any",
        must_exist: bool = True,
    ) -> ResolvedPath:
        if isinstance(value, str):
            path = parse_prefixed_path(
                value,
                field_path=field_path,
                allowed_scopes=allowed_scopes or tuple(PathScope),
            )
        else:
            path = value
            allowed = frozenset(allowed_scopes or tuple(PathScope))
            if path.scope not in allowed:
                raise PathContractError(
                    "PATH_PREFIX_NOT_ALLOWED",
                    field_path,
                    f"prefix {path.scope.prefix!r} is not allowed",
                )

        if expected_type not in {"any", "file", "directory", "executable"}:
            raise ValueError(f"unsupported expected_type {expected_type!r}")
        root = self.roots.root_for(path.scope, field_path=field_path)
        lexical = root / PurePosixPath(path.location)
        candidate = lexical.resolve(strict=False)
        if not candidate.is_relative_to(root):
            raise PathContractError(
                "PATH_SYMLINK_ESCAPE",
                field_path,
                "symbolic-link resolution escapes its logical root",
            )
        if must_exist and not candidate.exists():
            raise PathContractError("PATH_NOT_FOUND", field_path, f"path does not exist: {path}")
        if candidate.exists():
            if expected_type == "file" and not candidate.is_file():
                raise PathContractError("PATH_TYPE_MISMATCH", field_path, f"expected file: {path}")
            if expected_type == "directory" and not candidate.is_dir():
                raise PathContractError("PATH_TYPE_MISMATCH", field_path, f"expected directory: {path}")
            if expected_type == "executable" and (not candidate.is_file() or not os.access(candidate, os.X_OK)):
                raise PathContractError("PATH_TYPE_MISMATCH", field_path, f"expected executable file: {path}")
        return ResolvedPath(path, candidate)


@dataclass(frozen=True)
class LogicalPathRef:
    location_scope: PathScope
    location: str
    symbol: str = ""
    revision: str = ""
    sha256: str = ""

    def __post_init__(self) -> None:
        normalized = "." if self.location == "." else _normalize_location(
            self.location, "LogicalPathRef.location"
        )
        object.__setattr__(self, "location", normalized)
        if self.sha256 and not _SHA256.fullmatch(self.sha256):
            raise PathContractError(
                "PATH_TYPE_MISMATCH",
                "LogicalPathRef.sha256",
                "expected a 64-character hexadecimal sha256",
            )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, field_path: str = "logical_path_ref") -> "LogicalPathRef":
        allowed = {"location_scope", "location", "symbol", "revision", "sha256"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise PathContractError("PATH_TYPE_MISMATCH", field_path, f"unknown field {unknown[0]!r}")
        try:
            scope = PathScope(value["location_scope"])
            location = value["location"]
        except (KeyError, ValueError) as exc:
            raise PathContractError(
                "PATH_TYPE_MISMATCH",
                field_path,
                "location_scope and location are required",
            ) from exc
        if not isinstance(location, str):
            raise PathContractError("PATH_TYPE_MISMATCH", field_path, "location must be a string")
        optional: dict[str, str] = {}
        for key in ("symbol", "revision", "sha256"):
            item = value.get(key, "")
            if item is None:
                item = ""
            if not isinstance(item, str):
                raise PathContractError("PATH_TYPE_MISMATCH", field_path, f"{key} must be a string")
            optional[key] = item
        return cls(scope, location, **optional)

    @classmethod
    def from_prefixed_path(cls, value: PrefixedPath, **metadata: str) -> "LogicalPathRef":
        return cls(value.scope, value.location, **metadata)

    @property
    def prefixed_path(self) -> PrefixedPath:
        return PrefixedPath(self.location_scope, self.location)

    def resolve(
        self,
        resolver: PathResolver,
        *,
        field_path: str = "logical_path_ref",
        expected_type: str = "any",
        must_exist: bool = True,
    ) -> ResolvedPath:
        return resolver.resolve(
            self.prefixed_path,
            field_path=field_path,
            allowed_scopes={self.location_scope},
            expected_type=expected_type,
            must_exist=must_exist,
        )

    def to_mapping(self) -> Mapping[str, str]:
        data = {
            "location_scope": self.location_scope.value,
            "location": self.location,
        }
        for key in ("symbol", "revision", "sha256"):
            value = getattr(self, key)
            if value:
                data[key] = value
        return MappingProxyType(data)


def logical_ref_for_path(
    path: Path | str,
    *,
    scope: PathScope,
    roots: PathRoots,
    field_path: str,
    symbol: str = "",
    revision: str = "",
    sha256: str = "",
) -> LogicalPathRef:
    """Convert a runtime path to a reference with one caller-declared scope.

    Reverse mapping is intentionally not heuristic: project and verifier roots
    commonly overlap, so the caller must preserve the field's semantic scope.
    """
    root = roots.root_for(scope, field_path=field_path)
    physical = Path(path)
    if not physical.is_absolute():
        raise PathContractError(
            "PATH_ROOT_UNBOUND",
            field_path,
            "runtime path must be absolute before it can become a LogicalPathRef",
        )
    resolved = physical.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise PathContractError(
            "PATH_TRAVERSAL",
            field_path,
            f"runtime path is outside the declared {scope.value!r} root",
        )
    relative = resolved.relative_to(root).as_posix() or "."
    return LogicalPathRef(
        scope,
        relative,
        symbol=symbol,
        revision=revision,
        sha256=sha256,
    )


def _normalize_location(value: str, field_path: str) -> str:
    _reject_nonportable_location(value, field_path)
    if value == ".":
        return value
    if "\\" in value:
        raise PathContractError("PATH_TRAVERSAL", field_path, "location must use POSIX '/' separators")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PathContractError("PATH_TRAVERSAL", field_path, "location must be a normalized relative path")
    normalized = path.as_posix()
    if normalized != value:
        raise PathContractError("PATH_TRAVERSAL", field_path, "location must already be normalized")
    return normalized


def _reject_nonportable_location(value: str, field_path: str) -> None:
    if (
        value.startswith(("/", "~", "file://", "//", "\\\\"))
        or _WINDOWS_ABSOLUTE.match(value)
    ):
        raise PathContractError("PATH_ABSOLUTE_CONFIG", field_path, "absolute or home-relative paths are forbidden")
    if "$" in value or _WINDOWS_ENV.search(value):
        raise PathContractError("PATH_TRAVERSAL", field_path, "environment expansion is forbidden inside a logical path")
