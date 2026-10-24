# File Management Logic Audit (April 1, 2026)

This audit reviews the current file-management paths in `mystats.py` and calls out gaps that can still cause data integrity issues.

## Scope reviewed

- Season results migration and initialization.
- One-time Season 68 cleanup behavior.
- Team data and cache persistence.
- MyCycle persistence patterns (as a comparison baseline).
- General write/replace patterns and failure handling.

## Current behavior breakdown

### 1) Season migration flow

- Season results migration is intentionally disabled for race/BR/checkpoint/tilt artifacts.  
- New seasons are treated as a blank slate for season-scoped result files.  
- The previous season migration helper was removed to avoid confusion/duplicate responsibility; startup/reset initialization owns directory creation.

Reference: `create_results_files`.  

### 2) One-time Season 68 cleanup flow

- Runs only when season is `68` and cleanup flag is not set.
- Deletes files in `Season_68` with mtime before `2026-03-31`.
- Sets persistent completion flag after run.

Reference: `_run_one_time_season68_cleanup_if_needed`, `create_results_files`.

### 3) Team data persistence

- Team JSON and team cache JSON are loaded with parse guards.
- Save path writes directly with `open(..., 'w')` and `json.dump(...)`.

Reference: `_load_team_data`, `_save_team_data`, `_load_team_points_cache`, `_save_team_points_cache`.

### 4) MyCycle persistence (stronger pattern)

- Writes to temp file, then `os.replace` with retry loop.
- This is the safer/atomic pattern currently not used everywhere else.

Reference: `save_mycycle_data`.

## Gaps identified (potential future issues)

1. **Season 68 cleanup deletes *all* pre-cutoff files in folder.**  
   Cleanup iterates every file in the folder and removes by mtime only; no allowlist of expected result files.

2. **Cleanup depends on mtime trustworthiness.**  
   Copy operations and user/system clock behavior can alter mtime and lead to false positives/false negatives.

3. **Cleanup marks completion even when some deletes fail.**  
   Flag is set regardless of partial failures, making retries impossible without manual flag reset.

4. **No backup/rollback for destructive cleanup.**  
   Deleted files are unlinked directly; there is no quarantine folder or restore path.

5. **Team/cache writes are non-atomic.**  
   `_save_team_data` and `_save_team_points_cache` write directly to final file; interruption can leave truncated/corrupt JSON.

6. **Inconsistent durability strategy across modules.**  
   MyCycle uses temp+replace+retry (good), while team/cache files use direct writes (weaker), increasing inconsistency and operational risk.

7. **Limited observability for migration/cleanup outcomes.**  
   Logging exists, but there is no persisted audit ledger (e.g., per-run JSON event record) to support incident investigations.

8. **No concurrency guard around migration/cleanup.**  
    If initialization is triggered concurrently, there is no lock specifically protecting cleanup/migration file operations.

## Recommended next hardening steps (priority order)

1. Apply atomic-write helper everywhere JSON state is saved (team data/cache, token data, other mutable state files).  
2. Restrict cleanup to an explicit allowlist of season result artifacts (`allraces_*.csv`, `checkpoints_*.csv`, `tilts_*.csv`, `maps_*.csv`, raid JSON files).
3. Replace delete with quarantine move (`Season_68/_cleanup_quarantine/<timestamp>/...`) plus retention policy.
4. Set cleanup-complete flag only when all targeted operations succeed (or store partial-state for resumable retry).
5. Add a migration/cleanup audit JSONL file in appdata for support diagnostics.
6. Add a process-level lock around `create_results_files` migration/cleanup phases.

## Summary

Disabling season-result migration removes the highest-risk copy path, but file management still has integrity risks in destructive cleanup behavior, non-atomic writes, and limited operational observability. The highest-value next fix is standardizing atomic/quarantined file operations across mutable state paths.
