"""
engine/app.py — GEO Audit Engine FastAPI service.

Run:
    uvicorn engine.app:app --port 8000 --reload

Environment variables:
    GEO_ENGINE_API_KEY   If set, all non-/health requests require
                         x-api-key header matching this value.
"""

import os
import sys
import re
import json
import logging
from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

# ---------------------------------------------------------------------------
# Path setup so engine can import scripts/ from repo root
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ---------------------------------------------------------------------------
# Import scripts (lazy-safe: errors surfaced at request time, not import)
# ---------------------------------------------------------------------------
try:
    from scripts.fetch_page import (
        fetch_page,
        fetch_robots_txt,
        fetch_llms_txt,
    )
    from scripts.llmstxt_generator import generate_llmstxt, validate_llmstxt
    _SCRIPTS_OK = True
except Exception as _scripts_err:
    _SCRIPTS_OK = False
    _SCRIPTS_ERR = str(_scripts_err)

from engine.scoring import (
    compute_scores,
    score_schema,
    score_content,
    score_technical,
    score_crawlers,
    score_llmstxt,
    detect_faq_patterns,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="GEO Audit Engine",
    version="1.0.0",
    description="AI-search readiness audit service",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API-key middleware (optional)
# ---------------------------------------------------------------------------
GEO_API_KEY = os.getenv("GEO_ENGINE_API_KEY", "")


async def _check_api_key(request: Request) -> None:
    if not GEO_API_KEY:
        return
    incoming = request.headers.get("x-api-key", "")
    if incoming != GEO_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing x-api-key")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class AuditRequest(BaseModel):
    url: str


class SchemaRequest(BaseModel):
    url: str
    org_name: Optional[str] = None


class LlmstxtRequest(BaseModel):
    url: str


class RobotsRequest(BaseModel):
    url: str


class Finding(BaseModel):
    category: str
    severity: str
    title: str
    description: str
    recommendation: str
    automatable: bool
    fix_type: str


class Fix(BaseModel):
    fix_type: str
    title: str
    description: str
    mechanism: str
    score_impact: int
    payload: Any


class AuditResult(BaseModel):
    status: str
    scores: dict
    findings: list
    fixes: list


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.post("/run-audit", response_model=AuditResult, tags=["audit"])
async def run_audit(body: AuditRequest, request: Request):
    await _check_api_key(request)

    url = body.url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    has_https = parsed.scheme == "https"

    # --- Fetch page ---
    try:
        if not _SCRIPTS_OK:
            raise RuntimeError(f"Scripts not importable: {_SCRIPTS_ERR}")
        page_data = fetch_page(url)
        robots_data = fetch_robots_txt(url)
        llms_check = fetch_llms_txt(url)
    except Exception as exc:
        logger.error("Fetch failed for %s: %s", url, exc)
        error_finding = {
            "category": "technical",
            "severity": "critical",
            "title": "Page fetch failed",
            "description": str(exc),
            "recommendation": "Verify the URL is accessible and returns HTTP 200.",
            "automatable": False,
            "fix_type": "manual",
        }
        return AuditResult(
            status="failed",
            scores={"overall": 0, "schema": 0, "content": 0, "technical": 0, "crawlers": 0},
            findings=[error_finding],
            fixes=[],
        )

    # Treat any non-2xx as a fetch failure (but return structured result)
    status_code = page_data.get("status_code")
    if status_code and not (200 <= status_code < 300):
        error_finding = {
            "category": "technical",
            "severity": "critical",
            "title": f"Page returned HTTP {status_code}",
            "description": f"The URL {url} returned status code {status_code}.",
            "recommendation": "Ensure the URL is publicly accessible and returns 200.",
            "automatable": False,
            "fix_type": "manual",
        }
        return AuditResult(
            status="failed",
            scores={"overall": 0, "schema": 0, "content": 0, "technical": 0, "crawlers": 0},
            findings=[error_finding],
            fixes=[],
        )

    # -----------------------------------------------------------------------
    # Compute sub-scores
    # -----------------------------------------------------------------------
    structured_data = page_data.get("structured_data", [])
    word_count = page_data.get("word_count", 0)
    text_content = page_data.get("text_content", "")
    h1_tags = page_data.get("h1_tags", [])
    meta_tags = page_data.get("meta_tags", {})
    has_canonical = bool(page_data.get("canonical"))
    has_ssr = page_data.get("has_ssr_content", True)
    security_headers = page_data.get("security_headers", {})
    security_count = sum(1 for v in security_headers.values() if v)

    ai_crawler_status = robots_data.get("ai_crawler_status", {})
    has_sitemap = bool(robots_data.get("sitemaps"))

    llmstxt_data = {
        "llms_txt": llms_check.get("llms_txt", {}),
        "llms_full_txt": llms_check.get("llms_full_txt", {}),
    }

    # Enrich llmstxt_data with validate result if llms.txt exists
    if llmstxt_data.get("llms_txt", {}).get("exists"):
        try:
            validated = validate_llmstxt(url)
            llmstxt_data["llms_txt"]["format_valid"] = validated.get("format_valid", False)
            llmstxt_data["llms_txt"]["link_count"] = validated.get("link_count", 0)
        except Exception:
            pass

    # Rough citability score: use average sentence length heuristic when
    # full citability analysis is skipped (keeps endpoint fast).
    avg_citability = _fast_citability_estimate(text_content)
    has_faq = detect_faq_patterns(text_content)

    s_schema = score_schema(structured_data)
    s_content = score_content(
        word_count,
        avg_citability,
        bool(h1_tags),
        bool(meta_tags.get("description")),
        has_faq,
    )
    s_technical = score_technical(
        has_ssr,
        has_canonical,
        status_code,
        has_https,
        security_count,
    )
    s_crawlers = score_crawlers(ai_crawler_status, has_sitemap)
    s_llmstxt = score_llmstxt(llmstxt_data)

    scores = compute_scores(s_schema, s_content, s_technical, s_crawlers, s_llmstxt)

    # -----------------------------------------------------------------------
    # Build findings
    # -----------------------------------------------------------------------
    findings = []
    fixes = []

    # Schema findings
    if s_schema == 0:
        findings.append({
            "category": "schema",
            "severity": "critical",
            "title": "No structured data (JSON-LD) detected",
            "description": "The page has no JSON-LD schema markup. AI search engines rely heavily on structured data to understand entity identity.",
            "recommendation": "Add Organization or LocalBusiness JSON-LD schema to the <head> of your homepage.",
            "automatable": True,
            "fix_type": "schema_injection",
        })
        fixes.append({
            "fix_type": "schema_injection",
            "title": "Inject Organization JSON-LD",
            "description": "Add Organization schema markup via edge middleware or CMS injection.",
            "mechanism": "edge",
            "score_impact": 20,
            "payload": _build_org_schema(url, None),
        })
    elif s_schema < 70:
        findings.append({
            "category": "schema",
            "severity": "high",
            "title": "Incomplete Organization schema",
            "description": "JSON-LD schema is present but missing key Organization properties (name, url, sameAs).",
            "recommendation": "Add name, url, and sameAs links to Wikipedia and social profiles.",
            "automatable": True,
            "fix_type": "schema_injection",
        })

    # llms.txt findings
    if s_llmstxt == 0:
        findings.append({
            "category": "llmstxt",
            "severity": "high",
            "title": "No llms.txt file found",
            "description": "llms.txt is the emerging standard for guiding AI crawlers. Its absence means AI models must guess your site structure.",
            "recommendation": "Create /llms.txt at your domain root with site navigation and key page descriptions.",
            "automatable": True,
            "fix_type": "llmstxt",
        })
        fixes.append({
            "fix_type": "llmstxt",
            "title": "Generate and deploy llms.txt",
            "description": "Auto-generate an llms.txt based on site navigation.",
            "mechanism": "artifact",
            "score_impact": 10,
            "payload": {"url": url, "action": "generate"},
        })

    # Content findings
    if word_count < 300:
        findings.append({
            "category": "content",
            "severity": "critical",
            "title": f"Insufficient content ({word_count} words)",
            "description": "Pages with fewer than 300 words are rarely cited by AI models. Optimal citability requires 600+ words with fact-dense passages.",
            "recommendation": "Expand page content to at least 600 words, structured with H2 headings and data-rich paragraphs.",
            "automatable": False,
            "fix_type": "rewrite",
        })
    elif word_count < 600:
        findings.append({
            "category": "content",
            "severity": "medium",
            "title": f"Thin content ({word_count} words)",
            "description": "Content is below optimal length for AI citation. AI prefers 134-167 word self-contained passages.",
            "recommendation": "Add FAQ sections, statistics, and structured answer blocks.",
            "automatable": True,
            "fix_type": "faq_block",
        })

    if not h1_tags:
        findings.append({
            "category": "content",
            "severity": "high",
            "title": "No H1 heading found",
            "description": "Missing H1 reduces AI model confidence in the page topic.",
            "recommendation": "Add a clear, descriptive H1 that matches your primary entity name and service.",
            "automatable": False,
            "fix_type": "rewrite",
        })

    if not meta_tags.get("description"):
        findings.append({
            "category": "content",
            "severity": "medium",
            "title": "Missing meta description",
            "description": "Meta descriptions provide AI crawlers with a concise summary used in knowledge extraction.",
            "recommendation": "Add a 150-160 character meta description summarizing the page topic.",
            "automatable": True,
            "fix_type": "meta",
        })
        fixes.append({
            "fix_type": "meta",
            "title": "Inject meta description",
            "description": "Add or update the meta description tag.",
            "mechanism": "edge",
            "score_impact": 5,
            "payload": {"tag": "meta", "name": "description", "content": f"[Your description for {urlparse(url).netloc}]"},
        })

    if not has_faq:
        findings.append({
            "category": "content",
            "severity": "low",
            "title": "No FAQ section detected",
            "description": "FAQ sections with question-answer patterns are highly citable by AI models.",
            "recommendation": "Add an FAQ section addressing common questions about your service.",
            "automatable": True,
            "fix_type": "faq_block",
        })
        fixes.append({
            "fix_type": "faq_block",
            "title": "Add FAQ block",
            "description": "Generate and inject an FAQ section targeting common questions.",
            "mechanism": "artifact",
            "score_impact": 8,
            "payload": {"url": url, "action": "generate_faq"},
        })

    # Technical findings
    if not has_ssr:
        findings.append({
            "category": "technical",
            "severity": "critical",
            "title": "Client-side rendering only (no SSR)",
            "description": "AI crawlers do not execute JavaScript. Content only in JS bundles is invisible to AI search.",
            "recommendation": "Implement server-side rendering (SSR) or static generation (SSG) for key content.",
            "automatable": False,
            "fix_type": "manual",
        })

    if not has_https:
        findings.append({
            "category": "technical",
            "severity": "critical",
            "title": "Site not served over HTTPS",
            "description": "HTTPS is required for AI crawlers and browser trust. HTTP sites are penalized in AI search.",
            "recommendation": "Enable HTTPS with a valid SSL certificate.",
            "automatable": False,
            "fix_type": "manual",
        })

    if not has_canonical:
        findings.append({
            "category": "technical",
            "severity": "medium",
            "title": "Missing canonical URL tag",
            "description": "Without a canonical tag, AI crawlers cannot identify the authoritative version of duplicate or similar pages.",
            "recommendation": "Add <link rel='canonical' href='...'> to all pages.",
            "automatable": True,
            "fix_type": "meta",
        })
        fixes.append({
            "fix_type": "meta",
            "title": "Inject canonical tag",
            "description": "Add canonical link element via edge middleware.",
            "mechanism": "edge",
            "score_impact": 5,
            "payload": {"tag": "link", "rel": "canonical", "href": url},
        })

    if security_count < 3:
        findings.append({
            "category": "technical",
            "severity": "low",
            "title": f"Weak security headers ({security_count}/6 present)",
            "description": "Missing security headers reduce trust signals for AI indexers.",
            "recommendation": "Add HSTS, CSP, X-Frame-Options, X-Content-Type-Options headers.",
            "automatable": True,
            "fix_type": "robots",
        })

    # Crawler findings
    blocked_crawlers = [
        c for c, s in ai_crawler_status.items()
        if s in ("BLOCKED", "BLOCKED_BY_WILDCARD", "PARTIALLY_BLOCKED")
    ]
    if blocked_crawlers:
        findings.append({
            "category": "crawlers",
            "severity": "critical",
            "title": f"AI crawlers blocked: {', '.join(blocked_crawlers)}",
            "description": f"robots.txt is blocking or partially blocking AI crawlers: {blocked_crawlers}. This prevents AI models from indexing your content.",
            "recommendation": "Update robots.txt to explicitly allow GPTBot, ClaudeBot, PerplexityBot, and Google-Extended.",
            "automatable": True,
            "fix_type": "robots",
        })
        fixes.append({
            "fix_type": "robots",
            "title": "Update robots.txt to allow AI crawlers",
            "description": "Replace blocking rules with explicit allow directives for AI crawlers.",
            "mechanism": "artifact",
            "score_impact": 20,
            "payload": _build_robots_payload(url, ai_crawler_status),
        })

    if not has_sitemap:
        findings.append({
            "category": "crawlers",
            "severity": "medium",
            "title": "No sitemap referenced in robots.txt",
            "description": "Without a sitemap, AI crawlers may miss pages beyond the homepage.",
            "recommendation": "Add a Sitemap: directive to robots.txt pointing to /sitemap.xml.",
            "automatable": True,
            "fix_type": "robots",
        })

    # Page errors from fetch
    for err in page_data.get("errors", []):
        findings.append({
            "category": "technical",
            "severity": "medium",
            "title": "Page parsing warning",
            "description": err,
            "recommendation": "Investigate and resolve the parsing issue.",
            "automatable": False,
            "fix_type": "manual",
        })

    return AuditResult(
        status="complete",
        scores=scores,
        findings=findings,
        fixes=fixes,
    )


@app.post("/gen-schema", tags=["generators"])
async def gen_schema(body: SchemaRequest, request: Request):
    await _check_api_key(request)
    parsed = urlparse(body.url)
    payload = _build_org_schema(body.url, body.org_name)
    return {"payload": payload, "mechanism": "edge"}


@app.post("/gen-llmstxt", tags=["generators"])
async def gen_llmstxt(body: LlmstxtRequest, request: Request):
    await _check_api_key(request)
    url = body.url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        if not _SCRIPTS_OK:
            raise RuntimeError(f"Scripts not importable: {_SCRIPTS_ERR}")
        result = generate_llmstxt(url)
        content = result.get("generated_llmstxt", "")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"llms.txt generation failed: {exc}")
    return {"payload": {"content": content}, "mechanism": "edge"}


