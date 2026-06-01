// Seeds a confirmed demo user linked to the STG demo org so the dashboard
// is populated on first login. Idempotent. Run: node scripts/seed-demo-user.mjs
import { createClient } from "@supabase/supabase-js";

const URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54521";
const SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;
const ORG_ID = "11111111-1111-1111-1111-111111111111";
const EMAIL = "demo@geo.local";
const PASSWORD = "geodemo123";

if (!SERVICE) {
  console.error("SUPABASE_SERVICE_ROLE_KEY not set");
  process.exit(1);
}

const admin = createClient(URL, SERVICE, {
  auth: { persistSession: false, autoRefreshToken: false },
});

async function main() {
  // find or create the user
  let userId;
  const { data: list } = await admin.auth.admin.listUsers({ perPage: 1000 });
  const existing = list?.users.find((u) => u.email === EMAIL);
  if (existing) {
    userId = existing.id;
    console.log("user exists:", userId);
  } else {
    const { data, error } = await admin.auth.admin.createUser({
      email: EMAIL,
      password: PASSWORD,
      email_confirm: true,
    });
    if (error) throw error;
    userId = data.user.id;
    console.log("user created:", userId);
  }

  // link to the STG org as owner (idempotent)
  const { error: memErr } = await admin
    .from("org_members")
    .upsert(
      { org_id: ORG_ID, user_id: userId, role: "owner" },
      { onConflict: "org_id,user_id" },
    );
  if (memErr) throw memErr;

  console.log(`\n✓ Demo login ready:\n  email: ${EMAIL}\n  password: ${PASSWORD}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
