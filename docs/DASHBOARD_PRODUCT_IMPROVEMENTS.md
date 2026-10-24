# Dashboard product improvements

The dashboard hub retains the single `mystats.py` application and existing asset bundles. No Python helper module or new runtime dependency is required.

## User-visible behavior

- Darkly and Midnight themes, readable secondary text, wrapping navigation, compact comparisons, expandable details, search and reset controls. At narrow widths, summaries move above the leaderboard.
- A connection banner retains the last successful payload while reconnecting, and reports stale data after 90 seconds without a successful response. Live updates preserve draft search text and expanded details. Only the selected view redraws.
- Clicking a player opens season results, strict personal-record improvements and saved desktop goals. History shows at most 200 results and states the full matching count.
- MyCycle supports active/inactive session selection, closest-to-completion ordering, one-position-away highlighting, and the last 50 recorded cycle completions. Search and pagination apply to the full selected session.
- Season Quests shows progress toward each enabled target and the closest incomplete target. Page-two numbering includes the page offset. Page-based summary totals are labeled accordingly.
- Tilt supports season, today and current-run scopes, with a pending confirmation indicator. Deaths and survival rates use explicit saved outcomes. Unknown older outcomes are excluded from the rate denominator and coverage is shown. Speculative Pressure and Consistency choices are removed.
- Rivals clears empty updates, supports a saved pinned comparison, player details and observed gap history. Gap samples are retained in this browser from the time a matchup is pinned; past gaps are not reconstructed. Up to 60 changed-gap observations are retained per matchup.
- Race/BR supports player search, points/entry/high-score/kill/damage/survival ordering, archived BR survival averages/bests/sample counts, and recorded kill/damage totals. Missing older telemetry is labeled unavailable.
- Teams supports recruiting-only filtering, name/points/size ordering, expandable rosters, individual season results and active-bonus countdowns. Individual results are explicitly distinguished from bonus-adjusted team totals and historic membership.
- Trends defaults to event volume instead of every metric. Participant counts use every saved player result; winner counts remain separate. Weekly participant/winner values are labeled average daily counts. Charts link to day/week history, including the original dates of comparison points. Existing filters, weighted PPR, comparisons, CSV export and SVG fallback remain available. Full season analytics are expandable.
- Guide provides searchable setup, OBS, chat and troubleshooting tasks plus the same command catalog as desktop Help. It works without the optional README.html and provides a retry if the command API fails.
- OBS presets provide independent source URLs, target-size previews, opacity/text controls, horizontal layout and simple season/today/all stat scope. Presets persist in this browser; copied URLs contain the settings. URL values are bounded. Settings survive Race/Tilt redirects, and the server chooses the proper layout for the source's horizontal override.

## Validation

Run from the repository root:

    python -m py_compile mystats.py
    node --check modern_dashboard/dashboard.js
    node --check obs_overlay/overlay.js
    node --check obs_overlay/tilt_overlay.js
    node tests/test_trend_charts.cjs
    node tests/test_dashboard_product.cjs

Additional isolated backend checks exercised complete-source pagination, empty searches, cache isolation, explicit/unknown Tilt outcomes, pending status, and counting non-winning participants. Existing Tilt confirmation (11), desktop tools (21), and diagnostics/chat (5) regression checks passed. Browser verification used synthetic data, including desktop layout, a 375px content viewport without horizontal overflow, player details, quests, pinned rivals, Guide without README.html, participant trends and OBS source previews. No live Twitch messages, actual game run, packaged executable, OBS scene or Inno build was used for these checks.

## Data limits

Survival metrics cannot recover fields missing from older exports. Cycle history uses the application's existing bounded stored history. Rivalry observations and OBS presets are local to the browser profile and are not cloud-synced. Team member results are individual current-season results rather than reconstructed historic team contributions. Dashboard history is scoped to the current Results directory, as in desktop Tools.
