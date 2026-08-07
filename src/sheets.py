"""Google Sheets I/O via a service account (headless-friendly).

Share the target Sheet with the service account's client_email as an Editor.
Each dataset (registry/slots) lives in its own worksheet.
"""
from __future__ import annotations

import os

import gspread
from google.oauth2.service_account import Credentials

from .schema import DATASETS, columns

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
KEY_PATH = os.environ.get("SLOTS_SA_KEY", "secrets/service_account.json")


def _client() -> gspread.Client:
    creds = Credentials.from_service_account_file(KEY_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def _sheet_id(cfg: dict) -> str:
    """Resolve the Sheet ID, kept OUT of version control.

    Order: env var SLOTS_SHEET_ID > gitignored secrets/sheet_id.txt > config value.
    """
    sid = os.environ.get("SLOTS_SHEET_ID")
    if not sid and os.path.exists("secrets/sheet_id.txt"):
        sid = open("secrets/sheet_id.txt").read().strip()
    return sid or cfg["sheet"].get("spreadsheet_id", "")


def open_sheet(cfg: dict) -> gspread.Spreadsheet:
    gc = _client()
    sid = _sheet_id(cfg)
    if sid:
        return gc.open_by_key(sid)
    return gc.open(cfg["sheet"]["spreadsheet_name"])


def _tab(ss: gspread.Spreadsheet, title: str, header: list[str]) -> gspread.Worksheet:
    try:
        ws = ss.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=title, rows=1000, cols=max(len(header), 12))
        ws.update([header], "A1")
    return ws


def read_dataset(ss: gspread.Spreadsheet, kind: str) -> list[dict]:
    ws = _tab(ss, DATASETS[kind]["tab"], columns(kind))
    return ws.get_all_records()


def write_dataset(ss: gspread.Spreadsheet, kind: str, rows: list[dict]) -> None:
    """Full-refresh a dataset tab (diff already decided this is safe)."""
    cols = columns(kind)
    ws = _tab(ss, DATASETS[kind]["tab"], cols)
    values = [cols] + [[r.get(c, "") for c in cols] for r in rows]
    ws.clear()
    ws.update(values, "A1")


def append_changelog(ss, cfg, entries: list[list]) -> None:
    ws = _tab(ss, cfg["sheet"]["worksheets"]["changelog"], ["ts", "source", "action", "detail"])
    if entries:
        ws.append_rows(entries, value_input_option="RAW")


REVIEW_HEADER = ["ts", "source", "reasons", "added", "updated", "removed",
                 "fingerprint", "status"]


def _review_ws(ss, cfg):
    ws = _tab(ss, cfg["sheet"]["worksheets"]["review"], REVIEW_HEADER)
    if ws.row_values(1) != REVIEW_HEADER:      # keep header current (e.g. after a schema bump)
        ws.update([REVIEW_HEADER], "A1")
    return ws


def write_review(ss, cfg, items: list[list]) -> None:
    """Append escalation rows (the doorbell routine + you read these)."""
    ws = _review_ws(ss, cfg)
    if items:
        ws.append_rows(items, value_input_option="RAW")


def read_review(ss, cfg) -> list[dict]:
    """Return review rows as dicts with their 1-based sheet row number (`_row`)."""
    ws = _review_ws(ss, cfg)
    out = []
    for i, rec in enumerate(ws.get_all_records(), start=2):   # row 1 = header
        rec["_row"] = i
        out.append(rec)
    return out


def set_review_status(ss, cfg, row: int, status: str) -> None:
    col = REVIEW_HEADER.index("status") + 1
    _review_ws(ss, cfg).update_cell(row, col, status)


def write_meta(ss, cfg, rows: list[list]) -> None:
    ws = _tab(ss, cfg["sheet"]["worksheets"]["meta"], ["ts", "source", "rows", "health"])
    if rows:
        ws.append_rows(rows, value_input_option="RAW")
