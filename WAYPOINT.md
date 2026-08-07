# Waypoint — Airport Landing Slots Database

_Last updated: 2026-08-07_

A running checkpoint of decisions, state, and next steps so any session (or you on
your phone) can pick up without re-deriving context.

## Goal

Autonomous pipeline that scrapes airport landing-slot data → writes a Google Sheet,
running mostly on this laptop, with AFK approve/steer from the phone.

## Decisions locked

| Topic | Decision |
|---|---|
| Architecture | **Hybrid** — laptop pipeline does the work; Claude Code routine bridges to phone |
| Data source | Web scraping public sources; **first target: IATA WASG Level 3/2 registry** |
| Sheets access | **Service account + gspread** (headless) |
| Cadence | **Scheduled daily** (local cron and/or routine) |
| Phone interaction | **Notify + approve/steer** (skip / retry / apply-anyway / investigate) |
| Model routing | Cheap tier = **Claude Haiku**; escalate anomalies to Sonnet |
| Target Sheet | `Drive/airport_slots/database` (blank, ready) |

## Design in one line

Scrape → normalize → diff vs Sheet → **auto-apply low-risk / escalate high-risk to phone.**
Risk = empty scrape, >5% deletions, >30% churn, or scraper exception.

## Key finding (recon workflow `witi4uqr7`) — TWO data tiers

- **Tier A — airport registry (backbone):** WASG Annex 12.7 XLSX. Global, free,
  no auth, ~400 airports, Level 2/3 per season + coordinator email/portal/website.
  **This is the only openly machine-readable GLOBAL source.**
- **Tier B — actual per-flight slot allocations:** openly available for only a few
  regions — **Brazil/ANAC (daily CSV, best), Hong Kong (historical text), FAA
  DCA/JFK/LGA (PDF)**. Everywhere else is commercial (ACL, OAG) or restricted
  (Eurocontrol). Fill in source-by-source; the 127 coordinator emails from the
  WASG file are the expansion leads.

Datasets defined in `src/schema.py` (`registry`, `slots`) → separate Sheet tabs
(`airports`, `slots`).

## Current state

- [x] Repo scaffolded, git initialized
- [x] Pipeline, risk/diff engine, Sheets I/O, model routing, entrypoint
- [x] Two-tier dataset architecture (`registry` + `slots`)
- [x] **`iata_wasg` scraper implemented + verified against LIVE data**
      (402 airports; NS26 = 216 L3 + 178 L2, matches IATA fact sheet; idempotent diff)
- [x] **`anac_br` (Brazil allocations) implemented + verified live** — aggregates
      per-date rows to recurring slots (CGH S26: 110k dated rows → 2,569 slots,
      zero key collisions, idempotent). Enabled in config.
- [x] README (service-account guide) + `docs/phone-routine.md`
- [x] Sheet ID configured (kept out of VCS — `secrets/sheet_id.txt` / `SLOTS_SHEET_ID`)
- [x] Phone "doorbell" routine created via `/schedule` (DISABLED) —
      `trig_01WaXxTA5R7ktybDSDNGZboQ`, reads `_review` tab via Google Drive
- [x] Service account created + Sheet shared (`slots-bot@airport-landing-slots…`)
- [x] **First real end-to-end run OK (2026-08-07):** airports=402, slots=16,703,
      nothing escalated. Tabs airports/slots/_meta/_changelog/_review all live.
- [x] **Doorbell test run PASSED (2026-08-07)** — returned "✅ All clear" reading
      the empty `_review` tab via Google Drive. Phone path verified end-to-end.
