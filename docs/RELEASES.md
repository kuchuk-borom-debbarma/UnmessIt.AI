# Release Notes

Release notes live in `changelog/`, one file per semantic version:

```txt
changelog/
  0.0.1.md
  0.0.2.md
  0.0.3.md
```

Each file must start with its version heading:

```md
## [0.1.0] - 2026-07-03
```

`scripts/generate_version.js` reads every `*.md` file in that folder, sorts them by semantic version, and writes `web/public/version.json`. The frontend consumes that generated JSON for the Release History modal.

`CHANGELOG.md` is intentionally absent. Do not recreate it; write release notes directly into `changelog/<version>.md`.

For a release:

1. Bump `web/package.json`.
2. Add or update `changelog/<version>.md`.
3. Run `node scripts/generate_version.js`.
4. Do not commit `web/public/version.json`.

The staging release gate checks that `changelog/<web package version>.md` changed and has a matching version heading.
