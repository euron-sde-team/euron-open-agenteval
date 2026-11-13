"use client";

import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import { qk, STALE } from "@/lib/query-keys";

export function useAuditLog(orgId: string) {
  return useQuery({
    queryKey: qk.auditLog(orgId),
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_id}/audit-log", { params: { path: { org_id: orgId } } })),
    enabled: !!orgId,
    staleTime: STALE.list,
  });
}