- [ ] **Enable the routine when ready** (user deferred) —
      `RemoteTrigger update trig_01WaXxTA5R7ktybDSDNGZboQ {enabled:true}`.
      Google Drive tool permissions are fine as-is (Read/Grep allowed_tools didn't block it).
- [x] **Laptop acts on phone decisions (DONE)** — `_review.status` APPLY/SKIP/RETRY
      honored next run; changes fingerprinted so stale decisions are ignored.
      Unit-tested (7 cases) + live review round-trip. `src/pipeline.py::_resolve` +
      `src/diff.py::fingerprint`.
- [x] **Demo web app (DONE)** — `web/` static "SlotEx" slot-trading marketplace
      (vanilla JS, no build). Snapshot via `scripts/export_web_data.py`
      (402 airports + 1,600 sampled slots → `web/data/*.json`). Served locally OK.
      Data expansion (HK/FAA, more sources) PARKED per user.
- [x] **Published (DONE)** — public repo https://github.com/DogThatHunts/airport-slots
      → live at **https://dogthathunts.github.io/airport-slots/** via Actions
      (`.github/workflows/pages.yml` deploys `web/`). Sheet ID scrubbed from VCS
      (moved to gitignored `secrets/sheet_id.txt`; `sheets._sheet_id()` resolves
      env `SLOTS_SHEET_ID` > secrets file > config). Auto-redeploys on push to main.
- [x] **SlotEx v2 (DONE)** — favicon (`scripts/make_favicon.py` → light-blue plane
      `web/favicon.ico`); brand palette reference `brand/colors.css`; tidied
      coordinator email/website display; fixed level-as-number bug (L3 badge/stat/
      price now correct). Expanded via `scripts/build_web_dataset.py`: real Brazil
      + SIMULATED US/EU Level-3 hubs (35 airports, 3,790 listings, market-grouped
      dropdown, SIM badges). Real Sheet/pipeline stay real-only.
- [x] **FAA real holdings view (DONE)** — `scripts/fetch_faa_holdings.py` parses the
      real FAA "Holder Totals" PDFs (DCA/JFK/LGA, S25) via pdftotext →
      `web/data/faa_holdings.json` (DCA 892 slots/9 holders, JFK 1497/93, LGA 1141/12,
      Summer 2025). Separate "FAA slot holdings [REAL]" tab in SlotEx with per-carrier
      bars; deep-link `?view=faa`. FAA WAF needs a plain browser UA (bot UA 403s).
      **EWR added as SIMULATED** (Newark is schedule-facilitated/Level 2, not
      slot-controlled → no real holdings exist; United-dominated sim, muted bars +
      SIMULATED badge to separate from the real three). `scripts/fetch_faa_holdings.py`
      `sim_ewr()`.
- [x] SlotEx demo checkpointed as "good enough" (user, 2026-08-07).
- [x] **Research (DONE) → `docs/research-real-data.md`.** Key findings: real US slot
      allocations exist ONLY for DCA/JFK/LGA (FAA PDFs; 2026/S26 not posted yet, only
      S25). EWR = Level 2 + real FAA cap 72/hr (36+36) through Oct 24 2026 (Federal
      Register, docket FAA-2008-0221). All other East Coast airports are uncontrolled
      (Level 1). Europe: no OPEN per-carrier allocations — real ones are gated behind
      **e-airportslots.aero** (registration) or ACL commercial license; free tier =
      capacity params only. **Gate data = proprietary, not usable.** Best real US
      surrogate = **BTS On-Time scheduled flights** (free, flight-level, every airport,
      2026-current) + **FAA ASPM called rates** for declared capacity (slot-pressure).
      Recommended next: a BTS-based real US East Coast layer; swap EWR to the real cap.
- [x] **Real US East Coast layer (DONE)** — `scripts/fetch_bts_eastcoast.py` pulls
      BTS On-Time Performance (latest month, 2026-05), filters 19 East Coast airports
      (PWM/BOS/BDL/JFK/LGA/EWR/PHL/BWI/DCA/IAD/CLT/RDU/CHS/ATL/SAV/MIA/MCO/FLL/TPA),
      collapses to recurring slots (~3,800 real listings) → `web/data/slots_bts.json`.
      App loads + merges them (SCHED badge, "US East Coast (real schedules)" group).
      US hubs removed from the simulator (`build_web_dataset.py` now EU-only sim).
- [x] **EWR → real FAA cap (DONE)** — FAA view shows the real operating cap 72/hr
      (36+36) through 2026-10-24 (Fed. Reg. 2025-18871) instead of simulated holdings.
- [x] **FAA auto-season poller (DONE)** — `fetch_faa_holdings.py` auto-detects the
      latest posted HOLDER_TOTALS season per airport (S25 now; auto-upgrades to S26).
- [ ] Local cron worker (deferred)
- [ ] Enable doorbell routine when ready
- [ ] PARKED: Hong Kong / FAA tiers

## Slot-modeling decision (important)

ANAC publishes one row PER OPERATING DATE. We aggregate to the **recurring-slot**
level: identity = (airport, season, direction, carrier, flight_no, slot_time);
days-of-week, aircraft, seats, orig/dest, service, and the operating-date window
are merged attributes (tracked for changes). This is why `days` is in `sig`, not
`key`, in `src/schema.py`. Keeps the Sheet ~25k rows instead of ~1M.

## Next actions

1. **User:** create service account, share Sheet, paste Sheet ID into `config/sources.yaml`.
2. **Then:** `python run.py` — populates the `airports` tab with 402 rows, exercises
   the full apply/escalate path for real.
3. Create the `/schedule` routine (draft in `docs/phone-routine.md`).
4. Decide allocations scope → implement `anac_br.fetch()` (Brazil), then HK/FAA.

## Verified scrapes (2026-08-07, live)

- **Registry (WASG):** 402 airports, season NS26, level split {3: 216, 2: 178,
  blank: 8} — matches IATA fact sheet. 127 unique coordinator emails.
- **Slots (ANAC Brazil):** 16,703 recurring slots, zero key collisions —
  CGH S26 2569 / W26 1311, GRU S26 8334 / W26 1815, REC S26 1532, SDU S26 793 /
  W26 349. (PLU currently returns no LIVE files → skipped gracefully.)
- **Scale/perf:** ~17k total rows (fine for a Sheet). Brazil daily pull ≈ 80 MB /
  ~3 min wall — acceptable for a daily cron. WASG pull is instant.

## Key paths

- Entry: `run.py` (`--summary` prints last run; exit 2 = needs attention)
- Config: `config/sources.yaml`
- Escalation state: `state/last_run.json` → surfaced in Sheet `_review` tab
- Recon workflow script: `.../workflows/scripts/wasg-source-recon-wf_8f17f772-f0b.js`

## Open questions / parking lot

- Which coordinators after WASG (EU vs APAC ordering)?
- Add a non-Claude cheap tier (OpenAI/Gemini/Ollama) later? Currently Haiku-only.
- Notify-always vs. notify-only-on-attention for the routine.
