# Data sources — by dataset and by airport

Where every figure in the project comes from and how it's obtained. The app is
**all-real data** (only prices and "trading" are mock). See also
`docs/research-real-data.md` for the landscape analysis.

## By dataset

| Dataset | Coverage | Source | How it's obtained | Script → file | Refresh | License |
|---|---|---|---|---|---|---|
| **Airport registry** | ~400 coordinated airports (global) | IATA WASG Annex 12.7 (XLSX) | Download XLSX, skip preamble, auto-detect header + season columns, parse | `src/scrapers/iata_wasg.py` → Sheet `airports` → `web/data/registry.json` | Weekly | IATA © (free) |
| **Brazil slots** (real allocations) | CGH, GRU, REC, SDU (PLU has no LIVE files) | ANAC "Slots Alocados" open data | Crawl the ANAC directory index, download `LIVE_{apt}_{season}.csv` (`;`-delimited), aggregate per-date rows → recurring slots | `src/scrapers/anac_br.py` → Sheet `slots` → sampled to `web/data/slots.json` (`scripts/build_web_dataset.py`) | Daily | CC BY-ND 3.0 |
| **US East Coast schedules** (real; slot-demand surrogate) | 19 airports (see below) | BTS On-Time Performance (monthly PREZIP) | Download monthly zip, stream CSV, filter to targets, collapse to recurring slots (days-of-week set) | `scripts/fetch_bts_eastcoast.py` → `web/data/slots_bts.json` | Monthly (latest 2026-05; ~2-mo lag) | Public domain |
| **FAA slot holdings** (real) | DCA, JFK, LGA | FAA "Holder Totals" PDFs (latest season auto-detected) | Scrape PDF links, download, `pdftotext -layout`, parse per-carrier rows | `scripts/fetch_faa_holdings.py` → `web/data/faa_holdings.json` | Per IATA season (auto-upgrades) | Public domain |
| **EWR operating cap** (real) | EWR | FAA Order — Fed. Reg. 2025-18871 (docket FAA-2008-0221) | Curated constant (72/hr = 36+36, through 2026-10-24) | `scripts/fetch_faa_holdings.py` `ewr_cap()` | On FAA amendment | Public domain |
| **EU declared capacity** (real parameters) | 15 hubs (see below) | Coordinators' published capacity declarations | Curated from a cited research pass (several read via `pdftotext`) | `web/data/eu_capacity.json` | Manual, per season | Per source (mostly public) |

## US East Coast (BTS) — target airports

PWM, BOS, BDL, JFK, LGA, EWR, PHL, BWI, DCA, IAD, CLT, RDU, CHS, ATL, SAV, MIA, MCO, FLL, TPA.
All flights to/from these in the BTS month are kept; the ~200 most-frequent recurring
slots per airport are sampled for the web snapshot. These are **scheduled operations**
(a demand surrogate), not slot allocations — only DCA/JFK/LGA are truly slot-controlled.

## EU declared capacity — by airport

| Airport | Coordinator | Peak (mvts/hr) | Source | Confidence |
|---|---|---|---|---|
| LHR | ACL (UK) | 46 arr / 45 dep | [ACL S26 appendices](https://www.acl-uk.org/wp-content/uploads/2025/10/S26-Declaration-Appendices-RSL1.pdf) | High (primary) |
| LGW | ACL (UK) | 57 | [ACL S26](https://www.acl-uk.org/wp-content/uploads/2025/10/Gatwick-Summer-2026-Declaration-Appendices.pdf) | High (primary) |
| STN | ACL (UK) | 50 | [ACL S26](https://www.acl-uk.org/wp-content/uploads/2025/10/London-Stansted-Airport-S26-Capacity-Declaration.pdf) | High (primary) |
| MAN | ACL (UK) | 61 | [ACL S26](https://www.acl-uk.org/wp-content/uploads/2025/10/MAN-S26-Capacity-Declaration-3.pdf) | High (primary) |
| DUB | ACL / IAA | 57 | [IAA S26 decision](https://www.iaa.ie/docs/default-source/publications/corporate-publications/economic-regulation/final-decision-on-summer-2026-coordination-parameters-at-dublin-airport.pdf) | High (primary) |
| CDG | COHOR (FR) | 73 arr / 78 dep | [COHOR CDG](https://www.cohor.org/en/airports/paris-charles-de-gaulle-airport-cdg-lfpg/) | High (primary) |
| ORY | COHOR (FR) | ~40 | [COHOR ORY](https://www.cohor.org/en/airports/paris-orly-airport-ory-lfpo/) | Med-high (primary rule) |
| FRA | Fluko (DE) | 106 (mixed) | [Fluko params](https://fluko.org/wp-content/uploads/2026/04/20260423-Airport-Capacity-Parameters_W26_L3.pdf) | High (primary) |
| MUC | Fluko (DE) | 90 (mixed) | [Fluko params](https://fluko.org/wp-content/uploads/2026/04/20260423-Airport-Capacity-Parameters_W26_L3.pdf) | High (primary) |
| MAD | AECFA / DGAC (ES) | 52 | [DGAC S26 resolution](https://www.transportes.gob.es/recursos_mfom/comodin/recursos/resolucion_dgac_s26_vi.pdf) | High (primary) |
| BCN | AECFA / DGAC (ES) | 40 | [DGAC S26 resolution](https://www.transportes.gob.es/recursos_mfom/comodin/recursos/resolucion_dgac_s26_vi.pdf) | High (primary) |
| ZRH | Slot Coord. Switzerland | 66 | [SCS ZRH](https://www.slotcoordination.ch/airport-information/zurich-zrhlszh/airport-capacities-zurich.html/106) | High (season undated) |
| VIE | Slot Coord. Austria | 68 | [SCA VIE](https://www.slots-austria.com/airports/vienna_airport) | High (primary) |
| AMS | ACNL (NL) | 110 (dep-peak) / 106 (arr-peak) | [ACNL S26 declaration](https://slotcoordination.nl/wp-content/uploads/2025/10/AMS-Capacity-Declaration-Summer-2026.pdf) | High (primary, via pdftotext) |
| LIS | NAV Portugal | ~38 (26 arr / 26 dep) | [Portugal Post 2025](https://theportugalpost.com/posts/lisbon-targets-45-flights-an-hour-as-airport-overhaul-looms) · [MIT ICAT-2020-09](https://dspace.mit.edu/bitstream/handle/1721.1/132655/ICAT-2020-09_Slot%20Allocation%20Process.pdf?sequence=1) | **Medium — secondary** (no open S26 primary) |
| FCO | Assoclearance (IT) | — omitted — | [Assoclearance FCO](https://www.assoclearance.it/en/coordination/coordinated-airports/FCO/) (parameters login-gated) | N/A (not public) |

### Notes on the hard cases
- **AMS** — the coordinator PDF's web-fetch text was garbled, but `pdftotext -layout` on the downloaded file read the tables cleanly (Appendix I/II). Real primary data.
- **LIS** — no open S26 primary declaration; the coordinator page (`slots.nav.pt`) is a JS page-builder blob. The ~38/hr ceiling is corroborated by 2025 reporting + a MIT/ICAT study (S14/S15 granular split). Flagged "secondary" in the UI.
- **FCO** — Assoclearance publishes FCO's "Coordination Parameters" only in its login-gated area; no reputable public source states the hourly figure. Omitted rather than guessed. To obtain: request from Assoclearance (coordinamento@assoclearance.it) or an authenticated account.
