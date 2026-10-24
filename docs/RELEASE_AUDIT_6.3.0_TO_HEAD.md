# Release Audit: Changes Since v6.3.0

## Scope audited
- **Baseline commit (v6.3.0 bump):** `017a5db`
- **Audited range:** `017a5db..HEAD`
- **Total commits in range:** 70 (35 non-merge)
- **Total files changed:** 12
- **Total diff size:** 1242 insertions / 580 deletions

## Change inventory by area

### 1) Storage and path migration (highest impact)
Primary intent across several commits is to centralize writable runtime data in appdata paths and migrate legacy file locations:
- Centralized writable paths under appdata root.
- Added first-run settings migration and path fallback logic.
- Fixed token/settings/results/mycycle lookup fallbacks for non-standard launch contexts.
- Fixed installed-dashboard path resolution and removed test-only nested path candidates.

**Risk posture:** Medium-High (touches many code paths and startup/runtime file IO behavior).

### 2) Auth/token lifecycle and reconnect behavior
Changes improve token refresh and startup/reconnect behavior:
- proactive token refresh before expiry.
- token reconnect cancellation handling fixes.
- avoid bot restart during proactive refresh.
- reduce duplicate token validity logs and make logging thread-safe.

**Risk posture:** Medium (stability improvements, but auth state handling is always sensitive).

### 3) Dashboard/overlay transport and rendering
Web/UI path included notable runtime behavior updates:
- SSE stream implementation for dashboard/overlay with polling fallback.
- overlay mode switching and recap visibility fixes.
- dashboard tab hidden-state and path lookup fixes.
- overlay frame sizing standardization.

**Risk posture:** Medium (front-end runtime and data feed behavior changed, but fixes are coherent and targeted).

### 4) Gameplay/stat logic correctness fixes
A sequence of logic corrections for user-visible commands and scoring:
- `!xp`, `!thisrun`, and `!mytilts` fixes.
- queue-open and raid summary handoff flow updates.
- `!join` renamed to `!jointeam` plus docs updates.
- race winner points output formatting tweak.

**Risk posture:** Low-Medium (bug-fix heavy and generally localized).

### 5) Documentation alignment
README and related guides were updated for command naming and overlay/dashboard guidance consistency.

**Risk posture:** Low.

## Diff concentration (hotspots)
Largest modified files in this range:
- `mystats.py`: +907 / -295
- `obs_overlay/overlay.js`: +206 / -109
- `modern_dashboard/dashboard.js`: +95 / -82

This indicates primary risk concentration remains in core runtime orchestration and dashboard/overlay integration.

## Validation executed in this audit
- `python -m py_compile mystats.py` ✅
- `node --check modern_dashboard/dashboard.js` ✅
- `node --check obs_overlay/overlay.js` ✅
- `node --check obs_overlay/tilt_overlay.js` ✅
- `pytest -q` (no tests discovered) ⚠️

## Release-readiness assessment

### What increases confidence
- The post-6.3.0 stream is predominantly **bugfix and hardening** work rather than broad new feature expansion.
- A large percentage of commits specifically address known operational failures (path fallbacks, token handling, startup noise, dashboard behavior).
- No syntax-level issues were found in Python/JavaScript entry files checked.

### What limits confidence
- No automated test suite coverage was available (`pytest` discovered no tests).
- Significant refactoring in path and runtime file-resolution logic has high blast radius in real-world install variants.
- SSE + polling fallback behavior is runtime-environment dependent and best validated in a live stream-like setup.

## Confidence score

**0.82 / 1.00 (82%)** for shipping today, with a **Go** recommendation.

### Recommended release gate before publish (fast manual smoke)
1. Fresh launch with existing user data and verify settings/token load.
2. Verify dashboard opens and updates (SSE active, polling fallback not stuck).
3. Verify overlay mode switching + tilt recap visibility in OBS/browser source.
4. Run quick command smoke in chat: `!jointeam`, `!mytilts`, `!thisrun`, `!xp`.
5. Confirm exported/results files land in appdata location and legacy migration did not regress history visibility.

If this 5-point smoke passes, this release is suitable to cut today.
