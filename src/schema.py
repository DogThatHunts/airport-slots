"""Dataset definitions.

The database has two tiers, each its own worksheet:

- `registry`: the global backbone — one row per coordinated airport (WASG Annex
  12.7). Which airports are Level 2/3 per season + coordinator contacts/portals.
- `slots`: actual per-flight slot allocations, filled source-by-source (ANAC
  Brazil first; Hong Kong, FAA later). Openly available for only a few regions.

Each dataset declares its columns, the fields that identify a row (`key`, used
for stable diffing) and the fields whose change is meaningful (`sig`, used to
detect updates). Provenance columns are appended to every row.
"""
from __future__ import annotations

import hashlib

PROVENANCE = ["source_key", "source_url", "last_seen", "row_key"]

DATASETS = {
    "registry": {
        "tab": "airports",
        "fields": ["region", "country", "city", "iata", "current_season",
                   "current_level", "levels", "coordinator_email", "portal",
                   "website", "notes"],
        "key": ["iata"],
        "sig": ["current_level", "levels", "coordinator_email", "portal", "website"],
    },
    "slots": {
        "tab": "slots",
        "fields": ["airport", "season", "direction", "carrier", "flight_no",
                   "days", "slot_time", "aircraft", "seats", "orig_dest",
                   "service", "status"],
        # Identity of a recurring slot (days-of-week is an attribute, not identity).
        "key": ["airport", "season", "direction", "carrier", "flight_no", "slot_time"],
        "sig": ["days", "aircraft", "seats", "orig_dest", "service", "status"],
    },
}


def columns(kind: str) -> list[str]:
    return DATASETS[kind]["fields"] + PROVENANCE


def make_key(kind: str, rec: dict) -> str:
    parts = [str(rec.get(k, "")).strip().lower() for k in DATASETS[kind]["key"]]
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


def signature(kind: str, rec: dict) -> tuple:
    return tuple(str(rec.get(k, "")) for k in DATASETS[kind]["sig"])
