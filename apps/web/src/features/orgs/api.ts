"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import { api, unwrap } from "@/lib/api/client";
import type { MemberInvite, MemberRoleUpdate, Organization, OrganizationCreate } from "@/lib/api/types";
import { qk, STALE } from "@/lib/query-keys";
import { roleAtLeast } from "@/lib/roles";
import { useUiPrefs } from "@/lib/store";

import { useMe } from "../auth/api";

export function useOrgs() {
  const me = useMe();
  return useQuery({
    queryKey: qk.orgs,
    queryFn: () => unwrap(api.GET("/api/v1/orgs")),
    enabled: !!me.data,
    staleTime: STALE.config,
  });
}

/**
 * The organization every org-scoped screen reads. Falls back to the first organization
 * the user belongs to if none is persisted yet, or the persisted one no longer exists
 * (removed, or the user lost access). Nothing renders org-scoped content until this
 * resolves, the same way AppShell holds for /auth/me.
 */
export function useActiveOrg(): { org: Organization | undefined; isLoading: boolean } {
  const orgs = useOrgs();
  const activeOrgId = useUiPrefs((s) => s.activeOrgId);
  const setActiveOrgId = useUiPrefs((s) => s.setActiveOrgId);

  const resolved = React.useMemo(() => {
    if (!orgs.data?.length) return undefined;
    return orgs.data.find((o) => o.id === activeOrgId) ?? orgs.data[0];
  }, [orgs.data, activeOrgId]);

  React.useEffect(() => {
    if (resolved && resolved.id !== activeOrgId) setActiveOrgId(resolved.id);
  }, [resolved, activeOrgId, setActiveOrgId]);

  return { org: resolved, isLoading: orgs.isLoading };
}

/** Permission flags for the active organization's role. While loading, everything is read only. */
export function useOrgPermissions() {
  const { org } = useActiveOrg();
  const role = org?.role;
  return {
    role,
    isViewer: !!role,
    isMember: roleAtLeast(role, "member"),
    isAdmin: roleAtLeast(role, "admin"),
    isOwner: roleAtLeast(role, "owner"),
  };
}

export function useCreateOrg() {
  const client = useQueryClient();
  const setActiveOrgId = useUiPrefs((s) => s.setActiveOrgId);
  return useMutation({
    mutationFn: (body: OrganizationCreate) => unwrap(api.POST("/api/v1/orgs", { body })),
    onSuccess: (org) => {
      void client.invalidateQueries({ queryKey: qk.orgs });
      setActiveOrgId(org.id);
    },
  });
}

export function useMembers(orgId: string) {
  return useQuery({
    queryKey: qk.members(orgId),
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_id}/members", { params: { path: { org_id: orgId } } })),
    enabled: !!orgId,
    staleTime: STALE.list,
  });
}

export function useInviteMember(orgId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: MemberInvite) =>
      unwrap(api.POST("/api/v1/orgs/{org_id}/members", { params: { path: { org_id: orgId } }, body })),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.members(orgId) }),
  });
}

export function useUpdateMemberRole(orgId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, body }: { userId: string; body: MemberRoleUpdate }) =>
      unwrap(
        api.PATCH("/api/v1/orgs/{org_id}/members/{user_id}", {
          params: { path: { org_id: orgId, user_id: userId } },
          body,
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.members(orgId) }),
  });
}

export function useRemoveMember(orgId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) =>
      unwrap(
        api.DELETE("/api/v1/orgs/{org_id}/members/{user_id}", {
          params: { path: { org_id: orgId, user_id: userId } },
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.members(orgId) }),
  });
}
