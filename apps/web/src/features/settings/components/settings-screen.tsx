"use client";

import { KeyRoundIcon, PlusIcon, UsersIcon } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { Surface } from "@/components/surface";
import { TableSkeleton } from "@/components/table-skeleton";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { SimpleSelect } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApiKeys, useRevokeApiKey } from "@/features/api-keys/api";
import { useMe } from "@/features/auth/api";
import { ChangePasswordDialog } from "@/features/auth/components/change-password-dialog";
import { useActiveOrg, useMembers, useOrgPermissions, useRemoveMember, useUpdateMemberRole } from "@/features/orgs/api";
import { errorMessage } from "@/lib/api/errors";
import { formatRelative } from "@/lib/format";
import { ORG_ROLES, roleLabel } from "@/lib/roles";

import { CreateApiKeyDialog } from "./create-api-key-dialog";
import { InviteMemberDialog } from "./invite-member-dialog";

function MembersPanel({ orgId }: { orgId: string }) {
  const { data: me } = useMe();
  const { isOwner, isAdmin } = useOrgPermissions();
  const members = useMembers(orgId);
  const updateRole = useUpdateMemberRole(orgId);
  const removeMember = useRemoveMember(orgId);
  const [inviteOpen, setInviteOpen] = React.useState(false);
  const [removeTarget, setRemoveTarget] = React.useState<{ userId: string; email: string } | null>(null);

  function confirmRemove() {
    if (!removeTarget) return;
    removeMember.mutate(removeTarget.userId, {
      onSuccess: () => {
        toast.success(`Removed ${removeTarget.email}.`);
        setRemoveTarget(null);
      },
      onError: (err) => {
        toast.error(errorMessage(err));
        setRemoveTarget(null);
      },
    });
  }

  return (
    <>
      <Surface className="overflow-hidden">
        <div className="flex items-center justify-end px-5 pt-3.5 pb-1">
          {isAdmin && (
            <Button size="sm" onClick={() => setInviteOpen(true)}>
              <PlusIcon />
              Add member
            </Button>
          )}
        </div>
        {members.isPending ? (
          <TableSkeleton rows={4} cols={3} />
        ) : members.isError ? (
          <ErrorState error={members.error} onRetry={() => void members.refetch()} />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Member</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className="w-28" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.data.map((member) => {
                const self = member.user_id === me?.id;
                return (
                  <TableRow key={member.id}>
                    <TableCell>
                      <div className="font-medium text-foreground">
                        {member.user_name}
                        {self && <span className="ml-1.5 text-xs text-muted-foreground">(you)</span>}
                      </div>
                      <div className="text-xs text-muted-foreground">{member.user_email}</div>
                    </TableCell>
                    <TableCell>
                      {isOwner && !self ? (
                        <SimpleSelect
                          size="sm"
                          className="w-32"
                          value={member.role}
                          onValueChange={(role) =>
                            updateRole.mutate(
                              { userId: member.user_id, body: { role } },
                              { onError: (err) => toast.error(errorMessage(err)) },
                            )
                          }
                          options={ORG_ROLES.map((r) => ({ value: r, label: roleLabel(r) }))}
                        />
                      ) : (
                        <Chip tone="primary">{roleLabel(member.role)}</Chip>
                      )}
                    </TableCell>
                    <TableCell>
                      {isOwner && !self && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setRemoveTarget({ userId: member.user_id, email: member.user_email })}
                        >
                          Remove
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </Surface>
      <InviteMemberDialog orgId={orgId} open={inviteOpen} onOpenChange={setInviteOpen} />
      <ConfirmDialog
        open={!!removeTarget}
        onOpenChange={(o) => !o && setRemoveTarget(null)}
        title="Remove this member?"
        description={`${removeTarget?.email ?? ""} will lose access to this organization immediately.`}
        confirmLabel="Remove"
        pending={removeMember.isPending}
        onConfirm={confirmRemove}
      />
    </>
  );
}

function ApiKeysPanel({ orgId }: { orgId: string }) {
  const { isAdmin, isOwner } = useOrgPermissions();
  const keys = useApiKeys(orgId);
  const revoke = useRevokeApiKey(orgId);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [revokeTarget, setRevokeTarget] = React.useState<{ id: string; name: string } | null>(null);

  function confirmRevoke() {
    if (!revokeTarget) return;
    revoke.mutate(revokeTarget.id, {
      onSuccess: () => {
        toast.success(`Revoked ${revokeTarget.name}.`);
        setRevokeTarget(null);
      },
      onError: (err) => {
        toast.error(errorMessage(err));
        setRevokeTarget(null);
      },
    });
  }

  return (
    <>
      <Surface className="overflow-hidden">
        <div className="flex items-center justify-end px-5 pt-3.5 pb-1">
          {/* Hidden only once we KNOW there are no keys (not merely while that is still
              loading, or it would flicker away for every admin on first page load): the
              empty state below has its own identical call to action, and showing both at
              once reads as a bug, not emphasis. */}
          {isAdmin && keys.data?.length !== 0 && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <PlusIcon />
              New key
            </Button>
          )}
        </div>
        {keys.isPending ? (
          <TableSkeleton rows={3} cols={4} />
        ) : keys.isError ? (
          <ErrorState error={keys.error} onRetry={() => void keys.refetch()} />
        ) : keys.data.length === 0 ? (
          <EmptyState
            icon={KeyRoundIcon}
            title="No API keys yet"
            description="Create one for the AgentEval SDK or a CI pipeline."
            action={
              isAdmin && (
                <Button onClick={() => setCreateOpen(true)}>
                  <PlusIcon />
                  New key
                </Button>
              )
            }
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Key</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Last used</TableHead>
                <TableHead className="w-20" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.data.map((key) => (
                <TableRow key={key.id} className={key.revoked_at ? "opacity-50" : undefined}>
                  <TableCell className="font-medium text-foreground">{key.name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{key.display}</TableCell>
                  <TableCell>
                    <Chip tone="primary">{roleLabel(key.role)}</Chip>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{formatRelative(key.last_used_at)}</TableCell>
                  <TableCell>
                    {isOwner && !key.revoked_at && (
                      <Button variant="ghost" size="sm" onClick={() => setRevokeTarget({ id: key.id, name: key.name })}>
                        Revoke
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Surface>
      <CreateApiKeyDialog orgId={orgId} open={createOpen} onOpenChange={setCreateOpen} />
      <ConfirmDialog
        open={!!revokeTarget}
        onOpenChange={(o) => !o && setRevokeTarget(null)}
        title="Revoke this API key?"
        description={`${revokeTarget?.name ?? ""} will stop working immediately. This cannot be undone.`}
        confirmLabel="Revoke"
        pending={revoke.isPending}
        onConfirm={confirmRevoke}
      />
    </>
  );
}

export function SettingsScreen() {
  const { org } = useActiveOrg();
  const orgId = org?.id ?? "";
  const { role } = useOrgPermissions();
  const [pwOpen, setPwOpen] = React.useState(false);

  return (
    <>
      <PageHeader title="Settings" description={org ? `${org.name}, signed in as ${roleLabel(role ?? "")}.` : undefined} />
      <Tabs defaultValue="members">
        <TabsList>
          <TabsTrigger value="members">
            <UsersIcon />
            Members
          </TabsTrigger>
          <TabsTrigger value="keys">
            <KeyRoundIcon />
            API keys
          </TabsTrigger>
        </TabsList>
        <TabsContent value="members">
          <MembersPanel orgId={orgId} />
        </TabsContent>
        <TabsContent value="keys">
          <ApiKeysPanel orgId={orgId} />
        </TabsContent>
      </Tabs>

      <Surface className="mt-4 p-5">
        <h2 className="mb-1 text-[13px] font-semibold text-foreground">Account</h2>
        <p className="mb-3 text-[13px] text-muted-foreground">Change the password for your own sign-in.</p>
        <Button variant="outline" onClick={() => setPwOpen(true)}>
          Change password
        </Button>
      </Surface>
      <ChangePasswordDialog open={pwOpen} onOpenChange={setPwOpen} />
    </>
  );
}
