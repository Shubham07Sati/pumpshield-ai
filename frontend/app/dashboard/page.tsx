"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import AnalysisHistoryTable from "@/components/AnalysisHistoryTable";
import StockSearchForm from "@/components/StockSearchForm";
import Watchlist from "@/components/Watchlist";
import NotionStatusBadge from "@/components/NotionStatusBadge";
import RiskDistributionChart from "@/components/charts/RiskDistributionChart";
import AnalysisTimelineChart from "@/components/charts/AnalysisTimelineChart";
import ScoreBucketChart from "@/components/charts/ScoreBucketChart";
import SymbolRiskChart from "@/components/charts/SymbolRiskChart";
import { useAuth } from "@/lib/useAuth";
import { api, AnalysisStats, AnalysisSummary } from "@/lib/api";
import { useRouter } from "next/navigation";

function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: string }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
      <p className="text-gray-400 text-sm">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${accent || "text-white"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const { user, loading } = useAuth(true);
  const router = useRouter();
  const [recent, setRecent] = useState<AnalysisSummary[]>([]);
  const [stats, setStats] = useState<AnalysisStats | null>(null);

  useEffect(() => {
    if (!loading) {
      api.history(0, 5).then((res) => setRecent(res.items)).catch(() => {});
      api.stats().then(setStats).catch(() => {});
    }
  }, [loading]);

  function handleSearch(symbol: string) {
    router.push(`/analyze?symbol=${encodeURIComponent(symbol)}`);
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading...</div>;
  }

  return (
    <>
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">Welcome, {user?.name}</h1>
            <p className="text-gray-400">
              AI-powered pump-and-dump detection with live market charts and Notion audit trail.
            </p>
          </div>
          <NotionStatusBadge />
        </div>

        <div className="mb-8">
          <StockSearchForm onSubmit={handleSearch} />
        </div>

        <div className="mb-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Search Examples</h2>
            <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5 space-y-4">
              <div className="border-l-2 border-emerald-500 pl-3">
                <p className="font-bold text-sm text-white">AAPL</p>
                <p className="text-xs text-gray-400">Large-cap, low volatility and steady volumes. (Safe baseline example)</p>
              </div>
              <div className="border-l-2 border-red-500 pl-3">
                <p className="font-bold text-sm text-white">GME</p>
                <p className="text-xs text-gray-400">High volatility and major volume spikes. (Classic pump indicators)</p>
              </div>
              <div className="border-l-2 border-yellow-500 pl-3">
                <p className="font-bold text-sm text-white">TSLA</p>
                <p className="text-xs text-gray-400">Elevated retail hype, active price swings, and moderate risks.</p>
              </div>
            </div>
          </div>
          <div className="lg:col-span-2">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">My Watchlist</h2>
            <Watchlist />
          </div>
        </div>

        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard label="Total analyses" value={stats.total} />
            <StatCard label="Avg risk score" value={stats.avg_score || "—"} />
            <StatCard label="Red zone alerts" value={stats.red_count} accent="text-red-400" sub="Score ≥ 80" />
            <StatCard label="Green zone" value={stats.green_count} accent="text-emerald-400" sub="Score &lt; 80" />
          </div>
        )}

        {stats && stats.total > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6">
              <h3 className="text-lg font-semibold mb-4">Risk zone split</h3>
              <RiskDistributionChart stats={stats} />
            </div>
            <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6">
              <h3 className="text-lg font-semibold mb-4">Score distribution</h3>
              <ScoreBucketChart stats={stats} />
            </div>
            <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6">
              <h3 className="text-lg font-semibold mb-4">Analysis timeline</h3>
              <AnalysisTimelineChart stats={stats} />
            </div>
            <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6">
              <h3 className="text-lg font-semibold mb-4">Avg risk by symbol</h3>
              <SymbolRiskChart stats={stats} />
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <p className="text-gray-400 text-sm">Risk Zones</p>
            <p className="text-lg font-semibold mt-1">
              <span className="text-emerald-400">Green 0–79</span>
              <span className="text-gray-600 mx-2">|</span>
              <span className="text-red-400">Red 80–100</span>
            </p>
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <p className="text-gray-400 text-sm">5 Indicators</p>
            <p className="text-sm text-gray-300 mt-1">Volume · Hype · Volatility · Institutional · Insider</p>
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <p className="text-gray-400 text-sm">Full History</p>
            <Link href="/history" className="text-emerald-400 hover:underline font-semibold">
              View all →
            </Link>
          </div>
        </div>

        <h2 className="text-xl font-semibold mb-4">Recent Analyses</h2>
        <AnalysisHistoryTable items={recent} />
      </main>
    </>
  );
}
