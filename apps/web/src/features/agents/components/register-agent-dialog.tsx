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

import { useRegisterAgent } from "../api";

const ADAPTER_TYPES = [
  { value: "http", label: "HTTP endpoint" },
  { value: "python", label: "Python callable" },
  { value: "recorded", label: "Recorded traces (pushed by the SDK)" },
];

const PROVIDERS = [
  { value: "other", label: "Other" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "mock", label: "Mock (CI and demos)" },
];

export function RegisterAgentDialog({
  orgId,
  open,
  onOpenChange,
}: {
  orgId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [name, setName] = React.useState("");
  const [adapterType, setAdapterType] = React.useState("http");
  const [provider, setProvider] = React.useState("other");
  const [error, setError] = React.useState<string | null>(null);
  const register = useRegisterAgent(orgId);

  function reset() {
    setName("");
    setAdapterType("http");
    setProvider("other");
    setError(null);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Enter a name for this agent.");
      return;
    }
    setError(null);
    register.mutate(
      { name: name.trim(), adapter_type: adapterType, provider: provider as "openai" | "anthropic" | "mock" | "other" },
      {
        onSuccess: (agent) => {
          toast.success(`Registered ${agent.name}.`);
          reset();
          onOpenChange(false);
        },
        onError: (err) => setError(errorMessage(err)),
      },
    );
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) reset();
    onOpenChange(nextOpen);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Register an agent</DialogTitle>
          <DialogDescription>
            Add a version afterward with the adapter's own config (an HTTP endpoint URL or a Python import path).
            A recorded agent needs no config: its traces are supplied by the SDK at evaluation time.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogBody className="space-y-4">
            <Field label="Name" htmlFor="agent-name">
              <Input
                id="agent-name"
                placeholder="support-agent"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Field label="Adapter type" htmlFor="agent-adapter" hint="How AgentEval invokes this agent during a run.">
              <SimpleSelect id="agent-adapter" value={adapterType} onValueChange={setAdapterType} options={ADAPTER_TYPES} />
            </Field>
            <Field
              label="Model provider"
              htmlFor="agent-provider"
              hint="Used for the judge self-preference-bias check: a judge from the same family is flagged."
              error={error ?? undefined}
            >
              <SimpleSelect id="agent-provider" value={provider} onValueChange={setProvider} options={PROVIDERS} />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={register.isPending}>
              {register.isPending ? "Registering..." : "Register"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
