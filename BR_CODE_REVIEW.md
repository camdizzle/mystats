# BR Code Review (mystats.py)

This document reviews the current Battle Royale (BR) pipeline and highlights practical improvements.

## Scope reviewed

- `async def royale(bot)` BR watcher + parser + announcement flow.
- BR-related high score/state updates and output files.
- BR stat recomputation patterns that affect responsiveness and reliability.

## Priority improvements

### 1) Prevent event-loop blocking in `royale`

**Issue**
- The BR coroutine uses `time.sleep(...)` inside retry handling, which blocks the entire asyncio loop during retries.

**Where**
- `mystats.py` lines 12631-12639.

**Why improve**
- Blocking sleeps can delay chat responses, overlays, and other async tasks.

**Recommendation**
- Replace `time.sleep(retry_delay)` with `await asyncio.sleep(retry_delay)`.
- Keep all I/O waits in this coroutine async-safe.

---

### 2) Avoid hot-spin loop when BR file is missing

**Issue**
- On `FileNotFoundError`, the loop immediately `continue`s with no delay.

**Where**
- `mystats.py` lines 12580-12583.

**Why improve**
- Can cause unnecessary CPU churn if the file is temporarily absent.

**Recommendation**
- Add a small backoff (e.g., `await asyncio.sleep(1-3)`) before continuing.

---

### 3) Replace naive CSV splitting with a CSV parser

**Issue**
- BR input rows are parsed via `.split(',')`.

**Where**
- Header parse at line 12648 and row parse at line 12666.

**Why improve**
- Names or fields containing commas can break indexing and corrupt data.

**Recommendation**
- Use the same CSV iteration utility used elsewhere (`iter_csv_rows`) or Python's `csv.reader`.
- Preserve explicit schema checks and fallback logging.

---

### 4) Remove duplicated message/color logic via helpers

**Issue**
- Message creation and color-code mapping are duplicated across crown/non-crown and chunk/non-chunk branches.

**Where**
- Message branches: lines 12817-12871.
- Color mapping duplicated: lines 12899-12912 and 12918-12931.

**Why improve**
- Increases maintenance overhead and risk of formatting drift.

**Recommendation**
- Create small helpers:
  - `build_br_winner_message(..., crownwin, chunky)`
  - `map_name_color(color_code)`
- Keep final display/send behavior unchanged.

---

### 5) Reduce O(N) rescans of `allraces_file` per BR event

**Issue**
- The BR flow re-opens and scans all historical rows for per-player counts and winner totals each update.

**Where**
- Race-count scan: lines 12714-12719.
- Winner totals scan: lines 12792-12801.

**Why improve**
- Cost grows with history size and can become noticeable during long seasons.

**Recommendation**
- Maintain incremental counters in memory and/or a compact cache persisted on shutdown.
- If full rescan is needed, do it on startup/day reset instead of every BR update.

---

### 6) Harden numeric conversions and malformed row handling

**Issue**
- Multiple `int(...)` conversions assume clean data (`br_winner[4]`, etc.).

**Where**
- Example conversions at lines 12707-12708, 12713, 12742, 12797.

**Why improve**
- One malformed value can skip the entire update path or trigger broad exception handling.

**Recommendation**
- Introduce safe parse helpers (`to_int_or_default`) for external-file fields.
- Keep warning logs with enough context (line index + raw row).

---

### 7) Count marbles correctly for winner display

**Issue**
- `marbcount = len(lines)` includes the header line.

**Where**
- `mystats.py` line 12650.

**Why improve**
- User-facing marble count may be off by +1.

**Recommendation**
- Use `len(lines) - 1` when a header is present and valid.

---

### 8) Normalize and centralize winner identity handling

**Issue**
- Winner display/identity logic (`br_winner[1]` vs `br_winner[2].lower()`) is repeated.

**Where**
- Repeated at lines 12737-12740, 12760-12763, 12809-12812, and message branches.

**Why improve**
- Repetition makes behavior hard to reason about and risks subtle inconsistencies.

**Recommendation**
- Add a helper returning `winner_login`, `winner_display`, and `winner_label` once.

---

### 9) Prefer atomic writes for overlay/output files

**Issue**
- Output files are written directly (`LatestWinner.txt`, `HighScore.txt`, etc.).

**Where**
- Lines 12749-12773 and other BR score files in the module.

**Why improve**
- Partial writes are possible if interrupted mid-write.

**Recommendation**
- Write to temp file then `os.replace(...)` for atomic swap.

---

### 10) Clarify config semantics (`hscore` naming)

**Issue**
- `hscore` appears to represent BR high score in BR path naming, which is ambiguous.

**Where**
- BR high score updates around lines 12744-12751.

**Why improve**
- Ambiguous naming slows onboarding and increases accidental misuse.

**Recommendation**
- Introduce explicit aliases (`br_hscore_global`, etc.) with migration shim.

## Suggested implementation order

1. Async safety fixes (items 1-2).
2. Parser correctness and resilience (items 3, 6, 7).
3. Maintainability refactors (items 4, 8, 10).
4. Performance optimization/caching (item 5).
5. Output robustness (item 9).
