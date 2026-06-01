# Changelog — platform

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Auto-initialized by changelog-guard hook.

## [0.1.0] — 2026-05-31

### Added
- **GEO Platform** — multi-tenant Next.js 16 + React 19 + Tailwind 4 SaaS on Supabase.
- Supabase schema + RLS (orgs/org_members/sites/audits/audit_findings/deliverables/fixes/fix_jobs/subscriptions),
  tenant isolation via `public.user_org_ids()`. Seed migrates the 3 existing clients.
- Auth (email/password) with signup auto-provisioning an org + owner membership + trial; Next 16 `proxy.ts` session refresh.
- Dashboard (KPIs + sites + scores), site detail (the "auto-fixed vs premium-required" upsell engine, findings, fixes, deliverables), add-website, pricing.
- API routes: `/api/audit/trigger` (calls the FastAPI engine, writes findings + fixes), `/api/fix/apply`, Stripe `/checkout` + `/webhook`.
- **Edge product mechanism**: `/s/[id]/llms.txt`, `/robots.txt`, `/schema.json` serve applied fixes to AI crawlers from the DB (service role) — works because AI crawlers don't run JS.
- Stripe billing (test mode, inline price_data — no pre-created products needed).
- Tests: vitest (scores + util, 6) + `scripts/smoke-rls.mjs` (RLS isolation). Build + typecheck green.
- `scripts/seed-demo-user.mjs` (demo@geo.local / geodemo123), `scripts/shots.mjs` (Playwright screenshots).
- Project changelog initialized on 2026-05-31.

### Verified
- `npm run build` ✓ · `npm test` 6/6 ✓ · RLS smoke ✓ (anon=0 sites, demo=3) · edge routes serve live ✓ · engine /run-audit ✓.

