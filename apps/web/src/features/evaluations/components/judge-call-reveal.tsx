"use client";

import { EyeIcon } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/error-state";

import { useJudgeCall } from "../api";

/**
 * The raw judge prompt and response behind a judge-scored result, kept behind an
 * explicit click, never auto-fetched: the server's own GET endpoint is itself an
 * audited reveal (AC4), so this component only calls it once a person actually asks.
 */
export function JudgeCallReveal({ orgId, resultId }: { orgId: string; resultId: string }) {
  const [revealed, setRevealed] = React.useState(false);
  const judgeCall = useJudgeCall(orgId, resultId, revealed);

  if (!revealed) {
    return (
      <Button variant="outline" size="sm" onClick={() => setRevealed(true)}>
        <EyeIcon />
        Reveal judge prompt and response
      </Button>
    );
  }

  if (judgeCall.isPending) {
    return <p className="text-[13px] text-muted-foreground">Loading...</p>;
  }
  if (judgeCall.isError) {
    return <ErrorState error={judgeCall.error} onRetry={() => void judgeCall.refetch()} compact />;
  }

  return (
    <div className="space-y-3">
      <div>
        <div className="mb-1 text-[11.5px] font-semibold text-muted-foreground uppercase tracking-wide">
          Prompt sent to the judge
        </div>
        <pre className="overflow-x-auto rounded-lg bg-muted px-3 py-2 font-mono text-[11.5px] whitespace-pre-wrap text-foreground">
          {judgeCall.data.prompt}
        </pre>
      </div>
      <div>
        <div className="mb-1 text-[11.5px] font-semibold text-muted-foreground uppercase tracking-wide">
          Raw judge response
        </div>
        <pre className="overflow-x-auto rounded-lg bg-muted px-3 py-2 font-mono text-[11.5px] whitespace-pre-wrap text-foreground">
          {judgeCall.data.raw_response}
        </pre>
      </div>
    </div>
  );
}
