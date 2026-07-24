"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Navbar from "@/components/Navbar";
import RiskScoreCard from "@/components/RiskScoreCard";
import IndicatorBreakdown from "@/components/IndicatorBreakdown";
import StockSearchForm from "@/components/StockSearchForm";
import NotionStatusBadge from "@/components/NotionStatusBadge";
import RiskGauge from "@/components/charts/RiskGauge";
import IndicatorRadarChart from "@/components/charts/IndicatorRadarChart";
import PriceTrendChart from "@/components/charts/PriceTrendChart";
import VolumeCompareChart from "@/components/charts/VolumeCompareChart";
import { useAuth } from "@/lib/useAuth";
import { api, Analysis } from "@/lib/api";

function MarketMetrics({ analysis }: { analysis: Analysis }) {
  const ctx = analysis.market_context;
  if (!ctx) return null;

  const metrics = [
    { label: "Price", value: ctx.current_price != null ? `$${ctx.current_price.toFixed(2)}` : "—" },
    {
      label: "3-day change",
      value: ctx.recent_price_change_pct != null ? `${ctx.recent_price_change_pct.toFixed(1)}%` : "—",
    },
    {
      label: "Volatility",
      value: ctx.daily_return_std != null ? `${(ctx.daily_return_std * 100).toFixed(1)}%` : "—",
    },
    {
      label: "Institutional",
      value: ctx.institutional_ownership_pct != null ? `${ctx.institutional_ownership_pct.toFixed(0)}%` : "—",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {metrics.map((m) => (
        <div key={m.label} className="rounded-lg bg-gray-950/60 border border-gray-800 px-3 py-2">
          <p className="text-xs text-gray-500">{m.label}</p>
          <p className="font-semibold text-sm">{m.value}</p>
        </div>
      ))}
    </div>
  );
}

function AnalyzeContent() {
  const { loading: authLoading } = useAuth(true);
  const searchParams = useSearchParams();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [watchlist, setWatchlist] = useState<string[]>([]);

  useEffect(() => {
    const saved = localStorage.getItem("watchlist");
    if (saved) {
      try {
        setWatchlist(JSON.parse(saved));
      } catch (e) {}
    }
  }, []);

  const toggleWatchlist = (symbol: string) => {
    let updated = [...watchlist];
    if (watchlist.includes(symbol)) {
      updated = updated.filter((s) => s !== symbol);
    } else {
      updated.push(symbol);
    }
    setWatchlist(updated);
    localStorage.setItem("watchlist", JSON.stringify(updated));
  };

  const runAnalysis = useCallback(async (symbol: string) => {
    setError("");
    setLoading(true);
    setAnalysis(null);
    try {
      const result = await api.analyze(symbol);
      setAnalysis(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const symbol = searchParams.get("symbol");
    const id = searchParams.get("id");
    if (id && !authLoading) {
      api.getAnalysis(Number(id)).then(setAnalysis).catch((e) => setError(e.message));
    } else if (symbol && !authLoading) {
      runAnalysis(symbol);
    }
  }, [searchParams, authLoading, runAnalysis]);

  if (authLoading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading...</div>;
  }

  return (
    <>
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">Stock Analysis</h1>
            <p className="text-gray-400">Real-time charts + 5-indicator fraud risk engine powered by Gemini AI.</p>
          </div>
          <NotionStatusBadge />
        </div>

        <div className="mb-8">
          <StockSearchForm onSubmit={runAnalysis} loading={loading} />
        </div>

        {error && (
          <div className="mb-6 text-red-400 bg-red-950/50 border border-red-800 rounded-xl p-4 text-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="text-center py-16 text-gray-400">
            <div className="inline-block w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mb-4" />
            <p>Collecting market data and running AI analysis...</p>
            <p className="text-xs text-gray-600 mt-2">Syncing to Notion audit log on completion</p>
          </div>
        )}

        {analysis && !loading && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-300">Analysis for {analysis.stock_symbol}</h2>
              <button
                onClick={() => toggleWatchlist(analysis.stock_symbol)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
                  watchlist.includes(analysis.stock_symbol)
                    ? "bg-yellow-500/20 text-yellow-300 border border-yellow-500/50 hover:bg-yellow-500/30"
                    : "bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700"
                }`}
              >
                {watchlist.includes(analysis.stock_symbol) ? "★ Watchlisted" : "☆ Add to Watchlist"}
              </button>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <RiskScoreCard analysis={analysis} />
              </div>
              <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6 flex flex-col items-center justify-center">
                <h3 className="text-sm font-semibold text-gray-400 mb-4 self-start">Risk gauge</h3>
                <RiskGauge score={analysis.risk_score} level={analysis.risk_level} />
                {analysis.market_context?.company_name && (
                  <p className="text-xs text-gray-500 mt-4 text-center">{analysis.market_context.company_name}</p>
                )}
              </div>
            </div>

            {analysis.market_context && (
              <>
                <MarketMetrics analysis={analysis} />
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6">
                    <h3 className="text-lg font-semibold mb-4">30-day price trend</h3>
                    <PriceTrendChart
                      data={analysis.market_context.price_series || []}
                      symbol={analysis.stock_symbol}
                    />
                  </div>
                  <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6">
                    <h3 className="text-lg font-semibold mb-4">Volume analysis</h3>
                    <VolumeCompareChart context={analysis.market_context} />
                  </div>
                </div>
              </>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <IndicatorBreakdown indicators={analysis.indicators} />
              <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6">
                <h3 className="text-lg font-semibold mb-2">Indicator radar</h3>
                <p className="text-xs text-gray-500 mb-4">Normalized risk contribution per signal</p>
                <IndicatorRadarChart indicators={analysis.indicators} />
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-gray-400">Loading...</div>}>
      <AnalyzeContent />
    </Suspense>
  );
}
