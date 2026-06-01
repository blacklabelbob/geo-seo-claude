"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { slugify } from "@/lib/util";

export async function login(formData: FormData) {
  const supabase = await createClient();
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    redirect(`/login?error=${encodeURIComponent(error.message)}`);
  }
  redirect("/");
}

export async function signup(formData: FormData) {
  const supabase = await createClient();
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");
  const orgName = String(formData.get("org") ?? "My Agency");

  const { data, error } = await supabase.auth.signUp({ email, password });
  if (error || !data.user) {
    redirect(
      `/signup?error=${encodeURIComponent(error?.message ?? "Sign up failed")}`,
    );
  }

  // Provision the tenant (org + owner membership + trial subscription) with the
  // service role, since the new user has no rows yet for RLS to grant.
  const admin = createAdminClient();
  const slug = `${slugify(orgName) || "agency"}-${data.user.id.slice(0, 6)}`;
  const { data: org, error: orgErr } = await admin
    .from("orgs")
    .insert({ name: orgName, slug, plan: "starter" })
    .select()
    .single();
  if (orgErr || !org) {
    redirect(`/signup?error=${encodeURIComponent("Could not create org")}`);
  }
  await admin
    .from("org_members")
    .insert({ org_id: org.id, user_id: data.user.id, role: "owner" });
  await admin
    .from("subscriptions")
    .insert({ org_id: org.id, plan: "starter", status: "trialing" });

  // If email confirmation is on, there is no session yet — send to login.
  if (!data.session) {
    redirect(`/login?msg=${encodeURIComponent("Account created — sign in")}`);
  }
  redirect("/");
}
