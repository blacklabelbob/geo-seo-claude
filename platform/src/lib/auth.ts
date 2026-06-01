import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import type { Org } from "@/lib/scores";

/** Require a signed-in user; redirect to /login otherwise. */
export async function requireUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return { supabase, user };
}

/** The user's primary org (RLS scopes this to orgs they belong to). */
export async function getPrimaryOrg(
  supabase: Awaited<ReturnType<typeof createClient>>,
): Promise<Org | null> {
  const { data } = await supabase
    .from("orgs")
    .select("*")
    .order("created_at", { ascending: true })
    .limit(1)
    .maybeSingle();
  return data;
}
