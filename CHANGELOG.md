# Changelog — geo-seo-claude

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Auto-initialized by changelog-guard hook.

## [Unreleased]

### Added — 2026-05-31 (productization: audit tool → monetized platform)
- **`platform/`** — GEO Platform: multi-tenant Next.js 16 + Supabase SaaS (auth, dashboard, audit→fix→upsell flow,
  edge routes serving llms.txt/robots/schema to AI crawlers, Stripe billing). Built + tested locally. See `platform/README.md`.
- **`engine/`** — FastAPI wrapper around the geo scripts (`/run-audit`, `/gen-schema`, `/gen-llmstxt`, `/gen-robots`) + Dockerfile. 68 tests.
- **`n8n/`** — importable audit / fix / verify workflow JSON.
- **`scripts/geo_manifest.py`** — deliverable-manifest standard: every geo skill now emits each deliverable's
  description + purpose into `clients/<co>/manifest.json`. 29 tests. Wired into the Flask cockpit + the indexer.
- 12 geo skills updated with a "Deliverable Manifest" output step; `manifest.json` populated for all 3 clients.
- `start-all.sh` / `stop-all.sh` — bring the whole local stack up/down (Supabase, engine, Flask cockpit, Next platform).
- `START-HERE.md` — orientation doc tying the pieces together.

### Added — 2026-05-30 (reorganization)
- `clients/` library structure (one folder per site), data moved into the project, CRM reframed as a Report Library (English).

### Added — 2026-05-29
- Project changelog initialized.
- `start.sh` / `stop.sh` — launcher/stopper for the Flask GEO-SEO cockpit on port 5050.

