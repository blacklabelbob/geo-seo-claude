import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const runtime = "nodejs";

/**
 * Apply an auto-fix. For edge-served fix types (llmstxt/robots/schema) "applying"
 * flips status to 'applied' so the /s/[id]/* edge routes start serving the payload.
 * For api_push/pr mechanisms, this would hand off to n8n; here we record a job and
 * mark applied so the flow is demonstrable end-to-end.
 */
export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { fix_id } = await request.json().catch(() => ({}));
  if (!fix_id)
    return NextResponse.json({ error: "fix_id required" }, { status: 400 });

  const { data: fix } = await supabase
    .from("fixes")
    .select("*")
    .eq("id", fix_id)
    .maybeSingle();
  if (!fix)
    return NextResponse.json({ error: "Fix not found" }, { status: 404 });

  const now = new Date().toISOString();
  const { data: job } = await supabase
    .from("fix_jobs")
    .insert({
      fix_id: fix.id,
      org_id: fix.org_id,
      status: "success",
      started_at: now,
      completed_at: now,
    })
    .select()
    .single();

  await supabase
    .from("fixes")
    .update({ status: "applied", applied_at: now })
    .eq("id", fix.id);

  return NextResponse.json({ ok: true, fix_id: fix.id, job_id: job?.id ?? null });
}
