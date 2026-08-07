"""IATA WASG Annex 12.7 — global coordinated-airport registry (dataset: registry).

Downloads the Excel workbook IATA publishes of every Level 2/3 airport with its
coordination level per season and coordinator contacts. This is the database
backbone, not per-flight slot allocations.

Robustness notes (from source recon):
- The direct XLSX URL contains a content-hash that IATA rotates on republish, so
  we resolve the current href from the landing page first, falling back to the
  configured/last-known URL.
- ~10 preamble rows precede the header; the header row is detected dynamically.
- Trailing rows carry SUM formulas — filtered by requiring a valid IATA code.
- Season columns (e.g. NW25 / NS26 / NW26) shift each cycle — detected by pattern.
"""
from __future__ import annotations

import io
import re

import openpyxl
from bs4 import BeautifulSoup

from .base import Scraper

LANDING = "https://www.iata.org/en/programs/ops-infra/slots/coordinated-airports/"
FALLBACK_XLSX = ("https://www.iata.org/contentassets/"
                 "4ede2aabfcc14a55919e468054d714fe/wasg-annex-12.7.xlsx")
SEASON_RE = re.compile(r"\bN[SW]\d{2}\b", re.I)   # "NW25 Level" -> NW25
CODE_RE = re.compile(r"^[A-Z]{3,4}$")


def _cell(row, j) -> str:
    if j is None or j >= len(row) or row[j] is None:
        return ""
    return str(row[j]).strip()


class IataWasgScraper(Scraper):
    def _resolve_xlsx_url(self) -> str:
        try:
            html = self.get(LANDING).text
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "annex-12.7" in href.lower() and href.lower().endswith(".xlsx"):
                    return href if href.startswith("http") else "https://www.iata.org" + href
        except Exception:
            pass
        return self.url or FALLBACK_XLSX

    def fetch(self) -> list[dict]:
        url = self._resolve_xlsx_url()
        content = self.get(url).content
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        rows = [list(r) for r in wb.active.iter_rows(values_only=True)]

        hdr_idx = None
        for i, r in enumerate(rows):
            vals = [str(c).strip().lower() if c is not None else "" for c in r]
            if "region" in vals and any("airport code" in v for v in vals):
                hdr_idx = i
                break
        if hdr_idx is None:
            raise RuntimeError("iata_wasg: header row not found — WASG layout may have changed")

        headers = [str(c).strip() if c is not None else "" for c in rows[hdr_idx]]

        def find(*needles) -> int | None:
            for j, h in enumerate(headers):
                hl = h.lower()
                if any(n in hl for n in needles):
                    return j
            return None

        col = {
            "region": find("region"), "country": find("country"), "city": find("city"),
            "code": find("airport code", "airport"), "email": find("email", "scr", "sma"),
            "portal": find("portal"), "website": find("website"), "notes": find("notes"),
        }
        # Season columns are headed like "NW25 Level"; capture the season code token.
        season_cols = []
        for j, h in enumerate(headers):
            m = SEASON_RE.search(h)
            if m:
                season_cols.append((j, m.group(0).upper()))
        # "current" season = the middle one when three are present, else the last.
        cur_season = season_cols[len(season_cols) // 2][1] if season_cols else ""

        out = []
        for r in rows[hdr_idx + 1:]:
            code = _cell(r, col["code"])
            if not CODE_RE.match(code):
                continue
            levels = {name: _cell(r, j) for j, name in season_cols}
            out.append({
                "region": _cell(r, col["region"]),
                "country": _cell(r, col["country"]),
                "city": _cell(r, col["city"]),
                "iata": code,
                "current_season": cur_season,
                "current_level": levels.get(cur_season, ""),
                "levels": ";".join(f"{k}:{v}" for k, v in levels.items() if v),
                "coordinator_email": _cell(r, col["email"]),
                "portal": _cell(r, col["portal"]),
                "website": _cell(r, col["website"]),
                "notes": _cell(r, col["notes"]),
            })
        if not out:
            raise RuntimeError("iata_wasg: parsed 0 airport rows — layout may have changed")
        return out
