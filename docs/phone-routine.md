# Phone interaction (notify + approve/steer)

`/schedule` routines run **remotely in Anthropic's cloud** — they can't touch this
laptop, its venv, secrets, or `state/`. So the work stays on the laptop and the
routine is just a **doorbell**. Three parts:

| Part | Where | Role |
|---|---|---|
| `run.py` via local cron | Laptop | Worker: scrape → write Sheet → park risky changes in `_review` |
| `_review` tab in the Sheet | Cloud (your Drive) | Control surface — set a decision from the Sheets app on your phone |
| Remote `/schedule` routine | Cloud | Doorbell — reads `_review`, pings your phone when status is PENDING |

The loop: laptop parks a risky change as `PENDING` → routine pings you → you set the
status cell (SKIP / RETRY / APPLY / INVESTIGATE) from your phone → the laptop reads
those decisions on its next run and acts. The routine reads the Sheet as **you**
(your Google login) — no service account needed for the doorbell.

> Note: the laptop side of "act on decisions in `_review`" (reading the status
> column and applying/retrying) is not built yet — see WAYPOINT next actions. Until
> then the routine notifies and you act when back at the laptop.

## The routine (already created, DISABLED)

- **ID:** `trig_01WaXxTA5R7ktybDSDNGZboQ`
- **Manage:** https://claude.ai/code/routines/trig_01WaXxTA5R7ktybDSDNGZboQ
- **Schedule:** `30 11 * * *` = 07:30 America/New_York (EDT; 06:30 during EST)
- **Model:** claude-sonnet-4-6 · **MCP:** Google Drive · **Repo:** none

### Enable it (after the service account + first run.py write the Sheet)

1. Make sure the `database` Sheet exists with a `_review` tab (auto-created on first
   `run.py`) and is in your Drive `airport_slots` folder.
2. Test first with **Run now** (routine page → Run, or ask Claude Code to
   `RemoteTrigger run` it) — confirm it can read the Sheet via Google Drive.
3. If the read works, flip **enabled: true** (routine page toggle, or
   `RemoteTrigger update {enabled: true}`).

If the test run can't read the Sheet, the fix is a tool-permission tweak on the
Google Drive connector — adjust and re-run.
