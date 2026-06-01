# GEO Platform Build — todo (boil the ocean)
**Started:** 2026-05-31 · **Status: COMPLETE & VERIFIED** · Standard met: working + tested.

## Foundation
- [x] Scaffold Next.js 16 + TS + Tailwind 4 in `platform/`
- [x] Supabase local: schema migration + RLS (9 tables) + tenant-isolation function
- [x] Seed migration from existing 3 clients (Electron, CloseClinic, STG)
- [x] Supabase clients (server/browser/admin) via @supabase/ssr
- [x] App shell + GEO dark theme (Tailwind 4) + shared UI components
- [x] TypeScript DB types (generated from live DB)

## Auth + tenancy
- [x] Login / signup pages + server actions (signup auto-provisions org)
- [x] Next 16 `proxy.ts` session refresh
- [x] RLS isolation verified (anon=0, demo user=3 sites)

## Core product
- [x] Dashboard: sites list, KPIs, scores
- [x] Site/audit detail: upsell engine (auto-fixed vs premium) + findings + fixes + deliverables
- [x] Edge routes: /s/[id]/llms.txt, /robots.txt, /schema.json (serve applied fixes to crawlers)
- [x] Fix engine: apply API + UI states
- [x] Audit trigger API → engine → writes findings/fixes
- [x] Stripe billing (test mode): checkout (inline price_data) + webhook + pricing page

## Independent workstreams (parallel agents)
- [x] geo-skill deliverable MANIFEST upgrade + 29 tests · wired into Flask cockpit + indexer
- [x] FastAPI engine wrapper (/run-audit, /gen-*) + 68 tests + Dockerfile
- [x] n8n workflows (audit, fix, verify) importable JSON

## Verify (boil-the-ocean gate)
- [x] `supabase start` + migrations + seed applied clean
- [x] `npm run build` passes (typecheck + 15 routes)
- [x] tests pass: platform vitest 6/6, engine 68, manifest 29, RLS smoke
- [x] app runs, smoke-tested end-to-end (auth, edge routes, engine, fix apply)
- [x] Playwright screenshots captured (dashboard, site detail, pricing)
- [x] README + .env.example + deploy notes + START-HERE.md
- [x] CHANGELOGs (root, platform, stg) + start-all/stop-all scripts + memory

## Left for Rob (needs his accounts/decisions)
- [ ] Dedicated Supabase cloud project + `supabase db push`
- [ ] Stripe live/test keys + webhook
- [ ] Deploy platform→Vercel, engine→container, import n8n workflows
- [ ] Confirm STG real domain
