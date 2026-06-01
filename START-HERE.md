# START HERE — GEO project map (2026-05-31)

Three things live here now: the **engine** (analysis), the **cockpit** (your internal library),
and the **platform** (the product you sell).

## Run everything
```bash
./start-all.sh      # Supabase + engine + cockpit + platform
./stop-all.sh       # stop it all
```
Then open:
- **http://localhost:3000** — the **GEO Platform** (the product). Login: `demo@geo.local` / `geodemo123`
- **http://localhost:5050** — the **Flask cockpit** (your internal report library)
- http://127.0.0.1:54523 — Supabase Studio (DB browser)

## What's what
| Folder | What it is | Status |
|--------|-----------|--------|
| `platform/` | **The product** — Next.js + Supabase SaaS. Audit → auto-fix → premium upsell. Multi-tenant, auth, billing, edge routes. | Built + tested locally |
| `engine/` | FastAPI wrapper around the GEO scripts (`/run-audit` etc.) — the analysis brain. | 68 tests passing |
| `n8n/` | Importable audit/fix/verify workflows (the fix-execution layer). | Ready to import |
| `scripts/`, `skills/` | The original Python GEO engine + 14 geo skills (now emit deliverable manifests). | 29 manifest tests |
| `scripts/webapp/` | The Flask cockpit (your internal library, on 5050). | Live |
| `clients/` | One folder per site: audits, reports, proposals, deliverables, inputs + `manifest.json`. | Organized |

## The visual deliverables (in `clients/stg/deliverables/`)
- `GEO-Product-Blueprint-2026-05-31.html` — the strategy + architecture + pricing + roadmap
- `platform-dashboard.png`, `platform-site-detail.png`, `platform-pricing.png` — the built product

## What's proven working
- Auth + Row-Level-Security tenant isolation (anon sees 0 sites, demo user sees their 3)
- `/run-audit` scores a real URL; findings + auto-fixes written to the DB
- Apply a fix → it's served **live** to AI crawlers at `/s/<siteId>/llms.txt`, `/robots.txt`, `/schema.json`
- `npm run build` ✓ · all test suites ✓

## What needs YOU (decisions / credentials) before production
1. A **dedicated Supabase cloud project** (recommended over Mission Control's, for client-data isolation) → `supabase db push`.
2. **Stripe** test/live keys + the webhook (`/api/stripe/webhook`). Pricing ladder is wired: $497 / $597mo / $2,997mo.
3. **Deploy**: `platform/` → Vercel; `engine/` → a container host; import `n8n/*.json` into n8n cloud.
4. Confirm STG's real domain (currently a guess on the STG site record).

Full detail: `platform/README.md` and the blueprint HTML.
