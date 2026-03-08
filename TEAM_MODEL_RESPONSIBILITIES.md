# Team Model Responsibility Document (MyStats)

This document defines how to implement a complete **channel-level + global team system** for MyStats based on the requested chat commands.

It is split by responsibilities so desktop/bot, backend/web, and data layers can build in parallel.

---

## Delivery Phases

## Phase 1: Local Teams (single channel)
- Implement team lifecycle and moderation commands in-stream.
- Add local scoring model and leaderboards (`!dailyteams`, `!weeklyteams`).
- Add desktop Teams management UI tab (settings, roster visibility, moderation helpers).
- Add team points mode toggle:
  - `season`: use full season contribution.
  - `active`: only count points while team membership is active.

## Phase 2: Global Teams (cross-channel)
- Introduce global team identity and channel-team linking.
- Aggregate linked team points in real-time global leaderboards.
- Add global admin APIs, reconciliation, and anti-cheat cross-channel validation.

---

## 1) Product goals

- Let users create and manage teams inside a channel.
- Enforce role-based permissions (captain/co-captain/member).
- Enforce subscriber-only team creation (`!createteam`) through Twitch API.
- Support recruiting flow (`!join`) for teams accepting random joins.
- Track team and player point contribution for daily/weekly leaderboards.
- Support **global teams** (cross-channel identity) with real-time point calculation on demand.

---

## 2) Command behavior contract

## `!createteam TEAMNAME` (subscriber only)
- Allowed only if user is not already in a team for that channel.
- Validate team name uniqueness per channel (case-insensitive).
- Validate caller is an active subscriber of that channel.
- Create team with caller as captain.
- Default team options:
  - `logo_emote = null`
  - `auto_kick_inactive_days = null`
  - `is_recruiting = false`

## `!invite @username` (captain/co-captain)
- Caller must be captain or co-captain in channel team.
- Target must not already be in any team in that channel.
- Insert pending invite record.
- One pending invite per user per team.

## `!cocaptain @username` (captain only)
- Caller must be captain.
- Target must be current member of caller’s team.
- Promote target role to `co_captain`.

## `!acceptteam TEAMNAME`
- User must have pending invite to TEAMNAME in channel.
- If user already joined another team since invite creation, reject.
- Add membership and mark invite accepted.

## `!denyteam TEAMNAME`
- User must have pending invite to TEAMNAME in channel.
- Mark invite denied.

## `!kick @username` (captain/co-captain)
- Caller must be captain/co-captain.
- Target must be same team.
- Co-captain cannot kick captain.
- Remove membership and role entry for target.

## `!leave`
- Member can leave own team.
- If captain leaves:
  - If co-captain exists, oldest co-captain is auto-promoted to captain.
  - Else oldest member is promoted to captain.
  - Else team is soft-archived (no members).

## `!team @username`
- Returns that user’s team summary in current channel:
  - team name, role, members, total points (daily/weekly/all-time), recruiting status.

## `!myteam`
- Returns caller team stats with member contribution breakdown.

## `!logo EMOTE` (captain/co-captain)
- Update team logo/emote value.
- Validate emote format from message token (Twitch emote text or unicode).

## `!inactive X` (captain/co-captain)
- Set inactivity auto-kick threshold in days (`X`).
- Background job or on-command sweep kicks inactive members exceeding threshold.

## `!join`
- User joins best eligible recruiting team in channel.
- Eligibility criteria (recommended order):
  1. `is_recruiting = true`
  2. team not full (if max size configured)
  3. lowest member count, then oldest team

## `!daily`
- Existing player daily leaderboard (no team grouping).

## `!dailyteams`
- Team leaderboard aggregated by team points earned today.

## `!weekly`
- Existing player weekly leaderboard.

## `!weeklyteams`
- Team leaderboard aggregated by team points earned this week.

---

## 3) Data model (SQL responsibility for web developer)

Use UUID or BIGINT keys consistently. Include `channel_id` on all channel-scoped records.

### 3.1 Core identity tables

1. `channels`
- `id` (pk)
- `twitch_channel_id` (unique)
- `channel_login`

2. `users`
- `id` (pk)
- `twitch_user_id` (unique)
- `login`
- `display_name`

### 3.2 Team tables

3. `teams`
- `id` (pk)
- `channel_id` (fk channels)
- `name`
- `name_normalized` (lowercase, indexed)
- `captain_user_id` (fk users)
- `logo_emote` (nullable)
- `is_recruiting` (bool default false)
- `auto_kick_inactive_days` (nullable int)
- `is_archived` (bool default false)
- `created_at`, `updated_at`

