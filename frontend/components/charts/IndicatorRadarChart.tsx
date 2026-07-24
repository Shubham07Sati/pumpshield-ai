"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { IndicatorScore } from "@/lib/api";

interface Props {
  indicators: IndicatorScore[];
}

export default function IndicatorRadarChart({ indicators }: Props) {
  const data = indicators.map((ind) => ({
    name: ind.name.replace("Low ", "").replace("Social Media ", "Social "),
    pct: ind.max_score > 0 ? Math.round((ind.score / ind.max_score) * 100) : 0,
    score: ind.score,
    max: ind.max_score,
  }));

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="#374151" />
          <PolarAngleAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 11 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 10 }} />
          <Radar
            name="Risk %"
            dataKey="pct"
            stroke="#10b981"
            fill="#10b981"
            fillOpacity={0.35}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            formatter={(value, _name, props) => [
              `${(props?.payload as { score?: number })?.score ?? 0}/${(props?.payload as { max?: number })?.max ?? 0} (${value ?? 0}%)`,
              "Indicator",
            ]}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
