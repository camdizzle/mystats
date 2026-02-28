# Chat Output Current-State Assessment

This document inventories current chat-facing outputs found in the codebase and provides representative sample outputs for format review.

## Scope reviewed

- Runtime Twitch chat responses and announcements in `mystats.py`.
- Existing documented command output examples in `TILT_GUIDE.md`.
- Overlay-only text was excluded unless it explicitly reflects chat command display text.

## 1) Command-driven chat outputs (`!commands`)

Below is the current output style per command (or command family) with a representative sample.

| Command(s) | Current format pattern | Sample output |
|---|---|---|
| `!info` | Pipe-delimited seasonal/system summary with URL | `Version 6.4.0 | Season: 77 | Total Races: 12,440 | Total Points: 4,512,930 | Race High Score: 7,250 | BR High Score: 16,900 | Marble Day: 03/01/2026 | Points Today: 54,120 | Races Today: 180 | https://mystats.camwow.tv` |
| `!mostop10`, `!top10xp` | Multi-line leaderboard with medal emojis for top 3 + trailing link | `🥇 1. PlayerA - 184,320`<br>`🥈 2. PlayerB - 173,940`<br>`🥉 3. PlayerC - 169,102`<br>`... | View the full leaderboard at: https://pixelbypixel.studio/hub` |
| `!meta` | Single sentence + docs URL | `Interested in learning more about the Streamer Meta? 📖: https://docs.google.com/document/...` |
| `!energy` | Long explanatory paragraph-style command response | `Energy is the system by which viewers exchange their energy with streamers, for points...` |
| `!mosapp`, `!mosshop`, `!wiki` | Simple informational link response | `Marbles on Stream Wiki - https://wiki.pixelbypixel.studio/` |
| `!commands` | Comma-delimited command list with fixed prefix | `MyStats commands: !info, !mystats, !top10season, !mytilts, !xp, ...` |
| `!rivals` | Multiple variants: global leaderboard / user rivals / pairwise comparison / validation errors | `Rivals Check • PlayerA vs PlayerB | Gap: ±322 pts | PlayerA: 15,420 pts (240 races) | PlayerB: 15,098 pts (239 races) | ✅ Rivalry active` |
| `!h2h` | Compact comparative stat line with leader + gap | `H2H PlayerA vs PlayerB | Points: 15,420-15,098 | Races: 240-239 | Race HS: 7,200-6,980 | BR HS: 14,220-13,910 | Leader: PlayerA by 322` |
| `!mycycle` | Session-scoped cycle summary; includes no-data fallback | `PlayerA MyCycle [Primary]: 6 cycles | Best: 12 races | Avg: 14.3 races | Last: 13 races` |
| `!cyclestats` | `🔁 CycleStats [...]` line with fastest/slowest + average metric | `🔁 CycleStats [Primary Session] | Fastest: 10 races | Slowest: 19 races | Average: 14.1 races | Total cycles: 28` |
| `!myquests` | Headline + detail blocks separated by pipes | `Quest Progress for PlayerA | Races: 210/500 | Points: 54,120/100,000 | Tilt Levels: 128/300` |
| `!top10ppr` | Chunked leaderboard messages for points-per-race ranking | `Top 10 PPR (min races met): (1) PlayerA 312.4 ppr, (2) PlayerB 301.8 ppr, ...` |
| `!mystats` | Core profile line containing races/wins/points/high score style summary | `PlayerA: 180 races | 22 wins | 54,120 pts | HS: 6,990 | Avg: 300.7` |
| `!mytilts` | Tilt run/today/season in one line + last level completed | `PlayerA Tilt Stats | Run: 2,450 pts, 3 deaths | Today: 7,120 pts, 9 deaths | Season: 41,220 pts, 58 deaths | Last Level Completed: 27` |
| `!xp` | Expertise block with 4 metrics | `Expertise Stats | Last Level XP: 156 | Last Run XP: 2,142 | Today's XP: 5,220 | Season XP: 184,320` |
| `!toptiltees` | Comma-delimited placement list (tops + points) | `Top Tiltees: (1) PlayerA 22 tops, 41,220 points, (2) PlayerB 18 tops, 36,100 points, (3) PlayerC 15 tops, 29,880 points.` |
| `!top10tiltees` | Comma-delimited top points list | `Top 10 Tiltees by Tilt Points: (1) PlayerA 41,220 points, (2) PlayerB 36,100 points, ...` |
| `!tiltsurvivors` | Survival-rate leaderboard with minimum-level qualifier in prefix | `Top 10 Best Tilt Survival Rate (min 20 levels): (1) PlayerA 4 deaths, 92.0% survive, (2) PlayerB 6 deaths, 88.5% survive.` |
| `!top10nwr`, `!top10today`, `!top10races`, `!top10wins`, `!top10season`, `!top10wr`, `!top10seasonnwr` | Traditional Top-10 list format using `(rank) Name value` and commas | `Top 10 Season 77: (1) PlayerA 412,300 points, (2) PlayerB 399,120 points, ...` |

