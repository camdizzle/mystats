**MyStats 7.0.0 — What’s changed since August (1/3)**

MyStats has received a major refresh across the desktop app, dashboards, overlays and game-result handling.

**A clearer main window**
• The Overview brings together Today/Season statistics, Twitch connection, outgoing-chat status, file monitoring and recent activity.
• Refreshed Darkly styling makes the application easier to read.
• Open the web dashboards from the app to explore more detail.

**More reliable game results**
• Updated support for the newer Marbles Race, Battle Royale and Tilt exports.
• Faster file-change detection when Watchdog is available, with periodic checks as a fallback.
• Suspected Tilt run endings get a brief confirmation window. If the game corrects its export, MyStats can pick up that correction instead of announcing an ended run too early.
• Race chat messages now respect their disabled setting.
• Team bonus controls apply immediately, with fixes to bonus expiry handling.

**Getting started after updating**
1. Close MyStats before installing the update, then start it again.
2. Check the export folder and Twitch channel in Settings.
3. Check the monitoring/connection status in Overview or Diagnostics.
4. Complete a game and confirm that its results appear.

Keep your Results/history folders when updating. A merged GitHub change does not update an already installed application—you need the matching application build and dashboard assets.

---

**MyStats 7.0.0 — Dashboard and OBS guide (2/3)**

**The dashboard hub**
Choose Darkly or Midnight styling. Navigation wraps in narrower windows, and compact lists offer expandable detail. Connection messages explain reconnecting or stale data while keeping the last successful results visible.

Click a player to open recorded results, personal-record improvements and saved desktop goals.

**What to explore**
• **MyCycle:** choose a session, sort by closest completion, spot players one position away and expand recorded cycle history.
• **Season Quests:** see progress for each active quest and the closest unfinished target. Pagination now keeps the correct row numbering.
• **Tilt:** choose Current Run, Today or Season. A pending message shows when a possible run ending is being confirmed. Survival uses recorded outcomes; older unknown results are labeled rather than treated as deaths.
• **Rivals:** search and sort matchups, pin a comparison and view its observed point-gap history. Empty updates clear old matchups.
• **Race/BR:** find players and compare points, entries, high scores, kills, damage and archived survival data where available.
• **Teams:** filter recruiting teams, expand rosters, see individual season results and follow active bonus countdowns.
• **Trends:** select dates, daily/weekly grouping and metrics, compare periods, export CSV and open related history. Participant and winner counts are separate.
• **Guide:** search setup, OBS, chat, troubleshooting and command help.

**OBS presets**
Use the OBS presets tab to choose a target size, text scale, card opacity, layout and stat scope. Preview it, save the preset and copy its URL into an OBS Browser Source using the displayed dimensions.

Presets and pinned-rival observations are saved in that browser profile. Rival history starts when observed; unavailable older telemetry cannot be reconstructed.

---

**MyStats 7.0.0 — Chat, tools and settings (3/3)**

**Take control of chat**
Use Settings to choose which message categories are enabled. Desktop chat tools can pause outgoing messages or preview what MyStats would send without posting it. Changes are checked again before delayed messages are sent.

**Useful desktop tools**
• Browse saved game history by player, event and date, then export results to CSV.
• Review personal-record improvements and set score goals.
• Open Diagnostics to check monitoring, export paths and recent warning/error contexts.
• Save a troubleshooting report when requesting support.
• Back up and restore supported preferences. Credentials and game history are excluded from preference backups.

**Settings and Help**
• Settings are reorganized, wider and use vertical scrolling rather than horizontal scrollbars.
• Invalid settings are caught before saving, and preference updates are written together.
• Competitive Raid settings and code have been removed.
• About works offline again. Commands are organized into searchable categories with usage examples.
• Startup notification handling and the missing-image update prompt have been repaired.

**Custom bot logins**
Custom-login tokens now use Windows Credential Manager. Existing matching JSON credentials are removed only after the Windows copy is verified. If migration cannot finish, MyStats preserves the old file and reports the issue.

**Before reporting a problem**
Check that the application and dashboard assets came from the same release. Include your version, game mode, what you expected and what happened. Use the troubleshooting report where helpful; review it for personal paths before sharing. Do not post tokens or settings files containing credentials.
