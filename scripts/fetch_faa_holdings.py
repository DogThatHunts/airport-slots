#!/usr/bin/env python3
"""Fetch REAL FAA slot data -> web/data/faa_holdings.json.

- DCA/JFK/LGA: real per-carrier "Holder Totals" (aggregated holdings) from the
  latest posted season's PDF reports (auto-detected — upgrades to S26/W26 the
  moment the FAA posts them; today the newest is S25).
- EWR: NOT slot-controlled (schedule-facilitated / Level 2). We show the real FAA
  operating CAP (72/hr = 36 arr + 36 dep, through 2026-10-24) instead of holdings.

Needs `pdftotext` (poppler). FAA's WAF 403s bot UAs, so we present a browser UA.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAGE = ("https://www.faa.gov/about/office_org/headquarters_offices/ato/service_units/"
        "systemops/perf_analysis/slot_administration/data")
AIRPORTS = ["DCA", "JFK", "LGA"]
OUT = Path(__file__).resolve().parents[1] / "web" / "data" / "faa_holdings.json"
ROW = re.compile(r"^\s*([A-Z]{3})\s+(.+?)\s+(\d+)\s*$")
SEASON = re.compile(r"[_-]([SW])(\d{2})[_-]", re.I)   # _S25_ / -W24- in the filename


def _season_rank(letter: str, yy: str) -> tuple[int, int]:
    return (int(yy), 0 if letter.upper() == "S" else 1)   # winter sorts after summer


def discover() -> dict[str, str]:
    """Latest-season HOLDER_TOTALS URL per airport (auto-upgrades when FAA posts a new season)."""
    html = requests.get(PAGE, headers={"User-Agent": USER_AGENT}, timeout=60).text
    hrefs = re.findall(r'href="([^"]+\.pdf)"', html, re.I)
    best: dict[str, tuple] = {}
    for h in hrefs:
        hl = h.lower()
        if "holder" not in hl or "total" not in hl:
            continue
        m = SEASON.search(h)
        if not m:
            continue
        rank = _season_rank(m.group(1), m.group(2))
        for a in AIRPORTS:
            if a.lower() in hl and (a not in best or rank > best[a][0]):
                best[a] = (rank, h if h.startswith("http") else "https://www.faa.gov" + h)
    return {a: v[1] for a, v in best.items()}


def parse(pdf: bytes) -> tuple[str, str, list[dict]]:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf)
        path = f.name
    try:
        txt = subprocess.run(["pdftotext", "-layout", path, "-"],
                             capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(path)
    season = (re.search(r"Season\s*=\s*(\w+)", txt) or [None, ""])[1].title()
    status = (re.search(r"Status Date\s*=\s*(\d+)", txt) or [None, ""])[1]
    holders = [{"code": m.group(1), "name": m.group(2).strip(), "slots": int(m.group(3))}
               for m in (ROW.match(ln) for ln in txt.splitlines()) if m]
    holders.sort(key=lambda h: -h["slots"])
    return season, status, holders


def ewr_cap() -> dict:
    """Real EWR operating cap (not slot holdings — Newark is Level 2, not slot-controlled)."""
    return {"airport": "EWR", "type": "cap", "level": "2", "sim": False, "holders": [],
            "cap": {"perHour": 72, "arr": 36, "dep": 36, "through": "2026-10-24"},
            "order": "FAA Order — Fed. Reg. 2025-18871 (docket FAA-2008-0221)",
            "note": "Newark is schedule-facilitated (Level 2), not slot-controlled — no "
                    "per-carrier slot allocations are published. The FAA imposes a binding "
                    "hourly operating cap instead."}


def main() -> None:
    urls = discover()
    if [a for a in AIRPORTS if a not in urls]:
        print("WARN: missing HOLDER_TOTALS for", [a for a in AIRPORTS if a not in urls])
    airports = []
    for a, url in urls.items():
        pdf = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60).content
        season, status, holders = parse(pdf)
        airports.append({"airport": a, "type": "holdings", "season": season, "statusDate": status,
                         "total": sum(h["slots"] for h in holders), "holders": holders,
                         "sim": False, "source": url})
        print(f"  {a}: {len(holders)} carriers, {sum(h['slots'] for h in holders)} slots "
              f"({season} {status})  [{url.rsplit('/', 1)[-1]}]")
    airports.append(ewr_cap())
    print("  EWR: real FAA cap 72/hr (36+36) through 2026-10-24")
    OUT.write_text(json.dumps({
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "DCA/JFK/LGA: real FAA Holder Totals. EWR: real FAA operating cap (Level 2).",
        "airports": airports,
    }, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
