"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { ApiKeyIn } from "@/lib/api/types";
import { qk, STALE } from "@/lib/query-keys";

export function useApiKeys(orgId: string) {
  return useQuery({
    queryKey: qk.apiKeys(orgId),
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_id}/api-keys", { params: { path: { org_id: orgId } } })),
    enabled: !!orgId,
    staleTime: STALE.list,
  });
}

export function useCreateApiKey(orgId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ApiKeyIn) =>
      unwrap(api.POST("/api/v1/orgs/{org_id}/api-keys", { params: { path: { org_id: orgId } }, body })),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.apiKeys(orgId) }),
  });
}

export function useRevokeApiKey(orgId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) =>
      unwrap(api.DELETE("/api/v1/orgs/{org_id}/api-keys/{key_id}", { params: { path: { org_id: orgId, key_id: keyId } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.apiKeys(orgId) }),
  });
}
