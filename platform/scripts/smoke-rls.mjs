// Verifies the auth + RLS path: the demo user sees exactly their org's sites,
// and an anonymous client sees none. Run: node scripts/smoke-rls.mjs
import { createClient } from "@supabase/supabase-js";

const URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const ANON = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

let failures = 0;
const check = (name, cond) => {
  console.log(`  ${cond ? "✓" : "✗"} ${name}`);
  if (!cond) failures++;
};

// 1) anonymous client — RLS should expose zero rows
const anon = createClient(URL, ANON);
const { data: anonSites } = await anon.from("sites").select("*");
check("anonymous sees 0 sites (RLS closed)", (anonSites?.length ?? 0) === 0);

// 2) signed-in demo user — should see exactly the 3 STG sites
const user = createClient(URL, ANON);
const { error: signErr } = await user.auth.signInWithPassword({
  email: "demo@geo.local",
  password: "geodemo123",
});
check("demo user signs in", !signErr);
const { data: userSites } = await user.from("sites").select("name").order("name");
check(`demo user sees 3 sites (got ${userSites?.length ?? 0})`, (userSites?.length ?? 0) === 3);

// 3) the user can read their fixes (org-scoped)
const { data: fixes } = await user.from("fixes").select("id, status");
check(`demo user sees fixes (got ${fixes?.length ?? 0})`, (fixes?.length ?? 0) >= 3);

console.log(failures === 0 ? "\nRLS smoke: PASS" : `\nRLS smoke: ${failures} FAILED`);
process.exit(failures === 0 ? 0 : 1);
