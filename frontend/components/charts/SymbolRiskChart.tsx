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

export default function SymbolRiskChart({ stats }: Props) {
  const data = stats.by_symbol.map((s) => ({
    symbol: s.stock_symbol,
    score: s.avg_score,
    level: s.latest_level,
  }));

  if (!data.length) {
    return (
      <div className="h-52 flex items-center justify-center text-gray-500 text-sm">
        Analyze symbols to compare average risk
      </div>
    );
  }

  return (
    <div className="h-52 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
          <XAxis type="number" domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 10 }} />
          <YAxis type="category" dataKey="symbol" tick={{ fill: "#9ca3af", fontSize: 11 }} width={48} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            formatter={(value) => [`${value ?? 0} avg`, "Risk Score"]}
          />
          <Bar dataKey="score" radius={[0, 4, 4, 0]}>
            {data.map((entry) => (
              <Cell key={entry.symbol} fill={entry.level === "red" ? "#ef4444" : "#10b981"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
