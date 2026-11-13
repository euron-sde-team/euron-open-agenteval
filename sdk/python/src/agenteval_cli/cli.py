"""agenteval-cli: register an agent, create a dataset, run and inspect evaluations, and
compare runs, against a running AgentEval server. See docs/PLAN.md for the server side.
"""

from __future__ import annotations

import json
import sys

import click
import httpx

from agenteval_cli.config import Credentials, clear_credentials, load_credentials, save_credentials
from agenteval_sdk import AgentEval, AgentEvalApiError, AgentEvalError
from agenteval_sdk.client import DatasetCase


def _make_client(base_url: str, timeout: float) -> httpx.Client:
    """The only place `init` builds a raw httpx.Client (every other command goes
    through AgentEval's own client): tests monkeypatch this to inject a mock transport
    with no real server process, the same seam secretguard-cli's own cli.py uses."""
    return httpx.Client(base_url=base_url, timeout=timeout)


def _require_credentials() -> Credentials:
    creds = load_credentials()
    if creds is None:
        click.echo("agenteval-cli: not signed in, run `agenteval-cli init` first", err=True)
        raise SystemExit(2)
    return creds


def _client(creds: Credentials) -> AgentEval:
    return AgentEval(api_url=creds.api_url, api_key=creds.api_key, org_id=creds.org_id)


@click.group()
@click.version_option(package_name="euron-agenteval")
def main() -> None:
    """Euron Open AgentEval: score how well an AI agent completed a task."""


@main.command()
@click.option(
    "--api-url", prompt="AgentEval server URL", default="http://localhost:5730", show_default=True
)
@click.option("--email", prompt=True)
@click.option("--password", prompt=True, hide_input=True)
def init(api_url: str, email: str, password: str) -> None:
    """Sign in to an AgentEval server and store an API key for later commands."""
    api_url = api_url.rstrip("/")
    try:
        with _make_client(api_url, 10.0) as http:
            resp = http.post("/api/v1/auth/login", json={"email": email, "password": password})
            if resp.status_code != 200:
                click.echo(f"agenteval-cli: sign-in failed ({resp.status_code})", err=True)
                raise SystemExit(1)
            session_token = resp.json()["session_token"]
            auth_header = {"authorization": f"Bearer {session_token}"}

            orgs = http.get("/api/v1/orgs", headers=auth_header).json()
            if not orgs:
                click.echo("agenteval-cli: this account belongs to no organization", err=True)
                raise SystemExit(1)
            org = orgs[0]
            if len(orgs) > 1:
                click.echo(f"Using organization {org['name']!r} (the first of {len(orgs)}).")

            created = http.post(
                f"/api/v1/orgs/{org['id']}/api-keys",
                json={"name": "agenteval-cli"},
                headers=auth_header,
            )
            if created.status_code != 200:
                click.echo(
                    f"agenteval-cli: could not create an API key ({created.status_code}). "
                    "An admin or owner role is required.",
                    err=True,
                )
                raise SystemExit(1)
            api_key = created.json()["plaintext"]
    except httpx.HTTPError as exc:
        click.echo(f"agenteval-cli: could not reach {api_url}: {exc}", err=True)
        raise SystemExit(1) from exc

    save_credentials(Credentials(api_url=api_url, api_key=api_key, org_id=org["id"]))
    click.echo(f"Signed in to {api_url} as {email}, organization {org['name']!r}.")


@main.command()
def logout() -> None:
    """Remove the locally stored API key."""
    clear_credentials()
    click.echo("Credentials cleared.")


@main.group("agent")
def agent_group() -> None:
    """Register or list agents."""


@agent_group.command("add")
@click.option("--name", required=True)
@click.option(
    "--adapter",
    "adapter_type",
    type=click.Choice(["http", "python", "recorded"]),
    required=True,
)
@click.option("--provider", default="other", show_default=True)
@click.option("--endpoint-url", default=None, help="For --adapter http.")
@click.option("--import-path", default=None, help="For --adapter python ('module:callable').")
@click.option("--version-label", default="v1", show_default=True)
def agent_add(
    name: str,
    adapter_type: str,
    provider: str,
    endpoint_url: str | None,
    import_path: str | None,
    version_label: str,
) -> None:
    """Register an agent (and its first version)."""
    creds = _require_credentials()
    config: dict[str, object] = {}
    if adapter_type == "http":
        if not endpoint_url:
            click.echo("agenteval-cli: --adapter http needs --endpoint-url", err=True)
            raise SystemExit(2)
        config = {"endpoint_url": endpoint_url}
    elif adapter_type == "python":
        if not import_path:
            click.echo("agenteval-cli: --adapter python needs --import-path", err=True)
            raise SystemExit(2)
        config = {"import_path": import_path}
    try:
        with _client(creds) as client:
            agent = client.get_or_create_agent(name, adapter_type=adapter_type, provider=provider)
            version = client.get_or_create_agent_version(agent["id"], version_label, config)
    except AgentEvalApiError as exc:
        click.echo(f"agenteval-cli: {exc}", err=True)
        raise SystemExit(1) from exc
    click.echo(f"Agent {agent['name']!r} ({agent['id']}), version {version['label']!r}.")


