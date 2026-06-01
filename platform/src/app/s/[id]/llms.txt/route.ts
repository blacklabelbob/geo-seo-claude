import { createAdminClient } from "@/lib/supabase/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Serves the applied llms.txt for a site to AI crawlers. */
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
    .eq("fix_type", "llmstxt")
    .in("status", ["applied", "verified"])
    .order("applied_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const content = (data?.payload as { content?: string } | null)?.content;
  if (!content) {
    return new Response("# No llms.txt configured for this site\n", {
      status: 404,
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
