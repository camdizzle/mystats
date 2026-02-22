# MyStats Tilt Mode Guide (Streamer-Friendly + Technical)

Welcome to your **Tilt hype hub**. This guide explains how Tilt tracking, the dashboard, and OBS overlays work together.

---

## What Tilt tracking gives you

MyStats turns Tilt sessions into a full stream workflow:

- **Live run status** (current level, elapsed time, current top tiltee).
- **Run leaderboard tracking** (leader + standings for the active run).
- **Run, daily, and lifetime expertise progression** updates.
- **Level completion + run completion recap payloads** for overlays.
- **Dashboard + OBS overlay views** served from the local MyStats web server.
- **Chat-ready narrative/milestone outputs** while Tilt is active.

---

## Dashboard + Overlay: what each one does

### Dashboard (Web)
The dashboard is your operator view. It is served by the built-in Flask server and loads at:

- `http://127.0.0.1:<overlay_server_port>/dashboard`

Use it to:

- Monitor Tilt KPIs and totals.
- Watch leaderboard pressure and placement changes.
- Check MyCycle / Season Quests / Tilt in one web UI.

### Overlay (OBS)
The Tilt overlay is viewer-facing and should be added as an OBS Browser Source.

- Tilt overlay URL: `http://127.0.0.1:<overlay_server_port>/overlay/tilt`
- Main overlay URL: `http://127.0.0.1:<overlay_server_port>/overlay`

Use it to:

- Show current run context and top-tiltee spotlight.
- Surface live standings.
- Display level/run recap cards.

**Best practice:** dashboard on a side monitor, overlay in your OBS scene.

---

## Exact connection steps (Dashboard + OBS)

1. Start **MyStats**.
2. Open **Settings → Overlay** and confirm **Server Port** (default is typically `5000`).
3. Verify in a browser:
   - Dashboard: `http://127.0.0.1:<port>/dashboard`
   - Tilt overlay page: `http://127.0.0.1:<port>/overlay/tilt`
4. In OBS, add **Browser Source**.
5. Paste one of these as the URL:
   - `http://127.0.0.1:<port>/overlay/tilt` (Tilt scene)
   - `http://127.0.0.1:<port>/overlay` (main race overlay)
6. If you change the port, restart MyStats and update OBS source URLs.

**Quick diagnostics**
- If overlay shows errors: open `http://127.0.0.1:<port>/api/overlay/tilt` and confirm JSON loads.
- If dashboard is blank: open `http://127.0.0.1:<port>/api/dashboard/main` and confirm JSON loads.
- If either page returns Not Found: confirm your install still includes `obs_overlay/` and `modern_dashboard/` assets.

---

## Tilt expertise formulas (technical users)

Below is the code-level behavior used during Tilt processing.

### 1) Per-level earned expertise

For each processed level:

- `survivors = count(players at current level with points > 0)`
- `earned_xp = floor(survivors * multiplier(level))`

Multiplier schedule:

- Levels 1–14: `1/3`
- 15–17: `6`
- 18–20: `7`
- 21–23: `12`
- 24–26: `13.5`
- 27–29: `50`
- 30–32: `66`
- 33–35: `84`
- 36–38: `104`
- 39–41: `126`
- 42+: `135 + 9 * floor((level - 42) / 3)`

### 2) Run expertise

- `run_xp_new = run_xp_prev + earned_xp`

### 3) Daily expertise

- `total_xp_today_new = total_xp_today_prev + earned_xp`

### 4) Lifetime expertise anchor + increment

MyStats combines a synced baseline and live session progress:

- `adjusted_total_xp = parsed_total_xp_from_level_state + lifetime_base_xp`
- `lifetime_expertise_working = max(previous_lifetime_expertise, adjusted_total_xp)`
- `lifetime_expertise_new = lifetime_expertise_working + earned_xp`

This is why startup baseline sync matters: it prevents stale local totals from being used as the long-term anchor.

---

## Other Tilt scoring shown in dashboard (pressure)

The Tilt leaderboard pressure score (dashboard highlight sorting) uses:

- `deaths = max(0, tilt_levels - tilt_top_tiltee)`
- `pressure = (tilt_points * 1.5) + (tilt_top_tiltee * 25) - (deaths * 8)`

This is separate from expertise, and is meant to rank “impact” in live standings.

---

## Coverage check: does this guide now match what Tilt is doing?

Yes—this guide now maps to the major Tilt systems currently in the codebase:

- Local web routes for dashboard and overlays.
- API endpoints those pages poll.
- Per-level/run/daily/lifetime expertise update logic.
- Pressure-score dashboard ranking logic.
- Operational setup steps for dashboard and OBS URL wiring.

If additional Tilt mechanics are added later (new milestone triggers, new formulas, or payload fields), this guide should be updated in the same release.

---

## TL;DR

- Use `http://127.0.0.1:<port>/dashboard` for operator monitoring.
- Use `http://127.0.0.1:<port>/overlay/tilt` as your OBS Tilt Browser Source.
- Expertise is survivor-count × level multiplier, accumulated into run/daily/lifetime totals.
- Pressure score is separate and used for dashboard ranking emphasis.
