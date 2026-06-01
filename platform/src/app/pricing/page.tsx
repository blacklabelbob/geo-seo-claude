import Link from "next/link";
import { CheckoutButton } from "@/components/CheckoutButton";

const tiers = [
  {
    stage: "Hook · PVP",
    name: "AI Visibility Snapshot",
    price: "Free",
    bullets: [
      "GEO score 0–100",
      '"What ChatGPT says about you"',
      "Competitor gap (named)",
      "Top 3 critical gaps",
    ],
    cta: null as null | { plan?: string; href?: string; label: string },
    accent: "#6c757d",
  },
  {
    stage: "Diagnose",
    name: "Full Diagnostic",
    price: "$497",
    unit: "one-time",
    bullets: [
      "50-page audit",
      "Platform-by-platform readiness",
      "30-60-90 roadmap",
      "45-min strategy call",
    ],
    cta: { href: "/signup", label: "Start diagnostic" },
    accent: "#0f3460",
  },
  {
    stage: "Prescription",
    name: "Auto-Remediate",
    price: "$597",
    unit: "/mo",
    bullets: [
      "Software applies all auto-fixes",
      "Monthly score-delta report",
      "Self-serve dashboard",
      "Edge-served llms.txt + schema",
    ],
    cta: { plan: "pro", label: "Subscribe" },
    accent: "#00b894",
    featured: true,
  },
  {
    stage: "Treatment",
    name: "AI Authority Build",
    price: "$2,997",
    unit: "/mo",
    bullets: [
      "Wikipedia / entity building",
      "Digital PR + citations",
      "E-E-A-T content",
      "Dedicated account manager",
    ],
    cta: { href: "mailto:sales@stg.example?subject=AI%20Authority%20Build", label: "Talk to sales" },
    accent: "#e94560",
  },
];

export default function Pricing() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <div className="mb-2 text-center">
        <Link href="/" className="text-lg font-extrabold">
          GEO<span className="text-accent">·</span>Platform
        </Link>
      </div>
      <h1 className="mb-1 text-center text-2xl font-extrabold">
        Diagnose → Prescription → Treatment
      </h1>
      <p className="mb-8 text-center text-sm text-dim">
        Audit is the hook. Software does the recurring fixes. Humans do the premium work.
      </p>

      <div className="grid gap-4 md:grid-cols-4">
        {tiers.map((t) => (
          <div
            key={t.name}
            id={t.name === "AI Authority Build" ? "premium" : undefined}
            className="relative overflow-hidden rounded-xl border border-line bg-panel p-5"
          >
            <div
              className="absolute inset-x-0 top-0 h-1"
              style={{ background: t.accent }}
            />
            <div className="text-[0.7rem] uppercase tracking-wider text-dim">
              {t.stage}
            </div>
            <div className="mt-1 text-lg font-bold">{t.name}</div>
            <div className="my-2 text-3xl font-extrabold">
              {t.price}
              {"unit" in t && t.unit && (
                <span className="text-sm font-medium text-dim"> {t.unit}</span>
              )}
            </div>
            <ul className="mb-4 space-y-1 text-sm text-dim">
              {t.bullets.map((b) => (
                <li key={b}>• {b}</li>
              ))}
            </ul>
            {t.cta?.plan ? (
              <CheckoutButton
                plan={t.cta.plan}
                label={t.cta.label}
                className="bg-good text-white"
              />
            ) : t.cta?.href ? (
              <a
                href={t.cta.href}
                className="block rounded-md border border-line py-2 text-center text-sm font-semibold hover:border-link"
              >
                {t.cta.label}
              </a>
            ) : (
              <Link
                href="/signup"
                className="block rounded-md border border-line py-2 text-center text-sm font-semibold hover:border-link"
              >
                Get free snapshot
              </Link>
            )}
          </div>
        ))}
      </div>
    </main>
  );
}
