"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalysisStats } from "@/lib/api";

interface Props {
  stats: AnalysisStats;
}

export default function ScoreBucketChart({ stats }: Props) {
  const data = stats.score_buckets;

  if (!stats.total) {
    return (
      <div className="h-52 flex items-center justify-center text-gray-500 text-sm">
        Score distribution appears after first analysis
      </div>
    );
  }

  return (
    <div className="h-52 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: "#9ca3af", fontSize: 10 }} />
          <YAxis allowDecimals={false} tick={{ fill: "#6b7280", fontSize: 10 }} width={28} />
          <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }} />
          <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
