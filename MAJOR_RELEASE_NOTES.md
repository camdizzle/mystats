# MyStats Major Release Notes 

## Platform, App Runtime, and Reliability

- Added a built-in local Flask service as a first-class part of the app so overlays and dashboards are served directly from MyStats endpoints.
- Improved startup/runtime reliability around threaded logging, Flask integration, and UI-safe log piping.
- Improved Twitch auth resilience by handling invalid/expired token scenarios with fallback behavior instead of hard-failing app startup.
- Added In-Place updater including download progress UX, install flow updates, and safer “Later” behavior limits. No more download/full reinstalls.
- Added minimize-to-tray behavior with tray menu controls so the app can keep running cleanly in the background.

## Overlay System (OBS Browser Source)

- Evolved the race overlay into a robust rotating presentation with:
  - Better section transitions and splash sequencing.
  - Stable continuous auto-scroll behavior across refreshes.
  - More reliable top-3 podium / race-end transitions.
  - Improved timing gates so race-complete and previous-race states render at the right moments.
- Added/expanded horizontal overlay support and tuned dimensions/typography so it is usable in stream layouts.
- Added richer theme customization (including new theme variants) and readability passes for pills, labels, spacing, and text scale.
- Added world-record celebration behavior and visual highlighting for standout race outcomes.
- Consolidated numerous “style-only” iterations into a cleaner, more legible overlay UX while retaining core data visibility.
- http://127.0.0.1:5000/overlay

## Tilt Overlay and Tilt Run Recap Experience

- Added a dedicated Tilt overlay endpoint and made tilt overlay modes (tracker, level recap, run recap) significantly more reliable.
- Improved overlay state handling so stale recap screens do not flash on startup and active-run transitions are correctly gated.
- Added continuous standings auto-scroll and stronger state persistence across refresh cycles.
- Refined completion overlays (run complete / level complete) with better layout hierarchy, stat presentation, and consistent pill formatting.
- http://127.0.0.1:5000/overlay/tilt

## Dashboards and Analytics Surface

- Introduced and expanded the modern browser dashboard model for race, tilt, rivals, and season-focused views.
- Added a Race dashboard with filters and leaderboard-focused monitoring views.
- Added a Tilt dashboard with leaderboard/death/survivability metrics and improved KPI accuracy.
- Added a Rivals dashboard and then refactored it toward head-to-head metrics for clearer competition tracking.
- Added a Season Quest dashboard path and integrated payload targets for seasonal progress workflows.
- Improved dashboard density, navigation naming, and table readability to better support stream/operator workflows.
- http://127.0.0.1:5000/dashboard

## Commands and Chat Features

- Added new tilt-focused chat capabilities including `!tiltdeath`, `!xp`, and improved `!top10xp` behavior.
- Added/updated tilt summary outputs like `!mytilts` and corrected command naming consistency (`!top10tiltees`).
- Updated command availability logic so key commands (for example head-to-head scenarios) remain usable even when certain modules are disabled.
- Added setting controls for chat behavior, including suppressing offline tilt chat messages.

## Settings and Configuration UX

- Expanded and reorganized settings UX:
  - Dedicated Tilt settings tab.
  - Better button visibility/layout consistency.
  - Relocated relevant alert controls into more intuitive tabs.
- Added/expanded overlay controls for timing, spacing, text scaling, theme, opacity, and layout behavior.

## Session/Workflow Utility Improvements

- Added CSV export support for active MyCycle leaderboard sessions.
- Improved MyCycle session/leaderboard UI behavior and home-tab presentation for daily operations.

---

## Practical “What’s New” Summary for Existing Users

- **You now run on a much more complete local web stack** for overlays + dashboard views.
- **Race and Tilt overlays are significantly more stable and stream-ready** (scrolling, timing, recap transitions, readability).
- **Tilt analytics are materially deeper** (dashboards, pressure/leaderboard insights, better death/survival math).
- **Chat tooling for Tilt and expertise ranking is stronger** (`!xp`, `!tiltdeath`, `!top10xp`, `!mytilts`).
- **The desktop app is more operationally polished** (settings organization, tray behavior, updater flow, auth fallback handling).
