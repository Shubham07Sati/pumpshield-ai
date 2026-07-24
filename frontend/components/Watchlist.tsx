"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, AnalysisSummary } from "@/lib/api";

export default function Watchlist() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [history, setHistory] = useState<AnalysisSummary[]>([]);

  const loadWatchlist = () => {
    const saved = localStorage.getItem("watchlist");
    if (saved) {
      try {
        setSymbols(JSON.parse(saved));
      } catch (e) {}
    }
  };

  useEffect(() => {
    loadWatchlist();
    // Fetch recent analysis to map scores if available
    api.history(0, 50).then((res) => {
      setHistory(res.items);
    }).catch(() => {});

    // Listen for storage changes in case they modify it elsewhere
    window.addEventListener("storage", loadWatchlist);
    return () => window.removeEventListener("storage", loadWatchlist);
  }, []);

  const removeSymbol = (sym: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const updated = symbols.filter((s) => s !== sym);
    setSymbols(updated);
    localStorage.setItem("watchlist", JSON.stringify(updated));
    // Trigger custom event so other components know
    window.dispatchEvent(new Event("storage"));
  };

  if (symbols.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-800 bg-gray-900/10 p-6 text-center text-gray-500 text-sm">
        Your watchlist is empty. Search a stock and click "Add to Watchlist" to save it here.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
      {symbols.map((sym) => {
        // Find latest analysis score for this symbol
        const latest = history.find((h) => h.stock_symbol.toUpperCase() === sym.toUpperCase());
        const hasScore = latest !== undefined;
        const isRed = hasScore && latest.risk_score >= 80;

        return (
          <Link
            key={sym}
            href={`/analyze?symbol=${sym}`}
            className="group relative rounded-xl border border-gray-800 bg-gray-950/40 p-4 transition hover:border-gray-700 hover:bg-gray-900/40"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-bold text-lg text-white group-hover:text-emerald-400 transition">
                {sym}
              </span>
              <button
                onClick={(e) => removeSymbol(sym, e)}
                className="text-gray-500 hover:text-red-400 p-1 transition"
                title="Remove from watchlist"
              >
                ✕
              </button>
            </div>
            
            <div className="flex items-center justify-between mt-2">
              {hasScore ? (
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    isRed ? "bg-red-500/20 text-red-300" : "bg-emerald-500/20 text-emerald-300"
                  }`}>
                    Score: {latest.risk_score}
                  </span>
                  <span className="text-[10px] text-gray-500 uppercase tracking-wider">
                    {latest.risk_level} risk
                  </span>
                </div>
              ) : (
                <span className="text-xs text-gray-500">Not analyzed yet</span>
              )}
              <span className="text-xs text-emerald-500 group-hover:translate-x-1 transition duration-200">
                Analyze →
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
