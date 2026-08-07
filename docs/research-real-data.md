# Research: getting REAL 2026 slot (or slot-surrogate) data

_Compiled 2026-08-07 from four parallel research passes. Sources at the bottom._

## TL;DR

| Region / airport | Real slot allocations? | What's actually obtainable (2026) | Open & free? |
|---|---|---|---|
| **DCA / JFK / LGA** (US Level 3) | ✅ yes | FAA "Holder/Operator" PDFs — but **only S25 posted so far**; S26/W26 not yet published (poll for it) | ✅ free, PDF-only |
| **EWR** (US Level 2 + FAA cap) | ⚠️ caps only | Real hourly cap **72/hr (36 arr + 36 dep) through Oct 24 2026** in FAA orders; per-carrier cuts are prose, not data | ✅ free, PDF/prose |
| **Other US East Coast** (BOS, PHL, BWI, CLT, ATL, MIA, MCO, FLL, RDU) | ❌ uncontrolled (Level 1) | No allocations exist. Use **BTS scheduled flights** as a demand surrogate | ✅ free (BTS) |
| **Europe** (LHR, CDG, FRA, AMS…) | ✅ exists but gated | Per-carrier allocations only via **e-airportslots.aero** (registration-gated) or ACL commercial license. Free tier = capacity/parameters only | ❌ gated / paid |
| **Gate availability** (anywhere) | — | Proprietary; **not obtainable as open data**. Do not build on it | ❌ |

**Bottom line:** For the US East Coast, the realistic *real 2026* path is **BTS flight schedules as a slot-demand surrogate** (free, flight-level, every airport) + FAA slot PDFs for the 3 Level-3 airports + the real EWR cap number. For Europe, real per-carrier allocations require a **registered e-airportslots.aero account** (airline/agent); otherwise only capacity parameters are free.

---

## 1. US East Coast

