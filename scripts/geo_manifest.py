#!/usr/bin/env python3
"""
geo_manifest.py — Deliverable manifest standard for GEO skills.

Every GEO skill writes structured metadata about each file it produces
into clients/<folder>/manifest.json. The library UI and future product
read this data to display rich descriptions instead of hand-maintained notes.

Pure stdlib — no external dependencies.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

MANIFEST_FILENAME = "manifest.json"

VALID_CATEGORIES = {"audits", "reports", "proposals", "deliverables", "inputs"}
VALID_AUDIENCES = {"Prospect", "Internal", "Client"}


@dataclass
class Deliverable:
    """Metadata for a single deliverable file produced by a GEO skill."""

    filename: str
    """Bare filename (e.g. 'GEO-AUDIT-REPORT.md') — no path component."""

    category: str
    """Subfolder: audits | reports | proposals | deliverables | inputs."""

    file_type: str
    """Human-readable format description, e.g. 'PDF report', 'Excel workbook',
    'Markdown document', 'HTML file', 'PowerPoint presentation'."""

    title: str
    """Short display name shown in UI and reports (e.g. 'GEO Audit Report')."""

    description: str
    """What the file IS — one or two sentences describing its contents."""

    purpose: str
    """What the file is FOR — what next step it enables or who acts on it."""

    audience: str
    """Primary reader: Prospect | Internal | Client."""

    created: str
    """ISO-8601 date string (YYYY-MM-DD) passed in by the caller.
    Do NOT call datetime.now() here — accept it as a parameter."""

    def validate(self) -> None:
        """Raise ValueError for obviously invalid fields."""
        if not self.filename or "/" in self.filename or "\\" in self.filename:
            raise ValueError(f"filename must be a bare name, got: {self.filename!r}")
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"category must be one of {VALID_CATEGORIES}, got: {self.category!r}"
            )
        if self.audience not in VALID_AUDIENCES:
            raise ValueError(
                f"audience must be one of {VALID_AUDIENCES}, got: {self.audience!r}"
            )
        for field in ("title", "description", "purpose", "created"):
            if not getattr(self, field, "").strip():
                raise ValueError(f"field '{field}' must not be empty")


# ---------------------------------------------------------------------------
# Core I/O helpers
# ---------------------------------------------------------------------------


def _manifest_path(client_folder: Path) -> Path:
    return client_folder / MANIFEST_FILENAME


def _load_raw(client_folder: Path) -> dict:
    """Load raw JSON dict from manifest.json, handling missing/corrupt files."""
    path = _manifest_path(client_folder)
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Root must be a JSON object")
        return data
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as exc:
        # Back up the corrupt file and start fresh
        backup = path.with_suffix(".json.bak")
        try:
            shutil.copy2(path, backup)
        except OSError:
            pass
        print(
            f"[geo_manifest] WARNING: manifest.json was malformed ({exc}). "
            f"Backed up to {backup.name} and recreated."
        )
        return {}


def _save_raw(client_folder: Path, data: dict) -> None:
    """Write dict to manifest.json with UTF-8 encoding and pretty-printing."""
    client_folder.mkdir(parents=True, exist_ok=True)
    path = _manifest_path(client_folder)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def add_deliverable(client_folder: Path, deliverable: Deliverable) -> None:
    """Upsert a Deliverable entry into clients/<folder>/manifest.json.

    Keyed by filename — if the file already has an entry, it is merged/updated
    (new values win). Creates manifest.json if it does not exist yet.

    Args:
        client_folder: Path to the client directory (e.g. Path("clients/stg")).
        deliverable:   Populated Deliverable dataclass instance.
    """
    deliverable.validate()
    data = _load_raw(client_folder)
    existing = data.get(deliverable.filename, {})
    # Merge: existing fields preserved unless overwritten by new values
    merged = {**existing, **asdict(deliverable)}
    data[deliverable.filename] = merged
    _save_raw(client_folder, data)


def load_manifest(client_folder: Path) -> dict[str, dict]:
    """Return the manifest as a dict keyed by filename.

    Returns an empty dict if the manifest does not exist or is empty.

    Args:
        client_folder: Path to the client directory.

    Returns:
        Dict mapping filename -> entry dict.
    """
    return _load_raw(client_folder)


def render_markdown(client_folder: Path) -> str:
    """Return a human-readable 'Deliverables produced' section.

    Suitable for pasting into a skill's final output to summarise what
    was produced. Groups entries by category.

    Args:
        client_folder: Path to the client directory.

    Returns:
        Formatted markdown string.
    """
    data = _load_raw(client_folder)
    if not data:
        return "## Deliverables Produced\n\n_No deliverables registered in manifest.json yet._\n"

    # Group by category preserving insertion order within each group
    by_cat: dict[str, list[dict]] = {}
    for entry in data.values():
        cat = entry.get("category", "deliverables")
        by_cat.setdefault(cat, []).append(entry)

    lines = ["## Deliverables Produced", ""]
    for cat in VALID_CATEGORIES:
        entries = by_cat.get(cat)
        if not entries:
            continue
        lines.append(f"### {cat}/")
        lines.append("")
        for e in entries:
            title = e.get("title") or e.get("filename", "")
            ftype = e.get("file_type", "")
            desc = e.get("description", "")
            purpose = e.get("purpose", "")
            audience = e.get("audience", "")
            created = e.get("created", "")
            lines.append(f"**{title}** ({ftype})")
            if desc:
                lines.append(f"- *What it is:* {desc}")
            if purpose:
                lines.append(f"- *Purpose:* {purpose}")
            if audience:
                lines.append(f"- *Audience:* {audience}")
            if created:
                lines.append(f"- *Created:* {created}")
            lines.append("")

    return "\n".join(lines)
