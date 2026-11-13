"use client";

import { SearchIcon, WaypointsIcon } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Surface } from "@/components/surface";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/ui/label";

/**
 * The API does not expose a "list every trace" endpoint (apps/api/src/agenteval/traces/
 * router.py only has ingest, get-by-id, and get-by-run-and-case), so this screen is
 * honestly a lookup, not a browsable index: paste a trace id (from a run's result
 * detail, which always links to its own trace) to open it. Listing traces is a real
 * gap for a future release, not something faked here with an invented endpoint.
 */
export function TracesScreen() {
  const [traceId, setTraceId] = React.useState("");
  const [submittedId, setSubmittedId] = React.useState<string | null>(null);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (traceId.trim()) setSubmittedId(traceId.trim());
  }

  return (
    <>
      <PageHeader
        title="Execution traces"
        description="Every run's trace is linked from its result in the Evaluations screen. Open one here by id, or follow a link from a result."
      />
      <Surface className="p-5">
        <form onSubmit={submit} className="flex items-end gap-3">
          <Field label="Trace id" htmlFor="trace-lookup" className="flex-1">
            <Input
              id="trace-lookup"
              placeholder="Paste a trace id"
              value={traceId}
              onChange={(e) => setTraceId(e.target.value)}
            />
          </Field>
          <Button type="submit">
            <SearchIcon />
            Open
          </Button>
        </form>
      </Surface>
      {submittedId ? (
        <div className="mt-4">
          <Link href={`/traces/${submittedId}`} className="text-[13px] text-primary hover:underline">
            Open trace {submittedId}
          </Link>
        </div>
      ) : (
        <div className="mt-4">
          <EmptyState
            icon={WaypointsIcon}
            title="No trace open"
            description="Open any evaluation run from the Evaluations screen and expand a result: every scored test case links straight to the trace that produced it."
            action={
              <Link href="/evaluations" className="text-[13px] text-primary hover:underline">
                Go to Evaluations
              </Link>
            }
          />
        </div>
      )}
    </>
  );
}
