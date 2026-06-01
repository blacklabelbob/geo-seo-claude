"""
test_engine.py — Pytest suite for GEO Audit Engine.

All network calls are monkeypatched. No real HTTP requests are made.
Run:
    python3 -m pytest engine/tests -q
from the repo root.
"""

import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Ensure repo root is on path
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


# ---------------------------------------------------------------------------
# Fixtures: canned script return values
# ---------------------------------------------------------------------------

GOOD_PAGE_DATA = {
    "url": "https://example.com",
    "status_code": 200,
    "redirect_chain": [],
    "headers": {"Content-Type": "text/html"},
    "meta_tags": {"description": "Example company providing great services since 2020."},
    "title": "Example Inc",
    "description": "Example company providing great services since 2020.",
    "canonical": "https://example.com/",
    "h1_tags": ["Welcome to Example Inc"],
    "heading_structure": [{"level": 1, "text": "Welcome to Example Inc"}],
    "word_count": 850,
    "text_content": (
        "Welcome to Example Inc. "
        "Example Inc is a leading provider of cloud solutions since 2020. "
        "According to Gartner, 73% of enterprises use cloud by 2025. "
        "Our revenue reached $5 million last year. "
        "FAQ: What is Example Inc? Example Inc is a SaaS company. "
    ) * 10,
    "internal_links": [],
    "external_links": [],
    "images": [],
    "structured_data": [
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Example Inc",
            "url": "https://example.com",
            "sameAs": ["https://linkedin.com/company/example"],
        }
    ],
    "has_ssr_content": True,
    "security_headers": {
        "Strict-Transport-Security": "max-age=31536000",
        "Content-Security-Policy": "default-src 'self'",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin",
        "Permissions-Policy": None,
    },
    "errors": [],
}

GOOD_ROBOTS_DATA = {
    "url": "https://example.com/robots.txt",
    "exists": True,
    "content": "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml",
    "ai_crawler_status": {
        "GPTBot": "ALLOWED",
        "ClaudeBot": "ALLOWED",
        "PerplexityBot": "ALLOWED",
        "Google-Extended": "ALLOWED",
    },
    "sitemaps": ["https://example.com/sitemap.xml"],
    "errors": [],
}

GOOD_LLMS_DATA = {
    "llms_txt": {"url": "https://example.com/llms.txt", "exists": True, "content": ""},
    "llms_full_txt": {"url": "https://example.com/llms-full.txt", "exists": True, "content": ""},
    "errors": [],
}

MINIMAL_PAGE_DATA = {
    "url": "https://thin.example.com",
    "status_code": 200,
    "redirect_chain": [],
    "headers": {},
    "meta_tags": {},
    "title": None,
    "description": None,
    "canonical": None,
    "h1_tags": [],
    "heading_structure": [],
    "word_count": 100,
    "text_content": "Short content " * 10,
    "internal_links": [],
    "external_links": [],
    "images": [],
    "structured_data": [],
    "has_ssr_content": False,
    "security_headers": {},
    "errors": [],
}

MINIMAL_ROBOTS_DATA = {
    "url": "https://thin.example.com/robots.txt",
    "exists": True,
    "content": "User-agent: *\nDisallow: /\n",
    "ai_crawler_status": {
        "GPTBot": "BLOCKED",
        "ClaudeBot": "BLOCKED",
        "PerplexityBot": "BLOCKED",
        "Google-Extended": "BLOCKED",
    },
    "sitemaps": [],
    "errors": [],
}

MINIMAL_LLMS_DATA = {
    "llms_txt": {"url": "https://thin.example.com/llms.txt", "exists": False, "content": ""},
    "llms_full_txt": {"url": "https://thin.example.com/llms-full.txt", "exists": False, "content": ""},
    "errors": [],
}

FAILED_LLMS_DATA = {
    "llms_txt": {"url": "https://example.com/llms.txt", "exists": False, "content": ""},
    "llms_full_txt": {"url": "https://example.com/llms-full.txt", "exists": False, "content": ""},
    "errors": [],
}

GENERATED_LLMSTXT = {
    "generated_llmstxt": "# Example Inc\n> Example description\n\n## Main Pages\n- [Home](https://example.com)\n",
    "generated_llmstxt_full": "",
    "pages_analyzed": 5,
    "sections": {"Main Pages": 1},
}


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from engine.app import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /run-audit — good site
# ---------------------------------------------------------------------------

