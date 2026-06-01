import Link from "next/link";
import { requireUser, getPrimaryOrg } from "@/lib/auth";
import { Kpi, NavBar, Panel, ScoreBar, StatusBadge } from "@/components/ui";
import { scoreTier, tierColor } from "@/lib/scores";

export default async function Dashboard() {
  const { supabase } = await requireUser();
  const org = await getPrimaryOrg(supabase);

  const [{ data: sites }, { data: audits }, { data: fixes }] = await Promise.all([
    supabase.from("sites").select("*").order("created_at", { ascending: true }),
    supabase
      .from("audits")
      .select("site_id, score_overall, completed_at, status")
      .eq("status", "complete")
      .order("completed_at", { ascending: false }),
    supabase.from("fixes").select("site_id, status"),
  ]);

  // latest complete score per site
  const latestScore = new Map<string, number | null>();
  for (const a of audits ?? []) {
    if (!latestScore.has(a.site_id)) latestScore.set(a.site_id, a.score_overall);
  }
  const availableFixes = (fixes ?? []).filter((f) => f.status === "available").length;
  const scored = (sites ?? [])
    .map((s) => latestScore.get(s.id))
    .filter((v): v is number => typeof v === "number");
  const avg = scored.length
    ? Math.round(scored.reduce((a, b) => a + b, 0) / scored.length)
    : null;
  const proposals = (sites ?? []).filter((s) => s.status === "proposal").length;

  return (
    <>
      <NavBar orgName={org?.name} />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Kpi value={sites?.length ?? 0} label="Websites Analyzed" />
          <Kpi
            value={avg === null ? "—" : `${avg}`}
            label="Avg GEO Score"
            color={tierColor[scoreTier(avg)]}
          />
          <Kpi value={availableFixes} label="Fixes Available" color="#58a6ff" />
          <Kpi value={proposals} label="Proposals Out" color="#fdcb6e" />
        </div>

        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-dim">
            Your websites
          </h2>
          <Link
            href="/site/new"
            className="rounded-md bg-blue px-3 py-1.5 text-sm font-semibold text-white hover:opacity-90"
          >
            + Add website
          </Link>
        </div>

        {sites && sites.length > 0 ? (
          <Panel className="overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-[0.7rem] uppercase tracking-wider text-dim">
                  <th className="px-4 py-3">Website</th>
                  <th className="px-4 py-3">Domain</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">GEO Score</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {sites.map((s) => (
                  <tr
                    key={s.id}
                    className="border-b border-line-soft transition-colors hover:bg-[#1c2128]"
                  >
                    <td className="px-4 py-3 font-semibold">
                      <Link href={`/site/${s.id}`} className="hover:text-link">
                        {s.name ?? s.domain}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-dim">{s.domain}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="px-4 py-3">
                      <ScoreBar score={latestScore.get(s.id) ?? null} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/site/${s.id}`} className="text-dim hover:text-link">
                        →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        ) : (
          <Panel className="py-12 text-center text-dim">
            No websites yet. Add one and run a GEO audit to see it here.
          </Panel>
        )}
      </main>
    </>
  );
}
