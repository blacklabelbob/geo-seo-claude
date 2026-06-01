import Link from "next/link";
import { notFound } from "next/navigation";
import { requireUser, getPrimaryOrg } from "@/lib/auth";
import {
  NavBar,
  Panel,
  ScoreCircle,
  StatusBadge,
  SeverityBadge,
} from "@/components/ui";
import { RunAuditButton } from "@/components/RunAuditButton";
import { FixButton } from "@/components/FixButton";

export default async function SiteDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { supabase } = await requireUser();
  const org = await getPrimaryOrg(supabase);

  const { data: site } = await supabase
    .from("sites")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (!site) notFound();

  const { data: latestAudit } = await supabase
    .from("audits")
    .select("*")
    .eq("site_id", id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const [{ data: findings }, { data: fixes }, { data: deliverables }] =
    await Promise.all([
      latestAudit
        ? supabase
            .from("audit_findings")
            .select("*")
            .eq("audit_id", latestAudit.id)
            .order("severity")
        : Promise.resolve({ data: [] as never[] }),
      supabase.from("fixes").select("*").eq("site_id", id),
      supabase.from("deliverables").select("*").eq("site_id", id),
    ]);

  const fixList = fixes ?? [];
  const appliedCount = fixList.filter(
    (f) => f.status === "applied" || f.status === "verified",
  ).length;
  const premiumFindings = (findings ?? []).filter((f) => !f.automatable);
  const premiumImpact = premiumFindings.length * 3; // rough estimate for display

  const appBase = process.env.NEXT_PUBLIC_APP_URL ?? "";

  return (
    <>
      <NavBar orgName={org?.name} />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <nav className="mb-4 text-sm text-dim">
          <Link href="/" className="hover:text-link">
            Dashboard
          </Link>{" "}
          / <span className="text-ink">{site.name ?? site.domain}</span>
        </nav>

        {/* Header */}
        <div className="mb-6 flex flex-wrap items-start gap-5">
          <ScoreCircle score={latestAudit?.score_overall ?? null} />
          <div className="flex-1">
            <h1 className="text-2xl font-extrabold">{site.name ?? site.domain}</h1>
            <div className="mt-1 text-sm text-dim">
              <a
                href={site.url}
                target="_blank"
                rel="noreferrer"
                className="hover:text-link"
              >
                {site.domain}
              </a>
              {site.industry ? ` · ${site.industry}` : ""}
            </div>
            <div className="mt-2">
              <StatusBadge status={site.status} />
            </div>
          </div>
          <RunAuditButton siteId={site.id} />
        </div>

        {/* The upsell engine: auto-fixed vs premium-required */}
        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <Panel className="border-good/40">
            <div className="text-xs uppercase tracking-wider text-dim">
              Fixed automatically
            </div>
            <div className="mt-1 text-3xl font-extrabold text-good">
              {appliedCount} thing{appliedCount === 1 ? "" : "s"}
            </div>
            <div className="mt-1 text-sm text-dim">
              Software applied these with no site access needed.
            </div>
          </Panel>
          <Panel className="border-poor/40">
            <div className="text-xs uppercase tracking-wider text-dim">
              Requires our premium team
            </div>
            <div className="mt-1 text-3xl font-extrabold text-poor">
              {premiumFindings.length} thing{premiumFindings.length === 1 ? "" : "s"}
              {premiumFindings.length > 0 && (
                <span className="ml-2 text-sm font-medium text-dim">
                  · +{premiumImpact} pts
                </span>
              )}
            </div>
            <Link
              href="/pricing#premium"
              className="mt-3 inline-block rounded-md bg-accent px-3 py-1.5 text-sm font-semibold text-white hover:opacity-90"
            >
              Upgrade to AI Authority Build →
            </Link>
          </Panel>
        </div>

        {/* Auto-fixes */}
        <Panel className="mb-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-dim">
            Auto-fixes
          </h2>
          {fixList.length === 0 ? (
            <p className="text-sm text-dim">
              No fixes yet. Run an audit to surface auto-fixable issues.
            </p>
          ) : (
            <div className="space-y-2">
              {fixList.map((f) => (
                <div
                  key={f.id}
                  className="flex items-start justify-between gap-3 rounded-lg border border-line bg-navy px-4 py-3"
                >
                  <div>
                    <div className="font-semibold">{f.title}</div>
                    <div className="text-sm text-dim">{f.description}</div>
                    <div className="mt-1 text-[0.72rem] text-dim">
                      {f.fix_type} · serves via {f.mechanism} · +{f.score_impact} pts
                    </div>
                    {(f.status === "applied" || f.status === "verified") &&
                      (f.fix_type === "llmstxt" ||
                        f.fix_type === "robots" ||
                        f.fix_type === "schema_injection") && (
                        <a
                          href={`${appBase}/s/${site.id}/${
                            f.fix_type === "schema_injection"
                              ? "schema.json"
                              : f.fix_type === "robots"
                                ? "robots.txt"
                                : "llms.txt"
                          }`}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-block text-xs text-link"
                        >
                          view live output ↗
                        </a>
                      )}
                  </div>
                  <FixButton fixId={f.id} status={f.status} />
                </div>
              ))}
            </div>
          )}
        </Panel>

        {/* Findings */}
        <Panel className="mb-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-dim">
            Audit findings
          </h2>
          {(findings ?? []).length === 0 ? (
            <p className="text-sm text-dim">No findings yet.</p>
          ) : (
            <div className="space-y-2">
              {(findings ?? []).map((f) => (
                <div
                  key={f.id}
                  className="rounded-lg border border-line bg-navy px-4 py-3"
                >
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={f.severity} />
                    <span className="font-semibold">{f.title}</span>
                    <span className="ml-auto text-[0.7rem] text-dim">
                      {f.automatable ? "auto-fixable" : "premium"}
                    </span>
                  </div>
                  {f.description && (
                    <p className="mt-1 text-sm text-dim">{f.description}</p>
                  )}
                  {f.recommendation && (
                    <p className="mt-1 text-sm text-ink">→ {f.recommendation}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>

        {/* Deliverables */}
        {(deliverables ?? []).length > 0 && (
          <Panel>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-dim">
              Deliverables
            </h2>
            <div className="space-y-2">
              {(deliverables ?? []).map((d) => (
                <div
                  key={d.id}
                  className="rounded-lg border border-line bg-navy px-4 py-3"
                >
                  <div className="font-semibold">{d.title}</div>
                  {d.description && (
                    <div className="text-sm text-dim">{d.description}</div>
                  )}
                  {d.purpose && (
                    <div className="mt-1 text-sm text-ink">Purpose: {d.purpose}</div>
                  )}
                </div>
              ))}
            </div>
          </Panel>
        )}
      </main>
    </>
  );
}
