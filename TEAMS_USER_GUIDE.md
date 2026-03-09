# MyStats MyTeams — User Guide (Current State)

This guide reflects the current MyTeams implementation in MyStats (local channel mode): setup, commands, team management, scoring/bonus behavior, dashboard visibility, and troubleshooting.

---

## 1) What MyTeams is

MyTeams is a channel-scoped competition layer in MyStats.

- Teams are stored locally per channel in MyStats data files.
- Chat commands handle creation, invites, joining, moderation, and status.
- Team standings are calculated from member race points using configured point mode.
- Optional bits-driven bonus windows can temporarily multiply team points.

---

## 2) Streamer setup (desktop app)

Open **Settings → MyTeams**.

### Core controls

- **Enable MyTeams Commands**
  - Master toggle for MyTeams chat commands.
- **Points Counting Mode**
  - `active`: counts points from member join/create timing onward.
  - `season`: counts full season points.
- **Max Team Size**
  - Hard cap for captain + co-captains + members.
- **TEP Threshold**
  - Team Effort Points required before the automatic TEP bonus triggers.
- **TEP per Race**
  - TEP added for each qualifying team race (before daily caps).
- **TEP Bonus %/Cooldown (min)**
  - First value is TEP bonus percent applied when threshold is reached.
  - Second value is cooldown in minutes after bits bonus activity before TEP can trigger again.
- **TEP Cap Member/Team (daily)**
  - Daily TEP gain cap per member and per team.
  - Prevents runaway looping and keeps participation scaling fair.

### Bits bonus controls

- **Bonus Bits Threshold**: bits required to activate a team bonus roll.
- **Bonus Duration (min)**: minutes added per activation.
- **Bonus Weights 15%/25%/35%/67%**: weighted odds for multiplier result.

### MyTeams admin table/actions

The MyTeams table shows each team's captain, size, recruiting state, active bonus label, and daily/weekly/season points.

Actions:
- **Refresh**
- **Generate Team Name** (copies a generated name to clipboard)
- **Toggle Recruiting** (selected team)
- **Rename Team** (selected team; preserves roster/invites/points cache under the new name)
- **Delete Team** (also clears related invites/cache entries)

---

## 3) Quickstart flows

### A) Captain quickstart

1. `!createteam Your Team Name`
2. `!invite username`
3. `!cocaptain username` (optional)
4. `!recruiting on`
5. `!logo :your_emote:` (optional)
6. `!inactive 14` (optional)
7. `!renameteam New Team Name` (captain only)
8. `!myteam`
9. `!teambonus`

### B) Member quickstart

- Join invite: `!acceptteam Team Name`
- Deny invite: `!denyteam Team Name`
- Auto-join open team: `!join`
- Check status: `!myteam`
- Check bonus progress: `!teambonus`
- Leave: `!leave`

### C) Streamer/admin quickstart

- Use Settings → MyTeams table actions for fast admin operations.
- Captains/co-captains can moderate in chat via `!kick`, `!recruiting`, and `!inactive`.

---

## 4) Current command reference

> Commands use `!` prefix.

### Discovery

- `!teamhelp` — short MyTeams chat explainer.
- `!tcommands` — lists currently available MyTeams commands.

### Team creation + joining

- `!createteam [team name]`
  - Subscriber-only (broadcaster exempt).
  - Fails if user is already in a team.
  - If no name is supplied, MyStats generates one.
- `!invite <username>`
  - Captain/co-captain only.
  - Invite expires after 7 days.
- `!acceptteam <team name>`
  - Accept a pending invite if valid and team has space.
- `!denyteam <team name>`
  - Deny a pending invite.
- `!join`
  - Auto-joins the best available recruiting team with room.
- `!leave`
  - Leaves current team.
  - If captain leaves, captaincy is handed off when possible; empty teams are archived.

### Team management

- `!cocaptain <username>`
  - Captain only.
  - Promotes existing member to co-captain.
