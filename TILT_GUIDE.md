# MyStats Tilt Logic Guide

This guide maps the end-to-end Tilt flow in MyStats: data ingestion, run lifecycle, scoring, persisted state, outputs, chat messages, and overlay behavior.

## 1) Where Tilt data comes from

MyStats reads two game-generated CSV files:

- `LastTiltLevel.csv` (`tilt_level_file`): level-level status (current level, elapsed time, top tiltee, level points/xp, total xp, pass/fail).
- `LastTiltLevelPlayers.csv` (`tilt_player_file`): per-player rows for the current level, used to determine survivors and deaths.

At startup, the app ensures both files are configured and created if missing, then continuously watches `tilt_level_file` for mtime changes.

## 2) Core Tilt watcher loop (`tilted`)

The `tilted(bot)` coroutine is the heart of Tilt processing.

### Triggering behavior

- Polls `tilt_level_file` mtime repeatedly.
- Skips processing on initial boot snapshot.
- Only processes when mtime changes (after a short debounce).
- Safely reads CSV with retries/encoding detection to tolerate partially-written files.

### Parsing level state

`parse_tilt_level_state()` supports header aliases with positional fallbacks, then normalizes:

- `current_level` from digits in level field.
- `elapsed_time` string.
- `top_tiltee` (default empty, later normalized to `None` in run logic).
- `level_xp` and `total_xp` as ints.
- `level_passed` as boolean.

### Run initialization

When level 1 is seen and no run is active:

- Generates `run_id` (urlsafe base64 uuid).
- Resets transient run settings (`tilt_run_ledger`, top-tiltee ledger/count, run xp/points, level/run overlay payloads, leader tracking).
- Captures `tilt_run_started_at`.

If no run exists for any reason, a fallback `run_id` is generated.

### Per-level participant evaluation

From `LastTiltLevelPlayers.csv` rows for the current level:

- `active_users` = users present for this level.
- `survivors` = users with points > 0.
- `deaths_this_level` increments when user has 0 points.
- `run_ledger[username]` increases by **level points** for each surviving user.

So standings are accumulated by awarded level points per successful level survival.

### XP/points progression rules

- `earned_xp = floor(survivors_count * tilt_multiplier(level))`.
- `run_xp += earned_xp`.
- `run_points += level_points` only if there is at least one survivor.
- `total_xp_today += earned_xp`.
- `total_deaths_today += deaths_this_level`.

`get_tilt_multiplier(level)` uses a piecewise table:

- L1–14: 1/3
- L15–17: 6
- L18–20: 7
- L21–23: 12
- L24–26: 13.5
- L27–29: 50
- L30–32: 66
- L33–35: 84
- L36–38: 104
- L39–41: 126
- L42+: `135 + (sets_of_three_after_42 * 9)`

### Best/high-water updates

If survivors exist, updates best stats:

- `tilt_best_run_xp_today`
- `tilt_highest_level_points_today`
- `tilt_highest_level_reached_num`
- `tilt_season_best_level_num`
- `tilt_personal_best_level_num`

Also keeps `tilt_lifetime_expertise` in sync with game total xp + configured `tilt_lifetime_base_xp`, then adds current level earned xp.

## 3) What happens on level completion (`level_passed == true`)

When the level is marked passed:

1. Increments internal level counter for narrative cooldown logic.
2. Updates top-tiltee run ledger/count for this run.
3. Appends survivors to daily `tilts_YYYY-MM-DD.csv` (`tilts_results_file`).
4. Optionally emits narrative chat alerts (grinder milestones, top-tiltee milestones, lead-change alerts).
5. Sends level completion chat message(s), chunked to stay under message length.
6. Writes overlay recap payload for the level (`tilt_level_completion_overlay`).
7. Writes text outputs into `TiltedOutputFiles` for OBS/other tooling.

### Tilt results CSV row format written on pass

For each survivor row from player file:

- `[run_id, current_level] + original player row + [is_top_tiltee, event_ids]`

Parser expectations elsewhere rely on:

- `row[0]` run_id
- `row[2]` username
- `row[4]` points
- `row[-2]` top-tiltee boolean-ish value

## 4) What happens on run end (`level_passed == false`)

When level is not passed, the run is considered complete:

1. Builds sorted standings from `run_ledger`.
2. Sends "Tilt run complete" chat with standings (or "No results").
3. Writes run-complete text outputs (including `CurrentLevel.txt=FAIL`).
4. Writes `Top10Today.txt` (newline list of top names) + `Top10Horizontal.txt`.
5. Stores `tilt_last_run_summary` and `tilt_run_completion_overlay`.
6. Increments `tilt_run_completion_event_id` for overlay replay gating.
7. Resets run-scoped transient settings and clears `tilt_current_run_id`.

## 5) Output files: when and what