**Constraint:** unique `(channel_id, name_normalized)` where `is_archived = false`.

4. `team_memberships`
- `id` (pk)
- `team_id` (fk teams)
- `channel_id` (fk channels, denormalized for fast filters)
- `user_id` (fk users)
- `role` (enum: `captain`, `co_captain`, `member`)
- `joined_at`
- `last_activity_at`
- `left_at` (nullable)

**Constraint:** one active membership per user/channel:
- unique `(channel_id, user_id)` where `left_at is null`.

5. `team_invites`
- `id` (pk)
- `channel_id` (fk channels)
- `team_id` (fk teams)
- `inviter_user_id` (fk users)
- `invitee_user_id` (fk users)
- `status` (enum: `pending`, `accepted`, `denied`, `expired`, `revoked`)
- `created_at`, `responded_at`, `expires_at`

**Constraint:** unique pending invite per `(team_id, invitee_user_id)` where `status='pending'`.

### 3.3 Points & aggregation tables

6. `player_point_events`
- append-only event stream
- `id` (pk)
- `channel_id`, `user_id`
- `source_type` (race, bonus, correction, etc.)
- `source_ref` (optional external id)
- `points_delta` (int)
- `occurred_at`
- `created_at`

7. `team_point_events`
- immutable projection of player events to team context at event time
- `id` (pk)
- `channel_id`, `team_id`, `user_id`
- `player_point_event_id` (fk)
- `points_delta`
- `occurred_at`

8. `team_score_daily` (materialized/cached)
- `channel_id`, `team_id`, `date_utc`
- `points_total`
- `member_count_snapshot`
- `updated_at`

9. `team_score_weekly` (materialized/cached)
- `channel_id`, `team_id`, `week_start_utc`
- `points_total`
- `member_count_snapshot`
- `updated_at`

### 3.4 Global teams tables

10. `global_teams`
- `id` (pk)
- `name`
- `name_normalized` (unique)
- `logo_emote` (nullable)
- `created_by_user_id`
- `created_at`, `updated_at`

11. `global_team_links`
- links channel team to global team
- `id` (pk)
- `global_team_id` (fk global_teams)
- `team_id` (fk teams)
- `linked_by_user_id`
- `linked_at`

**Constraint:** unique `(team_id)` (a channel team can belong to at most one global team).

12. `global_team_score_daily` / `global_team_score_weekly`
- Same concept as team score tables but aggregated over all linked channel teams.

---

## 4) Query/API requirements for web developer

## 4.1 Command support APIs

1. `POST /api/teams/create`
- input: `channel_id`, `creator_user_id`, `team_name`
- checks subscriber gate (via Twitch service)
- transaction: insert team + captain membership

2. `POST /api/teams/invite`
- input: `channel_id`, `actor_user_id`, `target_user_id`
- validate role and team membership rules

3. `POST /api/teams/invite/respond`
- input: `channel_id`, `user_id`, `team_name`, `action=accept|deny`
- transactional accept logic

4. `POST /api/teams/role/cocaptain`
- captain-only promotion endpoint

5. `POST /api/teams/kick`
- remove member with role guard rails

6. `POST /api/teams/leave`
- handle captain succession logic

7. `POST /api/teams/logo`
- update logo

8. `POST /api/teams/inactive-policy`
- update inactivity days and optionally trigger sweep

9. `POST /api/teams/join-recruiting`
- assigns user to recruiting team

10. `GET /api/teams/by-user?channel_id=&user_id=`
- powers `!team @user`

11. `GET /api/teams/my?channel_id=&user_id=`
- powers `!myteam`

## 4.2 Leaderboard APIs

12. `GET /api/leaderboard/daily`
13. `GET /api/leaderboard/weekly`
14. `GET /api/leaderboard/daily-teams`
15. `GET /api/leaderboard/weekly-teams`
16. `GET /api/leaderboard/global-daily-teams`
17. `GET /api/leaderboard/global-weekly-teams`

For team/global endpoints, support query params:
- `channel_id` (for local team boards)
- `limit` (default 10/25)
- `as_of` (optional timestamp for replay)

---

## 5) Real-time points model (global on demand)

To keep “real-time on demand” fast:

1. Write all player point changes to `player_point_events`.
2. On ingest, resolve active team membership at `occurred_at` and emit `team_point_events`.
3. Maintain cached daily/weekly rollups in score tables (upsert incremental totals).
4. For global teams, aggregate from `team_score_*` over linked teams.
5. If cache miss occurs, fallback to direct aggregation over `team_point_events` for correctness.

