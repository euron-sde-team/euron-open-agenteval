# agenteval (API, worker and evaluation engine)

The Python package behind Euron Open AgentEval: the dashboard and admin API (`/api/v1`),
the background worker that runs evaluations, the shared evaluation engine library
(`agenteval.evaluators`, `agenteval.benchmarks`) imported by the API, the worker and the
SDK alike, and the deterministic mock AI/LLM service used by the demo and the test suites.

```bash
uv sync
uv run agenteval --help          # serve, worker, migrate, openapi, create-owner, seed-demo
uv run pytest tests/unit         # no database, no network
make -C ../.. test-integration   # real Postgres and Redis
```

Layout and conventions: [CONTRIBUTING.md](../../CONTRIBUTING.md) and
[docs/PLAN.md](../../docs/PLAN.md).
