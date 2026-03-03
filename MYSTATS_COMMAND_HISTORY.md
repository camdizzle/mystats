# `!mystats` Command Change History (All PRs Reviewed)

This document tracks every merged PR where the `!mystats` command implementation changed.

## Scope / method

- Reviewed all merged PRs in repository history (`238` merged PRs).
- Compared `!mystats` implementation across PR merge commits.
- Recorded only PRs where `mystats_command` changed.

## PRs where `!mystats` changed

### PR #2 (`90a612f`) — Baseline format at beginning

`!mystats` output at this point:

- Prefix with username and **Today** stats.
- Then append **Season total** details.
- Included BR, Race, Season segments and World Records count.

Resulting format:

```text
{winnersdisplayname}: Today: {winstoday} {win/wins}, {pointstoday} points, {racestoday} races. PPR: {today_ppr} | Season total:
BRs - {br_wins} wins, {br_points} points, {br_count} royales, PPR: {br_ppr}. |
Races - {race_wins} wins, {race_points} points, {race_count} races, PPR: {race_ppr}. |
Season - {season_wins} wins, {season_points} points, {season_races} races, PPR: {season_ppr}. |
World Records - {world_record_count}
```

---

### PR #185 (`92e934b`) — Output body switched to `output_msg` only

Changed `send_chat_message(...)` from the long `"{user}: Today: ... | Season total: ..."` string to just `output_msg`.

Resulting format:

```text
BRs - ... | Races - ... | Season - ... | World Records - ...
```

(So the explicit leading `"{user}: Today: ..."` section was removed.)

---

### PR #199 (`940b7c1`) — Response pipeline changed (format unchanged)

`!mystats` command internals were updated to use the unified response helper (`send_command_response`) for certain responses, but the main formatted `output_msg` content did not change in this PR.

Resulting format remained:

```text
BRs - ... | Races - ... | Season - ... | World Records - ...
```

---

### PR #204 (`227e2fd`) — Major formatting refresh

`!mystats` text moved to a richer, normalized format:

- Added `📊` prefix.
- Switched to `pluralize(...)` for nouns (`win`, `royale`, `race`, `record`).
- Changed separators to mostly vertical pipes (`|`) between details.
- Changed world records section to `World Records: ...` (colon and comma formatting).

Resulting format:

```text
📊 BRs - {wins} {win/wins} | {points} points | {royales} {royale/royales} | PPR: {ppr} |
Races - ... |
Season - ... |
World Records: {count} {record/records}
```

---

### PR #209 (`bb80b21`) — Mixed separators style update

Adjusted internal segment punctuation:

- Within BR/Race/Season segments, changed separators from `|` to commas.
- Kept top-level segment breaks as `|`.

Resulting format:

```text
📊 BRs - {wins} {win/wins}, {points} points, {royales} {royale/royales}, PPR: {ppr} |
Races - ... |
Season - ... |
World Records: {count} {record/records}
```

---

### PR #216 (`16448c4`) — User tagging added to output

Prepended a user tag to the line via `format_user_tag(winnersdisplayname)`.

Resulting format:

```text
📊 @{user} | BRs - ... | Races - ... | Season - ... | World Records: ...
```

---

### PR #218 (`4bf089f`) — Display name resolution improved

Kept format from PR #216, but changed how the tagged display name is chosen:

- Prefer `ctx.author.display_name` when available.
- Override from race data display-name column when present.

Resulting visible format stayed the same, but the **name shown in the tag** became more accurate.

## Summary

Across all merged PRs, `!mystats` changed in these PRs:

- `#2`, `#185`, `#199`, `#204`, `#209`, `#216`, `#218`.

Key visible format milestones:

1. **Original (PR #2 era):** `User: Today ... | Season total: ...`
2. **PR #185:** dropped `Today` lead-in; emits season/BR/race/world-record aggregate line.
3. **PR #204/209:** modernized punctuation + pluralization + emoji.
4. **PR #216/218:** user tagging and better display-name sourcing.
