# Euron Open AgentEval 0.1.0: build plan

An open-source platform that scores how well an AI agent completed a task, traces exactly
how it got there, and tracks whether a new model or prompt version made things better or
worse. It runs an agent against a reusable dataset of test cases, evaluates each run with
deterministic checks and rubric-based scoring (never an LLM's opinion alone), and keeps
every run's score and trace side by side so a regression from the last version is a diff,
not a guess.

Source brief: the pasted "Euron AgentEval: Complete Product Blueprint" (a 100-feature,
7-phase roadmap: agent testing, hallucination detection, tool-calling evaluation, RAG
evaluation, multi-agent evaluation, security/safety evaluation, dataset management,
monitoring, SDKs). Per the user's explicit decision, 0.1.0 is scoped to the brief's own
closing recommendation, its three flagship pillars: the **Agent Evaluation Engine**, the
**Execution Trace Analyzer**, and **Continuous Benchmarking**. RAG evaluation, multi-agent
evaluation, safety/red-teaming, and first-party framework adapters (LangChain, LangGraph,
CrewAI) are roadmap, not 0.1.0. Per this program's standing rules, licensed MIT (the brief
says Apache 2.0) and the dashboard is Next.js (the brief says plain React).

## Purpose

An AI agent's quality is invisible until something breaks in front of a user. A team
ships a new prompt, a new model version, or a new tool, and has no repeatable way to ask
"did this make the agent better or worse at the tasks it actually needs to do." Testing
by hand against a handful of examples does not scale and does not repeat; a single
"intelligence score" from one run is not evidence of anything, because the dataset, the
model, the judge, and the task all change the number. **AgentEval's job is to make an
agent's quality measurable and comparable over time**: register an agent, run it against a
versioned dataset of test cases, score each run on multiple independent dimensions with a
method that is stated and reproducible, and see the next run's score next to this one, not
instead of it.

Comparable products, confirmed by research rather than assumed: **DeepEval** and **Ragas**
are libraries (pytest-style and RAG-specialist respectively), with no execution-trace view
of the run being scored; **Langfuse** and **Arize Phoenix** trace agent runs well but
Langfuse does not score, and Phoenix is source-available under the Elastic License, not
OSI-approved open source; **Promptfoo** is strong at prompt/model comparison and red-team
testing but its ownership is reportedly shifting toward an acquirer, worth treating as a
moving target. No tool in active use today combines scoring, the execution trace of the
scored run, and regression-over-time as one first-class object, under a genuinely
permissive license. **AgentEval's angle: one scored run is one trace plus one set of
metric results, and one agent's history is a graph of those over time**: never a trace
tool and a scoring tool a team has to stitch together themselves, and never a single
composite "intelligence score" presented as more than it is.

## Why not just reuse an existing library

DeepEval and Ragas are genuinely good at scoring and are not being reinvented here:
AgentEval's evaluators are designed to be swappable with either as a backend in a future
release (the roadmap's "custom evaluator" extension point exists for exactly this), but
0.1.0 ships its own deterministic-plus-rubric evaluators so the platform has no external
API dependency to score a run out of the box, and so every evaluator's method is fully
inspectable rather than inherited from a third-party library's own internals.

## Evaluation methodology (how a score is produced, stated up front)

Research into LLM-as-judge scoring surfaces real, reproducible failure modes this platform
must design around rather than ignore: **position bias** (a judge favoring whichever
answer it sees first in a pairwise comparison), **verbosity bias** (rewarding length over
correctness), and **self-preference bias** (a judge model scoring its own model family's
output more favorably even when it can tell the output is wrong). Asking a judge prompt to
"be fair" measurably does not fix any of these; only structural mitigations do.

AgentEval's evaluators therefore:

- Run **deterministic checks first** wherever a task defines them (exact match, regex,
  JSON schema validation, a required tool call having happened, a forbidden tool call
  having not happened) and only fall back to model-based judging for dimensions that
  cannot be checked deterministically (faithfulness, instruction adherence, open-ended
  accuracy).
- Use a **judge model from a different provider family than the agent under test** by
  default (configurable, but the UI warns when judge and agent share a provider), as the
  single structural mitigation for self-preference bias that research supports.
- Score with a **written rubric per metric**, not a bare "rate this 1 to 10" prompt, and
  record the rubric version alongside every score so a later rubric change cannot silently
  reinterpret an old score.
- Report **every metric separately** (task success, accuracy, faithfulness, tool accuracy,
  instruction adherence, efficiency) rather than one weighted composite by default; a
  composite is opt-in and always shown with its weights visible, never as a bare number.
- Never claim a score measures "intelligence." The dashboard and docs state plainly that a
  score is relative to its dataset, evaluator version, and judge model, and is for
  comparing runs of the same configuration over time, not for ranking unrelated agents.

## Trace format

Execution traces use **OpenTelemetry GenAI semantic conventions** (the `gen_ai.*`
attribute namespace) rather than a bespoke schema, for the same reason the sibling project
AgentDebugger (project 12 in this program) uses real W3C Trace Context: traces are never
locked into a proprietary format, and any OpenTelemetry-compatible exporter can send a
trace to AgentEval with no Euron-specific SDK required. A run's trace is attached to its
evaluation result by `run_id`, so opening a score always offers the matching trace, and
opening a trace from the Execution Trace Analyzer always offers its score, the two are
never separate objects a user has to cross-reference by hand.

## Acceptance criteria (each is an automated test)

1. `make up` starts the whole system (Postgres, Redis, Floci, mock AI/LLM, api, worker,
   web) with Terraform applied against Floci; the Python SDK evaluates a toy agent against
   a seeded dataset with no other configuration.
2. Registering an agent, creating a dataset of test cases (JSON/CSV import), and running
   an evaluation produces one `EvaluationRun` with a per-test-case result and a trace for
   each case, retrievable within seconds of the run completing.
3. A deterministic check (exact match, regex, required-tool-called, forbidden-tool-called)
   runs and reports a pass/fail with no model call; a dataset with only deterministic
   checks produces a complete evaluation with zero judge-model calls (proven by call count).
4. A judge-scored metric (faithfulness, instruction adherence, accuracy) records the judge
   model, the rubric version, and the raw judge response alongside the numeric score, and
   re-scoring the same case with the same rubric version and judge model is deterministic
   within the judge's own temperature=0 variance (tested with a mock judge for exact
   reproducibility).
