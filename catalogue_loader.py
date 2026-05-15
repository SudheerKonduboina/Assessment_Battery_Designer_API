# catalogue_loader.py
# ─────────────────────────────────────────────────────────────────────────────
# SHL Assessment Catalogue Ingestion Pipeline
# Reads: shl_product_catalogue.json (project root)
# Outputs: validated, normalized, indexed catalogue object
# Run independently: python catalogue_loader.py
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import Optional


# ── TYPE DERIVATION (mirrors ranker.py — kept in sync) ───────────────────────

_TYPE_PRIORITY: list[str] = [
    "Ability & Aptitude",
    "Personality & Behavior",
    "Biodata & Situational Judgment",
    "Simulations",
    "Knowledge & Skills",
    "Competencies",
    "Development & 360",
    "Assessment Exercises",
]

_KEY_TO_TYPE: dict[str, str] = {
    "Ability & Aptitude":              "A",
    "Personality & Behavior":          "P",
    "Biodata & Situational Judgment":  "B",
    "Simulations":                     "S",
    "Knowledge & Skills":              "K",
    "Competencies":                    "P",
    "Development & 360":               "P",
    "Assessment Exercises":            "S",
}

def derive_type(item: dict) -> str:
    for priority_key in _TYPE_PRIORITY:
        if priority_key in item.get("keys", []):
            return _KEY_TO_TYPE[priority_key]
    return "K"


# ── VALIDATION ────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {"entity_id", "name", "link", "description", "keys"}

VALID_JOB_LEVELS = {
    "Director", "Entry-Level", "Executive", "General Population",
    "Graduate", "Manager", "Mid-Professional", "Front Line Manager",
    "Professional Individual Contributor", "Supervisor",
}

def validate_entry(entry: dict, index: int) -> list[str]:
    """Validate a single catalogue entry. Returns list of error strings."""
    errors: list[str] = []

    # Required fields present and non-empty
    for f in REQUIRED_FIELDS:
        if f not in entry:
            errors.append(f"[{index}] Missing required field: '{f}'")
        elif not entry[f]:
            errors.append(f"[{index}] Empty required field: '{f}'")

    # URL format
    link = entry.get("link", "")
    if link and not link.startswith("https://www.shl.com/"):
        errors.append(f"[{index}] Invalid URL format: '{link[:60]}'")

    # Keys must be a list
    if not isinstance(entry.get("keys", []), list):
        errors.append(f"[{index}] 'keys' must be a list")

    # Pre-packaged Job Solutions exclusion guard
    name = entry.get("name", "").lower()
    desc = entry.get("description", "").lower()
    if "pre-packaged" in desc or "job solution" in desc:
        errors.append(f"[{index}] Suspected Pre-packaged Job Solution: '{entry.get('name', '')}'")

    return errors


# ── NORMALIZATION ─────────────────────────────────────────────────────────────

def normalize_entry(entry: dict) -> dict:
    """
    Normalize a single catalogue entry.
    - Strips whitespace from string fields
    - Ensures job_levels and keys are clean lists
    - Adds derived assessment_type
    - Normalizes remote/adaptive to bool
    """
    return {
        "entity_id":       str(entry.get("entity_id", "")).strip(),
        "name":            entry.get("name", "").strip(),
        "url":             entry.get("link", "").strip(),       # normalize to 'url' key
        "description":     entry.get("description", "").strip(),
        "job_levels":      [lvl.strip() for lvl in entry.get("job_levels", []) if lvl.strip()],
        "keys":            [k.strip() for k in entry.get("keys", []) if k.strip()],
        "languages":       [lg.strip() for lg in entry.get("languages", []) if lg.strip()],
        "duration":        entry.get("duration", "").strip(),
        "remote":          entry.get("remote", "no").strip().lower() == "yes",
        "adaptive":        entry.get("adaptive", "no").strip().lower() == "yes",
        "assessment_type": derive_type(entry),
    }


# ── INDEX BUILDER ─────────────────────────────────────────────────────────────

