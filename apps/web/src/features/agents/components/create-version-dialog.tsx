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
import { errorMessage } from "@/lib/api/errors";
import type { Agent } from "@/lib/api/types";

import { useCreateAgentVersion } from "../api";

/** `config` is adapter-specific, matching the server's own AgentVersionIn docstring
 * exactly: an http adapter's endpoint URL, a python adapter's import path, or nothing
 * at all for a recorded adapter. */
export function CreateVersionDialog({
  orgId,
  agent,
  open,
  onOpenChange,
}: {
  orgId: string;
  agent: Agent;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [label, setLabel] = React.useState("");
  const [configValue, setConfigValue] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const create = useCreateAgentVersion(orgId, agent.id);

  const configField =
    agent.adapter_type === "http"
      ? { key: "endpoint_url", label: "Endpoint URL", placeholder: "http://localhost:9000/invoke" }
      : agent.adapter_type === "python"
        ? { key: "import_path", label: "Import path", placeholder: "my_pkg.agents:support_agent" }
        : null;

  function reset() {
    setLabel("");
    setConfigValue("");
    setError(null);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!label.trim()) {
      setError("Enter a label for this version.");
      return;
    }
    if (configField && !configValue.trim()) {
      setError(`Enter the ${configField.label.toLowerCase()}.`);
      return;
    }
    setError(null);
    create.mutate(
      { label: label.trim(), config: configField ? { [configField.key]: configValue.trim() } : {} },
      {
        onSuccess: (version) => {
          toast.success(`Created version ${version.label}.`);
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
          <DialogTitle>New version of {agent.name}</DialogTitle>
          <DialogDescription>
            A benchmark compares specific versions, not just the latest, so label each one meaningfully (a
            model name, a prompt revision, a git ref).
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogBody className="space-y-4">
            <Field label="Label" htmlFor="version-label">
              <Input id="version-label" placeholder="v3 (gpt-4.1)" value={label} onChange={(e) => setLabel(e.target.value)} />
            </Field>
            {configField ? (
              <Field label={configField.label} htmlFor="version-config" error={error ?? undefined}>
                <Input
                  id="version-config"
                  placeholder={configField.placeholder}
                  value={configValue}
                  onChange={(e) => setConfigValue(e.target.value)}
                />
              </Field>
            ) : (
              error && <p className="text-xs text-danger">{error}</p>
            )}
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating..." : "Create version"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
