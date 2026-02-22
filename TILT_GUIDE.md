# MyStats Tilt Mode Guide (Streamer-Friendly + Technical)

Welcome to your **Tilt hub**. This guide explains Tilt tracking, dashboard usage, OBS overlay setup, and the technical formulas.

---

## What Tilt tracking gives you

MyStats provides:

- **Live run status** (level, elapsed time, top tiltee).
- **Run leaderboard tracking** (leader + standings for current run).
- **Run, daily, and lifetime expertise progression** updates.
- **Level completion + run completion recap payloads** for overlays.
- **Dashboard + OBS overlay views** from the local MyStats web server.

---

## Dashboard + Overlay: what each one does

### Dashboard (Web)
Use the dashboard as your operator/control view:

- URL: `http://127.0.0.1:<overlay_server_port>/dashboard`

### Overlay (OBS)
Use the overlays as viewer-facing Browser Sources in OBS:

- Tilt overlay URL: `http://127.0.0.1:<overlay_server_port>/overlay/tilt`
- Main overlay URL: `http://127.0.0.1:<overlay_server_port>/overlay`

---

## Exact connection steps (Dashboard + OBS)

1. Start **MyStats**.
2. Open **Settings → Overlay**.
3. Confirm **Server Port** (default is usually `5000`).
4. Open in a browser to verify:
   - Dashboard: `http://127.0.0.1:<port>/dashboard`
   - Tilt overlay page: `http://127.0.0.1:<port>/overlay/tilt`
5. In OBS, add a **Browser Source**.
6. Use one of these URLs:
   - `http://127.0.0.1:<port>/overlay/tilt` (Tilt scene)
   - `http://127.0.0.1:<port>/overlay` (main race scene)
7. If port changes, restart MyStats and update OBS Browser Source URLs.

---

## Tilt commands (API + verification)

Use these commands from a terminal for diagnostics and integrations.

### 1) Fetch current Tilt overlay payload

**Command**
```bash
curl -s http://127.0.0.1:<port>/api/overlay/tilt
```

**What it does**
- Returns the active Tilt overlay JSON used by `/overlay/tilt`.

**Sample payload (trimmed)**
```json
{
  "updated_at": "2026-02-22T14:35:01",
  "title": "MyStats Tilt Run Tracker",
  "settings": {
    "theme": "midnight"
  },
  "current_run": {
    "run_id": "d6f6c3f1-...",
    "run_short_id": "d6f6c3",
    "status": "active",
    "level": 23,
    "elapsed_time": "11:42",
    "top_tiltee": "PlayerA",
    "top_tiltee_count": 3,
    "run_points": 1280,
    "run_xp": 2142,
    "best_run_xp_today": 3010,
    "total_xp_today": 5220,
    "total_deaths_today": 17,
    "lifetime_expertise": 184320,
    "leader": { "name": "PlayerA", "points": 620 },
    "standings": [
      { "name": "PlayerA", "points": 620 },
      { "name": "PlayerB", "points": 510 }
    ]
  },
  "last_run": {},
  "level_completion": {},
  "run_completion": {},
  "run_completion_event_id": 14,
  "suppress_initial_recaps": true
}
```

### 2) Fetch dashboard payload (includes Tilt section)

**Command**
```bash
curl -s http://127.0.0.1:<port>/api/dashboard/main
```

**What it does**
- Returns full dashboard JSON for MyCycle, Season Quests, Rivals, and Tilt.

**Sample payload (Tilt-relevant subset)**
```json
{
  "tilt": {
    "totals": {
      "tilt_levels": 412,
      "tilt_top_tiltee": 156,
      "tilt_points": 82390
    },
    "deaths_today": 17,
    "participants": 42
  }
}
```

### 3) Fetch only Tilt section from dashboard payload

**Command**
```bash
curl -s http://127.0.0.1:<port>/api/dashboard/main | jq '.tilt'
```

**What it does**
- Extracts only the Tilt object for scripts/alerts.

**Sample payload**
```json
{
  "totals": {
    "tilt_levels": 412,
    "tilt_top_tiltee": 156,
    "tilt_points": 82390
  },
  "deaths_today": 17,
  "participants": 42
}
```

### 4) HTTP health check for Tilt overlay endpoint

**Command**
```bash
curl -I http://127.0.0.1:<port>/overlay/tilt
```

**What it does**
- Verifies the Tilt overlay page is being served.

**Sample response**
```text
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
```

---

## Tilt expertise formulas (technical users)

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

- `adjusted_total_xp = parsed_total_xp_from_level_state + lifetime_base_xp`
- `lifetime_expertise_working = max(previous_lifetime_expertise, adjusted_total_xp)`
- `lifetime_expertise_new = lifetime_expertise_working + earned_xp`

---

## Other Tilt scoring shown in dashboard (pressure)

The dashboard pressure score uses:

- `deaths = max(0, tilt_levels - tilt_top_tiltee)`
- `pressure = (tilt_points * 1.5) + (tilt_top_tiltee * 25) - (deaths * 8)`

Pressure is a ranking/highlight metric and is separate from expertise.

---

## TL;DR

- Dashboard: `http://127.0.0.1:<port>/dashboard`
- OBS Tilt Browser Source: `http://127.0.0.1:<port>/overlay/tilt`
- Tilt API payload: `http://127.0.0.1:<port>/api/overlay/tilt`
- Expertise = survivor-count × level multiplier, accumulated into run/day/lifetime totals.