All Tilt text outputs are written under:

- `%LOCALAPPDATA%\MyStats\TiltedOutputFiles`

### On each passed level

- `LastLevelPoints.txt`
- `CurrentLevel.txt` (next level number)
- `HighestLevelPoints.txt`
- `HighestLevelReached.txt`
- `SeasonBestLevel.txt`
- `PersonalBestLevel.txt`
- `CurrentRunExpertise.txt`
- `RunTotalPoints.txt`
- `TotalExpertiseToday.txt`
- `TotalDeathsToday.txt`
- `LastLevelExpertise.txt`
- `TotalExpertise.txt`

### On run completion/fail

- `CurrentLevel.txt` = `FAIL`
- `PreviousRunExpertise.txt`
- `BestRunXPToday.txt`
- `Top10Horizontal.txt`
- `Top10Today.txt`
- `TotalExpertiseToday.txt`
- `TotalDeathsToday.txt`
- `TotalExpertise.txt`

## 6) Overlay data flow

### Backend payload (`/api/overlay/tilt`)

`_build_tilt_overlay_payload()` assembles:

- `current_run`: live status, level, elapsed, top tiltee/count, run points/xp, leader, standings, totals.
- `last_run`: most recent run summary.
- `level_completion`: single level recap payload.
- `run_completion`: final run recap payload.
- `run_completion_event_id`: monotonically increasing event ID.
- `settings`: tilt theme + scroll tuning + general overlay controls.

### Frontend rendering (`obs_overlay/tilt_overlay.js`)

- Polls payload on interval (`refresh_seconds`, default 3s).
- Renders tracker card (status pills, metrics, current standings).
- Auto-scrolls standings with configurable step/tick/pause settings.
- Shows level recap overlay once per unique `level|completed_at` key (10s).
- Shows run recap overlay once per new event ID/key while idle (15s).
- Hides tracker while recap overlays are visible.
- Caches latest snapshot in localStorage for warm startup display.

## 7) Chat outputs driven by Tilt

### Automatic in-run/run-end chat

- Level pass message:
  - `End of Tilt Level X | Level Completion Time: ... | Top Tiltee: ... | Points Earned: ... | Survivors: ...`
  - Chunked when survivor lists are long.
- Narrative alerts (if enabled), e.g. grinder milestones, top-tiltee milestone, lead-change.
- Run complete messages:
  - `Tilt run complete! Final standings: ...`
  - Or `Tilt run complete! No results to display.`

### User commands over seasonal Tilt CSVs

- `!mytilts [user]`: today + season tilt runs/points/levels + PPL.
- `!toptiltees`: ranked top-tiltee count with season points tie-break.
- `!top10tilees`: top 10 by cumulative tilt points.
- `!tiltsurvivors`: best survival rate (min participated levels threshold).

These commands parse `tilts_*.csv` with encoding detection and use helpers like `parse_tilt_result_row/detail`.

## 8) Season quest integration

Tilt contributes to season quests and leaderboards through:

- Tilt levels participated.
- Top-tiltee finishes.
- Tilt points.

`get_tilt_season_stats()` aggregates these from all `tilts_*.csv`, and quest progress/leaderboards merge that with race/BR stats.

## 9) Practical worked examples

### Example A: Level passes with survivors

Given:

- Current level = 18
- Level points = 1,200
- Survivors = 30
- Multiplier at L18 = 7

Then:

- `earned_xp = floor(30 * 7) = 210`
- `run_xp += 210`
- `run_points += 1200`
- 30 survivor rows written to daily `tilts_*.csv`
- Level recap overlay payload updated
- Passed-level output files refreshed (`CurrentLevel.txt = 19`, etc.)

### Example B: Level fails (run ends)

Given no pass on the current update:

- Run standings are sorted from `tilt_run_ledger`
- Chat posts final standings (chunked if needed)
- `CurrentLevel.txt` becomes `FAIL`
- Last run summary + run completion overlay saved
- `tilt_run_completion_event_id` increments
- Run-scoped state resets for next run

### Example C: Top-tiltee milestone alert

If narrative alerts are enabled and top-tiltee count reaches milestone set `{3, 5, 10, 15, 20, ...}`:

- Grinder alert can fire:
  - `🏁 Grinder: USER reached N top-tiltee appearances this run`
- Top-tiltee milestone alert can also fire each positive count if enabled.

## 10) Key caveats and implementation notes

- Tilt parser assumes expected column positions when headers are absent/changed; malformed rows are skipped safely.
- `run_points` only increases when at least one survivor exists for the level.
- Overlay run recap is event-gated to avoid replaying old completion recaps on refresh/reload.
- `tilt_lifetime_base_xp` allows streamers to seed lifetime totals to align with pre-MyStats progress.
- Output writing is best-effort (warnings logged on failures).