@main.group("dataset")
def dataset_group() -> None:
    """Create or inspect datasets."""


@dataset_group.command("create")
@click.option("--name", required=True)
@click.option(
    "--file",
    "cases_file",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="A JSON file: a list of {input, expected_behavior, tags} objects.",
)
def dataset_create(name: str, cases_file: str) -> None:
    """Create a dataset from a JSON file of test cases."""
    creds = _require_credentials()
    with open(cases_file, encoding="utf-8") as f:
        raw_cases = json.load(f)
    test_cases = [
        DatasetCase(
            input=c.get("input", {}),
            expected_description=c.get("expected_behavior", {}).get("description", ""),
            exact_match=c.get("expected_behavior", {}).get("exact_match"),
            regex=c.get("expected_behavior", {}).get("regex"),
            json_schema=c.get("expected_behavior", {}).get("json_schema"),
            required_tool_calls=tuple(
                c.get("expected_behavior", {}).get("required_tool_calls", [])
            ),
            forbidden_tool_calls=tuple(
                c.get("expected_behavior", {}).get("forbidden_tool_calls", [])
            ),
            tags=tuple(c.get("tags", [])),
        )
        for c in raw_cases
    ]
    try:
        with _client(creds) as client:
            dataset = client.get_or_create_dataset(name, test_cases)
    except AgentEvalApiError as exc:
        click.echo(f"agenteval-cli: {exc}", err=True)
        raise SystemExit(1) from exc
    click.echo(
        f"Dataset {dataset['name']!r} ({dataset['id']}), {dataset['test_case_count']} cases."
    )


@main.group("evaluate")
def evaluate_group() -> None:
    """Run evaluations."""


@evaluate_group.command("run")
@click.option("--agent-version-id", required=True)
@click.option("--dataset-version-id", required=True)
@click.option("--metric", "metric_ids", multiple=True, required=True)
@click.option("--timeout", "timeout_s", type=float, default=120.0, show_default=True)
def evaluate_run(
    agent_version_id: str, dataset_version_id: str, metric_ids: tuple[str, ...], timeout_s: float
) -> None:
    """Queue an evaluation run and wait for it to finish."""
    creds = _require_credentials()
    try:
        with _client(creds) as client:
            run = client.queue_run(agent_version_id, dataset_version_id, list(metric_ids))
            click.echo(f"Run {run['id']} queued, waiting...")
            result = client.wait_for_run(run["id"], timeout_s=timeout_s)
    except AgentEvalError as exc:
        click.echo(f"agenteval-cli: {exc}", err=True)
        raise SystemExit(1) from exc
    click.echo(result.summary())


@main.command()
@click.option("--baseline-run-id", required=True)
@click.option("--candidate-run-id", required=True)
@click.option("--regression-threshold", type=float, default=0.05, show_default=True)
def compare(baseline_run_id: str, candidate_run_id: str, regression_threshold: float) -> None:
    """Compare two evaluation runs (AC8/AC9)."""
    creds = _require_credentials()
    try:
        with _client(creds) as client:
            result = client.compare(
                baseline_run_id, candidate_run_id, regression_threshold=regression_threshold
            )
    except AgentEvalApiError as exc:
        click.echo(f"agenteval-cli: {exc}", err=True)
        raise SystemExit(1) from exc
    click.echo(result.summary())
    if result.has_regression:
        raise SystemExit(1)


@main.group("report")
def report_group() -> None:
    """Export a run's results."""


@report_group.command("export")
@click.option("--run-id", required=True)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "csv"]),
    default="json",
    show_default=True,
)
def report_export(run_id: str, output_format: str) -> None:
    """Export one run's per-test-case results. No dedicated server-side export
    endpoint exists yet (docs/PLAN.md's roadmap); this builds the export from the same
    GET .../evaluation-runs/{run_id} the dashboard itself calls, honestly, rather than
    inventing a server route that is not really there."""
    creds = _require_credentials()
    try:
        with _client(creds) as client:
            data = client.get_run(run_id)
    except AgentEvalApiError as exc:
        click.echo(f"agenteval-cli: {exc}", err=True)
        raise SystemExit(1) from exc

    if output_format == "json":
        click.echo(json.dumps(data, indent=2))
        return

    results = data.get("results", [])
    click.echo("test_case_id,metric_id,method,score,passed")
    for r in results:
        click.echo(f"{r['test_case_id']},{r['metric_id']},{r['method']},{r['score']},{r['passed']}")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
