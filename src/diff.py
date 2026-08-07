"""Diff a fresh scrape against current sheet rows and classify risk.

Dataset-aware via schema.signature(). The pipeline auto-applies low-risk
changesets and routes high-risk ones to the phone-escalation queue.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .schema import signature


@dataclass
class Changeset:
    added: list[dict] = field(default_factory=list)
    updated: list[dict] = field(default_factory=list)   # new version of changed rows
    removed: list[dict] = field(default_factory=list)   # rows gone from scrape
    unchanged: int = 0
    reasons: list[str] = field(default_factory=list)    # why it's risky, if so
    risky: bool = False


def diff(kind: str, fresh: list[dict], current: list[dict], risk_cfg: dict) -> Changeset:
    cur_by_key = {r["row_key"]: r for r in current}
    fresh_by_key = {r["row_key"]: r for r in fresh}
    cs = Changeset()

    for k, r in fresh_by_key.items():
        if k not in cur_by_key:
            cs.added.append(r)
        elif signature(kind, r) != signature(kind, cur_by_key[k]):
            cs.updated.append(r)
        else:
            cs.unchanged += 1
    cs.removed = [r for k, r in cur_by_key.items() if k not in fresh_by_key]

    # Risk classification. First population of an empty tab is never "risky".
    n_cur = len(current)
    if len(fresh) < risk_cfg.get("min_expected_rows", 1):
        cs.risky = True
        cs.reasons.append(f"scrape returned only {len(fresh)} rows (likely broken source)")
    if n_cur:
        if len(cs.removed) / n_cur * 100 > risk_cfg.get("max_auto_delete_pct", 5):
            cs.risky = True
            cs.reasons.append(f"{len(cs.removed)} deletions ({len(cs.removed)/n_cur*100:.0f}% of rows)")
        changed = len(cs.updated) + len(cs.added)
        if changed / n_cur * 100 > risk_cfg.get("max_auto_change_pct", 30):
            cs.risky = True
            cs.reasons.append(f"{changed} adds/updates ({changed/n_cur*100:.0f}% of rows)")
    return cs


def fingerprint(kind: str, cs: Changeset) -> str:
    """Stable hash of *what* changed, so a phone decision binds to that exact diff.

    If the next scrape produces a different change, the fingerprint won't match and
    the stale decision is ignored (we re-escalate) — a safety property.
    """
    blob = json.dumps({
        "add": sorted(r["row_key"] for r in cs.added),
        "rem": sorted(r["row_key"] for r in cs.removed),
        "upd": sorted([r["row_key"], "|".join(signature(kind, r))] for r in cs.updated),
    }, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]
