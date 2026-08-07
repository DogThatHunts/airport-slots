# Airport Landing Slots Database

Autonomous pipeline that scrapes airport slot data, writes it to a Google Sheet,
and escalates anything risky to your phone for approval.

## Architecture (hybrid)

```
Laptop (scheduled daily)                         Your phone
────────────────────────                         ──────────
run.py  ── scrape (IATA WASG, ...)
        ── normalize  ─┐
        ── diff vs Sheet │  low risk ─► write to Sheet + _changelog
                         │  high risk ─► _review tab + state/last_run.json
                                                  │
   Claude Code routine (reads summary) ── push ─► "0 rows from WASG. Skip / retry / investigate?"
                                                  ◄── you reply, routine acts
```

- **Laptop does the work.** `run.py` is a plain Python pipeline; a local cron job
  (or a Claude Code routine wrapping it) runs it daily.
- **Low-risk changes auto-apply.** Big deletions, schema drift, empty scrapes, or
  large diffs get parked in the `_review` tab and flagged as `needs_attention`.
- **A Claude Code routine bridges to your phone.** It reads `state/last_run.json`,
  and when something needs attention it push-notifies you and lets you steer.
- **Model routing.** LLM-assisted steps (`src/models.py`) default to the **cheap
  tier (Haiku)**; only ambiguous parses/anomaly summaries use a stronger model.

## Layout

| Path | Role |
|---|---|
| `run.py` | Entrypoint for cron / routine |
| `config/sources.yaml` | Sources, Sheet target, risk thresholds |
| `src/scrapers/` | One module per source (`iata_wasg.py` first) |
| `src/normalize.py` | Raw records → canonical slot schema |
| `src/diff.py` | Compare scrape vs Sheet, classify risk |
| `src/sheets.py` | Service-account read/write |
| `src/pipeline.py` | Orchestration: scrape→diff→apply/escalate |
| `src/models.py` | Tiered model routing (cheap by default) |
| `secrets/` | Service-account key (gitignored) |
| `state/` | Last-run summary + idempotency |

---

## Setup

### 1. Python

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Google service account (headless Sheet access)

1. Go to <https://console.cloud.google.com> → create/select a project.
2. **APIs & Services → Library** → enable **Google Sheets API** (and **Google Drive API**).
3. **APIs & Services → Credentials → Create credentials → Service account.**
   Name it e.g. `slots-bot`, click through (no roles needed), Create.
4. Open the service account → **Keys → Add key → Create new key → JSON.**
   A JSON file downloads.
5. Move it here:
   ```bash
   mkdir -p secrets && mv ~/Downloads/<that-file>.json secrets/service_account.json
   ```
6. Copy the service account's `client_email` from that JSON (looks like
   `slots-bot@<project>.iam.gserviceaccount.com`).
7. Open your **`Drive/airport_slots/database`** Sheet → **Share** → paste that
   `client_email` → give it **Editor** → Send.
8. Put the Sheet ID in `config/sources.yaml` (`sheet.spreadsheet_id`). It's the
   long string in the Sheet URL: `.../spreadsheets/d/<THIS>/edit`.

> Env var alternative for the key path: `export SLOTS_SA_KEY=/abs/path.json`

### 3. Anthropic key (for model-routed steps)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 4. First run

```bash
python run.py            # today the WASG scraper is a stub → escalates cleanly
python run.py --summary  # what the phone routine will read
```

---

## Autonomy: schedule it

Local daily cron (leanest):

```bash
# crontab -e  — 07:00 daily
0 7 * * * cd /Users/edward/Projects/airport_slots && ./.venv/bin/python run.py >> state/cron.log 2>&1
```

Or drive it from a **Claude Code routine** (recommended, since it can reason about
anomalies and notify your phone) — see `docs/phone-routine.md`.

## Status

- [x] Repo scaffold, pipeline, diff/risk engine, Sheets I/O, model routing
- [ ] Service account created + Sheet shared (**your step 2 above**)
- [ ] `iata_wasg` scraper implemented (waiting on source-recon workflow results)
- [ ] Phone routine wired up