Recommended strategy:
- Command path reads from cache first.
- Background job reconciles drift every N minutes.
- Admin endpoint to rebuild day/week/global snapshots.

---

## 6) Twitch API integration (subscriber gating)

Subscriber verification is needed for `!createteam`.

Use Helix endpoint (broadcaster or moderator authorized token required):
- `GET https://api.twitch.tv/helix/subscriptions/user?broadcaster_id={channel_id}&user_id={user_id}`

Expected behavior:
- 200 with data entry => subscriber active.
- 404/no record => not subscribed.
- 401/403 => token invalid or scope missing (log + fail closed).

Required app/oauth considerations:
- Store `access_token`, `refresh_token`, `expires_at` per channel integration.
- Auto-refresh token before expiry.
- Cache positive sub status for short TTL (e.g., 60–180 seconds) to avoid rate pressure.
- Never trust local cache for longer than TTL during create flow.

Fallback policy:
- If Twitch check is unavailable, reject `!createteam` with explicit message (“subscriber verification unavailable; try again shortly”).

---

## 7) Authorization rules matrix

- Captain:
  - all team management commands including `!cocaptain`.
- Co-captain:
  - invite/kick/logo/inactive; cannot assign co-captain; cannot remove captain.
- Member:
  - `!leave`, `!myteam`, view commands.
- Non-member:
  - `!createteam`, `!join`, `!acceptteam`, `!denyteam`, view commands.

All mutating endpoints must verify both:
1. User role in channel team.
2. Team ownership in same `channel_id`.

---

## 8) Edge cases and anti-abuse requirements

- Team names normalized (`trim + lowercase`) for uniqueness.
- Invite expiration (recommended 7 days).
- Rate-limit invite/kick/create/join commands per user.
- Block self-invite, self-kick.
- Ignore duplicate chat commands with idempotency key (`channel_id + user_id + command + minute bucket`).
- Soft-delete/archive teams to preserve historical score integrity.
- Membership history must remain immutable for old events.

---

## 9) Suggested indexes

- `teams(channel_id, name_normalized)` unique partial
- `team_memberships(channel_id, user_id)` partial active
- `team_memberships(team_id, role, left_at)`
- `team_invites(channel_id, invitee_user_id, status)`
- `player_point_events(channel_id, occurred_at)`
- `team_point_events(channel_id, team_id, occurred_at)`
- `team_score_daily(channel_id, date_utc, points_total desc)`
- `team_score_weekly(channel_id, week_start_utc, points_total desc)`
- `global_team_links(global_team_id, team_id)`

---

## 10) Implementation responsibilities by owner

## Bot/Desktop owner (MyStats)
- Parse commands and map to API calls.
- Resolve Twitch username -> user_id for targets.
- Render success/failure chat responses.
- Send `player_point_events` when point-producing actions occur.

## Web/API developer
- Build schema + migrations from section 3.
- Build transactional command endpoints from section 4.
- Implement role checks + channel scoping in every write endpoint.
- Implement leaderboard query endpoints (local + global).
- Implement cache/materialization and rebuild tools.

## Data/infra owner
- Configure DB backups and retention for event tables.
- Add scheduled reconciliation jobs (daily/weekly/global rollups).
- Add observability: command failures, Twitch API failures, cache lag.

---

## 11) Minimum delivery sequence (recommended)

1. Schema + migrations + seed roles.
2. `create/invite/respond/leave/kick` APIs.
3. `myteam/team` read APIs.
4. Team daily/weekly leaderboard endpoints.
5. Twitch subscriber check integration on create.
6. Global team linking + global leaderboard.
7. Reconciliation jobs + admin rebuild endpoint.

This order gets a functional in-channel team system first, then adds global federation.

---

## 12) Competitive advantages (recommended extras)

- **Captain analytics card:** show team contribution %, retention %, and avg points/member to help captains coach better.
- **Smart recruiting quality score:** prefer joining teams with balanced activity and recent positive momentum, not just lowest member count.
- **Fraud resistance:** flag suspicious point spikes with source trace and moderation review queue.
- **Season portability:** allow optional team carry-over package between seasons (name/logo/roster template).
- **Goal systems:** team quests (daily/weekly) that stack with individual quests for dual progression.
- **Narrative hooks for stream:** auto-generated “rival team challenge” prompts to improve viewer engagement.
