# CI/CD

## Staging merge gate

PRs into `staging` run `.github/workflows/staging-release-gate.yml`.

The gate requires:
- `web/package.json` version is greater than `origin/staging`.
- `changelog/<version>.md` changed in the PR.
- `changelog/<version>.md` has release notes headed by the new version.
- `web/public/version.json` can be generated from `web/package.json` and `changelog/*.md`.
- Web lint and build pass.

## Version flow

`web/public/version.json` is generated during CI/build by:

```bash
node scripts/generate_version.js
```

It is not a source file. Do not hand-edit or commit it.

The generated JSON uses:
- `web/package.json` for `version`.
- `changelog/*.md`, sorted by semantic version, for current release notes and full version history.

See [`../CHANGELOGS.md`](../CHANGELOGS.md) for the changelog file layout.

## Prevent direct commits to staging

GitHub branch protection owns this. Repo files can check PRs, but they cannot truly block direct pushes by themselves.

Required protection for `staging`:
- Require pull requests before merging.
- Require status check `Staging release gate / release-gate`.
- Require zero approvals unless you want human review on top of the automated gate.
- Block force pushes.
- Apply rules to administrators if desired.

CLI setup:

```bash
gh api --method PUT repos/:owner/:repo/branches/staging/protection \
  --input .github/branch-protection/staging.json
```
