# MyStats MyTeams — Complete User Guide

This guide explains how to use the **MyTeams** feature end-to-end in MyStats: setup, commands, moderation, scoring, bonus multipliers, dashboard/overlay views, and troubleshooting.

---

## 1) What MyTeams is

MyTeams is a channel-scoped competition layer in MyStats.

- MyTeams currently runs in local channel mode.
- Chat commands manage team membership and moderation.
- Team points are computed from member race/BR activity (with optional bonus/sub logic).

> Tip: Use this guide for stream setup and to share with captains/co-captains.

---

## 2) Streamer setup (desktop app)

Open **Settings → MyTeams**.

### Core toggles

- **Enable MyTeams Commands**: enables/disables all team chat commands.
- **Rollout Phase**:
  - Keep this set to `local` for the current command-driven MyTeams experience.

### Scoring and size controls

- **Points Counting Mode**:
  - `season` = count members' full season points.
  - `active` = count points only after team creation/join timing.
- **Max Team Size**: hard cap on team size.

### Bits bonus controls

- **Bonus Bits Threshold**: bits required to trigger a team bonus roll.
- **Bonus Duration (min)**: minutes added per successful activation.
- **Bonus Weights 2x/3x/4x**: weighted odds for multiplier selection.

### MyTeams admin table/actions

The MyMyTeams table shows: captain, size, recruiting state, active bonus label, daily/weekly/season points.

Buttons:
- **Refresh**
- **Generate Team Name** (copies generated name to clipboard)
- **Toggle Recruiting** (for selected team)
- **Delete Team** (also removes associated invites/cache entries)

---

## 3) Quickstart flows

## A) Captain quickstart

1. Ensure you are a subscriber (or broadcaster), then run:
   - `!createteam Your Team Name`
2. Invite people:
   - `!invite username`
3. Appoint trusted helper:
   - `!cocaptain username`
4. Open recruiting:
   - `!recruiting on`
5. Set team logo/emote:
   - `!logo :your_emote:`
6. Set inactivity policy:
   - `!inactive 14`
7. Check status:
   - `!myteam`

## B) Member quickstart

- Join from invite: `!acceptteam Team Name`
- Reject invite: `!denyteam Team Name`
- Auto-join open recruiting: `!join`
- View team: `!myteam`
- Leave team: `!leave`

## C) Streamer moderation quickstart

- In UI: select team in MyTeams table, **Toggle Recruiting** or **Delete Team**.
- In chat (captain/co-captain): `!kick username`, `!inactive X`.

---

## 4) Complete command reference

> All commands use `!` prefix.

### Discovery

- `!teamhelp` — Quick MyTeams how-to blurb for chat.
- `!tcommands` — Shows all team commands.

### Team creation and joining

- `!createteam [team name]`
  - Creates a team if you are not already on one.
  - Subscriber-only (broadcaster exempt).
  - If name omitted, MyStats auto-generates one.
- `!invite <username>`
  - Captain/co-captain only.
  - Sends invite (expires after 7 days).
- `!acceptteam <team name>`
  - Accept a pending invite if team exists and has room.
- `!denyteam <team name>`
  - Deny a pending invite.
- `!join`
  - Auto-joins the best available recruiting team with space.

### Team management

- `!cocaptain <username>`
  - Captain only.
  - Promotes existing member to co-captain.
- `!kick <username>`
  - Captain/co-captain only.
  - Removes member/co-captain (captain cannot be kicked).
- `!leave`
  - Leave your current team.
  - If captain leaves:
    - first co-captain is promoted, else first member, else team is archived.
- `!recruiting on|off`
  - Captain/co-captain only.
- `!logo <emote>`
  - Captain/co-captain only.
  - Sets team logo shown in `!myteam`.
- `!inactive <days>`
  - Captain/co-captain only.
  - Stores inactivity threshold and performs immediate lightweight sweep of stale members.

### Team info and standings

- `!myteam [@username]`
  - Detailed status for your team, or for the tagged user's team:
  - rank, season/daily points, sub points, active bonus label, bonus races, kick policy, recruiting state, captain + member list.
