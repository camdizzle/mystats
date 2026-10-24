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
Settings -> Race/BR -> Chat now includes a master outgoing-chat switch and separate team bonus and quest announcement switches. Save to apply. Category switches still gate Race, BR, Tilt, and command output. MyCycle keeps its existing announcement switch; race/BR category switches also gate those associated messages. Team bonus announcements are independent of user command replies. Master mute suppresses outgoing chat while file processing, scoring, overlays, and team bonus accounting continue. Every outgoing send now passes the same checks, including replies to commands and messages awaiting announcement delays. Diagnostics counts attempted deliveries; an incoming command disabled before dispatch does not count as a blocked send.

## Interactive trends
Dashboard -> Race/BR Trends offers 7/21/30/90-day, all-data, and custom date ranges; daily/weekly grouping; metric selection; previous-period comparison; and CSV export. Presets end on the latest recorded day. Filters apply to current-season history; season charts remain an all-season overview. Comparisons shift the immediately preceding equally sized calendar window onto the current dates; CSV keeps original dates and a period column. No prior data is reported explicitly.

The existing trend source uses first-place result rows. Winner charts therefore describe distinct winners, not all race participants. Weekly winner counts average the daily counts on recorded days; they are not distinct weekly counts. Weekly points per event uses summed winning points divided by summed events, with exact point totals supplied by the API. Partial weeks include only selected recorded days. Missing days are not invented as zero activity. With Chart.js unavailable, comparisons render as separate SVG charts. Deploy the updated dashboard folder alongside the rebuilt executable and hard-refresh the browser.

Validation for this update includes temporary Python checks for master/category/feature gates, delayed-message cancellation, delivery failure accounting, diagnostic redaction, and the single common send path. The JavaScript harness covers filters, weighted weekly totals, invalid dates, comparisons, refresh cleanup, SVG fallback, and empty data. Browser preview checks use synthetic data; live Twitch/OBS integration and the full desktop settings flow still need a smoke test. No additional Python source or test files are shipped.
