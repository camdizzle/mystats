# MyStats — All-in-One User Guide (Current State)

This README is the single quick-reference guide for using **MyStats** in its current state, including setup, daily use, and the major feature systems:

- General MyStats use
- MyCycle
- MyTeams
- Rivals
- Season Quests
- Tilt
- Events
- Event Management
- Overlays
- Dashboards

---

## 1) General MyStats use

### What MyStats does
MyStats is a local companion app for Marbles on Stream creators that tracks race, BR, and Tilt data, drives chat commands, and powers browser-based overlays and dashboards.

### First-time setup checklist
1. Launch MyStats.
2. Open **Settings** and configure your channel/account.
3. If using your own account connection, use the app link/connect flow in the top-right of the app.
4. If you get token/auth startup errors, close the app, delete `token.json`, then restart and reconnect.
5. If you use the default account mode, make sure `mystats_results` is a moderator in your Twitch chat.

### Core runtime behavior
- MyStats reads and processes your local output/stat files continuously.
- MyStats runs a built-in local Flask server for:
  - OBS overlays
  - Modern web dashboard
  - JSON API endpoints used by those pages

### Overlay + dashboard server basics
- Default server URL pattern: `http://127.0.0.1:<overlay_server_port>/...`
- Default port is typically `5000` unless changed in **Settings → Overlay**.
- After changing server port, restart MyStats and update any OBS/browser links.

### 2-PC streaming setup
If OBS runs on a separate streaming PC, use the gaming PC local IP instead of localhost:

`http://<your_local_ip>:<overlay_server_port>/overlay`

Also allow the chosen port in Windows Defender Firewall inbound TCP rules.

---

## 2) MyCycle

MyCycle tracks repeated session progression loops for racers and exposes both personal and leaderboard-style summaries.

### What users get
- Personal cycle progress and completion tracking via `!mycycle`
- Cycle performance summary metrics via `!cyclestats`
- Chat event announcements when users complete cycles

### Key chat commands
- `!mycycle [username]`
  - Shows session name, completed cycle count, current cycle progress, and missing placements (if any).
- `!cyclestats`
  - Shows fastest/slowest cycle performance and rotating aggregate metrics.

### Typical use on stream
- Let viewers check their own grind progress with `!mycycle`.
- Use `!cyclestats` to spotlight consistency and completion speed.
- Keep MyCycle enabled as a recurring progression objective during longer sessions.

---

## 3) MyTeams

MyTeams is MyStats' local, channel-scoped team competition system.

### Core concept
- Viewers create/join teams.
- Teams compete on daily/weekly/season points.
- Captains/co-captains manage recruiting and membership.
- Teams can activate temporary point bonuses (Bits and TEP systems).

### Streamer setup path
Open **Settings → MyTeams** and configure:
- Enable/disable MyTeams commands
- Points counting mode (`active` or `season`)
- Max team size
- TEP values (threshold, per-race gain, bonus %, cooldown, caps)
- Bits bonus threshold/duration/weights

### Most-used chat commands
- Discovery: `!teamhelp`, `!tcommands`
- Create/join: `!createteam`, `!invite`, `!acceptteam`, `!denyteam`, `!join`, `!leave`
- Management: `!cocaptain`, `!kick`, `!recruiting on|off`, `!renameteam`, `!logo`, `!inactive`
- Status/boards: `!myteam`, `!teambonus`, `!dailyteams`, `!weeklyteams`

### Roles
- **Captain**: full team control
- **Co-captain**: invite/kick/recruiting/logo/inactivity management
- **Member**: join/leave/status actions

### Bonus system summary
- **Bits track**: team bits bank can trigger weighted bonus tiers.
- **TEP track** (Team Effort Points): participation-driven bank can trigger configured bonus windows.
- Only one bonus window can be active at a time.

---

## 4) Rivals

Rivals identifies close competitors using season performance similarity and allows direct head-to-head checks.

### What it does
- Detects likely rival matchups based on configurable qualification rules.
- Supports user-level rival lookups and direct pair comparisons.
- Surfaces rivalry data in both chat and dashboard views.

### Key chat commands
- `!rivals`
  - Global or user-targeted rivalry output depending on arguments.
- `!h2h <user1> <user2>`
  - Direct side-by-side comparison with leader and gap summary.

### Typical stream use
- Call out “closest race” narratives during leaderboard swings.
- Use `!h2h` for on-demand matchup storylines between top grinders.

---

## 5) Season Quests

Season Quests provide long-form progression goals that users can track and complete over time.

### What users see
- Personal quest progress summaries via `!myquests`.
- Completion announcements in chat when thresholds are reached.

### Key chat command
- `!myquests`
  - Displays completed quest count and progress toward tracked objectives (for example races, points, and Tilt-related goals).

### Event behavior
When a quest completes, MyStats can emit a completion line in chat using the `🎯 Season Quest Complete` style message.

---

## 6) Tilt

Tilt is a dedicated MyStats mode for run-based progression, survival tracking, expertise accumulation, and Tilt-specific leaderboards.

### What Tilt includes
- Current run monitoring (level, elapsed time, leader, and top tiltee context)
- Run/day/season Tilt points and death tracking
- Tilt expertise progression and leaderboard output
- Dashboard and overlay support for stream-facing visualization

