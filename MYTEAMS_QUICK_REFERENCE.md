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
4. `!renameteam New Team Name` (when needed)
5. `!myteam`
6. `!teambonus`

### Join a team (member)
- From invite: `!acceptteam Team Name`
- Decline invite: `!denyteam Team Name`
- Auto-join recruiting team: `!jointeam`

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
- `!jointeam` — Join a recruiting team with available space
- `!leave` — Leave your current team

### Team management
- `!cocaptain <username>` — Promote member to co-captain (captain only)
- `!kick <username>` — Remove teammate (captain/co-captain)
- `!recruiting on|off` — Open/close recruiting (captain/co-captain)
- `!renameteam <new team name>` — Rename your team (captain only; keeps roster/invites/points cache aligned)
- `!logo <emote>` — Set team logo (captain/co-captain)
- `!inactive <days>` — Set inactivity policy and sweep stale members (captain/co-captain)

### Team standings and status
- `!myteam [@username]` — Team summary, role, members, points, sub stats, active bonus
- `!teambonus [@username]` — Bits/TEP bank progress, active bonus source, and TEP cooldown status
- `!dailyteams` — Top teams (daily points)
- `!weeklyteams` — Top teams (weekly points)

---

## Roles at a glance

- **Captain**: full team control (including team rename)
- **Co-captain**: can invite, kick, set logo, recruiting, and inactivity policy
- **Member**: can accept/deny invites, view status, and leave

---

## Bits bonus (quick explanation)

- Bits from team members are added to that team's bits bank.
- Team races add Team Effort Points (TEP) to an effort bank (participation-based).
- Dual-track rule: bits and TEP do not overlap; only one bonus window can be active at a time.
- Bits bank crossing threshold rolls weighted bonus tiers (+15%/+25%/+35%/+67%), with 67% reserved for paid bits track.
- TEP bank crossing threshold triggers fixed +15% for 15m by default, and is blocked for 60m after bits bonus windows.
- Active bonus windows appear in team status (for example `⚡+35%`).

### TEP settings cheat sheet

- **TEP Threshold**: total Team Effort Points needed to trigger the automatic TEP bonus.
- **TEP per Race**: Team Effort Points gained from each qualifying team race.
- **TEP Bonus %/Cooldown (min)**: TEP boost amount and cooldown after bits activity.
- **TEP Cap Member/Team (daily)**: daily ceiling for per-member and team-wide TEP gain.

---

## Dashboard and overlay visibility

- Desktop app: **Settings → MyTeams** for command toggle, scoring mode, team cap, bonus settings, and admin actions (including **Rename Team** for the selected row).
- Dashboard: `/dashboard` includes MyTeams leaderboard cards.
- Overlay rotation includes:
  - Top MyTeams Today
  - Top MyTeams Season

---

## Common issues

- Team commands do nothing → Enable **MyTeams Commands** in **Settings → MyTeams**
- Can't create team → Subscriber required (except broadcaster)
- Can't accept invite → invite expired, team full, already on team, or team removed
- `!jointeam` fails → no recruiting teams currently open with available slots

---

## Chat blurb for streamers

"MyTeams is live! Type `!tcommands` for team commands. Use `!createteam` to start a team, `!invite` to recruit, `!renameteam` to rename your team (captain only), and `!dailyteams` / `!weeklyteams` / `!myteam` / `!teambonus` to track standings and bonus progress."
