#!/usr/bin/env python3
"""
GEO Report Library — Web UI (Flask + HTMX)  ·  STG edition (English)

What this is:
    A local library of the websites you have analyzed. Plug in a site, run a
    GEO/SEO audit, and every report, proposal and deliverable for that site
    shows up here — categorized, explained, and downloadable. No external CRM
    is required or connected; this is just a viewer over local files.

Where data lives (all inside the project, nothing hidden in your home folder):
    Project root: <project>/
    Records:      <project>/clients/_crm-data/prospects.json
    Per-site:     <project>/clients/<folder>/{audits,reports,proposals,deliverables,inputs}/
    (~/.geo-prospects is a symlink to clients/_crm-data so the GEO skills keep working.)

Usage:
    pip install flask
    python app.py
    open http://localhost:5050
"""

import json
import re
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, send_file, abort

app = Flask(__name__)


@app.context_processor
def inject_now():
    return {"now": datetime.now().strftime("%Y-%m-%d %H:%M")}


CRM_PATH = Path.home() / ".geo-prospects" / "prospects.json"
PROPOSALS_DIR = Path.home() / ".geo-prospects" / "proposals"
AUDITS_DIR = Path.home() / ".geo-prospects" / "audits"

# Project's clients/ folder — one folder per site, holds all outputs.
# app.py lives at <project>/scripts/webapp/app.py → root is three parents up.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLIENTS_DIR = PROJECT_ROOT / "clients"

# Output categories shown on a site page (folder, label, blurb).
OUTPUT_CATEGORIES = [
    ("audits",       "Audits",       "GEO / SEO audit files — the analysis of the site."),
    ("reports",      "Reports",      "Progress reports and month-over-month comparisons."),
    ("proposals",    "Proposals",    "Proposals and pricing for the engagement."),
    ("deliverables", "Deliverables", "Client-facing final outputs — decks, reports, workbooks."),
    ("inputs",       "Inputs",       "Source material the deliverables were built from."),
]

EXT_DESC = {
    ".pptx": "PowerPoint deck", ".ppt": "PowerPoint deck",
    ".pdf": "PDF document",
    ".xlsx": "Excel workbook", ".xls": "Excel workbook", ".csv": "CSV data",
    ".docx": "Word document", ".doc": "Word document",
    ".md": "Markdown document", ".txt": "Text file", ".json": "JSON data",
    ".html": "HTML page",
}

EXT_ICON = {
    ".pptx": "bi-file-earmark-slides", ".ppt": "bi-file-earmark-slides",
    ".pdf": "bi-file-earmark-pdf",
    ".xlsx": "bi-file-earmark-spreadsheet", ".xls": "bi-file-earmark-spreadsheet",
    ".csv": "bi-file-earmark-spreadsheet",
    ".docx": "bi-file-earmark-word", ".doc": "bi-file-earmark-word",
    ".md": "bi-file-earmark-text", ".txt": "bi-file-earmark-text",
    ".json": "bi-file-earmark-code", ".html": "bi-file-earmark-code",
}

CURRENCY_SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£"}


# ── Helpers ────────────────────────────────────────────────────────────

def load_prospects() -> list[dict]:
    if not CRM_PATH.exists():
        return []
    with open(CRM_PATH) as f:
        return json.load(f)


def save_prospects(prospects: list[dict]):
    with open(CRM_PATH, "w") as f:
        json.dump(prospects, f, indent=2, ensure_ascii=False)


def score_tier(score) -> str:
    if score is None:
        return "none"
    if score >= 80:
        return "good"
    if score >= 60:
        return "moderate"
    if score >= 40:
        return "poor"
    return "critical"


def score_label(score) -> str:
    if score is None:
        return "Not scored"
    if score >= 80:
        return "Good"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Poor"
    return "Critical"


def format_money(value, currency="USD") -> str:
    if not value:
        return "—"
    sym = CURRENCY_SYMBOL.get(currency, "$")
    return f"{sym}{int(value):,}"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def client_folder(prospect: dict) -> Path:
    """The clients/<slug>/ folder that holds this site's outputs."""
    name = prospect.get("folder") or slugify(prospect.get("company", ""))
    return CLIENTS_DIR / name


