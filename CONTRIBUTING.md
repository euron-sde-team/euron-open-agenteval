# Contributing

Thanks for helping improve Euron Open AgentEval. This guide covers the workflow, the bar a
change has to clear, and the conventions the codebase follows.

## Ground rules

- **Open an issue first** for anything larger than a bug fix or a docs tweak, so we can
  agree on the approach before you invest time.
- **One concern per pull request.** A refactor and a feature are two PRs.
- **Security issues go through private reporting**, never a public issue. See
  [SECURITY.md](SECURITY.md).
- By contributing you agree your work is released under the [MIT License](LICENSE).

## Development setup

Requirements: Docker, Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 22 and
pnpm 9 (`corepack enable`), and `git`.

```bash
make up          # Postgres, Redis, Floci (provisioned by Terraform), mock AI/LLM, api, worker, web
make demo        # demo agent, dataset and evaluation history
make test        # unit tests (API and web)
```

[docs/guides/quickstart-local.md](docs/guides/quickstart-local.md) walks through the local
stack in detail.

## Before you open a pull request

Each of these must pass:

```bash
make lint typecheck test
make test-integration                  # the API against real Postgres and Redis
make e2e                               # when you touched a dashboard flow or infrastructure
make tf-validate tf-lint tf-security   # when you touched infra/terraform
make tf-aws-on-floci                   # same: apply and destroy aws-dev against Floci
make openapi                           # when you changed an endpoint (a test checks drift)
make sanitize                          # no credentials, account ids, resource ids or dashes
```

## Conventions

**Package by domain.** `apps/api/src/agenteval/<domain>/` owns its `router.py` (HTTP
only), `schemas.py` (the public contract), `service.py` (rules), `models.py` and, where it
has queries of its own, `repository.py`. Dependencies point inward: router, service, data.
A domain calls another domain's service, never its tables. The `evaluators` package is the
one deliberate exception: it is a shared library the API, worker and SDK all import
directly, so an evaluation run locally by the SDK and a run executed by the worker apply
byte-identical scoring logic.

**A score is only as honest as its method.** A deterministic check never calls a model. A
judge-based metric always records its rubric version and the judge's raw response
alongside the numeric score, so a score can be audited, not just trusted. A judge from the
same provider family as the agent under test is flagged, never silently accepted as neutral.

**No bare composite score.** A single weighted number is opt-in and always shown with its
per-metric breakdown on the same screen, never as the only number a user sees.

**A dataset edit is a new version.** Past evaluation runs keep a reference to the exact
dataset version they ran against; editing a test case never silently changes what a
historical score means.

**Traces use OpenTelemetry GenAI semantic conventions**, not a bespoke schema. A trace
exported by any OpenTelemetry-compatible instrumentation should be ingestible with no
AgentEval-specific SDK required.

**External systems sit behind a Protocol.** The judge provider abstraction (so a mock
judge, OpenAI, Anthropic, or any other provider is a file, not a switch edited in five
places) and the agent adapter abstraction (`http`, `python`, `recorded`).

**Configuration is validated.** A new setting goes in `core/config.py`, is documented in
[docs/guides/configuration.md](docs/guides/configuration.md) in the same PR, and
security-relevant ones are enforced by `Settings.guard()` at boot.

**Database changes are new migrations.** Add an Alembic revision under
`apps/api/src/agenteval/migrations/versions/`. Never edit an applied one. Indexes for every
new filter the API exposes belong in the same revision.

**Comments explain why.** The code says what it does. Comments are for the constraint, the
incident, or the trade-off that made it this way.

**Style.** ruff and mypy `--strict` for Python; ESLint and TypeScript strict for the web.
No em dashes or en dashes anywhere (the sanitization check enforces it).

## Commit messages

Imperative mood with an optional scope: `evaluators: run deterministic checks before any
judge call`, `web: show the rubric version next to a judge score`. Explain the why in the
body when it is not obvious.

## Architecture decisions

Significant decisions are recorded in [docs/architecture/adr/](docs/architecture/adr/).
If your change reverses or extends one, add a new ADR rather than editing the old one.
