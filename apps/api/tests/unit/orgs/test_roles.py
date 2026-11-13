"""role_at_least: the one function every org-scoped route depends on (via org_actor) to
decide whether a membership or API key's role is high enough for a given route."""

from __future__ import annotations

from agenteval.orgs.service import role_at_least


def test_owner_satisfies_every_minimum() -> None:
    for minimum in ("viewer", "member", "admin", "owner"):
        assert role_at_least("owner", minimum) is True


def test_viewer_only_satisfies_viewer() -> None:
    assert role_at_least("viewer", "viewer") is True
    assert role_at_least("viewer", "member") is False
    assert role_at_least("viewer", "admin") is False
    assert role_at_least("viewer", "owner") is False


def test_admin_satisfies_admin_and_below_but_not_owner() -> None:
    assert role_at_least("admin", "member") is True
    assert role_at_least("admin", "admin") is True
    assert role_at_least("admin", "owner") is False


def test_an_unknown_role_satisfies_nothing() -> None:
    assert role_at_least("not-a-real-role", "viewer") is False
