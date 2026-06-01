"""
scoring.py — Pure, deterministic scoring functions for GEO audit sub-scores.

All functions are stateless and depend only on their inputs. They are
unit-testable with no network calls.

Score thresholds are documented inline. All five sub-scores are 0-100;
the overall score is the weighted average documented in compute_scores().
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Individual dimension scorers
# ---------------------------------------------------------------------------

def score_schema(structured_data: list) -> int:
    """
    Schema sub-score (0-100).

    Thresholds
    ----------
    - No JSON-LD at all                         →   0
    - JSON-LD present but no @type              →  30
    - Has @type (any recognized type)           →  55
    - Has Organization or LocalBusiness         →  70
    - Has Organization + name + url             →  85
    - Has Organization + name + url + sameAs    → 100
    """
    if not structured_data:
        return 0

    best = 0
    for item in structured_data:
        if not isinstance(item, dict):
            continue
        schema_type = item.get("@type", "")
        # Normalize: @type can be a list
        if isinstance(schema_type, list):
            schema_type = schema_type[0] if schema_type else ""
        schema_type = str(schema_type)

        if not schema_type:
            score = 30
        elif schema_type in ("Organization", "LocalBusiness", "Corporation"):
            has_name = bool(item.get("name"))
            has_url = bool(item.get("url"))
            has_same_as = bool(item.get("sameAs"))
            if has_name and has_url and has_same_as:
                score = 100
            elif has_name and has_url:
                score = 85
            else:
                score = 70
        else:
            score = 55
        best = max(best, score)

    return best


def score_content(
    word_count: int,
    avg_citability_score: float,
    has_h1: bool,
    has_meta_description: bool,
    has_faq_patterns: bool = False,
) -> int:
    """
    Content sub-score (0-100).

    Thresholds
    ----------
    Word count contribution (0-40 pts):
        < 300 words  →  0
        300-599      → 15
        600-999      → 25
        1000-1999    → 35
        >= 2000      → 40

    Citability contribution (0-30 pts):
        avg_citability_score is 0-100 (from citability_scorer.py)
        scaled linearly to 0-30.

    Structural signals (0-30 pts):
        has_h1               → 10
        has_meta_description → 10
        has_faq_patterns     → 10
    """
    # Word count (0-40)
    if word_count < 300:
        wc_pts = 0
    elif word_count < 600:
        wc_pts = 15
    elif word_count < 1000:
        wc_pts = 25
    elif word_count < 2000:
        wc_pts = 35
    else:
        wc_pts = 40

    # Citability (0-30)
    cite_pts = int(min(avg_citability_score, 100) * 0.30)

    # Structural (0-30)
    struct_pts = (
        (10 if has_h1 else 0)
        + (10 if has_meta_description else 0)
        + (10 if has_faq_patterns else 0)
    )

    return min(wc_pts + cite_pts + struct_pts, 100)


def score_technical(
    has_ssr_content: bool,
    has_canonical: bool,
    status_code: Optional[int],
    has_https: bool,
    security_header_count: int,
) -> int:
    """
    Technical sub-score (0-100).

    Thresholds
    ----------
    SSR content detected          → 30 pts
    Valid status code (200-299)   → 20 pts
    HTTPS                         → 20 pts
    Canonical tag present         → 15 pts
    Security headers (0-5):
        0 headers  →  0
        1-2        →  5
        3-4        → 10
        5-6        → 15
    """
    pts = 0
    pts += 30 if has_ssr_content else 0
    pts += 20 if (status_code and 200 <= status_code < 300) else 0
    pts += 20 if has_https else 0
    pts += 15 if has_canonical else 0

    if security_header_count >= 5:
        pts += 15
    elif security_header_count >= 3:
        pts += 10
    elif security_header_count >= 1:
        pts += 5

    return min(pts, 100)


def score_crawlers(
    ai_crawler_status: dict,
    has_sitemap: bool,
) -> int:
    """
    Crawler access sub-score (0-100).

    Thresholds
    ----------
    Key crawlers checked: GPTBot, ClaudeBot, PerplexityBot, Google-Extended.

    Per-crawler scoring:
        ALLOWED or ALLOWED_BY_DEFAULT  → 15 pts each  (max 60 total for 4)
        NOT_MENTIONED                  → 10 pts (implicit allow)
        PARTIALLY_BLOCKED              →  5 pts
        BLOCKED / BLOCKED_BY_WILDCARD  →  0 pts

    Sitemap present                    → 20 pts
    robots.txt exists at all           → 20 pts
    (if ai_crawler_status is non-empty, robots.txt exists)
    """
    key_crawlers = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended"]
    allow_statuses = {"ALLOWED", "ALLOWED_BY_DEFAULT", "NO_ROBOTS_TXT"}

    pts = 0
    for crawler in key_crawlers:
        status = ai_crawler_status.get(crawler, "NOT_MENTIONED")
        if status in allow_statuses:
            pts += 15
        elif status == "NOT_MENTIONED":
            pts += 10
        elif status == "PARTIALLY_BLOCKED":
            pts += 5
        # BLOCKED / BLOCKED_BY_WILDCARD → 0

    if ai_crawler_status:
        pts += 20  # robots.txt exists

    if has_sitemap:
        pts += 20

    return min(pts, 100)


def score_llmstxt(llmstxt_result: dict) -> int:
    """
    llms.txt sub-score (0-100).

    Thresholds
    ----------
    llms.txt absent              →   0
    llms.txt present             →  40
    Format valid (all 4 checks)  →  30 additional → 70
    llms-full.txt also present   →  20 additional → 90
    ≥ 10 links in file           →  10 additional → 100
    """
    if not llmstxt_result.get("llms_txt", {}).get("exists"):
        return 0

    pts = 40
    if llmstxt_result.get("llms_txt", {}).get("format_valid"):
        pts += 30
    if llmstxt_result.get("llms_full_txt", {}).get("exists"):
        pts += 20
    link_count = llmstxt_result.get("llms_txt", {}).get("link_count", 0)
    if link_count >= 10:
        pts += 10

    return min(pts, 100)


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def compute_scores(
    schema_score: int,
    content_score: int,
    technical_score: int,
    crawlers_score: int,
    llmstxt_score: int,
) -> dict:
    """
    Compute the 5 sub-scores plus weighted overall score.

    Weights
    -------
    schema    20%
    content   30%
    technical 20%
    crawlers  20%
    llmstxt   10%
    """
    overall = int(
        schema_score * 0.20
        + content_score * 0.30
        + technical_score * 0.20
        + crawlers_score * 0.20
        + llmstxt_score * 0.10
    )
    return {
        "overall": max(0, min(overall, 100)),
        "schema": max(0, min(schema_score, 100)),
        "content": max(0, min(content_score, 100)),
        "technical": max(0, min(technical_score, 100)),
        "crawlers": max(0, min(crawlers_score, 100)),
    }


# ---------------------------------------------------------------------------
# Helper: detect FAQ patterns in text
# ---------------------------------------------------------------------------

def detect_faq_patterns(text: str) -> bool:
    """Return True if text contains FAQ-like patterns (Q&A structure)."""
    patterns = [
        r"\b(?:FAQ|Frequently Asked|Common Questions)\b",
        r"\?(?:\n|\s{2,})",   # question followed by newline or large whitespace
        r"^Q[:\.]\s",          # "Q: " format
        r"^Q\d+[:.]\s",        # "Q1: " format
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            return True
    return False
