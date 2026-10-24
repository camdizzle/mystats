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