@dataclass
class CatalogueIndex:
    """
    Searchable index over the normalized catalogue.
    Built once at startup. Used by ranker.py for O(1) lookups.
    """
    all_items:             list[dict]             = field(default_factory=list)
    by_entity_id:          dict[str, dict]        = field(default_factory=dict)
    assessments_by_level:  dict[str, list[dict]]  = field(default_factory=lambda: defaultdict(list))
    assessments_by_type:   dict[str, list[dict]]  = field(default_factory=lambda: defaultdict(list))
    assessments_by_skill:  dict[str, list[dict]]  = field(default_factory=lambda: defaultdict(list))
    name_lookup:           dict[str, dict]        = field(default_factory=dict)   # lowercase name → item


def build_index(normalized_items: list[dict]) -> CatalogueIndex:
    idx = CatalogueIndex()
    idx.all_items = normalized_items

    for item in normalized_items:
        eid  = item["entity_id"]
        atype = item["assessment_type"]

        # Primary indices
        idx.by_entity_id[eid]       = item
        idx.assessments_by_type[atype].append(item)
        idx.name_lookup[item["name"].lower()] = item

        # By job level
        for lvl in item["job_levels"]:
            idx.assessments_by_level[lvl].append(item)

        # By skill key
        for key in item["keys"]:
            idx.assessments_by_skill[key].append(item)

    return idx


# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────

def load_catalogue(
    path: str | Path = "app/data/shl_product_catalogue.json",
    strict: bool = False,
) -> CatalogueIndex:
    """
    Full ingestion pipeline.
    """
    catalogue_path = Path(path)
    if not catalogue_path.exists():
        raise FileNotFoundError(
            f"Catalogue not found at '{catalogue_path.resolve()}'."
        )

    print(f"[catalogue_loader] Reading: {catalogue_path.resolve()}")
    with open(catalogue_path, encoding="utf-8") as f:
        raw: list[dict] = json.load(f)

    if not isinstance(raw, list):
        raise ValueError("shl_product_catalogue.json must be a JSON array at the top level.")

    print(f"[catalogue_loader] Raw entries: {len(raw)}")

    # Step 1: Validate
    all_errors: list[str] = []
    valid_raw:  list[dict] = []

    for i, entry in enumerate(raw):
        errors = validate_entry(entry, i)
        if errors:
            all_errors.extend(errors)
            if strict:
                raise ValueError("\n".join(errors))
            # Skip this entry — log the problem and continue
            print(f"  [WARN] Skipping entry {i} ('{entry.get('name', 'unknown')}') — {len(errors)} validation error(s)")
        else:
            valid_raw.append(entry)

    print(f"[catalogue_loader] Valid entries after validation: {len(valid_raw)}")
    if all_errors:
        print(f"[catalogue_loader] Total validation warnings: {len(all_errors)}")

    # Step 2: Normalize
    normalized = [normalize_entry(e) for e in valid_raw]

    # Step 3: Build index
    idx = build_index(normalized)

    # Step 4: Summary
    type_counts = Counter(item["assessment_type"] for item in normalized)
    print(f"[catalogue_loader] Index built successfully.")
    print(f"  Total items indexed : {len(normalized)}")
    print(f"  By type             : K={type_counts.get('K',0)}  A={type_counts.get('A',0)}  "
          f"P={type_counts.get('P',0)}  B={type_counts.get('B',0)}  S={type_counts.get('S',0)}")
    print(f"  Job levels indexed  : {len(idx.assessments_by_level)}")
    print(f"  Skill keys indexed  : {len(idx.assessments_by_skill)}")
    print(f"  Name lookup entries : {len(idx.name_lookup)}")

    return idx


# ── STANDALONE ENTRYPOINT ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("SHL Catalogue Ingestion Pipeline — Standalone Validation Run")
    print("=" * 60)

    try:
        idx = load_catalogue()
    except (FileNotFoundError, ValueError) as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    # Sample output — show 3 entries per type
    for atype in ["K", "A", "P", "B", "S"]:
        samples = idx.assessments_by_type.get(atype, [])[:3]
        print(f"\n  Type {atype} sample ({len(idx.assessments_by_type.get(atype,[]))} total):")
        for s in samples:
            print(f"    - {s['name'][:55]:55s} | levels: {s['job_levels'][:2]}")

    print("\n[catalogue_loader] Pipeline complete. Ready for use by ranker.py.")
    print("=" * 60)
