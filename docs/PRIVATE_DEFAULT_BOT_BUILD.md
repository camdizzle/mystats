# Private-build default bot credential

The temporary default `mystats_results` bot credential is read from `DEFAULT_BOT_TOKEN` in `mystats.py`, never from ConfigManager/settings. The public repository deliberately leaves that value empty. Populate it only in the private build source. The real credential must not enter Git history, PRs, release guides, logs or standalone settings files.

This is a temporary packaging change, not secure secret distribution: the credential remains extractable from source or a packaged executable, and therefore from an installer containing that executable. The planned hosted bot service is the long-term solution. Existing distributed installers and backups are not rewritten by this change.

## Building

1. Use the current application source and matching `modern_dashboard` / `obs_overlay` assets for the release being built. Retain the private `DEFAULT_BOT_TOKEN` value when updating the build source; never replace the only saved copy without first retaining it securely.
2. Build `mystats.exe` from that private source. Do not publish the source containing the credential.
3. Both current Inno scripts exclude raw `settings.txt`, legacy `token_data.json`, the private Python source and the installer source folder from their wildcard payloads.
4. The full installer explicitly installs `installer/settings-defaults.txt` as `settings.txt` only when no settings file exists. The public template uses non-secret application/setup defaults; review its season and Marble Day fields when preparing a release. The private build template preserves the original non-token settings. The updater does not ship a user's existing settings.
5. Keep the existing required executable, README.html, icon and runtime assets in the build staging folder. This change does not create a compiled executable or installer.

## Existing settings

At settings load, the application atomically removes obsolete `TWITCH_TOKEN` lines while preserving the other bytes. It ignores any such entries that remain because a file is read-only. The settings writer filters the key from ordered, persistent and unmanaged settings so it cannot be reintroduced on save. Other preferences remain unchanged.

## Private folder migration performed

The user-supplied private build folder contained version 6.3.2 source. Its default token was copied into its private Python constant and verified before its settings entry was removed. Its eight installer scripts now use a token-free template and exclude raw settings/source from wildcard inputs. Only the token-related behavior was changed there; that private source was not upgraded to the newer 7.0 implementation. The 7.0 Discord guide must be used with a current build, not that older source.

## Release-guide use

`docs/DISCORD_RELEASE_GUIDE_7.0.0.md` contains three independently pasteable posts, each below 2,000 characters. It covers the source changes from August through merged dashboard PR #411 plus the custom-login storage change in this PR. Publish after shipping a matching build. It does not announce pending Overview PR #412 or a hosted bot service as already available.
