import { createAdminClient } from "@/lib/supabase/admin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Serves the applied JSON-LD schema for a site as application/ld+json. */
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
    .eq("fix_type", "schema_injection")
    .in("status", ["applied", "verified"])
    .order("applied_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (!data?.payload) {
    return new Response(JSON.stringify({ error: "No schema configured" }), {
      status: 404,
      headers: { "content-type": "application/json" },
    });
  }
  return new Response(JSON.stringify(data.payload, null, 2), {
    headers: {
      "content-type": "application/ld+json; charset=utf-8",
      "cache-control": "s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
