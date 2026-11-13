"""Each deterministic check against both a pass and a fail case, and against a test case
that does not define its field at all (must return None, not a failing score)."""

from __future__ import annotations

from agenteval.evaluators.deterministic import (
    exact_match,
    forbidden_tool_called,
    json_schema_valid,
    regex_match,
    required_tool_called,
    run_deterministic_checks,
)
from agenteval.evaluators.schema import AgentOutput, EvaluationCase, ExpectedBehavior, ToolCall


def _case(
    expected: ExpectedBehavior, text: str = "", tool_calls: tuple[ToolCall, ...] = ()
) -> EvaluationCase:
    return EvaluationCase(
        test_case_id="tc-1", expected=expected, actual=AgentOutput(text=text, tool_calls=tool_calls)
    )


def test_exact_match_passes_on_identical_text() -> None:
    case = _case(ExpectedBehavior(exact_match="hello"), text="hello")
    result = exact_match(case)
    assert result is not None
    assert result.passed is True
    assert result.score == 1.0
    assert result.method == "deterministic"


def test_exact_match_fails_on_different_text() -> None:
    case = _case(ExpectedBehavior(exact_match="hello"), text="goodbye")
    result = exact_match(case)
    assert result is not None
    assert result.passed is False
    assert result.score == 0.0


def test_exact_match_ignores_surrounding_whitespace() -> None:
    case = _case(ExpectedBehavior(exact_match="hello"), text="  hello  \n")
    result = exact_match(case)
    assert result is not None
    assert result.passed is True


def test_exact_match_returns_none_when_not_configured() -> None:
    case = _case(ExpectedBehavior(), text="anything")
    assert exact_match(case) is None


def test_regex_match_passes_on_a_match() -> None:
    case = _case(ExpectedBehavior(regex=r"^\d{3}-\d{4}$"), text="555-1234")
    result = regex_match(case)
    assert result is not None
    assert result.passed is True


def test_regex_match_fails_on_no_match() -> None:
    case = _case(ExpectedBehavior(regex=r"^\d{3}-\d{4}$"), text="not a phone number")
    result = regex_match(case)
    assert result is not None
    assert result.passed is False


def test_regex_match_returns_none_when_not_configured() -> None:
    assert regex_match(_case(ExpectedBehavior())) is None


def test_json_schema_valid_passes_on_a_conforming_document() -> None:
    schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
    case = _case(ExpectedBehavior(json_schema=schema), text='{"name": "Ada"}')
    result = json_schema_valid(case)
    assert result is not None
    assert result.passed is True


def test_json_schema_valid_fails_on_a_schema_violation() -> None:
    schema = {"type": "object", "required": ["name"]}
    case = _case(ExpectedBehavior(json_schema=schema), text="{}")
    result = json_schema_valid(case)
    assert result is not None
    assert result.passed is False
    assert "schema violation" in result.reasoning


def test_json_schema_valid_fails_on_invalid_json_text() -> None:
    schema = {"type": "object"}
    case = _case(ExpectedBehavior(json_schema=schema), text="not json at all")
    result = json_schema_valid(case)
    assert result is not None
    assert result.passed is False
    assert "not valid JSON" in result.reasoning


def test_json_schema_valid_returns_none_when_not_configured() -> None:
    assert json_schema_valid(_case(ExpectedBehavior())) is None


def test_required_tool_called_passes_when_every_required_tool_was_called() -> None:
    case = _case(
        ExpectedBehavior(required_tool_calls=("search", "summarize")),
        tool_calls=(ToolCall("search", {}), ToolCall("summarize", {})),
    )
    result = required_tool_called(case)
    assert result is not None
    assert result.passed is True


def test_required_tool_called_fails_when_a_required_tool_is_missing() -> None:
    case = _case(
        ExpectedBehavior(required_tool_calls=("search", "summarize")),
        tool_calls=(ToolCall("search", {}),),
    )
    result = required_tool_called(case)
    assert result is not None
    assert result.passed is False
    assert "summarize" in result.reasoning


def test_required_tool_called_returns_none_when_not_configured() -> None:
    assert required_tool_called(_case(ExpectedBehavior())) is None


def test_forbidden_tool_called_passes_when_no_forbidden_tool_was_called() -> None:
    case = _case(
        ExpectedBehavior(forbidden_tool_calls=("delete_account",)),
        tool_calls=(ToolCall("search", {}),),
    )
    result = forbidden_tool_called(case)
    assert result is not None
    assert result.passed is True


def test_forbidden_tool_called_fails_when_a_forbidden_tool_was_called() -> None:
    case = _case(
        ExpectedBehavior(forbidden_tool_calls=("delete_account",)),
        tool_calls=(ToolCall("delete_account", {"id": 1}),),
    )
    result = forbidden_tool_called(case)
    assert result is not None
    assert result.passed is False
    assert "delete_account" in result.reasoning


def test_forbidden_tool_called_returns_none_when_not_configured() -> None:
    assert forbidden_tool_called(_case(ExpectedBehavior())) is None


def test_run_deterministic_checks_runs_every_applicable_check_and_skips_the_rest() -> None:
    case = _case(
        ExpectedBehavior(exact_match="hello", required_tool_calls=("search",)),
        text="hello",
        tool_calls=(ToolCall("search", {}),),
    )
    results = run_deterministic_checks(case)
    metric_ids = {r.metric_id for r in results}
    assert metric_ids == {"exact_match", "required_tool_called"}
    assert all(r.passed for r in results)


def test_run_deterministic_checks_with_nothing_configured_returns_nothing() -> None:
    assert run_deterministic_checks(_case(ExpectedBehavior())) == []
