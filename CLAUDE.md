# Stouro

## Release rules

These apply to every release, permanently.

1. **One version, three places.** `STOURO_VERSION` in `index.html` is the single source of truth. The splash version (`#splashVersion`) and Settings > About (`#settingsVersion`) are both filled in from it at startup. Also bump the static fallback text in `#splashVersion` and `#releaseNotesTitle` so the first paint matches.
2. **Every version has release notes.** Add a `STOURO_RELEASE_NOTES['<version>']` entry in `index.html` in the same change that bumps `STOURO_VERSION`. Without an entry the release-notes screen is skipped, so a release with no notes counts as incomplete.
3. **Notes are short and written for walkers.** Use 2–5 plain-language bullets about what a user will notice. Leave out internal refactors, file names and jargon. Each version's notes describe only that version's changes.
4. **Keep old entries.** Never edit or delete an earlier version's notes; add new entries above them.
5. **Versioning.** Use `MAJOR.MINOR.PATCH`. While in development, bump the patch number (`0.0.x`) for each release unless told otherwise.
6. **Shown once per version.** The release-notes screen appears after the splash (after the intro slides for new users) until the user taps Continue. That writes `stouroReleaseNotesVersion` to localStorage. Do not reset or rename this key, or returning users will see notes again.
7. **Preserve work in progress.** Before a release change, check `git status` and keep all existing uncommitted changes and untracked assets. Do not commit, push or deploy unless asked.
