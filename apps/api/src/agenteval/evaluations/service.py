"""Evaluation run orchestration: queuing, claiming (``FOR UPDATE SKIP LOCKED``, the same
pattern every worker in this program uses), and running a dataset version against an
agent version. ``run_evaluation`` is the one place deterministic checks, judge-based
metrics, trace capture and result storage all come together; the worker calls it after
claiming a run, and nothing else writes an EvaluationResult row."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.agents.adapters import AdapterError, build_adapter
from agenteval.agents.models import Agent, AgentVersion
from agenteval.audit.service import Actor, audit
from agenteval.core.config import Settings
from agenteval.core.errors import NotFoundError
from agenteval.datasets.service import ResolvedTestCase, resolve_test_cases
from agenteval.evaluations.models import EvaluationResult, EvaluationRun, JudgeCall, Metric
from agenteval.evaluations.schemas import (
    EvaluationResultOut,
    EvaluationRunDetailOut,
    EvaluationRunOut,
    JudgeCallOut,
)
from agenteval.evaluators.deterministic import DETERMINISTIC_CHECKS_BY_ID, run_deterministic_checks
from agenteval.evaluators.judge import (
    JUDGE_METRICS,
    JudgeConfig,
    JudgeProvider,
    run_custom_judge_metric,
)
from agenteval.evaluators.mock_judge import MockJudgeProvider
from agenteval.evaluators.providers import AnthropicCompatibleJudge, OpenAICompatibleJudge
from agenteval.evaluators.schema import (
    AgentOutput,
    EvaluationCase,
    ExpectedBehavior,
    MetricResult,
    RunMetricSummary,
)
from agenteval.traces import service as traces_service
from agenteval.traces.schemas import SpanIn


def _run_out(run: EvaluationRun) -> EvaluationRunOut:
    return EvaluationRunOut(
        id=run.id,
        organization_id=run.organization_id,
        agent_version_id=run.agent_version_id,
        dataset_version_id=run.dataset_version_id,
        status=run.status,
        metric_ids=run.metric_ids,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error=run.error,
        created_at=run.created_at,
    )


def _result_out(result: EvaluationResult) -> EvaluationResultOut:
    return EvaluationResultOut(
        id=result.id,
        test_case_id=result.test_case_id,
        trace_id=result.trace_id,
        metric_id=result.metric_id,
        method=result.method,
        score=result.score,
        passed=result.passed,
        reasoning=result.reasoning,
        rubric_version=result.rubric_version,
        judge_model=result.judge_model,
        judge_provider=result.judge_provider,
        same_family_warning=result.same_family_warning,
        created_at=result.created_at,
    )


def _expected_behavior_from_json(data: dict[str, object]) -> ExpectedBehavior:
    return ExpectedBehavior(
        description=str(data.get("description", "")),
        exact_match=data.get("exact_match"),  # type: ignore[arg-type]
        regex=data.get("regex"),  # type: ignore[arg-type]
        json_schema=data.get("json_schema"),  # type: ignore[arg-type]
        required_tool_calls=tuple(data.get("required_tool_calls", []) or []),  # type: ignore[arg-type]
        forbidden_tool_calls=tuple(data.get("forbidden_tool_calls", []) or []),  # type: ignore[arg-type]
    )


def new_otel_trace_id() -> str:
    """A real 32-hex-char (16-byte) OpenTelemetry trace id, generated locally for a run
    the worker itself invoked (never an externally-supplied one, which would come in
    through the ingestion endpoint instead). uuid4().hex is already exactly 32 hex
    characters, the OTel trace id's own byte length, with no padding needed."""
    return uuid.uuid4().hex


async def queue_run(
    session: AsyncSession,
    organization_id: uuid.UUID,
    agent_version_id: uuid.UUID,
    dataset_version_id: uuid.UUID,
    metric_ids: list[str],
    actor: Actor,
) -> EvaluationRunOut:
    run = EvaluationRun(
        organization_id=organization_id,
        agent_version_id=agent_version_id,
        dataset_version_id=dataset_version_id,
        metric_ids=metric_ids,
    )
    session.add(run)
    await session.flush()
    audit(session, actor, "evaluation_run.queued", "evaluation_run", run.id, metric_ids=metric_ids)
    await session.commit()
    return _run_out(run)


