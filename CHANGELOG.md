# Changelog

All notable changes to this project are stored as one markdown file per version in [`changelog/`](./changelog/).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Build Flow

`node scripts/generate_version.js` reads `web/package.json`, loads `changelog/*.md`, sorts releases by semantic version, and writes `web/public/version.json` for the frontend release-history modal.
