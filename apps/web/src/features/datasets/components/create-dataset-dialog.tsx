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
import type { TestCaseIn } from "@/lib/api/types";

import { useCreateDataset } from "../api";

function parseTestCases(text: string): { cases: TestCaseIn[] | null; error: string | null } {
  if (!text.trim()) return { cases: [], error: null };
  try {
    const parsed: unknown = JSON.parse(text);
    if (!Array.isArray(parsed)) return { cases: null, error: "JSON must be an array of test cases." };
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

const EXAMPLE = `[
  {
    "input": { "customer_message": "Can I get a refund?" },
    "expected_behavior": {
      "description": "Explain the 30 day refund policy without inventing terms",
      "forbidden_tool_calls": ["issue_refund"]
    },
    "tags": ["refunds"]
  }
]`;

export function CreateDatasetDialog({
  orgId,
  open,
  onOpenChange,
}: {
  orgId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [name, setName] = React.useState("");
  const [casesText, setCasesText] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const create = useCreateDataset(orgId);

  function reset() {
    setName("");
    setCasesText("");
    setError(null);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Enter a name for this dataset.");
      return;
    }
    const { cases, error: parseError } = parseTestCases(casesText);
    if (parseError || cases === null) {
      setError(parseError ?? "Could not read the test cases.");
      return;
    }
    setError(null);
    create.mutate(
      { name: name.trim(), test_cases: cases },
      {
        onSuccess: (dataset) => {
          toast.success(`Created ${dataset.name} with ${dataset.test_case_count} test case(s).`);
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
          <DialogTitle>Create a dataset</DialogTitle>
          <DialogDescription>
            Paste test cases as a JSON array. Add or edit cases later from the dataset&rsquo;s own page, which
            creates a new version rather than changing this one.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogBody className="space-y-4">
            <Field label="Name" htmlFor="dataset-name">
              <Input
                id="dataset-name"
                placeholder="customer-support-tests"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Field
              label="Test cases (JSON, optional)"
              htmlFor="dataset-cases"
              hint="Leave empty to create a dataset with no test cases yet."
              error={error ?? undefined}
            >
              <textarea
                id="dataset-cases"
                rows={10}
                placeholder={EXAMPLE}
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
              {create.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
