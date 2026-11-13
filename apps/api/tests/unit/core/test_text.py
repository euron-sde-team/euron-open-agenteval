"""slugify: the one piece of text normalization this project relies on for unique
organization slugs."""

from __future__ import annotations

from agenteval.core.text import slugify


def test_slugify_lowercases_and_hyphenates() -> None:
    assert slugify("Kestrel Labs") == "kestrel-labs"


def test_slugify_collapses_runs_of_non_alphanumeric_characters() -> None:
    assert slugify("A & B!! Corp.") == "a-b-corp"


def test_slugify_strips_leading_and_trailing_hyphens() -> None:
    assert slugify("  --hello--  ") == "hello"


def test_slugify_truncates_to_max_len() -> None:
    assert len(slugify("a" * 100, max_len=10)) == 10


def test_slugify_never_returns_an_empty_string() -> None:
    assert slugify("!!!") == "item"
