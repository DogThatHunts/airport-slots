#!/usr/bin/env python3
"""Fetch REAL FAA slot-holder totals for DCA/JFK/LGA -> web/data/faa_holdings.json.

Source: FAA Slot Administration "Holder Totals" PDF reports (latest season, S25).
These are aggregated per-carrier slot HOLDINGS (not per-flight), so they get their
own view in the web app rather than being mixed into the marketplace listings.

Needs `pdftotext` (poppler). A browser User-Agent is required (FAA 403s otherwise).
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

# FAA's WAF 403s our bot UA — must present a plain browser UA.
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

PAGE = ("https://www.faa.gov/about/office_org/headquarters_offices/ato/service_units/"
        "systemops/perf_analysis/slot_administration/data")
AIRPORTS = ["DCA", "JFK", "LGA"]
SEASON = "S25"
OUT = Path(__file__).resolve().parents[1] / "web" / "data" / "faa_holdings.json"
ROW = re.compile(r"^\s*([A-Z]{3})\s+(.+?)\s+(\d+)\s*$")


def discover() -> dict[str, str]:
    html = requests.get(PAGE, headers={"User-Agent": USER_AGENT}, timeout=60).text
    hrefs = re.findall(r'href="([^"]+\.pdf)"', html, re.I)
    urls = {}
    for a in AIRPORTS:
        for h in hrefs:
            if re.search(rf"{a}.*{SEASON}.*HOLDER_TOTALS", h, re.I):
                urls[a] = h if h.startswith("http") else "https://www.faa.gov" + h
                break
    return urls


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
    holders = []
    for line in txt.splitlines():
        m = ROW.match(line)
        if m:
            holders.append({"code": m.group(1), "name": m.group(2).strip(),
                            "slots": int(m.group(3))})
    holders.sort(key=lambda h: -h["slots"])
    return season, status, holders


def main() -> None:
    urls = discover()
    missing = [a for a in AIRPORTS if a not in urls]
    if missing:
        print("WARN: no HOLDER_TOTALS URL found for", missing)
    airports = []
    for a, url in urls.items():
        pdf = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60).content
        season, status, holders = parse(pdf)
        airports.append({"airport": a, "season": season, "statusDate": status,
                         "total": sum(h["slots"] for h in holders),
                         "holders": holders, "source": url})
        print(f"  {a}: {len(holders)} carriers, {sum(h['slots'] for h in holders)} slots "
              f"({season} {status})")
    OUT.write_text(json.dumps({
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Real FAA Holder Totals (aggregated per-carrier slot holdings, not per-flight).",
        "airports": airports,
    }, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
