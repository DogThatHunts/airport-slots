#!/usr/bin/env python3
"""Real US East Coast scheduled-operations layer from BTS On-Time Performance.

These airports (BOS, ATL, MIA, CLT, …) are uncontrolled (no slot allocations),
so we use published flight SCHEDULES as the slot-demand surrogate — real, free,
flight-level (see docs/research-real-data.md). Every reported flight to/from a
target airport is collapsed to a recurring "slot": (carrier, flight, time,
direction, other-end) with a days-of-week set — same modeling as ANAC.

Output: web/data/slots_bts.json = {"month": "...", "listings": [...]}.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PREZIP = ("https://transtats.bts.gov/PREZIP/"
          "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{y}_{m}.zip")
MONTHS = [(2026, 5), (2026, 4), (2026, 3), (2026, 2)]     # try newest first
OUT = Path(__file__).resolve().parents[1] / "web" / "data" / "slots_bts.json"
PER_AIRPORT = 200
WEEKDAY = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}

# East Coast targets (incl. the NY/NJ/DC slot airports, which BTS also covers).
TARGETS = ["PWM", "BOS", "BDL", "JFK", "LGA", "EWR", "PHL", "BWI", "DCA", "IAD",
           "CLT", "RDU", "CHS", "ATL", "SAV", "MIA", "MCO", "FLL", "TPA"]


def download() -> tuple[str, bytes]:
    for y, m in MONTHS:
        r = requests.get(PREZIP.format(y=y, m=m), headers={"User-Agent": UA}, timeout=300)
        if r.status_code == 200 and r.content[:2] == b"PK":
            return f"{y}-{m:02d}", r.content
    raise RuntimeError("no BTS month available")


def hhmm(t: str) -> str:
    t = (t or "").strip().split(".")[0]
    if not t.isdigit():
        return ""
    t = t.zfill(4)
    if t == "2400":
        t = "0000"
    return f"{t[:2]}:{t[2:]}"


def main() -> None:
    month, blob = download()
    zf = zipfile.ZipFile(io.BytesIO(blob))
    csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
    targets = set(TARGETS)
    agg: dict[tuple, dict] = defaultdict(lambda: {"days": set(), "dmin": "9999", "dmax": "0", "n": 0})

    with zf.open(csv_name) as fh:
        reader = csv.reader(io.TextIOWrapper(fh, encoding="latin-1"))
        header = next(reader)
        ix = {name: i for i, name in enumerate(header)}
        c_air = ix["Reporting_Airline"]; c_fn = ix["Flight_Number_Reporting_Airline"]
        c_o = ix["Origin"]; c_d = ix["Dest"]; c_dep = ix["CRSDepTime"]; c_arr = ix["CRSArrTime"]
        c_dow = ix["DayOfWeek"]; c_date = ix["FlightDate"]
        for row in reader:
            o, d = row[c_o], row[c_d]
            if o not in targets and d not in targets:
                continue
            carrier, fn, dow, date = row[c_air], row[c_fn], row[c_dow], row[c_date]
            for apt, direction, t, other in ((o, "dep", row[c_dep], d), (d, "arr", row[c_arr], o)):
                if apt not in targets:
                    continue
                tt = hhmm(t)
                if not tt:
                    continue
                g = agg[(apt, direction, carrier, fn, tt, other)]
                if dow.isdigit():
                    g["days"].add(int(dow))
                g["dmin"] = min(g["dmin"], date); g["dmax"] = max(g["dmax"], date); g["n"] += 1

    by_apt: dict[str, list] = defaultdict(list)
    for (apt, direction, carrier, fn, tt, other), g in agg.items():
        by_apt[apt].append({
            "airport": apt, "market": "US East Coast", "direction": direction,
            "carrier": carrier, "flight_no": fn,
            "days": ",".join(WEEKDAY[x] for x in sorted(g["days"])),
            "time": tt, "aircraft": "", "seats": "", "orig_dest": other, "service": "",
            "window": f"{g['dmin']}..{g['dmax']}", "sim": 0, "src": "BTS", "_n": g["n"],
        })

    listings = []
    for apt, rows in by_apt.items():
        rows.sort(key=lambda r: -r["_n"])          # keep the most-frequent (real recurring) slots
        for r in rows[:PER_AIRPORT]:
            r.pop("_n")
            listings.append(r)

    OUT.write_text(json.dumps({"month": month, "listings": listings}, ensure_ascii=False))
    print(f"month {month}: {len(listings)} listings across {len(by_apt)} airports "
          f"(of {len(TARGETS)} targets)")
    for apt in TARGETS:
        print(f"  {apt}: {min(len(by_apt.get(apt, [])), PER_AIRPORT)}")


if __name__ == "__main__":
    main()
