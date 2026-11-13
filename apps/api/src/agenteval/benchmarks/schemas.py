"""Pydantic schemas for the benchmarks domain."""

from __future__ import annotations

import uuid

from agenteval.core.schemas import ApiModel


class BenchmarkDeltaOut(ApiModel):
    metric_id: str
    baseline_mean: float
    candidate_mean: float
    delta: float
    is_regression: bool


class BenchmarkComparisonOut(ApiModel):
    baseline_run_id: uuid.UUID
    candidate_run_id: uuid.UUID
    deltas: list[BenchmarkDeltaOut]
    has_regression: bool


class BenchmarkTrendPointOut(ApiModel):
    run_id: uuid.UUID
    mean_score: float


class BenchmarkTrendOut(ApiModel):
    series: dict[str, list[BenchmarkTrendPointOut]]
