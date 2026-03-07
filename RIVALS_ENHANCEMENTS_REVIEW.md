# Rivals Code Review: Enhancements & Improvements

## Scope reviewed
- Backend rivals computation and settings in `mystats.py`
- Twitch chat command flows for `!rivals`/`!h2h`
- Dashboard rivals rendering in `modern_dashboard/dashboard.js` + `modern_dashboard/index.html`

## High-impact improvements (recommended first)

1. **Reduce O(n²) rival pair generation for large seasons**
   - `get_global_rivalries` compares every qualified player against every other player.
   - As user counts grow, this can become expensive and affect dashboard/chat responsiveness.
   - Improve by sorting users by points once, then using a sliding window bounded by `max_point_gap` to only compare nearby scores.

2. **Precompute/caching for chat commands**
   - `!rivals`, direct pair checks, and dashboard payloads all pull and recompute rivals against season stats.
   - Add a short-lived rivals cache keyed by:
     - season stats version/hash
    - `min_races`, `max_point_gap`, `pair_count`
   - Reuse the same computed matrix for chat + dashboard.

3. **Single source of truth for rivalry scoring/ranking rules**
   - Current ranking is primarily by smallest point gap; tie-breakers are lightweight.
   - Add optional weighted rivalry score (point gap, race proximity, momentum, head-to-head outcomes), then expose score in UI/chat.
   - This improves perceived quality and fairness when many pairs have similar gaps.

4. **Make limits explicit and consistent between backend and UI**
   - Backend defaults and hard caps exist (`pair_count`, dashboard slicing to 200), but UX messaging can drift.
   - Centralize max limits and surface them in API response so dashboard and chat never diverge.

## Correctness and reliability improvements

5. **Username canonicalization hardening**
   - `resolve_user_in_stats` matches by lowercased username/display name.
   - Consider stronger canonicalization (Unicode normalization, repeated whitespace collapse) to reduce false misses.

6. **Handle duplicate display names deterministically**
   - Display-name matching can be ambiguous if multiple users share similar names.
   - Return disambiguation details (or require exact handle when ambiguous), and include guidance in chat responses.

7. **Validation and guardrails for rivals settings**
   - Inputs are clamped, but UX could still allow unrealistic values.
   - Add upper bounds and inline validation feedback (e.g., min races max, gap max) to avoid accidental heavy computations.

8. **Structured telemetry for rivals command branches**
   - Add logging counters for outcomes: no-data, under-min-races, no-rivals-found, rivalry-active, rivalry-inactive.
   - Useful for tuning defaults and understanding feature adoption.

## Chat UX improvements

9. **Short/long response modes for `!rivals`**
   - Current output can get dense in busy chats.
   - Add compact mode by default and optional verbose mode (`!rivals user full`) with richer stats.

10. **Actionable fallback guidance**
    - Some failures say users were not found or no rivals qualify.
    - Add quick hints in the same message (e.g., “try exact @handle”, “lower min races in Settings → Rivals”).

11. **Rate limiting / cooldown tuning**
    - Protect against spam when users query rival checks repeatedly.
    - Add per-user and global cooldowns with friendly responses.

## Dashboard UX and accessibility improvements

12. **Client-side sort controls on rivals board**
    - Add sort toggles: closest gap, biggest gap, most races, best PPR edge.
    - Lets streamers quickly answer different on-stream narratives.

13. **Filter controls and quick presets**
    - Add filters for minimum races, max gap, and search by player.
    - Presets like “Ultra close (≤100)”, “Competitive (≤500)”, “Wide (≤1500)”.

14. **Explain “Most One-Sided” metric transparently**
    - Current highlight mixes point gap and race-gap tie-break.
    - Surface the exact rule in tooltip/help so users trust the card.

15. **Accessibility pass on rivals onboarding toggle**
    - Good `aria-expanded` usage already.
    - Improve keyboard/focus styles and add `aria-controls` linking toggle to collapsible content.

16. **Internationalization coverage for rivals-only strings**
    - Several rivals dashboard messages are English-only.
    - Move these into translation map to align with multilingual app behavior.

## Data and product improvements

17. **Add time-window rivalries (last 7/30 days vs season)**
    - Season-only rivalries can feel stale.
    - Let users compare current form with recent-window rivalries.

18. **Head-to-head race result integration**
    - Blend direct finishing-position outcomes into rivalry score.
    - Enables better storytelling than points-only closeness.

19. **Rivalry trend sparkline**
    - Show whether point gap is closing or widening over recent races.
    - Great for “heating up” narratives in stream overlays.

20. **Export/share rivals snapshots**
    - Add CSV export (and optional image card) from dashboard for social posts or moderator workflows.

## Suggested implementation order

1) Performance/caching (items 1–4)
2) Correctness/validation (items 5–8)
3) Chat UX improvements (items 9–11)
4) Dashboard UX + i18n/accessibility (items 12–16)
5) Product/data enhancements (items 17–20)
