# MyStats Tilt Mode Guide (Streamer-Friendly + Technical)

Welcome to your **Tilt hub**. This guide explains Tilt tracking, dashboard usage, OBS overlay setup, in-app Tilt commands, and the technical formulas.

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

## In-app Tilt chat commands (`!` commands)

These are the Tilt-related commands users run in chat.

### `!mytilts [username]`
**What it does**
- Shows Tilt points/deaths today and season totals for the caller or optional target username.
- Also reports the last passed level.

**Sample output**
```text
PlayerA Stats | Today: 2,450 pts, 3 deaths | Season: 41,220 pts, 58 deaths | Last Passed: Level 27
```

### `!xp`
**What it does**
- Shows expertise values tracked by the app:
  - last level XP
  - last run XP
  - today XP
  - season XP

**Sample output**
```text
Expertise Stats | Last Level XP: 156 | Last Run XP: 2,142 | Today's XP: 5,220 | Season XP: 184,320
```

### `!toptiltees`
**What it does**
- Shows top users by top-tiltee finishes (up to top 10).
- Tie-breaker uses season tilt points.

**Sample output**
```text
Top Tiltees: (1) PlayerA 22 tops, 41,220 points, (2) PlayerB 18 tops, 36,100 points, (3) PlayerC 15 tops, 29,880 points.
```

### `!top10tiltees`
**What it does**
- Shows top 10 users by total Tilt points.

**Sample output**
```text
Top 10 Tilees by Tilt Points: (1) PlayerA 41,220 points, (2) PlayerB 36,100 points, (3) PlayerC 29,880 points.
```

### `!tiltsurvivors`
**What it does**
- Shows best Tilt survival rates (lowest death rate) among users who meet a minimum levels-participated threshold.
- Minimum level threshold is configurable by settings (`tiltsurvivors_min_levels`, fallback `tiltdeath_min_levels`).

**Sample output**
```text
Top 10 Best Tilt Survival Rate (min 20 levels): (1) PlayerA 4 deaths, 92.0% survive, (2) PlayerB 6 deaths, 88.5% survive.
```

### `!top10xp`
**What it does**
- Shows top 10 from the TiltedExpertise leaderboard (Pixel by Pixel source), after refreshing lifetime XP baseline.

**Sample output**
```text
🏆 TOP 10 TiltedExpertise 🏆
🥇 1. PlayerA - 184,320
🥈 2. PlayerB - 173,940
🥉 3. PlayerC - 169,102
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
- Tilt chat commands: `!mytilts`, `!xp`, `!toptiltees`, `!top10tiltees`, `!tiltsurvivors`, `!top10xp`
- Expertise = survivor-count × level multiplier, accumulated into run/day/lifetime totals.
