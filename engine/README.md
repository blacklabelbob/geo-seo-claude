# GEO Audit Engine

FastAPI service wrapping the GEO analysis scripts into a clean HTTP API.

## Quick Start

```bash
# From repo root (required — scripts/ must be resolvable)
uvicorn engine.app:app --port 8000 --reload
```

Or with Docker (also built from repo root):

```bash
docker build -f engine/Dockerfile -t geo-engine .
docker run -p 8000:8000 -e GEO_ENGINE_API_KEY=secret geo-engine
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEO_ENGINE_API_KEY` | No | (unset) | If set, all non-/health requests require `x-api-key: <value>` header |

## Endpoints

### GET /health

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### POST /run-audit

Full GEO audit: fetch page, run all checks, compute 5 sub-scores, return findings + auto-fix opportunities.

```bash
curl -X POST http://localhost:8000/run-audit \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Response shape:
```json
{
  "status": "complete",
  "scores": {
    "overall": 72,
    "schema": 85,
    "content": 68,
    "technical": 80,
    "crawlers": 75
  },
  "findings": [
    {
      "category": "content",
      "severity": "medium",
      "title": "No FAQ section detected",
      "description": "...",
      "recommendation": "...",
      "automatable": true,
      "fix_type": "faq_block"
    }
  ],
  "fixes": [
    {
      "fix_type": "faq_block",
      "title": "Add FAQ block",
      "description": "...",
      "mechanism": "artifact",
      "score_impact": 8,
      "payload": {"url": "https://example.com", "action": "generate_faq"}
    }
  ]
}
```

On fetch failure: returns `{"status": "failed", ...}` — never 500.

### POST /gen-schema

Generate Organization JSON-LD for edge injection.

```bash
curl -X POST http://localhost:8000/gen-schema \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "org_name": "Example Inc"}'
```

Response:
```json
{
  "payload": {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Example Inc",
    "url": "https://example.com",
    "sameAs": ["https://www.linkedin.com/company/example-inc"]
  },
  "mechanism": "edge"
}
```

### POST /gen-llmstxt

Generate llms.txt content by crawling the site.

```bash
curl -X POST http://localhost:8000/gen-llmstxt \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Response:
```json
{
  "payload": {"content": "# Example\n> Description\n\n## Main Pages\n..."},
  "mechanism": "edge"
}
```

### POST /gen-robots

Generate an AI-crawler-friendly robots.txt.

```bash
curl -X POST http://localhost:8000/gen-robots \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Response:
```json
{
  "payload": {"content": "User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nAllow: /\n..."},
  "mechanism": "edge"
}
```

## Running Tests

```bash
# From repo root
python3 -m pytest engine/tests -q

# Using the engine venv
engine/.venv/bin/python -m pytest engine/tests -q
```

## Score Dimensions

| Dimension | Weight | Key Factors |
|---|---|---|
| schema | 20% | JSON-LD presence, Organization type, name/url/sameAs |
| content | 30% | Word count, citability, H1, meta description, FAQ |
| technical | 20% | SSR, HTTPS, canonical, status code, security headers |
| crawlers | 20% | GPTBot/ClaudeBot/PerplexityBot/Google-Extended allow status, sitemap |
| llmstxt | 10% | /llms.txt presence, format validity, link count, /llms-full.txt |

## Project Structure

```
engine/
  app.py           FastAPI application
  scoring.py       Pure scoring functions (unit-testable)
  requirements.txt Python dependencies
  Dockerfile       Container build (from repo root context)
  README.md        This file
  tests/
    test_engine.py Pytest suite (68 tests, all mocked)
    __init__.py
```