5. A judge from the same provider family as the agent under test triggers a visible warning
   on the run's results (self-preference bias mitigation); a cross-family judge does not.
6. An evaluation run's execution trace for a test case uses OpenTelemetry GenAI semantic
   convention attributes and is queryable by trace id from both the Evaluations screen and
   the Execution Trace Analyzer, landing on the same run either way.
7. A tool-calling test case scores tool selection accuracy and argument validity from the
   trace's recorded tool-call spans, not from re-parsing the agent's free-text output.
8. Two evaluation runs of the same agent against the same dataset (a baseline and a
   candidate version) produce a **Benchmark Comparison** showing each metric's delta, and a
   configurable regression threshold flags a metric that got worse beyond the threshold.
9. Benchmark history for one agent across more than two runs renders as a trend (each
   metric over time, oldest to newest), not just a pairwise diff.
10. An evaluation dataset is versioned: editing a test case creates a new dataset version
    and past evaluation runs keep a reference to the exact version they ran against, so a
    dataset edit never silently changes the meaning of a historical score.
11. A custom evaluator (a user-registered scoring function or rubric) is picked up by the
    next run with no restart, and its results appear with the same shape as a built-in
    metric's results.
12. The dashboard never presents a single composite score as the headline without the
    per-metric breakdown visible on the same screen; the composite is opt-in per view.
13. Tenant isolation: a member of one organization gets 404 for another organization's
    agents, datasets, evaluation runs and traces.
14. `make up && make demo` seeds a realistic agent, dataset, and evaluation history (at
    least one regression and one improvement across versions) with no configuration.

## Architecture

```
web (Next.js 15) ──► api (FastAPI) ──► PostgreSQL 16 (agents, datasets, runs, scores, spans)
                         │  ▲              Redis (run progress, response cache)
   SDK / OTLP ───────────┘  │
                      worker(s) ──► evaluator engine (deterministic checks, judge calls)
                         │      ──► judge model provider (or mock AI/LLM for CI/demo)
                         └────────► benchmark comparison engine
```

One Python package `agenteval` with process roles: `agenteval serve` (API), `agenteval
worker` (runs evaluations), `agenteval migrate`, `agenteval seed-demo`. The evaluator
engine is a shared library the API, worker, and SDK all import, so a dataset run locally by
the SDK and a run executed by the worker apply byte-identical scoring logic.

**Evaluation execution.** An evaluation run is queued (Postgres, `FOR UPDATE SKIP LOCKED`)
and claimed by a worker. For each test case, the worker invokes the registered agent
(directly, through an adapter, or against a recorded trace supplied by the caller),
captures an OpenTelemetry-shaped trace of the invocation, runs every configured metric's
deterministic checks first, then any judge-based metrics, and writes one `EvaluationResult`
row per test case per metric, each pointing at the trace span(s) it scored.

**Benchmarking.** A `BenchmarkComparison` is computed on demand (and cached) between any two
completed evaluation runs of the same agent and dataset version lineage: per-metric mean,
delta, and a regression flag against a configurable threshold. Benchmark history is the
same computation applied pairwise across a run sequence, surfaced as a trend.

