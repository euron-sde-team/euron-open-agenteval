"""CliRunner-driven tests of agenteval-cli's entry point. ``init``/``logout`` are tested
against an httpx.MockTransport standing in for the real API (the same seam
secretguard-cli's own test_cli.py uses); the other commands are tested by monkeypatching
AgentEval's client methods directly, since their job is thin argument plumbing onto a
client already covered by test_client.py, not request/response shapes of their own.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from click.testing import CliRunner

from agenteval_cli import cli as cli_module
from agenteval_cli.cli import main
from agenteval_cli.config import Credentials, config_dir, save_credentials
from agenteval_sdk.models import BenchmarkComparisonResult, EvaluationResult, MetricResultView


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _isolated_config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))


def _mock_client_factory(handler):
    def factory(base_url: str, timeout: float) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(handler), base_url=base_url)

    return factory


def test_init_saves_credentials_on_success(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"session_token": "sess-abc"})
        if request.url.path == "/api/v1/orgs":
            assert request.headers["authorization"] == "Bearer sess-abc"
            return httpx.Response(200, json=[{"id": "org-1", "name": "Acme"}])
        if request.url.path == "/api/v1/orgs/org-1/api-keys":
            return httpx.Response(200, json={"plaintext": "aek_test_xyz"})
        raise AssertionError(f"unexpected request to {request.url.path}")

    monkeypatch.setattr(cli_module, "_make_client", _mock_client_factory(handler))

    result = runner.invoke(
        main,
        [
            "init",
            "--api-url",
            "http://fake-agenteval",
            "--email",
            "owner@example.test",
            "--password",
            "whatever",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Acme" in result.output
    saved = json.loads((config_dir() / "credentials.json").read_text())
    assert saved == {
        "api_url": "http://fake-agenteval",
        "api_key": "aek_test_xyz",
        "org_id": "org-1",
    }


def test_init_with_bad_credentials_fails_cleanly(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "nope"})

    monkeypatch.setattr(cli_module, "_make_client", _mock_client_factory(handler))

    result = runner.invoke(
        main,
        [
            "init",
            "--api-url",
            "http://fake-agenteval",
            "--email",
            "x@example.test",
            "--password",
            "x",
        ],
    )

    assert result.exit_code == 1
    assert "sign-in failed" in result.output
    assert not (config_dir() / "credentials.json").is_file()


def test_logout_clears_saved_credentials(runner: CliRunner) -> None:
    save_credentials(Credentials(api_url="http://x", api_key="aek_x", org_id="o"))
    assert (config_dir() / "credentials.json").is_file()

    result = runner.invoke(main, ["logout"])

    assert result.exit_code == 0
    assert not (config_dir() / "credentials.json").is_file()


def test_agent_add_without_being_signed_in_exits_two(runner: CliRunner) -> None:
    result = runner.invoke(main, ["agent", "add", "--name", "x", "--adapter", "recorded"])
    assert result.exit_code == 2
    assert "not signed in" in result.output


def test_agent_add_http_requires_endpoint_url(runner: CliRunner) -> None:
    save_credentials(Credentials(api_url="http://x", api_key="aek_x", org_id="o"))
    result = runner.invoke(main, ["agent", "add", "--name", "x", "--adapter", "http"])
    assert result.exit_code == 2
    assert "--endpoint-url" in result.output


def test_agent_add_calls_the_client_with_the_right_adapter_config(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_credentials(Credentials(api_url="http://x", api_key="aek_x", org_id="org-1"))
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.get_or_create_agent.return_value = {"id": "agent-1", "name": "my-agent"}
    mock_client.get_or_create_agent_version.return_value = {"id": "av-1", "label": "v1"}
    monkeypatch.setattr(cli_module, "_client", lambda creds: mock_client)

    result = runner.invoke(
        main,
        [
            "agent",
            "add",
            "--name",
            "my-agent",
            "--adapter",
            "http",
            "--endpoint-url",
            "http://my-agent.example/run",
        ],
    )

    assert result.exit_code == 0, result.output
    mock_client.get_or_create_agent.assert_called_once_with(
        "my-agent", adapter_type="http", provider="other"
    )
    mock_client.get_or_create_agent_version.assert_called_once_with(
        "agent-1", "v1", {"endpoint_url": "http://my-agent.example/run"}
    )


def test_dataset_create_reads_test_cases_from_a_json_file(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    save_credentials(Credentials(api_url="http://x", api_key="aek_x", org_id="org-1"))
    cases_file = tmp_path / "cases.json"
    cases_file.write_text(
        json.dumps(
            [
                {
                    "input": {"q": "hi"},
                    "expected_behavior": {
                        "exact_match": "hello",
                        "required_tool_calls": ["lookup"],
                    },
                    "tags": ["smoke"],
                }
            ]
        )
    )
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.get_or_create_dataset.return_value = {
        "id": "ds-1",
        "name": "ds",
        "test_case_count": 1,
    }
    monkeypatch.setattr(cli_module, "_client", lambda creds: mock_client)

    result = runner.invoke(main, ["dataset", "create", "--name", "ds", "--file", str(cases_file)])

    assert result.exit_code == 0, result.output
    args = mock_client.get_or_create_dataset.call_args
    assert args[0][0] == "ds"
    test_case = args[0][1][0]
    assert test_case.input == {"q": "hi"}
    assert test_case.exact_match == "hello"
    assert test_case.required_tool_calls == ("lookup",)
    assert test_case.tags == ("smoke",)


def test_evaluate_run_prints_the_summary_and_exits_zero(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_credentials(Credentials(api_url="http://x", api_key="aek_x", org_id="org-1"))
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.queue_run.return_value = {"id": "run-1", "status": "queued"}
    mock_client.wait_for_run.return_value = EvaluationResult(
        run_id="run-1",
        status="completed",
        results=(
            MetricResultView(
                metric_id="exact_match",
                method="deterministic",
                score=1.0,
                passed=True,
                reasoning="",
                same_family_warning=False,
                test_case_id="case-1",
            ),
        ),
    )
    monkeypatch.setattr(cli_module, "_client", lambda creds: mock_client)

    result = runner.invoke(
        main,
        [
            "evaluate",
            "run",
            "--agent-version-id",
            "av-1",
            "--dataset-version-id",
            "dv-1",
            "--metric",
            "exact_match",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "exact_match: 1.00" in result.output
    mock_client.queue_run.assert_called_once_with("av-1", "dv-1", ["exact_match"])


def test_compare_exits_one_when_a_regression_is_flagged(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_credentials(Credentials(api_url="http://x", api_key="aek_x", org_id="org-1"))
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.compare.return_value = BenchmarkComparisonResult(
        baseline_run_id="run-a", candidate_run_id="run-b", deltas=(), has_regression=True
    )
    monkeypatch.setattr(cli_module, "_client", lambda creds: mock_client)

    result = runner.invoke(
        main,
        ["compare", "--baseline-run-id", "run-a", "--candidate-run-id", "run-b"],
    )

    assert result.exit_code == 1


def test_report_export_json_prints_the_raw_run_detail(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_credentials(Credentials(api_url="http://x", api_key="aek_x", org_id="org-1"))
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.get_run.return_value = {"id": "run-1", "status": "completed", "results": []}
    monkeypatch.setattr(cli_module, "_client", lambda creds: mock_client)

    result = runner.invoke(main, ["report", "export", "--run-id", "run-1"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["id"] == "run-1"


def test_report_export_csv_renders_one_row_per_result(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_credentials(Credentials(api_url="http://x", api_key="aek_x", org_id="org-1"))
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.get_run.return_value = {
        "id": "run-1",
        "status": "completed",
        "results": [
            {
                "test_case_id": "case-1",
                "metric_id": "exact_match",
                "method": "deterministic",
                "score": 1.0,
                "passed": True,
            }
        ],
    }
    monkeypatch.setattr(cli_module, "_client", lambda creds: mock_client)

    result = runner.invoke(main, ["report", "export", "--run-id", "run-1", "--format", "csv"])

    assert result.exit_code == 0, result.output
    assert "case-1,exact_match,deterministic,1.0,True" in result.output
