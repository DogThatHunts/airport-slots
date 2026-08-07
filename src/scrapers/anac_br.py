"""ANAC Brazil — Slots Alocados (dataset: slots).

Best openly-licensed flight-level slot feed (CC BY-ND 3.0). Semicolon-delimited
CSV, updated daily, for Brazil's coordinated airports (CGH, GRU, PLU, REC, SDU).

Directory: .../Slots Alocados/{year}/{IATA}/{SEASON}/LIVE_{IATA}_{SEASON}.csv
Row 1 is a metadata timestamp; row 2 is the header.

The raw file is one row PER OPERATING DATE (e.g. CGH S26 ≈ 110k rows for ≈2.5k
distinct flights). We aggregate to the recurring-slot level: one row per
(direction, carrier, flight, time, aircraft, orig/dest, service), collapsing the
calendar dates into a days-of-week set + operating window. That matches what a
"slot" actually is and keeps the Sheet a manageable size.
"""
from __future__ import annotations

import csv
import io
import re

from .base import Scraper

BASE = ("https://sistemas.anac.gov.br/dadosabertos/"
        "Voos%20e%20opera%C3%A7%C3%B5es%20a%C3%A9reas/Slots%20Alocados/")
DIR_LINK_RE = re.compile(r'href="([^".?][^"]*)"')
DIRECTION = {"A": "arr", "D": "dep", "P": "dep"}
WEEKDAYS = {"1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu", "5": "Fri", "6": "Sat", "7": "Sun"}


class AnacBrScraper(Scraper):
    def _list(self, url: str) -> list[str]:
        return [x for x in DIR_LINK_RE.findall(self.get(url).text) if not x.startswith(".")]

    def _target_files(self) -> list[tuple[str, str, str]]:
        """Return (airport, season, url) for every configured airport/season present."""
        want_apt = {a.upper() for a in self.opts.get("airports", [])}
        want_season = {s.upper() for s in self.opts.get("seasons", [])}
        out = []
        for year in self._list(BASE):                      # e.g. "2026/"
            for apt in self._list(BASE + year):            # "CGH/"
                code = apt.strip("/").upper()
                if want_apt and code not in want_apt:
                    continue
                for season in self._list(BASE + year + apt):
                    scode = season.strip("/").upper()
                    if want_season and scode not in want_season:
                        continue
                    out.append((code, scode, f"{BASE}{year}{apt}{season}LIVE_{code}_{scode}.csv"))
        return out

    def fetch(self) -> list[dict]:
        rows: list[dict] = []
        for airport, season, url in self._target_files():
            try:
                content = self.get(url).content
            except Exception:
                continue  # LIVE file may not exist for every airport/season
            rows.extend(self._parse(content.decode("utf-8-sig"), airport, season))
        if not rows:
            raise RuntimeError("anac_br: no rows parsed — check airports/seasons in config opts")
        return rows

    def _parse(self, text: str, airport: str, season: str) -> list[dict]:
        lines = text.splitlines()
        if len(lines) < 2:
            return []
        reader = csv.DictReader(io.StringIO("\n".join(lines[1:])), delimiter=";")  # skip meta row
        agg: dict[tuple, dict] = {}
        for r in reader:
            op = (r.get("TipodeOperacao") or "").strip().upper()
            # Slot identity only — attributes (aircraft, orig/dest, days) are merged in.
            key = (op, r.get("CodEmpresaAerea"), r.get("NumerodoVoo"), r.get("HorariodoVoo"))
            g = agg.get(key)
            if g is None:
                g = agg[key] = {"days": set(), "ac": set(), "od": set(), "svc": set(),
                                "dmin": "9999", "dmax": "0000", "seats": 0}
            wd = (r.get("DiadaSemana") or "").strip()
            if wd in WEEKDAYS:
                g["days"].add(wd)
            for fld, k in (("Equipamento", "ac"), ("AeroportodeOrigemouDestino", "od"),
                           ("Tipodeserviço", "svc")):
                v = (r.get(fld) or "").strip()
                if v:
                    g[k].add(v)
            d = (r.get("DatadoVoo") or "").strip()
            if d:
                g["dmin"] = min(g["dmin"], d)
                g["dmax"] = max(g["dmax"], d)
            try:
                g["seats"] = max(g["seats"], int(r.get("Assento") or 0))
            except ValueError:
                pass

        out = []
        for (op, carrier, flight, time), g in agg.items():
            out.append({
                "airport": airport, "season": season,
                "direction": DIRECTION.get(op, op.lower()),
                "carrier": carrier, "flight_no": flight,
                "days": ",".join(WEEKDAYS[d] for d in sorted(g["days"])),
                "slot_time": time,
                "aircraft": "/".join(sorted(g["ac"])), "seats": g["seats"],
                "orig_dest": "/".join(sorted(g["od"])), "service": "/".join(sorted(g["svc"])),
                "status": f"{g['dmin']}..{g['dmax']}",   # operating window; changes flag as updates
            })
        return out
