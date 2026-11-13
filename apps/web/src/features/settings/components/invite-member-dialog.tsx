"use client";

import * as React from "react";
import { toast } from "sonner";

import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/ui/label";
import { SimpleSelect } from "@/components/ui/select";
import { errorMessage } from "@/lib/api/errors";
import { ORG_ROLES, roleLabel } from "@/lib/roles";

import { useInviteMember } from "../../orgs/api";

export function InviteMemberDialog({
  orgId,
  open,
  onOpenChange,
}: {
  orgId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [email, setEmail] = React.useState("");
  const [role, setRole] = React.useState("member");
  const [error, setError] = React.useState<string | null>(null);
  const invite = useInviteMember(orgId);

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      setEmail("");
      setRole("member");
      setError(null);
    }
    onOpenChange(nextOpen);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) {
      setError("Enter the member's email.");
      return;
    }
    setError(null);
    invite.mutate(
      { email: email.trim(), role },
      {
        onSuccess: () => {
          toast.success(`Added ${email.trim()}.`);
          handleOpenChange(false);
        },
        onError: (err) => setError(errorMessage(err)),
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add a member</DialogTitle>
          <DialogDescription>
            AgentEval is self-hosted: the account must already exist. Create it on the server first with{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">agenteval create-owner</code> if
            it does not, then add it here.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogBody className="space-y-4">
            <Field label="Email" htmlFor="invite-email" error={error ?? undefined}>
              <Input
                id="invite-email"
                type="email"
                placeholder="person@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            <Field label="Role" htmlFor="invite-role">
              <SimpleSelect
                id="invite-role"
                value={role}
                onValueChange={setRole}
                options={ORG_ROLES.map((r) => ({ value: r, label: roleLabel(r) }))}
              />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={invite.isPending}>
              {invite.isPending ? "Adding..." : "Add member"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