async def claim_next_run(session: AsyncSession, worker_id: str) -> EvaluationRun | None:
    """Claim one queued evaluation run for this worker, or None if the queue is empty.
    Flushes, not commits: the caller's own transaction boundary decides when the row
    lock releases (the exact pattern secretguard's claim_next_scan uses)."""
    run = await session.scalar(
        select(EvaluationRun)
        .where(EvaluationRun.status == "queued")
        .order_by(EvaluationRun.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if run is None:
        return None
    run.status = "running"
    run.started_at = datetime.now(UTC)
    run.claimed_by = worker_id
    run.claimed_at = datetime.now(UTC)
    await session.flush()
    return run


def _build_judge(
    settings: Settings, http: httpx.AsyncClient, agent_provider: str
) -> tuple[JudgeProvider, JudgeConfig]:
    if settings.mock_ai_url:
        return MockJudgeProvider(), JudgeConfig(provider="mock", model="mock-judge")
    # Cross-family default (docs/PLAN.md's evaluation methodology): judge the agent with
    # a DIFFERENT provider family than the one under test, as the structural mitigation
    # for self-preference bias research supports.
    judge_provider = "anthropic" if agent_provider == "openai" else "openai"
    base_url = settings.judge_base_url(judge_provider)
    if judge_provider == "anthropic":
        return AnthropicCompatibleJudge(http, base_url, "judge-key"), JudgeConfig(
            provider="anthropic", model="claude-judge"
        )
    return OpenAICompatibleJudge(http, base_url, "judge-key", "openai"), JudgeConfig(
        provider="openai", model="gpt-judge"
    )


async def _custom_metrics_by_id(
    session: AsyncSession, organization_id: uuid.UUID, metric_ids: list[str]
) -> dict[str, Metric]:
    unknown = [
        m for m in metric_ids if m not in JUDGE_METRICS and m not in DETERMINISTIC_CHECKS_BY_ID
    ]
    if not unknown:
        return {}
    rows = await session.scalars(
        select(Metric).where(
            Metric.metric_id.in_(unknown),
            (Metric.organization_id == organization_id) | (Metric.organization_id.is_(None)),
            Metric.enabled.is_(True),
        )
    )
    return {m.metric_id: m for m in rows}


def build_invocation_spans(
    output: AgentOutput, started_at: datetime, ended_at: datetime
) -> list[SpanIn]:
    """A minimal OpenTelemetry GenAI-shaped span list for one agent invocation: one chat
    span, plus one execute_tool child span per tool call the agent made, using the real
    gen_ai.* attribute namespace (never a bespoke one). Pure and database-free, so the
    exact attribute mapping a worker run produces is directly unit-testable; the async
    wrapper below is the only part that touches storage."""
    agent_span_id = uuid.uuid4().hex[:16]
    spans = [
        SpanIn(
            otel_span_id=agent_span_id,
            name="invoke_agent",
            gen_ai_operation_name="chat",
            started_at=started_at,
            ended_at=ended_at,
            status="ok",
            attributes={
                "gen_ai.response.text": output.text,
                "gen_ai.provider.name": output.provider,
            },
        )
    ]
    for tool_call in output.tool_calls:
        spans.append(
            SpanIn(
                otel_span_id=uuid.uuid4().hex[:16],
                parent_otel_span_id=agent_span_id,
                name=f"execute_tool.{tool_call.name}",
                gen_ai_operation_name="execute_tool",
                started_at=started_at,
                ended_at=ended_at,
                status="ok",
                attributes={
                    "gen_ai.tool.name": tool_call.name,
                    "gen_ai.tool.call.arguments": tool_call.arguments,
                },
            )
        )
    return spans


async def _record_invocation_trace(
    session: AsyncSession,
    organization_id: uuid.UUID,
    run_id: uuid.UUID,
    test_case_id: uuid.UUID,
    output: AgentOutput,
    started_at: datetime,
    ended_at: datetime,
) -> uuid.UUID:
    """Builds the invocation's spans and ingests them through the same path an external
    OTLP exporter would use, so a worker run's trace and an SDK-sent trace are stored
    identically. Returns the new Trace row's id."""
    spans = build_invocation_spans(output, started_at, ended_at)
    trace_out = await traces_service.ingest_trace(
        session,
        organization_id,
        new_otel_trace_id(),
        spans,
        evaluation_run_id=run_id,
        test_case_id=test_case_id,
    )
    return trace_out.id


async def _store_result(
    session: AsyncSession,
    run_id: uuid.UUID,
    test_case_id: uuid.UUID,
    trace_id: uuid.UUID | None,
    result: MetricResult,
) -> uuid.UUID:
    row = EvaluationResult(
        evaluation_run_id=run_id,
        test_case_id=test_case_id,
        trace_id=trace_id,
        metric_id=result.metric_id,
        method=result.method,
        score=result.score,
        passed=result.passed,
        reasoning=result.reasoning,
        rubric_version=result.rubric_version,
        judge_model=result.judge_model,
        judge_provider=result.judge_provider,
        same_family_warning=result.same_family_warning,
        created_at=traces_service.utcnow(),
    )
    session.add(row)
    await session.flush()
    if result.raw_judge_response is not None:
        session.add(
            JudgeCall(
                evaluation_result_id=row.id,
                prompt=result.judge_prompt or f"[{result.metric_id}]",
                raw_response=result.raw_judge_response,
                created_at=traces_service.utcnow(),
            )
        )
    return row.id


async def _score_one_test_case(
    session: AsyncSession,
    run: EvaluationRun,
    test_case: ResolvedTestCase,
    output: AgentOutput,
    trace_id: uuid.UUID,
    judge: JudgeProvider,
    judge_config: JudgeConfig,
    custom_metrics: dict[str, Metric],
) -> None:
    expected = _expected_behavior_from_json(test_case.expected_behavior)
    evaluation_case = EvaluationCase(
        test_case_id=str(test_case.id), expected=expected, actual=output
    )

    deterministic_results = {
        r.metric_id: r
        for r in run_deterministic_checks(evaluation_case)
        if r.metric_id in run.metric_ids
    }
    for result in deterministic_results.values():
        await _store_result(session, run.id, test_case.id, trace_id, result)

    for metric_id in run.metric_ids:
        if metric_id in deterministic_results or metric_id in DETERMINISTIC_CHECKS_BY_ID:
            continue
        if metric_id in JUDGE_METRICS:
            judge_fn = JUDGE_METRICS[metric_id]
            result = await judge_fn(evaluation_case, judge, judge_config)
            await _store_result(session, run.id, test_case.id, trace_id, result)
        elif metric_id in custom_metrics:
            metric = custom_metrics[metric_id]
            rubric = str(metric.config.get("rubric", ""))
            result = await run_custom_judge_metric(
                metric_id,
                rubric,
                metric.rubric_version or "custom",
                evaluation_case,
                judge,
                judge_config,
            )
            await _store_result(session, run.id, test_case.id, trace_id, result)
        # An unknown, un-configured metric id is silently skipped for this test case: it
        # was requested but this organization has no such metric registered. The API
        # layer validates metric_ids exist at queue time; this path is defensive.


async def run_evaluation(
    session: AsyncSession, settings: Settings, http: httpx.AsyncClient, run: EvaluationRun
) -> EvaluationRunOut:
    """Run every test case in the run's dataset version against the run's agent
    version, scoring each with every requested metric, and write one EvaluationResult
    per test case per metric. Mutates and returns the given run; commits once per test
    case, so progress is visible incrementally (the same pattern secretguard's own
    run_scan uses)."""
    agent_version = await session.get(AgentVersion, run.agent_version_id)
    if agent_version is None:
        raise NotFoundError("Agent version not found")
    agent = await session.get(Agent, agent_version.agent_id)
    if agent is None:
        raise NotFoundError("Agent not found")

    test_cases = await resolve_test_cases(session, run.dataset_version_id)
    judge, judge_config = _build_judge(settings, http, agent.provider)
    custom_metrics = await _custom_metrics_by_id(session, run.organization_id, run.metric_ids)

    try:
        for test_case in test_cases:
            adapter = build_adapter(agent, agent_version, http)
            started_at = traces_service.utcnow()
            try:
                output = await adapter.invoke(test_case.input)
            except AdapterError as exc:
                run.status = "failed"
                run.error = str(exc)
                run.finished_at = traces_service.utcnow()
                await session.commit()
                return _run_out(run)
            ended_at = traces_service.utcnow()

            trace_id = await _record_invocation_trace(
                session, run.organization_id, run.id, test_case.id, output, started_at, ended_at
            )
            await _score_one_test_case(
                session, run, test_case, output, trace_id, judge, judge_config, custom_metrics
            )
            await session.commit()

        run.status = "completed"
        run.finished_at = traces_service.utcnow()
        await session.commit()
    except Exception as exc:
        # A failed flush or commit leaves the session's transaction unusable (any
        # further operation raises PendingRollbackError) until it is explicitly rolled
        # back; only then can this run's own failure be recorded in a fresh
        # transaction. Without the rollback here, this handler's own commit silently
        # failed too and left the run stuck "running" forever, exactly what it claims
        # to prevent (caught by actually running an evaluation against a real
        # database, not by any unit test).
        await session.rollback()
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = traces_service.utcnow()
        session.add(run)
        await session.commit()
        raise
    return _run_out(run)


async def get_run(
    session: AsyncSession, organization_id: uuid.UUID, run_id: uuid.UUID
) -> EvaluationRun:
    run = await session.get(EvaluationRun, run_id)
    if run is None or run.organization_id != organization_id:
        raise NotFoundError("Evaluation run not found")
    return run


async def get_run_detail(
    session: AsyncSession, organization_id: uuid.UUID, run_id: uuid.UUID
) -> EvaluationRunDetailOut:
    run = await get_run(session, organization_id, run_id)
    results = await session.scalars(
        select(EvaluationResult)
        .where(EvaluationResult.evaluation_run_id == run.id)
        .order_by(EvaluationResult.created_at)
    )
    out = _run_out(run)
    return EvaluationRunDetailOut(**out.model_dump(), results=[_result_out(r) for r in results])


async def list_runs(session: AsyncSession, organization_id: uuid.UUID) -> list[EvaluationRunOut]:
    runs = await session.scalars(
        select(EvaluationRun)
        .where(EvaluationRun.organization_id == organization_id)
        .order_by(EvaluationRun.created_at.desc())
    )
    return [_run_out(r) for r in runs]


async def metric_summaries(session: AsyncSession, run_id: uuid.UUID) -> list[RunMetricSummary]:
    """Per-metric mean score, pass rate and case count for a completed run: the unit
    benchmarks.compare.compare_runs computes a delta from (AC8)."""
    rows = (
        await session.execute(
            select(
                EvaluationResult.metric_id,
                func.avg(EvaluationResult.score),
                func.avg(EvaluationResult.passed.cast(Integer)),
                func.count(),
            )
            .where(EvaluationResult.evaluation_run_id == run_id)
            .group_by(EvaluationResult.metric_id)
        )
    ).all()
    return [
        RunMetricSummary(
            metric_id=metric_id, mean_score=float(mean), pass_rate=float(rate), case_count=count
        )
        for metric_id, mean, rate, count in rows
    ]


async def get_judge_call(
    session: AsyncSession, organization_id: uuid.UUID, evaluation_result_id: uuid.UUID
) -> JudgeCallOut:
    result = await session.get(EvaluationResult, evaluation_result_id)
    if result is None:
        raise NotFoundError("Evaluation result not found")
    await get_run(session, organization_id, result.evaluation_run_id)  # raises if cross-org
    judge_call = await session.scalar(
        select(JudgeCall).where(JudgeCall.evaluation_result_id == evaluation_result_id)
    )
    if judge_call is None:
        raise NotFoundError("No judge call is stored for this result")
    return JudgeCallOut(
        id=judge_call.id,
        prompt=judge_call.prompt,
        raw_response=judge_call.raw_response,
        created_at=judge_call.created_at,
    )
