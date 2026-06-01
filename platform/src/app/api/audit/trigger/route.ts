import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const runtime = "nodejs";

type EngineFinding = {
  category: string;
  severity: string;
  title: string;
  description?: string;
  recommendation?: string;
  automatable?: boolean;
  fix_type?: string;
};
type EngineFix = {
  fix_type: string;
  title: string;
  description?: string;
  mechanism?: string;
  score_impact?: number;
  payload?: unknown;
};
type EngineResult = {
  status?: string;
  scores?: Record<string, number>;
  findings?: EngineFinding[];
  fixes?: EngineFix[];
};

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { site_id } = await request.json().catch(() => ({}));
  if (!site_id)
    return NextResponse.json({ error: "site_id required" }, { status: 400 });

  const { data: site } = await supabase
    .from("sites")
    .select("*")
    .eq("id", site_id)
    .maybeSingle();
  if (!site)
    return NextResponse.json({ error: "Site not found" }, { status: 404 });

  // Create the audit row (running)
  const { data: audit, error: auditErr } = await supabase
    .from("audits")
    .insert({
      site_id: site.id,
      org_id: site.org_id,
      status: "running",
      triggered_by: "user",
    })
    .select()
    .single();
  if (auditErr || !audit)
    return NextResponse.json({ error: "Could not create audit" }, { status: 500 });

  // Call the GEO engine
  const engineUrl = process.env.GEO_ENGINE_URL ?? "http://127.0.0.1:8000";
  let result: EngineResult | null = null;
  let engineError: string | null = null;
  try {
    const res = await fetch(`${engineUrl}/run-audit`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(process.env.GEO_ENGINE_API_KEY
          ? { "x-api-key": process.env.GEO_ENGINE_API_KEY }
          : {}),
      },
      body: JSON.stringify({ url: site.url }),
      signal: AbortSignal.timeout(60_000),
    });
    if (!res.ok) throw new Error(`engine ${res.status}`);
    result = (await res.json()) as EngineResult;
  } catch (e) {
    engineError = e instanceof Error ? e.message : "engine unreachable";
  }

  if (!result || result.status === "failed") {
    await supabase
      .from("audits")
      .update({
        status: "failed",
        error_message: engineError ?? "audit failed",
        completed_at: new Date().toISOString(),
      })
      .eq("id", audit.id);
    return NextResponse.json(
      { ok: false, error: engineError ?? "Audit failed", audit_id: audit.id },
      { status: 200 },
    );
  }

  const s = result.scores ?? {};
  await supabase
    .from("audits")
    .update({
      status: "complete",
      score_overall: s.overall ?? null,
      score_schema: s.schema ?? null,
      score_content: s.content ?? null,
      score_technical: s.technical ?? null,
      score_crawlers: s.crawlers ?? null,
      completed_at: new Date().toISOString(),
    })
    .eq("id", audit.id);

  if (result.findings?.length) {
    await supabase.from("audit_findings").insert(
      result.findings.map((f) => ({
        audit_id: audit.id,
        org_id: site.org_id,
        category: f.category,
        severity: f.severity,
        title: f.title,
        description: f.description ?? null,
        recommendation: f.recommendation ?? null,
        automatable: f.automatable ?? false,
        fix_type: f.fix_type ?? null,
      })),
    );
  }

  if (result.fixes?.length) {
    await supabase.from("fixes").insert(
      result.fixes.map((f) => ({
        site_id: site.id,
        org_id: site.org_id,
        fix_type: f.fix_type,
        title: f.title,
        description: f.description ?? null,
        mechanism: f.mechanism ?? "edge",
        score_impact: f.score_impact ?? 0,
        payload: (f.payload ?? null) as never,
        status: "available",
      })),
    );
  }

  // refresh site status to 'audited' if it was 'new'
  if (site.status === "new") {
    await supabase.from("sites").update({ status: "audited" }).eq("id", site.id);
  }

  return NextResponse.json({ ok: true, audit_id: audit.id, scores: s });
}
