# GEO Platform

The monetized, multi-tenant SaaS layer on top of the GEO audit toolkit.
Audit a website → auto-remediate what software can → upsell the premium human work.
Built per `clients/stg/deliverables/GEO-Product-Blueprint-2026-05-31.html`.

- **Frontend + API:** Next.js 16 (App Router, React 19, Tailwind 4)
- **Backend:** Supabase (Postgres + Auth + RLS + Storage + Vault)
- **Analysis engine:** FastAPI wrapper (`/engine`) around the existing Python `geo` skills
- **Fix execution:** n8n workflows (`/n8n`) + edge-served routes for crawlers
- **Billing:** Stripe (test mode wired)

## Architecture

```
Browser ── Next.js (Vercel) ──┬─ Server Components / API routes ── Supabase (RLS-scoped)
                              ├─ /s/[id]/llms.txt · robots.txt · schema.json  (service role → AI crawlers)
                              └─ /api/audit/trigger ── FastAPI engine (/run-audit) ── geo skills
n8n workflows ── apply/verify fixes ── client sites + Supabase (service role)
```

Tenancy boundary = **orgs**, enforced by Postgres Row-Level Security (`public.user_org_ids()`).
The service role (edge routes, n8n, Stripe webhook) bypasses RLS by design.

## Local development

Prereqs: Node 20+, Docker, Supabase CLI, Python 3.13.

```bash
# 1. Backend — Postgres + Auth + Storage (ports 545xx to avoid Mission Control)
supabase start                       # applies migrations + seed automatically
node scripts/seed-demo-user.mjs      # creates demo@geo.local / geodemo123 (sees seeded sites)

# 2. Analysis engine (separate terminal, from repo root)
engine/.venv/bin/uvicorn engine.app:app --port 8000

# 3. Web app
npm install
npm run dev                          # http://localhost:3000
```

Demo login: **demo@geo.local / geodemo123** (sees the 3 migrated sites: Electron, CloseClinic, STG).

## Tests

```bash
npm test                 # vitest — scores + util (6 tests)
npm run build            # full typecheck + production build
node scripts/smoke-rls.mjs   # verifies RLS isolation + the auth data path
```

The engine has its own suite: `cd .. && engine/.venv/bin/python -m pytest engine/tests -q` (68 tests).
The manifest system: `python3 -m pytest tests/test_geo_manifest.py -q` (29 tests).

## Environment

See `.env.example`. For local dev `.env.local` is pre-filled with the local Supabase keys.
For production set: Supabase URL + anon + service-role keys, `GEO_ENGINE_URL`, `N8N_WEBHOOK_BASE`,
and the three `STRIPE_*` keys. Never expose `SUPABASE_SERVICE_ROLE_KEY` to the client.

## The product mechanism (why edge routes)

AI crawlers (GPTBot, ClaudeBot, PerplexityBot) **do not execute JavaScript** — client-side schema
injection is invisible to them. So applied fixes are served as real files from
`/s/[siteId]/llms.txt`, `/robots.txt`, and `/schema.json`, read from the `fixes` table. The client
points their domain at these (CNAME/redirect) and every AI crawler sees server-rendered output.

## Deploy

- **Web:** Vercel (this directory). Set env vars in the Vercel project.
- **DB:** a **dedicated** Supabase project (client data isolation) — `supabase db push` the migrations.
- **Engine:** container from `engine/Dockerfile` (Fly/Railway/Cloud Run).
- **Workflows:** import `n8n/*.json` into n8n cloud, set the env vars from `n8n/README.md`.
- **Stripe:** create the webhook → `/api/stripe/webhook`, set `STRIPE_WEBHOOK_SECRET`.

## Migration status (from the Flask cockpit)

The 3 existing clients are seeded into Postgres. The Flask app (`../scripts/webapp`) remains the
internal cockpit until this app reaches parity (Phase 2 of the blueprint roadmap).