def load_manifest(folder: Path) -> dict:
    """Read clients/<folder>/manifest.json (written by the geo skills). Keyed by
    filename; each entry carries a description + purpose. Resilient to missing /
    malformed files."""
    mf = folder / "manifest.json"
    if not mf.exists():
        return {}
    try:
        data = json.loads(mf.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def list_outputs(prospect: dict) -> list[dict]:
    """Scan the site's client folder and return outputs grouped by category.

    Per-file explanations come from the skill-written manifest.json (preferred),
    falling back to the record's "file_notes" map; type/icon from the extension.
    """
    folder = client_folder(prospect)
    notes = prospect.get("file_notes", {})
    manifest = load_manifest(folder)
    categories = []
    for key, label, blurb in OUTPUT_CATEGORIES:
        d = folder / key
        if not d.exists():
            continue
        files = []
        for f in sorted(d.iterdir()):
            if not f.is_file() or f.name.startswith(".") or f.name.lower() == "readme.md":
                continue
            ext = f.suffix.lower()
            entry = manifest.get(f.name, {})
            desc = entry.get("description") or notes.get(f.name, "")
            files.append({
                "name": f.name,
                "category": key,
                "size_kb": round(f.stat().st_size / 1024),
                "type": entry.get("file_type") or EXT_DESC.get(ext, "File"),
                "icon": EXT_ICON.get(ext, "bi-file-earmark"),
                "desc": desc,
                "purpose": entry.get("purpose", ""),
            })
        if files:
            categories.append({"key": key, "label": label, "blurb": blurb, "files": files})
    return categories


def count_outputs(prospect: dict) -> int:
    return sum(len(c["files"]) for c in list_outputs(prospect))


def library_stats(prospects: list[dict]) -> dict:
    total = len(prospects)
    scored = [p for p in prospects if p.get("geo_score") is not None]
    avg_score = round(sum(p["geo_score"] for p in scored) / len(scored)) if scored else 0
    reports = sum(count_outputs(p) for p in prospects)
    proposals = len([p for p in prospects if p.get("status") == "proposal"])
    return {
        "total": total,
        "scored": len(scored),
        "avg_score": avg_score,
        "avg_tier": score_tier(avg_score) if scored else "none",
        "reports": reports,
        "proposals": proposals,
    }


# ── Template filters ────────────────────────────────────────────────────

app.jinja_env.filters["score_tier"] = score_tier
app.jinja_env.filters["score_label"] = score_label


@app.template_filter("money")
def money_filter(value, currency="USD"):
    return format_money(value, currency)


STATUS_META = {
    "lead":     {"icon": "⬜", "badge": "secondary", "label": "New"},
    "audit":    {"icon": "\U0001f50d", "badge": "warning", "label": "Audited"},
    "proposal": {"icon": "\U0001f4c4", "badge": "info", "label": "Proposal Sent"},
    "active":   {"icon": "✅", "badge": "success", "label": "Active"},
    "won":      {"icon": "\U0001f3c6", "badge": "success", "label": "Won"},
    "archived": {"icon": "\U0001f5c4️", "badge": "dark", "label": "Archived"},
    "lost":     {"icon": "\U0001f480", "badge": "dark", "label": "Lost"},
}


@app.template_filter("status_meta")
def status_meta_filter(status: str) -> dict:
    return STATUS_META.get(status, {"icon": "?", "badge": "secondary", "label": status})


# ── Routes ─────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    prospects = load_prospects()
    status_filter = request.args.get("status", "")
    sort = request.args.get("sort", "score")

    filtered = [p for p in prospects if not status_filter or p.get("status") == status_filter]

    if sort == "score":
        filtered.sort(key=lambda x: (x.get("geo_score") is None, x.get("geo_score") or 0))
    elif sort == "company":
        filtered.sort(key=lambda x: x.get("company", "").lower())
    elif sort == "reports":
        filtered.sort(key=lambda x: count_outputs(x), reverse=True)

    # attach a live report count to each card
    for p in filtered:
        p["_report_count"] = count_outputs(p)

    stats = library_stats(prospects)
    statuses = list(STATUS_META.keys())

    return render_template(
        "dashboard.html",
        prospects=filtered,
        stats=stats,
        status_filter=status_filter,
        sort=sort,
        statuses=statuses,
        STATUS_META=STATUS_META,
    )


@app.route("/prospect/<pid>")
def prospect_detail(pid):
    prospects = load_prospects()
    p = next((x for x in prospects if x.get("id") == pid), None)
    if not p:
        abort(404)

    outputs = list_outputs(p)

    return render_template(
        "prospect.html",
        p=p,
        outputs=outputs,
        STATUS_META=STATUS_META,
        statuses=list(STATUS_META.keys()),
    )


@app.route("/prospect/<pid>/note", methods=["POST"])
def add_note(pid):
    """HTMX endpoint — returns updated notes fragment."""
    prospects = load_prospects()
    p = next((x for x in prospects if x.get("id") == pid), None)
    if not p:
        abort(404)

    text = request.form.get("text", "").strip()
    if text:
        p.setdefault("notes", [])
        p["notes"].append({
            "date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "text": text,
        })
        p["updated_at"] = datetime.now().strftime("%Y-%m-%d")
        save_prospects(prospects)

    return render_template("_notes.html", p=p)


@app.route("/prospect/<pid>/status", methods=["POST"])
def update_status(pid):
    """HTMX endpoint — update status, returns badge fragment."""
    prospects = load_prospects()
    p = next((x for x in prospects if x.get("id") == pid), None)
    if not p:
        abort(404)

    new_status = request.form.get("status", "").strip()
    if new_status in STATUS_META:
        p["status"] = new_status
        p["updated_at"] = datetime.now().strftime("%Y-%m-%d")
        save_prospects(prospects)

    meta = STATUS_META.get(p["status"], {})
    return f'<span class="badge bg-{meta["badge"]} fs-6">{meta["icon"]} {meta["label"]}</span>'


@app.route("/prospect/<pid>/file/<category>/<path:filename>")
def download_file(pid, category, filename):
    """Securely serve a single output file from clients/<folder>/<category>/."""
    prospects = load_prospects()
    p = next((x for x in prospects if x.get("id") == pid), None)
    if not p:
        abort(404)
    if category not in {c[0] for c in OUTPUT_CATEGORIES}:
        abort(404)

    base = (client_folder(p) / category).resolve()
    target = (base / filename).resolve()
    # path-traversal guard: target must stay inside the category folder
    if base not in target.parents or not target.is_file():
        abort(404)

    return send_file(target, as_attachment=True, download_name=target.name)


# ── Run ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5050)
