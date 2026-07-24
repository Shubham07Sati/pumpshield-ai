"use client";

import Link from "next/link";

const demos = [
  {
    symbol: "AAPL",
    label: "Safe baseline",
    desc: "Large-cap, low manipulation signals",
    color: "emerald",
  },
  {
    symbol: "GME",
    label: "High-risk demo",
    desc: "Volume spike + volatility — classic pump pattern",
    color: "red",
  },
  {
    symbol: "TSLA",
    label: "Moderate watch",
    desc: "Elevated hype and volatility indicators",
    color: "yellow",
  },
];

const colorMap = {
  emerald: "border-emerald-800/60 hover:border-emerald-600 bg-emerald-950/20",
  red: "border-red-800/60 hover:border-red-600 bg-red-950/20",
  yellow: "border-yellow-800/60 hover:border-yellow-600 bg-yellow-950/20",
};

export default function DemoStockCards() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {demos.map((d) => (
        <Link
          key={d.symbol}
          href={`/analyze?symbol=${d.symbol}`}
          className={`rounded-xl border p-4 transition ${colorMap[d.color as keyof typeof colorMap]}`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-bold text-lg">{d.symbol}</span>
            <span className="text-xs text-gray-500">Demo →</span>
          </div>
          <p className="text-sm font-medium text-gray-200">{d.label}</p>
          <p className="text-xs text-gray-500 mt-1">{d.desc}</p>
        </Link>
      ))}
    </div>
  );
}