class TestRunAuditGoodSite:
    def _mock_audit(self, monkeypatch):
        monkeypatch.setattr("engine.app.fetch_page", lambda url, **kw: GOOD_PAGE_DATA)
        monkeypatch.setattr("engine.app.fetch_robots_txt", lambda url, **kw: GOOD_ROBOTS_DATA)
        monkeypatch.setattr("engine.app.fetch_llms_txt", lambda url, **kw: GOOD_LLMS_DATA)
        monkeypatch.setattr("engine.app.validate_llmstxt", lambda url: {
            "format_valid": True, "link_count": 12,
        })
        monkeypatch.setattr("engine.app._SCRIPTS_OK", True)

    def test_returns_200(self, client, monkeypatch):
        self._mock_audit(monkeypatch)
        resp = client.post("/run-audit", json={"url": "https://example.com"})
        assert resp.status_code == 200

    def test_status_complete(self, client, monkeypatch):
        self._mock_audit(monkeypatch)
        data = client.post("/run-audit", json={"url": "https://example.com"}).json()
        assert data["status"] == "complete"

    def test_scores_present(self, client, monkeypatch):
        self._mock_audit(monkeypatch)
        data = client.post("/run-audit", json={"url": "https://example.com"}).json()
        scores = data["scores"]
        assert set(scores.keys()) == {"overall", "schema", "content", "technical", "crawlers"}
        for k, v in scores.items():
            assert 0 <= v <= 100, f"Score {k}={v} out of range"

    def test_good_site_has_high_overall(self, client, monkeypatch):
        self._mock_audit(monkeypatch)
        data = client.post("/run-audit", json={"url": "https://example.com"}).json()
        assert data["scores"]["overall"] >= 50, "Good site should score at least 50"

    def test_findings_and_fixes_are_lists(self, client, monkeypatch):
        self._mock_audit(monkeypatch)
        data = client.post("/run-audit", json={"url": "https://example.com"}).json()
        assert isinstance(data["findings"], list)
        assert isinstance(data["fixes"], list)

    def test_finding_fields(self, client, monkeypatch):
        self._mock_audit(monkeypatch)
        data = client.post("/run-audit", json={"url": "https://example.com"}).json()
        required = {"category", "severity", "title", "description", "recommendation", "automatable", "fix_type"}
        for f in data["findings"]:
            assert required.issubset(f.keys()), f"Finding missing keys: {f}"

    def test_fix_fields(self, client, monkeypatch):
        self._mock_audit(monkeypatch)
        data = client.post("/run-audit", json={"url": "https://example.com"}).json()
        required = {"fix_type", "title", "description", "mechanism", "score_impact", "payload"}
        for fix in data["fixes"]:
            assert required.issubset(fix.keys()), f"Fix missing keys: {fix}"


# ---------------------------------------------------------------------------
# /run-audit — thin/broken site
# ---------------------------------------------------------------------------

class TestRunAuditThinSite:
    def _mock_thin(self, monkeypatch):
        monkeypatch.setattr("engine.app.fetch_page", lambda url, **kw: MINIMAL_PAGE_DATA)
        monkeypatch.setattr("engine.app.fetch_robots_txt", lambda url, **kw: MINIMAL_ROBOTS_DATA)
        monkeypatch.setattr("engine.app.fetch_llms_txt", lambda url, **kw: MINIMAL_LLMS_DATA)
        monkeypatch.setattr("engine.app._SCRIPTS_OK", True)

    def test_returns_200_even_for_thin_site(self, client, monkeypatch):
        self._mock_thin(monkeypatch)
        resp = client.post("/run-audit", json={"url": "https://thin.example.com"})
        assert resp.status_code == 200

    def test_thin_site_has_low_scores(self, client, monkeypatch):
        self._mock_thin(monkeypatch)
        data = client.post("/run-audit", json={"url": "https://thin.example.com"}).json()
        assert data["scores"]["overall"] < 50

    def test_blocked_crawlers_finding_present(self, client, monkeypatch):
        self._mock_thin(monkeypatch)
        data = client.post("/run-audit", json={"url": "https://thin.example.com"}).json()
        cats = [f["category"] for f in data["findings"]]
        assert "crawlers" in cats

    def test_no_schema_finding_present(self, client, monkeypatch):
        self._mock_thin(monkeypatch)
        data = client.post("/run-audit", json={"url": "https://thin.example.com"}).json()
        schema_findings = [f for f in data["findings"] if f["category"] == "schema"]
        assert len(schema_findings) > 0


# ---------------------------------------------------------------------------
# /run-audit — network failure returns structured error, not 500
# ---------------------------------------------------------------------------

