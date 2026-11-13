"""Deterministic checks: exact match, regex, JSON schema validation, required/forbidden
tool calls. Each is a pure function with no model call (AC3: a dataset scored only by
these metrics makes zero judge calls, proven by call count in the integration suite),
so they run first and cheapest, before any judge-based metric even considers the case
(docs/PLAN.md's evaluation methodology)."""

from __future__ import annotations

import json
import re

import jsonschema
from jsonschema.exceptions import SchemaError, ValidationError

from agenteval.evaluators.schema import EvaluationCase, MetricResult


def _result(metric_id: str, passed: bool, reasoning: str) -> MetricResult:
    return MetricResult(
        metric_id=metric_id,
        method="deterministic",
        score=1.0 if passed else 0.0,
        passed=passed,
        reasoning=reasoning,
    )


def exact_match(case: EvaluationCase) -> MetricResult | None:
    """None when the test case does not define an exact_match target: this metric has
    nothing to score, not a failing score of 0."""
    expected = case.expected.exact_match
    if expected is None:
        return None
    passed = case.actual.text.strip() == expected.strip()
    reasoning = "matched exactly" if passed else f"expected {expected!r}, got {case.actual.text!r}"
    return _result("exact_match", passed, reasoning)


def regex_match(case: EvaluationCase) -> MetricResult | None:
    pattern = case.expected.regex
    if pattern is None:
        return None
    passed = re.search(pattern, case.actual.text) is not None
    reasoning = f"matched {pattern!r}" if passed else f"no match for {pattern!r}"
    return _result("regex_match", passed, reasoning)


def json_schema_valid(case: EvaluationCase) -> MetricResult | None:
    schema = case.expected.json_schema
    if schema is None:
        return None
    try:
        instance = json.loads(case.actual.text)
    except (json.JSONDecodeError, ValueError) as exc:
        return _result("json_schema_valid", False, f"output is not valid JSON: {exc}")
    try:
        jsonschema.validate(instance, schema)
    except ValidationError as exc:
        return _result("json_schema_valid", False, f"schema violation: {exc.message}")
    except SchemaError as exc:
        return _result("json_schema_valid", False, f"the test case's own schema is invalid: {exc}")
    return _result("json_schema_valid", True, "valid against the schema")


def required_tool_called(case: EvaluationCase) -> MetricResult | None:
    required = case.expected.required_tool_calls
    if not required:
        return None
    called = {t.name for t in case.actual.tool_calls}
    missing = [name for name in required if name not in called]
    passed = not missing
    reasoning = "every required tool was called" if passed else f"missing calls to {missing}"
    return _result("required_tool_called", passed, reasoning)


def forbidden_tool_called(case: EvaluationCase) -> MetricResult | None:
    forbidden = case.expected.forbidden_tool_calls
    if not forbidden:
        return None
    called = {t.name for t in case.actual.tool_calls}
    violated = [name for name in forbidden if name in called]
    passed = not violated
    reasoning = "no forbidden tool was called" if passed else f"called forbidden tools {violated}"
    return _result("forbidden_tool_called", passed, reasoning)


DETERMINISTIC_CHECKS = (
    exact_match,
    regex_match,
    json_schema_valid,
    required_tool_called,
    forbidden_tool_called,
)

# Every built-in deterministic check's metric_id, matching each function's own _result()
# call above exactly: the evaluations domain uses this to tell a built-in deterministic
# metric apart from a judge metric or a custom one requested by id, with no need to
# import the check functions themselves just to ask "is this one of ours."
DETERMINISTIC_CHECKS_BY_ID = frozenset(
    {
        "exact_match",
        "regex_match",
        "json_schema_valid",
        "required_tool_called",
        "forbidden_tool_called",
    }
)


def run_deterministic_checks(case: EvaluationCase) -> list[MetricResult]:
    """Every deterministic check that applies to this case (one whose expected_behavior
    field is set); a check whose field is unset contributes nothing, not a failure."""
    results = []
    for check in DETERMINISTIC_CHECKS:
        result = check(case)
        if result is not None:
            results.append(result)
    return results