- `!dailyteams`
  - Top 5 teams by today points.
- `!weeklyteams`
  - Top 5 teams by 7-day points.

---

## 5) Roles and permissions

- **Captain**
  - Full team control (invite, promote co-captain, kick, logo, recruiting, inactive policy).
- **Co-captain**
  - Operational control (invite, kick, logo, recruiting, inactive policy).
  - Cannot assign co-captain.
- **Member**
  - Can view/leave, accept/deny own invites.

---

## 6) How scoring works

Team points combine:

1. **Member race/BR points** from historical allraces data.
2. **Optional subscriber contribution effects** from member metadata.
3. **Team bonus windows** (bits-triggered multipliers).

### Points windows

- **Daily**: today only.
- **Weekly**: rolling 7 days.
- **Season**: full season.

### Points mode

- `season`: member's full season history counts.
- `active`: member points count from team join/create timing.

### Caching behavior

MyStats stores computed team points in `team_points_cache.json` for faster leaderboard reads.

---

## 7) Bits bonus system

When a chatter donates bits:

1. Bits are attributed to donor's current team.
2. Team accumulates `bits_bank`.
3. Each time `bits_bank >= threshold`, a bonus activation occurs:
   - choose multiplier (2x/3x/4x) from configured weights,
   - start/extend active bonus duration,
   - update label (e.g., `⚡3x`),
   - emit activation chat message.

Notes:
- Multiple threshold crossings can occur from one large bits event.
- Existing active bonus may be extended and/or increased.

---

## 8) Dashboard + overlay integration

## Dashboard

- Open `/dashboard` and use the **MyTeams** tab.
- MyTeams panel shows:
  - KPI cards (tracked teams, recruiting teams, average points),
  - highlight cards (season leader, today leader),
  - team leaderboard rows (captain, size, recruiting, bonus label).

## Overlay

- `/api/overlay/top3` now includes team views in rotation when team data exists:
  - **Top MyTeams Today**
  - **Top MyTeams Season**
- `/api/overlay/myteams` returns team lists explicitly:
  - `top_today`, `top_weekly`, `top_season`.

---

## 9) Data files (local persistence)

- `teams_data.json`
  - MyTeams records, invites, role/membership, metadata, recruiting flags, bonus state.
- `team_points_cache.json`
  - Cached daily/weekly/season team points and bonus race counters.

If teams are deleted/archived, MyStats cleans associated invites and cache entries.

---

## 10) Operational best practices

- Start with `Max Team Size` around 15–25.
- Keep recruiting closed by default; open during active community windows.
- Assign 1–2 co-captains per high-volume team.
- Use `!inactive` policies to keep teams fresh.
- Keep bonus threshold high enough to feel special (e.g., 1000+ bits).
- Share `!tcommands` in chat periodically for discoverability.

---

## 11) Troubleshooting

### "Nothing happens when I use team commands"

- Check **Enable MyTeams Commands** in Settings → MyTeams.
- Confirm you are in `local` phase for full command flow.

### "I can't create a team"

- `!createteam` is subscriber-only (except broadcaster).
- You also cannot create if already in a team.

### "Invite won't accept"

- Invite may have expired (7 days) or been denied.
- Team may be full (max size reached).
- Team might have been deleted.

### "`!join` says no recruiting teams"

- All recruiting teams may be closed or full.
- Captains/co-captains must run `!recruiting on`.

### "Bonus isn't triggering"

- Donor must be in a team.
- Bits amount must cross configured threshold (possibly cumulative via `bits_bank`).

### "My team points look stale"

- Cached values are used for speed; they refresh as activity and reads occur.
- Use UI **Refresh** in MyTeams tab and verify ingest is running.

---

## 12) Suggested streamer announcement

"MyTeams is live in MyStats! Use `!tcommands` to see commands. Subs can create teams with `!createteam`, captains can invite with `!invite`, and everyone can track standings with `!dailyteams`, `!weeklyteams`, and `!myteam`."
