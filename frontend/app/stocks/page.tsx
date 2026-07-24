"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { api, AnalysisSummary } from "@/lib/api";

interface CombinedStock extends AnalysisSummary {
  source: "Notion" | "Local DB";
}

export default function StocksPage() {
  const [stocks, setStocks] = useState<CombinedStock[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      api.history(0, 100),
      api.notionStocks()
    ]).then(([historyRes, notionRes]) => {
      const mergedMap = new Map<string, CombinedStock>();

      // Process Local DB history items
      if (historyRes.status === "fulfilled") {
        historyRes.value.items.forEach((item) => {
          const sym = item.stock_symbol.toUpperCase();
          if (sym !== "UNKNOWN") {
            mergedMap.set(sym, {
              ...item,
              source: "Local DB"
            });
          }
        });
      }

      // Process Notion items (override only if Notion record is newer or not already present)
      if (notionRes.status === "fulfilled") {
        notionRes.value.items.forEach((item) => {
          const sym = item.stock_symbol.toUpperCase();
          if (sym !== "UNKNOWN") {
            const existing = mergedMap.get(sym);
            if (!existing) {
              mergedMap.set(sym, {
                ...item,
                source: "Notion"
              });
            } else {
              // Compare timestamps to keep the latest one
              const existingTime = new Date(existing.created_at).getTime();
              const newTime = item.created_at ? new Date(item.created_at).getTime() : 0;
              if (newTime > existingTime) {
                mergedMap.set(sym, {
                  ...item,
                  source: "Notion"
                });
              }
            }
          }
        });
      }

      // Sort by date analyzed (descending)
      const sorted = Array.from(mergedMap.values()).sort((a, b) => {
        const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return timeB - timeA;
      });

      setStocks(sorted);
    })
    .catch(() => {})
    .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading...</div>;
  }

  return (
    <>
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-2">All Stocks Data</h1>
        <p className="text-gray-400 mb-8">
          A unified list of all unique stocks tracked in the Notion audit log and local database.
        </p>

        {stocks.length === 0 ? (
          <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-8 text-center text-gray-500">
            No stocks found. Go to the <Link href="/analyze" className="text-emerald-400 hover:underline">Analyze</Link> page to scan your first stock.
          </div>
        ) : (
          <div className="rounded-2xl border border-gray-800 bg-gray-900/50 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-950/40 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                    <th className="py-4 px-6">Symbol</th>
                    <th className="py-4 px-6">Source</th>
                    <th className="py-4 px-6">Risk Level</th>
                    <th className="py-4 px-6 text-center">Risk Score</th>
                    <th className="py-4 px-6">Date Analyzed</th>
                    <th className="py-4 px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 text-sm">
                  {stocks.map((stock) => {
                    const isRed = stock.risk_level === "red";
                    const formattedDate = stock.created_at ? new Date(stock.created_at).toLocaleDateString(undefined, {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit"
                    }) : "N/A";

                    return (
                      <tr key={`${stock.source}-${stock.stock_symbol}`} className="hover:bg-gray-900/20 transition">
                        <td className="py-4 px-6 font-bold text-white text-base">
                          {stock.stock_symbol}
                        </td>
                        <td className="py-4 px-6">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                              stock.source === "Notion"
                                ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                                : "bg-gray-800 text-gray-300 border border-gray-700"
                            }`}
                          >
                            {stock.source}
                          </span>
                        </td>
                        <td className="py-4 px-6">
                          <span
                            className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                              isRed ? "bg-red-500/20 text-red-300" : "bg-emerald-500/20 text-emerald-300"
                            }`}
                          >
                            {isRed ? "High Risk" : "Low Risk"}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-center">
                          <span className={`text-lg font-extrabold ${isRed ? "text-red-400" : "text-emerald-400"}`}>
                            {stock.risk_score}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-gray-400">
                          {formattedDate}
                        </td>
                        <td className="py-4 px-6 text-right space-x-3">
                          <Link
                            href={`/analyze?symbol=${stock.stock_symbol}`}
                            className="inline-flex items-center text-xs font-semibold text-emerald-400 hover:text-emerald-300 hover:underline"
                          >
                            View Analysis
                          </Link>
                          <span className="text-gray-700">|</span>
                          <Link
                            href={`/analyze?symbol=${stock.stock_symbol}`}
                            className="inline-flex items-center text-xs font-semibold text-gray-400 hover:text-white hover:underline"
                          >
                            Re-analyze
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
