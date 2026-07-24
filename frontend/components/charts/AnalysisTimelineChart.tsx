"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalysisStats } from "@/lib/api";

interface Props {
  stats: AnalysisStats;
}

function barColor(score: number) {
  if (score >= 80) return "#ef4444";
  if (score >= 60) return "#f97316";
  if (score >= 40) return "#eab308";
  return "#10b981";
}

export default function AnalysisTimelineChart({ stats }: Props) {
  const data = stats.timeline.map((t) => ({
    label: `${t.stock_symbol}`,
    score: t.score,
    date: t.date,
    level: t.risk_level,
  }));

  if (!data.length) {
    return (
      <div className="h-52 flex items-center justify-center text-gray-500 text-sm">
        No timeline data yet
      </div>
    );
  }

  return (
    <div className="h-52 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: "#9ca3af", fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 10 }} width={32} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            formatter={(value, _n, props) => [
              `${value ?? 0}/100 (${(props?.payload as { level?: string })?.level ?? ""})`,
              (props?.payload as { date?: string })?.date ?? "",
            ]}
          />
          <Bar dataKey="score" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.label + entry.date} fill={barColor(entry.score)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
