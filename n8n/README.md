# GEO n8n Workflows

Three importable n8n workflows for the GEO audit platform.

## Import Steps

1. Open your n8n instance (boostn8n.app.n8n.cloud)
2. Go to **Workflows** → **Import from file**
3. Upload each JSON file
4. Set environment variables (see below)
5. Activate each workflow

## Workflows

### audit-workflow.json — GEO Audit: Run & Persist

**Trigger:** POST webhook `/geo-audit`  
**Flow:** Webhook → Engine /run-audit → Shape record → Insert audit to Supabase → Insert findings → Respond

**Request body:**
```json
{
  "url": "https://example.com",
  "client_id": "optional-client-id"
}
```

**Response:**
```json
{
  "success": true,
  "audit_id": "uuid",
  "scores": {"overall": 72, "schema": 85, ...}
}
```

### fix-workflow.json — GEO Fix: Dispatch & Track

**Trigger:** POST webhook `/geo-fix`  
**Flow:** Webhook → Switch by mechanism (edge/api_push/artifact) → Dispatch → Update fix status in Supabase → Respond

**Request body:**
```json
{
  "fix_id": "supabase-fix-uuid",
  "fix_type": "schema_injection",
  "mechanism": "edge",
  "payload": {"@type": "Organization", "name": "..."},
  "client_id": "client-id"
}
```

**Mechanism routing:**
- `edge` → POST to `EDGE_DEPLOY_WEBHOOK_URL` (Vercel/Cloudflare deploy hook)
- `api_push` → POST to `CMS_API_URL/api/fix`
- `artifact` → Generates text artifact (llms.txt, robots.txt) for manual deploy

### verify-workflow.json — GEO Fix Verification: Re-crawl & Confirm

**Triggers:** Daily cron at 8am OR POST webhook `/geo-verify`  
**Flow:** Fetch applied fixes → Split → Re-audit each site → Check if fix present → Update verification status

Verification logic per fix type:
- `schema_injection` → schema score >= 70
- `llmstxt` → no critical/high llmstxt findings
- `robots` → crawlers score >= 60
- `meta` → content score >= 40

## Environment Variables

Set these in n8n **Settings → Variables** or as workflow credentials:

| Variable | Description | Example |
|---|---|---|
| `GEO_ENGINE_URL` | GEO Engine base URL | `https://geo-engine.your-domain.com` |
| `GEO_ENGINE_API_KEY` | Engine API key (if set) | `secret-key-here` |
| `SUPABASE_URL` | Supabase project URL | `https://xnbhfplcthrkjycvlwip.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | `eyJ...` |
| `EDGE_DEPLOY_WEBHOOK_URL` | Vercel/CF deploy hook for edge fixes | `https://api.vercel.com/v1/integrations/deploy/...` |
| `EDGE_DEPLOY_TOKEN` | Auth token for edge deploy webhook | `Bearer v1:...` |
| `CMS_API_URL` | Headless CMS base URL (api_push fixes) | `https://your-cms.com` |
| `CMS_API_TOKEN` | CMS API bearer token | `cms-token-here` |

## Supabase Table Requirements

The workflows assume these tables exist in your Supabase project:

**audits**
```sql
CREATE TABLE audits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id TEXT,
  url TEXT NOT NULL,
  status TEXT,
  scores JSONB,
  findings TEXT,
  fixes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**findings**
```sql
CREATE TABLE findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  audit_id UUID REFERENCES audits(id),
  category TEXT,
  severity TEXT,
  title TEXT,
  description TEXT,
  recommendation TEXT,
  automatable BOOLEAN,
  fix_type TEXT
);
```

**fixes**
```sql
CREATE TABLE fixes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  audit_id UUID REFERENCES audits(id),
  fix_type TEXT,
  mechanism TEXT,
  status TEXT DEFAULT 'pending',
  applied_at TIMESTAMPTZ,
  verified_at TIMESTAMPTZ,
  verify_reason TEXT,
  new_scores JSONB,
  payload JSONB
);
```
