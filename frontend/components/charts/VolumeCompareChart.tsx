"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MarketContext } from "@/lib/api";

interface Props {
  context: MarketContext;
}

function fmtVol(v: number | undefined) {
  if (!v) return "—";
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(Math.round(v));
}

export default function VolumeCompareChart({ context }: Props) {
  const ratio = context.volume_spike_ratio ?? 1;
  const data = [
    { name: "30-day avg", volume: context.avg_volume_30d ?? 0 },
    { name: "3-day avg", volume: context.avg_volume_3d ?? 0 },
  ];

  const spikeColor = ratio >= 2 ? "#ef4444" : ratio >= 1.5 ? "#eab308" : "#10b981";

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-400">Volume comparison</span>
        <span className="text-sm font-medium" style={{ color: spikeColor }}>
          {ratio.toFixed(2)}× spike ratio
        </span>
      </div>
      <div className="h-44 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 11 }} />
            <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={fmtVol} width={48} />
            <Tooltip
              contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
              formatter={(value) => [fmtVol(Number(value ?? 0)), "Volume"]}
            />
            <Bar dataKey="volume" radius={[6, 6, 0, 0]}>
              {data.map((_, i) => (
                <Cell key={i} fill={i === 1 ? spikeColor : "#374151"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
