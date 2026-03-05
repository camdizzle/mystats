# Overlay State Review (Current Repository Snapshot)

## 1) Overlay surfaces and routes

- The Flask server runs on `0.0.0.0` using `overlay_server_port` from `settings.txt` (default `5000`).
- OBS/Browser routes:
  - Main overlay page: `/overlay`
  - Tilt overlay page: `/overlay/tilt`
  - Overlay static assets: `/overlay/<path:filename>`
- Overlay APIs:
  - `/api/overlay/settings` (settings payload)
  - `/api/overlay/top3` (race/BR leaderboard payload)
  - `/api/overlay/tilt` (tilt payload)
  - `/api/overlay` (unified payload with active mode + race + tilt blocks)
- Overlay files are resolved from packaged (`_MEIPASS`) and local `obs_overlay` candidates.

## 2) Main results overlay (race/BR) architecture

### Markup and presentation layers
- `obs_overlay/index.html` contains:
  - title
  - six rotating header pills (today vs season KPIs)
  - leaderboard shell
  - splash screen
  - world record overlay
  - event overlay
- `obs_overlay/overlay.js` drives:
  - polling `/api/overlay`
  - mode-aware view selection (race vs BR)
  - timed top-3 and event queue presentation
  - world-record celebration timing
  - auto-scroll and horizontal layout behavior
  - translation/language rendering
- `obs_overlay/styles.css` defines:
  - theme variables and text scaling
  - card/pill/leaderboard styling
  - splash animation keyframes
  - top-3 card mode visuals
  - dedicated event and world-record overlay styles
  - compact rows + responsive breakpoints
  - horizontal ticker layout styles

### Data model exposed to the main overlay
- `_build_overlay_top3_payload()` provides:
  - multi-view leaderboards (`season`, `today`, race-only, BR-only, optional previous race)
  - `recent_race_top3` details (`race_key`, `race_type`, record indicators)
  - `header_stats` (avg points, unique racers, total races, today and season)
  - `settings`
  - `overlay_events` (rolling event log)

## 3) Tilt overlay architecture

### Markup and presentation layers
- `obs_overlay/tilt.html` contains:
  - tracker card with status pills and standings feed
  - last run summary section
  - tilt splash screen
  - level-complete recap overlay
  - run-complete recap overlay
- `obs_overlay/tilt_overlay.js` drives:
  - polling unified `/api/overlay`
  - automatic redirect to `/overlay` when mode is not tilt
  - theme + text scaling + scroll tuning
  - standings rendering (season, today, current/last run)
  - recap state machine (level then run recap gating)
  - run completion event-id tracking to prevent stale recap replay
  - snapshot caching in localStorage for startup resilience
- `obs_overlay/tilt_styles.css` defines:
  - full tracker visuals
  - standings typography/layout
  - level/run recap overlay visual systems
  - overlay pills/metrics/hero blocks
  - splash visuals and recap/tracker visibility modes

### Data model exposed to tilt overlay
- `_build_tilt_overlay_payload()` includes:
  - `current_run`, `last_run`
  - `level_completion`, `run_completion`
  - `run_completion_event_id`
  - `season_standings`, `today_standings`
  - `settings` (with tilt theme override)
  - `suppress_initial_recaps` safeguard

## 4) Configuration setup for overlays

### Settings persisted by desktop app
Results overlay:
- `overlay_rotation_seconds`
- `overlay_refresh_seconds`
- `overlay_server_port`
- `overlay_theme`
- `overlay_card_opacity`
- `overlay_text_scale`
- `overlay_show_medals`
- `overlay_compact_rows`
- `overlay_horizontal_layout`

Tilt overlay specific:
- `tilt_lifetime_base_xp`
- `tilt_season_best_level`
- `tilt_personal_best_level`
- `tilt_overlay_theme`
- `tilt_scroll_step_px`
- `tilt_scroll_interval_ms`
- `tilt_scroll_pause_ms`

### Default values (current)
- rotation `10s`, refresh `3s`, port `5000`
- theme `midnight`, opacity `84`, text scale `100`
- medals on, compact rows off, horizontal off
- tilt theme `midnight`
- tilt scroll step `1px`, tick `40ms`, edge pause `900ms`

### Runtime mode switching
- Overlay mode is driven by active data stream:
  - Tilt monitor sets mode `tilt`
  - Race monitor sets mode `race`
  - BR monitor sets mode `br`
- If a tilt run is active (`tilt_current_run_id`), mode resolves to tilt.

## 5) Styling system summary (all overlays)

- Both overlays use CSS custom properties populated by JS from server settings:
  - text color/accent variables
  - panel alpha from `card_opacity`
  - global `--text-scale`
- Shared theme family: `midnight`, `ocean`, `sunset`, `forest`, `mono`, `violethearts`.
- Main overlay has two layout modes:
  - standard card layout
  - ultra-wide horizontal ticker layout (optimized for 1080x100 style scenes)
- Tilt overlay styling emphasizes:
  - large scrollable standings cards
  - dedicated celebratory recap overlays (level/run)
  - explicit recap-vs-tracker state visibility controls

## 6) Event-related overlay behavior and changes summary

### Current event pipeline behavior
- Event source:
  - runtime code calls `enqueue_overlay_event(type, message)`
- Event storage:
  - in-memory/transient config JSON list, capped to last 40 events
  - monotonically increasing `overlay_event_counter` ids
- Event delivery:
  - race/BR payload exposes `overlay_events`
  - `overlay.js` hydrates once, then only enqueues events with new ids
- Event presentation:
  - queued event overlays are shown one at a time (`eventOverlayDurationMs`)
  - event overlays and top-3 overlays are sequenced to avoid collision
  - event overlays are disabled in horizontal layout mode

### Event types currently pushed into overlay queue
- Competitive raid events:
  - `raid_queue_open`
  - `raid_cancelled`
  - `raid_live_started`
  - `raid_summary`
- Performance/progression events:
  - `player_alert`
  - `cycle_completed`
  - `quest_completed`

### Tilt recap event gating changes (current state)
- Tilt run recap uses `run_completion_event_id` with baseline memory to prevent stale recap flash/repeat on load.
- A pending run-completion event is preserved while level recap is active and displayed afterward.
- Recap overlays are force-hidden at startup before first payload hydration.

### Documented higher-level overlay change trend
- Release notes describe a shift to a built-in Flask-served overlay system with stronger state/timing reliability, enhanced horizontal support, and recap stability.
- Post-major PR summary highlights ongoing improvements to splash sequencing, race-end transitions, readability, and stale/duplicate recap suppression.
