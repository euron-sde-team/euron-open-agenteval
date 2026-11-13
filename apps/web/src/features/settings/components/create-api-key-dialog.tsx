"use client";

import { CheckCircle2Icon, TriangleAlertIcon } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { CopyButton } from "@/components/copy-button";
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
import type { ApiKeyCreated } from "@/lib/api/types";
import { ORG_ROLES, roleLabel } from "@/lib/roles";

import { useCreateApiKey } from "../../api-keys/api";

export function CreateApiKeyDialog({
  orgId,
  open,
  onOpenChange,
}: {
  orgId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const create = useCreateApiKey(orgId);
  const [name, setName] = React.useState("");
  const [role, setRole] = React.useState("member");
  const [error, setError] = React.useState<string | null>(null);
  const [created, setCreated] = React.useState<ApiKeyCreated | null>(null);

  React.useEffect(() => {
    if (open) {
      setName("");
      setRole("member");
      setError(null);
      setCreated(null);
    }
  }, [open]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError('Name it after where it runs, for example "ci".');
      return;
    }
    setError(null);
    create.mutate(
      { name: name.trim(), role },
      {
        onSuccess: (key) => {
          setCreated(key);
          toast.success("API key created.");
        },
        onError: (err) => setError(errorMessage(err)),
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !create.isPending && onOpenChange(o)}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {created && <CheckCircle2Icon className="size-5 text-savings" />}
            {created ? "Key is ready" : "New API key"}
          </DialogTitle>
          <DialogDescription>
            {created
              ? "Used by the AgentEval SDK, or any CI pipeline, in place of a dashboard session."
              : "Scoped to this organization, with the role you choose. Revoke it any time."}
          </DialogDescription>
        </DialogHeader>
        {created ? (
          <>
            <DialogBody>
              <div className="space-y-4">
                <div className="flex gap-3 rounded-xl bg-warning-soft px-4 py-3 text-[13px]">
                  <TriangleAlertIcon className="mt-0.5 size-4 shrink-0 text-warning" />
                  <p className="text-foreground">
                    Copy this key now. It is shown <strong>once</strong>; AgentEval stores only a peppered hash
                    and cannot show it again.
                  </p>
                </div>
                <div className="flex items-center gap-2 rounded-xl bg-muted p-1.5 pl-3.5">
                  <code className="min-w-0 flex-1 truncate font-mono text-[12.5px] select-all">
                    {created.plaintext}
                  </code>
                  <CopyButton value={created.plaintext} label="Copy key" variant="default" />
                </div>
              </div>
            </DialogBody>
            <DialogFooter>
              <Button onClick={() => onOpenChange(false)}>I have copied the key</Button>
            </DialogFooter>
          </>
        ) : (
          <form onSubmit={submit} className="flex min-h-0 flex-col" noValidate>
            <DialogBody className="space-y-4">
              <Field label="Name" htmlFor="key-name" error={error ?? undefined}>
                <Input id="key-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="ci" />
              </Field>
              <Field label="Role" htmlFor="key-role" hint="The most this key can do in this organization.">
                <SimpleSelect
                  id="key-role"
                  value={role}
                  onValueChange={setRole}
                  options={ORG_ROLES.map((r) => ({ value: r, label: roleLabel(r) }))}
                />
              </Field>
            </DialogBody>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? "Creating..." : "Create key"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
