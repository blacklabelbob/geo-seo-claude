"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function RunAuditButton({ siteId }: { siteId: string }) {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const router = useRouter();

  async function run() {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch("/api/audit/trigger", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ site_id: siteId }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error ?? "Audit failed");
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Audit failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={run}
        disabled={loading}
        className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
      >
        {loading ? "Running audit…" : "Run GEO audit"}
      </button>
      {err && <span className="text-xs text-poor">{err}</span>}
    </div>
  );
}