@app.post("/gen-robots", tags=["generators"])
async def gen_robots(body: RobotsRequest, request: Request):
    await _check_api_key(request)
    url = body.url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    content = f"""\
# robots.txt for {base}
# Generated by GEO Audit Engine

User-agent: *
Allow: /

# AI crawlers — explicitly permitted
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Googlebot
Allow: /

Sitemap: {base}/sitemap.xml
"""
    return {"payload": {"content": content}, "mechanism": "edge"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_org_schema(url: str, org_name: Optional[str]) -> dict:
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    name = org_name or parsed.netloc.replace("www.", "").split(".")[0].title()
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": name,
        "url": base_url,
        "sameAs": [
            f"https://www.linkedin.com/company/{name.lower().replace(' ', '-')}",
        ],
    }


def _build_robots_payload(url: str, ai_crawler_status: dict) -> dict:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    crawlers = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended",
                "OAI-SearchBot", "ChatGPT-User", "anthropic-ai"]
    directives = [f"User-agent: {c}\nAllow: /" for c in crawlers]
    content = (
        "User-agent: *\nAllow: /\n\n"
        + "\n\n".join(directives)
        + f"\n\nSitemap: {base}/sitemap.xml\n"
    )
    return {"robots_txt_content": content, "blocked_crawlers": list(ai_crawler_status.keys())}


def _fast_citability_estimate(text: str) -> float:
    """
    Quick proxy for average citability without running the full scorer.
    Returns 0-100.
    """
    if not text:
        return 0
    words = text.split()
    if not words:
        return 0

    score = 0
    # Percentages / stats
    if re.search(r"\d+(?:\.\d+)?%", text):
        score += 20
    # Named sources
    if re.search(r"(?:according to|research shows|study|data shows)", text, re.I):
        score += 15
    # Dollar figures
    if re.search(r"\$[\d,]+", text):
        score += 10
    # Definition patterns
    if re.search(r"\b\w+\s+is\s+(?:a|an|the)\s", text, re.I):
        score += 15
    # Length bonus
    if len(words) >= 600:
        score += 20
    elif len(words) >= 300:
        score += 10
    # FAQ bonus
    if re.search(r"\?", text):
        score += 10
    # Proper nouns
    proper = len(re.findall(r"\b[A-Z][a-z]{2,}", text))
    score += min(proper, 10)

    return min(score, 100)


# ---------------------------------------------------------------------------
# Entry point guard
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("engine.app:app", host="0.0.0.0", port=8000, reload=True)
