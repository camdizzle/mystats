# Overlay Quick Summary (User Digest)

## What overlays are available?

MyStats currently has **one primary overlay URL**:

- **`/overlay`** → single smart overlay endpoint for:
  - race overlay view
  - BR overlay view
  - tilt overlay view

The app automatically mode-switches based on live activity (`race`, `br`, `tilt`).

Legacy path behavior:

- **`/overlay/tilt`** now shows a message only:
  - `for tilt overlay, use /overlay instead. Tilt overlay will appear after first completed level.`

---

## How do I access overlays in OBS?

1. Start MyStats.
2. Open **Settings → Overlay** and confirm **Server Port** (default `5000`).
3. In OBS add a Browser Source with:
   - `http://127.0.0.1:<port>/overlay`
4. Keep this single source in your scene.
5. MyStats will switch the rendered overlay mode automatically:
   - Race/BR data → main overlay cards
   - Tilt run context → tilt tracker/recap overlay

---

## What is contained in the overlay?

### Race/BR mode (`/overlay` rendering `index.html`)
- Title + rotating today/season stat pills
- Multi-view top 10 boards (season/today/race-only/br-only)
- Previous race top-3 presentation
- World-record callout panel
- Event popup panel (raid/cycle/quest/player-alert events)
- Optional horizontal ticker layout mode

### Tilt mode (`/overlay` rendering `tilt.html`)
- Live run tracker pills (top tiltee, level, elapsed)
- Combined standings feed:
  - season top 10
  - today top 10
  - current/last run standings
  - run stat rows
- Level-complete recap overlay
- Run-complete recap overlay
- Tilt splash timing + recap gating logic to avoid stale replay

---

## How do I change overlay settings?

All overlay settings are changed in the desktop app at:

- **Settings → Overlay**

### Main overlay settings
- Stats rotation speed
- Data refresh interval
- Server port
- Theme
- Card opacity
- Text scale
- Medal visibility
- Compact row spacing
- Horizontal ticker layout

### Tilt-specific settings
- Tilt theme
- Starting lifetime XP
- Season best level baseline
- Personal best level baseline
- Scroll step (px)
- Scroll tick interval (ms)
- Edge pause (ms)

Defaults (current):
- port `5000`
- refresh `3s`
- rotation `10s`
- theme `midnight`
- opacity `84`
- text scale `100`

---

## Single-API / single-endpoint architecture status

Already in place:

- Unified data API: **`/api/overlay`**
  - includes active mode + race payload + tilt payload
- Unified presentation URL: **`/overlay`**
  - now chooses rendered UI based on active mode server-side

This gives one stable OBS URL while preserving race/BR/tilt mode switching.
