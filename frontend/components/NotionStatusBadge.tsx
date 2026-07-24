"use client";

import { useEffect, useState } from "react";
import { api, NotionHealth } from "@/lib/api";

export default function NotionStatusBadge() {
  const [status, setStatus] = useState<NotionHealth | null>(null);

  useEffect(() => {
    api.notionHealth().then(setStatus).catch(() => {});
  }, []);

  if (!status) return null;

  const ok = status.connected;
  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
        ok
          ? "bg-emerald-950/50 border-emerald-800 text-emerald-300"
          : status.configured
            ? "bg-yellow-950/50 border-yellow-800 text-yellow-300"
            : "bg-gray-900 border-gray-700 text-gray-400"
      }`}
      title={status.error || status.database_title}
    >
      <span className={`w-2 h-2 rounded-full ${ok ? "bg-emerald-400 animate-pulse" : "bg-yellow-500"}`} />
      {ok ? `Notion Audit Log · ${status.database_title}` : "Notion sync pending setup"}
    </div>
  );
}
