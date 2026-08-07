"""Orchestrator: scrape -> normalize -> diff -> auto-apply | escalate | act-on-decision.

Each source declares a `kind` (registry | slots) selecting its dataset/tab.

Human-in-the-loop loop (AFK phone steering):
- A low-risk changeset auto-applies.
- A risky one is escalated as a PENDING row in `_review` (fingerprinted).
- You set that row's `status` from your phone: APPLY / SKIP / RETRY.
- On the next run, if the change still matches the fingerprint, we honor it:
  APPLY -> force-write, SKIP -> leave the Sheet as-is (stop nagging). A changed
  diff won't match the stale decision, so we re-escalate — a safety property.

Writes a JSON summary to state/ so the doorbell/notifier can decide whether to ping.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import scrapers, sheets
from .diff import diff, fingerprint
from .normalize import normalize

STATE = "state/last_run.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve(existing: dict | None, fp: str) -> str:
    """Map the latest review row for a source + current fingerprint to an action."""
    if existing and str(existing.get("fingerprint", "")) == fp:
        st = str(existing.get("status", "")).strip().upper()
        if st == "APPLY":
            return "apply"
        if st == "SKIP":
            return "skip"
        if st == "PENDING":
            return "await"      # already queued for this exact diff — don't duplicate
    return "escalate"           # new/changed diff, RETRY, or no prior row


def _apply(ss, cfg: dict, kind: str, src_key: str, current: list[dict],
           fresh: list[dict], cs, ts: str) -> None:
    others = [r for r in current if r.get("source_key") != src_key]
    sheets.write_dataset(ss, kind, others + fresh)
    sheets.append_changelog(ss, cfg, [[ts, src_key, "apply",
                            f"+{len(cs.added)} ~{len(cs.updated)} -{len(cs.removed)}"]])


def run_source(ss, cfg: dict, src: dict) -> dict:
    ts = _now()
    kind = src["kind"]
    scraper = scrapers.load(src["key"], src.get("url", ""), src.get("format", "unknown"),
                            src.get("opts", {}))
    fresh = normalize(kind, scraper.fetch(), source_key=src["key"],
                      source_url=src.get("url", ""), seen_at=ts)

    current = sheets.read_dataset(ss, kind)
    current_src = [r for r in current if r.get("source_key") == src["key"]]
    cs = diff(kind, fresh, current_src, cfg.get("risk", {}))
    fp = fingerprint(kind, cs)

    result = {
        "ts": ts, "source": src["key"], "kind": kind, "fingerprint": fp,
        "added": len(cs.added), "updated": len(cs.updated),
        "removed": len(cs.removed), "unchanged": cs.unchanged,
        "reasons": cs.reasons, "risky": False,
    }

    if not cs.risky:
        _apply(ss, cfg, kind, src["key"], current, fresh, cs, ts)
        result["action"] = "applied"
        sheets.write_meta(ss, cfg, [[ts, src["key"], len(fresh), "ok"]])
        return result

    # Risky — consult the decision you may have set from your phone.
    reviews = [r for r in sheets.read_review(ss, cfg) if r.get("source") == src["key"]]
    existing = max(reviews, key=lambda r: r["_row"]) if reviews else None
    action = _resolve(existing, fp)

    if action == "apply":
        _apply(ss, cfg, kind, src["key"], current, fresh, cs, ts)
        sheets.set_review_status(ss, cfg, existing["_row"], "APPLIED")
        result["action"] = "applied-by-decision"
    elif action == "skip":
        result["action"] = "skipped-by-decision"          # leave the Sheet untouched
    elif action == "await":
        result["action"] = "awaiting-decision"            # already PENDING; no new row
        result["risky"] = True
    else:  # escalate
        sheets.write_review(ss, cfg, [[ts, src["key"], "; ".join(cs.reasons),
                            len(cs.added), len(cs.updated), len(cs.removed), fp, "PENDING"]])
        result["action"] = "escalated"
        result["risky"] = True

    sheets.write_meta(ss, cfg, [[ts, src["key"], len(fresh),
                                 "ok" if not result["risky"] else "needs-review"]])
    return result


def run(cfg: dict) -> dict:
    ss = sheets.open_sheet(cfg)
    results = []
    for src in cfg.get("sources", []):
        if not src.get("enabled"):
            continue
        try:
            results.append(run_source(ss, cfg, src))
        except Exception as e:  # noqa: BLE001 — one broken source shouldn't kill the run
            results.append({"ts": _now(), "source": src["key"], "action": "error",
                            "error": str(e), "risky": True, "reasons": [f"exception: {e}"]})

    summary = {"ts": _now(), "results": results,
               "needs_attention": [r for r in results if r.get("risky")]}
    with open(STATE, "w") as f:
        json.dump(summary, f, indent=2)
    return summary
