-- ============================================================================
-- Seed data — migrates the existing 3 clients from the Flask tool's
-- clients/_crm-data/prospects.json into the relational model.
-- Idempotent: safe to re-run (fixed UUIDs + on conflict do nothing).
-- A demo org owns them so the dashboard is populated out of the box.
-- Site GEO score is derived from the latest completed audit (not stored on site).
-- ============================================================================

-- Demo org (the agency tenant)
insert into public.orgs (id, name, slug, plan) values
  ('11111111-1111-1111-1111-111111111111', 'Sales Transformation Group', 'stg', 'agency')
on conflict (id) do nothing;

-- Sites (the 3 existing records)
insert into public.sites (id, org_id, url, domain, name, industry, country, status)
values
  ('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111111',
   'https://electron-srl.com', 'electron-srl.com', 'Electron Srl',
   'Educational Equipment Manufacturing (B2B)', 'Italy', 'proposal'),
  ('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111111',
   'https://closeclinic.com', 'closeclinic.com', 'CloseClinic',
   'AI Sales OS for Contractors (brand launch)', 'USA', 'active'),
  ('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111111',
   'https://salestransformationgroup.com', 'salestransformationgroup.com',
   'Sales Transformation Group (STG)', 'Roofing contractor sales training', 'USA', 'active')
on conflict (id) do nothing;

-- Electron baseline audit (score 28 from the real GEO Quick Audit)
insert into public.audits (id, site_id, org_id, status, score_overall, score_schema, score_content, score_technical, score_crawlers, triggered_by, completed_at)
values
  ('33333333-3333-3333-3333-333333333301', '22222222-2222-2222-2222-222222222201',
   '11111111-1111-1111-1111-111111111111', 'complete', 28, 5, 35, 30, 0, 'user', now())
on conflict (id) do nothing;

insert into public.audit_findings (audit_id, org_id, category, severity, title, description, recommendation, automatable, fix_type)
values
  ('33333333-3333-3333-3333-333333333301','11111111-1111-1111-1111-111111111111','crawlers','critical',
   'Server blocks AI crawlers (403)','GPTBot/ClaudeBot/PerplexityBot receive a 403 and cannot read the site.',
   'Allow AI crawler user-agents at the host/CDN level, then re-audit.', false, 'manual'),
  ('33333333-3333-3333-3333-333333333301','11111111-1111-1111-1111-111111111111','schema','critical',
   'Zero schema markup','No Organization/Product/FAQ JSON-LD present.',
   'Inject Organization + Product + FAQ JSON-LD.', true, 'schema_injection'),
  ('33333333-3333-3333-3333-333333333301','11111111-1111-1111-1111-111111111111','llmstxt','high',
   'No llms.txt','Site has no llms.txt directive for AI systems.',
   'Generate and host an llms.txt.', true, 'llmstxt'),
  ('33333333-3333-3333-3333-333333333301','11111111-1111-1111-1111-111111111111','brand','high',
   'No entity presence','No Wikipedia / Wikidata / Knowledge Panel for the brand.',
   'Build entity presence (premium DFY).', false, 'manual')
on conflict do nothing;

-- Auto-fixable opportunities for Electron (available to apply)
insert into public.fixes (id, site_id, org_id, fix_type, title, description, status, mechanism, score_impact, payload)
values
  ('44444444-4444-4444-4444-444444444401','22222222-2222-2222-2222-222222222201','11111111-1111-1111-1111-111111111111','llmstxt',
   'Generate & host llms.txt','Publishes an llms.txt describing the site for AI systems.',
   'available','edge', 6,
   '{"content":"# Electron Srl\nEducational equipment manufacturer, 35+ years, 70+ countries.\n\n## Key pages\n- /products\n- /about\n"}'::jsonb),
  ('44444444-4444-4444-4444-444444444402','22222222-2222-2222-2222-222222222201','11111111-1111-1111-1111-111111111111','schema_injection',
   'Inject Organization + Product schema','Adds JSON-LD so AI engines can parse the company entity.',
   'available','edge', 10,
   '{"@context":"https://schema.org","@type":"Organization","name":"Electron Srl"}'::jsonb),
  ('44444444-4444-4444-4444-444444444403','22222222-2222-2222-2222-222222222201','11111111-1111-1111-1111-111111111111','robots',
   'Allow AI crawlers in robots.txt','Adds explicit allow rules for GPTBot, ClaudeBot, PerplexityBot.',
   'available','edge', 4,
   '{"content":"User-agent: GPTBot\nAllow: /\n\nUser-agent: ClaudeBot\nAllow: /\n\nUser-agent: PerplexityBot\nAllow: /\n"}'::jsonb)
on conflict (id) do nothing;

-- Subscription stub for the demo org
insert into public.subscriptions (org_id, plan, status)
values ('11111111-1111-1111-1111-111111111111', 'agency', 'active')
on conflict (org_id) do nothing;
