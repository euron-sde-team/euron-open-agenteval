/**
 * Mirrors agenteval.orgs.service.role_at_least and ORG_ROLES exactly: owner > admin >
 * member > viewer. Role is per-organization, never global, so every check here takes
 * the active organization's own role, not a global user field.
 */

export const ORG_ROLES = ["owner", "admin", "member", "viewer"] as const;
export type OrgRole = (typeof ORG_ROLES)[number];

const RANK: Record<string, number> = { owner: 3, admin: 2, member: 1, viewer: 0 };

export function roleAtLeast(role: string | null | undefined, minimum: OrgRole): boolean {
  if (!role) return false;
  return (RANK[role] ?? -1) >= (RANK[minimum] ?? 99);
}

export function roleLabel(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1);
}
