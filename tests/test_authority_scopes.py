from __future__ import annotations

import pytest

from impl.core.authority_scopes import (
    AuthorityScopeRejected,
    capability_carrier_enabled,
    enabled_scopes,
    in_run_authority_enabled,
    parse_enabled_scopes,
    require_in_run_scope,
)


def test_empty_scopes_disable_both_families() -> None:
    source = {"authority": {"enabled_scopes": []}}
    assert enabled_scopes(source) == ()
    assert in_run_authority_enabled(source) is False
    assert capability_carrier_enabled(source) is False


def test_capability_carrier_does_not_enable_in_run() -> None:
    source = {"authority": {"enabled_scopes": ["capability_carrier"]}}
    assert capability_carrier_enabled(source) is True
    assert in_run_authority_enabled(source) is False


def test_in_run_scope_member_check() -> None:
    source = {"authority": {"enabled_scopes": ["responsibility"]}}
    assert require_in_run_scope(source, "responsibility") == "responsibility"
    with pytest.raises(AuthorityScopeRejected):
        require_in_run_scope(source, "semantic_mapping")
    with pytest.raises(AuthorityScopeRejected):
        require_in_run_scope(source, "capability_carrier")


def test_client_search_project_enables_capability_carrier_only() -> None:
    from impl.core.project_loader import load_project

    spec = load_project("client_search")
    assert capability_carrier_enabled(spec) is True
    assert in_run_authority_enabled(spec) is False


def test_parse_rejects_unknown_scope() -> None:
    with pytest.raises(ValueError, match="unknown"):
        parse_enabled_scopes(["not_a_scope"], "verifier.authority.enabled_scopes")
