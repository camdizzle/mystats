# Chat Output Current-State Assessment

This document inventories chat-facing outputs currently implemented in `mystats.py` and provides representative examples of the live format patterns.

## Scope reviewed

- Runtime Twitch command responses (`@commands.command(...)`) in `mystats.py`.
- Automated race/BR/tilt/raid/chat announcements emitted outside direct `!command` handlers.
- Existing docs were cross-checked, but this file is source-of-truth based on **current code behavior**.

---

## 1) Command-driven chat outputs (`!commands`)

| Command(s) | Current format pattern | Representative sample |
|---|---|---|
| `!info` | Owner/channel-only system line with ℹ️ prefix + pipe delimiters + URL | `ℹ️ Version 6.4.0, Season: 77 \| Total Races: 12,440 \| Total Points: 4,512,930 \| Race High Score: 7,250 \| BR High Score: 16,900 \| Marble Day: 03/01/2026 \| Points Today: 54,120 \| Races Today: 180 \| https://mystats.camwow.tv` |
| `!mostop10`, `!top10xp` | Single-line leaderboard: `Leaderboard | <rank label> name - value | ... | View the full leaderboard, <url>` | `Leaderboard \| 🥇 PlayerA - 184,320 \| 🥈 PlayerB - 173,940 \| ... \| View the full leaderboard, https://pixelbypixel.studio/hub` |
| `!meta` | Single sentence + docs URL | `Interested in learning more about the Streamer Meta? 📖: https://docs.google.com/document/...` |
| `!mosapp`, `!mosshop`, `!wiki` | Informational links (plain text) | `Marbles on Stream Wiki - https://wiki.pixelbypixel.studio/` |
| `!commands` | Comma-delimited generated command list | `MyStats commands: !info, !mystats, !top10season, !mytilts, !xp, ...` |
| `!rivals` | Three modes: global list, user rivals list, direct pair check; pipe-delimited outputs and qualifying/no-data fallbacks | `Rivals Check • PlayerA vs PlayerB \| Gap: ±322 pts \| PlayerA: 15,420 pts, 240 races \| PlayerB: 15,098 pts, 239 races \| ✅ Rivalry active` |
| `!h2h` | Comparative line with ⚔️ prefix and explicit leader | `⚔️ H2H PlayerA vs PlayerB \| Points: 15,420, 15,098 \| Races: 240, 239 \| Race HS: 7,200, 6,980 \| BR HS: 14,220, 13,910 \| Leader: PlayerA by 322` |
| `!mycycle` | Session progress line with 🔁 prefix, cycle counts, progress ratio, optional missing placements list | `🔁 PlayerA \| Session: Primary Session \| Cycles: 6 \| Progress: 4/5 \| Races this cycle: 13 \| Last cycle races: 11 \| Missing: 2` |
| `!cyclestats` | `🔁 CycleStats [...]` line with fastest/slowest + rotating metric + total cycles | `🔁 CycleStats [Primary Session] \| Fastest: PlayerA (10 races) \| Slowest: PlayerB (19 races) \| Average: 14.1 races \| Total cycles: 28` |
| `!myquests` | Quest summary with 🔎 prefix, completed count, then quest progress detail segments | `🔎 PlayerA Quest Progress: 2/5 quests complete \| Races: 210/500 \| Points: 54,120/100,000 \| Tilt Levels: 128/300` |
| `!top10ppr` | PPR leaderboard with `Top 10 Racers by PPR (100+ races):` header; chunked into multiple chat messages as needed | `Top 10 Racers by PPR (100+ races): 🥇 PlayerA: 312.4 \| 🥈 PlayerB: 301.8 \| ...` |
| `!mystats` | Expanded profile line with race/BR/today/season breakdown + WR count and averages (pipe-delimited) | `PlayerA MyStats \| Today: 180 races, 22 wins, 54,120 pts \| Season: 1,240 races, 210 wins, 412,300 pts \| WRs: 5 \| Avg: 332.5` |
| `!mytilts` | ⚖️-prefixed tilt stats with run/today/season points+deaths + last completed level | `⚖️ PlayerA Tilt Stats \| Run: 2,450 pts, 3 deaths \| Today: 7,120 pts, 9 deaths \| Season: 41,220 pts, 58 deaths \| Last Level Completed: 27` |
| `!thisrun` | 🏃‍➡️ current/last-run snapshot; includes idle fallback message when no run exists | `🏃‍➡️ This Run (Active) \| Level: 19 \| Elapsed: 01:42 \| Leader: PlayerA (2,140 pts) \| Run Pts: 7,220 \| Run Expertise: 1,540 \| Top Tiltee: PlayerA (5) \| Deaths Today: 12` |
| `!xp` | ⚖️ expertise metrics line with last-level, last-run, today, season, lifetime XP | `⚖️ Expertise Stats \| Last Level XP: 156 \| Last Run XP: 2,142 \| Todays XP: 5,220 \| Season XP: 184,320 \| Lifetime XP: 912,440` |
| `!toptiltees` | ⚖️ leaderboard line combining top-tiltee counts and season points | `⚖️ Top Tiltees \| 🥇 PlayerA, 22 tops, 41,220 points \| 🥈 PlayerB, 18 tops, 36,100 points \| ...` |
| `!top10tiltees` | ⚖️ top tilt points leaderboard (`Top 10 Tiltees by Tilt Points`) | `⚖️ Top 10 Tiltees by Tilt Points \| 🥇 PlayerA, 41,220 points \| 🥈 PlayerB, 36,100 points \| ...` |
| `!tiltsurvivors` | ⚖️ survival leaderboard with configurable minimum-level qualifier | `⚖️ Top 10 Best Tilt Survival Rate (min 20 levels) \| 🥇 PlayerA, 4 deaths, 92.0% survive \| ...` |
| `!top10nwr`, `!top10today`, `!top10races`, `!top10wins`, `!top10season`, `!top10wr`, `!top10seasonnwr` | Standardized top lists using rank labels + pipe delimiters | `Top 10 Season 77 \| 🥇 PlayerA, 412,300 points \| 🥈 PlayerB, 399,120 points \| ...` |

