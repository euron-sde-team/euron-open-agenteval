"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { AgentIn, AgentVersionIn } from "@/lib/api/types";
import { qk, STALE } from "@/lib/query-keys";

export function useAgents(orgId: string) {
  return useQuery({
    queryKey: qk.agents(orgId),
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_id}/agents", { params: { path: { org_id: orgId } } })),
    enabled: !!orgId,
    staleTime: STALE.list,
  });
}

export function useAgent(orgId: string, agentId: string | undefined) {
  const agents = useAgents(orgId);
  return { ...agents, data: agents.data?.find((a) => a.id === agentId) };
}

export function useRegisterAgent(orgId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentIn) =>
      unwrap(api.POST("/api/v1/orgs/{org_id}/agents", { params: { path: { org_id: orgId } }, body })),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.agents(orgId) }),
  });
}

export function useAgentVersions(orgId: string, agentId: string) {
  return useQuery({
    queryKey: qk.agentVersions(orgId, agentId),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_id}/agents/{agent_id}/versions", {
          params: { path: { org_id: orgId, agent_id: agentId } },
        }),
      ),
    enabled: !!orgId && !!agentId,
    staleTime: STALE.list,
  });
}

export function useCreateAgentVersion(orgId: string, agentId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentVersionIn) =>
      unwrap(
        api.POST("/api/v1/orgs/{org_id}/agents/{agent_id}/versions", {
          params: { path: { org_id: orgId, agent_id: agentId } },
          body,
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.agentVersions(orgId, agentId) }),
  });
}
