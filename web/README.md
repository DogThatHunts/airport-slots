# SlotEx — demo web app

A **mock** airport landing-slot marketplace built from the `airport_slots`
pipeline data. Static, no build step (vanilla HTML/CSS/JS).

- `index.html` / `styles.css` / `app.js` — the app
- `data/registry.json` — airports (IATA WASG: Level, coordinator)
- `data/slots.json` — sampled slot listings (ANAC Brasil open data)

> ⚠️ Demo only — no real slots are traded; prices are simulated.

## Local preview

The page `fetch`es the JSON, so serve it (don't open via `file://`):

```bash
cd web && python -m http.server 8777   # then open http://localhost:8777
```

## Refresh the data snapshot

From the repo root, with the pipeline's venv and Sheet access configured:

```bash
python scripts/export_web_data.py --per-airport 400
```

## Deploy

Pushed to `main`, `.github/workflows/pages.yml` publishes this `web/` folder to
GitHub Pages automatically.

Data sources: IATA WASG Annex 12.7 (coordinated-airport registry) and ANAC Brasil
"Slots Alocados" (CC BY-ND 3.0). Public sources; attribution retained.
