"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PricePoint } from "@/lib/api";

interface Props {
  data: PricePoint[];
  symbol: string;
}

export default function PriceTrendChart({ data, symbol }: Props) {
  if (!data.length) {
    return <div className="h-56 flex items-center justify-center text-gray-500 text-sm">No price history available</div>;
  }

  const tickFormatter = (v: string) => (v.length > 10 ? v.slice(5) : v);

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={tickFormatter} />
          <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} domain={["auto", "auto"]} width={55} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            formatter={(value) => [`$${Number(value ?? 0).toFixed(2)}`, `${symbol} Close`]}
          />
          <Area type="monotone" dataKey="close" stroke="#10b981" fill="url(#priceGrad)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
