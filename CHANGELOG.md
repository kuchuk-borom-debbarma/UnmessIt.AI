# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-03

### Added
- Provider-native prompt caching now activates automatically for official OpenAI LLM presets by sending a stable, non-secret prompt cache key.
- Prompt rules now document cache-friendly structure: durable instructions first, reusable schemas/examples next, and dynamic user/source data last.
