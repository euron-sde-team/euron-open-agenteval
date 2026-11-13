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
import { Field } from "@/components/ui/label";
import { errorMessage } from "@/lib/api/errors";
import type { Dataset, TestCaseIn, TestCaseOut } from "@/lib/api/types";

import { useCreateDatasetVersion } from "../api";

function testCasesToJson(cases: TestCaseOut[]): string {
  return JSON.stringify(
    cases.map((c) => ({ input: c.input, expected_behavior: c.expected_behavior, tags: c.tags })),
    null,
    2,
  );
}

function parseTestCases(text: string): { cases: TestCaseIn[] | null; error: string | null } {
  try {
    const parsed: unknown = JSON.parse(text);
    if (!Array.isArray(parsed) || parsed.length === 0) {
      return { cases: null, error: "Enter at least one test case." };
    }
    const cases: TestCaseIn[] = parsed.map((item) => {
      const obj = item as Record<string, unknown>;
      return {
        input: (obj.input as Record<string, unknown>) ?? {},
        expected_behavior: (obj.expected_behavior as TestCaseIn["expected_behavior"]) ?? {},
        tags: Array.isArray(obj.tags) ? (obj.tags as string[]) : [],
      };
    });
    return { cases, error: null };
  } catch {
    return { cases: null, error: "That is not valid JSON." };
  }
}

/** Replacing a dataset's test cases always creates a new version (AC10): this dialog
 * never offers to edit the current version in place, because that is not an operation
 * the server exposes, on purpose, so a past run's score can never silently change
 * meaning underneath it. */
export function CreateDatasetVersionDialog({
  orgId,
  dataset,
  currentTestCases,
  open,
  onOpenChange,
}: {
  orgId: string;
  dataset: Dataset;
  currentTestCases: TestCaseOut[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [casesText, setCasesText] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const create = useCreateDatasetVersion(orgId, dataset.id);

  React.useEffect(() => {
    if (open) setCasesText(testCasesToJson(currentTestCases));
  }, [open, currentTestCases]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const { cases, error: parseError } = parseTestCases(casesText);
    if (parseError || cases === null) {
      setError(parseError ?? "Could not read the test cases.");
      return;
    }
    setError(null);
    create.mutate(
      { test_cases: cases },
      {
        onSuccess: (version) => {
          toast.success(`Created version ${version.version_number} with ${version.test_case_count} test case(s).`);
          onOpenChange(false);
        },
        onError: (err) => setError(errorMessage(err)),
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New version of {dataset.name}</DialogTitle>
          <DialogDescription>
            Currently v{dataset.current_version_number}. Saving creates v{dataset.current_version_number + 1};
            every run already queued against v{dataset.current_version_number} keeps that exact reference.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogBody className="space-y-4">
            <Field label="Test cases (JSON)" htmlFor="version-cases" error={error ?? undefined}>
              <textarea
                id="version-cases"
                rows={14}
                value={casesText}
                onChange={(e) => setCasesText(e.target.value)}
                className="w-full rounded-lg border border-input bg-card px-3 py-2 font-mono text-[12.5px] text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving..." : "Create new version"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