### Key Tilt commands
- `!mytilts [username]` — run/today/season Tilt stats and last completed level
- `!thisrun` — active (or last) run snapshot
- `!xp` — expertise totals (last level/run, today, season, lifetime)
- `!toptiltees`, `!top10tiltees`, `!tiltsurvivors`, `!top10xp` — Tilt leaderboard commands

### Tilt views
- Dashboard: `http://127.0.0.1:<overlay_server_port>/dashboard`
- Tilt overlay: `http://127.0.0.1:<overlay_server_port>/overlay/tilt`

---

## 7) Events

MyStats emits automatic chat events for major milestones and run outcomes.

### Common automated event categories
- Marble day reset notifications
- Checkpoint winner summaries
- Race milestone celebrations
- Winner/narrative alerts for race momentum
- BR winner announcements (including crown variants)
- Tilt level recap and run completion messages
- MyCycle completion announcements
- Season quest completion announcements
- Competitive raid queue/live/cancel/summary status messages

### Why these matter
These system-generated events reduce manual moderation overhead and keep chat informed with consistent, structured updates.

---

## 8) Event Management

MyStats also includes **Event Management** capabilities that are separate from automated chat/overlay event triggers. This area is focused on running structured competitions and managing standings across organized event formats.

### In-app Event Management (MyStats desktop app)
Within MyStats, event management workflows include functionality similar to local leaderboard management, including:
- Creating events
- Activating/deactivating events
- Managing event state during live operations
- Coordinating leaderboard-oriented event tracking locally

### Web platform integration
For expanded event operations, MyStats integrates with the web interface at:
- https://mystats.camwow.tv

The web experience provides robust tools for advanced organizers, including support for:
- Event management workflows
- Leaderboard management
- Multi-streamer events
- Multi-event seasons
- Additional platform features for larger structured competitions

### Partnership note
If you are planning an event, we want to partner with you early so MyStats can deliver the setup, tracking, and output behavior your event needs. Reach out ahead of time so we can align configuration and coverage before launch.

---

## 9) Overlays

MyStats serves OBS-ready overlays from its built-in local Flask server so you can add them as Browser Sources without managing manual text files.

### Overlay URLs
- Unified overlay (Race/BR/Tilt auto-rotation):
  - `http://127.0.0.1:<overlay_server_port>/overlay`
- Tilt-focused overlay:
  - `http://127.0.0.1:<overlay_server_port>/overlay/tilt`

### OBS setup quickstart
1. Start MyStats.
2. Open **Settings → Overlay** and confirm the **Server Port**.
3. In OBS, add a **Browser Source**.
4. Paste one of the overlay URLs above.
5. If you change the server port, restart MyStats and update OBS URLs.

### Overlay behavior summary
- Overlay pages poll local API endpoints and auto-refresh data.
- Overlay visual options (such as theme/text/spacing/rotation choices) are controlled from **Settings → Overlay**.
- If using a 2-PC setup, replace `127.0.0.1` with your gaming-PC local IP.

### Overlay troubleshooting
- If an overlay page returns **Not Found**, confirm your install includes the `obs_overlay` folder.
- If an overlay on another PC cannot connect, confirm firewall inbound TCP rule for the selected port.

---

## 10) Dashboards

MyStats includes web dashboards served from the local Flask server for monitoring live state and presenting stream-ready information.

### Modern Dashboard
- URL: `http://127.0.0.1:<overlay_server_port>/dashboard`
- Intended for live monitoring and scene/operator prep.
- Pulls data from API endpoints such as `/api/dashboard/main`.

### Dashboard quickstart
1. Start MyStats.
2. Confirm **Settings → Overlay → Server Port**.
3. Open `http://127.0.0.1:<overlay_server_port>/dashboard`.
4. If data appears stale/missing, verify API output directly in browser.

---

## 11) Command families at a glance

Depending on your enabled modules/settings, commonly used command groups include:

- General/profile: `!info`, `!mystats`, `!commands`
- Leaderboards: `!top10season`, `!top10today`, `!top10wins`, `!top10races`, `!top10ppr`, etc.
- Tilt: `!mytilts`, `!xp`, `!toptiltees`, `!top10tiltees`, `!tiltsurvivors`, `!top10xp`, `!thisrun`
- Rivals: `!rivals`, `!h2h`
- MyCycle: `!mycycle`, `!cyclestats`
- Season Quests: `!myquests`
- MyTeams: `!teamhelp`, `!tcommands`, `!myteam`, `!teambonus`, and team-management commands

---

## 12) Troubleshooting quick list

- **Auth/token errors at startup**
  - Delete `token.json`, restart MyStats, reconnect account.
- **Overlay page shows Not Found**
  - Confirm installation includes `obs_overlay` folder and verify server port.
- **Dashboard missing data**
  - Open `/api/dashboard/main` and verify JSON is returned.
- **MyTeams commands do nothing**
  - Enable MyTeams in **Settings → MyTeams**.
- **Cannot join/accept team invite**
  - Check invite validity, team capacity, and current team membership state.

---

## 13) Current-state note

This README summarizes the current implemented feature behavior for MyStats as an all-in-one operational guide. If future releases expand commands or settings, update this file so streamers/mods always have a single reliable reference.
