# MyTeams Quick Reference (Viewer-Friendly)

Use this as a one-page command and workflow guide for chat, Discord, or stream panels.

---

## What is MyTeams?

MyTeams is MyStats' local channel team system. Viewers can form teams, compete on points, and engage with team bonuses.

---

## Fast Start

### Create + build a team (captain)
1. `!createteam Your Team Name`
2. `!invite username`
3. `!recruiting on`
4. `!myteam`

### Join a team (member)
- From invite: `!acceptteam Team Name`
- Decline invite: `!denyteam Team Name`
- Auto-join an open team: `!join`

---

## Most-used commands

### Team setup and membership
- `!createteam [team name]` — Create a team (subscriber-only, broadcaster exempt)
- `!invite <username>` — Invite a user (captain/co-captain)
- `!acceptteam <team name>` — Accept invite
- `!denyteam <team name>` — Deny invite
- `!join` — Join an open recruiting team
- `!leave` — Leave current team

### Team management
- `!cocaptain <username>` — Promote member to co-captain (captain only)
- `!kick <username>` — Remove teammate (captain/co-captain)
- `!recruiting on|off` — Open/close recruiting (captain/co-captain)
- `!logo <emote>` — Set team logo (captain/co-captain)
- `!inactive <days>` — Set inactivity policy + sweep stale members (captain/co-captain)

### Team info + standings
- `!teamhelp` — Quick MyTeams overview blurb
- `!myteam [@username]` — Team status for you or a tagged user
- `!dailyteams` — Top teams today
- `!weeklyteams` — Top teams this week
- `!tcommands` — List MyTeams commands

---

## Roles at a glance

- **Captain**: full control
- **Co-captain**: can invite/kick/logo/recruiting/inactive
- **Member**: can accept/deny invites, view status, leave

---

## Bits bonus (quick explanation)

- Bits donated by a team member go to that team's bits bank.
- Crossing the configured threshold triggers a bonus multiplier window (2x/3x/4x weighted).
- Active bonus appears in team status/leaderboards (e.g., `⚡3x`).

---

## Dashboard + overlay visibility

- Dashboard: open `/dashboard` → **MyTeams** tab
- Overlay rotation includes:
  - Top MyTeams Today
  - Top MyTeams Season

---

## Common issues

- Team commands do nothing → Enable MyTeams commands in **Settings → MyTeams**
- Can't create team → Must be subscriber (unless broadcaster)
- Can't accept invite → invite expired, team full, or team deleted
- `!join` fails → no open recruiting teams with available slots

---

## Chat blurb for streamers

"MyTeams is live! Type `!tcommands` for team commands. Use `!createteam` to start a team, `!invite` to recruit, and `!dailyteams` / `!weeklyteams` / `!myteam` to track standings."
