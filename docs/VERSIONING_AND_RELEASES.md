# Versioning and Releases

UnmessIt.AI uses an automated, git-driven workflow for versioning and releases. The source of truth for the application's current version is `web/package.json`.

## How Versioning Works

1. **`web/package.json`**: Contains the current semantic version (e.g. `0.1.6`).
2. **`changelog/<version>.md`**: Contains the release notes specific to a single version.
3. **`web/public/version.json`**: A generated JSON payload that combines the package version with the entire semantic history of the changelog folder. The frontend fetches this file to display the "Release History" and trigger "Update Available" banners.

## How it's Automated (CI/CD)

The `staging` branch is highly protected. It blocks direct pushes and requires PRs to pass a strict "release gate".

When a developer opens a Pull Request against `staging`, the `.github/workflows/staging-release-gate.yml` workflow runs:
1. It validates that `web/package.json` was bumped to a higher version than the target branch.
2. It verifies that a corresponding `changelog/<version>.md` file was added/changed.
3. **It runs `node scripts/generate_version.js` to build `web/public/version.json`.**
4. **It uses a bot to automatically commit and push the generated `version.json` directly back to the developer's PR branch.**

Once the CI tests pass, the PR is merged into `staging`, carrying the updated `version.json` with it!

## What Developers Have to Do

When you are ready to ship a new feature or fix to `staging`:

1. **Bump the Version**: Update `version` in `web/package.json`.
2. **Write Release Notes**: Create or edit `changelog/<your-new-version>.md` and write your changes. Ensure the file starts with `## <your-new-version>`.
3. **Commit and Push**: You only need to commit the code you wrote, the `package.json` bump, and the changelog file. 
4. **Open a PR**: The CI pipeline will automatically run the generation script and attach the `version.json` commit to your PR for you. You don't have to generate it manually!

### Bypassing Version Bumps
If your PR is **strictly** limited to documentation changes (`.md` files only), the release gate will intentionally bypass the version bump requirement. You do not need to update `package.json` or write a changelog.
