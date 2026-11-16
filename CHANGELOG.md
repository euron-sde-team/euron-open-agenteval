# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-16

### Added
- Evaluation engine: five deterministic checks (exact match, regex, JSON schema
  validation, required tool call, forbidden tool call) at zero model calls, and four
  judge scored metrics (task success, accuracy, faithfulness, instruction adherence),
  each with a versioned rubric and the judge's raw response stored for audit.
- Cross family judge default, with a visible warning when a judge shares its provider
  family with the agent under test.
- Three agent adapters: `http`, `python`, and `recorded` (the SDK runs a local callable
  and pushes a real OpenTelemetry trace for the worker to score).
- OpenTelemetry GenAI semantic convention traces for every evaluation, linked both ways
  with the result that scored it.
- Versioned datasets: editing a test case creates a new version, and a past run keeps a
  reference to the exact version it ran against.
- Benchmarking: pairwise comparison between any two completed runs with a per metric
  delta and a configurable regression threshold, plus a trend view across a run history.
- Dashboard: Overview, Agents, Agent detail, Datasets, Dataset detail, Evaluations, Run
  detail, Execution traces, Benchmarks, Reports, Audit log, Settings, Sign in, each in
  light and dark mode and responsive to phone width.
- Python SDK and CLI (`agenteval-cli`), both OpenTelemetry instrumented.
- A deterministic mock AI/LLM provider for development, tests and the demo seed.
- Append only audit log for every evaluation run and every judge response reveal.
- Terraform for a local Floci environment and AWS dev and prod environments (ECS
  Fargate, RDS, ElastiCache, KMS, Secrets Manager, ECR, CloudWatch), applied, converged
  and destroyed end to end against Floci.
- 192 unit and integration tests, 9 Playwright end to end browser tests, a Puppeteer QA
  sweep across every screen in both themes and two viewport widths.

### Known limitations
- The scoring path and data model for an organization specific custom rubric based
  evaluator exist, but 0.1.0 ships no API endpoint or dashboard screen to register one,
  so it is not an end to end usable feature yet. See the Roadmap in the README.