## Caching and query layers

| Layer | What | Where | Key | TTL / invalidation |
| --- | --- | --- | --- | --- |
| Project config | API key lookup, judge provider settings | In-process TTL cache (5s) backed by a Redis version stamp | `cfg:v` counter | Any admin write bumps the version; every instance refreshes on next request |
| Evaluation write path | Runs, results, spans | Postgres (source of truth) | run id, result id | None; append-only per run |
| Dashboard aggregates | Overview counts, metric trend series | Postgres materialized query + Redis 15s response cache | query params | Recomputed on demand, cached briefly, invalidated by a new run completing |
| Live run progress | An in-progress evaluation run's per-case status | Redis pub/sub relayed over `/ws/runs/{id}` | run id | Not persisted; a reconnect re-fetches current state from Postgres |
| Benchmark comparison | Pairwise metric deltas between two runs | Postgres `benchmark_comparisons` (computed, cached) | run id pair | Recomputed if either run's results change (they should not, once complete) |
| Dashboard | Server state | TanStack Query | per resource | `staleTime` per view, invalidated on mutation |

## Scope

### In 0.1.0

| Area | What ships |
| --- | --- |
| Agent registration | Register an agent by name, with an adapter type (`http` calling a user's endpoint, `python` importing a callable, `recorded` scoring pre-captured traces supplied by the caller) and versions, so a benchmark compares specific agent versions, not just the latest. |
| Datasets | JSON/CSV import, versioned (an edit creates a new version, old runs keep their version reference), test-case tagging, expected-behavior fields matching the brief's example shape (expected outcomes, forbidden behaviors, required/forbidden tool calls). |
| Evaluation Engine | Deterministic checks (exact match, regex, JSON schema, required/forbidden tool call) run first and free of model calls; judge-based metrics (task success, accuracy, faithfulness, instruction adherence) with a stated rubric version, cross-family judge default with a same-family warning, and every judge call's raw response stored for audit. |
| Tool-calling evaluation | Tool selection accuracy and argument validity scored from the run's own recorded tool-call spans. |
| Execution Trace Analyzer | OpenTelemetry GenAI semantic-convention traces per run and per test case; a waterfall timeline and span detail view; every evaluation result links to the span(s) it scored, and every trace links back to its evaluation result. |
| Continuous Benchmarking | Pairwise comparison between any two runs (per-metric delta, configurable regression threshold, flagged regressions), and a trend view across more than two runs for one agent. |
| Efficiency metrics | Tokens, latency, and execution-step count per run, from the same trace the quality metrics score, never a separately maintained total. |
| Custom evaluators | A user-registered scoring function (Python, sandboxed the same way the program's other code-execution projects sandbox untrusted code) or a rubric-only judge metric, picked up by the next run with no restart. |
| Multi-tenant | `org_id` on every table via a scoped repository, the same structural tenant isolation as every other project in this program; roles `owner`, `admin`, `member`, `viewer`. |
| Dashboard (Next.js) | Sign in, Overview, Agents, Datasets, Test Suites, Evaluations (run + inspect), Execution Traces, Benchmarks (comparison + trend), Reports (export), Audit log, Settings (members, API keys). Dark and light, responsive to phone width. |
| Admin API | Everything the dashboard and SDK use, under `/api/v1`, OpenAPI documented. |
| SDK | Python (`AgentEval` client, `evaluator.evaluate(agent=..., dataset=..., metrics=[...])`, matching the brief's proposed shape) is 0.1.0's primary SDK, instrumented with OpenTelemetry so traces are standard-shaped with no proprietary wire format. A CLI (`agenteval init / agent add / dataset create / evaluate run / compare / report export`, matching the brief) ships alongside it. |
| Mock services | A mock AI/LLM provider (deterministic, speaks enough of a real provider's shape for CI, the demo, and unit tests needing no real API key) and a toy example agent for the quickstart and demo seed. |
| Ops | `/healthz`, `/readyz` (Postgres, Redis), Prometheus `/metrics`, structured JSON logs, append-only audit log for every evaluation run and every reveal of a stored judge response. |
| IaC | Terraform modules: network, database (RDS Postgres), cache (ElastiCache Redis), kms, secrets, ecr, service (ECS Fargate api + worker + web behind an ALB), observability. Envs: local-floci, aws-dev, aws-prod. |

### Roadmap (not 0.1.0)

RAG evaluation (retrieval precision/recall, context relevance, chunking/embedding
comparison), multi-agent evaluation (delegation accuracy, coordination scoring), security
and safety evaluation (prompt injection, jailbreak resistance, policy compliance
red-teaming), first-party framework adapters (LangChain, LangGraph, CrewAI, AutoGen,
LlamaIndex, OpenAI Agents SDK) beyond generic OpenTelemetry/HTTP/Python adapters, synthetic
test-case generation, a TypeScript SDK, CI/CD-native integrations (GitHub Actions) beyond
the generic CLI/API, pluggable DeepEval/Ragas backend evaluators, a hosted evaluation
infrastructure tier, SSO/OIDC.

## Code layout (domain packages)

`core/` (config, db, redis, errors, security, logging, deps) and one package per domain:
`auth`, `orgs`, `agents`, `datasets`, `test_suites`, `evaluations` (run orchestration),
`evaluators` (deterministic checks + judge-based metrics, the evaluator registry),
`traces` (OpenTelemetry-shaped ingestion and query), `tool_inspector`, `benchmarks`
(comparison + trend), `reports`, `audit`, `health`. Each has router, schemas, service,
repository, models. Backend architecture follows the program's layering: router -> service
-> repository -> models.

## Data model (Postgres, `org_id` structural tenant scoping)

`organizations`, `users`, `memberships`, `api_keys`, `agents`, `agent_versions`,
`datasets`, `dataset_versions`, `test_cases`, `evaluation_runs`, `evaluation_results`,
`metrics` (built-in and custom, with rubric version), `judge_calls` (raw request/response
for audit), `traces`, `spans`, `tool_calls`, `benchmark_comparisons`, `audit_log`
(append-only).

## Ports (project 17)

web 5710, api 5730, postgres 5742, redis 5779, floci 5766, mailpit 5725, mock AI/LLM 5750,
tf-aws-on-floci 5796.

## Test plan

- Unit: deterministic check evaluators (exact/regex/schema/tool-call), judge metric
  prompt construction and rubric versioning, cross-family judge detection, OpenTelemetry
  GenAI attribute mapping, benchmark delta/regression-threshold computation, custom
  evaluator loading, dataset versioning.
- Integration (real Postgres, Redis, Floci, mock AI/LLM): every admin endpoint with RBAC;
  an evaluation run end to end against the mock agent and mock judge, zero judge calls for
  a deterministic-only dataset (call count asserted); a judge-scored metric's rubric
  version and raw response are stored and retrievable; tool-calling accuracy scored from
  real recorded tool-call spans; a benchmark comparison between two real runs produces the
  correct per-metric delta and regression flag; a dataset edit creates a new version
  without changing a past run's version reference; tenant isolation (a second org's key
  gets 404s).
- E2E (Playwright): sign in, register an agent, create a dataset, run an evaluation, see
  live progress, open a result and its matching trace, run a second evaluation (a changed
  agent version), open the benchmark comparison and see a flagged regression, add a custom
  evaluator and see it picked up by the next run.
- Browser QA (Puppeteer): every page, light and dark, desktop and phone.

## Release verification (0.1.0)

Every acceptance criterion is proven by an automated test (integration tests run against
real Postgres, Redis, Floci and the mock AI/LLM service over HTTP; e2e against the full
Compose stack).

| # | Criterion | Proven by |
| --- | --- | --- |
| 1 | `make up` starts everything; SDK evaluates out of the box | Compose stack brought up from scratch; SDK integration test against it; e2e `01-first-evaluation` |
| 2 | Agent + dataset + run produces results and traces | `test_evaluations.py::test_ac2_*` |
| 3 | Deterministic checks need zero judge calls | `test_evaluators.py::test_ac3_deterministic_only_zero_judge_calls` |
| 4 | Judge metric stores rubric version, raw response, reproducible scoring | `test_evaluators.py::test_ac4_*` |
| 5 | Same-family judge warning | `test_evaluators.py::test_ac5_self_preference_warning` |
| 6 | Trace uses OTel GenAI attributes, linked both ways | `test_traces.py::test_ac6_*` |
| 7 | Tool accuracy scored from real spans | `test_tool_inspector.py::test_ac7_*` |
| 8 | Benchmark comparison delta + regression flag | `test_benchmarks.py::test_ac8_*` |
| 9 | Benchmark trend across more than two runs | `test_benchmarks.py::test_ac9_trend_history` |
| 10 | Dataset versioning preserves historical run meaning | `test_datasets.py::test_ac10_version_pinning` |
| 11 | Custom evaluator picked up with no restart | `test_evaluators.py::test_ac11_custom_evaluator_hot_pickup` |
| 12 | No bare composite score without breakdown | e2e `04-results-breakdown`; web unit test on the results component |
| 13 | Tenant isolation | `test_tenancy.py::test_ac13_cross_org_404` |
| 14 | `make demo` seeds a believable regression and improvement | `test_demo_seed.py::test_ac14_*` |
