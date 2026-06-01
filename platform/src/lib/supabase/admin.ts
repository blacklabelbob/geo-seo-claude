import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import type { Database } from "@/lib/database.types";

/**
 * Service-role Supabase client. SERVER-ONLY — bypasses RLS.
 * Used by edge routes (serving llms.txt/schema for crawlers) and by
 * trusted API routes (audit/fix orchestration, Stripe webhooks).
 * NEVER import this into a Client Component.
 */
export function createAdminClient() {
  return createSupabaseClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false, autoRefreshToken: false } },
  );
}
