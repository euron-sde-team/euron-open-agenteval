"use client";

import * as React from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ChartTooltipCard } from "@/components/charts/chart-tooltip";
import type { EvaluationResult } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";

/** Mean score per metric across the latest completed run's own results, never a
 * cross-run composite: this chart is a snapshot of one run, not a trend (the
 * Benchmarks screen is where trends across runs belong). */
export function MetricChart({ results }: { results: EvaluationResult[] }) {
  const data = React.useMemo(() => {
    const byMetric = new Map<string, number[]>();
    for (const r of results) {
      const list = byMetric.get(r.metric_id) ?? [];
      list.push(r.score);
      byMetric.set(r.metric_id, list);
    }
    return [...byMetric.entries()]
      .map(([metric_id, scores]) => ({
        metric_id,
        mean: scores.reduce((a, b) => a + b, 0) / scores.length,
      }))
      .sort((a, b) => a.metric_id.localeCompare(b.metric_id));
  }, [results]);

  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-[13px] text-muted-foreground">
        No evaluation results yet.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={224}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
        <XAxis dataKey="metric_id" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "var(--chart-axis)" }} />
        <YAxis
          domain={[0, 1]}
          tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
          axisLine={false}
          tickLine={false}
          width={36}
          tick={{ fontSize: 12, fill: "var(--chart-axis)" }}
        />
        <Tooltip
          cursor={{ fill: "var(--muted)" }}
          content={({ active, payload }) => {
            if (!active || !payload?.[0]) return null;
            const point = payload[0].payload as { metric_id: string; mean: number };
            return (
              <ChartTooltipCard
                title={point.metric_id}
                rows={[{ label: "Mean score", value: `${formatNumber(Math.round(point.mean * 100))}%`, color: "var(--primary)" }]}
              />
            );
          }}
        />
        <Bar dataKey="mean" radius={[6, 6, 0, 0]} maxBarSize={56}>
          {data.map((d) => (
            <Cell key={d.metric_id} fill="var(--chart-spend)" />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