### Notes on command coverage

- `!highfive` is a narrow owner-specific utility and only responds in a specific mention scenario.
- `!myenergy` is currently not active as a registered command (decorator is commented out).

### Command output behavior notes

- The codebase has moved heavily toward `|`-delimited single-line outputs.
- Rank formatting is increasingly unified via `format_ranked_label(...)` (often medal emojis for top placements).
- Tilt-related commands now consistently use `⚖️` prefixes.
- Rival/MyCycle/Quest features now have richer validation/no-data messaging than older baseline commands.

---

## 2) Automated (non-command) chat outputs

| Category | Current format pattern | Representative sample |
|---|---|---|
| Marble day reset | Fixed celebratory one-liner | `🎺 Marble Day Reset! 🎺` |
| Checkpoint winners | `Checkpoint Winners:` header + comma-separated checkpoint entries | `Checkpoint Winners: 1 - PlayerA, 2 - PlayerB, 3 - PlayerC` |
| Race milestone | Milestone celebration when racer reaches configured milestone (e.g., 120 races) | `🎉 PlayerA has just completed their 120th race today! Congratulations! 🎉` |
| Race winners / race narrative | Winner announcements + optional narrative alert bundles (grinder/win-milestone/lead-change) | `📣 Player Alerts: 🏁 Grinder: PlayerA reached 5 top finishes today \| 📈 Lead Change: PlayerB now leads by 1,240 points.` |
| Tilt per-level recap | Structured end-of-level recaps with survivors and points | `End of Tilt Level 19 \| Level Completion Time: 01:42 \| Top Tiltee: PlayerA \| Points Earned: 1,240 \| Survivors: PlayerA, PlayerB` |
| Tilt run completion | Final standings chunk(s), plus fallback when no results exist | `🏁 Tilt run complete! Final standings: (1) PlayerA 7,220 pts, (2) PlayerB 6,910 pts, ...` |
| Battle Royale winner | Crown/non-crown variants; optional `🧃` prefix; includes eliminations, damage, and today's stats | `🧃 CROWN WIN! 👑: PlayerA(usera) \| 12,440 points \| 19 eliminations \| 5,220 damage \| Today's stats: 54,120 points \| 22 wins \| 180 races` |
| MyCycle completion event | Fixed `🔁` event format with session and races used | `🔁 PlayerA completed a MyCycle in Primary Session! Cycle #6 took 13 races.` |
| Season quest completion | `🎯 Season Quest Complete:` templates across quest categories | `🎯 Season Quest Complete: PlayerA earned 100,400 / 100,000 season points!` |
| Competitive raid monitoring | Queue/live/cancel/summary announcements tied to competition API state | `🟡 channelname is next up for competitive raids! Queue is open now: https://pixelbypixel.studio/competitions` |

### Automated output behavior notes

- Automation messages are highly event-specific and emoji-forward.
- BR and race announcements have multiple format branches (display-name mode, crown mode, delay mode, chunking).
- Competitive raid messaging introduces a new queue/live/cancel/summary lifecycle in chat.

---

## 3) Existing documentation samples in repo

`TILT_GUIDE.md` includes sample output sections for:

- `!mytilts`
- `!xp`
- `!toptiltees`
- `!top10tiltees`
- `!tiltsurvivors`
- `!top10xp`

---

## 4) High-level assessment summary (current state)

1. **Formatting has improved toward consistency** (especially pipe-delimited one-line command responses).
2. **Command ecosystems are now more feature-rich** (`!rivals`, `!h2h`, `!mycycle`, `!myquests`, `!thisrun`) with clear branch-specific outputs.
3. **Tilt-related chat messaging is comparatively mature and visually consistent** (`⚖️`, structured metrics, robust no-data fallbacks).
4. **Automation remains the highest-variance area** due to many runtime branches (race narrative, BR crown logic, competition lifecycle).
5. **Legacy/edge commands still exist** with less standardization than newer command families.
