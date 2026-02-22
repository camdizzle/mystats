ALL SETTINGS ARE UPDATED IN settings.txt

You can link your own account to mystats via the app.  Click the button in the top right corner.  If you have any token errors and the app will not open, then delete token.json file from your mystats folder and restart the app.

If you use the default account, you need to make mystats_results a moderator in your twitch chat

Manual OBS OVERLAY FILES:
CountofRaces.txt (The number of races recorded in the results file for today)
AvgPointsToday.txt (Avg of points earned / Races completed)
HighScore.txt (Name and Points of the high score of the day!)
LatestWinner.txt (Text output displaying the last race winner)
TotalPointsToday.txt (Total points earned today)
WinnerTotalPoints.txt (Total points of the last race winner)

## Version 6.1.0 Enhancements

### Overlays (Race + Tilt)
MyStats ships with a built-in Flask web server that serves overlays directly to OBS Browser Sources. The overlays auto-refresh from MyStats API endpoints, so once the Browser Source is connected you do not need to manually refresh files.

**How overlays work:**
- MyStats reads race and tilt data from your local output files.
- The local web server exposes UI pages (`/overlay`, `/overlay/tilt`) and JSON APIs.
- Overlay pages poll those APIs on an interval and repaint cards/pills/leaderboards.
- Overlay visual settings (theme, text scale, spacing, rotation speed, etc.) come from Settings → Overlay and are pushed into the page payload.

**How to connect overlays in OBS:**
1. Start MyStats.
2. In MyStats, open **Settings → Overlay** and confirm the **Server Port** (default `5000`).
3. In OBS, add a **Browser Source**.
4. Use one of these URLs:
   - Main overlay: `http://127.0.0.1:<overlay_server_port>/overlay`
   - Tilt overlay: `http://127.0.0.1:<overlay_server_port>/overlay/tilt`
5. If you change the server port, restart MyStats and update the OBS source URL.

If an overlay page returns Not Found, open Settings once and confirm your install includes the `obs_overlay` folder.

### Modern Dashboard
The modern dashboard is also served by the same local Flask server and is intended for live monitoring, scene prep, and stream management.

**How dashboard data works:**
- Dashboard page: `http://127.0.0.1:<overlay_server_port>/dashboard`

**How to connect/open dashboard:**
1. Start MyStats.
2. Confirm Settings → Overlay **Server Port**.
3. Open **Dashboards (Modern)** from the app, or paste the dashboard URL above in a browser.
4. If data is missing, open `/api/dashboard/main` directly and verify JSON is returned.

### Tilt Dashboard Highlight: Pressure Score
In the Tilt leaderboard, the right-side **pressure** value is a weighted performance score used for ranking highlights and row order. It combines production, clutch finishes, and survivability:

`pressure = (tilt_points * 1.5) + (tilt_top_tiltee * 25) - (deaths * 8)`

Where:
- `deaths = max(0, tilt_levels - tilt_top_tiltee)`
- Higher tilt points increase pressure.
- More top-tiltee finishes increase pressure significantly.
- More deaths reduce pressure.

This gives you a quick “who is applying the most pressure right now” signal, instead of only sorting by one raw stat.


## OBS Overlay (Built-in Flask)
Use Browser Source: `http://127.0.0.1:5000/overlay`

If port `5000` is already in use, open Settings → Overlay and change **Server Port** (default `5000`).
After changing the port, restart MyStats and update the OBS Browser Source URL to match.

If `/overlay` returns Not Found, open desktop app Settings once and confirm your install includes the `obs_overlay` folder (the app now checks multiple locations automatically, including packaged and working-directory paths).

Header stats now show 6 pills:
- Avg Pts Today
- Avg Pts Season
- Unique Racers Today
- Unique Racers Season
- Total Races Today
- Total Races Season

Responsive tweaks are included for smaller OBS source sizes.

Header pills rotate every 10 seconds between Today stats and Season stats.

Overlay settings are controlled from the desktop app (Settings → Overlay) and pushed to the browser source:
- Top stat rotation speed (default 10s)
- Data refresh interval
- Background theme presets
- Card opacity
- Text scale
- Top-3 medal emote visibility
- Compact row spacing
