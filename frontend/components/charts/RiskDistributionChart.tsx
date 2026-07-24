"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { AnalysisStats } from "@/lib/api";

interface Props {
  stats: AnalysisStats;
}

export default function RiskDistributionChart({ stats }: Props) {
  const data = [
    { name: "Green (Low)", value: stats.green_count, color: "#10b981" },
    { name: "Red (High)", value: stats.red_count, color: "#ef4444" },
  ].filter((d) => d.value > 0);

  if (!stats.total) {
    return (
      <div className="h-52 flex items-center justify-center text-gray-500 text-sm">
        Run analyses to see risk distribution
      </div>
    );
  }

  return (
    <div className="h-52 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={75}
            paddingAngle={4}
            dataKey="value"
            nameKey="name"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} stroke="transparent" />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-4 -mt-2 text-xs">
        {data.map((d) => (
          <span key={d.name} className="flex items-center gap-1.5 text-gray-400">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: d.color }} />
            {d.name}: {d.value}
          </span>
        ))}
      </div>
    </div>
  );
}
