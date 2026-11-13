"use client";

import * as React from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ChartTooltipCard } from "@/components/charts/chart-tooltip";
import type { BenchmarkTrend } from "@/lib/api/types";

const LINE_COLORS = ["var(--chart-spend)", "var(--chart-avoided)", "var(--chart-rejected)", "var(--info)", "var(--warning)"];

/** AC9: every metric's mean score across more than two runs, oldest first, as a real
 * trend rather than only ever a pairwise diff. */
export function TrendChart({ trend, runOrder }: { trend: BenchmarkTrend; runOrder: string[] }) {
  const metricIds = Object.keys(trend.series);

  const data = React.useMemo(() => {
    return runOrder.map((runId, index) => {
      const point: Record<string, number | string> = { run: `#${index + 1}`, runId };
      for (const metricId of metricIds) {
        const series = trend.series[metricId] ?? [];
        const match = series.find((p) => p.run_id === runId);
        if (match) point[metricId] = Math.round(match.mean_score * 100);
      }
      return point;
    });
  }, [trend, runOrder, metricIds]);

  if (metricIds.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-[13px] text-muted-foreground">
        No shared metrics across these runs.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
        <XAxis dataKey="run" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "var(--chart-axis)" }} />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          axisLine={false}
          tickLine={false}
          width={36}
          tick={{ fontSize: 12, fill: "var(--chart-axis)" }}
        />
        <Tooltip
          cursor={{ stroke: "var(--border)" }}
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <ChartTooltipCard
                title={String(label)}
                rows={payload.map((p) => ({
                  label: String(p.dataKey),
                  value: `${p.value}%`,
                  color: String(p.color),
                }))}
              />
            );
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {metricIds.map((metricId, i) => (
          <Line
            key={metricId}
            type="monotone"
            dataKey={metricId}
            stroke={LINE_COLORS[i % LINE_COLORS.length]}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
