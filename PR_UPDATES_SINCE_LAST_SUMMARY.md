# PR Updates Since Last Major Summary

This summary covers merged pull requests **#173 through #234** (the changes after PR #172, which originally created the major release notes).

## What users will notice most

### 1) Race and Tilt overlays are cleaner, more readable, and more reliable
- Better splash sequencing, transitions, timing, and alignment in race overlays.
- Smoother behavior for race-end / podium / run-complete moments.
- Continued layout tuning for standings, current-run, summary panels, and overlay scaling.
- Improved readability tweaks across font sizes, spacing, labels, and top-10 list styling.

### 2) Tilt recap and state handling became much more dependable
- Multiple fixes to stop stale/duplicate recap states and repeating tilt messages.
- Better persistence through restarts and refreshes.
- Dynamic sizing improvements so recap/current-run sections use space more intelligently.

### 3) Chat command output quality improved significantly
- New commands and richer outputs (for example `!thisrun`, `!highfive`, and XP/stat output improvements).
- Formatting and naming consistency updates across chat responses.
- Better user tagging consistency in command responses.
- Bug fixes for duplicate/repeating chat messages and reconnect behavior.

### 4) Localization and personality options expanded
- Added language setting support and extended language coverage.
- Added Australian language/slang option.

### 5) Desktop app usability and update flow got polish
- Ongoing improvements to update-screen handling and post-build notification behavior.
- Better minimize-to-tray / systray behavior and open/exit flows.

### 6) Data quality and stat correctness were tightened
- Fixes and revisions around expertise, survivor/death logic, race numbers, and XP/stat line formatting.
- Additional improvements to API polling and mode-detection logic that stabilize what data appears when.

## Net effect for streamers and viewers
- Overlays are now more “broadcast safe”: fewer visual glitches, better timing, better readability.
- Chat interactions feel more consistent and useful during live play.
- The app feels more operationally stable during long sessions due to tray/update/reconnect hardening.
