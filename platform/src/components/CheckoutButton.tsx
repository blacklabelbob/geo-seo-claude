"use client";

import { useState } from "react";

export function CheckoutButton({
  plan,
  label,
  className = "",
}: {
  plan: string;
  label: string;
  className?: string;
}) {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function go() {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch("/api/stripe/checkout", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ plan }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error ?? "Checkout unavailable");
      if (body.url) window.location.href = body.url;
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Checkout unavailable");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <button
        onClick={go}
        disabled={loading}
        className={`w-full rounded-md py-2 text-sm font-semibold disabled:opacity-50 ${className}`}
      >
        {loading ? "…" : label}
      </button>
      {err && <p className="mt-2 text-center text-xs text-poor">{err}</p>}
    </div>
  );
}
