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
import { Checkbox } from "@/components/ui/checkbox";
import { Field } from "@/components/ui/label";
import { SimpleSelect } from "@/components/ui/select";
import { useAgents, useAgentVersions } from "@/features/agents/api";
import { useDatasets } from "@/features/datasets/api";
import { errorMessage } from "@/lib/api/errors";

import { useQueueRun } from "../api";

const DETERMINISTIC = ["exact_match", "regex_match", "json_schema_valid", "required_tool_called", "forbidden_tool_called"];
const JUDGE = ["task_success", "accuracy", "faithfulness", "instruction_adherence"];
const ALL_METRICS = [...DETERMINISTIC, ...JUDGE];

export function QueueRunDialog({
  orgId,
  open,
  onOpenChange,
}: {
  orgId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const agents = useAgents(orgId);
  const datasets = useDatasets(orgId);
  const [agentId, setAgentId] = React.useState("");
  const versions = useAgentVersions(orgId, agentId);
  const [agentVersionId, setAgentVersionId] = React.useState("");
  const [datasetVersionId, setDatasetVersionId] = React.useState("");
  const [metricIds, setMetricIds] = React.useState<string[]>(DETERMINISTIC);
  const [error, setError] = React.useState<string | null>(null);
  const queue = useQueueRun(orgId);

  function reset() {
    setAgentId("");
    setAgentVersionId("");
    setDatasetVersionId("");
    setMetricIds(DETERMINISTIC);
    setError(null);
  }

  function toggleMetric(id: string) {
    setMetricIds((prev) => (prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!agentVersionId || !datasetVersionId) {
      setError("Choose an agent version and a dataset.");
      return;
    }
    if (metricIds.length === 0) {
      setError("Choose at least one metric.");
      return;
    }
    setError(null);
    queue.mutate(
      { agent_version_id: agentVersionId, dataset_version_id: datasetVersionId, metric_ids: metricIds },
      {
        onSuccess: (run) => {
          toast.success(run.status === "pending_traces" ? "Run created; push traces from the SDK to start it." : "Run queued.");
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Queue an evaluation run</DialogTitle>
          <DialogDescription>
            Deterministic checks run first with no model call; a judge-based metric runs only for the
            cases it applies to.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogBody className="space-y-4">
            <Field label="Agent" htmlFor="run-agent">
              <SimpleSelect
                id="run-agent"
                value={agentId}
                onValueChange={(v) => {
                  setAgentId(v);
                  setAgentVersionId("");
                }}
                placeholder="Choose an agent"
                options={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
              />
            </Field>
            <Field label="Agent version" htmlFor="run-agent-version">
              <SimpleSelect
                id="run-agent-version"
                value={agentVersionId}
                onValueChange={setAgentVersionId}
                placeholder={agentId ? "Choose a version" : "Choose an agent first"}
                options={(versions.data ?? []).map((v) => ({ value: v.id, label: v.label }))}
              />
            </Field>
            <Field label="Dataset" htmlFor="run-dataset" hint="Runs against that dataset's current version.">
              <SimpleSelect
                id="run-dataset"
                value={datasetVersionId}
                onValueChange={setDatasetVersionId}
                placeholder="Choose a dataset"
                options={(datasets.data ?? []).map((d) => ({ value: d.current_version_id, label: d.name }))}
              />
            </Field>
            <Field label="Metrics" htmlFor="run-metrics" error={error ?? undefined}>
              <div className="flex flex-wrap gap-x-4 gap-y-2">
                {ALL_METRICS.map((id) => (
                  <label key={id} className="flex items-center gap-1.5 text-[13px] text-foreground">
                    <Checkbox checked={metricIds.includes(id)} onCheckedChange={() => toggleMetric(id)} />
                    {id}
                  </label>
                ))}
              </div>
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={queue.isPending}>
              {queue.isPending ? "Queuing..." : "Queue run"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
