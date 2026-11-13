# Security Policy

AgentEval runs your registered AI agents against your own test datasets and stores
judge-model request and response bodies for audit. Because of what it handles, we take
reports seriously and respond quickly.

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.x (latest minor) | Yes |
| Older minors | No |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report privately through GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
on this repository ("Security" tab, "Report a vulnerability").

Please include:

- the affected component (`apps/api`, `apps/web`, `infra/terraform/...`) and version or commit,
- a description of the issue and its impact,
- steps to reproduce, or a proof of concept,
- any suggested mitigation.

What to expect:

| Stage | Target |
| ----- | ------ |
| Acknowledgement | within 3 business days |
| Initial assessment and severity | within 7 business days |
| Fix or mitigation for critical and high issues | within 30 days |
| Coordinated public disclosure | after a fix is released, credited to you unless you prefer otherwise |

## Scope

In scope: the code in this repository and the infrastructure it provisions with its
default settings. We are especially interested in:

- any way to recover a judge model provider credential (an API key) from the API, logs,
  or database,
- any way to read another organization's agents, datasets, evaluation runs, traces or
  benchmark comparisons, or to use an API key beyond its scopes,
- any way a custom evaluator (a user-registered scoring function) escapes its sandbox,
- a crash or worker restart that loses or corrupts an in-progress evaluation run's results,
- authentication or authorization bypasses in the dashboard API,
- a dataset version reference silently pointing at the wrong historical version after an
  edit.

Out of scope:

- **The demo seed.** `make demo` creates well-known demo passwords on purpose and refuses
  to run with `ENVIRONMENT=production`.
- **The mock AI/LLM provider service** (`apps/api/src/mockllm`), a test fixture never
  deployed to AWS.
- Denial of service through resource exhaustion of a deployment you operate yourself.
- The accuracy of a judge-based score itself (a model-based metric is a measurement with
  stated error characteristics, not a security property).

## Hardening checklist for operators

See [docs/architecture/security.md](docs/architecture/security.md#operator-checklist).
