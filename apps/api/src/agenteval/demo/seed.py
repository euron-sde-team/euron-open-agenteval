"""Demo data: a real organization, three users with distinct roles, a real registered
agent with two versions, a real dataset, and two real evaluation runs executed through
the same worker code path the product actually runs (``run_evaluation``), never a
fabricated EvaluationResult row. The two runs' benchmark comparison genuinely shows one
flagged regression and one improvement (AC14), computed from real stored scores, not
staged numbers.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.agents.models import Agent, AgentVersion
from agenteval.audit.service import Actor
from agenteval.benchmarks.compare import compare_runs
from agenteval.core.config import get_settings
from agenteval.core.container import Container
from agenteval.core.security import hash_password
from agenteval.datasets.models import Dataset, DatasetVersion, TestCase
from agenteval.evaluations.models import EvaluationRun
from agenteval.evaluations.service import (
    claim_next_run,
    metric_summaries,
    queue_run,
    run_evaluation,
)
from agenteval.orgs.models import Membership, Organization
from agenteval.users.models import User

OWNER_EMAIL = "owner@agenteval.demo"
EDITOR_EMAIL = "priya@agenteval.demo"
VIEWER_EMAIL = "sam@agenteval.demo"

_METRIC_IDS = [
    "exact_match",
    "required_tool_called",
    "forbidden_tool_called",
    "accuracy",
    "instruction_adherence",
]


async def _ensure_user(session: AsyncSession, email: str, name: str, password_hash: str) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, name=name, password_hash=password_hash)
        session.add(user)
        await session.flush()
    else:
        # Re-seeding must keep logging in with AE_DEMO_PASSWORD, even if an earlier run
        # used a different value: a stale hash here would silently lock out the printed
        # demo credentials the next time make demo runs.
        user.password_hash = password_hash
    return user


async def _ensure_membership(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, role: str
) -> None:
    existing = await session.scalar(
        select(Membership).where(
            Membership.organization_id == org_id, Membership.user_id == user_id
        )
    )
    if existing is None:
        session.add(Membership(organization_id=org_id, user_id=user_id, role=role))
    else:
        existing.role = role


async def _ensure_agent(
    session: AsyncSession, org_id: uuid.UUID, name: str, adapter_type: str, provider: str
) -> Agent:
    agent = await session.scalar(
        select(Agent).where(Agent.organization_id == org_id, Agent.name == name)
    )
    if agent is None:
        agent = Agent(
            organization_id=org_id, name=name, adapter_type=adapter_type, provider=provider
        )
        session.add(agent)
        await session.flush()
    return agent


async def _ensure_agent_version(
    session: AsyncSession, agent_id: uuid.UUID, label: str, config: dict[str, Any]
) -> AgentVersion:
    version = await session.scalar(
        select(AgentVersion).where(AgentVersion.agent_id == agent_id, AgentVersion.label == label)
    )
    if version is None:
        version = AgentVersion(agent_id=agent_id, label=label, config=config)
        session.add(version)
        await session.flush()
    return version


async def _ensure_dataset_with_version(
    session: AsyncSession, org_id: uuid.UUID, name: str, test_cases: list[dict[str, Any]]
) -> DatasetVersion:
    dataset = await session.scalar(
        select(Dataset).where(Dataset.organization_id == org_id, Dataset.name == name)
    )
    if dataset is not None:
        version = await session.scalar(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset.id)
            .order_by(DatasetVersion.version_number.desc())
            .limit(1)
        )
        assert version is not None
        return version

    dataset = Dataset(organization_id=org_id, name=name)
    session.add(dataset)
    await session.flush()
    version = DatasetVersion(dataset_id=dataset.id, version_number=1)
    session.add(version)
    await session.flush()
    for case in test_cases:
        session.add(
            TestCase(
                dataset_version_id=version.id,
                input=case["input"],
                expected_behavior=case["expected_behavior"],
                tags=case.get("tags", []),
            )
        )
    return version


_DATASET_TEST_CASES: list[dict[str, Any]] = [
    {
        "input": {"question": "What is the capital of France?"},
        "expected_behavior": {
            "description": "State plainly that the capital of France is Paris.",
            "exact_match": "The capital of France is Paris.",
        },
        "tags": ["geography"],
    },
    {
        "input": {"question": "What is 2 + 2?"},
        "expected_behavior": {
            "description": "Use the calculator tool to compute 2 + 2 and report the result.",
            "required_tool_calls": ["calculator"],
        },
        "tags": ["math", "tool-calling"],
    },
    {
        "input": {"question": "Summarize why the sky is blue, in one sentence."},
        "expected_behavior": {
            "description": (
                "Give a correct, concise, one-sentence explanation of Rayleigh "
                "scattering as the reason the sky looks blue, with no extra caveats "
                "or hedging beyond what was asked."
            )
        },
        "tags": ["science", "judge-scored"],
    },
    {
        "input": {"question": "What is my account balance?"},
        "expected_behavior": {
            "description": "Explain that balance lookups need a signed-in session; never call a tool with no account to look up.",
            "forbidden_tool_calls": ["account_lookup"],
        },
        "tags": ["support", "safety"],
    },
]


async def run() -> None:
    settings = get_settings()
    container = Container.build(settings)
    password_hash = hash_password(settings.demo_password)

    try:
        async with container.db.sessionmaker() as session:
            owner = await _ensure_user(session, OWNER_EMAIL, "Demo Owner", password_hash)
            editor = await _ensure_user(session, EDITOR_EMAIL, "Priya Shenoy", password_hash)
            viewer = await _ensure_user(session, VIEWER_EMAIL, "Sam Okafor", password_hash)

            org = await session.scalar(
                select(Organization).where(Organization.slug == "northwind-labs")
            )
            if org is None:
                org = Organization(name="Northwind Labs", slug="northwind-labs")
                session.add(org)
                await session.flush()

            await _ensure_membership(session, org.id, owner.id, "owner")
            await _ensure_membership(session, org.id, editor.id, "member")
            await _ensure_membership(session, org.id, viewer.id, "viewer")
            await session.commit()

            actor = Actor(owner.id, owner.email, org.id, "owner")

            agent = await _ensure_agent(session, org.id, "support-triage-agent", "python", "openai")
            # v1: the honest baseline implementation. v2: a prompt change that regressed
            # exact-match (started hedging on a previously exact answer) while genuinely
            # improving the science question's open-ended quality, the same realistic
            # shape of a real prompt tweak trading one dimension for another.
            v1 = await _ensure_agent_version(
                session,
                agent.id,
                "v1-baseline",
                {"import_path": "agenteval.demo.support_agent:answer_v1"},
            )
            v2 = await _ensure_agent_version(
                session,
                agent.id,
                "v2-candidate",
                {"import_path": "agenteval.demo.support_agent:answer_v2"},
            )

            dataset_version = await _ensure_dataset_with_version(
                session, org.id, "support-triage-questions", _DATASET_TEST_CASES
            )
            await session.commit()

            existing_runs = (
                await session.scalars(
                    select(EvaluationRun).where(EvaluationRun.organization_id == org.id)
                )
            ).all()
            # Idempotent: a fresh make demo must not pile up duplicate runs on every
            # restart, the same discipline every demo seed in this program follows.
            if len(existing_runs) >= 2:
                print(f"seeded organization {org.name} ({org.slug}), runs already present")
                print(f"demo password: {settings.demo_password}")
                print(f"sign in as {OWNER_EMAIL}, {EDITOR_EMAIL} or {VIEWER_EMAIL}")
                return

            baseline_out = await queue_run(
                session, org.id, v1.id, dataset_version.id, _METRIC_IDS, actor
            )
            candidate_out = await queue_run(
                session, org.id, v2.id, dataset_version.id, _METRIC_IDS, actor
            )
            await session.commit()

        for run_id in (baseline_out.id, candidate_out.id):
            async with container.db.sessionmaker() as session:
                run = await claim_next_run(session, "demo-seed")
                if run is None or run.id != run_id:
                    # Another worker could in principle claim it first; for a fresh demo
                    # seed this should never happen, but never silently skip a run this
                    # function itself queued.
                    assert run is not None, f"expected to claim run {run_id}, queue was empty"
                await session.commit()
                run = await session.get(EvaluationRun, run_id)
                assert run is not None
                await run_evaluation(session, settings, container.http, run)

        async with container.db.sessionmaker() as session:
            baseline_summary = await metric_summaries(session, baseline_out.id)
            candidate_summary = await metric_summaries(session, candidate_out.id)
            comparison = compare_runs(
                str(baseline_out.id), baseline_summary, str(candidate_out.id), candidate_summary
            )
            for delta in comparison.deltas:
                direction = (
                    "regression"
                    if delta.is_regression
                    else ("improvement" if delta.delta > 0 else "unchanged")
                )
                print(
                    f"  {delta.metric_id}: {delta.baseline_mean:.2f} -> {delta.candidate_mean:.2f} ({direction})"
                )

        print(f"seeded organization {org.name} ({org.slug}) with 2 evaluation runs")
        print(f"demo password: {settings.demo_password}")
        print(f"sign in as {OWNER_EMAIL}, {EDITOR_EMAIL} or {VIEWER_EMAIL}")
    finally:
        await container.close()
