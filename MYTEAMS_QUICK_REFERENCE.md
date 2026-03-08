# MyTeams Quick Reference (Current)

Use this as a one-page command and workflow guide for chat, Discord, or stream panels.

---

## What is MyTeams?

MyTeams is MyStats' channel team system (local mode). Viewers form teams, compete on points, and can trigger temporary bits-based team bonuses.

---

## Fast start

### Create and build a team (captain)
1. `!createteam Your Team Name`
2. `!invite username`
3. `!recruiting on`
4. `!myteam`

### Join a team (member)
- From invite: `!acceptteam Team Name`
- Decline invite: `!denyteam Team Name`
- Auto-join recruiting team: `!join`

---

## Current MyTeams command set

### Discovery
- `!teamhelp` — short MyTeams explainer
- `!tcommands` — lists all currently enabled MyTeams chat commands

### Team setup and membership
- `!createteam [team name]` — Create a team (subscriber-only; broadcaster exempt)
- `!invite <username>` — Invite a user (captain/co-captain)
- `!acceptteam <team name>` — Accept invite
- `!denyteam <team name>` — Deny invite
- `!join` — Join a recruiting team with available space
- `!leave` — Leave your current team

### Team management
- `!cocaptain <username>` — Promote member to co-captain (captain only)
- `!kick <username>` — Remove teammate (captain/co-captain)
- `!recruiting on|off` — Open/close recruiting (captain/co-captain)
- `!logo <emote>` — Set team logo (captain/co-captain)
- `!inactive <days>` — Set inactivity policy and sweep stale members (captain/co-captain)

### Team standings and status
- `!myteam [@username]` — Team summary, role, members, points, sub stats, active bonus
- `!dailyteams` — Top teams (daily points)
- `!weeklyteams` — Top teams (weekly points)

---

## Roles at a glance

- **Captain**: full team control
- **Co-captain**: can invite, kick, set logo, recruiting, and inactivity policy
- **Member**: can accept/deny invites, view status, and leave

---

## Bits bonus (quick explanation)

- Bits from team members are added to that team's bits bank.
- When the bank crosses the configured threshold, MyTeams rolls a weighted multiplier (2x/3x/4x).
- Active bonus windows extend/refresh based on settings and appear in team status (for example `⚡3x`).

---

## Dashboard and overlay visibility

- Desktop app: **Settings → MyTeams** for command toggle, scoring mode, team cap, bonus settings, and admin actions.
- Dashboard: `/dashboard` includes MyTeams leaderboard cards.
- Overlay rotation includes:
  - Top MyTeams Today
  - Top MyTeams Season

---

## Common issues

- Team commands do nothing → Enable **MyTeams Commands** in **Settings → MyTeams**
- Can't create team → Subscriber required (except broadcaster)
- Can't accept invite → invite expired, team full, already on team, or team removed
- `!join` fails → no recruiting teams currently open with available slots

---

## Chat blurb for streamers

"MyTeams is live! Type `!tcommands` for team commands. Use `!createteam` to start a team, `!invite` to recruit, and `!dailyteams` / `!weeklyteams` / `!myteam` to track standings."
