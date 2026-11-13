/**
 * Named aliases over the generated OpenAPI types (`pnpm gen:api`). Nothing here is
 * hand-written: every shape comes from `schema.d.ts`, which is generated from
 * docs/api/openapi.yaml.
 */
import type { components } from "./schema";

type S = components["schemas"];

export type User = S["UserOut"];
export type Session = S["SessionOut"];
export type Organization = S["OrganizationOut"];
export type OrganizationCreate = S["OrganizationCreate"];
export type Membership = S["MembershipOut"];
export type MemberInvite = S["MemberInvite"];
export type MemberRoleUpdate = S["MemberRoleUpdate"];
export type ApiKey = S["ApiKeyOut"];
export type ApiKeyCreated = S["ApiKeyCreated"];
export type ApiKeyIn = S["ApiKeyIn"];
export type AuditLogEntry = S["AuditLogOut"];

export type Agent = S["AgentOut"];
export type AgentIn = S["AgentIn"];
export type AgentVersion = S["AgentVersionOut"];
export type AgentVersionIn = S["AgentVersionIn"];

export type ExpectedBehaviorIn = S["ExpectedBehaviorIn"];
export type TestCaseIn = S["TestCaseIn"];
export type TestCaseOut = S["TestCaseOut"];
export type Dataset = S["DatasetOut"];
export type DatasetCreate = S["DatasetCreate"];
export type DatasetVersion = S["DatasetVersionOut"];
export type DatasetVersionUpdate = S["DatasetVersionUpdate"];

export type EvaluationRunIn = S["EvaluationRunIn"];
export type EvaluationRun = S["EvaluationRunOut"];
export type EvaluationRunDetail = S["EvaluationRunDetailOut"];
export type EvaluationResult = S["EvaluationResultOut"];
export type JudgeCall = S["JudgeCallOut"];

export type Span = S["SpanOut"];
export type Trace = S["TraceOut"];

export type BenchmarkDelta = S["BenchmarkDeltaOut"];
export type BenchmarkComparison = S["BenchmarkComparisonOut"];
export type BenchmarkTrend = S["BenchmarkTrendOut"];
export type BenchmarkTrendPoint = S["BenchmarkTrendPointOut"];
