#!/usr/bin/env python3
"""Export a static data snapshot for the demo web app (web/data/*.json).

Reads the live Sheet and writes compact JSON. Slots are stratified-sampled per
airport so the static page stays small/fast. Re-run to refresh the snapshot.

    python scripts/export_web_data.py [--per-airport N]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import sheets  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "web" / "data"
PER_AIRPORT = 400
if "--per-airport" in sys.argv:
    PER_AIRPORT = int(sys.argv[sys.argv.index("--per-airport") + 1])


def main() -> None:
    cfg = yaml.safe_load(open("config/sources.yaml"))
    ss = sheets.open_sheet(cfg)

    registry = sheets.read_dataset(ss, "registry")
    reg = [{"iata": r["iata"], "city": r["city"], "country": r["country"],
            "region": r["region"], "level": r["current_level"],
            "coordinator": r["coordinator_email"], "website": r["website"]}
           for r in registry if r.get("iata")]

    slots = sheets.read_dataset(ss, "slots")
    by_airport: dict[str, list] = {}
    for s in slots:
        by_airport.setdefault(s["airport"], []).append(s)
    sample = []
    for apt, rows in by_airport.items():
        for s in rows[:PER_AIRPORT]:
            sample.append({"airport": s["airport"], "direction": s["direction"],
                           "carrier": s["carrier"], "flight_no": s["flight_no"],
                           "time": s["slot_time"], "days": s["days"],
                           "aircraft": s["aircraft"], "seats": s["seats"],
                           "orig_dest": s["orig_dest"], "service": s["service"],
                           "window": s["status"]})

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "registry.json").write_text(json.dumps(reg, ensure_ascii=False))
    (OUT / "slots.json").write_text(json.dumps(sample, ensure_ascii=False))
    reg_by = {r["iata"] for r in reg}
    print(f"registry: {len(reg)} airports  |  slots: {len(sample)} sampled "
          f"(from {len(slots)}) across {len(by_airport)} airports")
    print("slot airports covered by registry:",
          sum(1 for a in by_airport if a in reg_by), "/", len(by_airport))


if __name__ == "__main__":
    main()
