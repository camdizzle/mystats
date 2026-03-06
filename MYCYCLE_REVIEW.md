# MyCycle Code Review: Enhancement Ideas

## 1) Data model & migration robustness
1. **Add a schema version migrator for `mycycle_data.json`.** The loader currently defaults missing top-level keys but does not migrate older session/user shapes into a normalized structure before read/write cycles.
2. **Normalize username keys once at ingest boundaries.** Several paths rely on lowercase + strip rules; centralizing this into a single helper would prevent subtle mismatches between `display_name` lookups and stat-key lookups.
3. **Store timestamps in ISO-8601 UTC.** Current timestamps are local-time formatted strings, which complicates cross-timezone ordering and dashboard consistency.

## 2) Concurrency, persistence, and failure handling
4. **Reduce write frequency in read-oriented paths.** `get_mycycle_progress`, `get_mycycle_sessions`, and cycle-stats paths write file state even when no user-visible values changed; this is unnecessary disk churn under frequent dashboard polling.
5. **Add file corruption backup/recovery flow.** If `mycycle_data.json` is malformed, loader currently resets to empty payload; a backup of bad payload and explicit recovery message would avoid silent data loss.
6. **Add bounded retry around atomic replace.** `os.replace` is correct for atomicity, but temporary transient I/O errors (networked drives, antivirus hooks) should trigger retries before hard failure.

## 3) Core cycle math & stat quality
7. **Track cycle history records, not only aggregates.** Keeping per-cycle snapshots (`completed_at`, `races_used`, `session_id`) unlocks richer analytics and better debugging of suspicious spikes.
8. **Use tie-breakers that reward efficiency.** Leaderboard currently ranks by cycles completed, progress hits, then current-cycle races; consider adding total races or average races-per-cycle to make ties fairer.
9. **Expose BR-vs-Race split metrics per user.** MyCycle can include BR rows, but downstream stats don’t expose mode-specific cycle efficiency.
10. **Fix all-season MyCycle analytics merge shape.** Multi-season aggregation reads `session['users']`, while active MyCycle data stores records under `session['stats']`; this can under-report historical MyCycle data.

## 4) API / command / UX improvements
11. **Add session argument support to `!mycycle`.** `!cyclestats` supports session selection, but `!mycycle` is locked to primary session and cannot directly query a named custom session.
12. **Add pagination/filtering for dashboard MyCycle rows.** Front-end caps display at first 120 racers; adding sort/filter controls would improve large-season usability.
13. **Return machine-friendly timestamps in API payloads.** Dashboard currently displays raw timestamp strings; adding epoch or ISO fields would support relative-time labels and localization.
14. **Add explicit inactive-session controls in UI.** Session management exists, but home leaderboard navigation could better show active/inactive state and explain why a session is hidden.

## 5) Testability and maintainability
15. **Extract MyCycle logic into a dedicated module with unit tests.** Most MyCycle logic sits inside a monolithic file, making regression testing and reuse harder.
16. **Add deterministic tests for cycle completion edge cases.** Examples: duplicate placements in one cycle, min/max placement changes mid-season, and mixed race+BR ingestion.
17. **Add contract tests for dashboard payload compatibility.** Front-end assumptions (field presence/types) should be validated against API serializers.

## 6) Performance opportunities
18. **Cache dashboard payload segments with short TTL.** Main dashboard rebuilds multiple expensive aggregates on request; short-lived cache can cut CPU and disk pressure.
19. **Avoid repeated full-file scans for historical aggregates.** All-season analytics repeatedly walk CSV directories; precomputed rollups per directory would scale better.

## Quick implementation priority (suggested)
- **High impact / low effort:** #4, #10, #11, #13
- **High impact / medium effort:** #1, #7, #15, #18
- **Strategic investments:** #16, #17, #19
