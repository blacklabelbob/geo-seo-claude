import { createAdminClient } from "@/lib/supabase/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Serves the applied robots.txt (AI-crawler allow rules) for a site. */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const admin = createAdminClient();
  const { data } = await admin
    .from("fixes")
    .select("payload, status")
    .eq("site_id", id)
    .eq("fix_type", "robots")
    .in("status", ["applied", "verified"])
    .order("applied_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const content = (data?.payload as { content?: string } | null)?.content;
  if (!content) {
    return new Response("User-agent: *\nAllow: /\n", {
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
  return new Response(content, {
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
