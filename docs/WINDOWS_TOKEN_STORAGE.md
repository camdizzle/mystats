# Windows OAuth credential storage

Custom Twitch access and refresh tokens formerly saved in `token_data.json` now use a Windows Credential Manager generic credential named `MyStats/TwitchOAuth`. It belongs to the Windows user running MyStats, persists on that PC, and requires neither administrator access nor a new dependency. The Windows API bindings remain inside `mystats.py`.

## Migration and use

On the first token load, MyStats checks Windows first. Only when no entry exists does it inspect known legacy application/launch locations. It validates the payload, writes Windows storage, reads back the exact saved bytes, and then removes unchanged JSON files belonging to that login. Different legacy logins, corrupt files, files changed during migration and files Windows will not let it delete are preserved with a notice. Cleanup of matching leftovers is retried on later loads.

New login and token refresh save and verify Windows storage before activating the login. A successful replacement login removes the known valid legacy token snapshots after verification. Writes never create a JSON fallback. A storage failure retains existing legacy files and reports the problem. Transient refresh/network/server failures retain the saved login instead of erasing it. Both refresh callers use the same serialized path.

Invalidation writes a non-secret signed-out marker in Credential Manager. This prevents an undeletable leftover JSON from reviving the invalid login on the next startup. A new successful login replaces the marker. Manually deleting this Windows entry while old JSON remains permits migration again; remove obsolete token files or use Custom Bot Login to replace them.

Open **Windows Credential Manager → Windows Credentials → Generic Credentials** to find `MyStats/TwitchOAuth`. Run MyStats under the same Windows account as before. Restarting a build containing this change performs migration automatically; no login is normally required. No real user token was migrated during development.

Both Inno installer wildcard entries and Git now exclude `token_data.json`. Installers do not delete user token files: the running application handles deletion only after verified secure storage. Existing external backups and unknown copies are outside the migration's reach.

## Security scope

This protects the stored custom OAuth access/refresh payload by handing storage to Windows rather than leaving a readable JSON file. It does not isolate credentials from other software running as the same Windows user, remove tokens from process memory, revoke old leaked tokens, or erase external backups. Application client credentials and the existing shared/default-bot configuration are separate from this migration and still require their own authentication architecture review. No credentials are added to diagnostics or preference backups. Authentication failures no longer print raw Twitch response bodies.

The implementation follows Microsoft's [CREDENTIALW layout and 2560-byte blob limit](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw), [CredWriteW](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew), and [CredReadW](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credreadw). Oversized payloads fail without deleting legacy files.

## Validation

Isolated tests use synthetic credentials and temporary JSON fixtures. Coverage includes migration/read-back verification, write/read failures, corrupt data, changed/read-only files, duplicate and different accounts, refresh rotation, activation ordering, invalidation markers and native Windows credential round-trip/cleanup. The native check uses a unique temporary `MyStats/StorageTest/...` entry and removes it in a finally block. It never reads or overwrites the user's production credential.

Python compilation, package exclusions and existing desktop/chat regressions are also checked. The native round-trip was run using the available 32-bit Python runtime on Windows. Live Twitch authorization and installer compilation were not performed.
