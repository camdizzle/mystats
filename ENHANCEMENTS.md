# Watchdog and Chart.js

Install the optional filesystem notification dependency in the Python environment used to run or build MyStats:

    python -m pip install -r requirements-enhancements.txt

Race, BR, and Tilt monitors use filesystem notifications when available, with seven-second reconciliation checks if events are missed or Watchdog is unavailable. Existing modification-time checks and file-settling delays still apply.

The six trend charts use a local copy of Chart.js 4.4.8, including its MIT license, so no internet connection is required. The previous SVG charts remain available when Chart.js cannot load. Existing installers copy the dashboard vendor directory recursively. Rebuild the application executable with Watchdog available in the build environment; the monitoring helper is embedded in mystats.py; no executable or installer is included in this change.

Checks:

    node test_trend_charts.cjs
    python -m py_compile mystats.py
    node --check modern_dashboard/dashboard.js

Full Twitch/OBS operation and visual dashboard rendering require a smoke test in the normal MyStats environment.

MyStats remains a single Python application file. No companion Python module or test file is required or shipped by this change. Watchdog is an optional third-party package; without it the embedded monitor uses periodic checks.


## Diagnostics
Open Settings -> Diagnostics. Refresh status to inspect Twitch connection state, Watchdog/polling status, configured export paths, file modification times, last notification times, dashboard asset directory/build fingerprint, Chart.js availability, and chat sent/blocked/failed counters. Copy report copies the displayed snapshot, including local paths but excluding tokens and message contents. Counters and notification history reset when the app restarts. A notification means a file changed, not that scoring completed. Checkpoints continue to use periodic checks.

## Chat controls
Settings -> Chat -> Chat Controls now includes a master outgoing-chat switch and separate team bonus and quest announcement switches. Save to apply. Category switches still gate Race, BR, Tilt, and command output. MyCycle keeps its existing announcement switch; race/BR category switches also gate those associated messages. Team bonus announcements are independent of user command replies. Master mute suppresses outgoing chat while file processing, scoring, overlays, and team bonus accounting continue. Every outgoing send now passes the same checks, including replies to commands and messages awaiting announcement delays. Diagnostics counts attempted deliveries; an incoming command disabled before dispatch does not count as a blocked send.

## Interactive trends
Dashboard -> Race/BR Trends offers 7/21/30/90-day, all-data, and custom date ranges; daily/weekly grouping; metric selection; previous-period comparison; and CSV export. Presets end on the latest recorded day. Filters apply to current-season history; season charts remain an all-season overview. Comparisons shift the immediately preceding equally sized calendar window onto the current dates; CSV keeps original dates and a period column. No prior data is reported explicitly.

The existing trend source uses first-place result rows. Winner charts therefore describe distinct winners, not all race participants. Weekly winner counts average the daily counts on recorded days; they are not distinct weekly counts. Weekly points per event uses summed winning points divided by summed events, with exact point totals supplied by the API. Partial weeks include only selected recorded days. Missing days are not invented as zero activity. With Chart.js unavailable, comparisons render as separate SVG charts. Deploy the updated dashboard folder alongside the rebuilt executable and hard-refresh the browser.

Validation for this update includes temporary Python checks for master/category/feature gates, delayed-message cancellation, delivery failure accounting, diagnostic redaction, and the single common send path. The JavaScript harness covers filters, weighted weekly totals, invalid dates, comparisons, refresh cleanup, SVG fallback, and empty data. Browser preview checks use synthetic data; live Twitch/OBS integration and the full desktop settings flow still need a smoke test. No additional Python source or test files are shipped.


## Settings menu and saving
Main tabs are General, Chat, Overlays, Features, MyTeams, and Diagnostics. General opens on General rather than Audio. MyCycle, Rivals, Season Quests and Tilt command thresholds are under Features. Diagnostics contains status and the optional Send Test Messages page. Preferences pages scroll vertically only; the footer adapts to narrower windows, and the initial window size respects the screen height.

Preferences, themes, audio device and sound file choices remain pending until Apply or Save and Close. Apply keeps the menu open. Cancel or the window close button offers save/discard/keep-editing choices when there are pending edits. An asterisk in the title marks unsaved changes. Only one settings window opens at a time. Opening Settings and refreshing the team table no longer save draft preferences.

All numeric fields are checked before any preferences are written. Invalid fields are marked, revealed and focused, with a readable error and allowed range. Cross-field checks cover MyCycle placement order and nonzero random bonus weights. Overlay display ranges match the existing overlay limits. Invalid stored values remain editable even when their feature is disabled. Linked controls are disabled when irrelevant; alert options remain editable while chat is muted because they also control overlay events.

A form submission writes changed preferences once using the existing temporary-file/atomic-replace mechanism. Configuration reads and writes share a reentrant lock. If persistence fails, previous in-memory values are restored and pending edits remain in the open form. Unedited settings changed by another app task are not overwritten by an old form snapshot. Channel, server-port and language changes prompt for restart.

Reset section and Reset all preferences stage defaults rather than saving immediately. They preserve the channel, chosen sound files, selected MyCycle session, teams and progress counters. Team preferences and the desktop theme are included in reset coverage. Management actions, session activation/creation/deletion, quest-progress resets, and test sends are immediate; these are labeled separately and are not undone by Cancel. Quest reset and session deletion ask for confirmation.

Verification used isolated temporary settings and mocked Twitch/team services: six persistence checks (single write, validation, memory rollback, no-op/zero targets, concurrent writers, failed atomic replacement) and nine actual Tk window checks (navigation/read-only open, invalid fields, Apply, failure retention, reset coverage, dependencies/Cancel, section-only reset/staged theme, disabled-field recovery, and minimum-size save-button visibility). Existing live Twitch/OBS integration still needs a smoke test. No additional Python files are shipped; version remains 6.4.1.


## Wider settings and removed competitive raid feature
Settings pages no longer create horizontal scrollbars or move horizontally. The window opens wider and grows to the natural width of its preferences (within screen limits). Canvas content follows the visible width. Audio and team settings cards stack vertically on narrower screens. Vertical scrolling remains available, including in session management.

Competitive raid controls, stored-setting definitions, startup task, API polling/history requests, announcements, snapshot writing and exclusive parsing helpers have been removed. Existing historical files and unknown legacy settings are preserved but are not used by the application. Current feature documentation and message examples no longer advertise the removed feature. The Windows toast callback fix remains a separate change in PR #402.

Verification for this change: nine existing Tk menu regressions and six persistence checks passed. Three additional layout checks covered absence of horizontal scrollbars, input bounds across every settings tab, and vertical stacking below the team cards' natural combined width. Source checks confirmed 21 exclusive raid functions were removed without dangling references, while Race, BR, Tilt and checkpoint startup tasks remain. Python compilation and whitespace checks passed.
