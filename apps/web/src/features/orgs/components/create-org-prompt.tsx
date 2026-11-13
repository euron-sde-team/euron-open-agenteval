"use client";

import { Building2Icon } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { EvalMark } from "@/components/eval-logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/ui/label";
import { errorMessage } from "@/lib/api/errors";

import { useCreateOrg } from "../api";

/** Shown to a signed-in user who belongs to no organization yet: a brand new
 * self-hosted install, or a member removed from their last one. */
export function CreateOrgPrompt() {
  const [name, setName] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const create = useCreateOrg();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Enter a name for your organization.");
      return;
    }
    setError(null);
    create.mutate(
      { name: name.trim() },
      {
        onSuccess: (org) => toast.success(`Created ${org.name}.`),
        onError: (err) => setError(errorMessage(err)),
      },
    );
  }

  return (
    <div className="flex flex-col items-center text-center">
      <div className="mb-3.5 flex size-11 items-center justify-center rounded-xl bg-primary-soft text-primary">
        <Building2Icon className="size-5" />
      </div>
      <h2 className="text-sm font-semibold text-foreground">Create your organization</h2>
      <p className="mt-1 max-w-sm text-[13px] leading-relaxed text-muted-foreground">
        AgentEval scopes agents, datasets and evaluations to an organization. You own this one and can
        invite your team once it exists.
      </p>
      <form onSubmit={submit} className="mt-5 w-full max-w-xs space-y-3 text-left" noValidate>
        <Field label="Organization name" htmlFor="org-name" error={error ?? undefined}>
          <Input
            id="org-name"
            autoFocus
            placeholder="Acme Corp"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Button type="submit" className="w-full" disabled={create.isPending}>
          {create.isPending ? "Creating..." : "Create organization"}
        </Button>
      </form>
      <div className="mt-6 flex items-center gap-1.5 text-[11.5px] text-faint">
        <EvalMark className="size-4" />
        AgentEval
      </div>
    </div>
  );
}
