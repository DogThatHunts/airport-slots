"""Stamp raw scraper records into a dataset's canonical shape.

Scrapers return dicts using the dataset's own field names; this just fills any
missing fields, adds provenance, and computes the stable row_key for diffing.
"""
from __future__ import annotations

from .schema import DATASETS, make_key


def normalize(kind: str, raw: list[dict], *, source_key: str, source_url: str,
              seen_at: str) -> list[dict]:
    fields = DATASETS[kind]["fields"]
    out = []
    for r in raw:
        rec = {f: r.get(f, "") for f in fields}
        rec["source_key"] = source_key
        rec["source_url"] = source_url
        rec["last_seen"] = seen_at
        rec["row_key"] = make_key(kind, rec)
        out.append(rec)
    return out