- `!kick <username>`
  - Captain/co-captain only.
  - Removes co-captain or member (captain cannot be kicked).
- `!recruiting on|off`
  - Captain/co-captain only.
- `!renameteam <new team name>`
  - Captain only.
  - Renames the current team while keeping members, invites, and cached points aligned to the new name.
- `!logo <emote>`
  - Captain/co-captain only.
  - Sets logo/emote shown in status and overlays.
- `!inactive <days>`
  - Captain/co-captain only.
  - Sets inactivity threshold and runs an immediate stale-member sweep.

### Team status + leaderboards

- `!myteam [@username]`
  - Shows team name, rank, season/daily points, subscriber breakdown, active bonus, bonus races, recruiting state, role, captain tier, and member list.
- `!teambonus [@username]`
  - Shows bits/TEP bank progress, active bonus source, and TEP cooldown status.
- `!dailyteams`
  - Top MyTeams leaderboard (daily window).
- `!weeklyteams`
  - Top MyTeams leaderboard (weekly window).

---

## 5) Roles and permissions

- **Captain**
  - Full team control, including `!renameteam`.
- **Co-captain**
  - Invite, kick, recruiting, logo, inactive-policy controls.
- **Member**
  - Accept/deny invites, view team, leave.

---

## 6) Scoring model (current)

MyTeams scores are computed from member **Race + BR** points with configurable mode:

- **active mode**: member points counted from join/create timestamp.
- **season mode**: member full-season points counted.

Displayed windows:
- Daily
- Weekly
- Season

`!myteam` and UI leaderboard snapshots surface these values.

---

## 7) Bits bonus behavior

- Team member bits add to team bits bank.
- Team races also add Team Effort Points (TEP) to a separate effort bank (participation-driven).
- Bits and TEP are dual-track and non-overlapping: only one active bonus window at a time.
- Bits track rolls weighted bonus tiers (+15%/+25%/+35%/+67%), where 67% is paid-track only.
- TEP track triggers a fixed +15% bonus for 15 minutes by default, and cannot trigger if a bits bonus was active in the last hour.
- Active bonus appears as `⚡+N%` in team status and leaderboard surfaces.

### TEP settings in plain language

- **TEP Threshold** decides how much total team effort is needed to fire the automatic TEP bonus.
- **TEP per Race** defines how quickly teams fill that effort bank from races.
- **TEP Bonus %/Cooldown** controls both the TEP boost size and the lockout window after bits-triggered bonuses.
- **TEP Cap Member/Team (daily)** constrains how much TEP can be earned daily by one member and by the full team.

---

## 8) Dashboard + overlay integration

- **Dashboard** (`/dashboard`)
  - Includes MyTeams leaderboard cards/snapshot.
- **Overlay** (`/overlay`)
  - Rotation includes Top MyTeams Today and Top MyTeams Season cards.

---

## 9) Local data files

- `teams_data.json`
  - Teams, members, invites, role data, recruiting state, bonus state.
- `team_points_cache.json`
  - Cached team points/bonus race counters.

When teams are deleted/archived, related invite and cache entries are cleaned.

---

## 10) Operational best practices

- Start with team size cap around 15–25.
- Keep recruiting closed by default; open intentionally.
- Assign co-captains for larger teams.
- Use `!inactive` policies to keep teams active.
- Tune bonus threshold high enough to feel meaningful.
- Periodically post `!tcommands` in chat.

---

## 11) Troubleshooting

### "Nothing happens when I use team commands"
- Confirm **Enable MyTeams Commands** is on in Settings → MyTeams.

### "I can't create a team"
- `!createteam` requires subscriber status (except broadcaster).
- You cannot create a new team while already in one.

### "Invite won't accept"
- Invite may be expired/denied.
- Team may be full.
- You may already be on a team.
- Target team may have been removed.

### "!join says no teams available"
- No teams are currently both recruiting **and** under max team size.
