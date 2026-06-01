-- ============================================================================
-- GEO Platform — initial schema
-- Multi-tenant AI-visibility (GEO/AEO) SaaS. Tenancy boundary = orgs, enforced
-- by Row-Level Security. The service role (edge routes, n8n) bypasses RLS.
-- ============================================================================

-- gen_random_uuid() is built in on PG13+. Ensure pgcrypto for safety.
create extension if not exists pgcrypto;

-- ── updated_at trigger helper ───────────────────────────────────────────────
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ── TENANCY ─────────────────────────────────────────────────────────────────
create table public.orgs (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  slug        text unique not null,
  plan        text not null default 'starter' check (plan in ('starter','pro','agency')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table public.org_members (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references public.orgs(id) on delete cascade,
  user_id     uuid not null references auth.users(id) on delete cascade,
  role        text not null default 'viewer' check (role in ('owner','admin','viewer')),
  created_at  timestamptz not null default now(),
  unique (org_id, user_id)
);
create index org_members_user_idx on public.org_members(user_id);

-- SECURITY DEFINER helper: the org ids the current user belongs to.
-- Bypasses RLS to prevent recursive policy evaluation on org_members.
create or replace function public.user_org_ids()
returns setof uuid
language sql stable security definer set search_path = public
as $$
  select org_id from public.org_members where user_id = auth.uid()
$$;

-- ── SITES ───────────────────────────────────────────────────────────────────
create table public.sites (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references public.orgs(id) on delete cascade,
  url         text not null,
  domain      text not null,
  name        text,
  industry    text,
  country     text,
  cms_type    text default 'unknown' check (cms_type in ('wordpress','webflow','shopify','custom','unknown')),
  status      text not null default 'new'
              check (status in ('new','audited','proposal','active','won','archived','lost')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index sites_org_idx on public.sites(org_id);
create trigger sites_updated before update on public.sites
  for each row execute function public.set_updated_at();

-- ── AUDITS ──────────────────────────────────────────────────────────────────
create table public.audits (
  id              uuid primary key default gen_random_uuid(),
  site_id         uuid not null references public.sites(id) on delete cascade,
  org_id          uuid not null references public.orgs(id) on delete cascade,
  status          text not null default 'queued'
                  check (status in ('queued','running','complete','failed')),
  score_overall   int check (score_overall between 0 and 100),
  score_schema    int check (score_schema between 0 and 100),
  score_content   int check (score_content between 0 and 100),
  score_technical int check (score_technical between 0 and 100),
  score_crawlers  int check (score_crawlers between 0 and 100),
  triggered_by    text not null default 'user' check (triggered_by in ('user','scheduled','prospect')),
  error_message   text,
  created_at      timestamptz not null default now(),
  completed_at    timestamptz
);
create index audits_site_idx on public.audits(site_id, created_at desc);
create index audits_org_idx on public.audits(org_id);

create table public.audit_findings (
  id              uuid primary key default gen_random_uuid(),
  audit_id        uuid not null references public.audits(id) on delete cascade,
  org_id          uuid not null references public.orgs(id) on delete cascade,
  category        text not null check (category in ('schema','content','technical','crawlers','llmstxt','brand')),
  severity        text not null check (severity in ('critical','high','medium','low')),
  title           text not null,
  description     text,
  recommendation  text,
  automatable     boolean not null default false,
  fix_type        text check (fix_type in ('schema_injection','llmstxt','robots','meta','faq_block','rewrite','manual')),
  raw_data        jsonb,
  created_at      timestamptz not null default now()
);
create index findings_audit_idx on public.audit_findings(audit_id, category, severity);

-- ── DELIVERABLES (files in Supabase Storage) ────────────────────────────────
create table public.deliverables (
  id            uuid primary key default gen_random_uuid(),
  audit_id      uuid references public.audits(id) on delete cascade,
  site_id       uuid not null references public.sites(id) on delete cascade,
  org_id        uuid not null references public.orgs(id) on delete cascade,
  category      text not null default 'deliverables'
                check (category in ('audits','reports','proposals','deliverables','inputs')),
  file_type     text,                          -- "PDF report", "Excel workbook"
  title         text not null,
  description   text,                          -- what it is
  purpose       text,                          -- what it's for / next step it enables
  storage_path  text not null,                 -- path within the 'deliverables' bucket
  size_bytes    bigint,
  created_at    timestamptz not null default now()
);
create index deliverables_site_idx on public.deliverables(site_id);

-- ── FIXES ───────────────────────────────────────────────────────────────────
create table public.fixes (
  id            uuid primary key default gen_random_uuid(),
  site_id       uuid not null references public.sites(id) on delete cascade,
  org_id        uuid not null references public.orgs(id) on delete cascade,
  finding_id    uuid references public.audit_findings(id) on delete set null,
  fix_type      text not null check (fix_type in ('schema_injection','llmstxt','robots','meta','faq_block','rewrite')),
  title         text not null,
  description   text,
  status        text not null default 'available'
                check (status in ('available','queued','applied','verified','failed','manual_required')),
  mechanism     text not null default 'edge'
                check (mechanism in ('edge','api_push','artifact','pr')),
  payload       jsonb,                         -- the fix content (schema JSON, llms.txt text, ...)
  score_impact  int default 0,                 -- estimated GEO points if applied
  applied_at    timestamptz,
  verified_at   timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index fixes_site_idx on public.fixes(site_id, status);
create trigger fixes_updated before update on public.fixes
  for each row execute function public.set_updated_at();

create table public.fix_jobs (
  id               uuid primary key default gen_random_uuid(),
  fix_id           uuid not null references public.fixes(id) on delete cascade,
  org_id           uuid not null references public.orgs(id) on delete cascade,
  status           text not null default 'queued' check (status in ('queued','running','success','failed')),
  n8n_execution_id text,
  error_message    text,
  started_at       timestamptz,
  completed_at     timestamptz,
  created_at       timestamptz not null default now()
);
create index fix_jobs_fix_idx on public.fix_jobs(fix_id, created_at desc);

-- ── SUBSCRIPTIONS (Stripe) ──────────────────────────────────────────────────
create table public.subscriptions (
  id                     uuid primary key default gen_random_uuid(),
  org_id                 uuid not null unique references public.orgs(id) on delete cascade,
  stripe_customer_id     text unique,
  stripe_subscription_id text unique,
  plan                   text not null default 'starter' check (plan in ('starter','pro','agency')),
  status                 text not null default 'inactive'
                         check (status in ('inactive','trialing','active','past_due','canceled')),
  current_period_end     timestamptz,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);
create trigger subscriptions_updated before update on public.subscriptions
  for each row execute function public.set_updated_at();

-- ============================================================================
-- ROW-LEVEL SECURITY
-- Every tenant table: a row is visible/writable only to members of its org.
-- service_role bypasses RLS automatically (used by edge routes + n8n).
-- ============================================================================
alter table public.orgs            enable row level security;
alter table public.org_members     enable row level security;
alter table public.sites           enable row level security;
alter table public.audits          enable row level security;
alter table public.audit_findings  enable row level security;
alter table public.deliverables    enable row level security;
alter table public.fixes           enable row level security;
alter table public.fix_jobs        enable row level security;
alter table public.subscriptions   enable row level security;

-- orgs: members can see their orgs
create policy orgs_select on public.orgs for select to authenticated
  using (id in (select public.user_org_ids()));
create policy orgs_update on public.orgs for update to authenticated
  using (id in (select public.user_org_ids()));

-- org_members: a user sees their own membership rows + co-members of their orgs
create policy members_select on public.org_members for select to authenticated
  using (user_id = auth.uid() or org_id in (select public.user_org_ids()));

-- Generic org-scoped policy for the rest (select/insert/update/delete)
do $$
declare t text;
begin
  foreach t in array array['sites','audits','audit_findings','deliverables','fixes','fix_jobs','subscriptions']
  loop
    execute format($f$
      create policy %1$s_all on public.%1$s for all to authenticated
      using (org_id in (select public.user_org_ids()))
      with check (org_id in (select public.user_org_ids()));
    $f$, t);
  end loop;
end $$;
