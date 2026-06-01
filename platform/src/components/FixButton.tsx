"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function FixButton({
  fixId,
  status,
}: {
  fixId: string;
  status: string;
}) {
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const done = status === "applied" || status === "verified";

  async function apply() {
    setLoading(true);
    try {
      const res = await fetch("/api/fix/apply", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ fix_id: fixId }),
      });
      if (res.ok) router.refresh();
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <span className="rounded-md border border-good px-3 py-1.5 text-xs font-semibold text-good">
        ✓ {status === "verified" ? "Verified" : "Applied"}
      </span>
    );
  }

  return (
    <button
      onClick={apply}
      disabled={loading}
      className="rounded-md bg-good px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
    >
      {loading ? "Applying…" : "Apply fix"}
    </button>
  );
}
