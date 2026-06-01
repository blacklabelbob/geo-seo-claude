import Link from "next/link";
import { scoreTier, scoreLabel, tierColor, statusMeta, type Tier } from "@/lib/scores";

export function Panel({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-line bg-panel p-5 ${className}`}
    >
      {children}
    </div>
  );
}

export function Kpi({
  value,
  label,
  color = "var(--color-ink)",
}: {
  value: React.ReactNode;
  label: string;
  color?: string;
}) {
  return (
    <Panel className="text-center">
      <div className="text-3xl font-extrabold leading-none" style={{ color }}>
        {value}
      </div>
      <div className="mt-2 text-[0.72rem] uppercase tracking-wider text-dim">
        {label}
      </div>
    </Panel>
  );
}

export function ScoreBar({ score }: { score: number | null }) {
  const tier = scoreTier(score);
  const color = tierColor[tier];
  return (
    <div className="flex items-center gap-2 min-w-[160px]">
      <div className="h-2 flex-1 overflow-hidden rounded bg-line">
        <div
          className="h-full rounded transition-all"
          style={{ width: `${score ?? 0}%`, background: color }}
        />
      </div>
      <span
        className="min-w-[68px] text-xs font-semibold whitespace-nowrap"
        style={{ color }}
      >
        {score === null ? "Not scored" : `${score}/100`}
      </span>
    </div>
  );
}

export function ScoreCircle({ score }: { score: number | null }) {
  const tier = scoreTier(score);
  const color = tierColor[tier];
  return (
    <div
      className="flex h-[110px] w-[110px] flex-shrink-0 flex-col items-center justify-center rounded-full font-bold"
      style={{ border: `4px solid ${color}`, color }}
    >
      {score === null ? (
        <>
          <span className="text-lg">N/A</span>
          <span className="mt-1 text-center text-[0.6rem] text-dim">
            No audit
            <br />
            yet
          </span>
        </>
      ) : (
        <>
          <span className="text-3xl leading-none">{score}</span>
          <span className="text-[0.7rem] text-dim">/100</span>
          <span className="mt-0.5 text-[0.65rem]">{scoreLabel(score)}</span>
        </>
      )}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const meta = statusMeta[status] ?? { label: status, badge: "#6c757d" };
  return (
    <span
      className="inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold text-white"
      style={{ background: meta.badge }}
    >
      {meta.label}
    </span>
  );
}

const sevColor: Record<string, string> = {
  critical: "#d63031",
  high: "#e94560",
  medium: "#fdcb6e",
  low: "#6c757d",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className="inline-block rounded-full px-2 py-0.5 text-[0.7rem] font-semibold uppercase"
      style={{
        color: sevColor[severity] ?? "#6c757d",
        border: `1px solid ${sevColor[severity] ?? "#6c757d"}`,
      }}
    >
      {severity}
    </span>
  );
}

export function TierDot({ tier }: { tier: Tier }) {
  return (
    <span
      className="inline-block h-2.5 w-2.5 rounded-full"
      style={{ background: tierColor[tier] }}
    />
  );
}

export function NavBar({ orgName }: { orgName?: string }) {
  return (
    <nav className="border-b-2 border-blue bg-navy">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="text-lg font-extrabold tracking-tight">
          GEO<span className="text-accent">·</span>Platform
          <span className="ml-2 hidden text-xs font-normal text-dim md:inline">
            AI Visibility for Contractors
          </span>
        </Link>
        <div className="flex items-center gap-4 text-sm">
          {orgName && <span className="text-dim">{orgName}</span>}
          <Link href="/pricing" className="text-dim hover:text-ink">
            Pricing
          </Link>
          <form action="/auth/signout" method="post">
            <button className="rounded-md border border-line px-3 py-1 text-dim hover:text-ink">
              Sign out
            </button>
          </form>
        </div>
      </div>
    </nav>
  );
}
