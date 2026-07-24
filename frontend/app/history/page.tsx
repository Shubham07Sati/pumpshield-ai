"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import AnalysisHistoryTable from "@/components/AnalysisHistoryTable";
import AnalysisTimelineChart from "@/components/charts/AnalysisTimelineChart";
import ScoreBucketChart from "@/components/charts/ScoreBucketChart";
import { useAuth } from "@/lib/useAuth";
import { api, AnalysisStats, AnalysisSummary } from "@/lib/api";

export default function HistoryPage() {
  const { loading: authLoading } = useAuth(true);
  const [items, setItems] = useState<AnalysisSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<AnalysisStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading) {
      Promise.all([api.history(0, 50), api.stats()])
        .then(([history, s]) => {
          setItems(history.items);
          setTotal(history.total);
          setStats(s);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [authLoading]);

  if (authLoading || loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading...</div>;
  }

  return (
    <>
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-2">Analysis History</h1>
        <p className="text-gray-400 mb-8">{total} total analyses · synced to Notion audit log</p>

        {stats && stats.total > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6">
              <h3 className="text-lg font-semibold mb-4">Risk scores over time</h3>
              <AnalysisTimelineChart stats={stats} />
            </div>
            <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6">
              <h3 className="text-lg font-semibold mb-4">Score distribution</h3>
              <ScoreBucketChart stats={stats} />
            </div>
          </div>
        )}

        <div className="rounded-2xl border border-gray-800 bg-gray-900/50 p-6">
          <AnalysisHistoryTable items={items} />
        </div>
      </main>
    </>
  );
}