- **Real slot allocations exist only at DCA, JFK, LGA** (the 3 US Level-3 airports). FAA publishes 4 PDF reports per airport/season (Holder Totals/Details, Operator Totals/Details — "holder" = owns the slot, "operator" = flies it). PDF only; filename conventions vary by season (scrape links, don't construct).
  - **2026 not yet posted:** as of 2026-08-07 the newest season live is **S25**; S26/W26 filenames 404. Publication lags the schedule-submission deadline; poll the data page + archive for the S26 drop.
- **EWR** is IATA **Level 2** (schedule-facilitated), *plus* a binding FAA operating cap layered on in 2025 due to construction + ATC staffing: **72 ops/hr (36+36), extended through Oct 24 2026** (Federal Register orders under docket **FAA-2008-0221**). Caps are real and citable; per-carrier reductions are narrative prose, not a table.
- **US Level 2 list** = ORD, LAX, EWR, SFO (+ MCO seasonal). **US Level 3** = JFK, LGA, DCA. Everything else on the East Coast (BOS, PHL, BWI, CLT, ATL, MIA, FLL, RDU) is **Level 1 / uncontrolled** — no allocations to publish.
- **Real-data path for the uncontrolled majority: BTS** (see §4).

## 2. Europe

- **No European coordinator publishes open per-carrier slot allocations.** Free material is "upstream" only: capacity declarations, coordination parameters, local rules, start-of-season reports, statistics (PDF/XLSX) — real for S26/W26 but not allocations.
- **Real allocations (S26/W26)** live in **e-airportslots.aero** (the shared EUACA portal aggregating COHOR/Fluko/ACNL/Spain/Austria/… ) as CSV + IATA SIR/SSIM, nightly refresh — but **registration-gated** (apply; each coordinator grants read access airport-by-airport; intended for airlines/agents).
- **UK/ACL** runs its own system; allocations are a **commercial licensed product** (price on request). Free tier = capacity declarations + parameters.
- **Only open per-flight allocation dataset globally = Brazil ANAC** (already in this project). Edinburgh DataShare has a **synthetic** slot dataset for benchmarking.

## 3. "Schedule-facilitated" (IATA Level 2) — what it is

- **Level 1** = uncontrolled. **Level 2** = *schedules facilitated*: a **facilitator advises/negotiates** voluntary schedule adjustments to stay within capacity. **Level 3** = *coordinated*: a **coordinator allocates enforceable slots** (historic precedence, series, use-it-or-lose-it).
- **Key fact:** "No slots are allocated at a Level 2 airport. Historic precedence and series of slots do not apply." Level 2 uses **SMA (Schedule Movement Advice)**; Level 3 uses **SCR (Slot Clearance Request)**. Level 2 carriers hold **no enforceable slot** — only advisory agreed times.
- **Published Level-2 data** = capacity/coordination parameters (human-readable PDF), submission notices, contacts. The transactional SMA/SCR layer is machine-readable SSIM but exchanged **bilaterally, not published**.
- **EWR** is the instructive hybrid: nominally Level 2, but with a binding FAA cap that behaves like a Level-3 limit *without* conferring slot property rights. Per-carrier approved movements are conveyed privately.
- **Verdict:** Level-2 published data is useful for **capacity/congestion context**, not as a per-flight slot registry.

## 4. Gate availability vs. schedules as a slot surrogate

- **Gate data is proprietary and not open.** It lives in airport Gate Management Systems (ProDIGIQ, Amadeus/SITA common-use) over secured channels; gate *rights* (exclusive/preferential/common-use) are in lease agreements (policy, not a live feed). Any "gate availability" from open sources is *inferred* from flight timings — an estimate, not ground truth. **Slots are runway access, not gate access.** → Don't build on gate data.
- **Scheduled flights = the right surrogate, and it's free (US):**
  - **BTS Reporting-Carrier On-Time Performance** — every reported flight, flight-level: tail, flight no, **CRS (scheduled) dep/arr times**, origin, dest, actuals, delays. Bin by airport × time to reconstruct **slot demand per runway hour**. CSV/Excel via TranStats. **2026-current** (latest ~May 2026), ~2-month lag, public domain. Caveat: only carriers ≥0.5% of domestic revenue must report (misses small/regional/pure-cargo).
  - **BTS T-100 segment** — monthly route volumes/seats (no intraday timing) — good volume cross-check.
  - **FAA ASPM "called rates"** — the best free stand-in for **declared capacity** at the 77 busiest airports. Pair BTS demand ÷ ASPM capacity = a real **slot-pressure** metric.
  - **OAG / Cirium** — comprehensive incl. *forward* schedules, but enterprise-priced (no public pricing). Only needed for forward-looking or non-US/small-carrier completeness.

---

## Recommendations for SlotEx

1. **Real US East Coast layer (recommended):** build listings from **BTS On-Time** for any US airport (BOS, ATL, MIA, CLT, BWI, RDU, PHL…), labeled clearly as *real scheduled operations (demand surrogate)* — distinct from both "allocations" and the "simulated" hubs. Optionally overlay **ASPM called rates** to show demand-vs-capacity (slot pressure). This is the honest way to give the East Coast real 2026 data.
2. **DCA/JFK/LGA:** keep the FAA holder PDFs; add an S26 poller so it upgrades from S25 automatically when FAA posts it.
3. **EWR:** replace the simulated panel's framing with the **real FAA cap** (72/hr = 36+36, through Oct 24 2026) as a capacity fact, keeping any per-carrier split clearly simulated.
4. **Europe real allocations:** only via a **registered e-airportslots.aero account** (manual/credentialed) or ACL commercial license — a business/credential decision, not a scrape. Until then, EU stays simulated (or show free capacity parameters).
5. **Gate data:** drop the idea — not obtainable.

## Sources

- FAA slot data: https://www.faa.gov/about/office_org/headquarters_offices/ato/service_units/systemops/perf_analysis/slot_administration/data — archive: https://www.faa.gov/headquartersoffices/ato/slot-administration-data-archive
- FAA Level 2 list: https://www.faa.gov/about/office_org/headquarters_offices/ato/service_units/systemops/perf_analysis/slot_administration/slot_administration_schedule_facilitation/level-2-airports
- EWR order (Sep 29 2025, 72/hr through Oct 24 2026): https://www.federalregister.gov/documents/2025/09/29/2025-18871/operating-limitations-at-newark-liberty-international-airport — docket FAA-2008-0221
- IATA WASG program: https://www.iata.org/en/programs/ops-infra/slots/slot-guidelines/
- e-airportslots.aero (EUACA portal): https://e-airportslots.aero/ — EUACA: https://www.euaca.org/
- ACL latest airport info: https://www.acl-uk.org/latest-airport-info/ · COHOR: https://www.cohor.org/en/rules/ · ACNL transparency: https://slotcoordination.nl/about-acnl/transparency/
- Brazil ANAC open slots: https://www.gov.br/anac/pt-br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/slots-alocados
- BTS On-Time: https://www.transtats.bts.gov/ontime/ · fields: https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ · T-100: https://www.transtats.bts.gov/DatabaseInfo.asp?QO_VQ=EGD
- FAA ASPM: https://www.aspm.faa.gov/aspmhelp/index/Aviation_System_Performance_Metrics_(ASPM).html · FAA data: https://www.faa.gov/data
