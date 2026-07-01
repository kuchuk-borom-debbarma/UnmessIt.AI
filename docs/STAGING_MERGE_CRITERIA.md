# Staging Merge Criteria

PRs into `staging` must pass `.github/workflows/staging-release-gate.yml`.

Required:
- `web/package.json` version is greater than `origin/staging`.
- `CHANGELOG.md` changed in the PR.
- `CHANGELOG.md` has release notes for the new version.
- CI regenerates `web/public/version.json` from `web/package.json` and `CHANGELOG.md`.

Prevent direct commits in GitHub:
- Protect `staging`.
- Require pull requests before merging.
- Require the `Staging release gate / release-gate` status check.
- Restrict who can push to matching branches if needed.
