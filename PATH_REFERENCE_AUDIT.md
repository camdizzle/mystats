# Path Reference Audit (MyStats)

## Goal
Ensure that **all files the app writes** land under:

- `/appdata/local/mystats`

While still allowing `mystats.py` to run from any working directory.

## What exists today

### 1) Config/settings location is mixed
- `settings.txt` is resolved from script dir, current working directory, executable dir, then fallback to `~/.mystats/settings.txt`.
- This means config can move depending on launch context.

### 2) Results/output root is currently Windows-user-profile based
- `create_results_files()` writes season data to `~\AppData\Local\MyStats\Results\Season_<n>`.
- It sets `directory`, `allraces_file`, `checkpoint_results_file`, `tilts_results_file`, and `map_results_file` under that root.

### 3) External game input files are read/written in MOS SaveGames
- These are currently set to `~\AppData\Local\MarblesOnStream\Saved\SaveGames\...`:
  - `LastSeasonRoyale.csv`
  - `LastSeasonRace.csv`
  - `LastTiltLevelPlayers.csv`
  - `LastTiltLevel.csv`
  - `LastRaceNumbersHit.csv`
  - `LastCustomRaceMapPlayed.csv`
- Current logic creates these files if missing.

### 4) Many write targets are relative-path outputs (working-directory dependent)
These currently write to wherever the process starts:
- `mystats.log`
- `log.txt`
- `HighScore.txt`
- `LatestWinner.txt`
- `LatestWinner_horizontal.txt`
- `race_hs_season.txt`
- `br_hs_season.txt`
- `race_hs_today.txt`
- `br_hs_today.txt`
- `TotalPointsToday.txt`
- `AvgPointsToday.txt`
- `CountofRaces.txt`
- `token_data.json`

### 5) Some app-internal JSON artifacts are anchored to configured `directory`
- Team/cache files are resolved via `config.get_setting('directory')`:
  - `teams_data.json`
  - `team_points_cache.json`
- Competitive raid JSON files are also placed under `directory`.

### 6) Mixed static roots still exist
- A few places hardcode `~\AppData\Local\MyStats\...` directly instead of using one central path resolver.

---

## Absolute vs Relative summary

### Absolute-ish / expanded-user references
- `~\AppData\Local\MyStats\...` (results/output)
- `~\AppData\Local\MarblesOnStream\Saved\SaveGames\...` (game source files)
- `%localappdata%/mystats/...` in parts of UI defaults

### Relative references
- `mystats.log`, `settings.txt` candidates (script/cwd/exe), `HighScore.txt`, `LatestWinner*.txt`, `log.txt`, `token_data.json`, stat text files listed above.

---

## Risk to your target state

With the current structure, write locations vary by:
- launch directory,
- packaging mode (script vs executable), and
- code path.

That directly conflicts with your requirement that **all writes must live in `/appdata/local/mystats`**.

---

## Plan to fix cleanly

1. **Introduce one canonical writable root**
   - `APPDATA_ROOT = Path('/appdata/local/mystats')`
   - Create on startup (`mkdir -p`).

2. **Create a small path helper layer**
   - `get_appdata_file(name)` and `get_appdata_subdir(*parts)`.
   - Optional: helper map for known artifacts (`high_score_file()`, `token_file()`, etc.).

3. **Move settings + logs + token to canonical root**
   - `settings.txt`, `mystats.log`, `token_data.json`, `log.txt`.

4. **Move all relative text outputs to canonical root**
   - `HighScore.txt`, `LatestWinner*.txt`, `race_hs_*.txt`, `br_hs_*.txt`, `TotalPointsToday.txt`, etc.

5. **Retain MOS input file locations as external read sources (not app outputs)**
   - Keep `race_file/br_file/checkpoint_file/...` pointing to MOS SaveGames.
   - Stop creating/writing those files from MyStats (read-only behavior preferred).

6. **Unify season/result data under canonical root**
   - Example target: `/appdata/local/mystats/results/Season_<n>/...`
   - Keep `config['directory']` pointed there.

7. **Add migration step for existing users**
   - On first run after update, detect known legacy files in cwd/script dir/old AppData path and move/copy once.
   - Keep backup behavior simple and logged.

8. **Validation pass**
   - Grep/AST check for `open(..., 'w'/'a')`, `logging.FileHandler`, and temp writes to ensure all app-owned writes point to `/appdata/local/mystats`.

