# Update Button / Installer Flow Breakdown

This document maps the complete code path behind the **One-Click Update** button and calls out where installer launch can fail if MyStats is terminated mid-update.

## 1) Where update availability is detected

Function: `ver_season_only()` in `mystats.py`.

- Calls the app settings endpoint and reads:
  - `version` (server/latest version)
  - `download_url` (installer URL)
- If `versioncheck != version`, it:
  1. Prints update availability
  2. Shows a Windows toast
  3. Opens the update popup via `show_update_message(versioncheck, download_url)`

## 2) Update popup and button wiring

Function: `show_update_message(versioncheck, download_url)`.

UI elements:
- Title: `Update Available`
- Message text showing current and latest version
- Link to release page
- Buttons:
  - `One-Click Update`
  - `Remind Me Later`

Critical handler:
- `One-Click Update` calls `start_update()`.
- `start_update()`:
  1. marks `update_now_requested = True`
  2. closes popup
  3. calls `download_and_install_update(download_url, versioncheck, silent_mode=True)`

## 3) Download progress window and background download

Function: `download_and_install_update(download_url, version_label, silent_mode=True)`.

Steps:
1. Validates `download_url`.
2. Shows an initial toast: download started.
3. Creates modal progress UI via `_create_update_progress_dialog(version_label)`.
4. Starts a daemon worker thread (`threading.Thread(..., daemon=True)`) that:
   - streams installer bytes from `requests.get(download_url, stream=True)`
   - writes to a temp executable using `tempfile.NamedTemporaryFile(delete=False, suffix='.exe', prefix='mystats_update_')`
   - updates progress UI via `root.after(...)`

Completion path inside worker:
- Sets progress to 100%
- Updates status to "Launching installer..."
- Closes progress dialog shortly after
- Schedules `_start_installer_and_exit(installer_path, silent_mode=silent_mode)`

## 4) Installer launch command and shutdown behavior

Function: `_start_installer_and_exit(installer_path, silent_mode=True)`.

Launch command:
- Base: `[installer_path]`
- Silent flags when `silent_mode=True`:
  - `/VERYSILENT`
  - `/SUPPRESSMSGBOXES`
  - `/NORESTART`
  - `/CLOSEAPPLICATIONS`

Then:
1. `subprocess.Popen(command, shell=False)` starts installer.
2. Calls `force_exit_application()` immediately after successful spawn.

`force_exit_application()` sets `is_forced_exit = True` and calls `on_close()`.

`on_close()` forced-exit branch:
- Disables root UI
- Shows "Application is closing..."
- Stops bot loop (`BOT_SHOULD_RUN = False` + scheduled bot shutdown)
- Destroys tray icon and root window after a short delay

## 5) Why installer launch may fail after MyStats is killed

Observed from code behavior:

1. **Updater worker is daemon-thread based**
   - The download + launch path runs in a daemon thread.
   - If the MyStats process is killed (Task Manager/end task/crash) before `_start_installer_and_exit(...)` runs, that thread is terminated too, so installer never launches.

2. **Launch is deferred via `root.after(...)` callbacks**
   - The actual installer start is scheduled on the Tk event loop.
   - If the app is killed or Tk loop is blocked/stopped between download completion and callback execution, launch is skipped.

3. **No persisted resume/recovery marker for in-progress update**
   - There is no startup check like "downloaded installer exists, continue launch".
   - So a killed app has no recovery step for pending installer execution.

## 6) Related update state settings

- `update_later_version`
- `update_later_clicks`

These are managed by:
- `_get_update_later_clicks(versioncheck)`
- `_register_update_later_click(versioncheck)`

Current note: in this file, `Remind Me Later` currently closes the popup and does not increment a click counter in the button command path.

## 7) Practical implications for support triage

When users report "installer didn’t launch":

- Ask whether they killed MyStats during or right after the update download.
- Verify whether the app reached "Download complete. Launching installer..." state.
- If MyStats was terminated early, expected behavior from current code is that installer launch may be skipped.

## 8) Hardening ideas (future change candidates)

1. Persist a "pending installer path" setting before launch and consume it at next startup.
2. Launch installer with a detached helper process before UI teardown.
3. Add a startup recovery check that launches pending installer if present and valid.
4. Avoid depending only on daemon-thread + Tk callback timing for critical installer start.
