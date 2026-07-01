# Development Guide

## Versioning & Release System

The UnmessIt.AI frontend uses a static `version.json` file to manage versioning and changelog updates. This approach is highly secure and prevents DDOS or rate-limiting issues associated with polling external APIs like GitHub.

### How it works

1. **`web/public/version.json`**: This is the single source of truth for the latest version and the changelog. It is served statically by the frontend server.
2. **`web/vite.config.ts`**: During the build process, Vite injects the current version from `package.json` into the application as `import.meta.env.VITE_APP_VERSION`.
3. **`web/src/lib/useVersionCheck.ts`**: The application periodically fetches `/version.json?t=[timestamp]`. It compares the fetched version against `VITE_APP_VERSION`.
4. **UI Notification**: If a newer version is detected, a global banner appears in the `AppShell`. Clicking it opens a modal displaying the markdown-formatted changelog, allowing the user to refresh the page to apply the update.

### How to release a new version

When you are ready to cut a new release, follow these steps:

1. **Update `package.json`**:
   Bump the version number in `web/package.json` (e.g., from `0.1.0` to `0.1.1`).
   
2. **Update `public/version.json`**:
   Update `web/public/version.json` with the new version string and the markdown changelog.
   
   ```json
   {
     "version": "0.1.1",
     "changelog": "## UnmessIt.AI 0.1.1\n\n### Added\n- Support for new AI models\n- Improved UI responsiveness\n\n### Fixed\n- Fixed an issue with infinite loading on the settings page"
   }
   ```

3. **Build and Deploy**:
   Run your normal deployment process (`npm run build`). The new `version.json` will be deployed along with the static assets. 
   
4. **Client Notification**:
   Once deployed, active clients will detect the new `version.json` file within an hour (or on their next page load) and prompt the user to update.

### Automated CI/CD Process

We have fully automated the `version.json` generation!

1. **Update `package.json`**:
   Bump the version number in `web/package.json`.
   
2. **Update `CHANGELOG.md`**:
   Add your release notes under the new version header (e.g., `## [0.1.1]`) in the `CHANGELOG.md` file at the root of the project.

When you run `npm run build` in the `web/` directory, it automatically executes the `prebuild` script (`scripts/generate_version.js`). 

This script:
- Reads the current version from `package.json`.
- Extracts the exact markdown release notes for that specific version from `CHANGELOG.md`.
- Generates a fresh `web/public/version.json` file on the fly, which gets packaged with the build.
