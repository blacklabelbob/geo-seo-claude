"""
tests/test_geo_manifest.py — pytest suite for scripts/geo_manifest.py

Tests:
  - add_deliverable creates manifest.json and populates it
  - load_manifest returns correct dict keyed by filename
  - upsert merges/updates an existing entry without losing other entries
  - render_markdown produces non-empty output grouped by category
  - malformed JSON is backed up and recreated cleanly
  - the 3 real client manifests load and have non-empty description+purpose
    for every entry present

Run:
    python3 -m pytest tests/test_geo_manifest.py -q
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Dynamic import so we don't need geo_manifest on sys.path by default.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

def _import_geo_manifest():
    spec = importlib.util.spec_from_file_location(
        "geo_manifest", SCRIPTS_DIR / "geo_manifest.py"
    )
    mod = importlib.util.module_from_spec(spec)
    # Must register in sys.modules BEFORE exec so dataclasses can resolve
    # the module's __dict__ when inspecting type annotations (Python 3.13+).
    sys.modules["geo_manifest"] = mod
    spec.loader.exec_module(mod)
    return mod

gm = _import_geo_manifest()
Deliverable = gm.Deliverable
add_deliverable = gm.add_deliverable
load_manifest = gm.load_manifest
render_markdown = gm.render_markdown


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_dir(tmp_path):
    """A fresh temporary client folder for unit tests."""
    d = tmp_path / "test-client"
    d.mkdir()
    return d


def _sample(filename="report.md", category="reports", audience="Client") -> Deliverable:
    return Deliverable(
        filename=filename,
        category=category,
        file_type="Markdown document",
        title="Test Report",
        description="A sample deliverable for testing.",
        purpose="Verify that the manifest system records deliverables correctly.",
        audience=audience,
        created="2026-05-31",
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestAddAndLoad:
    def test_creates_manifest_on_first_add(self, client_dir):
        d = _sample()
        add_deliverable(client_dir, d)
        manifest_path = client_dir / "manifest.json"
        assert manifest_path.exists(), "manifest.json should be created"

    def test_load_returns_entry_keyed_by_filename(self, client_dir):
        d = _sample("audit.md", category="audits")
        add_deliverable(client_dir, d)
        data = load_manifest(client_dir)
        assert "audit.md" in data
        entry = data["audit.md"]
        assert entry["title"] == "Test Report"
        assert entry["category"] == "audits"
        assert entry["created"] == "2026-05-31"

    def test_load_empty_when_no_manifest(self, tmp_path):
        folder = tmp_path / "empty-client"
        folder.mkdir()
        data = load_manifest(folder)
        assert data == {}

    def test_multiple_entries_coexist(self, client_dir):
        add_deliverable(client_dir, _sample("a.md", category="audits"))
        add_deliverable(client_dir, _sample("b.pdf", category="deliverables"))
        data = load_manifest(client_dir)
        assert set(data.keys()) == {"a.md", "b.pdf"}


class TestUpsert:
    def test_upsert_updates_existing_entry(self, client_dir):
        d1 = _sample("report.md")
        add_deliverable(client_dir, d1)

        # Now upsert with a different description
        d2 = Deliverable(
            filename="report.md",
            category="reports",
            file_type="Markdown document",
            title="Updated Title",
            description="Updated description.",
            purpose="Updated purpose.",
            audience="Internal",
            created="2026-05-31",
        )
        add_deliverable(client_dir, d2)

        data = load_manifest(client_dir)
        assert len(data) == 1  # no duplicate keys
        entry = data["report.md"]
        assert entry["title"] == "Updated Title"
        assert entry["description"] == "Updated description."
        assert entry["audience"] == "Internal"

    def test_upsert_preserves_other_entries(self, client_dir):
        add_deliverable(client_dir, _sample("keep.md", category="audits"))
        add_deliverable(client_dir, _sample("update.md", category="reports"))

        updated = Deliverable(
            filename="update.md",
            category="reports",
            file_type="PDF report",
            title="New Title",
            description="New desc.",
            purpose="New purpose.",
            audience="Client",
            created="2026-05-31",
        )
        add_deliverable(client_dir, updated)

        data = load_manifest(client_dir)
        assert "keep.md" in data, "Unrelated entry must not be removed on upsert"
        assert data["update.md"]["title"] == "New Title"


class TestRenderMarkdown:
    def test_render_produces_nonempty_string(self, client_dir):
        add_deliverable(client_dir, _sample("report.md", category="reports"))
        md = render_markdown(client_dir)
        assert isinstance(md, str)
        assert len(md) > 50

    def test_render_includes_title_and_purpose(self, client_dir):
        d = _sample("schema.html", category="deliverables")
        add_deliverable(client_dir, d)
        md = render_markdown(client_dir)
        assert "Test Report" in md
        assert "Verify that the manifest system" in md

    def test_render_groups_by_category(self, client_dir):
        add_deliverable(client_dir, _sample("audit.md", category="audits"))
        add_deliverable(client_dir, _sample("report.pdf", category="reports"))
        md = render_markdown(client_dir)
        assert "### audits/" in md
        assert "### reports/" in md

    def test_render_empty_manifest(self, tmp_path):
        folder = tmp_path / "no-files"
        folder.mkdir()
        md = render_markdown(folder)
        assert "No deliverables registered" in md


class TestMalformedJsonRecovery:
    def test_malformed_json_is_recovered(self, client_dir):
        manifest_path = client_dir / "manifest.json"
        manifest_path.write_text("{ this is not valid json !!!", encoding="utf-8")

        # Should NOT raise; should back up and start fresh
        d = _sample("recovered.md")
        add_deliverable(client_dir, d)

        data = load_manifest(client_dir)
        assert "recovered.md" in data

    def test_malformed_json_creates_backup(self, client_dir):
        manifest_path = client_dir / "manifest.json"
        manifest_path.write_text("NOT JSON", encoding="utf-8")

        add_deliverable(client_dir, _sample("x.md"))

        backup = client_dir / "manifest.json.bak"
        assert backup.exists(), "Backup of corrupt manifest.json should be created"
        assert backup.read_text(encoding="utf-8") == "NOT JSON"

    def test_non_object_root_recovered(self, client_dir):
        manifest_path = client_dir / "manifest.json"
        manifest_path.write_text("[1, 2, 3]", encoding="utf-8")  # array, not object

        add_deliverable(client_dir, _sample("y.md"))
        data = load_manifest(client_dir)
        assert "y.md" in data


class TestValidation:
    def test_invalid_category_raises(self, client_dir):
        d = _sample()
        d.category = "nonsense"
        with pytest.raises(ValueError, match="category"):
            add_deliverable(client_dir, d)

    def test_invalid_audience_raises(self, client_dir):
        d = _sample()
        d.audience = "Aliens"
        with pytest.raises(ValueError, match="audience"):
            add_deliverable(client_dir, d)

    def test_empty_description_raises(self, client_dir):
        d = _sample()
        d.description = "  "
        with pytest.raises(ValueError, match="description"):
            add_deliverable(client_dir, d)

    def test_filename_with_path_separator_raises(self, client_dir):
        d = _sample("subdir/file.md")
        with pytest.raises(ValueError, match="filename"):
            add_deliverable(client_dir, d)


# ---------------------------------------------------------------------------
# Integration: real client manifests
# ---------------------------------------------------------------------------

CLIENTS_DIR = REPO_ROOT / "clients"
REAL_CLIENTS = [
    ("closeclinic", ["CloseClinic-Executive-Deck-2026-04-21.pptx",
                     "CloseClinic-Master-Strategic-Report-2026-04-21.pdf",
                     "CloseClinic-Master-Workbook-2026-04-21.xlsx",
                     "STRATEGIC-INPUTS.md"]),
    ("stg", ["stg-keyword-universe-audit.md",
             "content-gap-analysis-2026-03-20.md",
             "stg-page-rewrites-intros-faqs.md",
             "stg-schema-markup.html",
             "GEO-Product-Blueprint-2026-05-31.html"]),
    ("electron-srl", []),  # no deliverables yet — manifest exists but empty
]


class TestRealClientManifests:
    @pytest.mark.parametrize("folder,expected_files", REAL_CLIENTS)
    def test_manifest_loads(self, folder, expected_files):
        client_folder = CLIENTS_DIR / folder
        data = load_manifest(client_folder)
        assert isinstance(data, dict), f"{folder}/manifest.json should load as a dict"

    @pytest.mark.parametrize("folder,expected_files", REAL_CLIENTS)
    def test_expected_files_present(self, folder, expected_files):
        client_folder = CLIENTS_DIR / folder
        data = load_manifest(client_folder)
        for filename in expected_files:
            assert filename in data, (
                f"{folder}/manifest.json missing entry for '{filename}'"
            )

    @pytest.mark.parametrize("folder,expected_files", REAL_CLIENTS)
    def test_all_entries_have_nonempty_description_and_purpose(self, folder, expected_files):
        client_folder = CLIENTS_DIR / folder
        data = load_manifest(client_folder)
        for filename, entry in data.items():
            desc = (entry.get("description") or "").strip()
            purpose = (entry.get("purpose") or "").strip()
            assert desc, (
                f"{folder}/{filename}: 'description' is empty in manifest.json"
            )
            assert purpose, (
                f"{folder}/{filename}: 'purpose' is empty in manifest.json"
            )

    @pytest.mark.parametrize("folder,expected_files", REAL_CLIENTS)
    def test_render_markdown_runs_without_error(self, folder, expected_files):
        client_folder = CLIENTS_DIR / folder
        md = render_markdown(client_folder)
        assert isinstance(md, str)