### Command output behavior notes

- Formatting style is mixed: some commands use pipes (`|`), others commas, others multiline blocks.
- Emoji usage is inconsistent (some commands are plain-text, others emoji-prefixed).
- Singular/plural handling is present in some outputs, absent in others.
- Error/no-data outputs exist for most commands, typically terse (`No ... available yet.`).

## 2) Automated (non-command) chat outputs

These are emitted by background race/BR/tilt processing.

| Category | Current format pattern | Sample output |
|---|---|---|
| Marble day reset | Fixed celebratory one-liner | `🎺 Marble Day Reset! 🎺` |
| Race winners | Multiple variants: world-record prefix vs standard winners list, chunked if long | `🧃 🌎 WORLD RECORD 🌎: PlayerA 7,250 points, PlayerB 6,980 points` |
| Race no-winner fallback | Fixed message | `Race Winners 🏆: No Winners!` |
| Race/BR milestone | Event-specific milestone line | `120th race today! Congratulations! 🎉` |
| Tilt per-level recap | Prefix-rich line with level time, top tiltee, points, survivors | `End of Tilt Level 19 | Level Completion Time: 01:42 | Top Tiltee: PlayerA | Points Earned: 1,240 | Survivors: PlayerA, PlayerB, PlayerC` |
| Tilt narrative alerts | Aggregated player alert block, pipe-separated | `📣 Player Alerts: 🏁 Grinder: PlayerA reached 5 top-tiltee appearances this run | 📈 Lead Change: PlayerB now leads by 1,240 points.` |
| Tilt run completion | Final standings chunk(s) or no-results fallback | `Tilt run complete! Final standings: (1) PlayerA 7,220 pts, (2) PlayerB 6,910 pts, ...` |
| Battle Royale winner | Crown/non-crown variants, optional `🧃` prefix, includes eliminations+damage+today stats | `🧃 CROWN WIN! 👑: PlayerA(usera) | 12,440 points | 19 eliminations | 5,220 damage | Today's stats: 54,120 points | 22 wins | 180 races` |
| MyCycle completion event | Fixed `🔁` structure with cycle number and races used | `🔁 PlayerA completed a MyCycle in Primary Session! Cycle #6 took 13 races.` |
| Season quest completion | `🎯 Season Quest Complete:` templates across races/points/HS/tilt metrics | `🎯 Season Quest Complete: PlayerA earned 100,400 / 100,000 season points!` |

### Automated output behavior notes

- Strong variability in prefixing (`🧃`, `🌎`, `🏆`, `🎯`, `🔁`) depending on category/settings.
- BR and race winner strings have the most variant branching (crown win, display name mode, chunking, delay settings).
- Tilt outputs are the most structured category (`Level`, `Run`, `Narrative`, `No results` fallbacks).

## 3) Existing documentation samples already in repo

`TILT_GUIDE.md` already includes “Sample output” blocks for:

- `!mytilts`
- `!xp`
- `!toptiltees`
- `!top10tiltees`
- `!tiltsurvivors`
- `!top10xp`

## 4) High-level assessment summary (current state)

1. **Output style is functionally rich but not standardized.** The codebase mixes multiline, pipe-delimited, comma-delimited, and sentence-style outputs.
2. **Emoji conventions are category-specific rather than global.** Race/BR/tilt automation is emoji-heavy; many direct commands are not.
3. **No-data/error responses are present but inconsistent in tone and phrasing.**
4. **Some command families are already semi-aligned internally** (Top-10 commands), while cross-family alignment is still low.
5. **Tilt command docs are relatively mature** compared with race/BR/general command documentation.

---

If you want, I can generate a follow-up **normalization checklist only** (no code changes) that you can use to apply your own formatting standard across these message families.
