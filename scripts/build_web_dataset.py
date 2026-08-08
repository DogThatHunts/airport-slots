#!/usr/bin/env python3
"""Build the SlotEx demo dataset: web/data/{registry,slots}.json.

- REAL Brazil slots (ANAC) read from the Sheet, stratified-sampled.  sim=0
- SIMULATED listings for major US + European Level-3 hubs.            sim=1
  (Real open per-flight slot data doesn't exist for the US/EU — see WAYPOINT —
   so hubs are synthetic but realistic, and clearly flagged for the UI.)

The real pipeline/Sheet stay REAL-only; simulation lives here in the web export.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import sheets  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "web" / "data"
PER_BR_AIRPORT = 250

AC_SHORT = ["32N", "32Q", "321", "738", "7M8", "223", "319", "E90"]
AC_LONG = ["359", "789", "77W", "333", "351", "7M9", "339"]
SEATS = {"32N": 186, "32Q": 186, "321": 220, "738": 189, "7M8": 186, "223": 160,
         "319": 150, "E90": 100, "359": 315, "789": 290, "77W": 350, "333": 290,
         "351": 330, "7M9": 330, "339": 290}
DAY_PATTERNS = ["Mon,Tue,Wed,Thu,Fri", "Mon,Tue,Wed,Thu,Fri,Sat,Sun",
                "Sat,Sun", "Mon,Wed,Fri", "Tue,Thu,Sat", "Mon,Tue,Wed,Thu,Fri,Sun"]

# hub: (market, carriers[dominant first], haul)  haul: short|mix|long
HUBS = {
    "LHR": ("Europe", ["BA", "VS", "U2", "AA"], "mix"),
    "LGW": ("Europe", ["U2", "BA", "TOM"], "short"),
    "CDG": ("Europe", ["AF", "U2", "TO"], "mix"),
    "ORY": ("Europe", ["AF", "TO", "U2"], "short"),
    "FRA": ("Europe", ["LH", "EW", "AF"], "mix"),
    "MUC": ("Europe", ["LH", "EW"], "mix"),
    "AMS": ("Europe", ["KL", "HV", "TO"], "mix"),
    "MAD": ("Europe", ["IB", "UX", "VY"], "mix"),
    "BCN": ("Europe", ["VY", "IB", "U2"], "short"),
    "FCO": ("Europe", ["AZ", "U2"], "mix"),
    "MXP": ("Europe", ["AZ", "U2", "EW"], "short"),
    "LIS": ("Europe", ["TP", "FR"], "mix"),
    "DUB": ("Europe", ["EI", "FR"], "short"),
    "ZRH": ("Europe", ["LX", "U2"], "mix"),
    "VIE": ("Europe", ["OS", "FR"], "short"),
    "CPH": ("Europe", ["SK", "D8"], "short"),
    "ARN": ("Europe", ["SK", "D8"], "short"),
    "DUS": ("Europe", ["EW", "U2"], "short"),
    "MAN": ("Europe", ["U2", "TOM", "BA"], "short"),
    # US hubs are now covered by REAL BTS scheduled data (scripts/fetch_bts_eastcoast.py),
    # so they are no longer simulated here. Europe stays simulated (no open EU slot data).
}
PER_HUB = 90
WINDOWS = ["2026-03-29..2026-10-24", "2026-10-25..2027-03-27"]


def weighted_time(rnd: random.Random) -> str:
    # bias toward morning/evening peaks
    bucket = rnd.choices(["peakAM", "day", "peakPM", "eve"], weights=[3, 2, 3, 1])[0]
    hr = {"peakAM": rnd.randint(6, 9), "day": rnd.randint(10, 16),
          "peakPM": rnd.randint(17, 20), "eve": rnd.randint(21, 22)}[bucket]
    return f"{hr:02d}:{rnd.choice(['00','05','10','15','20','25','30','35','40','45','50','55'])}"


def simulate(rnd_seed_airports: list[str]) -> list[dict]:
    out = []
    hubs = list(HUBS)
    for apt in rnd_seed_airports:
        market, carriers, haul = HUBS[apt]
        rnd = random.Random("slotex:" + apt)          # deterministic per airport
        for _ in range(PER_HUB):
            carrier = rnd.choices(carriers, weights=[5] + [2] * (len(carriers) - 1))[0]
            longhaul = haul == "long" or (haul == "mix" and rnd.random() < 0.28)
            ac = rnd.choice(AC_LONG if longhaul else AC_SHORT)
            dest = rnd.choice([h for h in hubs if h != apt])
            out.append({
                "airport": apt, "market": market,
                "direction": rnd.choice(["arr", "dep"]),
                "carrier": carrier, "flight_no": str(rnd.randint(1, 3999)),
                "days": rnd.choice(DAY_PATTERNS),
                "time": weighted_time(rnd),
                "aircraft": ac, "seats": SEATS[ac],
                "orig_dest": dest, "service": "J",
                "window": rnd.choice(WINDOWS), "sim": 1,
            })
    return out


def main() -> None:
    cfg = yaml.safe_load(open("config/sources.yaml"))
    ss = sheets.open_sheet(cfg)

    registry = sheets.read_dataset(ss, "registry")
    reg = [{"iata": r["iata"], "city": r["city"], "country": r["country"],
            "region": r["region"], "level": str(r["current_level"]),
            "coordinator": r["coordinator_email"], "website": r["website"]}
           for r in registry if r.get("iata")]

    # Real Brazil, sampled.
    real = sheets.read_dataset(ss, "slots")
    by: dict[str, list] = {}
    for s in real:
        by.setdefault(s["airport"], []).append(s)
    brazil = []
    for apt, rows in by.items():
        for s in rows[:PER_BR_AIRPORT]:
            brazil.append({"airport": s["airport"], "market": "Brazil",
                           "direction": s["direction"], "carrier": s["carrier"],
                           "flight_no": s["flight_no"], "days": s["days"],
                           "time": s["slot_time"], "aircraft": s["aircraft"],
                           "seats": s["seats"], "orig_dest": s["orig_dest"],
                           "service": s["service"], "window": s["status"], "sim": 0})

    sim = []   # Europe is now shown as REAL capacity params (web/data/eu_capacity.json) — no simulation
    slots = brazil + sim

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "registry.json").write_text(json.dumps(reg, ensure_ascii=False))
    (OUT / "slots.json").write_text(json.dumps(slots, ensure_ascii=False))

    markets = {}
    for s in slots:
        markets[s["market"]] = markets.get(s["market"], 0) + 1
    print(f"registry: {len(reg)} airports")
    print(f"slots: {len(slots)}  (real Brazil {len(brazil)} + simulated {len(sim)})")
    print("by market:", markets)
    print("airports with listings:", len({s['airport'] for s in slots}))


if __name__ == "__main__":
    main()