class TestRunAuditFetchFailure:
    def test_bad_url_returns_failed_status_not_500(self, client, monkeypatch):
        monkeypatch.setattr("engine.app.fetch_page", lambda url, **kw: (_ for _ in ()).throw(Exception("DNS failure")))
        monkeypatch.setattr("engine.app._SCRIPTS_OK", True)
        resp = client.post("/run-audit", json={"url": "https://notreal.notadomain.xyz"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert len(data["findings"]) > 0
        assert data["findings"][0]["category"] == "technical"

    def test_http_error_code_returns_failed(self, client, monkeypatch):
        bad_data = dict(GOOD_PAGE_DATA)
        bad_data["status_code"] = 404
        monkeypatch.setattr("engine.app.fetch_page", lambda url, **kw: bad_data)
        monkeypatch.setattr("engine.app.fetch_robots_txt", lambda url, **kw: GOOD_ROBOTS_DATA)
        monkeypatch.setattr("engine.app.fetch_llms_txt", lambda url, **kw: GOOD_LLMS_DATA)
        monkeypatch.setattr("engine.app._SCRIPTS_OK", True)
        resp = client.post("/run-audit", json={"url": "https://example.com/missing"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"


# ---------------------------------------------------------------------------
# /gen-schema
# ---------------------------------------------------------------------------

class TestGenSchema:
    def test_returns_org_schema(self, client):
        resp = client.post("/gen-schema", json={"url": "https://example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mechanism"] == "edge"
        assert data["payload"]["@type"] == "Organization"

    def test_org_name_overrides_derived(self, client):
        resp = client.post("/gen-schema", json={"url": "https://example.com", "org_name": "Acme Corp"})
        assert resp.json()["payload"]["name"] == "Acme Corp"

    def test_url_in_payload(self, client):
        resp = client.post("/gen-schema", json={"url": "https://example.com"})
        assert "https://example.com" in resp.json()["payload"]["url"]

    def test_schema_context(self, client):
        resp = client.post("/gen-schema", json={"url": "https://example.com"})
        assert resp.json()["payload"]["@context"] == "https://schema.org"


# ---------------------------------------------------------------------------
# /gen-llmstxt
# ---------------------------------------------------------------------------

class TestGenLlmstxt:
    def test_returns_content(self, client, monkeypatch):
        monkeypatch.setattr("engine.app.generate_llmstxt", lambda url: GENERATED_LLMSTXT)
        monkeypatch.setattr("engine.app._SCRIPTS_OK", True)
        resp = client.post("/gen-llmstxt", json={"url": "https://example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mechanism"] == "edge"
        assert "content" in data["payload"]

    def test_content_is_string(self, client, monkeypatch):
        monkeypatch.setattr("engine.app.generate_llmstxt", lambda url: GENERATED_LLMSTXT)
        monkeypatch.setattr("engine.app._SCRIPTS_OK", True)
        data = client.post("/gen-llmstxt", json={"url": "https://example.com"}).json()
        assert isinstance(data["payload"]["content"], str)

    def test_generation_failure_returns_422(self, client, monkeypatch):
        monkeypatch.setattr("engine.app.generate_llmstxt", lambda url: (_ for _ in ()).throw(Exception("boom")))
        monkeypatch.setattr("engine.app._SCRIPTS_OK", True)
        resp = client.post("/gen-llmstxt", json={"url": "https://example.com"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /gen-robots
# ---------------------------------------------------------------------------

class TestGenRobots:
    def test_returns_content(self, client):
        resp = client.post("/gen-robots", json={"url": "https://example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mechanism"] == "edge"
        assert "content" in data["payload"]

    def test_gptbot_allowed(self, client):
        content = client.post("/gen-robots", json={"url": "https://example.com"}).json()["payload"]["content"]
        assert "GPTBot" in content
        assert "Allow: /" in content

    def test_claudebot_allowed(self, client):
        content = client.post("/gen-robots", json={"url": "https://example.com"}).json()["payload"]["content"]
        assert "ClaudeBot" in content

    def test_perplexitybot_allowed(self, client):
        content = client.post("/gen-robots", json={"url": "https://example.com"}).json()["payload"]["content"]
        assert "PerplexityBot" in content

    def test_google_extended_allowed(self, client):
        content = client.post("/gen-robots", json={"url": "https://example.com"}).json()["payload"]["content"]
        assert "Google-Extended" in content

    def test_sitemap_included(self, client):
        content = client.post("/gen-robots", json={"url": "https://example.com"}).json()["payload"]["content"]
        assert "Sitemap:" in content


# ---------------------------------------------------------------------------
# scoring.py unit tests
# ---------------------------------------------------------------------------

class TestScoreSchema:
    def test_no_data_returns_zero(self):
        from engine.scoring import score_schema
        assert score_schema([]) == 0

    def test_non_dict_items_ignored(self):
        from engine.scoring import score_schema
        assert score_schema(["string", 123]) == 0

    def test_org_with_all_fields_returns_100(self):
        from engine.scoring import score_schema
        schema = [{"@type": "Organization", "name": "X", "url": "https://x.com", "sameAs": ["https://linkedin.com/x"]}]
        assert score_schema(schema) == 100

    def test_org_without_same_as_returns_85(self):
        from engine.scoring import score_schema
        schema = [{"@type": "Organization", "name": "X", "url": "https://x.com"}]
        assert score_schema(schema) == 85

    def test_org_type_without_fields_returns_70(self):
        from engine.scoring import score_schema
        schema = [{"@type": "Organization"}]
        assert score_schema(schema) == 70

    def test_other_type_returns_55(self):
        from engine.scoring import score_schema
        schema = [{"@type": "WebPage", "name": "X"}]
        assert score_schema(schema) == 55

    def test_no_type_returns_30(self):
        from engine.scoring import score_schema
        schema = [{"name": "Something"}]
        assert score_schema(schema) == 30

    def test_list_type_field_normalized(self):
        from engine.scoring import score_schema
        schema = [{"@type": ["Organization"], "name": "X", "url": "u", "sameAs": ["l"]}]
        assert score_schema(schema) == 100

    def test_best_of_multiple_items(self):
        from engine.scoring import score_schema
        schema = [
            {"@type": "WebPage"},  # 55
            {"@type": "Organization", "name": "X", "url": "u", "sameAs": ["l"]},  # 100
        ]
        assert score_schema(schema) == 100


class TestScoreContent:
    def test_thin_content_low_score(self):
        from engine.scoring import score_content
        s = score_content(100, 10, False, False, False)
        assert s < 30

    def test_rich_content_high_score(self):
        from engine.scoring import score_content
        s = score_content(2000, 80, True, True, True)
        assert s >= 70

    def test_word_count_thresholds(self):
        from engine.scoring import score_content
        # zero citability, no structural
        assert score_content(0, 0, False, False, False) == 0
        assert score_content(300, 0, False, False, False) == 15
        assert score_content(600, 0, False, False, False) == 25
        assert score_content(1000, 0, False, False, False) == 35
        assert score_content(2000, 0, False, False, False) == 40

    def test_h1_adds_10(self):
        from engine.scoring import score_content
        base = score_content(600, 0, False, False, False)
        with_h1 = score_content(600, 0, True, False, False)
        assert with_h1 - base == 10

    def test_meta_desc_adds_10(self):
        from engine.scoring import score_content
        base = score_content(600, 0, False, False, False)
        with_meta = score_content(600, 0, False, True, False)
        assert with_meta - base == 10

    def test_faq_adds_10(self):
        from engine.scoring import score_content
        base = score_content(600, 0, False, False, False)
        with_faq = score_content(600, 0, False, False, True)
        assert with_faq - base == 10

    def test_capped_at_100(self):
        from engine.scoring import score_content
        s = score_content(9999, 100, True, True, True)
        assert s == 100


class TestScoreTechnical:
    def test_all_present_high_score(self):
        from engine.scoring import score_technical
        s = score_technical(True, True, 200, True, 5)
        assert s >= 85

    def test_no_ssr_loses_30(self):
        from engine.scoring import score_technical
        full = score_technical(True, True, 200, True, 5)
        no_ssr = score_technical(False, True, 200, True, 5)
        assert full - no_ssr == 30

    def test_http_not_https_loses_20(self):
        from engine.scoring import score_technical
        with_https = score_technical(True, True, 200, True, 5)
        without = score_technical(True, True, 200, False, 5)
        assert with_https - without == 20

    def test_no_canonical_loses_15(self):
        from engine.scoring import score_technical
        with_c = score_technical(True, True, 200, True, 5)
        without_c = score_technical(True, False, 200, True, 5)
        assert with_c - without_c == 15

    def test_404_loses_20(self):
        from engine.scoring import score_technical
        ok = score_technical(True, True, 200, True, 5)
        not_found = score_technical(True, True, 404, True, 5)
        assert ok - not_found == 20

    def test_security_header_tiers(self):
        from engine.scoring import score_technical
        s0 = score_technical(True, True, 200, True, 0)
        s1 = score_technical(True, True, 200, True, 1)
        s3 = score_technical(True, True, 200, True, 3)
        s5 = score_technical(True, True, 200, True, 5)
        assert s0 < s1 < s3 < s5


class TestScoreCrawlers:
    def test_all_allowed_plus_sitemap_high_score(self):
        from engine.scoring import score_crawlers
        status = {
            "GPTBot": "ALLOWED",
            "ClaudeBot": "ALLOWED",
            "PerplexityBot": "ALLOWED",
            "Google-Extended": "ALLOWED",
        }
        s = score_crawlers(status, True)
        assert s >= 80

    def test_all_blocked_low_score(self):
        from engine.scoring import score_crawlers
        status = {
            "GPTBot": "BLOCKED",
            "ClaudeBot": "BLOCKED",
            "PerplexityBot": "BLOCKED",
            "Google-Extended": "BLOCKED",
        }
        s = score_crawlers(status, False)
        assert s <= 20  # only robots.txt exists bonus

    def test_sitemap_adds_20(self):
        from engine.scoring import score_crawlers
        status = {"GPTBot": "ALLOWED"}
        no_sitemap = score_crawlers(status, False)
        with_sitemap = score_crawlers(status, True)
        assert with_sitemap - no_sitemap == 20

    def test_empty_status_gives_not_mentioned_pts(self):
        from engine.scoring import score_crawlers
        # Empty ai_crawler_status: 4 key crawlers × 10pts (NOT_MENTIONED) = 40
        # No robots.txt bonus (empty dict), no sitemap bonus
        s = score_crawlers({}, False)
        assert s == 40


class TestScoreLlmstxt:
    def test_no_llmstxt_returns_zero(self):
        from engine.scoring import score_llmstxt
        assert score_llmstxt({"llms_txt": {"exists": False}}) == 0

    def test_present_adds_40(self):
        from engine.scoring import score_llmstxt
        assert score_llmstxt({"llms_txt": {"exists": True}}) == 40

    def test_format_valid_adds_30(self):
        from engine.scoring import score_llmstxt
        assert score_llmstxt({"llms_txt": {"exists": True, "format_valid": True}}) == 70

    def test_full_version_adds_20(self):
        from engine.scoring import score_llmstxt
        s = score_llmstxt({
            "llms_txt": {"exists": True, "format_valid": True},
            "llms_full_txt": {"exists": True},
        })
        assert s == 90

    def test_10_links_adds_10_more(self):
        from engine.scoring import score_llmstxt
        s = score_llmstxt({
            "llms_txt": {"exists": True, "format_valid": True, "link_count": 10},
            "llms_full_txt": {"exists": True},
        })
        assert s == 100

    def test_capped_at_100(self):
        from engine.scoring import score_llmstxt
        s = score_llmstxt({
            "llms_txt": {"exists": True, "format_valid": True, "link_count": 999},
            "llms_full_txt": {"exists": True},
        })
        assert s == 100


class TestComputeScores:
    def test_weighted_average(self):
        from engine.scoring import compute_scores
        scores = compute_scores(100, 100, 100, 100, 100)
        assert scores["overall"] == 100

    def test_zeroes(self):
        from engine.scoring import compute_scores
        scores = compute_scores(0, 0, 0, 0, 0)
        assert scores["overall"] == 0

    def test_weights(self):
        from engine.scoring import compute_scores
        # schema=100, rest=0: 100*0.20 = 20
        scores = compute_scores(100, 0, 0, 0, 0)
        assert scores["overall"] == 20

    def test_all_keys_present(self):
        from engine.scoring import compute_scores
        scores = compute_scores(50, 60, 70, 80, 90)
        assert set(scores.keys()) == {"overall", "schema", "content", "technical", "crawlers"}

    def test_clamped_to_100(self):
        from engine.scoring import compute_scores
        scores = compute_scores(110, 110, 110, 110, 110)
        for v in scores.values():
            assert v <= 100


class TestDetectFaqPatterns:
    def test_faq_keyword_detected(self):
        from engine.scoring import detect_faq_patterns
        assert detect_faq_patterns("## FAQ\nQ: What is this?")

    def test_question_block(self):
        from engine.scoring import detect_faq_patterns
        assert detect_faq_patterns("Q: What is X?\nA: X is Y.")

    def test_no_faq(self):
        from engine.scoring import detect_faq_patterns
        assert not detect_faq_patterns("This is a normal paragraph with no questions.")

    def test_frequently_asked(self):
        from engine.scoring import detect_faq_patterns
        assert detect_faq_patterns("Frequently Asked Questions about our service.")
